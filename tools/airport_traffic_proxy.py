"""Retrospective, chronological traffic-proxy ablation; never promotes a model."""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS', '2')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '2')
import argparse
import calendar
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import time
from zoneinfo import ZoneInfo
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
import airport_train_v2 as train
from airport_train_v3 import load_airport, eligible_splits, support_reason
from airport_features import features, feature_names
from airport_models import logit_many, predict_batch, serializable
from airport_weather import ROOT, atomic_json, stamp

SPEC = json.loads((ROOT/'research/airport-traffic-proxy-v1.json').read_text())
BASE = json.loads((ROOT/'research/airport-protocol-v3.json').read_text())
P = {**BASE, **{k:SPEC[k] for k in ('train','probabilityCalibration','intervalCalibration','test','previouslySeenStressTest')}}
DATA = ROOT/'.airport-data/model-v3'
OUT = ROOT/'.airport-data/traffic-proxy-v1'
VARIANTS = SPEC['variants']


def source_months(target_month, available, spec=SPEC):
    cutoff = datetime.strptime(target_month+'-01','%Y-%m-%d').date()-timedelta(days=spec['availabilityLagDays']+1)
    # A source month is not available until all its dates precede the embargo.
    end_index = cutoff.year*12+cutoff.month-2
    def index(month):
        y,m=map(int,month.split('-')); return y*12+m-1
    return [m for m in sorted(available) if end_index-spec['profileLookbackMonths']+1 <= index(m) <= end_index]


def month_exposure(month, zone, boundary):
    y,m=map(int,month.split('-')); result=np.zeros((7,12))
    for day in range(boundary+1, calendar.monthrange(y,m)[1]-boundary+1):
        for slot in range(12):
            naive=datetime(y,m,day,slot*2); local=naive.replace(tzinfo=ZoneInfo(zone))
            if datetime.fromtimestamp(local.timestamp(),ZoneInfo(zone)).replace(tzinfo=None)!=naive: continue
            result[naive.weekday(),slot]+=1
    return result


def build_monthly():
    result={a:{} for a in P['airports']}; manifests=[]
    for path in sorted(DATA.glob('flights-*.csv.gz')):
        month=path.name[8:15]
        frame=pd.read_csv(path,usecols=['airport','direction','start','n'])
        manifests.append({'month':month,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
        groups=dict(tuple(frame.groupby('airport')))
        for airport,zone in P['airports'].items():
            sums=np.zeros((7,12,2)); group=groups.get(airport)
            if group is not None:
                local=pd.to_datetime(group.start,unit='s',utc=True).dt.tz_convert(zone)
                di=(group.direction=='arrivals').astype(int).to_numpy()
                np.add.at(sums,(local.dt.weekday.to_numpy(),(local.dt.hour//2).to_numpy(),di),group.n.to_numpy())
            result[airport][month]={'sums':sums,'exposure':month_exposure(month,zone,P['monthBoundaryExclusionDays'])}
    return result,manifests


def traffic_profile(target_month, monthly):
    months=source_months(target_month,monthly)
    if len(months)<SPEC['minimumProfileMonths']: return None
    sums=sum((monthly[m]['sums'] for m in months),np.zeros((7,12,2)))
    exposure=sum((monthly[m]['exposure'] for m in months),np.zeros((7,12)))
    if sums.sum()==0 or np.any(exposure<5): return None
    expected=sums/exposure[:,:,None]
    peak=float(np.quantile(expected.sum(axis=2),.95))
    return {'months':months,'expected':expected,'peak':max(1.,peak)}


def profile_values(profile, weekday, slot):
    expected=profile['expected']; departure,arrival=expected[weekday,slot]
    pressure=(departure+arrival)/profile['peak']
    before=expected[(weekday-1)%7 if slot==0 else weekday,(slot-1)%12].sum()
    after=expected[(weekday+1)%7 if slot==11 else weekday,(slot+1)%12].sum()
    return [float(np.log1p(departure)),float(np.log1p(arrival)),float(pressure),float(np.log1p(before+after))]


def attach_profiles(rows, monthly, zone):
    profiles={}; retained=[]
    for row in rows:
        month=row['localDate'][:7]
        if month not in profiles: profiles[month]=traffic_profile(month,monthly)
        profile=profiles[month]
        if profile is None: continue
        local=datetime.fromtimestamp(row['start'],timezone.utc).astimezone(ZoneInfo(zone))
        row={**row,'traffic':profile_values(profile,local.weekday(),local.hour//2)}
        retained.append(row)
    audit={m:{'sourceMonths':p['months'],'historicalPeakTwoHourEvents':p['peak']} for m,p in profiles.items() if p}
    return retained,audit


def matrix(rows, airport, horizon, variant):
    zone={airport:P['airports'][airport]}; result=[]
    for row in rows:
        wx=row['weather'][str(horizon)]
        values=features(airport,row['start'],wx,zone,variant!='calendar')
        if variant=='weatherTraffic':
            traffic=row['traffic']; pressure=traffic[2]
            values+=traffic+[pressure*max(wx[6:9]),pressure*max(wx[5],wx[12]),pressure*wx[1]/50.]
        result.append(values)
    return np.array(result)


def fit_variant(rows, calibration, airport, direction, horizon, variant):
    x=matrix(rows,airport,horizon,variant); xc=matrix(calibration,airport,horizon,variant)
    scaler=StandardScaler().fit(x,sample_weight=train.original.counts(rows)['n'])
    xs=scaler.transform(x); xcs=scaler.transform(xc); heads={}
    tc=train.original.targets(calibration,direction)
    for name,(success,total) in train.original.targets(rows,direction).items():
        head=train.fit_head(xs,success,total,'linear')
        calx=np.column_stack((logit_many(head,xcs),xc[:,:1]))
        head['calibration']={**train.fit_head(calx,*tc[name],'linear',calibration=True),'airportCount':1}
        heads[name]=head
    return {'kind':'linear','mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),'heads':heads,
        'features':feature_names({airport:P['airports'][airport]},variant!='calendar')+(SPEC['trafficFeatures'] if variant=='weatherTraffic' else [])}


def paired_blocks(rows, predictions):
    n=np.array([r['n'] for r in rows]); y=np.array([r['cancelled']+r['diverted']+r['delayed'] for r in rows])
    losses={v:train.original.brier(p['disruption'],y,n)*n for v,p in predictions.items()}
    blocks=defaultdict(lambda:np.zeros(4))
    for i,row in enumerate(rows):
        blocks[row['block']]+=np.array([losses['calendar'][i],losses['weather'][i],losses['weatherTraffic'][i],n[i]])
    return {str(k):v.tolist() for k,v in blocks.items()}


def fit_airport(airport, monthly):
    started=time.perf_counter(); train.P={**P,'airports':{airport:P['airports'][airport]}}
    rows,audit=attach_profiles(load_airport(airport),monthly,P['airports'][airport])
    result={'airport':airport,'profileAudit':audit,'coverage':{},'test':{},'previouslySeenStressTest':{}}
    for direction in ('departures','arrivals'):
        for h in P['horizons']:
            key=f'{direction}_{h}'; s=eligible_splits(rows,P,direction,h); reason=support_reason(s,P)
            result['coverage'][key]={'reason':reason,'windows':{k:len(v) for k,v in s.items()}}
            if reason: continue
            models={v:fit_variant(s['train'],s['probabilityCalibration'],airport,direction,h,v) for v in VARIANTS}
            bands={v:train.calibrate_band(s['intervalCalibration'],predict_batch(models[v],matrix(s['intervalCalibration'],airport,h,v))) for v in VARIANTS}
            for period in ('test','previouslySeenStressTest'):
                test=s[period]
                if len(test)<P['minimumTestWindows']: continue
                predictions={v:predict_batch(models[v],matrix(test,airport,h,v)) for v in VARIANTS}
                reports={}; train.metrics.horizon=h
                for v in VARIANTS:
                    comparison='weather' if v=='weatherTraffic' else 'calendar'
                    reports[v]=train.metrics(test,predictions[v],predictions[comparison],bands[v])
                result[period][key]={'variants':reports,'pairedBlocks':paired_blocks(test,predictions)}
    result['seconds']=round(time.perf_counter()-started,2)
    return serializable(result)


def assemble(results, manifest, protocol_hash, elapsed):
    train.P=P
    report={'version':SPEC['version'],'generatedAt':stamp(),'protocol':SPEC,'protocolSha256':protocol_hash,
        'sourceFiles':manifest,'seconds':round(elapsed,2),'airports':results,'summary':{}}
    for period in ('test','previouslySeenStressTest'):
        slices=[s for a in results.values() for s in a[period].values()]
        traffic=[s['variants']['weatherTraffic'] for s in slices]
        train.adjust_evidence(traffic)
        aggregate={}
        for direction in ('departures','arrivals'):
            for h in P['horizons']:
                key=f'{direction}_{h}'; blocks=defaultdict(lambda:np.zeros(4)); airports=0
                for a in results.values():
                    value=a[period].get(key)
                    if not value: continue
                    airports+=1
                    for day,values in value['pairedBlocks'].items(): blocks[day]+=values
                if not blocks: continue
                values=np.array(list(blocks.values())); total=values.sum(axis=0)
                rng=np.random.default_rng(P['seed']); draws=values[rng.integers(0,len(values),size=(P['bootstrapDayResamples'],len(values)))].sum(axis=1)
                skill=1-draws[:,2]/draws[:,1]
                aggregate[key]={'airports':airports,'flightEvents':int(total[3]),'calendarBrier':total[0]/total[3],
                    'weatherBrier':total[1]/total[3],'trafficBrier':total[2]/total[3],
                    'trafficSkill':1-total[2]/total[1],'trafficSkillInterval95':np.quantile(skill,[.025,.975]).tolist(),
                    'sharedCalendarBlocks':len(blocks)}
        report['summary'][period]={'testedAirports':sum(bool(a[period]) for a in results.values()),'slices':len(slices),
            'positiveTrafficBrierSlices':sum(m['brierSkill']>0 for m in traffic),
            'positiveAdjustedSlices':sum(m['skillInterval95'][0]>0 and m['qValueApproximate']<=P['falseDiscoveryRate'] for m in traffic),
            'moderateTrafficEvidenceSlices':sum(m['evidence']=='moderate' for m in traffic),
            'meanMetrics':{v:{k:float(np.mean([s['variants'][v][k] for s in slices])) for k in ('brier','calibrationError','mae','logLoss','bandCoverage','bandMeanWidth','intervalScore')} for v in VARIANTS},
            'byDirectionHorizon':aggregate}
    atomic_json(OUT/'report.json',serializable(report))
    print(json.dumps({'status':'complete','seconds':report['seconds'],'summary':report['summary']}),flush=True)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--airport'); args=parser.parse_args()
    started=time.perf_counter(); OUT.mkdir(parents=True,exist_ok=True); (OUT/'airports').mkdir(exist_ok=True)
    protocol_hash=hashlib.sha256((ROOT/'research/airport-traffic-proxy-v1.json').read_bytes()).hexdigest()
    code_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    monthly,manifest=build_monthly()
    source_hash=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    codes=[args.airport] if args.airport else list(P['airports']); results={}
    for airport in codes:
        if airport not in P['airports']: raise ValueError('Unknown airport')
        path=OUT/'airports'/f'{airport}.json'
        if path.exists():
            result=json.loads(path.read_text())
            if result.get('protocolSha256')!=protocol_hash or result.get('sourceSha256')!=source_hash or result.get('codeSha256')!=code_hash: raise ValueError('Existing experiment inputs differ; create a new version')
        else:
            result=fit_airport(airport,monthly[airport]); result.update(protocolSha256=protocol_hash,sourceSha256=source_hash,codeSha256=code_hash)
            atomic_json(path,result)
            print(json.dumps({'airport':airport,'slices':len(result['test']),'seconds':result['seconds']}),flush=True)
        results[airport]=result
    if not args.airport: assemble(results,manifest,protocol_hash,time.perf_counter()-started)


if __name__=='__main__': main()
