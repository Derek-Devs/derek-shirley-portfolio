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


def _exact_active_account(plan, account_id, plan_type):
    return (isinstance(plan, dict) and isinstance(account_id, str) and len(account_id) == 12 and account_id.isdigit()
            and plan.get('accountId') == account_id and plan.get('accountPlanType') == plan_type
            and plan.get('accountPlanStatus') == 'ACTIVE')


def _remaining_credits(plan):
    """Return the remaining USD credit balance. A missing, malformed, or empty balance raises."""
    import math
    credits = plan.get('accountPlanRemainingCredits') or {}
    try:
        amount = float(credits.get('amount', 0))
    except (TypeError, ValueError, AttributeError):
        raise ValueError('Account credits are unreadable') from None
    if credits.get('unit') != 'USD' or not math.isfinite(amount) or amount <= 0:
        raise ValueError('Account credits are missing or exhausted')
    return amount


def paid_credit_floor():
    """The reviewed minimum credit balance for work on a paid plan. A bad setting stops work."""
    import math
    floor = LIMITS.get('minimumPaidCreditsUsd')
    if isinstance(floor, bool) or not isinstance(floor, (int, float)) or not math.isfinite(floor) or floor <= 0:
        raise ValueError('The paid-plan credit floor is missing or invalid')
    return float(floor)


def require_free_account(plan, account_id, now=None):
    """Validate an ACTIVE FREE plan with credits and a future expiry, and return that expiry."""
    now = now or datetime.now(timezone.utc)
    if not _exact_active_account(plan, account_id, 'FREE'):
        raise ValueError('The exact account must have an ACTIVE FREE account plan')
    _remaining_credits(plan)
    expiry = plan.get('accountPlanExpirationDate')
    if isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
    if not isinstance(expiry, datetime) or expiry.tzinfo is None or expiry <= now:
        raise ValueError('The Free account plan has expired or its expiration is unavailable')
    return expiry


def require_billing_protection(plan, account_id, now=None):
    """Validate AWS's live account-plan response before any work, deployment, or activation.

    An ACTIVE FREE plan passes as before and returns its expiry. An ACTIVE PAID plan passes only
    while AWS reports remaining credits at or above the reviewed floor in limits.json. It returns
    None because a paid plan has no expiry. Credits pay first, and the separate early-stop budget
    still measures usage before credits. Anything else, including an unreadable balance, raises.
    """
    if isinstance(plan, dict) and plan.get('accountPlanType') == 'PAID':
        if not _exact_active_account(plan, account_id, 'PAID'):
            raise ValueError('The exact account must have an ACTIVE account plan')
        if _remaining_credits(plan) < paid_credit_floor():
            raise ValueError('Paid account credits are below the reviewed floor')
        return None
    return require_free_account(plan, account_id, now)


def check_billing_protection(account_id):
    import boto3
    from botocore.config import Config
    client = boto3.client('freetier', region_name='us-east-1',
                         config=Config(connect_timeout=5, read_timeout=10, retries={'total_max_attempts': 1}))
    return require_billing_protection(client.get_account_plan_state(), account_id)
