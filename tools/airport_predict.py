"""Score shared hourly snapshots with portable weights. No dependencies or network calls."""
from datetime import datetime,timezone
import math
from zoneinfo import ZoneInfo
from airport_features import parse_taf,weather_features,features
from airport_weather import PUBLIC,STATE,read_json,atomic_json,stamp
from airport_models import calibrated_one,interval_offsets


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()


def predict(model,vector):
    dimension=len(model['mean'])
    if len(vector)!=dimension or len(model['scale'])!=dimension or any('coef' in h and len(h['coef'])!=dimension for h in model['heads'].values()):
        raise ValueError('Feature/model schema mismatch; refusing to score')
    if not all(math.isfinite(v) for v in vector) or not all(math.isfinite(s) and s>0 for s in model['scale']):
        raise ValueError('Non-finite feature or invalid model scaling')
    x=[(v-m)/s for v,m,s in zip(vector,model['mean'],model['scale'])]
    q={}
    for name,head in model['heads'].items():
        q[name]=calibrated_one(head,x,vector)
    cancel=q['cancelled']; divert=(1-cancel)*q.get('diverted',0)
    delayed=(1-cancel-divert)*q['delayed']
    return {'cancelled':cancel,'diverted':divert,'delayed':delayed,
            'disruption':cancel+divert+delayed,'onTime':1-cancel-divert-delayed}


def score(snapshot,model,evaluation):
    asof=timestamp(snapshot['generatedAt']); protocol=model['protocol']; zones=protocol['airports']
    output={'version':model['version'],'generatedAt':snapshot['generatedAt'],'modelBuiltAt':model['generatedAt'],
            'windowHours':2,'airports':{}}
    source=snapshot['sources'].get('forecasts',{})
    fresh=source.get('status')=='ok' and asof-timestamp(source.get('fetchedAt','1970-01-01T00:00:00Z'))<=90*60
    for airport in zones:
        station=protocol.get('stations',{}).get(airport,'K'+airport)
        reports=snapshot['stations'].get(station,{}).get('tafs',[])
        known=[r for r in reports if timestamp(r['issuedAt'])<=asof and timestamp(r['firstSeenAt'])<=asof]
        latest=max(known,key=lambda r:timestamp(r['issuedAt'])) if known else None
        try: taf=parse_taf(latest['raw'],datetime.fromtimestamp(timestamp(latest['issuedAt']),timezone.utc)) if latest else None
        except (ValueError,TypeError): taf=None
        if taf and taf['station']!=station: taf=None
        item={'directions':{},'issuedAt':latest['issuedAt'] if latest else None}
        for direction in ('departures','arrivals'):
            item['directions'][direction]={}
            for h in protocol['horizons']:
                key=f'{direction}_{h}'
                entry=model['airportModels'][airport].get(key) if airport in model.get('airportModels',{}) else model['models'].get(key)
                target=asof+h*3600; wx=weather_features(taf,target,asof) if fresh else None
                local_hours={datetime.fromtimestamp(t,timezone.utc).astimezone(ZoneInfo(zones[airport])).hour//2*2 for t in (target,target+7199)}
                support=entry.get('clockSupport',model.get('clockSupport',{}).get(airport,{}).get(direction,{})) if entry else {}
                supported=all(support.get(str(hour),0)>=model.get('servingPolicy',{}).get('minimumTrainingWindowsPerClockBlock',30) for hour in local_hours)
                result={'start':stamp(datetime.fromtimestamp(target,timezone.utc)),
                        'end':stamp(datetime.fromtimestamp(target+7200,timezone.utc)),
                        'status':'available' if wx else 'no-forecast',
                        'reason':None if wx else 'A fresh, supported forecast must cover the complete two-hour window.'}
                if not entry:
                    wx=None
                    detail=model.get('airportCoverage',{}).get(airport,{}).get('directions',{}).get(direction,{}).get(str(h),{})
                    result.update({'status':'insufficient-evidence','reason':detail.get('reason') or 'This airport and horizon do not have enough historical evidence for a tested model.'})
                elif wx and not supported:
                    wx=None
                    result.update({'status':'low-data','reason':'Too few eligible training windows at these local hours. Sparse overnight flight periods are not extrapolated into a probability.'})
                if wx:
                    feature_zones=entry.get('featureAirports',zones)
                    vector=features(airport,target,wx,feature_zones)
                    p=predict(entry['weather'],vector); base=predict(entry['baseline'],features(airport,target,wx,feature_zones,False))
                    evidence=evaluation['airports'][airport]['directions'][direction][str(h)]
                    outside=any(v<lo-1e-6 or v>hi+1e-6 for v,lo,hi in zip(wx,entry['weatherMin'],entry['weatherMax']))
                    lo,hi=interval_offsets(entry['intervals'][airport],p['disruption'])
                    result.update({'probabilities':p,'baseline':base['disruption'],
                                   'band':[max(0,p['disruption']+lo),min(1,p['disruption']+hi)],
                                   'evidence':'limited' if outside else evidence['evidence'],'outsideTrainingRange':outside,
                                   'bandCoverage':evidence['bandCoverage'],
                                   'weather':wx})
                item['directions'][direction][str(h)]=result
        output['airports'][airport]=item
    return output


def publish_risk(snapshot):
    model=read_json(PUBLIC/'model.json',None); evaluation=read_json(PUBLIC/'evaluation.json',None)
    if not model or not evaluation or model['version']!=evaluation['version'] or model['generatedAt']!=evaluation['generatedAt']: return 0
    atomic_json(PUBLIC/'risk.json',score(snapshot,model,evaluation))
    return sum(any(a['directions'].values()) for a in evaluation['airports'].values())


if __name__=='__main__':
    snapshot=read_json(STATE/'latest.json',None)
    if not snapshot: raise SystemExit('Collect weather before scoring')
    print({'modeledAirports':publish_risk(snapshot),'weatherAsOf':snapshot['generatedAt']})
