"""Operator-only deployment checks. Collection still uses the normal durable hourly quota."""
import argparse
import base64
from datetime import datetime, timezone
import json

from botocore.config import Config
from manage import ROOT, session_for, account_plan, outputs


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['audit', 'stop-drill', 'collect'])
    p.add_argument('--profile', required=True); p.add_argument('--account-id', required=True)
    p.add_argument('--stack', default='portfolio-airport-weather')
    args = p.parse_args(); session = session_for(args)
    out = outputs(session, args.stack)
    runtime = session.client('lambda', config=Config(read_timeout=140, retries={'total_max_attempts': 1}))
    if args.command != 'stop-drill': account_plan(session, args.account_id)
    report = {'checkedAt': datetime.now(timezone.utc).isoformat(), 'command': args.command, 'dataUrl': out['DataUrl']}
    if args.command in ('stop-drill', 'collect'):
        job = 'stop' if args.command == 'stop-drill' else 'collector'
        event = ({'Records': [{'Sns': {'TopicArn': out['BudgetTopic'], 'Message': 'Operator shutdown drill; not actual spend'}}]}
                 if job == 'stop' else {'job': 'collector'})
        response = runtime.invoke(FunctionName=args.stack + '-' + job, InvocationType='RequestResponse',
                                  LogType='Tail', Payload=json.dumps(event).encode())
        report['result'] = json.loads(response['Payload'].read())
        report['functionError'] = response.get('FunctionError')
        report['log'] = base64.b64decode(response.get('LogResult', '')).decode('utf-8', errors='replace')
    report['workers'] = {}
    resources = session.client('cloudformation').list_stack_resources(StackName=args.stack)['StackResourceSummaries']
    resource_ids = {r['LogicalResourceId']: r.get('PhysicalResourceId') for r in resources}
    for logical, job in (('Collector', 'collector'), ('Learning', 'learning')):
        name = args.stack + '-' + job
        config = runtime.get_function_configuration(FunctionName=name)
        concurrency = runtime.get_function_concurrency(FunctionName=name).get('ReservedConcurrentExecutions')
        schedule = session.client('events').describe_rule(Name=resource_ids[logical + 'Schedule'])
        report['workers'][job] = {'state': config['State'], 'memoryMb': config['MemorySize'],
            'timeoutSeconds': config['Timeout'], 'concurrency': concurrency, 'scheduleState': schedule['State'],
            'schedule': schedule['ScheduleExpression']}
    report['control'] = session.client('dynamodb').get_item(TableName=out['ControlTable'], Key={'id': {'S': 'control'}}, ConsistentRead=True).get('Item')
    subscriptions = session.client('sns').list_subscriptions_by_topic(TopicArn=out['BudgetTopic'])['Subscriptions']
    report['budgetEmailConfirmed'] = any(s['Protocol'] == 'email' and s['Endpoint'] == 'derek@derekdevs.com'
        and s['SubscriptionArn'] != 'PendingConfirmation' for s in subscriptions)
    delivery = session.client('cloudfront').get_distribution(Id=out['DistributionId'])['Distribution']
    report['delivery'] = {'status': delivery['Status'], 'enabled': delivery['DistributionConfig']['Enabled']}
    if args.command == 'stop-drill':
        report['shutdownVerified'] = (not report['functionError'] and report['result'] == {'status': 'paused'}
            and report['control']['enabled'] == {'BOOL': False}
            and all(w['concurrency'] == 0 and w['scheduleState'] == 'DISABLED' for w in report['workers'].values()))
    path = ROOT / '.airport-data/aws-package' / (args.command + '-verification.json')
    path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
    if report.get('functionError') or report.get('shutdownVerified') is False:
        raise RuntimeError('Live verification failed; inspect the saved report')
    if args.command == 'collect' and 'generatedAt' not in report['result']:
        raise RuntimeError('No new snapshot was published; inspect the quota/control report')


if __name__ == '__main__': main()
