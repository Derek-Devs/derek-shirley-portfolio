"""Bounded free-data preparation for the frozen airport experiment protocol."""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
from bisect import bisect_right
from collections import Counter
from datetime import datetime,timedelta,timezone
import calendar
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
import zipfile
import numpy as np
import pandas as pd
from timezonefinder import TimezoneFinder
from airport_weather import ROOT,USER_AGENT,atomic_json,stamp
from airport_features import parse_taf,weather_features

PROTOCOL = json.loads((ROOT/'research/airport-protocol-v2.json').read_text())
AIRPORTS = PROTOCOL['airports']
DATA = ROOT/'.airport-data/model-v2'
DATA.mkdir(parents=True,exist_ok=True)


def fetch(url, path, limit):
    if path.exists(): return path.read_bytes()
    if urllib.parse.urlparse(url).hostname not in {'transtats.bts.gov','mesonet.agron.iastate.edu','davidmegginson.github.io','raw.githubusercontent.com'}:
        raise ValueError('Research source is not allowlisted')
    request = urllib.request.Request(url,headers={'User-Agent':USER_AGENT})
    with urllib.request.urlopen(request,timeout=55) as response:
        raw = response.read(limit+1)
    if len(raw)>limit: raise ValueError('Research response exceeds byte cap')
    temp=path.with_suffix(path.suffix+'.tmp'); temp.write_bytes(raw); temp.replace(path)
    return raw


def timezone_map():
    path=DATA/'timezones.json'
    if path.exists(): return json.loads(path.read_text())
    raw=fetch('https://davidmegginson.github.io/ourairports-data/airports.csv',DATA/'airports.csv',20*1024*1024)
    finder=TimezoneFinder()
    result={}
    for airport in csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))):
        code=airport['iata_code']
        if not code or airport['iso_country'] not in {'US','PR','VI','GU','MP','AS'}: continue
        if code in result and airport['scheduled_service']!='yes': continue
        zone=finder.timezone_at(lng=float(airport['longitude_deg']),lat=float(airport['latitude_deg']))
        if zone: result[code]=zone
    result.update(AIRPORTS)
    atomic_json(path,result)
    return result


def monthly_flights(month,zones):
    path=DATA/f'flights-{month}.csv.gz'
    manifest_path=DATA/f'flights-{month}-source.json'
    if path.exists(): return pd.read_csv(path),json.loads(manifest_path.read_text())
    year,number=map(int,month.split('-'))
    url=f'https://transtats.bts.gov/PREZIP/On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{number}.zip'
    download=DATA/f'bts-{month}.zip'
    raw=fetch(url,download,96*1024*1024)
    cols=['FlightDate','Origin','Dest','CRSDepTime','CRSArrTime','CRSElapsedTime','Cancelled','Diverted','DepDelay','ArrDelay','Reporting_Airline','Flight_Number_Reporting_Airline']
    retained=[]; qa=Counter()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members=[m for m in archive.infolist() if m.filename.lower().endswith('.csv')]
        if len(members)!=1 or members[0].file_size>768*1024*1024: raise ValueError('BTS archive schema/size changed')
        with archive.open(members[0]) as handle:
            for chunk in pd.read_csv(handle,usecols=cols,chunksize=150000,dtype={'FlightDate':'str','Origin':'str','Dest':'str','Reporting_Airline':'str'}):
                qa['sourceFlightRows']+=len(chunk)
                aliases=PROTOCOL.get('outcomeAliases',{})
                if aliases:
                    chunk['Origin']=chunk.Origin.replace(aliases)
                    chunk['Dest']=chunk.Dest.replace(aliases)
                retained.append(chunk[chunk.Origin.isin(AIRPORTS)|chunk.Dest.isin(AIRPORTS)])
    frame=pd.concat(retained,ignore_index=True)
    qa['selectedRouteRows']=len(frame)
    key=['FlightDate','Origin','Dest','CRSDepTime','Reporting_Airline','Flight_Number_Reporting_Airline']
    dedup=frame.drop_duplicates(key).copy(); qa['duplicates']=len(frame)-len(dedup); frame=dedup
    clock=pd.to_numeric(frame.CRSDepTime,errors='coerce')
    valid_clock=clock.between(0,2400)&((clock%100)<60)&((clock<2400)|(clock==2400))
    local=pd.to_datetime(frame.FlightDate.str[:10],errors='coerce')+pd.to_timedelta((clock//100)*60+clock%100,unit='m')
    frame['depUtc']=pd.Series(pd.NaT,index=frame.index,dtype='datetime64[ns, UTC]')
    frame['originZone']=frame.Origin.map(zones)
    for zone,index in frame.groupby('originZone').groups.items():
        frame.loc[index,'depUtc']=local.loc[index].dt.tz_localize(zone,ambiguous='NaT',nonexistent='NaT').dt.tz_convert('UTC')
    frame.loc[~valid_clock,'depUtc']=pd.NaT
    frame['arrUtc']=frame.depUtc+pd.to_timedelta(pd.to_numeric(frame.CRSElapsedTime,errors='coerce'),unit='m')
    output=[]
    for airport,zone in AIRPORTS.items():
        for direction,field,event_col,delay_col in [('departures','Origin','depUtc','DepDelay'),('arrivals','Dest','arrUtc','ArrDelay')]:
            rows=frame[frame[field]==airport].copy(); qa[f'{airport}_{direction}_source']=len(rows)
            local_event=rows[event_col].dt.tz_convert(zone)
            if direction=='arrivals':
                expected=(local_event.dt.hour*100+local_event.dt.minute).fillna(-1)
                reported=pd.to_numeric(rows.CRSArrTime,errors='coerce').replace(2400,0)
                matching=(expected==reported)&rows.CRSElapsedTime.between(0,1440)
                qa[f'{airport}_{direction}_clockMismatch']=int((~matching).sum())
                local_event=local_event.where(matching)
            qa[f'{airport}_{direction}_missingTime']=int(local_event.isna().sum())
            boundary=PROTOCOL['monthBoundaryExclusionDays']
            eligible=local_event.notna()&(local_event.dt.strftime('%Y-%m')==month)&(local_event.dt.day>boundary)&(local_event.dt.day<=calendar.monthrange(year,number)[1]-boundary)
            qa[f'{airport}_{direction}_boundaryOrTimeExcluded']=int((~eligible).sum())
            rows=rows[eligible].copy(); local_event=local_event[eligible]
            slots=local_event.dt.tz_localize(None).dt.floor('2h').dt.tz_localize(zone,ambiguous='NaT',nonexistent='NaT').dt.tz_convert('UTC')
            rows['start']=slots.astype('int64')//10**9
            rows=rows[slots.notna()].copy()
            cancelled=rows.Cancelled==1
            diverted=(rows.Diverted==1)&~cancelled if direction=='arrivals' else pd.Series(False,index=rows.index)
            delay=pd.to_numeric(rows[delay_col],errors='coerce')
            rows['cancelled']=cancelled.astype(int); rows['diverted']=diverted.astype(int)
            rows['delayed']=((delay>=15)&~cancelled&~diverted).astype(int)
            rows['onTime']=((delay<15)&~cancelled&~diverted).astype(int)
            rows['unknown']=(delay.isna()&~cancelled&~diverted).astype(int)
            rows['n']=1
            aggregated=rows.groupby('start')[['n','cancelled','diverted','delayed','onTime','unknown']].sum().reset_index()
            aggregated['airport']=airport; aggregated['direction']=direction
            output.append(aggregated)
    result=pd.concat(output,ignore_index=True)
    result.to_csv(path,index=False,compression='gzip')
    manifest={'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'downloadedAt':stamp(),'qa':dict(qa)}
    atomic_json(manifest_path,manifest)
    # Only remove this command's own bounded download, after the derived data and hash are durable.
    if download.resolve().is_relative_to(DATA.resolve()): download.unlink()
    return result,manifest


def weather_batch(month, airports, batch):
    year,number=map(int,month.split('-')); start=datetime(year,number,1,tzinfo=timezone.utc)
    end=(start.replace(day=28)+timedelta(days=4)).replace(day=1)
    stations={a:PROTOCOL.get('historicalStations',{}).get(a,PROTOCOL.get('stations',{}).get(a,'K'+a)) if month<='2026-06' else PROTOCOL.get('stations',{}).get(a,'K'+a) for a in airports}
    permitted={a:{station} for a,station in stations.items()}
    if month=='2026-07':
        for a in airports:
            if a in PROTOCOL.get('historicalStations',{}): permitted[a].add(PROTOCOL['historicalStations'][a])
    products={station[1:]:a for a,values in permitted.items() for station in sorted(values)}
    params={'pil':','.join('TAF'+suffix for suffix in products),'fmt':'zip','sdate':stamp(start-timedelta(days=2)),'edate':stamp(end+timedelta(days=1)),'limit':9999}
    url='https://mesonet.agron.iastate.edu/cgi-bin/afos/retrieve.py?'+urllib.parse.urlencode(params)
    raw=fetch(url,DATA/f'weather-{month}-{batch}.zip',16*1024*1024)
    result={airport:[] for airport in airports}; qa=Counter()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        if len(archive.infolist())>=9999 or sum(m.file_size for m in archive.infolist())>32*1024*1024:
            raise ValueError('Weather archive exceeds query cap or is truncated')
        for member in archive.infolist():
            match=re.search(r'TAF([A-Z0-9]{3})_(\d{12})',member.filename)
            if not match or match[1] not in products: continue
            airport=products[match[1]]
            reference=datetime.strptime(match[2],'%Y%m%d%H%M').replace(tzinfo=timezone.utc)
            text=archive.read(member).decode('utf-8',errors='strict')
            try: parsed=parse_taf(text,reference)
            except (ValueError,TypeError): parsed=None
            qa['reports']+=1
            if parsed and parsed['station'] not in permitted[airport]:
                qa['stationMismatch']+=1
                parsed=None
            if not parsed:
                qa['unsupported']+=1
                parsed={'station':stations[airport],'issued':reference.timestamp(),'productTime':reference.timestamp(),'start':0,'end':0,'prevailing':[],'conditional':[]}
            parsed['hash']=hashlib.sha256(text.encode()).hexdigest()
            result[airport].append(parsed)
    for airport,forecasts in result.items():
        unique={}
        for forecast in forecasts:
            key=max(forecast['issued'],forecast['productTime'])
            if key in unique and unique[key]['hash']!=forecast['hash']:
                qa['ambiguousIssueVersions']+=1
                forecast={**forecast,'start':0,'end':0,'prevailing':[],'conditional':[]}
            unique[key]=forecast
        result[airport]=sorted(unique.values(),key=lambda f:max(f['issued'],f['productTime']))
    return result,{'url':url,'sha256':hashlib.sha256(raw).hexdigest(),'qa':dict(qa)}



def monthly_weather(month):
    result={}; manifests=[]; qa=Counter(); codes=list(AIRPORTS)
    for batch,offset in enumerate(range(0,len(codes),PROTOCOL['maxWeatherAirportsPerRequest'])):
        values,manifest=weather_batch(month,codes[offset:offset+PROTOCOL['maxWeatherAirportsPerRequest']],batch)
        result.update(values); manifests.append(manifest); qa.update(manifest['qa'])
    return result,{'batches':manifests,'qa':dict(qa)}

def prepare_month(month,zones):
    path=DATA/f'joined-{month}.json.gz'
    if path.exists(): return json.loads(gzip.decompress(path.read_bytes()))
    flights,bts=monthly_flights(month,zones)
    weather,wx_source=monthly_weather(month)
    time_index={a:[max(f['issued'],f['productTime']) for f in fs] for a,fs in weather.items()}
    joined=[]; qa=Counter()
    for row in flights.to_dict('records'):
        qa['airportWindows']+=1
        qa[f"{row['airport']}_{row['direction']}_candidateWindows"]+=1
        if row['n']<PROTOCOL['minimumScheduledFlightsPerWindow'] or row['unknown']:
            qa['lowCountOrUnknownWindows']+=1
            qa[f"{row['airport']}_{row['direction']}_lowCountOrUnknown"]+=1; continue
        vectors={}; delayed_vectors={}
        for h in PROTOCOL['horizons']:
            cutoff=row['start']-h*3600
            def vector(lag):
                index=bisect_right(time_index[row['airport']],cutoff-lag*60)-1
                return weather_features(weather[row['airport']][index],row['start'],cutoff) if index>=0 else None
            vectors[str(h)]=vector(PROTOCOL['availabilityLagMinutes'])
            delayed_vectors[str(h)]=vector(PROTOCOL['availabilitySensitivityMinutes'])
            if vectors[str(h)] is None:
                qa[f'missingFullForecast_{h}']+=1
                qa[f"{row['airport']}_{row['direction']}_missing_{h}"]+=1
        if any(v is None for v in vectors.values()):
            qa['excludedCommonCohortWindows']+=1; continue
        qa[f"{row['airport']}_{row['direction']}_included"]+=1
        joined.append({**row,'weather':vectors,'weatherDelayed':delayed_vectors})
    result={'month':month,'rows':joined,'qa':dict(qa),'sources':[bts,wx_source]}
    path.write_bytes(gzip.compress(json.dumps(result,separators=(',',':')).encode(),mtime=0))
    print(json.dumps({'month':month,'eligibleWindows':len(joined),'excludedWindows':qa['excludedCommonCohortWindows'],'weather':wx_source['qa']}),flush=True)
    return result



def main():
    from concurrent.futures import ThreadPoolExecutor,as_completed
    months=[f'{year}-{month:02d}' for year in (2023,2024,2025) for month in range(1,13) if year<2025 or month<=9]
    # The new final holdout is kept separate; it is prepared but never read by selection.
    months += [f'2026-{month:02d}' for month in range(1,7)]
    if len(months)>PROTOCOL['maxResearchMonths']: raise ValueError('Research month cap exceeded')
    zones=timezone_map(); inventory=[]
    with ThreadPoolExecutor(max_workers=PROTOCOL['maxConcurrentMonths']) as pool:
        futures={pool.submit(prepare_month,month,zones):month for month in months}
        for future in as_completed(futures):
            result=future.result()
            inventory.append({'month':result['month'],'rows':len(result['rows']),'qa':result['qa'],'sources':result['sources']})
            atomic_json(DATA/'inventory.json',sorted(inventory,key=lambda row:row['month']))
            print(f'Completed {len(inventory)}/{len(months)} months',flush=True)
    print('V2 preparation complete.',flush=True)

if __name__=='__main__': main()
