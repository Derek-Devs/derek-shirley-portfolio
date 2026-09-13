"""U.S. expansion: bounded downloads, explicit station IDs, horizon-specific cohorts."""
from bisect import bisect_right
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import argparse
import gzip
import hashlib
import json
import shutil
import time
from pathlib import Path
import airport_prepare_v2 as base
from airport_weather import ROOT, atomic_json
from airport_features import weather_features

P=json.loads((ROOT/'research/airport-protocol-v3.json').read_text())
DATA=ROOT/'.airport-data/model-v3'


def configure(folder=DATA, protocol=P):
    folder.mkdir(parents=True,exist_ok=True)
    base.DATA=folder; base.PROTOCOL=protocol; base.AIRPORTS=protocol['airports']


def monthly_weather(month):
    result={}; manifests=[]; qa=Counter()
    old=P['incumbentAirports']
    groups=[old[i:i+8] for i in range(0,len(old),8)]
    new=[a for a in base.AIRPORTS if a not in old]
    groups += [new[i:i+8] for i in range(0,len(new),8)]
    for batch,codes in enumerate(groups):
        values,manifest=base.weather_batch(month,codes,batch)
        result.update(values); manifests.append(manifest); qa.update(manifest['qa'])
    return result,{'batches':manifests,'qa':dict(qa)}


def join_rows(flights,weather,protocol):
    index={a:[max(f['issued'],f['productTime']) for f in fs] for a,fs in weather.items()}
    joined=[]; qa=Counter()
    for row in flights.to_dict('records'):
        prefix=f"{row['airport']}_{row['direction']}"
        qa['airportWindows']+=1; qa[prefix+'_candidateWindows']+=1
        if row['n']<protocol['minimumScheduledFlightsPerWindow'] or row['unknown']:
            qa[prefix+'_lowCountOrUnknown']+=1; continue
        vectors={}; delayed={}
        for h in protocol['horizons']:
            cutoff=row['start']-h*3600
            def vector(lag):
                ix=bisect_right(index[row['airport']],cutoff-lag*60)-1
                return weather_features(weather[row['airport']][ix],row['start'],cutoff) if ix>=0 else None
            vectors[str(h)]=vector(protocol['availabilityLagMinutes'])
            delayed[str(h)]=vector(protocol['availabilitySensitivityMinutes'])
            qa[prefix+('_missing_' if vectors[str(h)] is None else '_included_')+str(h)]+=1
        if not any(v is not None for v in vectors.values()): continue
        joined.append({**row,'weather':vectors,'weatherDelayed':delayed})
    return joined,dict(qa)


def prepare_month(month,zones):
    path=base.DATA/f'joined-{month}.json.gz'
    digest=hashlib.sha256(json.dumps(base.PROTOCOL,sort_keys=True).encode()).hexdigest()
    if path.exists():
        cached=json.loads(gzip.decompress(path.read_bytes()))
        if cached.get('protocolSha256')==digest: return cached
    started=time.perf_counter()
    flights,bts=base.monthly_flights(month,zones)
    weather,wx_source=monthly_weather(month)
    rows,qa=join_rows(flights,weather,base.PROTOCOL)
    result={'month':month,'rows':rows,'qa':qa,'sources':[bts,wx_source],
            'protocolSha256':hashlib.sha256(json.dumps(base.PROTOCOL,sort_keys=True).encode()).hexdigest(),
            'seconds':round(time.perf_counter()-started,2)}
    # A month is reusable only after the complete gzip is atomically installed.
    temp=path.with_suffix('.tmp'); temp.write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0)); temp.replace(path)
    return result


def shard(result):
    month=result['month']; groups={a:[] for a in P['airports']}
    for row in result['rows']: groups[row['airport']].append(row)
    for airport,rows in groups.items():
        folder=DATA/'airports'/airport; folder.mkdir(parents=True,exist_ok=True)
        path=folder/f'{month}.json.gz'
        raw=gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0)
        if path.exists() and path.read_bytes()==raw: continue
        temp=path.with_suffix('.tmp'); temp.write_bytes(raw); temp.replace(path)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--month'); args=parser.parse_args()
    configure()
    months=[f'{y}-{m:02d}' for y in (2023,2024,2025) for m in range(1,13) if y<2025 or m<=9]+[f'2026-{m:02d}' for m in range(1,7)]
    if args.month:
        if args.month not in months: raise ValueError('Month outside frozen experiment')
        months=[args.month]
    if len(months)>P['maxResearchMonths']: raise ValueError('Research month cap exceeded')
    # Reuse exact source archives for the incumbent airports; do not reuse their
    # common-horizon derived rows for the expanded eligibility calculation.
    previous=ROOT/'.airport-data/model-v2'
    for name in ('timezones.json','airports.csv'):
        if not (DATA/name).exists(): shutil.copyfile(previous/name,DATA/name)
    for month in months:
        for batch in range(4):
            name=f'weather-{month}-{batch}.zip'
            if (previous/name).exists() and not (DATA/name).exists(): shutil.copyfile(previous/name,DATA/name)
    zones=base.timezone_map(); zones.update(P['airports'])
    inventory={r['month']:r for r in json.loads((DATA/'inventory.json').read_text())} if (DATA/'inventory.json').exists() else {}
    started=time.perf_counter()
    failures={}
    with ThreadPoolExecutor(max_workers=2) as pool:
        remaining=iter(months)
        futures={pool.submit(prepare_month,m,zones):m for m in [next(remaining,None),next(remaining,None)] if m}
        while futures:
            done,_=wait(futures,return_when=FIRST_COMPLETED)
            for future in done:
                month=futures.pop(future)
                try:
                    result=future.result(); shard(result)
                    inventory[month]={k:v for k,v in result.items() if k!='rows'}
                    inventory[month]['rows']=len(result['rows'])
                    atomic_json(DATA/'inventory.json',sorted(inventory.values(),key=lambda r:r['month']))
                    print(json.dumps({'month':month,'windows':len(result['rows']),'seconds':result['seconds'],'completed':len(inventory)}),flush=True)
                    del result
                except Exception as error:
                    failures[month]=f'{type(error).__name__}: {error}'
                    print(json.dumps({'month':month,'error':failures[month]}),flush=True)
                following=next(remaining,None)
                if following: futures[pool.submit(prepare_month,following,zones)]=following
    if failures: raise RuntimeError('Incomplete source months: '+json.dumps(failures))
    print(json.dumps({'status':'prepared','months':len(months),'wallSeconds':round(time.perf_counter()-started,2)}),flush=True)


if __name__=='__main__': main()
