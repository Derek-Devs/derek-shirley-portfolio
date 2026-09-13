"""Budget-triggered stop is sticky. It never automatically resumes next month."""
import json
import os


def main(event, context):
    import boto3
    from botocore.config import Config
    config = Config(retries={'total_max_attempts': 1})
    if not event.get('Records') or any(r.get('Sns', {}).get('TopicArn') != os.environ['BUDGET_TOPIC'] for r in event['Records']):
        raise ValueError('Unexpected budget event')
    failures = []
    actions = [('ledger', lambda: boto3.client('dynamodb', config=config).update_item(
        TableName=os.environ['CONTROL_TABLE'], Key={'id': {'S': 'control'}},
        UpdateExpression='SET enabled = :off', ExpressionAttributeValues={':off': {'BOOL': False}}))]
    for name in json.loads(os.environ['WORKER_FUNCTIONS']):
        actions.append((name, lambda name=name: boto3.client('lambda', config=config).put_function_concurrency(FunctionName=name, ReservedConcurrentExecutions=0)))
    for name in json.loads(os.environ['WORKER_RULES']):
        actions.append((name, lambda name=name: boto3.client('events', config=config).disable_rule(Name=name)))
    for name, action in actions:
        try: action()
        except Exception as error: failures.append({'resource': name, 'error': type(error).__name__})
    print(json.dumps({'status': 'paused', 'failures': failures}))
    if failures: raise RuntimeError('Some stop actions failed; inspect the budget notification')
    return {'status': 'paused'}
