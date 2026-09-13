"""Bounded monthly labels -> challenger, never automatic production promotion.

Weather collection alone is not learning: BTS outcomes arrive months later.
Two genuinely new outcome months are required for each candidate evaluation.
"""
import calendar
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import tempfile
from zoneinfo import ZoneInfo
from guard import LIMITS, validate_pair


def shift(month, offset):
    year, number = map(int, month.split('-'))
    index = year * 12 + number - 1 + offset
    return f'{index // 12:04d}-{index % 12 + 1:02d}'


def months(first, last):
    result = []
    while first <= last:
        result.append(first); first = shift(first, 1)
    return result


def protocol_for(last_test_month, base):
    # Frozen rolling recipe, with two-day monthly boundary exclusions and full disjoint months.
    def period(start, end):
        first, last = shift(last_test_month, start), shift(last_test_month, end)
        y, m = map(int, last.split('-'))
        return [first + '-03', last + f'-{calendar.monthrange(y, m)[1] - 2:02d}']
    p = {**base, 'version': '3.0.0-monthly', 'train': period(-31, -14),
         'probabilityCalibration': period(-13, -8), 'intervalCalibration': period(-7, -2),
         'test': period(-1, 0), 'selection': 'Fixed v2 boosted learner; no new hyperparameter selection.',
         'previouslySeenStressTest': None}
    return p


def fit_candidate(rows, protocol, incumbent, context):
    import numpy as np
    import airport_train_v2 as train
    from airport_models import predict_batch, serializable
    from airport_features import features
    train.P = protocol
    for row in rows:
        local = datetime.fromtimestamp(row['start'], timezone.utc).astimezone(ZoneInfo(protocol['airports'][row['airport']]))
        row['localDate'] = local.date().isoformat()
        row['block'] = local.date().toordinal() // protocol['bootstrapBlockDays']
    all_splits = train.split(rows, protocol)
    generated = datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
    version = 'airport-monthly-' + protocol['test'][1][:7]
    model = {'version': version, 'generatedAt': generated, 'protocol': protocol, 'models': {},
             'clockSupport': train.original.clock_support(all_splits['train'], protocol['airports']),
             'servingPolicy': incumbent['servingPolicy']}
    evidence = {'version': version, 'generatedAt': generated, 'protocol': protocol, 'airports': {},
                'cohorts': {k: {'airportWindows': len(v), 'flightEvents': sum(r['n'] for r in v)} for k, v in all_splits.items()},
                'status': 'candidate-awaiting-review', 'automaticPromotion': False}
    reports = []
    for direction in ('departures', 'arrivals'):
        splits = {k: [r for r in values if r['direction'] == direction] for k, values in all_splits.items()}
        baseline = train.fit(splits['train'], splits['probabilityCalibration'], direction, 6, 'boosted', False)
        for horizon in protocol['horizons']:
            if context.get_remaining_time_in_millis() < 120000:
                raise TimeoutError('Candidate cannot finish within its fixed runtime budget')
            fitted = train.fit(splits['train'], splits['probabilityCalibration'], direction, horizon, 'boosted')
            calibration = splits['intervalCalibration']; test = splits['test']
            ip = predict_batch(fitted, train.matrix(calibration, horizon))
            tp = predict_batch(fitted, train.matrix(test, horizon))
            bp = predict_batch(baseline, train.matrix(test, horizon, False))
            oldx = np.array([features(r['airport'], r['start'], r['weather'][str(horizon)], incumbent['protocol']['airports']) for r in test])
            oldp = predict_batch(incumbent['models'][f'{direction}_{horizon}']['weather'], oldx)
            wx = np.array([r['weather'][str(horizon)] for r in splits['train']])
            entry = {'weather': fitted, 'baseline': baseline, 'intervals': {}, 'weatherMin': wx.min(axis=0).tolist(), 'weatherMax': wx.max(axis=0).tolist()}
            for airport in protocol['airports']:
                ci = [i for i, r in enumerate(calibration) if r['airport'] == airport]
                ti = [i for i, r in enumerate(test) if r['airport'] == airport]
                if len(ci) < 100 or len(ti) < 50:
                    raise ValueError(f'Insufficient calibration/test coverage for {airport}')
                band = train.calibrate_band([calibration[i] for i in ci], {k: v[ci] for k, v in ip.items()})
                entry['intervals'][airport] = band
                part = [test[i] for i in ti]; train.metrics.horizon = horizon
                report = train.metrics(part, {k: v[ti] for k, v in tp.items()}, {k: v[ti] for k, v in bp.items()}, band)
                report['incumbentBrier'] = train.brier_summary(part, {k: v[ti] for k, v in oldp.items()})
                evidence['airports'].setdefault(airport, {'directions': {}})['directions'].setdefault(direction, {})[str(horizon)] = report
                reports.append(report)
            model['models'][f'{direction}_{horizon}'] = entry
    train.adjust_evidence(reports)
    # Even a recommended challenger is held for review; an aggregate win cannot hide airport regressions.
    evidence['review'] = {'candidateMeanBrier': float(np.mean([r['brier'] for r in reports])),
                          'incumbentMeanBrier': float(np.mean([r['incumbentBrier'] for r in reports])),
                          'regressedSlices': sum(r['brier'] > r['incumbentBrier'] for r in reports),
                          'undercoveredSlices': sum(r['bandCoverage'] < .75 for r in reports)}
    return serializable(model), evidence


def run(s3, bucket, context):
    from handler import read, put, encode
    import airport_prepare_v2 as prep
    index = json.loads(read(s3, bucket, 'history/index.json'))
    incumbent_bytes = read(s3, bucket, 'active/model.json')
    incumbent = json.loads(incumbent_bytes)
    evaluation = json.loads(read(s3, bucket, 'active/evaluation.json'))
    validate_pair(incumbent, evaluation, incumbent_bytes)
    if 'airportModels' in incumbent:
        from learning_v3 import run as expanded_run
        return expanded_run(s3,bucket,context)
    current = datetime.now(timezone.utc).strftime('%Y-%m')
    latest_possible = shift(current, -2)  # A conservative probe, not a claim the release exists.
    available = set(index['months'])
    if len(available) > 72 or not available or not all(len(m) == 7 for m in available):
        raise ValueError('History outside reviewed bounds')
    missing = [m for m in months(min(available), latest_possible) if m not in available][:LIMITS['historyMonthsPerLearningRun']]
    with tempfile.TemporaryDirectory(prefix='airport-learning-') as folder:
        prep.DATA = Path(folder); prep.AIRPORTS = incumbent['protocol']['airports']
        prep.PROTOCOL = {**prep.PROTOCOL, 'airports': prep.AIRPORTS}
        zones = json.loads(read(s3, bucket, 'history/timezones.json'))
        # Strict allowlist plus no redirects and a per-month request cap for research downloads.
        import urllib.request
        from airport_weather import NoRedirect, USER_AGENT
        def bounded_fetch(url, path, limit):
            if path.exists(): return path.read_bytes()
            from urllib.parse import urlparse
            if urlparse(url).scheme != 'https' or urlparse(url).hostname not in ('transtats.bts.gov', 'mesonet.agron.iastate.edu'):
                raise ValueError('Unexpected research provider')
            bounded_fetch.requests += 1
            if bounded_fetch.requests > 10:
                raise ValueError('Research request quota exceeded')
            with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(url, headers={'User-Agent': USER_AGENT}), timeout=35) as response:
                raw = response.read(limit + 1)
            if len(raw) > limit: raise ValueError('Research response too large')
            path.write_bytes(raw); return raw
        bounded_fetch.requests = 0
        prep.fetch = bounded_fetch
        for month in missing:
            if context.get_remaining_time_in_millis() < 180000: break
            try:
                result = prep.prepare_month(month, zones)
            except Exception as error:
                print(json.dumps({'month': month, 'status': 'not-ingested', 'reason': type(error).__name__}))
                break  # No retries and no skipping an unavailable earlier release.
            raw = (prep.DATA / f'joined-{month}.json.gz').read_bytes()
            if len(raw) > 2 * 1024 * 1024: raise ValueError('Derived month too large')
            put(s3, bucket, f'history/joined-{month}.json.gz', raw)
            available.add(month); index['months'] = sorted(available)
            put(s3, bucket, 'history/index.json', encode(index))
        frontier = index['lastEvaluatedMonth']
        last_test = shift(frontier, 2)
        required = months(shift(last_test, -31), last_test)
        if not set(required).issubset(available):
            return {'status': 'waiting-for-new-outcomes', 'nextTestMonths': [shift(frontier, 1), last_test],
                    'missingMonths': [m for m in required if m not in available]}
        protocol = protocol_for(last_test, incumbent['protocol'])
        # Mark the holdout as consumed BEFORE reading labels/fitting. A crash must not permit repeated tuning.
        index['lastEvaluatedMonth'] = last_test
        index['lastAttempt'] = {'period': last_test, 'status': 'reserved', 'protocol': protocol}
        put(s3, bucket, 'history/index.json', encode(index))
        rows = []
        for month in required:
            raw = read(s3, bucket, f'history/joined-{month}.json.gz', 2 * 1024 * 1024)
            with gzip.GzipFile(fileobj=__import__('io').BytesIO(raw)) as compressed:
                expanded = compressed.read(24 * 1024 * 1024 + 1)
            if len(expanded) > 24 * 1024 * 1024: raise ValueError('Expanded research month too large')
            payload = json.loads(expanded)
            if payload['month'] != month: raise ValueError('Research month mismatch')
            rows.extend(payload['rows'])
            if len(rows) > 400000: raise ValueError('Training row cap exceeded')
        model, evidence = fit_candidate(rows, protocol, incumbent, context)
        model_bytes = encode(model)
        evidence['modelSha256'] = hashlib.sha256(model_bytes).hexdigest()
        evidence['sources'] = {'months': required, 'forecastDelivery': 'archived issue time plus 10 minutes; not actual first retrieval'}
        validate_pair(model, evidence, model_bytes)
        prefix = f'candidates/{last_test}'
        put(s3, bucket, prefix + '/model.json', model_bytes)
        put(s3, bucket, prefix + '/evaluation.json', encode(evidence))
        index['lastAttempt']['status'] = 'candidate-awaiting-review'
        put(s3, bucket, 'history/index.json', encode(index))
        return {'status': 'candidate-awaiting-review', 'candidate': prefix, **evidence['review']}
