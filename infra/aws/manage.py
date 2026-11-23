"""Prepare/inspect the AWS deployment. Cloud writes always require an exact target account.

No credentials are accepted as command arguments. Use a temporary-credential AWS profile.
Cloud creation and activation require AWS to report an active Free account plan, or an active
paid plan with remaining credits at or above the reviewed floor in limits.json.
"""
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE / 'runtime'))
from guard import LIMITS, validate_pair, require_billing_protection
from template import build


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()


def seed_files():
    public = ROOT / 'public/data/airport-weather'
    history = ROOT / '.airport-data/model-v2'
    model_raw = (public / 'model.json').read_bytes()
    model, evaluation = json.loads(model_raw), json.loads((public / 'evaluation.json').read_bytes())
    validate_pair(model, evaluation, model_raw)
    expanded='airportModels' in model
    if expanded: history=ROOT/'.airport-data/model-v3'
    inventory = json.loads((history / 'inventory.json').read_text())
    files = {'active/model.json': model_raw, 'active/evaluation.json': (public / 'evaluation.json').read_bytes(),
             'public/airports.json': (public / 'airports.json').read_bytes(),
             'state/latest.json': encoded({'stations': {}, 'sources': {}}),
             'history/timezones.json': (history / 'timezones.json').read_bytes()}
    for item in inventory:
        name = 'joined-' + item['month'] + '.json.gz'
        files['history/' + name] = (history / name).read_bytes()
    history_months=[r['month'] for r in inventory]
    extras=history/'operational-history'
    if expanded and (extras/'inventory.json').exists():
        operational=json.loads((extras/'inventory.json').read_text())
        if {r['month'] for r in operational}!={'2025-10','2025-11','2025-12'}: raise ValueError('Operational seed gaps are incomplete')
        for item in operational:
            name='joined-'+item['month']+'.json.gz'
            files['history/'+name]=(extras/name).read_bytes(); history_months.append(item['month'])
    files['history/index.json'] = encoded({'scope':'us-v3' if expanded else 'v2','months': sorted(history_months),
        'lastEvaluatedMonth': '2026-06', 'seedModel': model['version'], 'seedModelSha256': hashlib.sha256(model_raw).hexdigest(),
        'note': 'Jan-Jun 2026 were inspected in v2. Only later outcome months may evaluate a new candidate.'})
    if len(files) > 80 or sum(map(len, files.values())) > (96 if expanded else 32) * 1024 * 1024:
        raise ValueError('Bootstrap seed exceeds reviewed upload limits')
    return files


def prepare():
    folder = ROOT / '.airport-data/aws-package'; folder.mkdir(exist_ok=True)
    files = seed_files()
    with zipfile.ZipFile(folder / 'seed.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in files.items(): archive.writestr(name, body)
    (HERE / 'cloudformation.json').write_text(json.dumps(build(), indent=2) + '\n', encoding='utf-8')
    manifest = {'status': 'prepared-not-deployed', 'files': {k: {'bytes': len(v), 'sha256': hashlib.sha256(v).hexdigest()} for k, v in files.items()},
                'limits': LIMITS, 'credentialsIncluded': False, 'automaticPromotion': False}
    (folder / 'manifest.json').write_bytes(encoded(manifest))
    print(json.dumps({'status': manifest['status'], 'seedZip': str(folder / 'seed.zip'), 'seedBytes': sum(map(len, files.values()))}))


def session_for(args):
    if not args.profile or not args.account_id or not args.account_id.isdigit() or len(args.account_id) != 12:
        raise ValueError('A named AWS profile and exact 12-digit account ID are required')
    import boto3
    from botocore.config import Config
    session = boto3.Session(profile_name=args.profile, region_name=LIMITS['region'])
    caller = session.client('sts', config=Config(retries={'total_max_attempts': 1})).get_caller_identity()
    if caller['Account'] != args.account_id or caller['Arn'].endswith(':root'):
        raise ValueError('Wrong AWS account or root credentials; use the dedicated project role')
    return session


def account_plan(session, account_id):
    from botocore.config import Config
    plan = session.client('freetier', region_name='us-east-1',
                          config=Config(retries={'total_max_attempts': 1})).get_account_plan_state()
    plan.pop('ResponseMetadata', None)
    require_billing_protection(plan, account_id)
    return plan


def preflight(session, args):
    plan = account_plan(session, args.account_id)
    limits = session.client('lambda').get_account_settings()['AccountLimit']
    if limits['ConcurrentExecutions'] < 103:
        raise ValueError('Lambda quota must support three reserved executions plus the unreserved minimum')
    print(json.dumps({'status': 'billing-protection-verified', 'region': LIMITS['region'],
                      'plan': plan, 'lambdaLimits': limits}, default=str))
    return plan


def outputs(session, stack):
    result = session.client('cloudformation').describe_stacks(StackName=stack)['Stacks'][0]
    if result['StackStatus'] not in ('CREATE_COMPLETE', 'UPDATE_COMPLETE'):
        raise ValueError('Stack is not ready')
    return {o['OutputKey']: o['OutputValue'] for o in result['Outputs']}


def inspect(session, args):
    plan = account_plan(session, args.account_id)
    out = outputs(session, args.stack)
    budget = session.client('budgets').describe_budget(AccountId=args.account_id, BudgetName=out['BudgetName'])['Budget']
    if float(budget['BudgetLimit']['Amount']) > 8 or budget['BudgetLimit']['Unit'] != 'USD':
        raise ValueError('Early stop budget is missing or above $8')
    print(json.dumps({'status': 'billing-protection-and-budget-checked', 'plan': plan, 'automaticPromotion': False, **out}, default=str))
    return out


def jobs_state(parameters, rule_states, concurrency, deny_attached):
    """Decide how activation reaches the enabled state.

    'needs-update' when the stack parameters still have jobs or delivery off. 'current' when the
    parameters and the live schedules and worker concurrency already agree that jobs run, so only
    the lease needs renewing. Anything in between is drift, for example after a budget stop changed
    live resources outside CloudFormation, and raises before any control write.
    """
    if deny_attached:
        raise ValueError('The budget stop deny policy is still attached to a worker role. Wait for the budget period to reset')
    if parameters.get('EnableJobs') != 'true' or parameters.get('EnableDelivery') != 'true':
        return 'needs-update'
    if rule_states and concurrency and all(s == 'ENABLED' for s in rule_states.values()) and all(c == 1 for c in concurrency.values()):
        return 'current'
    raise ValueError('The stack has jobs on, but a schedule or worker concurrency is off, for example after a budget stop. '
                     'Run pause, wait for UPDATE_COMPLETE, then activate')


def live_jobs_state(session, stack):
    cf = session.client('cloudformation')
    parameters = {p['ParameterKey']: p['ParameterValue'] for p in cf.describe_stacks(StackName=stack)['Stacks'][0]['Parameters']}
    physical = lambda logical: cf.describe_stack_resource(StackName=stack, LogicalResourceId=logical)['StackResourceDetail']['PhysicalResourceId']
    events, lam, iam = session.client('events'), session.client('lambda'), session.client('iam')
    rule_states = {job: events.describe_rule(Name=physical(job + 'Schedule'))['State'] for job in ('Collector', 'Learning')}
    concurrency = {job: lam.get_function_concurrency(FunctionName=physical(job)).get('ReservedConcurrentExecutions')
                   for job in ('Collector', 'Learning')}
    deny = physical('RuntimeDeny')
    deny_attached = any(p['PolicyArn'] == deny for role in ('CollectorRole', 'LearningRole')
                        for p in iam.list_attached_role_policies(RoleName=physical(role))['AttachedPolicies'])
    return jobs_state(parameters, rule_states, concurrency, deny_attached)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'preflight', 'bootstrap', 'seed', 'inspect', 'activate', 'pause', 'cleanup-rollback'])
    parser.add_argument('--profile'); parser.add_argument('--account-id')
    parser.add_argument('--stack', default='portfolio-airport-weather'); parser.add_argument('--image-uri')
    args = parser.parse_args()
    if args.command == 'prepare': return prepare()
    session = session_for(args)
    if args.command == 'cleanup-rollback':
        cf = session.client('cloudformation')
        stack = cf.describe_stacks(StackName=args.stack)['Stacks'][0]
        if stack['StackStatus'] != 'ROLLBACK_COMPLETE':
            raise ValueError('Cleanup only accepts a completed failed initial deployment')
        resources = cf.list_stack_resources(StackName=args.stack)['StackResourceSummaries']
        data = next((r for r in resources if r['LogicalResourceId'] == 'Data'), None)
        if data and data.get('PhysicalResourceId'):
            if data['ResourceStatus'] != 'DELETE_SKIPPED': raise ValueError('Bucket was not retained by rollback')
            s3 = session.client('s3'); bucket = data['PhysicalResourceId']
            found = s3.list_objects_v2(Bucket=bucket, MaxKeys=1, ExpectedBucketOwner=args.account_id)
            if found.get('KeyCount') != 0: raise ValueError('Refuse to remove a bucket containing any data')
            s3.delete_bucket(Bucket=bucket, ExpectedBucketOwner=args.account_id)
        cf.delete_stack(StackName=args.stack)
        print(json.dumps({'status': 'removing-empty-failed-deployment'})); return
    if args.command == 'preflight': return preflight(session, args)
    if args.command == 'inspect': return inspect(session, args)
    if args.command == 'pause':
        out = outputs(session, args.stack)
        session.client('dynamodb').update_item(TableName=out['ControlTable'], Key={'id': {'S': 'control'}},
            UpdateExpression='SET enabled = :off', ExpressionAttributeValues={':off': {'BOOL': False}})
        response = session.client('cloudformation').update_stack(StackName=args.stack, UsePreviousTemplate=True,
            Parameters=[{'ParameterKey': 'ImageUri', 'UsePreviousValue': True}, {'ParameterKey': 'ContactEmail', 'UsePreviousValue': True},
                        {'ParameterKey': 'EnableJobs', 'ParameterValue': 'false'}, {'ParameterKey': 'EnableDelivery', 'UsePreviousValue': True}],
            Capabilities=['CAPABILITY_IAM'])
        print(json.dumps({'status': 'pausing-workers', 'stackId': response['StackId']})); return
    plan = account_plan(session, args.account_id)
    if args.command == 'activate':
        out = inspect(session, args)
        subscriptions = session.client('sns').list_subscriptions_by_topic(TopicArn=out['BudgetTopic'])['Subscriptions']
        if not any(s['Protocol'] == 'email' and s['Endpoint'] == 'derek@derekdevs.com' and s['SubscriptionArn'] != 'PendingConfirmation' for s in subscriptions):
            raise ValueError('Confirm the budget notification email before activation')
        # Check the seed and calibration pair again, not merely the existence of a bucket.
        s3 = session.client('s3')
        from handler import read
        raw = read(s3, out['Bucket'], 'active/model.json')
        validate_pair(json.loads(raw), json.loads(read(s3, out['Bucket'], 'active/evaluation.json')), raw)
        read(s3, out['Bucket'], 'history/index.json')
        # Decide before any control write, so drift cannot leave a renewed lease with schedules off.
        state = live_jobs_state(session, args.stack)
        now = datetime.now(timezone.utc)
        until = now + timedelta(days=LIMITS['maximumActivationDays'])
        plan_expiry = require_billing_protection(plan, args.account_id, now)
        if plan_expiry is not None:
            until = min(until, plan_expiry - timedelta(hours=1))
        if until <= now:
            raise ValueError('Free account plan expires too soon for safe activation')
        session.client('dynamodb').update_item(TableName=out['ControlTable'], Key={'id': {'S': 'control'}},
            UpdateExpression='SET enabled = :yes, authorizedUntil = :until', ConditionExpression='attribute_exists(id)',
            ExpressionAttributeValues={':yes': {'BOOL': True}, ':until': {'N': str(int(until.timestamp()))}})
        if state == 'current':
            # Jobs already run, so CloudFormation has nothing to change. Only the lease is renewed.
            print(json.dumps({'status': 'lease-renewed', 'authorizedUntil': until.isoformat(), 'dataUrl': out['DataUrl'], 'stackUpdate': 'not-needed'})); return
        response = session.client('cloudformation').update_stack(StackName=args.stack, UsePreviousTemplate=True,
            Parameters=[{'ParameterKey': 'ImageUri', 'UsePreviousValue': True}, {'ParameterKey': 'ContactEmail', 'UsePreviousValue': True},
                        {'ParameterKey': 'EnableJobs', 'ParameterValue': 'true'}, {'ParameterKey': 'EnableDelivery', 'ParameterValue': 'true'}], Capabilities=['CAPABILITY_IAM'])
        print(json.dumps({'status': 'activating', 'authorizedUntil': until.isoformat(), 'dataUrl': out['DataUrl'], 'stackId': response['StackId']})); return
    if args.command == 'bootstrap':
        import re
        if not args.image_uri or not re.fullmatch(args.account_id + r'\.dkr\.ecr\.' + re.escape(LIMITS['region']) + r'\.amazonaws\.com/[a-z0-9/_-]+@sha256:[a-f0-9]{64}', args.image_uri):
            raise ValueError('Supply the immutable image digest in this account and region')
        preflight(session, args)
        response = session.client('cloudformation').create_stack(StackName=args.stack, TemplateBody=json.dumps(build()),
            Parameters=[{'ParameterKey': 'ImageUri', 'ParameterValue': args.image_uri}], Capabilities=['CAPABILITY_IAM'],
            OnFailure='ROLLBACK', Tags=[{'Key': 'Project', 'Value': 'airport-weather'}])
        print(json.dumps({'status': 'creating-disabled-stack', 'stackId': response['StackId']})); return
    out = outputs(session, args.stack)
    s3 = session.client('s3')
    # Never overwrite a running model or reset a quota/history frontier through bootstrap.
    existing = s3.list_objects_v2(Bucket=out['Bucket'], MaxKeys=1)
    if existing.get('KeyCount', 0): raise ValueError('Seed requires an empty new bucket')
    for key, body in seed_files().items():
        s3.put_object(Bucket=out['Bucket'], Key=key, Body=body, ServerSideEncryption='AES256',
            ContentType='application/json' if key.endswith('.json') else 'application/gzip',
            CacheControl='public,max-age=86400' if key == 'public/airports.json' else 'private,no-store')
    session.client('dynamodb').put_item(TableName=out['ControlTable'], Item={'id': {'S': 'control'}, 'enabled': {'BOOL': False}, 'authorizedUntil': {'N': '0'}}, ConditionExpression='attribute_not_exists(id)')
    print(json.dumps({'status': 'seeded-disabled', 'bucket': out['Bucket']}))


if __name__ == '__main__': main()
