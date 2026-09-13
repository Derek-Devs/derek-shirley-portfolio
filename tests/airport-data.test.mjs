import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeDataBase, generationPath, setAirportGeneration, airportDataUrl } from '../src/lib/airport-data.ts';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

test('local snapshots remain the default and cloud endpoint cannot contain credentials', () => {
  assert.equal(normalizeDataBase(), '/data/airport-weather');
  assert.equal(normalizeDataBase('https://d123abc.cloudfront.net'), 'https://d123abc.cloudfront.net');
  for (const value of ['http://d123.cloudfront.net', 'https://user:pass@d123.cloudfront.net', 'https://evil.test', 'https://d123.cloudfront.net/?x=1']) {
    assert.throws(() => normalizeDataBase(value));
  }
});

test('snapshot generation cannot redirect or traverse and shared catalog keeps its stable path', () => {
  for (const value of ['../active', 'https://example.org', 'snapshots/../model']) assert.throws(() => generationPath(value));
  setAirportGeneration('snapshots/20260911T200000Z');
  assert.equal(airportDataUrl('risk.json'), '/data/airport-weather/snapshots/20260911T200000Z/risk.json');
  assert.equal(airportDataUrl('airports.json', true), '/data/airport-weather/airports.json');
  setAirportGeneration();
  assert.equal(airportDataUrl('risk.json'), '/data/airport-weather/risk.json');
});

test('CloudFront rejects arbitrary origin misses, invalid dates and unknown station buckets', () => {
  const template = JSON.parse(readFileSync(new URL('../infra/aws/cloudformation.json', import.meta.url), 'utf8'));
  const source = template.Resources.PathGuard.Properties.FunctionCode;
  const fixed = Date.parse('2026-09-11T20:15:00Z');
  class Clock extends Date { static now() { return fixed; } }
  const handler = runInNewContext(source + ';handler', { Date: Clock });
  for (const uri of ['/latest.json', '/airports.json', '/snapshots/20260911T200000Z/stations/KD.json', '/snapshots/20260911T200000Z/operations/risk.json', '/snapshots/20260911T200000Z/operations/evaluation.json']) {
    assert.equal(handler({request:{uri}}).uri, uri);
  }
  for (const uri of ['/active/model.json', '/random', '/snapshots/20260911T200001Z/risk.json', '/snapshots/20260111T200000Z/risk.json', '/snapshots/20269911T200000Z/risk.json', '/snapshots/20260911T200000Z/stations/00.json', '/snapshots/20260911T200000Z/operations/model.json', '/snapshots/20260911T200000Z/operations/anything.json']) {
    assert.equal(handler({request:{uri}}).statusCode, 404);
  }
});
