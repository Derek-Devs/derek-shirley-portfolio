"""Reproduce saved-model scores and publish an auditable, aggregate-only report."""
from __future__ import annotations
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
from airport_operations_pilot import OUT, ROOT, PUBLIC, P, SPEC, SPEC_PATH, VARIANTS, matrix, hashes
from airport_models import predict_batch
import airport_train_v2 as train
from airport_weather import atomic_json
import numpy as np
import pandas as pd
import scipy
import sklearn


def main():
    report=json.loads((OUT/'report.json').read_text()); inputs=report['inputs']
    assert hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()==inputs['protocolSha256']
    assert hashes()==inputs['protectedFiles']
    assert len(report['airports'])==6
    assert report['summary']['test']['slices']==34
    assert report['summary']['previouslySeenStressTest']['slices']==34
    for name,digest in inputs['code'].items():
        folder='research' if name.endswith('.json') else 'tools'
        assert hashlib.sha256((ROOT/folder/name).read_bytes()).hexdigest()==digest
    reproduced=0; model_hashes={}
    for airport,entry in report['airports'].items():
        rows=json.loads(gzip.decompress((OUT/'prepared'/(airport+'.json.gz')).read_bytes()))
        models_path=OUT/'fitted'/(airport+'-models.json')
        models=json.loads(models_path.read_text()); model_hashes[airport]=hashlib.sha256(models_path.read_bytes()).hexdigest()
        for period in ('test','previouslySeenStressTest'):
            for key,trial in entry[period].items():
                direction,h=key.split('_'); h=int(h)
                part=[r for r in rows if r['direction']==direction and str(h) in r['operations'] and P[period][0]<=r['localDate']<=P[period][1]]
                assert len({(m['flights'],m['windows'],m['days']) for m in trial['variants'].values()})==1
                for v,metric in trial['variants'].items():
                    assert len(part)==metric['windows'] and sum(r['n'] for r in part)==metric['flights']
                    p=predict_batch(models[key]['variants'][v],matrix(part,airport,h,v))
                    assert abs(train.brier_summary(part,p)-metric['brier'])<1e-12
                    assert np.allclose(p['onTime']+p['cancelled']+p['diverted']+p['delayed'],1)
                    reproduced+=1
                assert all(0<=m['qValueApproximate']<=1 for m in trial['comparisons'].values())
    report['validation'].update(reproducedSavedModelScores=reproduced,modelHashes=model_hashes,
        runtime={'python':sys.version.split()[0],'platform':platform.platform(),'numpy':np.__version__,
            'pandas':pd.__version__,'scipy':scipy.__version__,'scikitLearn':sklearn.__version__})
    probes=[p for p in OUT.iterdir() if p.is_file() and (p.name.endswith('.html') or p.name in ('runways-2022-12-31.csv','runway-commit-before-2023.json'))]
    report['validation']['sourceProbes']=[{'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in probes]
    destination=PUBLIC/'experiments'; destination.mkdir(exist_ok=True)
    raw=json.dumps(report,separators=(',',':'),allow_nan=False).encode()
    (destination/'operations-pilot-v1-full.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    metrics=['flights','windows','days','brier','brierSkill','skillInterval95','qValueApproximate','calibrationError',
        'logLoss','mae','bandCoverage','bandMeanWidth','intervalScore','evidence','eventCalibration']
    compact={k:report[k] for k in ('version','generatedAt','protocol','inputs','seconds','summary','decision','validation')}
    compact['sourceAudit']={k:report['features'][k] for k in ('audit','runways','faa','seconds')}
    compact['fullReportSha256']=hashlib.sha256(raw).hexdigest()
    compact['airports']={a:{'coverage':entry['coverage'],**{period:{key:{
        'variants':{v:{k:m[k] for k in metrics if k in m} for v,m in trial['variants'].items()},
        'comparisons':{v:{k:m[k] for k in metrics if k in m} for v,m in trial['comparisons'].items()},
        'deliverySensitivity':trial['deliverySensitivity'],'windowsWithRecentFaaActivity':trial['windowsWithRecentFaaActivity']}
        for key,trial in entry[period].items()} for period in ('test','previouslySeenStressTest')}} for a,entry in report['airports'].items()}
    atomic_json(destination/'operations-pilot-v1.json',compact)
    # Derived tables keep the human report reproducible without choosing the best slice.
    lines=['# Operations pilot: all aggregate results','',
        'Relative Brier-error reduction versus the matched calendar + weather model. Positive values mean lower probability error, not percentage points of flight delay or percent accuracy. Brackets are paired 95% bootstrap intervals, not adjusted aggregate significance tests.','',
        'Each direction/horizon pools eligible flight events across airports. Windows differ across horizons. Arrivals and departures can count the same flight; do not add these counts as distinct journeys.','']
    for period,label in [('test','Winter: January–February 2026'),('previouslySeenStressTest','Spring: March–June 2026')]:
        lines += ['## '+label,'','| Direction / horizon | Airports | Airport flight events | + direction / runways | + FAA activity | Combined |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
        for key,value in report['summary'][period]['byDirectionHorizon'].items():
            if value is None: continue
            cells=[]
            for name in ('runwayVsWeather','faaVsWeather','combinedVsWeather'):
                m=value['comparisons'][name]; lo,hi=m['skillInterval95']
                cells.append(f"{100*m['brierSkill']:+.2f}% [{100*lo:+.2f}, {100*hi:+.2f}]")
            d,h=key.split('_'); lines.append(f"| {d.title()} / {h}h | {value['airports']} | {value['flightEvents']:,} | "+' | '.join(cells)+' |')
        lines+=['','### Calibration and uncertainty','',
            'Equal-weight means across the 34 tested airport/direction/horizon slices. Calibration gap is the flight-weighted absolute gap within 10 probability bins, then averaged across slices. Outcome-rate bands target 80% coverage; these are not confidence intervals on an individual flight.','',
            '| Input variant | Brier error ↓ | Calibration gap ↓ | 80% band coverage | Mean band width | Log loss ↓ |',
            '| --- | ---: | ---: | ---: | ---: | ---: |']
        for v,m in report['summary'][period]['meanMetrics'].items():
            lines.append(f"| {v} | {m['brier']:.5f} | {100*m['calibrationError']:.2f} pp | {100*m['bandCoverage']:.1f}% | {100*m['bandMeanWidth']:.1f} pp | {m['logLoss']:.5f} |")
        lines+=['','### Six-hour airport results: combined inputs versus weather','',
            '| Airport | Departure error reduction [95% interval] | Departure adjusted q | Arrival error reduction [95% interval] | Arrival adjusted q |',
            '| --- | ---: | ---: | ---: | ---: |']
        for a,entry in report['airports'].items():
            cells=[]
            for d in ('departures','arrivals'):
                m=entry[period][d+'_6']['comparisons']['combinedVsWeather']; lo,hi=m['skillInterval95']
                cells += [f"{100*m['brierSkill']:+.2f}% [{100*lo:+.2f}, {100*hi:+.2f}]",f"{m['qValueApproximate']:.3f}"]
            lines.append('| '+a+' | '+' | '.join(cells)+' |')
        lines+=['','The approximate BH adjustment includes all four experimental contrasts across the 34 airport/direction/horizon slices (136 tests) within this period. It does not remove retrospective selection, dependence, or delivery uncertainty.','']
    (ROOT/'docs/airport-operations-pilot-v1-tables.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'validated':True,'reproducedScores':reproduced,'productionUnchanged':hashes()==inputs['protectedFiles'],
        'summaryBytes':(destination/'operations-pilot-v1.json').stat().st_size,'fullReportGzipBytes':(destination/'operations-pilot-v1-full.json.gz').stat().st_size}))


if __name__=='__main__': main()
