"""Frozen six-airport mixed-input ablation. Local research, no model promotion."""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from sklearn.preprocessing import StandardScaler
import airport_train_v2 as train
from airport_train_v3 import support_reason
from airport_features import features, feature_names
from airport_models import logit_many, predict_batch, serializable
from airport_operations_history import SPEC, SPEC_PATH, OUT, PERIODS
from airport_weather import ROOT, PUBLIC, atomic_json, stamp

BASE=json.loads((ROOT/'research/airport-protocol-v3.json').read_text())
P={**BASE,**{k:SPEC[k] for k in PERIODS},'airports':{a:BASE['airports'][a] for a in SPEC['airports']}}
VARIANTS=SPEC['variants']
COMPARISONS={'runwayVsWeather':('weatherRunway','weather'), 'faaVsWeather':('weatherFaa','weather'),
    'combinedVsWeather':('weatherRunwayFaa','weather'), 'runwayVsDirection':('weatherRunway','weatherDirection')}
PROTECTED=('model.json','evaluation.json')


def hashes():
    return {name:hashlib.sha256((PUBLIC/name).read_bytes()).hexdigest() for name in PROTECTED}


def names(airport,variant):
    result=feature_names({airport:P['airports'][airport]},variant!='calendar')
    if variant in ('weatherDirection','weatherRunway','weatherRunwayFaa'): result+=SPEC['directionFeatures']
    if variant in ('weatherRunway','weatherRunwayFaa'): result+=SPEC['runwayFeatures']
    if variant in ('weatherFaa','weatherRunwayFaa'): result+=SPEC['faaFeatures']
    return result


def matrix(rows,airport,horizon,variant,delayed=False):
    result=[]; zone={airport:P['airports'][airport]}
    for row in rows:
        wx=row['weather'][str(horizon)]; ops=row['operations'][str(horizon)]
        values=features(airport,row['start'],wx,zone,variant!='calendar')
        if variant in ('weatherDirection','weatherRunway','weatherRunwayFaa'): values+=ops['direction']
        if variant in ('weatherRunway','weatherRunwayFaa'): values+=ops['runway']
        if variant in ('weatherFaa','weatherRunwayFaa'): values+=ops['faaDelayed' if delayed else 'faa']
        result.append(values)
    x=np.array(result)
    if x.shape!=(len(rows),len(names(airport,variant))) or not np.isfinite(x).all(): raise ValueError('Invalid research matrix')
    return x


def fit_variant(rows,calibration,airport,direction,horizon,variant):
    x=matrix(rows,airport,horizon,variant); xc=matrix(calibration,airport,horizon,variant)
    scaler=StandardScaler().fit(x,sample_weight=train.original.counts(rows)['n'])
    xs=scaler.transform(x); xcs=scaler.transform(xc); heads={}
    tc=train.original.targets(calibration,direction)
    for name,(success,total) in train.original.targets(rows,direction).items():
        head=train.fit_head(xs,success,total,'linear')
        calx=np.column_stack((logit_many(head,xcs),xc[:,:1]))
        head['calibration']={**train.fit_head(calx,*tc[name],'linear',calibration=True),'airportCount':1}
        heads[name]=head
    return {'kind':'linear','mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'heads':heads,'features':names(airport,variant)}


def paired_blocks(rows,predictions):
    n=np.array([r['n'] for r in rows]); y=np.array([r['cancelled']+r['diverted']+r['delayed'] for r in rows])
    losses=np.column_stack([train.original.brier(predictions[v]['disruption'],y,n)*n for v in VARIANTS]+[n])
    blocks=defaultdict(lambda:np.zeros(len(VARIANTS)+1))
    for i,row in enumerate(rows): blocks[str(row['block'])]+=losses[i]
    return {k:v.tolist() for k,v in blocks.items()}


def fit_airport(airport,manifest):
    started=time.perf_counter(); train.P={**P,'airports':{airport:P['airports'][airport]}}
    path=OUT/'prepared'/(airport+'.json.gz')
    entry=next(a for a in manifest['prepared'] if a['airport']==airport)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']: raise ValueError('Prepared data changed')
    rows=json.loads(gzip.decompress(path.read_bytes()))
    if any(r['airport']!=airport for r in rows): raise ValueError('Cross-airport label leakage')
    result={'airport':airport,'coverage':{},'test':{},'previouslySeenStressTest':{}}; saved={}
    for direction in ('departures','arrivals'):
        for h in SPEC['horizons']:
            key=f'{direction}_{h}'
            eligible=[r for r in rows if r['direction']==direction and str(h) in r['operations']]
            s=train.split(eligible,P); reason=support_reason(s,P)
            result['coverage'][key]={'reason':reason,'windows':{k:len(v) for k,v in s.items()},
                'flightEvents':{k:sum(r['n'] for r in v) for k,v in s.items()}}
            if reason: continue
            models={v:fit_variant(s['train'],s['probabilityCalibration'],airport,direction,h,v) for v in VARIANTS}
            bands={v:train.calibrate_band(s['intervalCalibration'],predict_batch(models[v],matrix(s['intervalCalibration'],airport,h,v))) for v in VARIANTS}
            saved[key]={'variants':models,'bands':bands}
            for period in ('test','previouslySeenStressTest'):
                test=s[period]
                if len(test)<P['minimumTestWindows']: continue
                predictions={v:predict_batch(models[v],matrix(test,airport,h,v)) for v in VARIANTS}
                for pred in predictions.values():
                    if not np.allclose(pred['onTime']+pred['cancelled']+pred['diverted']+pred['delayed'],1): raise ValueError('Outcome probability sum')
                train.metrics.horizon=h
                reports={v:train.metrics(test,predictions[v],predictions['calendar' if v in ('calendar','weather') else 'weather'],bands[v]) for v in VARIANTS}
                comparisons={name:train.metrics(test,predictions[v],predictions[baseline],bands[v]) for name,(v,baseline) in COMPARISONS.items()}
                sensitivity={}; delayed_rows=[r for r in test if r['operations'][str(h)]['faaDelayed'] is not None]
                if delayed_rows:
                    for v in ('weatherFaa','weatherRunwayFaa'):
                        normal=predict_batch(models[v],matrix(delayed_rows,airport,h,v))
                        late=predict_batch(models[v],matrix(delayed_rows,airport,h,v,True))
                        sensitivity[v]={'windows':len(delayed_rows),'coverage':len(delayed_rows)/len(test),
                            'normalBrierSameWindows':train.brier_summary(delayed_rows,normal),'extraHourLagBrier':train.brier_summary(delayed_rows,late)}
                result[period][key]={'variants':reports,'comparisons':comparisons,'pairedBlocks':paired_blocks(test,predictions),
                    'deliverySensitivity':sensitivity,'windowsWithRecentFaaActivity':sum(any(r['operations'][str(h)]['faa']) for r in test)}
    result['seconds']=round(time.perf_counter()-started,3)
    atomic_json(OUT/'fitted'/(airport+'-models.json'),saved)
    return result


def aggregate(results,period,direction,horizon):
    key=f'{direction}_{horizon}'; blocks=defaultdict(lambda:np.zeros(len(VARIANTS)+1)); airports=0
    for result in results.values():
        value=result[period].get(key)
        if not value: continue
        airports+=1
        for day,values in value['pairedBlocks'].items(): blocks[day]+=values
    if not blocks: return None
    values=np.array([blocks[k] for k in sorted(blocks)]); total=values.sum(axis=0)
    rng=np.random.default_rng(P['seed']); draws=values[rng.integers(0,len(values),size=(P['bootstrapDayResamples'],len(values)))].sum(axis=1)
    comparisons={}
    for name,(v,baseline) in COMPARISONS.items():
        i=VARIANTS.index(v); j=VARIANTS.index(baseline); skill=1-draws[:,i]/draws[:,j]
        comparisons[name]={'brierSkill':1-total[i]/total[j],'skillInterval95':np.quantile(skill,[.025,.975]).tolist()}
    return {'airports':airports,'flightEvents':int(total[-1]),'sharedCalendarBlocks':len(blocks),
        'brier':{v:total[i]/total[-1] for i,v in enumerate(VARIANTS)},'comparisons':comparisons}


def main():
    started=time.perf_counter(); manifest=json.loads((OUT/'features-manifest.json').read_text())
    protocol_hash=hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()
    if manifest['protocolSha256']!=protocol_hash: raise ValueError('Feature protocol mismatch')
    paths=[Path(__file__),ROOT/'tools/airport_operations_pilot_features.py',ROOT/'tools/airport_operations_history.py',
        ROOT/'tools/airport_train_v2.py',ROOT/'tools/airport_train_v3.py',ROOT/'tools/airport_train.py',ROOT/'tools/airport_features.py',ROOT/'tools/airport_models.py',
        ROOT/'research/airport-protocol-v3.json']
    code={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    for name,digest in manifest['code'].items():
        if code.get(name)!=digest: raise ValueError('Feature code changed after preparation')
    inputs={'protocolSha256':protocol_hash,'featureManifestSha256':hashlib.sha256((OUT/'features-manifest.json').read_bytes()).hexdigest(),
        'code':code,'protectedFiles':hashes()}
    lock=OUT/'fit-inputs.json'
    if lock.exists() and json.loads(lock.read_text())!=inputs: raise ValueError('Frozen fit inputs differ; start a new experiment version')
    atomic_json(lock,inputs)
    (OUT/'fitted').mkdir(exist_ok=True); results={}
    for airport in SPEC['airports']:
        path=OUT/'fitted'/(airport+'.json')
        if path.exists(): result=json.loads(path.read_text())
        else:
            result=fit_airport(airport,manifest); atomic_json(path,result)
            print(json.dumps({'airport':airport,'slices':len(result['test']),'seconds':result['seconds']}),flush=True)
        results[airport]=result
    train.P=P; summary={}
    for period in ('test','previouslySeenStressTest'):
        slices=[s for a in results.values() for s in a[period].values()]
        corrected=[c for s in slices for c in s['comparisons'].values()]
        train.adjust_evidence(corrected)
        summary[period]={'slices':len(slices),'testedAirports':sum(bool(a[period]) for a in results.values()),
            'comparisons':{name:{'positiveSlices':sum(s['comparisons'][name]['brierSkill']>0 for s in slices),
                'positiveAdjustedSlices':sum(s['comparisons'][name]['skillInterval95'][0]>0 and s['comparisons'][name]['qValueApproximate']<=P['falseDiscoveryRate'] for s in slices),
                'moderateEvidenceSlices':sum(s['comparisons'][name]['evidence']=='moderate' for s in slices)} for name in COMPARISONS},
            'meanMetrics':{v:{k:float(np.mean([s['variants'][v][k] for s in slices])) for k in ('brier','logLoss','calibrationError','mae','bandCoverage','bandMeanWidth','intervalScore')} for v in VARIANTS},
            'byDirectionHorizon':{f'{d}_{h}':aggregate(results,period,d,h) for d in ('departures','arrivals') for h in SPEC['horizons']}}
    if hashes()!=inputs['protectedFiles']: raise ValueError('Production files changed during local experiment')
    report={'version':SPEC['version'],'generatedAt':stamp(),'protocol':SPEC,'inputs':inputs,'features':manifest,
        'seconds':round(time.perf_counter()-started,3),'airports':results,'summary':summary,
        'decision':'Research only. No production promotion; prospective validation and live feature parity are required.',
        'validation':{'sameWindowsAllVariants':True,'productionUnchanged':True,'privateJetProbabilitiesValidated':False}}
    atomic_json(OUT/'report.json',serializable(report))
    print(json.dumps({'status':'complete','seconds':report['seconds'],'summary':summary}),flush=True)


if __name__=='__main__': main()
