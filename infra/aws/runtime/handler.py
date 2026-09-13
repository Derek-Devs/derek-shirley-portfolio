"""Hourly shared snapshots and monthly candidate research; no public invocation endpoint."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent / 'tools'))
from guard import LIMITS, reserve, validate_pair, validate_publication


def clients():
    import boto3
    from botocore.config import Config
    config = Config(retries={'total_max_attempts': 1}, connect_timeout=5, read_timeout=25)
    return boto3.client('s3', config=config), boto3.client('dynamodb', config=config)


def read(s3, bucket, key, cap=16 * 1024 * 1024):
    response = s3.get_object(Bucket=bucket, Key=key)
    if response['ContentLength'] > cap:
        response['Body'].close()
        raise ValueError('Stored object exceeds cap')
    try:
        value = response['Body'].read(cap + 1)
    finally:
        response['Body'].close()
    if len(value) > cap:
        raise ValueError('Stored object exceeds cap')
    return value


def put(s3, bucket, key, body, public=False):
    args = {'Bucket': bucket, 'Key': key, 'Body': body, 'ServerSideEncryption': 'AES256',
            'ContentType': 'application/json' if key.endswith('.json') else 'application/gzip'}
    if public:
        args['CacheControl'] = 'public,max-age=60' if key == 'public/latest.json' else 'public,max-age=86400,immutable'
    s3.put_object(**args)


def encode(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()


def publish(s3, bucket, snapshot, files):
    validate_publication(files)
    archive = gzip.compress(encode(snapshot), mtime=0)
    if len(archive) > LIMITS['maximumCompressedArchiveBytes']:
        raise ValueError('Forecast archive exceeds cap')
    generation = datetime.fromisoformat(snapshot['generatedAt'].replace('Z', '+00:00')).strftime('%Y%m%dT%H0000Z')
    prefix = f'snapshots/{generation}'
    summary = json.loads(files['latest.json'])
    summary['dataPrefix'] = prefix
    # Any partial upload stays unreachable. The small manifest is the only mutable public pointer.
    for name, body in files.items():
        if name != 'latest.json':
            put(s3, bucket, f'public/{prefix}/{name}', body, True)
    put(s3, bucket, f'archive/{generation}.json.gz', archive)
    put(s3, bucket, 'state/latest.json', encode(snapshot))
    put(s3, bucket, 'public/latest.json', encode(summary), True)
    return {'generatedAt': snapshot['generatedAt'], 'airports': len(snapshot['stations']), 'files': len(files)}


def collect(s3, bucket, context):
    import airport_weather as weather
    import airport_predict as predictor
    model_bytes = read(s3, bucket, 'active/model.json')
    evaluation_bytes = read(s3, bucket, 'active/evaluation.json')
    model, evaluation = json.loads(model_bytes), json.loads(evaluation_bytes)
    validate_pair(model, evaluation, model_bytes)
    catalog_bytes = read(s3, bucket, 'public/airports.json')
    catalog = weather.scope_catalog(json.loads(catalog_bytes))
    catalog_bytes = encode(catalog)
    if not 100 <= len(catalog['airports']) <= LIMITS['maximumCatalogAirports']:
        raise ValueError('Catalog outside reviewed capacity')
    with tempfile.TemporaryDirectory(prefix='airport-') as folder:
        root = Path(folder)
        weather.STATE = root / 'state'; weather.PUBLIC = root / 'public'
        predictor.STATE = weather.STATE; predictor.PUBLIC = weather.PUBLIC
        weather.PUBLIC.mkdir(); weather.STATE.mkdir()
        for name, data in [('airports.json', catalog_bytes), ('model.json', model_bytes), ('evaluation.json', evaluation_bytes)]:
            (weather.PUBLIC / name).write_bytes(data)
        # Catalog pins the optional pair; no probe of a missing S3 key is required.
        # The existing active/* read permission covers these immutable versions.
        release = catalog.get('operationsRelease')
        if release:
            import re
            release_bytes = encode(release)
            version = release['version']
            if not re.fullmatch(r'airport-operations-us-v\d+', version): raise ValueError('Invalid operations release')
            folder = weather.PUBLIC / 'operations'; folder.mkdir()
            pair = {}
            for name in ('model.json', 'evaluation.json'):
                raw = read(s3, bucket, f'active/operations/versions/{version}/{name}')
                if hashlib.sha256(raw).hexdigest() != release['files'][name]: raise ValueError('Operations release hash mismatch')
                (folder / name).write_bytes(raw); pair[name] = json.loads(raw)
            validate_pair(pair['model.json'], pair['evaluation.json'], (folder / 'model.json').read_bytes())
            (folder / 'release.json').write_bytes(release_bytes)
        # Required even at bootstrap: an explicit empty seed prevents accidentally losing retrieval history.
        (weather.STATE / 'latest.json').write_bytes(read(s3, bucket, 'state/latest.json'))
        weather.refresh(context.get_remaining_time_in_millis if context else None)
        if context.get_remaining_time_in_millis() < 15000:
            raise TimeoutError('Insufficient time to publish a complete generation')
        snapshot = json.loads((weather.STATE / 'latest.json').read_text(encoding='utf-8'))
        files = {p.relative_to(weather.PUBLIC).as_posix(): p.read_bytes() for p in weather.PUBLIC.rglob('*.json')
                 if p.name not in ('model.json', 'airports.json')}
        return publish(s3, bucket, snapshot, files)


def main(event, context):
    job = os.environ['JOB']
    # The scheduler passes a fixed literal; requests cannot request arbitrary jobs or downloads.
    if event != {'job': job}:
        return {'status': 'rejected-event'}
    s3, ddb = clients()
    try:
        reserve(ddb, os.environ['CONTROL_TABLE'], job)
        # A paid-plan upgrade must never silently authorize this Free-plan deployment.
        from guard import check_free_account
        check_free_account(os.environ['ACCOUNT_ID'])
    except Exception as error:
        # A missing, corrupt, exhausted or unreachable ledger disables work.
        print(json.dumps({'status': 'paused', 'reason': type(error).__name__, 'job': job}))
        return {'status': 'paused'}
    if job == 'collector':
        result = collect(s3, os.environ['DATA_BUCKET'], context)
    else:
        from learning import run
        result = run(s3, os.environ['DATA_BUCKET'], context)
    print(json.dumps({'job': job, **result}))
    return result
