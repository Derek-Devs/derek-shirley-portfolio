import test from 'node:test';
import assert from 'node:assert/strict';
import { faaState, operationsPanel } from '../src/lib/airport-operations.ts';

const now = Date.parse('2026-09-12T18:20:00Z');
const source = {status:'ok',fetchedAt:'2026-09-12T18:10:00Z',issuedAt:'2026-09-12T18:02:00Z'};
const airport = {icao:'KLAX',iata:'LAX'};
const station = {faa:{events:[],identifierAvailable:true}};

test('absence of a notice requires fresh source and known identifier; errors never mean all clear', () => {
  assert.equal(faaState(station,source,now),'none-reported');
  assert.equal(faaState(undefined,source,now),'unavailable');
  assert.equal(faaState(station,undefined,now),'unavailable');
  assert.equal(faaState({faa:{events:[],identifierAvailable:false}},source,now),'unmapped');
  for (const change of [{status:'error'},{status:'deferred'},{issuedAt:'garbage'},
    {issuedAt:'2026-09-12T15:00:00Z'},{fetchedAt:'2026-09-12T15:00:00Z'},
    {issuedAt:'2026-09-12T21:00:00Z'}]) assert.equal(faaState(station,{...source,...change},now),'stale');
});

test('closure exceptions remain visible, are escaped, and are not turned into a flight prediction', () => {
  const value = {...station,faa:{...station.faa,events:[{id:'1',type:'closure',reason:'CLSD TO GA EXC PPR <script>bad</script>',details:[]} ]}};
  const html = operationsPanel(airport,value,{faa:source},now);
  assert.match(html,/Closure \/ access restriction/);
  assert.match(html,/CLSD TO GA EXC PPR &lt;script&gt;/);
  assert.doesNotMatch(html,/<script>/);
  assert.match(html,/not forecast for your selected flight time/);
  assert.match(html,/not included in the delay probabilities/);
  assert.match(html,/does not automatically mean the entire airport is closed/);
  const old = operationsPanel(airport,value,{faa:{...source,status:'error'}},now);
  assert.match(old,/current status is unknown/);
});

test('runway counts represent physical records with known status, not runway ends or capacity', () => {
  const runway = {id:'1',ends:['09','27'],lengthFt:10000,widthFt:150,surface:'CON',closed:false,lighted:true,headingsTrue:[90,270]};
  const html = operationsPanel(airport,{...station,runways:{sourceIdent:'KLAX',runways:[runway,{...runway,id:'2',closed:true,lengthFt:20000},{...runway,id:'3',closed:null,lengthFt:null}] }},{faa:source,runways:source},now);
  assert.match(html, /Listed open runways<\/dt><dd>1/);
  assert.match(html, /Longest listed open runway<\/dt><dd>10,000 ft/);
  assert.match(html, /status is missing for 1 additional record/);
  assert.match(html, /not the runways currently in use/);
  assert.match(html, /90°T \/ 270°T/);
});

test('older snapshots and absent runway records show unavailable rather than zero', () => {
  const html = operationsPanel(airport,undefined,{},now);
  assert.match(html,/FAA status unavailable/);
  assert.match(html,/No matching runway inventory available/);
  assert.doesNotMatch(html,/Listed open runways<\/dt><dd>0/);
});
