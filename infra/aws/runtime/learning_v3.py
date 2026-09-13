"""Stream expanded history to disk; fit local challengers inside the existing job cap."""
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo
from guard import LIMITS, validate_pair


def run(s3,bucket,context):
    from handler import read,put,encode
    from learning import shift,months,protocol_for
    import airport_prepare_v3 as prep
    import airport_train_v3 as local
    import airport_train_v2 as train
    from airport_models import predict_batch
    from airport_features import features
    import numpy as np
    incumbent_raw=read(s3,bucket,'active/model.json')
    incumbent=json.loads(incumbent_raw); previous=json.loads(read(s3,bucket,'active/evaluation.json'))
    validate_pair(incumbent,previous,incumbent_raw)
    index=json.loads(read(s3,bucket,'history/index.json'))
    if index.get('scope')!='us-v3': raise ValueError('Expanded model requires expanded source history')
    available=set(index['months'])
    if not available or len(available)>72: raise ValueError('History exceeds reviewed month count')
    latest=shift(datetime.now(timezone.utc).strftime('%Y-%m'),-2)
    missing=[m for m in months(min(available),latest) if m not in available][:LIMITS['historyMonthsPerLearningRun']]
    with tempfile.TemporaryDirectory(prefix='airport-local-learning-') as folder:
        root=Path(folder); prep.configure(root,incumbent['protocol'])
        zones=json.loads(read(s3,bucket,'history/timezones.json'))
        import urllib.request
        from urllib.parse import urlparse
        from airport_weather import NoRedirect,USER_AGENT
        def fetch(url,path,limit):
            if path.exists(): return path.read_bytes()
            if urlparse(url).scheme!='https' or urlparse(url).hostname not in ('transtats.bts.gov','mesonet.agron.iastate.edu'):
                raise ValueError('Unexpected research source')
            fetch.requests+=1
            if fetch.requests>30: raise ValueError('Expanded research request quota exceeded')
            with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url,headers={'User-Agent':USER_AGENT}),timeout=35) as response:
                raw=response.read(limit+1)
            if len(raw)>limit: raise ValueError('Research response too large')
            path.write_bytes(raw); return raw
        fetch.requests=0; prep.base.fetch=fetch
        for month in missing:
            if context.get_remaining_time_in_millis()<180000: break
            try: prep.prepare_month(month,zones)
            except Exception as error:
                print(json.dumps({'month':month,'status':'not-ingested','reason':type(error).__name__})); break
            raw=(root/f'joined-{month}.json.gz').read_bytes()
            if len(raw)>2*1024*1024: raise ValueError('Derived history month too large')
            put(s3,bucket,f'history/joined-{month}.json.gz',raw)
            available.add(month); index['months']=sorted(available)
            put(s3,bucket,'history/index.json',encode(index))
        last=shift(index['lastEvaluatedMonth'],2)
        required=months(shift(last,-31),last)
        if not set(required).issubset(available):
            return {'status':'waiting-for-new-outcomes','nextTestMonths':[shift(last,-1),last],
                    'missingMonths':[m for m in required if m not in available]}
        protocol=protocol_for(last,incumbent['protocol'])
        protocol['selection']='Fixed airport-local regularized logistic challengers; no holdout tuning and no automatic promotion.'
        protocol['previouslySeenStressTest']=None
        index['lastEvaluatedMonth']=last; index['lastAttempt']={'period':last,'status':'reserved','protocol':protocol}
        put(s3,bucket,'history/index.json',encode(index))
        # Never hold the entire expanded row set in Lambda memory. Each archive is
        # bounded, decoded once, then sharded into temporary airport files.
        total_rows=0
        for month in required:
            raw=read(s3,bucket,f'history/joined-{month}.json.gz',2*1024*1024)
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream: expanded=stream.read(48*1024*1024+1)
            if len(expanded)>48*1024*1024: raise ValueError('Expanded month cap exceeded')
            payload=json.loads(expanded)
            if payload['month']!=month: raise ValueError('Source month mismatch')
            groups={a:[] for a in protocol['airports']}
            for row in payload['rows']:
                if row['airport'] not in groups: raise ValueError('Unexpected airport in source history')
                groups[row['airport']].append(row)
            total_rows+=len(payload['rows'])
            if total_rows>1600000: raise ValueError('Expanded history row cap exceeded')
            for airport,rows in groups.items():
                with gzip.open(root/(airport+'.jsonl.gz'),'at',encoding='utf-8') as stream:
                    for row in rows: stream.write(json.dumps(row,separators=(',',':'))+'\n')
            if sum(p.stat().st_size for p in root.iterdir() if p.is_file())>384*1024*1024:
                raise ValueError('Temporary storage cap exceeded')
            del payload,groups,expanded
        generated=datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
        model={'version':'airport-local-monthly-'+last,'generatedAt':generated,'protocol':protocol,
               'models':{},'airportModels':{},'airportCoverage':{},'servingPolicy':incumbent['servingPolicy']}
        evidence={'version':model['version'],'generatedAt':generated,'protocol':protocol,'airports':{},
                  'coverage':{},'status':'candidate-awaiting-review','automaticPromotion':False,'cohorts':{}}
        reports=[]
        for airport in protocol['airports']:
            if context.get_remaining_time_in_millis()<90000: raise TimeoutError('Fixed learner runtime is nearly exhausted')
            with gzip.open(root/(airport+'.jsonl.gz'),'rt',encoding='utf-8') as stream: rows=[json.loads(line) for line in stream]
            for row in rows:
                local_date=datetime.fromtimestamp(row['start'],timezone.utc).astimezone(ZoneInfo(protocol['airports'][airport])).date()
                row['localDate']=local_date.isoformat(); row['block']=local_date.toordinal()//protocol['bootstrapBlockDays']
            fitted=local.fit_airport(airport,rows,protocol)
            model['airportModels'][airport]=fitted['models']; model['airportCoverage'][airport]=fitted['coverage']
            evidence['airports'][airport]=fitted['test']; evidence['coverage'][airport]=fitted['coverage']
            for direction,horizons in fitted['test']['directions'].items():
                for horizon,report in horizons.items():
                    key=f'{direction}_{horizon}'
                    entry=incumbent['airportModels'][airport].get(key) if airport in incumbent.get('airportModels',{}) else incumbent['models'].get(key)
                    if entry:
                        part=local.eligible_splits(rows,protocol,direction,int(horizon))['test']
                        x=np.array([features(airport,r['start'],r['weather'][horizon],entry.get('featureAirports',incumbent['protocol']['airports'])) for r in part])
                        report['incumbentBrier']=train.brier_summary(part,predict_batch(entry['weather'],x))
                    reports.append(report)
            del rows
        train.P=protocol; train.adjust_evidence(reports)
        paired=[r for r in reports if 'incumbentBrier' in r]
        evidence['review']={'testedSlices':len(reports),'pairedSlices':len(paired),
            'candidateMeanBrier':float(np.mean([r['brier'] for r in paired])) if paired else None,
            'incumbentMeanBrier':float(np.mean([r['incumbentBrier'] for r in paired])) if paired else None,
            'regressedSlices':sum(r['brier']>r['incumbentBrier'] for r in paired),
            'undercoveredSlices':sum(r['bandCoverage']<.75 for r in reports)}
        model_raw=encode(model); evidence['modelSha256']=hashlib.sha256(model_raw).hexdigest()
        validate_pair(model,evidence,model_raw)
        prefix=f'candidates/{last}'
        put(s3,bucket,prefix+'/model.json',model_raw); put(s3,bucket,prefix+'/evaluation.json',encode(evidence))
        index['lastAttempt']['status']='candidate-awaiting-review'; put(s3,bucket,'history/index.json',encode(index))
        return {'status':'candidate-awaiting-review','candidate':prefix,**evidence['review']}
