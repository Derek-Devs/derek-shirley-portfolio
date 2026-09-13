"""Shared FAA advisory-activity features for historical evaluation and live scoring.

Counts are messages, including revisions/cancellations; not active restrictions.
This module is standard-library only and performs no network I/O.
"""
from bisect import bisect_right
from datetime import datetime, timedelta, timezone
import hashlib
import html
import math
import re

FEATURE_VERSION='faa-advisory-activity-v1'
FEATURE_NAMES=['log_gs_messages_6h','log_gs_messages_24h','log_gdp_messages_6h',
    'log_gdp_messages_24h','log_cancellation_messages_24h','recent_advisory_decay']
MAX_BYTES=512*1024
COLLECTION_MINUTE=35
PUBLICATION_LAG_MINUTES=10
ALIASES={'PBI':'DJT'}


def plain(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]*>',' ',value)).split())


def parse_listing(raw,requested,airports,now=None):
    if len(raw)>MAX_BYTES: raise ValueError('FAA advisory listing exceeds byte cap')
    text=raw.decode('utf-8',errors='replace')
    if f'ATCSCC ADVISORIES FOR {requested}' not in plain(text):
        raise ValueError('FAA listing does not confirm the requested date')
    records=[]; seen=set(); total=0; airport_set=set(airports)
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr\s*>',text,re.I|re.S):
        cells=re.findall(r'<td\b[^>]*>(.*?)</td\s*>',row,re.I|re.S)
        if len(cells)!=5 or 'adv_otherdis?' not in cells[0]: continue
        number,element,day,title,sent=map(plain,cells)
        published=datetime.strptime(sent,'%m/%d/%y %H:%M').replace(tzinfo=timezone.utc)
        if published.date().isoformat()!=requested or datetime.strptime(day,'%m/%d/%y').date().isoformat()!=requested:
            raise ValueError('FAA advisory dates disagree')
        if now is not None and published.timestamp()>now: raise ValueError('FAA advisory publication is in the future')
        number=int(number)
        if number in seen: raise ValueError('Duplicate FAA advisory number')
        seen.add(number); total+=1
        source=element.split('/')[0]; airport=ALIASES.get(source,source)
        if airport not in airport_set: continue
        upper=title.upper()
        kind='gs' if re.fullmatch(r'(?:CDM )?(?:GROUND STOP|GS)(?: .*)?',upper) else (
            'gdp' if re.fullmatch(r'(?:CDM )?(?:GROUND DELAY PROGRAM|GDP)(?: .*)?',upper) else None)
        if not kind: continue
        records.append({'airport':airport,'sourceAirport':source,'kind':kind,
            'cancelled':bool(re.search(r'\b(CNX|CANCEL\w*)\b',upper)),
            'published':int(published.timestamp()),'number':number,'title':title})
    if not total: raise ValueError('No validated advisory rows; coverage is unknown')
    return {'date':requested,'totalAdvisories':total,'records':records,
        'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


def available_at(cutoff,lag_minutes=PUBLICATION_LAG_MINUTES):
    phase=COLLECTION_MINUTE*60
    return math.floor((cutoff-phase)/3600)*3600+phase-lag_minutes*60


def required_dates(available):
    first=datetime.fromtimestamp(available-86400,timezone.utc).date()
    last=datetime.fromtimestamp(available,timezone.utc).date(); result=[]
    while first<=last:
        result.append(first.isoformat()); first+=timedelta(days=1)
    return result


def build_index(days,airports):
    records={a:[] for a in airports}
    for day in days:
        for r in day['records']:
            if r['airport'] in records: records[r['airport']].append(r)
    result={}
    for airport,items in records.items():
        items.sort(key=lambda r:r['published']); result[airport]=([r['published'] for r in items],items)
    return result


def features(airport,cutoff,coverage,index,lag_minutes=PUBLICATION_LAG_MINUTES):
    available=available_at(cutoff,lag_minutes)
    if airport not in index or any(day not in coverage for day in required_dates(available)): return None
    times,records=index[airport]
    left=bisect_right(times,available-86400); right=bisect_right(times,available)
    recent=records[left:right]
    counts=[sum(r['kind']=='gs' and r['published']>available-21600 for r in recent),
        sum(r['kind']=='gs' for r in recent),sum(r['kind']=='gdp' and r['published']>available-21600 for r in recent),
        sum(r['kind']=='gdp' for r in recent),sum(r['cancelled'] for r in recent)]
    decay=math.exp(-(available-recent[-1]['published'])/21600) if recent else 0.
    return [math.log1p(n) for n in counts]+[decay]


def snapshot_features(history,airport,cutoff):
    """Reject stale, incomplete, future, or incompatible history; never fill with zeros."""
    if not history or history.get('featureVersion')!=FEATURE_VERSION or history.get('status')!='ok': return None
    fetched=history.get('fetchedAtEpoch',0)
    if not 0<=cutoff-fetched<=5400: return None
    available=available_at(cutoff)
    for day in required_dates(available):
        entry=history.get('days',{}).get(day)
        if not entry or entry.get('fetchedAtEpoch',0)>cutoff: return None
        # A past partial daily fetch cannot establish the rest of that day's coverage.
        end=datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()+86400
        required=min(available,end)
        if entry.get('fetchedAtEpoch',0)<required: return None
    days=list(history['days'].values())
    return features(airport,cutoff,set(history['days']),build_index(days,[airport]))
