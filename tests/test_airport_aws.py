import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'infra/aws/runtime'))
sys.path.insert(0, str(ROOT / 'infra/aws'))
import guard
import handler
import learning
import template
import manage


class SafetyTests(unittest.TestCase):
    def test_full_collection_publishes_catalog_with_missing_data_preserved(self):
        import gzip
        import io
        import airport_weather as weather
        import airport_predict as predictor
        import tempfile
        files = manage.seed_files()
        class MemoryS3:
            def __init__(self): self.values = dict(files)
            def get_object(self, Bucket, Key):
                raw = self.values[Key]
                return {'ContentLength': len(raw), 'Body': io.BytesIO(raw)}
            def put_object(self, **kwargs): self.values[kwargs['Key']] = kwargs['Body']
        s3 = MemoryS3()
        fixed = datetime(2026, 9, 11, 20, tzinfo=timezone.utc)
        xml = {
            'observations': b'<response><data><METAR><station_id>KDFW</station_id><raw_text>KDFW 112000Z 18010KT 10SM CLR 30/20 A2992</raw_text><observation_time>2026-09-11T20:00:00Z</observation_time></METAR></data></response>',
            'forecasts': b'<response><data><TAF><station_id>KDFW</station_id><raw_text>TAF KDFW 111730Z 1118/1300 18010KT P6SM SKC</raw_text><issue_time>2026-09-11T17:30:00Z</issue_time><valid_time_from>2026-09-11T18:00:00Z</valid_time_from><valid_time_to>2026-09-13T00:00:00Z</valid_time_to></TAF></data></response>'}
        context = Mock(); context.get_remaining_time_in_millis.return_value = 120000
        with patch.object(weather, 'STATE', weather.STATE), patch.object(weather, 'PUBLIC', weather.PUBLIC), patch.object(predictor, 'STATE', predictor.STATE), patch.object(predictor, 'PUBLIC', predictor.PUBLIC), patch.object(weather, 'utc_now', return_value=fixed), patch.object(weather, 'fetch', side_effect=lambda kind: gzip.compress(xml[kind])):
            result = handler.collect(s3, 'bucket', context)
        manifest = json.loads(s3.values['public/latest.json'])
        self.assertEqual(result['airports'], len(json.loads(files['public/airports.json'])['airports']))
        self.assertEqual(manifest['coverage']['observations'], 1)
        risk = json.loads(s3.values['public/' + manifest['dataPrefix'] + '/risk.json'])
        self.assertEqual(risk['generatedAt'], manifest['generatedAt'])
        self.assertTrue(all(v['status'] == 'no-forecast' for d in risk['airports']['ORD']['directions'].values() for v in d.values()))

    def test_transactions_reserve_both_hour_and_month_before_work(self):
        ddb = Mock()
        guard.reserve(ddb, 'table', 'collector', datetime(2026, 9, 30, 23, tzinfo=timezone.utc))
        old = ddb.transact_write_items.call_args.kwargs['TransactItems']
        guard.reserve(ddb, 'table', 'collector', datetime(2026, 10, 1, tzinfo=timezone.utc))
        new = ddb.transact_write_items.call_args.kwargs['TransactItems']
        self.assertNotEqual(old[1]['Put']['Item']['id'], new[1]['Put']['Item']['id'])
        self.assertNotEqual(old[2]['Update']['Key'], new[2]['Update']['Key'])
        self.assertIn('authorizedUntil', old[0]['ConditionCheck']['ConditionExpression'])
        self.assertEqual(old[2]['Update']['ExpressionAttributeValues'][':cap']['N'], '744')
        guard.reserve(ddb, 'table', 'learning')
        self.assertEqual(ddb.transact_write_items.call_args.kwargs['TransactItems'][2]['Update']['ExpressionAttributeValues'][':cap']['N'], '1')

    def test_quota_failure_never_reads_data_or_calls_weather(self):
        s3, ddb = Mock(), Mock()
        ddb.transact_write_items.side_effect = RuntimeError('Duplicate, disabled, exhausted, or offline')
        with patch.object(handler, 'clients', return_value=(s3, ddb)), patch.dict('os.environ', {'JOB': 'collector', 'CONTROL_TABLE': 'table'}):
            self.assertEqual(handler.main({'job': 'collector'}, Mock()), {'status': 'paused'})
        s3.get_object.assert_not_called()

    def test_external_event_cannot_choose_work_or_download(self):
        with patch.dict('os.environ', {'JOB': 'collector'}), patch.object(handler, 'clients') as clients:
            self.assertEqual(handler.main({'job': 'collector', 'url': 'https://example.org'}, Mock())['status'], 'rejected-event')
            clients.assert_not_called()

    def test_public_pointer_is_last_and_partial_upload_does_not_publish(self):
        snapshot = {'generatedAt': '2026-09-11T20:00:00Z', 'stations': {}}
        files = {'latest.json': b'{}', 'risk.json': b'{}', 'stations/KD.json': b'{}'}
        s3 = Mock()
        handler.publish(s3, 'bucket', snapshot, files)
        calls = s3.put_object.call_args_list
        self.assertEqual(calls[-1].kwargs['Key'], 'public/latest.json')
        self.assertEqual(json.loads(calls[-1].kwargs['Body'])['dataPrefix'], 'snapshots/20260911T200000Z')
        s3 = Mock(); s3.put_object.side_effect = [None, RuntimeError('S3 unavailable')]
        with self.assertRaises(RuntimeError): handler.publish(s3, 'bucket', snapshot, files)
        self.assertNotIn('public/latest.json', [c.kwargs['Key'] for c in s3.put_object.call_args_list])

    def test_private_data_and_oversize_publication_are_rejected_before_upload(self):
        for files in ({'model.json': b'{}'}, {'../active/model.json': b'{}'}, {'risk.json': b'x' * (guard.LIMITS['maximumPublicSnapshotBytes'] + 1)}):
            s3 = Mock()
            with self.assertRaises(ValueError): handler.publish(s3, 'bucket', {}, files)
            s3.put_object.assert_not_called()

    def test_only_live_free_account_with_credits_and_expiry_passes(self):
        now = datetime(2026, 9, 11, tzinfo=timezone.utc)
        expiry = now + timedelta(days=180)
        plan = {'accountId': '123456789012', 'accountPlanType': 'FREE', 'accountPlanStatus': 'ACTIVE',
                'accountPlanRemainingCredits': {'amount': 100, 'unit': 'USD'}, 'accountPlanExpirationDate': expiry}
        self.assertEqual(guard.require_free_account(plan, '123456789012', now), expiry)
        self.assertEqual(guard.require_free_account({**plan, 'accountPlanExpirationDate': expiry.isoformat()}, '123456789012', now), expiry)
        changes = [{'accountPlanType': 'PAID'}, {'accountId': '999999999999'}, {'accountPlanStatus': 'EXPIRED'},
                   {'accountPlanStatus': 'NOT_STARTED'}, {'accountPlanExpirationDate': now},
                   {'accountPlanExpirationDate': None}, {'accountPlanExpirationDate': '2026-12-01'},
                   {'accountPlanRemainingCredits': {}},
                   *[{'accountPlanRemainingCredits': {'amount': value, 'unit': 'USD'}} for value in (0, -1, float('nan'), float('inf'))]]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                guard.require_free_account({**plan, **change}, '123456789012', now)

    def test_paid_plan_passes_only_with_credits_at_or_above_floor(self):
        now = datetime(2026, 11, 23, tzinfo=timezone.utc)
        expiry = now + timedelta(days=100)
        free = {'accountId': '123456789012', 'accountPlanType': 'FREE', 'accountPlanStatus': 'ACTIVE',
                'accountPlanRemainingCredits': {'amount': 100, 'unit': 'USD'}, 'accountPlanExpirationDate': expiry}
        self.assertEqual(guard.require_billing_protection(free, '123456789012', now), expiry)
        paid = {'accountId': '123456789012', 'accountPlanType': 'PAID', 'accountPlanStatus': 'ACTIVE',
                'accountPlanRemainingCredits': {'amount': 132.21, 'unit': 'USD'}}
        floor = guard.LIMITS['minimumPaidCreditsUsd']
        self.assertIsNone(guard.require_billing_protection(paid, '123456789012', now))
        self.assertIsNone(guard.require_billing_protection({**paid, 'accountPlanRemainingCredits': {'amount': floor, 'unit': 'USD'}}, '123456789012', now))
        changes = [{'accountId': '999999999999'}, {'accountPlanStatus': 'EXPIRED'}, {'accountPlanStatus': 'NOT_STARTED'},
                   {'accountPlanType': 'OTHER'}, {'accountPlanType': None},
                   {'accountPlanRemainingCredits': None}, {'accountPlanRemainingCredits': {}},
                   {'accountPlanRemainingCredits': {'amount': 50, 'unit': 'EUR'}},
                   *[{'accountPlanRemainingCredits': {'amount': value, 'unit': 'USD'}}
                     for value in (floor - 0.01, 0, -1, float('nan'), float('inf'), 'many', None, [1])]]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                guard.require_billing_protection({**paid, **change}, '123456789012', now)
        for account in ('12345678901', 123456789012, None):
            with self.subTest(account=account), self.assertRaises(ValueError):
                guard.require_billing_protection(paid, account, now)
        with self.assertRaises(ValueError): guard.require_billing_protection(None, '123456789012', now)
        for bad in (None, 0, -5, float('nan'), True, '20'):
            with self.subTest(floor=bad), patch.dict(guard.LIMITS, {'minimumPaidCreditsUsd': bad}), self.assertRaises(ValueError):
                guard.require_billing_protection(paid, '123456789012', now)

    def test_activation_renews_lease_only_and_refuses_drift(self):
        on = {'EnableJobs': 'true', 'EnableDelivery': 'true'}
        live = ({'Collector': 'ENABLED', 'Learning': 'ENABLED'}, {'Collector': 1, 'Learning': 1})
        self.assertEqual(manage.jobs_state(on, *live, False), 'current')
        for parameters in ({**on, 'EnableJobs': 'false'}, {**on, 'EnableDelivery': 'false'}, {}):
            with self.subTest(parameters=parameters):
                self.assertEqual(manage.jobs_state(parameters, {'Collector': 'DISABLED', 'Learning': 'DISABLED'}, {'Collector': 0, 'Learning': 0}, False), 'needs-update')
        drifted = [({'Collector': 'DISABLED', 'Learning': 'ENABLED'}, live[1]), (live[0], {'Collector': 0, 'Learning': 1}),
                   (live[0], {'Collector': None, 'Learning': 1}), ({}, {})]
        for rules, concurrency in drifted:
            with self.subTest(rules=rules, concurrency=concurrency), self.assertRaises(ValueError):
                manage.jobs_state(on, rules, concurrency, False)
        for parameters in (on, {**on, 'EnableJobs': 'false'}):
            with self.subTest(deny=parameters), self.assertRaises(ValueError):
                manage.jobs_state(parameters, *live, True)

    def test_unprotected_or_unavailable_plan_stops_before_weather_or_training(self):
        for job in ('collector', 'learning'):
            s3, ddb = Mock(), Mock()
            with patch.object(handler, 'clients', return_value=(s3, ddb)), \
                    patch.dict('os.environ', {'JOB': job, 'ACCOUNT_ID': '123456789012', 'CONTROL_TABLE': 'table'}), \
                    patch.object(guard, 'check_billing_protection', side_effect=ValueError('Credits below floor or unavailable')) as check, \
                    patch.object(handler, 'collect') as collect, patch.object(learning, 'run') as learn:
                self.assertEqual(handler.main({'job': job}, Mock()), {'status': 'paused'})
                ddb.transact_write_items.assert_called_once()
                check.assert_called_once_with('123456789012')
                collect.assert_not_called(); learn.assert_not_called(); s3.get_object.assert_not_called()

    def test_active_artifacts_match_and_tampering_is_rejected(self):
        p = ROOT / 'public/data/airport-weather'; raw = (p / 'model.json').read_bytes()
        model, evaluation = json.loads(raw), json.loads((p / 'evaluation.json').read_bytes())
        guard.validate_pair(model, evaluation, raw)
        with self.assertRaises(ValueError): guard.validate_pair(model, evaluation, raw + b' ')
        with self.assertRaises(ValueError): guard.validate_pair({**model, 'version': 'different'}, evaluation, raw)

    def test_learning_periods_are_disjoint_and_do_not_fit_on_holdout(self):
        base = json.loads((ROOT / 'research/airport-protocol-v2.json').read_text())
        p = learning.protocol_for('2026-08', base)
        self.assertEqual(p['test'], ['2026-07-03', '2026-08-29'])
        keys = ['train', 'probabilityCalibration', 'intervalCalibration', 'test']
        for a, b in zip(keys, keys[1:]): self.assertLess(p[a][1], p[b][0])
        self.assertEqual(learning.shift('2026-01', -1), '2025-12')

    def test_cloud_resources_have_no_unbounded_compute_or_public_invocation(self):
        t = template.build(); resources = t['Resources']
        self.assertEqual(t['Parameters']['EnableJobs']['Default'], 'false')
        self.assertEqual(t['Parameters']['EnableDelivery']['Default'], 'false')
        for name in ('Collector', 'Learning'):
            prop = resources[name]['Properties']
            self.assertEqual(prop['ReservedConcurrentExecutions'], {'Fn::If': ['JobsEnabled', 1, 0]})
            self.assertLessEqual(prop['MemorySize'], 3008)
            self.assertEqual(resources[name + 'Retry']['Properties']['MaximumRetryAttempts'], 0)
            self.assertNotIn('VpcConfig', prop)
        self.assertFalse(any('FunctionUrl' in r['Type'] or 'EC2' in r['Type'] or 'ApiGateway' in r['Type'] for r in resources.values()))
        statements = resources['LearningRole']['Properties']['Policies'][0]['PolicyDocument']['Statement']
        writes = [s for s in statements if s['Action'] == ['s3:PutObject']][0]
        self.assertNotIn('active', json.dumps(writes))
        self.assertNotIn('public', json.dumps(writes))
        self.assertEqual(resources['BudgetAction']['Properties']['ActionThreshold']['Value'], 8)
        self.assertFalse(any(r['Type'] == 'AWS::WAFv2::WebACL' for r in resources.values()))
        self.assertEqual(guard.LIMITS['billingProtection'], 'AWS_FREE_PLAN_OR_PAID_CREDIT_FLOOR')
        self.assertEqual(guard.LIMITS['minimumPaidCreditsUsd'], 20)
        self.assertEqual(guard.LIMITS['earlyStopUsd'], 8)

    def test_seed_preserves_holdout_frontier_and_contains_no_credentials(self):
        files = manage.seed_files()
        self.assertEqual(json.loads(files['history/index.json'])['lastEvaluatedMonth'], '2026-06')
        self.assertEqual(json.loads(files['state/latest.json'])['stations'], {})
        self.assertTrue(all(k.startswith(('history/', 'active/', 'public/', 'state/')) for k in files))

    def test_saved_cloudformation_matches_generator(self):
        self.assertEqual(template.build(), json.loads((ROOT / 'infra/aws/cloudformation.json').read_text()))

    def test_shared_cache_does_not_reuse_another_sites_cors_header(self):
        resources = template.build()['Resources']
        behavior = resources['Distribution']['Properties']['DistributionConfig']['DefaultCacheBehavior']
        config = resources[behavior['ResponseHeadersPolicyId']['Ref']]['Properties']['ResponseHeadersPolicyConfig']['CorsConfig']
        self.assertTrue(config['OriginOverride'])
        self.assertFalse(config['AccessControlAllowCredentials'])
        self.assertEqual(set(config['AccessControlAllowOrigins']['Items']),
                         {'https://derekdevs.com', 'https://www.derekdevs.com', 'http://127.0.0.1:4321'})


@unittest.skipUnless(importlib.util.find_spec('boto3'), 'Run in isolated aws-env for SDK validation')
class SdkTests(unittest.TestCase):
    def test_account_plan_response_uses_supported_aws_schema(self):
        import boto3
        from botocore.stub import Stubber
        session = boto3.Session(region_name='us-east-2', aws_access_key_id='test', aws_secret_access_key='test')
        client = session.client('freetier', region_name='us-east-1')
        response = {'accountId': '123456789012', 'accountPlanType': 'FREE', 'accountPlanStatus': 'ACTIVE',
                    'accountPlanRemainingCredits': {'amount': 100., 'unit': 'USD'},
                    'accountPlanExpirationDate': datetime.now(timezone.utc) + timedelta(days=180)}
        with Stubber(client) as stub, patch.object(session, 'client', return_value=client):
            stub.add_response('get_account_plan_state', response, {})
            self.assertEqual(manage.account_plan(session, '123456789012'), response)
            paid = {'accountId': '123456789012', 'accountPlanType': 'PAID', 'accountPlanStatus': 'ACTIVE',
                    'accountPlanRemainingCredits': {'amount': 132.21, 'unit': 'USD'}}
            stub.add_response('get_account_plan_state', paid, {})
            self.assertEqual(manage.account_plan(session, '123456789012'), paid)
            stub.add_response('get_account_plan_state', {**paid, 'accountPlanRemainingCredits': {'amount': 19.99, 'unit': 'USD'}}, {})
            with self.assertRaises(ValueError): manage.account_plan(session, '123456789012')
            stub.assert_no_pending_responses()

    def test_live_jobs_state_uses_valid_aws_api_schemas_without_network(self):
        import boto3
        from botocore.stub import Stubber
        session = boto3.Session(region_name='us-east-2', aws_access_key_id='test', aws_secret_access_key='test')
        clients = {name: session.client(name) for name in ('cloudformation', 'events', 'lambda', 'iam')}
        stack, deny = 'portfolio-airport-weather', 'arn:aws:iam::123456789012:policy/stack-RuntimeDeny-x'
        physical = {'CollectorSchedule': 'collector-rule', 'LearningSchedule': 'learning-rule', 'Collector': 'stack-collector',
                    'Learning': 'stack-learning', 'RuntimeDeny': deny, 'CollectorRole': 'collector-role', 'LearningRole': 'learning-role'}
        stubs = {name: Stubber(client) for name, client in clients.items()}
        now = datetime(2026, 11, 23, tzinfo=timezone.utc)
        stubs['cloudformation'].add_response('describe_stacks', {'Stacks': [{'StackName': stack, 'CreationTime': now, 'StackStatus': 'UPDATE_COMPLETE',
            'Parameters': [{'ParameterKey': 'EnableJobs', 'ParameterValue': 'true'}, {'ParameterKey': 'EnableDelivery', 'ParameterValue': 'true'}]}]},
            {'StackName': stack})
        def resource(logical):
            stubs['cloudformation'].add_response('describe_stack_resource', {'StackResourceDetail': {'LogicalResourceId': logical,
                'PhysicalResourceId': physical[logical], 'ResourceType': 'AWS::Test', 'LastUpdatedTimestamp': now, 'ResourceStatus': 'UPDATE_COMPLETE'}},
                {'StackName': stack, 'LogicalResourceId': logical})
        for job in ('Collector', 'Learning'):
            resource(job + 'Schedule')
            stubs['events'].add_response('describe_rule', {'Name': physical[job + 'Schedule'], 'State': 'DISABLED'}, {'Name': physical[job + 'Schedule']})
        for job in ('Collector', 'Learning'):
            resource(job)
            stubs['lambda'].add_response('get_function_concurrency', {'ReservedConcurrentExecutions': 0}, {'FunctionName': physical[job]})
        resource('RuntimeDeny')
        for role in ('CollectorRole', 'LearningRole'):
            resource(role)
            stubs['iam'].add_response('list_attached_role_policies', {'AttachedPolicies': []}, {'RoleName': physical[role]})
        for stub in stubs.values(): stub.activate()
        with patch.object(session, 'client', side_effect=lambda name, **kwargs: clients[name]):
            with self.assertRaisesRegex(ValueError, 'Run pause'):
                manage.live_jobs_state(session, stack)
        for stub in stubs.values():
            stub.assert_no_pending_responses(); stub.deactivate()

    def test_reservation_uses_valid_aws_api_schema_without_network(self):
        import boto3
        from botocore.stub import Stubber
        client = boto3.client('dynamodb', region_name='us-east-1', aws_access_key_id='test', aws_secret_access_key='test')
        with Stubber(client) as stub:
            stub.add_response('transact_write_items', {})
            guard.reserve(client, 'airport-control', 'collector')
            stub.assert_no_pending_responses()


if __name__ == '__main__': unittest.main()
