"""Narrow the existing service to U.S. geography; preserve models, timestamps and spending controls."""
import argparse
import copy
import json
import sys

from manage import ROOT, session_for, inspect, encoded
from template import build

sys.path.insert(0, str(ROOT / 'tools'))
from airport_weather import scope_catalog, scope_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--account-id', required=True)
    parser.add_argument('--stack', default='portfolio-airport-weather')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    session = session_for(args)
    out = inspect(session, args)
    s3 = session.client('s3'); cf = session.client('cloudformation')

    def get(key):
        response = s3.get_object(Bucket=out['Bucket'], Key=key, ExpectedBucketOwner=args.account_id)
        try:
            raw = response['Body'].read(16 * 1024 * 1024 + 1)
        finally:
            response['Body'].close()
        if len(raw) > 16 * 1024 * 1024:
            raise ValueError('Object exceeds reviewed size')
        return json.loads(raw), response['ETag']

    catalog, catalog_etag = get('public/airports.json')
    scoped = scope_catalog(catalog)
    local = json.loads((ROOT / 'public/data/airport-weather/airports.json').read_text(encoding='utf-8'))
    if not 100 <= len(scoped['airports']) <= 1200:
        raise ValueError('U.S. catalog outside reviewed scope')
    if {a['icao'] for a in scoped['airports']} != {a['icao'] for a in local['airports']}:
        raise ValueError('Cloud and reviewed local U.S. catalogs differ')
    manifest, manifest_etag = get('public/latest.json')
    snapshot, _ = get('state/latest.json')
    if snapshot['generatedAt'] != manifest['generatedAt']:
        raise ValueError('Collection changed during inspection; retry after it finishes')
    projected = scope_snapshot(snapshot, scoped)
    summary = copy.deepcopy(manifest)
    summary['scope'] = projected['scope']
    summary['coverage'].update({
        'airports': len(projected['stations']),
        'observations': sum(bool(s['observation']) for s in projected['stations'].values()),
        'forecasts': sum(bool(s['tafs']) for s in projected['stations'].values()),
    })
    # Only the viewer path allowlist changes. Keep every other deployed resource and parameter.
    deployed = cf.get_template(StackName=args.stack)['TemplateBody']
    if isinstance(deployed, str): deployed = json.loads(deployed)
    proposed = copy.deepcopy(deployed)
    proposed['Resources']['PathGuard']['Properties']['FunctionCode'] = build()['Resources']['PathGuard']['Properties']['FunctionCode']
    review = {'scope': scoped['scope'], 'before': len(catalog['airports']), 'after': len(scoped['airports']),
              'coverage': summary['coverage'], 'weatherTimestampPreserved': summary['generatedAt'],
              'templateChange': 'PathGuard.FunctionCode only', 'modelsChanged': False, 'spendingControlsChanged': False}
    folder = ROOT / '.airport-data/aws-package'
    (folder / 'us-scope-review.json').write_bytes(encoded(review))
    if not args.apply:
        print(json.dumps({'status': 'reviewed-not-applied', **review})); return

    def put(key, value, etag):
        s3.put_object(Bucket=out['Bucket'], Key=key, Body=encoded(value), IfMatch=etag,
                      ExpectedBucketOwner=args.account_id, ServerSideEncryption='AES256',
                      ContentType='application/json', CacheControl='public,max-age=60')

    (folder / 'us-scope-previous-catalog.json').write_bytes(encoded(catalog))
    put('public/airports.json', scoped, catalog_etag)
    # This only narrows the counts for existing immutable weather files; it does not refresh their age.
    put('public/latest.json', summary, manifest_etag)
    if proposed != deployed:
        stack = cf.describe_stacks(StackName=args.stack)['Stacks'][0]
        cf.update_stack(StackName=args.stack, TemplateBody=json.dumps(proposed),
                        Parameters=[{'ParameterKey': p['ParameterKey'], 'UsePreviousValue': True} for p in stack['Parameters']],
                        Capabilities=['CAPABILITY_IAM'])
    invalidation = session.client('cloudfront').create_invalidation(DistributionId=out['DistributionId'],
        InvalidationBatch={'Paths': {'Quantity': 2, 'Items': ['/airports.json', '/latest.json']},
                           'CallerReference': 'us-scope-' + catalog_etag.strip('"')})
    print(json.dumps({'status': 'catalog-narrowed', 'invalidation': invalidation['Invalidation']['Id'], **review}))


if __name__ == '__main__': main()
