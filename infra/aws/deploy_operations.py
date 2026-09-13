"""Install context collection using the existing stack, quotas, model and operating lease."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
from manage import ROOT, session_for, inspect, encoded

PACKAGE = ROOT / '.airport-data/aws-package'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['runtime', 'collect', 'verify'])
    parser.add_argument('--profile', required=True)
    parser.add_argument('--account-id', required=True)
    args = parser.parse_args(); args.stack = 'portfolio-airport-weather'
    session = session_for(args); out = inspect(session, args)
    s3 = session.client('s3'); cf = session.client('cloudformation')
    ddb = session.client('dynamodb'); lam = session.client('lambda')

    def read(key, cap=16 * 1024 * 1024):
        result = s3.get_object(Bucket=out['Bucket'], Key=key, ExpectedBucketOwner=args.account_id)
        if result['ContentLength'] > cap:
            result['Body'].close(); raise ValueError('Object exceeds cap')
        with result['Body'] as body: raw = body.read(cap + 1)
        if len(raw) > cap: raise ValueError('Object exceeds cap')
        return raw

    model = read('active/model.json'); evidence = read('active/evaluation.json')
    for name, raw in [('model', model), ('evaluation', evidence)]:
        if raw != (ROOT / f'public/data/airport-weather/{name}.json').read_bytes():
            raise ValueError('Active evidence changed; review before proceeding')
    control = ddb.get_item(TableName=out['ControlTable'], Key={'id': {'S': 'control'}}, ConsistentRead=True)['Item']
    now = datetime.now(timezone.utc)
    if not control.get('enabled', {}).get('BOOL') or int(control.get('authorizedUntil', {}).get('N', 0)) <= now.timestamp():
        raise ValueError('Operating lease is disabled or expired; this command cannot renew it')
    if args.command == 'runtime':
        receipt = json.loads((PACKAGE / 'build-receipt.json').read_text())
        inputs = json.loads((PACKAGE / 'build-inputs.json').read_text())
        image = receipt.get('imageUri', '')
        pattern = re.escape(args.account_id) + r'\.dkr\.ecr\.us-east-2\.amazonaws\.com/portfolio-airport-weather@sha256:[a-f0-9]{64}'
        if receipt.get('buildStatus') != 'SUCCEEDED' or not re.fullmatch(pattern, image):
            raise ValueError('A successful immutable build is required')
        if receipt.get('sourceSha256') != inputs['sourceSha256']:
            raise ValueError('Build receipt and source disagree')
        for name, digest in inputs['files'].items():
            if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest:
                raise ValueError('Build input changed after review: ' + name)
        if 'tools/airport_operations.py' not in inputs['files']:
            raise ValueError('Operations collector is missing from the image')
        stack = cf.describe_stacks(StackName=args.stack)['Stacks'][0]
        before = {p['ParameterKey']: p['ParameterValue'] for p in stack['Parameters']}
        review = {'oldParameters': before, 'newImage': image, 'sourceSha256': inputs['sourceSha256'],
                  'monetaryAndComputeLimitsUnchanged': True, 'operatingControl': control,
                  'modelSha256': hashlib.sha256(model).hexdigest(), 'evaluationSha256': hashlib.sha256(evidence).hexdigest(),
                  'freeProviderRequests': {'ordinaryPerRun': 3, 'maximumPerRun': 4, 'runways': 'monthly cached attempt'},
                  'reviewedAt': now.isoformat()}
        (PACKAGE / 'operations-runtime-review.json').write_bytes(encoded(review))
        if before['ImageUri'] == image:
            print('{"status":"runtime-already-current"}'); return
        parameters = [{'ParameterKey': key, **({'ParameterValue': image} if key == 'ImageUri' else {'UsePreviousValue': True})} for key in before]
        response = cf.update_stack(StackName=args.stack, UsePreviousTemplate=True, Parameters=parameters, Capabilities=['CAPABILITY_IAM'])
        print(json.dumps({'status': 'updating-operations-runtime', 'stackId': response['StackId']})); return
    if args.command == 'collect':
        key = f'slot/collector/{now.strftime("%Y-%m-%dT%H")}'
        if ddb.get_item(TableName=out['ControlTable'], Key={'id': {'S': key}}, ConsistentRead=True).get('Item'):
            print('{"status":"hour-already-reserved","action":"wait for the next permitted hour; quota unchanged"}'); return
        from botocore.config import Config
        lam = session.client('lambda', config=Config(read_timeout=140, retries={'total_max_attempts': 1}))
        response = lam.invoke(FunctionName=args.stack + '-collector', InvocationType='RequestResponse', Payload=encoded({'job': 'collector'}))
        with response['Payload'] as payload: result = payload.read(65537)
        (PACKAGE / 'operations-collection.json').write_bytes(result)
        if response.get('FunctionError'): raise RuntimeError(result.decode())
        print(result.decode()); return
    manifest = json.loads(read('public/latest.json')); snapshot = json.loads(read('state/latest.json'))
    if manifest['generatedAt'] != snapshot['generatedAt']:
        raise ValueError('Publication in progress')
    if any(snapshot.get('sources', {}).get(kind, {}).get('status') != 'ok' for kind in ('faa', 'runways')):
        raise ValueError('New context is not available in the live snapshot yet')
    review = json.loads((PACKAGE / 'operations-runtime-review.json').read_text())
    if control != review['operatingControl']:
        raise ValueError('Operating controls changed')
    stack = cf.describe_stacks(StackName=args.stack)['Stacks'][0]
    parameters = {p['ParameterKey']: p['ParameterValue'] for p in stack['Parameters']}
    if parameters != {**review['oldParameters'], 'ImageUri': review['newImage']}:
        raise ValueError('Stack parameters changed beyond the reviewed image')
    deployed = lam.get_function(FunctionName=args.stack + '-collector')
    if deployed['Code'].get('ResolvedImageUri') != review['newImage']:
        raise ValueError('Collector is not using the reviewed image')
    if deployed['Configuration']['MemorySize'] != 1024 or deployed['Configuration']['Timeout'] != 120:
        raise ValueError('Collector compute settings changed')
    airports = json.loads(read('public/airports.json'))['airports']
    runways = lambda code: snapshot['stations'][code].get('runways', {}).get('runways', [])
    proof = {'generatedAt': snapshot['generatedAt'], 'sources': snapshot['sources'],
             'runwayAirports': sum(bool(runways(a['icao'])) for a in airports),
             'majorRunwayAirports': sum(bool(runways(a['icao'])) for a in airports if a['size'] == 'large_airport'),
             'operatingControlsUnchanged': True, 'stackParametersPreserved': True, 'imageUri': review['newImage'],
             'modelSha256': hashlib.sha256(model).hexdigest(),
             'evaluationSha256': hashlib.sha256(evidence).hexdigest()}
    (PACKAGE / 'operations-cloud-verification.json').write_bytes(encoded(proof))
    # Mirror genuine cloud timestamps for the local/static fallback; no provider calls.
    import sys
    sys.path.insert(0, str(ROOT / 'tools'))
    import airport_weather as weather
    weather.atomic_json(weather.STATE / 'latest.json', snapshot); weather.publish(snapshot)
    print(json.dumps(proof))


if __name__ == '__main__': main()
