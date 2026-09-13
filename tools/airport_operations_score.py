"""Portable operations scoring using the same FAA features as the nationwide fit."""
import math
from airport_features import features
from airport_faa_history import FEATURE_VERSION,snapshot_features,available_at
from airport_models import interval_offsets
from airport_predict import score as weather_score,predict,timestamp


def score(snapshot,model,evaluation):
    if model.get('featureVersion')!=FEATURE_VERSION or evaluation.get('featureVersion')!=FEATURE_VERSION:
        raise ValueError('Operations feature version mismatch')
    output=weather_score(snapshot,model,evaluation); output['modelKind']='operations'
    cutoff=timestamp(snapshot['generatedAt'])
    for airport,airport_result in output['airports'].items():
        faa=snapshot_features(snapshot.get('faaHistory'),airport,cutoff)
        for direction,periods in airport_result['directions'].items():
            for h,result in periods.items():
                if result['status']!='available' or 'probabilities' not in result: continue
                if faa is None:
                    for key in ('probabilities','baseline','band','evidence','outsideTrainingRange','bandCoverage','weather'): result.pop(key,None)
                    result.update(status='no-faa-history',reason='Fresh, complete FAA advisory history is unavailable. Select the weather model to view its estimate.')
                    continue
                entry=model['airportModels'][airport][f'{direction}_{h}']; wx=result['weather']
                vector=features(airport,timestamp(result['start']),wx,entry['featureAirports'])+faa
                p=predict(entry['operations'],vector); baseline=result['probabilities']['disruption']
                outside=result['outsideTrainingRange'] or any(v<lo-1e-6 or v>hi+1e-6 for v,lo,hi in zip(faa,entry['faaMin'],entry['faaMax']))
                evidence=evaluation['airports'][airport]['directions'][direction][h]
                lo,hi=interval_offsets(entry['intervals'][airport],p['disruption'])
                result.update(probabilities=p,baseline=baseline,baselineKind='matched-weather',
                    band=[max(0,p['disruption']+lo),min(1,p['disruption']+hi)],outsideTrainingRange=outside,
                    evidence='limited' if outside else evidence['evidence'],
                    faaActivity={'messages24h':round(math.expm1(faa[1])+math.expm1(faa[3])),
                        'availableAtEpoch':available_at(cutoff),'trainingWindows':entry['trainingWindowsWithFaaActivity']},
                    operationsBrierSkill=evidence['brierSkill'])
    return output


def publish(snapshot,public):
    from airport_weather import read_json,atomic_json
    folder=public/'operations'; model=read_json(folder/'model.json',None); evaluation=read_json(folder/'evaluation.json',None)
    if not model or not evaluation: return
    import hashlib
    if model['version']!=evaluation['version'] or model['generatedAt']!=evaluation['generatedAt'] or evaluation.get('modelSha256')!=hashlib.sha256((folder/'model.json').read_bytes()).hexdigest():
        raise ValueError('Operations model/evaluation pair mismatch')
    atomic_json(folder/'risk.json',score(snapshot,model,evaluation))
