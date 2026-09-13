import test from 'node:test';
import assert from 'node:assert/strict';
import { forecastAt, periodsAt, ceilingLabel, groupLabel, windLabel, escapeHtml, findAirport, isUsAirport } from '../src/lib/airport-weather.ts';

test('U.S. scope accepts Alaska, Hawaii and territories but rejects foreign and unknown countries', () => {
  for (const country of ['US', 'PR', 'VI', 'GU', 'MP', 'AS']) assert.equal(isUsAirport({country}), true);
  for (const country of ['CA', 'GB', 'BR', '', undefined]) assert.equal(isUsAirport({country}), false);
});

const conditions = {windDirection: null, windKt: null, gustKt: null, visibilityMi: null,
  weather: null, clouds: [], verticalVisibilityFt: null};
const old = {id: 'old', issuedAt: '2025-05-01T00:00:00Z', firstSeenAt: '2025-05-01T00:10:00Z',
  validFrom: '2025-05-01T00:00:00Z', validTo: '2025-05-02T06:00:00Z', periods: [], raw: ''};
test('a later amendment cannot leak into an earlier as-of prediction', () => {
  const amendment = {...old, id:'amendment', issuedAt:'2025-05-01T05:00:00Z', firstSeenAt:'2025-05-01T05:08:00Z'};
  const station = {observation:null, tafs:[old, amendment]};
  assert.equal(forecastAt(station, Date.parse('2025-05-01T12:00:00Z'), Date.parse('2025-05-01T05:05:00Z')).id, 'old');
  assert.equal(forecastAt(station, Date.parse('2025-05-01T12:00:00Z'), Date.parse('2025-05-01T05:10:00Z')).id, 'amendment');
});
test('forecast coverage ends at the exclusive end, with no invented extension', () => {
  assert.equal(forecastAt({tafs:[old]}, Date.parse(old.validTo), Date.parse(old.firstSeenAt)), undefined);
  assert.equal(periodsAt({periods:[{from:old.validFrom,to:old.validTo}]}, Date.parse(old.validTo)).length, 0);
});
test('an older forecast cannot fill a gap left by a superseding amendment', () => {
  const short = {...old, id:'short', issuedAt:'2025-05-01T05:00:00Z', firstSeenAt:'2025-05-01T05:08:00Z',validTo:'2025-05-01T12:00:00Z'};
  assert.equal(forecastAt({tafs:[old,short]}, Date.parse('2025-05-01T18:00:00Z'), Date.parse('2025-05-01T06:00:00Z')), undefined);
});
test('missing winds and ceiling are not converted into calm or clear conditions', () => {
  assert.equal(windLabel(conditions), 'Not reported');
  assert.equal(ceilingLabel(conditions), 'Not reported');
  assert.equal(windLabel({...conditions, windKt:0}), 'Calm');
  assert.equal(windLabel({...conditions, windKt:4,windDirection:'VRB'}), 'Variable 4 kt');
});
test('ceiling uses the lowest broken/overcast/vertical layer, not scattered clouds', () => {
  const c = {...conditions, clouds:[{cover:'SCT',baseFt:400},{cover:'BKN',baseFt:1900},{cover:'OVC',baseFt:4000}]};
  assert.equal(ceilingLabel(c), '1,900 ft AGL');
});
test('conditional groups retain their weather probability and temporary qualifier', () => {
  assert.equal(groupLabel({change:'PROB TEMPO',probability:30}), '30% weather group · temporary');
  assert.equal(groupLabel({change:'BECMG',probability:null}), 'Transition');
});
test('airport lookup accepts case-insensitive IATA and ICAO and does not guess unknown codes', () => {
  const airports = [{icao:'KDFW',iata:'DFW',name:'Dallas Fort Worth International Airport'}];
  assert.equal(findAirport(airports,'dfw').icao,'KDFW');
  assert.equal(findAirport(airports,'KDFW').iata,'DFW');
  assert.equal(findAirport(airports,'ZZZZ'),undefined);
});

test('an empty route field never selects an airport with no IATA code', () => {
  const airports=[{icao:'KAWO',iata:'',name:'Arlington Municipal Airport'}];
  assert.equal(findAirport(airports,''),undefined);
  assert.equal(findAirport(airports,'   '),undefined);
  assert.equal(findAirport(airports,'KAWO').icao,'KAWO');
});
test('external report text is escaped before HTML rendering', () => {
  assert.equal(escapeHtml('<img src=x onerror="alert(1)">'), '&lt;img src=x onerror=&quot;alert(1)&quot;&gt;');
});
