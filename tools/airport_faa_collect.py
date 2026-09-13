"""At most two national advisory requests per run, with rolling date coverage."""
from datetime import datetime,timezone
from airport_faa_history import FEATURE_VERSION,available_at,required_dates,parse_listing,snapshot_features


def collect(previous,airports,fetch,now,remaining_ms=None):
    # Snapshot generatedAt is second-resolution; do not make this fetch appear
    # fractionally in its future and suppress every operations probability.
    cutoff=int(now.timestamp()); available=available_at(cutoff)
    days={k:v for k,v in (previous or {}).get('days',{}).items()
        if cutoff-datetime.fromisoformat(k).replace(tzinfo=timezone.utc).timestamp()<3*86400}
    result={'featureVersion':FEATURE_VERSION,'status':'ok','fetchedAtEpoch':cutoff,'days':days,'attemptedAt':now.isoformat()}
    wanted=required_dates(available)
    if len(wanted)>2: raise ValueError('FAA history request bound')
    try:
        for day in wanted:
            end=datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()+86400
            cached=days.get(day)
            if cached and cached.get('fetchedAtEpoch',0)>=end: continue
            if remaining_ms is not None and remaining_ms()<28000: raise TimeoutError('FAA history deferred for publication time')
            parsed=parse_listing(fetch('faaHistory',day=day),day,airports,now=cutoff)
            # A complete cached past day is immutable; current-day pages are refreshed hourly.
            days[day]={**parsed,'fetchedAtEpoch':cutoff}
        if not all(day in days for day in wanted): raise ValueError('FAA history dates incomplete')
    except Exception as error:
        result.update(status='error',error=type(error).__name__)
    return result


def metadata(history):
    return {'status':history['status'],'fetchedAt':datetime.fromtimestamp(history['fetchedAtEpoch'],timezone.utc).isoformat().replace('+00:00','Z'),
        'featureVersion':FEATURE_VERSION,'coveredDates':sorted(history['days']),
        'error':history.get('error'),'description':'Recent ground-stop/GDP advisory messages, including revisions and cancellations; not universal active restrictions.'}
