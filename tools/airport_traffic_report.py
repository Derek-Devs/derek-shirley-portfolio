"""Validate and publish an experiment report separately from production forecasts."""
import gzip
import hashlib
import json
from pathlib import Path
from airport_weather import ROOT, PUBLIC, atomic_json


def publish():
    folder=ROOT/'.airport-data/traffic-proxy-v1'
    report=json.loads((folder/'report.json').read_text())
    protocol_hash=hashlib.sha256((ROOT/'research/airport-traffic-proxy-v1.json').read_bytes()).hexdigest()
    code_hash=hashlib.sha256((ROOT/'tools/airport_traffic_proxy.py').read_bytes()).hexdigest()
    assert report['protocolSha256']==protocol_hash
    assert len(report['airports'])==100
    for airport in report['airports'].values():
        assert airport['codeSha256']==code_hash and airport['protocolSha256']==protocol_hash
        for period in ('test','previouslySeenStressTest'):
            for trial in airport[period].values():
                variants=list(trial['variants'].values())
                assert len({(m['flights'],m['windows'],m['days']) for m in variants})==1
                assert all(0<=m['bandCoverage']<=1 and 0<=m['brier']<=1 for m in variants)
                assert all(m['intervalCalibrationWindows']>0 for m in variants)
    # The experiment never modifies the selected production pair.
    model_hash=hashlib.sha256((PUBLIC/'model.json').read_bytes()).hexdigest()
    assert model_hash=='ec351874faadd887187764b376e882f72f1bcf9121c37ad6ffb688721cdea344'
    assert (PUBLIC/'evaluation.json').read_bytes()==(PUBLIC/'versions/v3/evaluation.json').read_bytes()
    report['validation']={'sameWindowComparisons':True,'productionModelUnchanged':True,'modelSha256':model_hash,
        'experimentCodeSha256':code_hash,'assessedAirports':len(report['airports'])}
    raw=json.dumps(report,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    destination=PUBLIC/'experiments'; destination.mkdir(exist_ok=True)
    (destination/'traffic-proxy-v1-full.json.gz').write_bytes(gzip.compress(raw,mtime=0))
    metrics=('flights','windows','days','brier','brierSkill','skillInterval95','qValueApproximate','calibrationError','mae','logLoss','bandCoverage','bandMeanWidth','intervalScore')
    summary={k:report[k] for k in ('version','generatedAt','protocol','protocolSha256','summary','seconds','validation')}
    summary['decision']='Keep the production model. This retrospective experiment does not establish a reliable general improvement from lagged historical traffic.'
    summary['fullReportSha256']=hashlib.sha256(raw).hexdigest()
    summary['airports']={code:{period:{key:{v:{k:m[k] for k in metrics if k in m} for v,m in trial['variants'].items()} for key,trial in a[period].items()} for period in ('test','previouslySeenStressTest')} for code,a in report['airports'].items()}
    atomic_json(destination/'traffic-proxy-v1.json',summary)
    print(json.dumps({'validated':True,'summaryBytes':(destination/'traffic-proxy-v1.json').stat().st_size,'fullReportGzipBytes':(destination/'traffic-proxy-v1-full.json.gz').stat().st_size}))


if __name__=='__main__': publish()
