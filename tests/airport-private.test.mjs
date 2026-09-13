import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { flightCategory, privateWeather, lookaheadTime } from '../src/lib/airport-private.ts';

const now = Date.parse('2026-09-12T06:00:00Z');
const snapshotAt = new Date(now).toISOString();
const c = { windDirection:'180', windKt:10, gustKt:null, visibilityMi:'6+', weather:null,
  clouds:[{cover:'SCT',baseFt:5000,type:null}], verticalVisibilityFt:null };
const f = {id:'test',raw:'TAF test',issuedAt:'2026-09-12T05:30:00Z',firstSeenAt:'2026-09-12T05:45:00Z',
  validFrom:snapshotAt,validTo:'2026-09-13T06:00:00Z',periods:[{...c,from:snapshotAt,to:'2026-09-13T06:00:00Z',change:'BASE',becomingAt:null,probability:null}]};
const station = {observation:null,tafs:[f]};

test('ceiling / visibility categories respect NOAA boundaries and the more restrictive value', () => {
  for (const [height,category] of [[499,'LIFR'],[500,'IFR'],[999,'IFR'],[1000,'MVFR'],[3000,'MVFR'],[3001,'VFR']]) {
    assert.equal(flightCategory({...c,clouds:[{cover:'BKN',baseFt:height,type:null}]}),category);
  }
  for (const [visibilityMi,category] of [['0.5','LIFR'],['1','IFR'],['2.9','IFR'],['3','MVFR'],['5','MVFR'],['5+','VFR'],['6+','VFR'],['0.25-','LIFR']]) {
    assert.equal(flightCategory({...c,visibilityMi}),category);
  }
  assert.equal(flightCategory({...c,visibilityMi:'10',verticalVisibilityFt:400}),'LIFR');
});

test('missing fields, unknown cloud heights and ambiguous censoring never become VFR', () => {
  for (const value of [{...c,visibilityMi:null},{...c,clouds:[]},{...c,clouds:[{cover:'OVC',baseFt:null}]},
    {...c,visibilityMi:'3+'},{...c,visibilityMi:'6-'},{...c,visibilityMi:'garbage'}]) assert.equal(flightCategory(value),'unknown');
  assert.equal(flightCategory({...c,clouds:[{cover:'CLR',baseFt:null}]}),'VFR');
});

test('all horizons return a useful status without requiring an airline model', () => {
  for (const h of [6,12,24]) {
    const r = privateWeather(station,now+h*3600000,snapshotAt,now);
    assert.equal(r.status,h===24?'outside-coverage':'available');
    assert.equal(privateWeather(undefined,now+h*3600000,snapshotAt,now).status,'no-forecast');
  }
  const r=privateWeather(station,now+26*3600000,snapshotAt,now);
  assert.match(r.detail,/Latest forecast ends 13 Sept, 06:00 UTC/);
});

test('current observations do not fill future gaps; old snapshots and downloads fail closed', () => {
  assert.equal(privateWeather({observation:{...c},tafs:[]},now+6*3600000,snapshotAt,now).status,'no-forecast');
  assert.equal(privateWeather(station,now+6*3600000,snapshotAt,now+91*60000).status,'stale');
  assert.equal(privateWeather(station,now+6*3600000,snapshotAt,now,true).status,'unavailable');
  assert.equal(privateWeather(station,now+6*3600000,'invalid',now).status,'stale');
});

test('a shorter amendment supersedes an older longer forecast and future reports stay unavailable', () => {
  const shorter={...f,issuedAt:'2026-09-12T05:50:00Z',firstSeenAt:'2026-09-12T05:55:00Z',validTo:'2026-09-12T12:00:00Z'};
  assert.equal(privateWeather({...station,tafs:[f,shorter]},now+12*3600000,snapshotAt,now).status,'outside-coverage');
  assert.equal(privateWeather({...station,tafs:[{...f,firstSeenAt:'2026-09-12T06:01:00Z'}]},now+6*3600000,snapshotAt,now).status,'no-forecast');
});

test('temporary and probability categories stay separate from prevailing conditions', () => {
  const tempo={...f.periods[0],change:'TEMPO',visibilityMi:'0.5',clouds:[]};
  const prob={...f.periods[0],change:'PROB',probability:30,visibilityMi:null,clouds:[{cover:'BKN',baseFt:700,type:null}]};
  const r=privateWeather({...station,tafs:[{...f,periods:[...f.periods,tempo,prob]}]},now+6*3600000,snapshotAt,now);
  assert.equal(r.category,'VFR');
  assert.deepEqual(r.conditional,[{category:'LIFR',label:'Temporary'},{category:'IFR',label:'30% weather group'}]);
  assert.equal(privateWeather({...station,tafs:[{...f,periods:[{...f.periods[0],change:'BECMG'}]}]},now+6*3600000,snapshotAt,now).status,'partial');
});

test('private airport horizons use now; airline windows stay aligned to their model snapshot', () => {
  for (const h of [6,12,24]) {
    const modelTime=now+h*3600000-25*60000;
    assert.equal(lookaheadTime(h,'airline',now,modelTime),modelTime);
    assert.equal(lookaheadTime(h,'private',now,modelTime),now+h*3600000);
  }
});

test('every bundled U.S. airport handles all three private horizons independently of airline coverage', () => {
  const read = name => JSON.parse(readFileSync(new URL(`../public/data/airport-weather/${name}`,import.meta.url),'utf8'));
  const catalog=read('airports.json').airports; const snapshot=read('latest.json');
  const asOf=Date.parse(snapshot.generatedAt); const buckets=new Map(); const statuses={};
  for (const airport of catalog) {
    const prefix=airport.icao.slice(0,2);
    if (!buckets.has(prefix)) buckets.set(prefix,read(`stations/${prefix}.json`).stations);
    for (const h of [6,12,24]) {
      const summary=privateWeather(buckets.get(prefix)[airport.icao],asOf+h*3600000,snapshot.generatedAt,asOf);
      assert.ok(['available','partial','no-forecast','outside-coverage'].includes(summary.status),`${airport.icao} +${h}h: ${summary.status}`);
      assert.ok(summary.detail.length>0);
      if (summary.status!=='available') assert.equal(summary.category,'unknown');
      statuses[summary.status]=(statuses[summary.status]||0)+1;
    }
  }
  assert.ok(catalog.length>=900);
  assert.ok(statuses.available>0 && statuses['no-forecast']>0 && statuses['outside-coverage']>0);
});
