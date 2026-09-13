"""Frozen airport-local expansion. Existing 25 models remain unchanged."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import json
import time
from zoneinfo import ZoneInfo
import numpy as np
import airport_train_v2 as train
from airport_models import predict_batch, serializable
from airport_weather import ROOT, PUBLIC, atomic_json, stamp

P=json.loads((ROOT/'research/airport-protocol-v3.json').read_text())
DATA=ROOT/'.airport-data/model-v3'
OUT=DATA/'candidate'
PERIODS=('train','probabilityCalibration','intervalCalibration','test','previouslySeenStressTest')


def load_airport(airport):
    inventory=json.loads((DATA/'inventory.json').read_text())
    if len(inventory)!=39: raise ValueError('Complete all 39 frozen source months before fitting')
    expected=hashlib.sha256(json.dumps(P,sort_keys=True).encode()).hexdigest()
    if any(item.get('protocolSha256')!=expected for item in inventory): raise ValueError('Preparation protocol changed; rebuild derived rows before fitting')
    rows=[]
    for item in inventory:
        path=DATA/'airports'/airport/(item['month']+'.json.gz')
        rows.extend(json.loads(gzip.decompress(path.read_bytes())))
    for row in rows:
        local=datetime.fromtimestamp(row['start'],timezone.utc).astimezone(ZoneInfo(P['airports'][airport]))
        row['localDate']=local.date().isoformat(); row['block']=local.date().toordinal()//P['bootstrapBlockDays']
    return rows


def eligible_splits(rows,protocol,direction,horizon):
    return train.split([r for r in rows if r['direction']==direction and r['weather'].get(str(horizon)) is not None],protocol)


def support_reason(s,protocol):
    gates={'train':protocol['minimumFitWindows'],'probabilityCalibration':protocol['minimumProbabilityCalibrationWindows'],
           'intervalCalibration':protocol['minimumIntervalCalibrationWindows'],'test':protocol['minimumTestWindows']}
    gaps=[f'{key}: {len(s[key])}/{minimum} windows' for key,minimum in gates.items() if len(s[key])<minimum]
    return 'Insufficient local evidence ('+'; '.join(gaps)+').' if gaps else None


def fit_airport(airport,rows,protocol=P):
    if any(r['airport']!=airport for r in rows): raise ValueError('Airport-local fitting cannot use another airport outcomes')
    start=time.perf_counter(); local={**protocol,'airports':{airport:protocol['airports'][airport]}}
    train.P=local
    result={'airport':airport,'models':{},'test':{'directions':{}},'stress':{'directions':{}},
            'coverage':{'method':'airport-local-linear','directions':{}},'cohorts':{}}
    for direction in ('departures','arrivals'):
        result['coverage']['directions'][direction]={}
        for h in protocol['horizons']:
            s=eligible_splits(rows,protocol,direction,h)
            info={'windows':{k:len(v) for k,v in s.items()},'flightEvents':{k:int(sum(r['n'] for r in v)) for k,v in s.items()}}
            reason=support_reason(s,protocol)
            info.update(status='insufficient-data' if reason else 'tested',reason=reason)
            result['coverage']['directions'][direction][str(h)]=info
            if reason: continue
            model=train.fit(s['train'],s['probabilityCalibration'],direction,h,'linear')
            baseline=train.fit(s['train'],s['probabilityCalibration'],direction,h,'linear',False)
            ip=predict_batch(model,train.matrix(s['intervalCalibration'],h))
            band=train.calibrate_band(s['intervalCalibration'],ip)
            wx=np.array([r['weather'][str(h)] for r in s['train']])
            entry={'weather':model,'baseline':baseline,'intervals':{airport:band},
                   'weatherMin':wx.min(axis=0).tolist(),'weatherMax':wx.max(axis=0).tolist(),
                   'featureAirports':local['airports'],
                   'clockSupport':train.original.clock_support(s['train'],local['airports'])[airport][direction],
                   'method':'airport-local-linear'}
            result['models'][f'{direction}_{h}']=entry
            for period,key in [('test','test'),('previouslySeenStressTest','stress')]:
                test=s.get(period,[])
                if len(test)<protocol['minimumTestWindows']: continue
                p=predict_batch(model,train.matrix(test,h)); bp=predict_batch(baseline,train.matrix(test,h,False))
                train.metrics.horizon=h
                report=train.metrics(test,p,bp,band)
                report['cohorts']={k:{'airportWindows':len(v),'flightEvents':int(sum(r['n'] for r in v))} for k,v in s.items()}
                report['method']='airport-local-linear'
                matched=[i for i,r in enumerate(test) if all(r['weather'].get(str(t)) is not None for t in protocol['horizons'])]
                if matched:
                    part=[test[i] for i in matched]
                    report['matchedHorizon']={'windows':len(part),'flights':int(sum(r['n'] for r in part)),
                        'brier':train.brier_summary(part,{k:v[matched] for k,v in p.items()}),
                        'baselineBrier':train.brier_summary(part,{k:v[matched] for k,v in bp.items()})}
                sensitivity=[r for r in test if r['weatherDelayed'].get(str(h)) is not None]
                if sensitivity:
                    sp=predict_batch(model,train.matrix(sensitivity,h,key='weatherDelayed'))
                    normal=predict_batch(model,train.matrix(sensitivity,h))
                    report['deliverySensitivity']={'lagMinutes':60,'windows':len(sensitivity),'coverage':len(sensitivity)/len(test),
                        'brier':train.brier_summary(sensitivity,sp),'mainBrierSameWindows':train.brier_summary(sensitivity,normal)}
                result[key]['directions'].setdefault(direction,{})[str(h)]=report
    result['seconds']=round(time.perf_counter()-start,3)
    return serializable(result)


def assemble():
    old=json.loads((PUBLIC/'versions/v2/model.json').read_text())
    prior=json.loads((PUBLIC/'versions/v2/evaluation.json').read_text())
    model=deepcopy(old); evidence=deepcopy(prior)
    model.update(version='airport-v3-us-local-expansion',generatedAt=stamp(),protocol=P,airportModels={},airportCoverage={})
    for entry in model['models'].values(): entry['featureAirports']=old['protocol']['airports']
    evidence.update(version=model['version'],generatedAt=model['generatedAt'],protocol=P,coverage={},
                    evaluationLabel='Retrospective winter backtest',
                    studyMethod='The original 25 airport-aware boosted models are retained. Each added airport has its own fixed logistic model, probability calibration, and interval calibration. No blind airport transfer.',
                    preparation=json.loads((DATA/'inventory.json').read_text()))
    # The old development selection applies to the incumbent only.
    evidence['incumbentSelection']=evidence.pop('selection',None)
    for a in P['incumbentAirports']:
        evidence['coverage'][a]={'method':'retained-v2','directions':{d:{str(h):{'status':'tested','reason':None} for h in P['horizons']} for d in ('departures','arrivals')}}
        for collection in ('airports','stressAirports'):
            for direction in evidence[collection][a]['directions'].values():
                for report in direction.values(): report['method']='retained-v2'
    for airport in P['airports']:
        if airport in P['incumbentAirports']: continue
        candidate=json.loads((OUT/'airports'/f'{airport}.json').read_text())
        if candidate['protocolSha256']!=protocol_hash(): raise ValueError('Stale airport experiment')
        model['airportModels'][airport]=candidate['models']
        evidence['airports'][airport]=candidate['test']; evidence['stressAirports'][airport]=candidate['stress']
        evidence['coverage'][airport]=candidate['coverage']
    model['airportCoverage']=evidence['coverage']
    train.P=P
    for key in ('airports','stressAirports'):
        reports=[r for a in evidence[key].values() for d in a['directions'].values() for r in d.values()]
        train.adjust_evidence(reports)
        for report in reports: report['multipleTestingComparisons']=len(reports)
        evidence.setdefault('summary',{})['test' if key=='airports' else 'previouslySeenStressTest']={
            'slices':len(reports),'meanBrier':float(np.mean([r['brier'] for r in reports])),
            'meanBaselineBrier':float(np.mean([r['baselineBrier'] for r in reports])),
            'meanBandCoverage':float(np.mean([r['bandCoverage'] for r in reports])),
            'moderateEvidenceSlices':sum(r['evidence']=='moderate' for r in reports)}
    tested=sum(any(a['directions'].values()) for a in evidence['airports'].values())
    evidence['coverageSummary']={'targetAirports':len(P['airports']),'testedAirports':tested,
        'withoutTestedSlices':[a for a,v in evidence['airports'].items() if not any(v['directions'].values())],
        'retainedAirports':len(P['incumbentAirports']),'newlyTestedAirports':tested-len(P['incumbentAirports'])}
    model.pop('selection',None)
    raw=json.dumps(model,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    evidence['modelSha256']=hashlib.sha256(raw).hexdigest()
    atomic_json(OUT/'model.json',model); atomic_json(OUT/'evaluation.json',evidence)
    print(json.dumps({'coverage':evidence['coverageSummary'],'summary':evidence['summary'],'modelBytes':len(raw)}),flush=True)


def protocol_hash():
    return hashlib.sha256((ROOT/'research/airport-protocol-v3.json').read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--airport'); parser.add_argument('--assemble-only',action='store_true'); args=parser.parse_args()
    (OUT/'airports').mkdir(parents=True,exist_ok=True)
    if not args.assemble_only:
        codes=[a for a in P['airports'] if a not in P['incumbentAirports']]
        if args.airport:
            if args.airport not in codes: raise ValueError('Choose an airport in the frozen expansion')
            codes=[args.airport]
        start=time.perf_counter()
        for airport in codes:
            path=OUT/'airports'/f'{airport}.json'
            if path.exists():
                if json.loads(path.read_text())['protocolSha256']!=protocol_hash(): raise ValueError('Protocol changed after fitting')
                continue
            result=fit_airport(airport,load_airport(airport)); result['protocolSha256']=protocol_hash()
            atomic_json(path,result)
            print(json.dumps({'airport':airport,'testedSlices':len(result['models']),'seconds':result['seconds']}),flush=True)
        print(json.dumps({'trainingWallSeconds':round(time.perf_counter()-start,2)}),flush=True)
    if not args.airport: assemble()


if __name__=='__main__': main()
