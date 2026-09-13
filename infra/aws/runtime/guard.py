"""Persistent reservations precede work. Retries, crashes and month rollover do not refund quota."""
from datetime import datetime, timezone
import json
from pathlib import Path

_limits = Path(__file__).parent / 'limits.json'
LIMITS = json.loads((_limits if _limits.exists() else Path(__file__).parents[1] / 'limits.json').read_text())


def reserve(ddb, table, job, now=None):
    if job not in ('collector', 'learning'):
        raise ValueError('Unknown job')
    now = now or datetime.now(timezone.utc)
    month = now.strftime('%Y-%m')
    slot = now.strftime('%Y-%m-%dT%H') if job == 'collector' else month
    # No TTL on the monthly counter. Missing control state never authorizes work.
    ddb.transact_write_items(TransactItems=[
        {'ConditionCheck': {'TableName': table, 'Key': {'id': {'S': 'control'}},
         'ConditionExpression': 'enabled = :yes AND authorizedUntil > :now',
         'ExpressionAttributeValues': {':yes': {'BOOL': True}, ':now': {'N': str(int(now.timestamp()))}}}},
        {'Put': {'TableName': table,
         'Item': {'id': {'S': f'slot/{job}/{slot}'}, 'expiresAt': {'N': str(int(now.timestamp()) + 93 * 86400)}},
         'ConditionExpression': 'attribute_not_exists(id)'}},
        {'Update': {'TableName': table, 'Key': {'id': {'S': f'quota/{job}/{month}'}},
         'UpdateExpression': 'ADD runs :one',
         'ConditionExpression': 'attribute_not_exists(runs) OR runs < :cap',
         'ExpressionAttributeValues': {':one': {'N': '1'}, ':cap': {'N': str(LIMITS[job]['monthlyRuns'])}}}}
    ])


def validate_pair(model, evaluation, model_bytes):
    import hashlib
    if evaluation.get('modelSha256') != hashlib.sha256(model_bytes).hexdigest():
        raise ValueError('Model hash mismatch')
    if model['version'] != evaluation['version'] or model['generatedAt'] != evaluation['generatedAt']:
        raise ValueError('Model and evaluation disagree')
    airports = set(model['protocol']['airports'])
    if not airports or len(airports) > LIMITS['maximumModeledAirports'] or airports != set(evaluation['airports']):
        raise ValueError('Unreviewed airport coverage change')
    if sorted(model['protocol']['horizons']) != [6, 12, 24]:
        raise ValueError('Unreviewed horizons')
    if 'airportModels' in model:
        if set(model.get('airportCoverage',{}))!=airports:
            raise ValueError('Expanded airport audit is incomplete')
        for airport,entries in model['airportModels'].items():
            if airport not in airports: raise ValueError('Unknown local model airport')
            for key,entry in entries.items():
                if set(entry.get('featureAirports',{}))!={airport}:
                    raise ValueError('Local model must use its own airport features')
                direction,horizon=key.split('_')
                if horizon not in evaluation['airports'][airport]['directions'].get(direction,{}):
                    raise ValueError('Local model has no airport-specific backtest')


def validate_publication(files):
    if len(files) > LIMITS['maximumPublicFilesPerSnapshot']:
        raise ValueError('Too many public files')
    if sum(len(value) for value in files.values()) > LIMITS['maximumPublicSnapshotBytes']:
        raise ValueError('Public snapshot too large')
    import re
    for name in files:
        if name not in ('latest.json', 'risk.json', 'evaluation.json', 'operations/risk.json', 'operations/evaluation.json', 'operations/release.json') and not re.fullmatch(r'stations/[A-Z0-9]{2}\.json', name):
            raise ValueError('Unexpected public path')


def require_free_account(plan, account_id, now=None):
    """Validate AWS's live account-plan response; credits on a paid plan are insufficient."""
    import math
    now = now or datetime.now(timezone.utc)
    if (not isinstance(account_id, str) or len(account_id) != 12 or not account_id.isdigit()
            or plan.get('accountId') != account_id or plan.get('accountPlanType') != 'FREE'
            or plan.get('accountPlanStatus') != 'ACTIVE'):
        raise ValueError('The exact account must have an ACTIVE FREE account plan; paid plans require a new billing design')
    credits = plan.get('accountPlanRemainingCredits', {})
    amount = float(credits.get('amount', 0))
    if credits.get('unit') != 'USD' or not math.isfinite(amount) or amount <= 0:
        raise ValueError('Free account credits are missing or exhausted')
    expiry = plan.get('accountPlanExpirationDate')
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
    if not isinstance(expiry, datetime) or expiry.tzinfo is None or expiry <= now:
        raise ValueError('The Free account plan has expired or its expiration is unavailable')
    return expiry


def check_free_account(account_id):
    import boto3
    from botocore.config import Config
    client = boto3.client('freetier', region_name='us-east-1',
                         config=Config(connect_timeout=5, read_timeout=10, retries={'total_max_attempts': 1}))
    return require_free_account(client.get_account_plan_state(), account_id)
