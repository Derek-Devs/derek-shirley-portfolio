"""Validate and promote a completed candidate to this local static site; no network/deployment."""
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from airport_weather import ROOT,PUBLIC,STATE,atomic_json,read_json,publish
from airport_models import predict_batch
from airport_predict import predict,score


def validate(model,evaluation):
    encoded=json.dumps(model,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    if hashlib.sha256(encoded).hexdigest()!=evaluation['modelSha256']: raise ValueError('Model hash mismatch')
    if model['version']!=evaluation['version'] or model['generatedAt']!=evaluation['generatedAt']: raise ValueError('Version mismatch')
    if len(model['protocol']['airports'])!=25 or len(evaluation['airports'])!=25: raise ValueError('Incomplete coverage')
    if model['selection']['testReadDuringSelection']: raise ValueError('Test leaked into selection')
    if len(model['selection']['results'])!=36: raise ValueError('Incomplete development experiment')
    if len({(r['fold'],r['direction'],r['horizon'],r['candidate']) for r in model['selection']['results']})!=36: raise ValueError('Duplicate development slices')
    rng=np.random.default_rng(48)
    for key,entry in model['models'].items():
        for name in ('weather','baseline'):
            fitted=entry[name]; means=np.array(fitted['mean']); scales=np.array(fitted['scale'])
            x=means+rng.normal(size=(100,len(means)))*scales
            batch=predict_batch(fitted,x)
            for i,row in enumerate(x):
                one=predict(fitted,row)
                if abs(sum(one[k] for k in ('delayed','cancelled','diverted','onTime'))-1)>1e-10: raise ValueError('Outcome sum mismatch')
                if any(not math.isfinite(v) or not 0<=v<=1 for v in one.values()): raise ValueError('Invalid probability')
                if any(abs(one[k]-batch[k][i])>1e-10 for k in one): raise ValueError('Serving/batch mismatch')
    for collection in ('airports','stressAirports'):
        for airport in evaluation[collection].values():
            for horizons in airport['directions'].values():
                if len({r['flights'] for r in horizons.values()})!=1 or len({r['windows'] for r in horizons.values()})!=1: raise ValueError('Horizon cohorts differ')
                for r in horizons.values():
                    if sum(b['flights'] for b in r['calibration'])!=r['flights']: raise ValueError('Calibration denominator mismatch')
                    if not 0<=r['qValueApproximate']<=1 or r['qValueApproximate']<r['pValueApproximate']-1e-12: raise ValueError('Invalid multiplicity correction')
    return {'portableParityVectors':1200,'airports':25,'testSlices':150,'stressSlices':150}


if __name__=='__main__':
    source=ROOT/'.airport-data/model-v2/candidate'
    model=read_json(source/'model.json',None); evaluation=read_json(source/'evaluation.json',None)
    if not model or not evaluation: raise SystemExit('Complete selection and evaluation first')
    checks=validate(model,evaluation)
    audit_path=ROOT/'.airport-data/model-v2/experiment-source.json'
    audit=read_json(audit_path,None)
    if audit:
        for name,digest in audit['files'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest: raise ValueError(f'Experiment code changed after the source audit: {name}')
    latest=read_json(STATE/'latest.json',None)
    if not latest: raise ValueError('Collect weather before promotion')
    score(latest,model,evaluation)  # Verify the actual snapshot before changing the current model.
    version=PUBLIC/'versions/v2'
    if version.exists(): raise ValueError('v2 is already archived; do not overwrite an experiment')
    atomic_json(version/'model.json',model); atomic_json(version/'evaluation.json',evaluation)
    atomic_json(version/'validation.json',checks)
    if audit: atomic_json(version/'experiment-source.json',audit)
    atomic_json(PUBLIC/'model.json',model); atomic_json(PUBLIC/'evaluation.json',evaluation)
    publish(latest)
    print(json.dumps({'promotedLocally':model['version'],**checks}),flush=True)
