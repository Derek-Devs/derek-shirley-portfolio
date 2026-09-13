"""Validate national candidates and compare the actual incumbent before choosing a default."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import airport_operations_us as study
from airport_models import predict_batch
from airport_features import features
from airport_train_v3 import load_airport
from airport_faa_history import build_index
from airport_weather import atomic_json,PUBLIC,ROOT,stamp


def main():
    report=json.loads((study.OUT/'report.json').read_text()); inputs=report['inputs']
    assert all(study.digest(ROOT/'tools'/name)==h for name,h in inputs['code'].items())
    assert all(study.digest(PUBLIC/name)==h for name,h in inputs['production'].items())
    incumbent=json.loads((PUBLIC/'model.json').read_text()); model=json.loads((study.OUT/'model.json').read_text())
    history=json.loads((study.OUT/'history.json').read_text()); index=build_index(history['days'],study.P['airports'])
    count=0; incumbent_scores={'test':[],'previouslySeenStressTest':[]}
    for airport,entry in report['airports'].items():
        rows,_=study.attach(load_airport(airport),history['days'],index)
        for period in ('test','previouslySeenStressTest'):
            for key,trial in entry[period].items():
                direction,h=key.split('_'); h=int(h)
                part=[r for r in rows if r['direction']==direction and str(h) in r['operations'] and study.P[period][0]<=r['localDate']<=study.P[period][1]]
                local=model['airportModels'][airport][key]
                for variant in study.VARIANTS:
                    name='baseline' if variant=='calendar' else variant
                    p=predict_batch(local[name],study.matrix(part,airport,h,variant))
                    actual=study.train.brier_summary(part,p); recorded=trial['variants'][variant]
                    assert len(part)==recorded['windows'] and sum(r['n'] for r in part)==recorded['flights']
                    assert abs(actual-recorded['brier'])<1e-12; count+=1
                native=incumbent['airportModels'][airport].get(key) if airport in incumbent['airportModels'] else incumbent['models'].get(key)
                assert native is not None
                zones=native.get('featureAirports',incumbent['protocol']['airports'])
                x=np.array([features(airport,r['start'],r['weather'][str(h)],zones) for r in part])
                p=predict_batch(native['weather'],x); n=np.array([r['n'] for r in part]); y=np.array([r['cancelled']+r['diverted']+r['delayed'] for r in part])
                clipped=np.clip(p['disruption'],1e-8,1-1e-8)
                metrics={'brier':study.train.brier_summary(part,p),'logLoss':float(-(y*np.log(clipped)+(n-y)*np.log(1-clipped)).sum()/n.sum()),
                    'windows':len(part),'flights':int(n.sum()),'modelVersion':incumbent['version']}
                trial['productionComparator']=metrics; incumbent_scores[period].append(metrics)
        if (list(report['airports']).index(airport)+1)%20==0: print(json.dumps({'validatedAirports':list(report['airports']).index(airport)+1}),flush=True)
    release_rule=json.loads((ROOT/'research/airport-operations-us-v1-release.json').read_text())
    # Added-input evidence is impossible when no FAA activity occurred in fitting.
    # Separately optimized equivalent models differ by floating-point/solver noise;
    # block bootstrap can misleadingly call that tiny difference significant.
    correction={'reason':'No FAA activity in training cannot establish a learned FAA effect; suppress numerical-only skill tests while retaining raw probability scores.',
        'modelWeightsChanged':False,'correctionStage':'post-fit validation, before serving'}
    study.train.P=study.P
    for period in incumbent_scores:
        metrics=[s['variants']['operations'] for a in report['airports'].values() for s in a[period].values()]
        for m in metrics:
            if m['trainingWindowsWithFaaActivity']==0:
                m['rawNumericalComparison']={k:m[k] for k in ('brierSkill','skillInterval95','pValueApproximate')}
                m.update(brierSkill=0.,skillInterval95=[0.,0.],pValueApproximate=1.,faaEvidenceStatus='no-learned-faa-effect')
        study.train.adjust_evidence(metrics)
        s=report['summary'][period]
        s.update(positiveSlices=sum(m['brierSkill']>0 for m in metrics),
            positiveAdjustedSlices=sum(m['skillInterval95'][0]>0 and m['qValueApproximate']<=study.P['falseDiscoveryRate'] for m in metrics),
            moderateEvidenceSlices=sum(m['evidence']=='moderate' for m in metrics),
            noFaaTrainingActivitySlices=sum(m['trainingWindowsWithFaaActivity']==0 for m in metrics))
    report['evidenceCorrection']=correction
    default='operations'
    for period in incumbent_scores:
        summary=report['summary'][period]
        native={k:float(np.mean([r[k] for r in incumbent_scores[period]])) for k in ('brier','logLoss')}
        summary['productionComparatorMean']=native
        for key in ('brier','logLoss'):
            if not summary['meanMetrics']['operations'][key]<min(summary['meanMetrics']['weather'][key],native[key]): default='weather'
    report.update(defaultModel=default,releaseRule=release_rule,validation={'savedModelScoresReproduced':count,'incumbentSlicesScored':sum(map(len,incumbent_scores.values())),
        'productionWeightsPreserved':True,'privateJetOutcomeValidation':False})
    evaluation=json.loads((study.OUT/'evaluation.json').read_text()); evaluation['summary']=report['summary']
    for period,evidence_key in [('test','airports'),('previouslySeenStressTest','stressAirports')]:
        for airport,entry in report['airports'].items():
            for key,trial in entry[period].items():
                d,h=key.split('_')
                evaluation[evidence_key][airport]['directions'][d][h]={**trial['variants']['operations'],'productionComparator':trial['productionComparator']}
    evaluation['evidenceCorrection']=correction
    folder=PUBLIC/'operations'; folder.mkdir(exist_ok=True)
    model_bytes=(study.OUT/'model.json').read_bytes(); (folder/'model.json').write_bytes(model_bytes)
    evaluation['modelSha256']=hashlib.sha256(model_bytes).hexdigest(); atomic_json(folder/'evaluation.json',evaluation)
    release={'version':report['version'],'generatedAt':model['generatedAt'],'defaultModel':default,'experimental':True,'featureVersion':model['featureVersion'],
        'ruleSha256':study.digest(ROOT/'research/airport-operations-us-v1-release.json'),
        'files':{name:study.digest(folder/name) for name in ('model.json','evaluation.json')}}
    atomic_json(folder/'release.json',release)
    raw=json.dumps(report,separators=(',',':'),allow_nan=False).encode()
    (PUBLIC/'experiments/operations-us-v1-full.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    compact={k:report[k] for k in ('version','generatedAt','protocol','inputs','summary','history','seconds','paidApiDollars','awsTrainingJobs','defaultModel','releaseRule','validation','evidenceCorrection')}
    compact['fullReportSha256']=hashlib.sha256(raw).hexdigest()
    atomic_json(PUBLIC/'experiments/operations-us-v1.json',compact)
    atomic_json(study.OUT/'validated-report.json',report)
    print(json.dumps({'validated':True,'scores':count,'defaultModel':default,
        'productionMeans':{k:v['productionComparatorMean'] for k,v in report['summary'].items()},
        'modelBytes':len(model_bytes),'evaluationBytes':(folder/'evaluation.json').stat().st_size}))


if __name__=='__main__': main()
