"""Selection uses 2024 development folds. New 2026 test stays sealed until selection is durable."""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import gzip
import hashlib
import json
import math
from zoneinfo import ZoneInfo
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from airport_weather import ROOT,PUBLIC,atomic_json,stamp
from airport_features import features,feature_names
from airport_models import logit_many,predict_batch,interval_offsets,serializable
import airport_train as original

P=json.loads((ROOT/'research/airport-protocol-v2.json').read_text())
DATA=ROOT/'.airport-data/model-v2'
OUT=DATA/'candidate'
OUT.mkdir(parents=True,exist_ok=True)


def matrix(rows,h,weather=True,key='weather'):
    return np.array([features(r['airport'],r['start'],r[key][str(h)],P['airports'],weather) for r in rows])


def load_rows(include_2026=False):
    inventory=json.loads((DATA/'inventory.json').read_text())
    expected=39 if include_2026 else 24
    chosen=[r for r in inventory if include_2026 or r['month']<'2025']
    if len(chosen)!=expected: raise ValueError(f'Need {expected} prepared months, got {len(chosen)}')
    rows=[]
    for item in chosen:
        payload=json.loads(gzip.decompress((DATA/f"joined-{item['month']}.json.gz").read_bytes()))
        for row in payload['rows']:
            local=datetime.fromtimestamp(row['start'],timezone.utc).astimezone(ZoneInfo(P['airports'][row['airport']]))
            row['localDate']=local.date().isoformat(); row['block']=local.date().toordinal()//P['bootstrapBlockDays']
            rows.append(row)
    return rows,inventory


def split(rows,spec):
    return {key:[r for r in rows if value[0]<=r['localDate']<=value[1]] for key,value in spec.items() if isinstance(value,list) and len(value)==2 and isinstance(value[0],str)}


def fit_head(x,success,total,kind,calibration=False):
    use=total>0; x=x[use]; success=success[use]; total=total[use]
    if success.sum()==0 or success.sum()==total.sum():
        rate=(success.sum()+.5)/(total.sum()+1)
        return {'coef':[0.]*x.shape[1],'intercept':float(np.log(rate/(1-rate)))}
    doubled=np.concatenate((x,x)); labels=np.concatenate((np.ones(len(x)),np.zeros(len(x))))
    weights=np.concatenate((success,total-success)); keep=weights>0
    if kind=='linear':
        config={**P['candidates']['linear']}
        if calibration: config['C']=.02
        learner=LogisticRegression(**config).fit(doubled[keep],labels[keep],sample_weight=weights[keep])
        if learner.n_iter_[0]>=config['max_iter']: raise RuntimeError('Logistic solver did not converge')
        return {'coef':learner.coef_[0].tolist(),'intercept':float(learner.intercept_[0])}
    learner=HistGradientBoostingClassifier(**P['candidates']['boosted'],random_state=P['seed']).fit(doubled[keep],labels[keep],sample_weight=weights[keep])
    trees=[]
    for stage in learner._predictors:
        tree=[]
        for node in stage[0].nodes:
            if node['is_categorical']: raise ValueError('Categorical tree export not supported')
            tree.append([-1 if node['is_leaf'] else int(node['feature_idx']),0. if node['is_leaf'] else float(node['num_threshold']),
                         int(node['left']),int(node['right']),float(node['value']) if node['is_leaf'] else 0.])
        trees.append(tree)
    head={'trees':trees,'intercept':float(learner._baseline_prediction[0,0])}
    probe=x[np.linspace(0,len(x)-1,min(1000,len(x))).astype(int)]
    if not np.allclose(logit_many(head,probe),learner.decision_function(probe),atol=1e-10,rtol=0):
        raise ValueError('Portable tree export does not reproduce sklearn scores')
    head['_native']=learner
    return head


def fit(train,calibration,direction,h,kind,weather=True):
    x=matrix(train,h,weather); xc=matrix(calibration,h,weather)
    if kind=='linear':
        scaler=StandardScaler().fit(x,sample_weight=original.counts(train)['n']); mean=scaler.mean_; scale=scaler.scale_
    else: mean=np.zeros(x.shape[1]); scale=np.ones(x.shape[1])
    xs=(x-mean)/scale; xcs=(xc-mean)/scale
    heads={}; tc=original.targets(calibration,direction)
    for name,(success,total) in original.targets(train,direction).items():
        head=fit_head(xs,success,total,kind)
        calx=np.column_stack((logit_many(head,xcs),xc[:,:len(P['airports'])]))
        head['calibration']={**fit_head(calx,*tc[name],'linear',calibration=True),'airportCount':len(P['airports'])}
        heads[name]=head
    return {'kind':kind,'mean':mean.tolist(),'scale':scale.tolist(),'heads':heads,'features':feature_names(P['airports'],weather)}


def brier_summary(rows,p):
    c=original.counts(rows); n=c['n']; y=c['cancelled']+c['diverted']+c['delayed']
    return float(np.average(original.brier(p['disruption'],y,n),weights=n))


def calibrate_band(rows,p):
    c=original.counts(rows); observed=(c['cancelled']+c['diverted']+c['delayed'])/c['n']; residual=observed-p['disruption']
    def quantiles(values):
        # Conservative finite-sample order statistics for each signed tail.
        values=np.sort(values); n=len(values)
        lo=max(0,math.floor((n+1)*.1)-1); hi=min(n-1,math.ceil((n+1)*.9)-1)
        return [min(0.,float(values[lo])),max(0.,float(values[hi]))]
    bins={}; counts={}
    index=np.where(p['disruption']<.25,0,np.where(p['disruption']<.5,1,2))
    for i in range(3):
        part=residual[index==i]; counts[str(i)]=len(part)
        if len(part)>=P['minimumIntervalBinWindows']: bins[str(i)]=quantiles(part)
    return {'global':quantiles(residual),'bins':bins,'counts':counts,'windows':len(rows)}


def metrics(rows,p,baseline,spec):
    # Keep component and reliability definitions identical to v1; replace its daily
    # bootstrap and constant-width band with prespecified v2 procedures below.
    report=original.metrics(rows,p,baseline,0.,compute_bootstrap=False)
    c=original.counts(rows); n=c['n']; y=c['cancelled']+c['diverted']+c['delayed']; rate=y/n
    pred=p['disruption']; loss=original.brier(pred,y,n); base_loss=original.brier(baseline['disruption'],y,n)
    grouped=defaultdict(list)
    for i,r in enumerate(rows): grouped[r['block']].append(i)
    blocks=np.array([[(loss[ix]*n[ix]).sum(),(base_loss[ix]*n[ix]).sum(),n[ix].sum()] for ix in grouped.values()])
    rng=np.random.default_rng(P['seed']); draws=blocks[rng.integers(0,len(blocks),size=(P['bootstrapDayResamples'],len(blocks)))].sum(axis=1)
    improvement=1-draws[:,0]/draws[:,1]; delta=(draws[:,1]-draws[:,0])/draws[:,2]
    point=report['baselineBrier']-report['brier']
    pvalue=(1+np.sum(delta-point>=point))/(len(delta)+1) if point>0 else 1.
    bounds=np.array([interval_offsets(spec,v) for v in pred]); lo=np.maximum(0,pred+bounds[:,0]); hi=np.minimum(1,pred+bounds[:,1])
    report.update({'skillInterval95':np.quantile(improvement,[.025,.975]).tolist(),'bootstrapBlocks':len(blocks),
                   'pValueApproximate':float(pvalue),'bandCoverage':float(((rate>=lo)&(rate<=hi)).mean()),
                   'bandMeanWidth':float((hi-lo).mean()),'intervalCalibrationWindows':spec['windows'],
                   'intervalOffsets':spec['global'],'evidence':'limited',
                   'intervalScore':float((hi-lo+10*np.maximum(0,lo-rate)+10*np.maximum(0,rate-hi)).mean())})
    groups={}
    for name,flag in [('thunderMentioned',True),('noThunderMentioned',False)]:
        group=[r for r in rows if (max(r['weather'][str(metrics.horizon)][6:9])>0)==flag]
        if group: groups[name]={'windows':len(group),'flights':int(sum(r['n'] for r in group)),
                               'observedRate':sum(r['cancelled']+r['diverted']+r['delayed'] for r in group)/sum(r['n'] for r in group)}
    report['weatherGroups']=groups
    report['eventCalibration']={k:{'predicted':report['components'][k]['predictedRate'],'observed':report['components'][k]['observedRate']} for k in ('cancelled','diverted','delayed')}
    return report


def adjust_evidence(reports):
    order=sorted(range(len(reports)),key=lambda i:reports[i]['pValueApproximate']); best=1.
    for rank in range(len(order),0,-1):
        r=reports[order[rank-1]]; best=min(best,r['pValueApproximate']*len(order)/rank); r['qValueApproximate']=best
        r['evidence']='moderate' if r['days']>=P['minimumTestDaysForModerateEvidence'] and r['flights']>=P['minimumTestFlightsForModerateEvidence'] and r['skillInterval95'][0]>0 and best<=P['falseDiscoveryRate'] and r['calibrationError']<.05 and r['bandCoverage']>=.75 else 'limited'


def select():
    rows,_=load_rows(False); results=[]
    for fold in P['folds']:
        splits=split(rows,fold)
        for direction in ('departures','arrivals'):
            s={k:[r for r in v if r['direction']==direction] for k,v in splits.items()}
            for kind in P['candidates']:
                for h in P['horizons']:
                    cache=DATA/f"development-{fold['name'].replace(' ','-')}-{direction}-{kind}-{h}.json"
                    if cache.exists(): results.append(json.loads(cache.read_text())); continue
                    print(f"Development: {fold['name']} {direction} T-{h} {kind}",flush=True)
                    model=fit(s['train'],s['probabilityCalibration'],direction,h,kind)
                    p=predict_batch(model,matrix(s['test'],h))
                    score=brier_summary(s['test'],p)
                    result={'fold':fold['name'],'direction':direction,'horizon':h,'candidate':kind,'brier':score,
                            'windows':len(s['test']),'flights':int(sum(r['n'] for r in s['test']))}
                    atomic_json(cache,result); results.append(result)
    means={kind:float(np.mean([r['brier'] for r in results if r['candidate']==kind])) for kind in P['candidates']}
    winner='boosted' if means['boosted']<means['linear']*.995 else 'linear'
    record={'selected':winner,'meanBrier':means,'results':results,'selectedAt':stamp(),
            'protocolSha256':hashlib.sha256((ROOT/'research/airport-protocol-v2.json').read_bytes()).hexdigest(),
            'testReadDuringSelection':False}
    atomic_json(DATA/'selection.json',record)
    print(json.dumps({k:v for k,v in record.items() if k!='results'}),flush=True)


def evaluate():
    selection=json.loads((DATA/'selection.json').read_text())
    digest=hashlib.sha256((ROOT/'research/airport-protocol-v2.json').read_bytes()).hexdigest()
    if selection['protocolSha256']!=digest or selection['testReadDuringSelection']: raise ValueError('Selection protocol mismatch')
    if (OUT/'evaluation.json').exists(): raise ValueError('Evaluation already exists. Version a new experiment instead of tuning this test.')
    rows,inventory=load_rows(True); s0=split(rows,P); kind=selection['selected']
    model={'version':'airport-v2-'+kind,'generatedAt':stamp(),'protocol':P,'models':{},'clockSupport':original.clock_support(s0['train'],P['airports']),
           'servingPolicy':{'minimumTrainingWindowsPerClockBlock':30},'selection':selection}
    evidence={'version':model['version'],'generatedAt':model['generatedAt'],'protocol':P,'selection':selection,'preparation':inventory,
              'cohorts':{k:{'airportWindows':len(v),'flightEvents':int(sum(r['n'] for r in v))} for k,v in s0.items()},
              'airports':{a:{'directions':{}} for a in P['airports']},'stressAirports':{a:{'directions':{}} for a in P['airports']}}
    primary=[]; stress=[]
    for direction in ('departures','arrivals'):
        s={k:[r for r in v if r['direction']==direction] for k,v in s0.items()}
        print(f'Final matched calendar baseline: {direction} {kind}',flush=True)
        baseline=fit(s['train'],s['probabilityCalibration'],direction,6,kind,False)
        for h in P['horizons']:
            print(f'Final frozen fit: {direction} T-{h} {kind}',flush=True)
            fitted=fit(s['train'],s['probabilityCalibration'],direction,h,kind)
            ip=predict_batch(fitted,matrix(s['intervalCalibration'],h))
            wx=np.array([r['weather'][str(h)] for r in s['train']])
            entry={'weather':fitted,'baseline':baseline,'intervals':{},'weatherMin':wx.min(axis=0).tolist(),'weatherMax':wx.max(axis=0).tolist()}
            for airport in P['airports']:
                ix=[i for i,r in enumerate(s['intervalCalibration']) if r['airport']==airport]
                if len(ix)<100: raise ValueError(f'Insufficient interval evidence for {airport}')
                entry['intervals'][airport]=calibrate_band([s['intervalCalibration'][i] for i in ix],{k:v[ix] for k,v in ip.items()})
            for period,target,reports in [('test','airports',primary),('previouslySeenStressTest','stressAirports',stress)]:
                test=s[period]; p=predict_batch(fitted,matrix(test,h)); bp=predict_batch(baseline,matrix(test,h,False)); metrics.horizon=h
                for airport in P['airports']:
                    ix=[i for i,r in enumerate(test) if r['airport']==airport]; part=[test[i] for i in ix]
                    if len(part)<50: raise ValueError(f'Insufficient holdout coverage for {airport}')
                    report=metrics(part,{k:v[ix] for k,v in p.items()},{k:v[ix] for k,v in bp.items()},entry['intervals'][airport])
                    sensitivity=[r for r in part if r['weatherDelayed'][str(h)] is not None]
                    if sensitivity:
                        sp=predict_batch(fitted,matrix(sensitivity,h,key='weatherDelayed')); normal=predict_batch(fitted,matrix(sensitivity,h))
                        report['deliverySensitivity']={'lagMinutes':60,'windows':len(sensitivity),'coverage':len(sensitivity)/len(part),
                                                       'brier':brier_summary(sensitivity,sp),'mainBrierSameWindows':brier_summary(sensitivity,normal)}
                    # A paired v1 comparator is only legitimate on exactly these same events.
                    v1=json.loads((PUBLIC/'versions/v1/model.json').read_text())
                    if airport in v1['protocol']['airports']:
                        old=v1['models'][f'{direction}_{h}']; oldx=np.array([features(airport,r['start'],r['weather'][str(h)],v1['protocol']['airports']) for r in part])
                        oldp=predict_batch(old['weather'],oldx); n=original.counts(part)['n']
                        bounds=np.array([interval_offsets(old['intervals'][airport],v) for v in oldp['disruption']]); y=np.array([(r['cancelled']+r['diverted']+r['delayed'])/r['n'] for r in part])
                        oldlo=np.maximum(0,oldp['disruption']+bounds[:,0]); oldhi=np.minimum(1,oldp['disruption']+bounds[:,1])
                        report['previousModel']={'brier':brier_summary(part,oldp),'bandCoverage':float(((y>=oldlo)&(y<=oldhi)).mean()),
                                                 'bandMeanWidth':float((oldhi-oldlo).mean()),'intervalScore':float((oldhi-oldlo+10*np.maximum(0,oldlo-y)+10*np.maximum(0,y-oldhi)).mean()),
                                                 'mae':float(np.abs(oldp['disruption']-y).mean()),
                                                 'predictedCancellation':float(np.average(oldp['cancelled'],weights=n)),
                                                 'sameEventComparison':True,'note':'v1 used later training/calibration dates; this comparison does not isolate learner architecture'}
                    evidence[target][airport]['directions'].setdefault(direction,{})[str(h)]=report; reports.append(report)
            model['models'][f'{direction}_{h}']=entry
    adjust_evidence(primary); adjust_evidence(stress)
    model=serializable(model); encoded=json.dumps(model,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    evidence['modelSha256']=hashlib.sha256(encoded).hexdigest()
    for period,key in [('test','airports'),('previouslySeenStressTest','stressAirports')]:
        reports=[r for a in evidence[key].values() for d in a['directions'].values() for r in d.values()]
        evidence.setdefault('summary',{})[period]={'meanBrier':float(np.mean([r['brier'] for r in reports])),
             'meanBaselineBrier':float(np.mean([r['baselineBrier'] for r in reports])),
             'meanBandCoverage':float(np.mean([r['bandCoverage'] for r in reports])),
             'moderateEvidenceSlices':sum(r['evidence']=='moderate' for r in reports),'slices':len(reports)}
    atomic_json(OUT/'model.json',model); atomic_json(OUT/'evaluation.json',evidence)
    print(json.dumps(evidence['summary']),flush=True)
    print('Candidate artifacts written. Run parity/schema checks before explicitly promoting locally.',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['select','evaluate']); args=parser.parse_args()
    select() if args.command=='select' else evaluate()
