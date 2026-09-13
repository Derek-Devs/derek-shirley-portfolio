"""Isolated as-of research features; never imported by the live collector/model."""
from __future__ import annotations
from bisect import bisect_right
from collections import Counter
from datetime import datetime, timedelta, timezone
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile
from airport_features import CHANGE, parse_taf, weather_features
from airport_operations_history import SPEC, SPEC_PATH, OUT, PERIODS
from airport_train_v3 import load_airport
from airport_weather import ROOT, atomic_json, stamp

HEADER = re.compile(r'\b([A-Z][A-Z0-9]{3})\s+(\d{6})Z\s+(\d{4})/(\d{4})\s+')
WIND = re.compile(r'(?:^|\s)(\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT\b')


def parse_direction_taf(raw, reference):
    parsed=parse_taf(raw,reference)
    if parsed is None: return None
    text=' '.join(raw.replace('=',' ').split()); header=HEADER.search(text)
    body=text[header.end():]; matches=list(CHANGE.finditer(body))
    parts=[(parsed['prevailing'][0],body[:matches[0].start()] if matches else body)]
    p=1; c=0
    for i,match in enumerate(matches):
        segment=body[match.end():matches[i+1].start() if i+1<len(matches) else len(body)]
        if match[1].startswith('FM'):
            parts.append((parsed['prevailing'][p],segment)); p+=1
        else:
            parts.append((parsed['conditional'][c],segment)); c+=1
    for part,segment in parts:
        wind=WIND.search(segment)
        part['direction']=None if not wind or wind[1]=='VRB' else float(wind[1])%360
        part['variable']=bool(wind and wind[1]=='VRB')
    return parsed


def geometry(path):
    result={a:[] for a in SPEC['airports']}
    with path.open(newline='',encoding='utf-8-sig') as handle:
        for row in csv.DictReader(handle):
            airport=row['airport_ident'][1:]
            if row['airport_ident']!='K'+airport or airport not in result or row['closed']!='0': continue
            if not re.search(r'\b(ASP\w*|CON\w*)\b',row['surface'].upper()): continue
            try: heading=float(row['le_heading_degT'])
            except (ValueError,TypeError): continue
            if not math.isfinite(heading) or not 0<=heading<=360: continue
            result[airport].append({'heading':heading,'ends':[row['le_ident'],row['he_ident']], 'lengthFt':int(row['length_ft'])})
    if any(not v for v in result.values()): raise ValueError('Missing frozen runway headings')
    return result


def directional_features(forecast, target, cutoff, runways):
    wx=weather_features(forecast,target,cutoff)
    if wx is None: return None
    parts=[p for p in forecast['prevailing']+forecast['conditional']
        if p['start']<target+7200 and p['end']>target and p['conditions']['gust'] is not None]
    if not parts or not runways: return None
    east=[]; north=[]; variable=[]; best=[]; mean=[]
    for p in parts:
        gust=p['conditions']['gust']; direction=p['direction']
        if direction is None:
            if not p['variable']: return None
            east.append(0.); north.append(0.); variable.append(gust)
            cross=[gust for _ in runways]  # Unknown direction: conservative upper bound, not measured crosswind.
        else:
            angle=math.radians(direction)
            east.append(gust*math.sin(angle)); north.append(gust*math.cos(angle)); variable.append(0.)
            cross=[abs(gust*math.sin(math.radians(direction-r['heading']))) for r in runways]
        best.append(min(cross)); mean.append(sum(cross)/len(cross))
    direction=[sum(east)/len(east),sum(north)/len(north),max(variable)]
    runway=[max(best),max(mean),max(best)*max(wx[5],wx[12])]
    return {'direction':direction,'runway':runway}


def faa_features(airport, cutoff, days, index, lag_minutes=10):
    # Only information available at the most recent hourly run, with publication lag.
    available=math.floor(cutoff/3600)*3600-lag_minutes*60
    first=datetime.fromtimestamp(available-86400,timezone.utc).date()
    last=datetime.fromtimestamp(available,timezone.utc).date()
    day=first
    while day<=last:
        if day.isoformat() not in days: return None
        day+=timedelta(days=1)
    times,records=index[airport]
    left=bisect_right(times,available-86400); right=bisect_right(times,available)
    recent=records[left:right]
    counts=[sum(r['kind']=='gs' and r['published']>available-21600 for r in recent),
        sum(r['kind']=='gs' for r in recent),
        sum(r['kind']=='gdp' and r['published']>available-21600 for r in recent),
        sum(r['kind']=='gdp' for r in recent),sum(r['cancelled'] for r in recent)]
    decay=math.exp(-(available-recent[-1]['published'])/21600) if recent else 0.
    return [math.log1p(n) for n in counts]+[decay]


def weather_month(month):
    forecasts={a:{} for a in SPEC['airports']}; manifest=[]; qa=Counter()
    # Reproduce the source batching of airport_prepare_v3; DAL was added after v2.
    protocol=json.loads((ROOT/'research/airport-protocol-v3.json').read_text())
    old=protocol['incumbentAirports']; new=[a for a in protocol['airports'] if a not in old]
    groups=[old[i:i+8] for i in range(0,len(old),8)]+[new[i:i+8] for i in range(0,len(new),8)]
    paths=[ROOT/'.airport-data/model-v3'/f'weather-{month}-{i}.zip' for i,g in enumerate(groups) if set(g)&set(SPEC['airports'])]
    if not paths or any(not p.exists() for p in paths): raise ValueError('Missing cached weather month '+month)
    for path in paths:
        raw=path.read_bytes(); manifest.append({'path':str(path.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(raw).hexdigest()})
        with zipfile.ZipFile(path) as archive:
            members=archive.infolist()
            if len(members)>=9999 or sum(m.file_size for m in members)>32*1024*1024: raise ValueError('Unsafe/truncated weather archive')
            for member in members:
                match=re.search(r'TAF([A-Z0-9]{3})_(\d{12})',member.filename)
                if not match or match[1] not in forecasts: continue
                airport=match[1]; reference=datetime.strptime(match[2],'%Y%m%d%H%M').replace(tzinfo=timezone.utc)
                text=archive.read(member).decode('utf-8'); digest=hashlib.sha256(text.encode()).hexdigest()
                try: parsed=parse_direction_taf(text,reference)
                except (ValueError,TypeError): parsed=None
                if parsed and parsed['station']!='K'+airport: parsed=None
                if not parsed:
                    qa['unsupported']+=1
                    parsed={'station':'K'+airport,'issued':reference.timestamp(),'productTime':reference.timestamp(),'start':0,'end':0,'prevailing':[],'conditional':[]}
                parsed['hash']=digest; key=max(parsed['issued'],parsed['productTime'])
                prior=forecasts[airport].get(key)
                if prior and (prior['hash']!=digest or prior.get('ambiguous')):
                    parsed.update(start=0,end=0,prevailing=[],conditional=[],ambiguous=True); qa['ambiguous']+=1
                forecasts[airport][key]=parsed; qa['reports']+=1
    values={a:sorted(fs.values(),key=lambda f:max(f['issued'],f['productTime'])) for a,fs in forecasts.items()}
    return values,manifest,dict(qa)


def main():
    started=datetime.now(timezone.utc); history=json.loads((OUT/'faa-history.json').read_text())
    protocol_hash=hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest()
    if history['protocolSha256']!=protocol_hash: raise ValueError('History protocol mismatch')
    runway_path=OUT/'runways-2022-12-31.csv'; runways=geometry(runway_path)
    days={d['date'] for d in history['days']}; index={}
    for airport in SPEC['airports']:
        records=sorted([r for d in history['days'] for r in d['records'] if r['airport']==airport],key=lambda r:r['published'])
        index[airport]=([r['published'] for r in records],records)
    by_airport={a:[r for r in load_airport(a) if any(SPEC[p][0]<=r['localDate']<=SPEC[p][1] for p in PERIODS)] for a in SPEC['airports']}
    months=sorted({r['localDate'][:7] for rows in by_airport.values() for r in rows})
    output={a:[] for a in SPEC['airports']}; audit={a:Counter() for a in SPEC['airports']}; source=[]; weather_qa={}
    for month in months:
        forecasts,manifest,qa=weather_month(month); source+=manifest; weather_qa[month]=qa
        for airport,rows in by_airport.items():
            fs=forecasts[airport]; times=[max(f['issued'],f['productTime']) for f in fs]
            selected=[r for r in rows if r['localDate'].startswith(month)]
            for row in selected:
                extra={}; audit[airport]['sourceWindows']+=1
                for horizon in SPEC['horizons']:
                    h=str(horizon); wx=row['weather'].get(h)
                    if wx is None: audit[airport][h+'_weatherMissing']+=1; continue
                    cutoff=row['start']-horizon*3600; i=bisect_right(times,cutoff-600)-1
                    forecast=fs[i] if i>=0 else None
                    recreated=weather_features(forecast,row['start'],cutoff)
                    if recreated is None or any(abs(a-b)>1e-7 for a,b in zip(wx,recreated)):
                        # Different archive eligibility excludes every comparator, with an explicit count.
                        audit[airport][h+'_tafVersionMismatch']+=1; continue
                    direction=directional_features(forecast,row['start'],cutoff,runways[airport])
                    faa=faa_features(airport,cutoff,days,index)
                    if direction is None: audit[airport][h+'_directionMissing']+=1; continue
                    if faa is None: audit[airport][h+'_faaHistoryMissing']+=1; continue
                    extra[h]={**direction,'faa':faa,'faaDelayed':faa_features(airport,cutoff,days,index,SPEC['faaLatencySensitivityMinutes'])}
                    audit[airport][h+'_retained']+=1
                    if any(faa): audit[airport][h+'_withRecentFaaActivity']+=1
                output[airport].append({**row,'operations':extra})
            bts=ROOT/'.airport-data/model-v3/airports'/airport/(month+'.json.gz')
            source.append({'path':str(bts.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(bts.read_bytes()).hexdigest()})
        print(json.dumps({'preparedMonth':month}),flush=True)
    source.extend([{'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in (runway_path,OUT/'faa-history.json')])
    source_hash=hashlib.sha256(json.dumps(source,sort_keys=True).encode()).hexdigest()
    code_paths=[Path(__file__),ROOT/'tools/airport_operations_history.py',ROOT/'tools/airport_features.py']
    code={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in code_paths}
    (OUT/'prepared').mkdir(exist_ok=True)
    prepared=[]
    for airport,rows in output.items():
        path=OUT/'prepared'/(airport+'.json.gz')
        path.write_bytes(gzip.compress(json.dumps(rows,separators=(',',':')).encode(),mtime=0))
        prepared.append({'airport':airport,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(rows)})
    atomic_json(OUT/'features-manifest.json',{'version':SPEC['version'],'createdAt':stamp(),'protocolSha256':protocol_hash,
        'sourceSha256':source_hash,'sources':source,'code':code,'prepared':prepared,'audit':{a:dict(c) for a,c in audit.items()},
        'runways':runways,'weatherArchiveQa':weather_qa,'faa':{'validDays':len(days),'missingDays':history['missingDays'],
        'messagesByAirport':{a:len(v[1]) for a,v in index.items()},'downloadBytesCharged':history['downloadBytesCharged'],'attempts':history['attempts']},
        'seconds':(datetime.now(timezone.utc)-started).total_seconds()})
    print(json.dumps({'status':'prepared','audit':{a:dict(c) for a,c in audit.items()}}),flush=True)


if __name__=='__main__': main()
