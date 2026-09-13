"""Fit once against a frozen chronological protocol; export portable models and honest evidence."""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
from datetime import datetime,timezone
import gzip
import hashlib
import json
import math
from zoneinfo import ZoneInfo
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from airport_features import features,feature_names
from airport_weather import ROOT,PUBLIC,atomic_json,stamp

P=json.loads((ROOT/'research/airport-protocol.json').read_text())
DATA=ROOT/'.airport-data/model'


def clock_support(rows,zones=None):
    zones=zones or P['airports']
    support={a:{d:{str(hour):0 for hour in range(0,24,2)} for d in ('arrivals','departures')} for a in zones}
    for row in rows:
        hour=datetime.fromtimestamp(row['start'],timezone.utc).astimezone(ZoneInfo(zones[row['airport']])).hour
        support[row['airport']][row['direction']][str(hour//2*2)]+=1
    return support


def sigmoid(x):
    return 1/(1+np.exp(-np.clip(x,-35,35)))


def fit_head(x,success,total):
    use=total>0; x=x[use]; success=success[use]; total=total[use]
    if success.sum()==0 or success.sum()==total.sum():
        rate=(success.sum()+.5)/(total.sum()+1)
        return {'coef':[0.]*x.shape[1],'intercept':float(np.log(rate/(1-rate)))}
    doubled=np.concatenate((x,x)); labels=np.concatenate((np.ones(len(x)),np.zeros(len(x))))
    weights=np.concatenate((success,total-success)); keep=weights>0
    model=LogisticRegression(C=1.,solver='lbfgs',max_iter=1500,tol=1e-7)
    model.fit(doubled[keep],labels[keep],sample_weight=weights[keep])
    if model.n_iter_[0]>=1500: raise RuntimeError('Optimizer did not converge')
    return {'coef':model.coef_[0].tolist(),'intercept':float(model.intercept_[0])}


def counts(rows):
    return {k:np.array([r[k] for r in rows],dtype=float) for k in ('n','cancelled','diverted','delayed','onTime')}


def targets(rows,direction):
    c=counts(rows); operated=c['n']-c['cancelled']-c['diverted']
    return {'cancelled':(c['cancelled'],c['n']),
            **({'diverted':(c['diverted'],c['n']-c['cancelled'])} if direction=='arrivals' else {}),
            'delayed':(c['delayed'],operated)}


def matrix(rows,h,weather=True,key='weather'):
    return np.array([features(r['airport'],r['start'],r[key][str(h)],P['airports'],weather) for r in rows])


def head_logit(head,x):
    return x@np.array(head['coef'])+head['intercept']


def fit(train,calibration,direction,h,weather):
    x=matrix(train,h,weather); xc=matrix(calibration,h,weather)
    scaler=StandardScaler().fit(x,sample_weight=counts(train)['n'])
    x=scaler.transform(x); xc=scaler.transform(xc)
    heads={}; tc=targets(calibration,direction)
    for name,(success,total) in targets(train,direction).items():
        head=fit_head(x,success,total)
        # Disjoint probability calibration: a sigmoid on the fixed model's log odds.
        head['calibration']=fit_head(head_logit(head,xc).reshape(-1,1),*tc[name])
        heads[name]=head
    return {'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'heads':heads,
            'features':feature_names(P['airports'],weather)}


def predict(model,x):
    from airport_models import predict_batch
    return predict_batch(model,x)


def brier(p,y,n):
    return (y*(1-p)**2+(n-y)*p**2)/n


def metrics(rows,p,baseline,band,compute_bootstrap=True):
    c=counts(rows); n=c['n']; y=c['cancelled']+c['diverted']+c['delayed']; rate=y/n
    predicted=p['disruption']; base=baseline['disruption']; clipped=np.clip(predicted,1e-8,1-1e-8)
    loss=brier(predicted,y,n); base_loss=brier(base,y,n)
    score=float(np.average(loss,weights=n)); base_score=float(np.average(base_loss,weights=n))
    bins=[]
    bin_index=np.minimum(9,np.floor(predicted*10).astype(int))
    for index in range(10):
        use=bin_index==index
        if use.any(): bins.append({'predicted':float(np.average(predicted[use],weights=n[use])),
                                  'observed':float(y[use].sum()/n[use].sum()),'flights':int(n[use].sum()),'windows':int(use.sum())})
    # Resample airport-local days, retaining all windows in each sampled day.
    days={}
    for i,r in enumerate(rows):
        day=r['localDate']; days.setdefault(day,[]).append(i)
    blocks=np.array([[float((loss[ix]*n[ix]).sum()),float((base_loss[ix]*n[ix]).sum()),float(n[ix].sum())] for ix in days.values()])
    rng=np.random.default_rng(P['seed']); boot=[]
    for _ in range(P['bootstrapDayResamples'] if compute_bootstrap else 0):
        sample=blocks[rng.integers(0,len(blocks),len(blocks))].sum(axis=0)
        boot.append(1-sample[0]/sample[1])
    if not boot: boot=[1-score/base_score]
    lo=np.maximum(0,predicted-band); hi=np.minimum(1,predicted+band)
    return {'flights':int(n.sum()),'windows':len(rows),'days':len(days),'observedRate':float(y.sum()/n.sum()),
            'predictedRate':float(np.average(predicted,weights=n)), 'brier':score,'baselineBrier':base_score,
            'brierSkill':1-score/base_score,'skillInterval95':np.quantile(boot,[.025,.975]).tolist(),
            'logLoss':float(-(y*np.log(clipped)+(n-y)*np.log(1-clipped)).sum()/n.sum()),
            'mae':float(np.abs(predicted-rate).mean()),'baselineMae':float(np.abs(base-rate).mean()),
            'calibrationError':float(sum(b['flights']*abs(b['predicted']-b['observed']) for b in bins)/n.sum()),
            'bandCoverage':float(((rate>=lo)&(rate<=hi)).mean()),'bandMeanWidth':float((hi-lo).mean()),'calibration':bins,
            'components':{k:{'brier':float(np.average(brier(p[k],c[k],n),weights=n)),
                             'observedRate':float(c[k].sum()/n.sum()),'predictedRate':float(np.average(p[k],weights=n))}
                          for k in ('cancelled','delayed','diverted')}}


def interval_radius(rows,p):
    c=counts(rows); observed=(c['cancelled']+c['diverted']+c['delayed'])/c['n']
    residual=np.abs(observed-p['disruption']); level=min(1,math.ceil((len(rows)+1)*P['intervalNominalCoverage'])/len(rows))
    return float(np.quantile(residual,level,method='higher'))


def main():
    inventory=json.loads((DATA/'inventory.json').read_text())
    if len(inventory)!=27: raise ValueError('Complete the fixed 27-month preparation before fitting')
    rows=[]
    for item in inventory:
        for row in json.loads(gzip.decompress((DATA/f"joined-{item['month']}.json.gz").read_bytes()))['rows']:
            row['localDate']=datetime.fromtimestamp(row['start'],timezone.utc).astimezone(ZoneInfo(P['airports'][row['airport']])).date().isoformat()
            rows.append(row)
    splits={key:[r for r in rows if P[key][0]<=r['localDate']<=P[key][1]] for key in ('train','probabilityCalibration','intervalCalibration','test')}
    if any(not value for value in splits.values()): raise ValueError('Empty chronological split')
    model={'version':'airport-logit-1','generatedAt':stamp(),'protocol':P,'models':{},
           'clockSupport':clock_support(splits['train']),
           'servingPolicy':{'minimumTrainingWindowsPerClockBlock':30,'introducedAfterFirstBacktest':True,
                            'rationale':'Withhold live windows intersecting local clock blocks absent or sparse in training; this does not alter the published test.'}}
    evidence={'version':model['version'],'generatedAt':model['generatedAt'],'protocol':P,
              'cohorts':{k:{'airportWindows':len(v),'flightEvents':int(sum(r['n'] for r in v))} for k,v in splits.items()},
              'preparation':inventory,'airports':{a:{'directions':{}} for a in P['airports']}}
    for direction in ('departures','arrivals'):
        s={key:[r for r in value if r['direction']==direction] for key,value in splits.items()}
        for h in P['horizons']:
            print(f'Fitting {direction} T-{h}',flush=True)
            weather=fit(s['train'],s['probabilityCalibration'],direction,h,True)
            baseline=fit(s['train'],s['probabilityCalibration'],direction,h,False)
            entry={'weather':weather,'baseline':baseline,'intervals':{},
                   'weatherMin':np.min(np.array([r['weather'][str(h)] for r in s['train']]),axis=0).tolist(),
                   'weatherMax':np.max(np.array([r['weather'][str(h)] for r in s['train']]),axis=0).tolist()}
            testp=predict(weather,matrix(s['test'],h)); testbase=predict(baseline,matrix(s['test'],h,False))
            ip=predict(weather,matrix(s['intervalCalibration'],h))
            for airport in P['airports']:
                ix=[i for i,r in enumerate(s['test']) if r['airport']==airport]
                ci=[i for i,r in enumerate(s['intervalCalibration']) if r['airport']==airport]
                test=[s['test'][i] for i in ix]; interval=[s['intervalCalibration'][i] for i in ci]
                if len(interval)<50 or len(test)<50: raise ValueError(f'Insufficient evaluation for {airport}')
                radius=interval_radius(interval,{k:v[ci] for k,v in ip.items()}); entry['intervals'][airport]=radius
                report=metrics(test,{k:v[ix] for k,v in testp.items()},{k:v[ix] for k,v in testbase.items()},radius)
                report['intervalCalibrationWindows']=len(interval); report['intervalRadius']=radius
                report['evidence']='moderate' if report['days']>=P['minimumTestDaysForModerateEvidence'] and report['flights']>=P['minimumTestFlightsForModerateEvidence'] and report['skillInterval95'][0]>0 and report['calibrationError']<.05 else 'limited'
                sensitivity=[r for r in test if r['weatherDelayed'][str(h)] is not None]
                if sensitivity:
                    sp=predict(weather,matrix(sensitivity,h,key='weatherDelayed')); sb=predict(baseline,matrix(sensitivity,h,False))
                    main_same=predict(weather,matrix(sensitivity,h)); sc=counts(sensitivity); sy=sc['cancelled']+sc['diverted']+sc['delayed']
                    report['deliverySensitivity']={'lagMinutes':60,'windows':len(sensitivity),'coverage':len(sensitivity)/len(test),
                        'brier':float(np.average(brier(sp['disruption'],sy,sc['n']),weights=sc['n'])),
                        'mainBrierSameWindows':float(np.average(brier(main_same['disruption'],sy,sc['n']),weights=sc['n']))}
                groups={}
                for name,flag in [('thunderMentioned',True),('noThunderMentioned',False)]:
                    group=[r for r in test if (max(r['weather'][str(h)][6:9])>0)==flag]
                    if group: groups[name]={'windows':len(group),'flights':int(sum(r['n'] for r in group)),
                                           'observedRate':sum(r['cancelled']+r['diverted']+r['delayed'] for r in group)/sum(r['n'] for r in group)}
                report['weatherGroups']=groups
                evidence['airports'][airport]['directions'].setdefault(direction,{})[str(h)]=report
            model['models'][f'{direction}_{h}']=entry
    encoded=json.dumps(model,separators=(',',':'),allow_nan=False).encode(); evidence['modelSha256']=hashlib.sha256(encoded).hexdigest()
    atomic_json(PUBLIC/'model.json',model); atomic_json(PUBLIC/'evaluation.json',evidence)
    atomic_json(DATA/'evaluation-run.json',{'at':stamp(),'modelSha256':evidence['modelSha256'],'protocolSha256':hashlib.sha256((ROOT/'research/airport-protocol.json').read_bytes()).hexdigest()})
    for a in P['airports']:
        print(a,json.dumps({h:{'skill':round(v['brierSkill'],4),'mae':round(v['mae'],4),'evidence':v['evidence']} for h,v in evidence['airports'][a]['directions']['departures'].items()}),flush=True)
    print('Portable model and held-out evaluation published locally.',flush=True)


if __name__=='__main__': main()
