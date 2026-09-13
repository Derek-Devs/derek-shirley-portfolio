"""Nationwide airport-local FAA + weather experiment and portable candidate export."""
from __future__ import annotations
import os
os.environ['OMP_NUM_THREADS']='2'
os.environ['OPENBLAS_NUM_THREADS']='2'
from collections import Counter,defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from sklearn.preprocessing import StandardScaler
import airport_train_v2 as train
from airport_train_v3 import load_airport,support_reason
from airport_features import features as weather_vector,feature_names
from airport_models import logit_many,predict_batch
from airport_faa_history import parse_listing,build_index,features as faa_vector,FEATURE_NAMES,FEATURE_VERSION
from airport_weather import ROOT,PUBLIC,atomic_json,stamp

SPEC_PATH=ROOT/'research/airport-operations-us-v1.json'
SPEC=json.loads(SPEC_PATH.read_text())
BASE=json.loads((ROOT/'research/airport-protocol-v3.json').read_text())
PERIODS=('train','probabilityCalibration','intervalCalibration','test','previouslySeenStressTest')
P={**BASE,**{k:SPEC[k] for k in PERIODS},'selection':SPEC['learner']}
OUT=ROOT/'.airport-data/operations-us-v1'
PILOT=ROOT/'.airport-data/operations-pilot-v1'
VARIANTS=SPEC['variants']


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def history():
    prior=json.loads((PILOT/'faa-history.json').read_text()); days=[]
    for day in prior['days']:
        path=PILOT/'faa-history'/(day['date']+'.html')
        if digest(path)!=day['sha256']: raise ValueError('Cached FAA source changed')
        parsed=parse_listing(path.read_bytes(),day['date'],P['airports'])
        if parsed['totalAdvisories']!=day['totalAdvisories']: raise ValueError('Archive parser coverage changed')
        days.append(parsed)
    if len(days)!=903 or len(prior['missingDays'])!=30: raise ValueError('Frozen national archive coverage changed')
    return days,prior['missingDays']


def attach(rows,days,index):
    kept=[]; audit=Counter(); coverage={d['date'] for d in days}
    for row in rows:
        if not any(SPEC[k][0]<=row['localDate']<=SPEC[k][1] for k in PERIODS): continue
        extra={}; audit['sourceWindows']+=1
        for h in SPEC['horizons']:
            if row['weather'].get(str(h)) is None: audit[f'{h}_weatherMissing']+=1; continue
            cutoff=row['start']-h*3600; f=faa_vector(row['airport'],cutoff,coverage,index)
            if f is None: audit[f'{h}_faaHistoryMissing']+=1; continue
            extra[str(h)]={'faa':f,'faaDelayed':faa_vector(row['airport'],cutoff,coverage,index,SPEC['sensitivityLagMinutes'])}
            audit[f'{h}_retained']+=1
        kept.append({**row,'operations':extra})
    return kept,dict(audit)


def matrix(rows,airport,h,variant,delayed=False):
    x=[]; zones={airport:P['airports'][airport]}
    for r in rows:
        values=weather_vector(airport,r['start'],r['weather'][str(h)],zones,variant!='calendar')
        if variant=='operations': values+=r['operations'][str(h)]['faaDelayed' if delayed else 'faa']
        x.append(values)
    result=np.array(x)
    if not np.isfinite(result).all(): raise ValueError('Invalid model input')
    return result


def fit_variant(rows,calibration,airport,direction,h,variant):
    x=matrix(rows,airport,h,variant); xc=matrix(calibration,airport,h,variant)
    scaler=StandardScaler().fit(x,sample_weight=train.original.counts(rows)['n'])
    xs=scaler.transform(x); xcs=scaler.transform(xc); heads={}; tc=train.original.targets(calibration,direction)
    for name,(success,total) in train.original.targets(rows,direction).items():
        head=train.fit_head(xs,success,total,'linear')
        calx=np.column_stack((logit_many(head,xcs),xc[:,:1]))
        head['calibration']={**train.fit_head(calx,*tc[name],'linear',calibration=True),'airportCount':1}; heads[name]=head
    return {'kind':'linear','mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'heads':heads,
        'features':feature_names({airport:P['airports'][airport]},variant!='calendar')+(FEATURE_NAMES if variant=='operations' else [])}


def paired(rows,predictions):
    n=np.array([r['n'] for r in rows]); y=np.array([r['cancelled']+r['diverted']+r['delayed'] for r in rows])
    losses=np.column_stack([train.original.brier(predictions[v]['disruption'],y,n)*n for v in VARIANTS]+[n])
    blocks=defaultdict(lambda:np.zeros(4))
    for i,r in enumerate(rows): blocks[str(r['block'])]+=losses[i]
    return {k:v.tolist() for k,v in blocks.items()}


def fit_airport(airport,days,index):
    started=time.perf_counter(); train.P={**P,'airports':{airport:P['airports'][airport]}}
    rows,audit=attach(load_airport(airport),days,index)
    result={'airport':airport,'audit':audit,'coverage':{'method':'airport-local-operations','directions':{}},'test':{},'previouslySeenStressTest':{}}
    entries={}
    for direction in ('departures','arrivals'):
        result['coverage']['directions'][direction]={}
        for h in SPEC['horizons']:
            key=f'{direction}_{h}'; eligible=[r for r in rows if r['direction']==direction and str(h) in r['operations']]
            s=train.split(eligible,P); reason=support_reason(s,P)
            cohorts={k:{'airportWindows':len(v),'flightEvents':sum(r['n'] for r in v)} for k,v in s.items()}
            info={'status':'insufficient-data' if reason else 'tested','reason':reason,'windows':{k:len(v) for k,v in s.items()}}
            result['coverage']['directions'][direction][str(h)]=info
            if reason: continue
            models={v:fit_variant(s['train'],s['probabilityCalibration'],airport,direction,h,v) for v in VARIANTS}
            bands={v:train.calibrate_band(s['intervalCalibration'],predict_batch(models[v],matrix(s['intervalCalibration'],airport,h,v))) for v in VARIANTS}
            wx=np.array([r['weather'][str(h)] for r in s['train']]); fx=np.array([r['operations'][str(h)]['faa'] for r in s['train']])
            activity=int(np.any(fx!=0,axis=1).sum()); info['trainingWindowsWithFaaActivity']=activity
            entries[key]={'weather':models['weather'],'operations':models['operations'],'baseline':models['calendar'],
                'intervals':{airport:bands['operations']},'weatherIntervals':{airport:bands['weather']},
                'weatherMin':wx.min(axis=0).tolist(),'weatherMax':wx.max(axis=0).tolist(),
                'faaMin':fx.min(axis=0).tolist(),'faaMax':fx.max(axis=0).tolist(),
                'clockSupport':train.original.clock_support(s['train'],train.P['airports'])[airport][direction],
                'featureAirports':train.P['airports'],'method':'airport-local-operations','trainingWindowsWithFaaActivity':activity}
            for period in ('test','previouslySeenStressTest'):
                part=s[period]
                if len(part)<P['minimumTestWindows']: continue
                predictions={v:predict_batch(models[v],matrix(part,airport,h,v)) for v in VARIANTS}; train.metrics.horizon=h
                metrics={v:train.metrics(part,predictions[v],predictions['weather' if v=='operations' else 'calendar'],bands[v]) for v in VARIANTS}
                for m in metrics.values(): m.update(method='airport-local-operations',cohorts=cohorts)
                m=metrics['operations']; m['trainingWindowsWithFaaActivity']=activity
                m['faaActivityWindows']=sum(any(r['operations'][str(h)]['faa']) for r in part)
                sensitivity=[r for r in part if r['operations'][str(h)]['faaDelayed'] is not None]
                if sensitivity:
                    normal=predict_batch(models['operations'],matrix(sensitivity,airport,h,'operations'))
                    late=predict_batch(models['operations'],matrix(sensitivity,airport,h,'operations',True))
                    m['faaDeliverySensitivity']={'lagMinutes':SPEC['sensitivityLagMinutes'],'coverage':len(sensitivity)/len(part),
                        'windows':len(sensitivity),'brier':train.brier_summary(sensitivity,late),'mainBrierSameWindows':train.brier_summary(sensitivity,normal)}
                m['weatherComparator']={k:metrics['weather'][k] for k in ('brier','calibrationError','bandCoverage','bandMeanWidth','logLoss','mae','intervalScore')}
                result[period][key]={'variants':metrics,'pairedBlocks':paired(part,predictions)}
    result['seconds']=round(time.perf_counter()-started,3)
    atomic_json(OUT/'fitted'/(airport+'-models.json'),entries)
    return result


def aggregate(results,period,key):
    blocks=defaultdict(lambda:np.zeros(4)); count=0
    for entry in results.values():
        trial=entry[period].get(key)
        if not trial: continue
        count+=1
        for day,values in trial['pairedBlocks'].items(): blocks[day]+=values
    if not blocks: return None
    values=np.array([blocks[k] for k in sorted(blocks)]); totals=values.sum(axis=0)
    rng=np.random.default_rng(P['seed']); draws=values[rng.integers(0,len(values),size=(P['bootstrapDayResamples'],len(values)))].sum(axis=1)
    return {'airports':count,'flightEvents':int(totals[3]),'blocks':len(blocks),
        'brier':{v:totals[i]/totals[3] for i,v in enumerate(VARIANTS)},'brierSkill':1-totals[2]/totals[1],
        'skillInterval95':np.quantile(1-draws[:,2]/draws[:,1],[.025,.975]).tolist()}


def main():
    started=time.perf_counter(); OUT.mkdir(exist_ok=True); (OUT/'fitted').mkdir(exist_ok=True)
    if len(P['airports'])!=SPEC['budget']['maximumAirports']: raise ValueError('Airport scope changed')
    days,missing=history(); index=build_index(days,P['airports'])
    atomic_json(OUT/'history.json',{'days':days,'missingDays':missing})
    codes=['airport_operations_us.py','airport_faa_history.py','airport_train_v2.py','airport_train_v3.py','airport_train.py','airport_features.py','airport_models.py']
    source={str(p.relative_to(ROOT)).replace('\\','/'):digest(p) for a in P['airports'] for p in sorted((ROOT/'.airport-data/model-v3/airports'/a).glob('*.json.gz'))}
    inputs={'protocolSha256':digest(SPEC_PATH),'baseProtocolSha256':digest(ROOT/'research/airport-protocol-v3.json'),
        'code':{name:digest(ROOT/'tools'/name) for name in codes},'sourcesSha256':hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest(),
        'historySha256':digest(OUT/'history.json'),'production':{name:digest(PUBLIC/name) for name in ('model.json','evaluation.json')}}
    lock=OUT/'fit-inputs.json'
    if lock.exists() and json.loads(lock.read_text())!=inputs: raise ValueError('Frozen experiment inputs changed')
    atomic_json(lock,inputs); atomic_json(OUT/'source-manifest.json',source)
    results={}
    for airport in P['airports']:
        path=OUT/'fitted'/(airport+'.json')
        if path.exists(): result=json.loads(path.read_text())
        else:
            result=fit_airport(airport,days,index); atomic_json(path,result)
        results[airport]=result
        print(json.dumps({'airport':airport,'slices':len(result['test']),'seconds':result['seconds'],'completed':len(results)}),flush=True)
    train.P=P; summary={}
    for period in ('test','previouslySeenStressTest'):
        trials=[s for r in results.values() for s in r[period].values()]; metrics=[s['variants']['operations'] for s in trials]
        train.adjust_evidence(metrics)
        for m in metrics: m['multipleTestingComparisons']=len(metrics)
        summary[period]={'slices':len(metrics),'testedAirports':sum(bool(r[period]) for r in results.values()),
            'positiveSlices':sum(m['brierSkill']>0 for m in metrics),
            'positiveAdjustedSlices':sum(m['skillInterval95'][0]>0 and m['qValueApproximate']<=P['falseDiscoveryRate'] for m in metrics),
            'moderateEvidenceSlices':sum(m['evidence']=='moderate' for m in metrics),
            'meanMetrics':{v:{k:float(np.mean([s['variants'][v][k] for s in trials])) for k in ('brier','calibrationError','bandCoverage','bandMeanWidth','logLoss','mae','intervalScore')} for v in VARIANTS},
            'byDirectionHorizon':{f'{d}_{h}':aggregate(results,period,f'{d}_{h}') for d in ('departures','arrivals') for h in SPEC['horizons']}}
    generated=stamp(); airport_models={a:json.loads((OUT/'fitted'/(a+'-models.json')).read_text()) for a in P['airports']}
    model={'version':SPEC['version'],'generatedAt':generated,'protocol':P,'operationsProtocol':SPEC,'featureVersion':FEATURE_VERSION,
        'models':{},'airportModels':airport_models,'airportCoverage':{a:r['coverage'] for a,r in results.items()},
        'servingPolicy':{'minimumTrainingWindowsPerClockBlock':30},'deploymentStatus':'experimental-comparison'}
    def evidence(period):
        return {a:{'directions':{d:{str(h):r[period][f'{d}_{h}']['variants']['operations'] for h in SPEC['horizons'] if f'{d}_{h}' in r[period]} for d in ('departures','arrivals')}} for a,r in results.items()}
    evaluation={'version':SPEC['version'],'generatedAt':generated,'protocol':P,'operationsProtocol':SPEC,
        'evaluationLabel':'Retrospective winter operations backtest','airports':evidence('test'),'stressAirports':evidence('previouslySeenStressTest'),
        'coverage':model['airportCoverage'],'coverageSummary':{'targetAirports':len(results),'testedAirports':summary['test']['testedAirports']},
        'cohorts':{},'summary':summary,'featureVersion':FEATURE_VERSION}
    atomic_json(OUT/'model.json',model); atomic_json(OUT/'evaluation.json',evaluation)
    report={'version':SPEC['version'],'generatedAt':generated,'protocol':SPEC,'inputs':inputs,'airports':results,'summary':summary,
        'history':{'validDays':len(days),'missingDays':missing,'messagesByAirport':{a:len(v[1]) for a,v in index.items()}},
        'seconds':round(time.perf_counter()-started,2),'paidApiDollars':0,'awsTrainingJobs':0}
    atomic_json(OUT/'report.json',report)
    if any(digest(PUBLIC/name)!=value for name,value in inputs['production'].items()): raise ValueError('Production files changed')
    print(json.dumps({'status':'complete','seconds':report['seconds'],'summary':summary}),flush=True)


if __name__=='__main__': main()
