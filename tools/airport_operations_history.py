"""Bounded public advisory archive acquisition for the local research pilot only."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import threading
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from airport_weather import ROOT, atomic_json, stamp

SPEC_PATH = ROOT/'research/airport-operations-pilot-v1.json'
SPEC = json.loads(SPEC_PATH.read_text())
OUT = ROOT/'.airport-data/operations-pilot-v1'
PERIODS = ('train', 'probabilityCalibration', 'intervalCalibration', 'test', 'previouslySeenStressTest')


def plain(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]*>', ' ', value)).split())


def parse_listing(raw, requested):
    text = raw.decode('utf-8', errors='replace')
    if f'ATCSCC ADVISORIES FOR {requested}' not in plain(text):
        raise ValueError('Archive does not confirm the requested date and complete listing')
    records = []; seen = set(); total = 0
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr\s*>', text, re.I|re.S):
        cells = re.findall(r'<td\b[^>]*>(.*?)</td\s*>', row, re.I|re.S)
        if len(cells) != 5 or 'adv_otherdis?' not in cells[0]:
            continue
        number, element, day, title, sent = map(plain, cells)
        published = datetime.strptime(sent, '%m/%d/%y %H:%M').replace(tzinfo=timezone.utc)
        if published.date().isoformat() != requested or datetime.strptime(day, '%m/%d/%y').date().isoformat() != requested:
            raise ValueError('Advisory send date does not match its daily archive')
        number = int(number)
        if number in seen: raise ValueError('Duplicate advisory number')
        seen.add(number); total += 1
        airport = element.split('/')[0]
        if airport not in SPEC['airports']: continue
        upper = title.upper()
        kind = 'gs' if re.fullmatch(r'(?:CDM )?(?:GROUND STOP|GS)(?: .*)?', upper) else (
            'gdp' if re.fullmatch(r'(?:CDM )?(?:GROUND DELAY PROGRAM|GDP)(?: .*)?', upper) else None)
        if not kind: continue
        link = re.search(r'href\s*=\s*[\"\']([^\"\']+)', cells[0], re.I)
        records.append({'airport':airport, 'kind':kind, 'cancelled':bool(re.search(r'\b(CNX|CANCEL\w*)\b',upper)),
            'published':int(published.timestamp()), 'number':number, 'title':title,
            'path':html.unescape(link[1]) if link else None})
    # Absence is never inferred from an error page or a changed/empty parser result.
    if not total: raise ValueError('No validated advisory rows; leave date unknown')
    return {'date':requested, 'totalAdvisories':total, 'records':records,
        'sha256':hashlib.sha256(raw).hexdigest(), 'bytes':len(raw)}


def requested_dates():
    result=set()
    for period in PERIODS:
        first,last=map(date.fromisoformat,SPEC[period]); first-=timedelta(days=3); last+=timedelta(days=1)
        while first<=last:
            result.add(first.isoformat()); first+=timedelta(days=1)
    return sorted(result)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('Research redirects are disabled')


def main():
    OUT.mkdir(parents=True,exist_ok=True); cache=OUT/'faa-history'; cache.mkdir(exist_ok=True)
    ledger_path=OUT/'http-ledger.json'; budget=SPEC['budget']; started=time.monotonic()
    ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {'attempts':[], 'createdAt':stamp()}
    # Unfinished reservations from an interrupted process retain a full byte charge.
    lock=threading.Lock(); stop=threading.Event(); next_at=[0.]
    errors=[]; completed=[]
    def get(day):
        path=cache/(day+'.html')
        if path.exists(): return parse_listing(path.read_bytes(),day)
        with lock:
            if stop.is_set(): return {'date':day,'error':'download stopped'}
            if any(a['date']==day for a in ledger['attempts']): return {'date':day,'error':'prior attempt not retried'}
            charged=sum(a.get('bytes',budget['maxResponseBytes']) for a in ledger['attempts'])
            if len(ledger['attempts'])>=budget['maxHttpAttempts'] or charged+budget['maxResponseBytes']>budget['maxTotalDownloadBytes'] or time.monotonic()-started>budget['maxRuntimeSeconds']:
                stop.set(); return {'date':day,'error':'research budget exhausted'}
            at=max(time.monotonic(),next_at[0]); next_at[0]=at+budget['minimumRequestIntervalSeconds']
            entry={'date':day,'reservedAt':stamp(),'status':'reserved'}
            ledger['attempts'].append(entry); atomic_json(ledger_path,ledger)
        # At most two workers; this subsecond rate limiter is not a user-facing wait.
        time.sleep(max(0,at-time.monotonic()))
        url='https://www.fly.faa.gov/adv/adv_list?'+urlencode({'whichAdvisories':'ATCSCC','advisoryCategory':'All','date':day})
        raw=None
        try:
            if stop.is_set(): raise ValueError('download stopped')
            with build_opener(NoRedirect).open(Request(url,headers={'User-Agent':'DerekDevs-AirportOperationsResearch/0.1'}),timeout=20) as response:
                raw=response.read(budget['maxResponseBytes']+1)
            if len(raw)>budget['maxResponseBytes']: raise ValueError('response byte limit exceeded')
            result=parse_listing(raw,day)
            path.write_bytes(raw)
            status='complete'
        except Exception as exc:
            if isinstance(exc,HTTPError) and exc.code in (401,403,429): stop.set()
            result={'date':day,'error':str(exc)}; status='failed'
        with lock:
            entry.update(status=status,bytes=len(raw) if raw is not None else budget['maxResponseBytes'],completedAt=stamp())
            if status=='failed': entry['error']=result['error']
            atomic_json(ledger_path,ledger)
        return result
    dates=requested_dates()
    print(json.dumps({'status':'downloading','requestedDates':len(dates),'maximumAttempts':budget['maxHttpAttempts']}),flush=True)
    with ThreadPoolExecutor(max_workers=budget['maxConcurrentRequests']) as pool:
        for i,result in enumerate(pool.map(get,dates)):
            (errors if 'error' in result else completed).append(result)
            if (i+1)%100==0: print(json.dumps({'processed':i+1,'validDays':len(completed),'missingDays':len(errors)}),flush=True)
    payload={'version':SPEC['version'],'createdAt':stamp(),'protocolSha256':hashlib.sha256(SPEC_PATH.read_bytes()).hexdigest(),
        'seconds':round(time.monotonic()-started,2),'days':completed,'missingDays':errors,
        'attempts':len(ledger['attempts']),'downloadBytesCharged':sum(a.get('bytes',budget['maxResponseBytes']) for a in ledger['attempts'])}
    atomic_json(OUT/'faa-history.json',payload)
    print(json.dumps({k:v for k,v in payload.items() if k not in ('days','missingDays')}|{'validDays':len(completed),'missingDays':len(errors)}),flush=True)


if __name__=='__main__': main()
