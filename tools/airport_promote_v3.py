"""Validate the expanded artifact and archive it before switching the local site."""
from copy import deepcopy
import hashlib
import json
import math
import time
import numpy as np
from airport_weather import ROOT,PUBLIC,STATE,atomic_json,read_json,publish
from airport_models import predict_batch
from airport_predict import predict,score


def validate(model,evidence):
    raw=json.dumps(model,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    if hashlib.sha256(raw).hexdigest()!=evidence['modelSha256']: raise ValueError('Model digest differs')
    if model['version']!=evidence['version'] or model['generatedAt']!=evidence['generatedAt']: raise ValueError('Mismatched artifacts')
    catalog=read_json(PUBLIC/'airports.json',None)
    target={a['iata'] for a in catalog['airports'] if a['size']=='large_airport'}
    if target!=set(model['protocol']['airports']) or target!=set(evidence['coverage']) or target!=set(evidence['airports']):
        raise ValueError('Coverage does not match all major U.S. catalog airports')
    old=read_json(PUBLIC/'versions/v2/model.json',None)
    for key,entry in model['models'].items():
        copy=deepcopy(entry); zones=copy.pop('featureAirports')
        if zones!=old['protocol']['airports'] or copy!=old['models'][key]: raise ValueError('Incumbent weights changed')
    rng=np.random.default_rng(183); probes=0; slices=0
    for airport,entries in model['airportModels'].items():
        for key,entry in entries.items():
            if set(entry['featureAirports'])!={airport}: raise ValueError('Local model is using other airport features')
            direction,horizon=key.split('_')
            if horizon not in ('6','12','24') or direction not in ('departures','arrivals'): raise ValueError('Unknown model slice')
            if horizon not in evidence['airports'][airport]['directions'].get(direction,{}): raise ValueError('Untested model cannot be served')
            for name in ('weather','baseline'):
                fitted=entry[name]; means=np.array(fitted['mean']); scales=np.array(fitted['scale'])
                x=means+rng.normal(size=(32,len(means)))*scales
                batch=predict_batch(fitted,x)
                for i,vector in enumerate(x):
                    single=predict(fitted,vector)
                    if any(not math.isfinite(v) or not 0<=v<=1 for v in single.values()): raise ValueError('Invalid probability')
                    if abs(sum(single[k] for k in ('cancelled','diverted','delayed','onTime'))-1)>1e-10: raise ValueError('Outcome total differs')
                    if any(abs(single[k]-batch[k][i])>1e-10 for k in single): raise ValueError('Portable prediction parity differs')
                    probes+=1
            slices+=1
    for collection in ('airports','stressAirports'):
        reports=[r for a in evidence[collection].values() for d in a['directions'].values() for r in d.values()]
        for report in reports:
            if sum(b['flights'] for b in report['calibration'])!=report['flights']: raise ValueError('Calibration denominator differs')
            if report['multipleTestingComparisons']!=len(reports): raise ValueError('Multiple-testing family differs')
            if not 0<=report['pValueApproximate']<=report['qValueApproximate']<=1: raise ValueError('Invalid adjusted significance')
        for airport in evidence[collection].values():
            for horizons in airport['directions'].values():
                matched=[r['matchedHorizon'] for r in horizons.values() if 'matchedHorizon' in r]
                if len({(m['windows'],m['flights']) for m in matched})>1: raise ValueError('Matched horizon cohorts differ')
    return {'targetAirports':len(target),'newModelSlices':slices,'portableParityVectors':probes,'modelBytes':len(raw)}


def main():
    source=ROOT/'.airport-data/model-v3/candidate'
    model=read_json(source/'model.json',None); evidence=read_json(source/'evaluation.json',None)
    checks=validate(model,evidence)
    latest=read_json(STATE/'latest.json',None)
    start=time.perf_counter(); risk=score(latest,model,evidence)
    checks['snapshotScoringSeconds']=round(time.perf_counter()-start,4)
    checks['scoredAirportEntries']=len(risk['airports'])
    audit=read_json(ROOT/'.airport-data/model-v3/experiment-source.json',None)
    if not audit: raise ValueError('Record the frozen experiment source hashes before promotion')
    for path,digest in audit['files'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest: raise ValueError('Experiment source changed: '+path)
    version=PUBLIC/'versions/v3'
    if version.exists(): raise ValueError('Do not overwrite an archived experiment')
    for name,value in [('model',model),('evaluation',evidence),('validation',checks),('experiment-source',audit)]: atomic_json(version/(name+'.json'),value)
    atomic_json(PUBLIC/'model.json',model); atomic_json(PUBLIC/'evaluation.json',evidence)
    publish(latest)
    print(json.dumps({'promoted':model['version'],**checks}),flush=True)


if __name__=='__main__': main()
