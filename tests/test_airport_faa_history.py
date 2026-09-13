from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import airport_faa_history as faa
from airport_faa_collect import collect
from airport_operations_score import score
from airport_models import predict_batch
from airport_features import features as wx_features
import airport_weather as weather


def ts(value): return datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp()


def listing(day,airport='DFW',title='CDM GROUND STOP',clock='12:00'):
    date=datetime.fromisoformat(day).strftime('%m/%d/%y')
    return f'<th>ATCSCC ADVISORIES FOR {day}</th><tr><td><a href="/adv/adv_otherdis?advn=1">1</a></td><td>{airport}/ZFW</td><td>{date}</td><td>{title}</td><td>{date} {clock}</td></tr>'.encode()


def full_history(cutoff,records=None):
    days={}
    for d in faa.required_dates(faa.available_at(cutoff)):
        days[d]={'date':d,'fetchedAtEpoch':cutoff,'records':[r for r in records or [] if datetime.fromtimestamp(r['published'],timezone.utc).date().isoformat()==d]}
    return {'featureVersion':faa.FEATURE_VERSION,'status':'ok','fetchedAtEpoch':cutoff,'days':days}


class FaaHistoryTests(unittest.TestCase):
    def test_actual_collection_phase_and_publication_embargo(self):
        self.assertEqual(faa.available_at(ts('2026-09-12T22:00')),ts('2026-09-12T21:25'))
        self.assertEqual(faa.available_at(ts('2026-09-12T21:35')),ts('2026-09-12T21:25'))
        self.assertEqual(faa.available_at(ts('2026-09-12T21:34')),ts('2026-09-12T20:25'))

    def test_history_and_live_features_are_identical_and_ignore_future_messages(self):
        cutoff=ts('2026-09-12T21:35')
        events=[{'airport':'DFW','published':ts('2026-09-12T21:20'),'kind':'gs','cancelled':False},
            {'airport':'DFW','published':ts('2026-09-12T21:26'),'kind':'gdp','cancelled':False}]
        history=full_history(cutoff,events)
        live=faa.snapshot_features(history,'DFW',cutoff)
        offline=faa.features('DFW',cutoff,set(history['days']),faa.build_index(history['days'].values(),['DFW']))
        np.testing.assert_array_equal(live,offline)
        self.assertAlmostEqual(live[1],np.log(2)); self.assertEqual(live[3],0)
        history['days']['2026-09-12']['records'].pop()
        np.testing.assert_array_equal(live,faa.snapshot_features(history,'DFW',cutoff))

    def test_no_data_stale_future_wrong_version_and_incomplete_prior_day_fail_closed(self):
        cutoff=ts('2026-09-12T21:35'); good=full_history(cutoff)
        for field,value in [('status','error'),('fetchedAtEpoch',cutoff-6000),('fetchedAtEpoch',cutoff+1),('featureVersion','other')]:
            bad={**good,field:value}; self.assertIsNone(faa.snapshot_features(bad,'DFW',cutoff))
        bad=deepcopy(good); bad['days'].pop('2026-09-11'); self.assertIsNone(faa.snapshot_features(bad,'DFW',cutoff))
        bad=deepcopy(good); bad['days']['2026-09-11']['fetchedAtEpoch']=ts('2026-09-11T23:35')
        self.assertIsNone(faa.snapshot_features(bad,'DFW',cutoff))
        np.testing.assert_array_equal(faa.snapshot_features(good,'DFW',cutoff),np.zeros(6))

    def test_exact_airport_alias_and_route_exclusion(self):
        r=faa.parse_listing(listing('2026-09-12','PBI'),'2026-09-12',['DJT'])
        self.assertEqual(r['records'][0]['airport'],'DJT')
        self.assertEqual(faa.parse_listing(listing('2026-09-12','DCC','DFW DAL ROUTE'),'2026-09-12',['DFW','DAL'])['records'],[])
        with self.assertRaises(ValueError): faa.parse_listing(listing('2026-09-12'),'2026-09-11',['DFW'])

    def test_midnight_finalization_is_bounded_then_reused(self):
        now=datetime(2026,9,12,0,35,tzinfo=timezone.utc)
        fetch=Mock(side_effect=lambda source,day:listing(day,clock='00:01'))
        first=collect(None,['DFW'],fetch,now)
        self.assertEqual(first['status'],'ok'); self.assertEqual(fetch.call_count,2)
        fetch.reset_mock(); later=now.replace(hour=1)
        second=collect(first,['DFW'],fetch,later)
        self.assertEqual(second['status'],'ok'); self.assertEqual(fetch.call_count,1)
        self.assertEqual(fetch.call_args.kwargs['day'],'2026-09-12')

    def test_fractional_fetch_time_matches_second_resolution_snapshot(self):
        now=datetime(2026,9,12,21,35,1,555555,tzinfo=timezone.utc)
        result=collect(None,['DFW'],lambda source,day:listing(day,clock='00:01'),now)
        self.assertIsNotNone(faa.snapshot_features(result,'DFW',int(now.timestamp())))

    def test_timeout_or_provider_failure_never_retries_or_implies_clear(self):
        now=datetime(2026,9,12,21,35,tzinfo=timezone.utc)
        fetch=Mock(side_effect=TimeoutError())
        result=collect(None,['DFW'],fetch,now)
        self.assertEqual(result['status'],'error'); self.assertEqual(fetch.call_count,1)
        fetch.reset_mock(); result=collect(None,['DFW'],fetch,now,lambda:20000)
        self.assertEqual(result['status'],'error'); fetch.assert_not_called()

    def test_dynamic_source_cannot_bypass_date_or_request_budget(self):
        with self.assertRaises(ValueError): weather.fetch('faaHistory',day='2023-01-01')
        with tempfile.TemporaryDirectory() as tmp,patch.object(weather,'STATE',Path(tmp)):
            weather.atomic_json(weather.STATE/'usage.json',{'month':weather.utc_now().strftime('%Y-%m'),'requests':weather.MAX_REQUESTS_PER_MONTH})
            with self.assertRaises(RuntimeError): weather.fetch('faaHistory',day=weather.utc_now().date().isoformat())

    def test_released_evidence_cannot_claim_a_learned_effect_without_training_activity(self):
        folder=ROOT/'public/data/airport-weather/operations'
        if not (folder/'evaluation.json').exists(): self.skipTest('National candidate not fitted')
        evaluation=json.loads((folder/'evaluation.json').read_text())
        for period in ('airports','stressAirports'):
            count=0
            for airport in evaluation[period].values():
                for horizons in airport['directions'].values():
                    for metrics in horizons.values():
                        if metrics['trainingWindowsWithFaaActivity']!=0: continue
                        count+=1
                        self.assertEqual(metrics['faaEvidenceStatus'],'no-learned-faa-effect')
                        self.assertEqual(metrics['brierSkill'],0)
                        self.assertEqual(metrics['skillInterval95'],[0,0])
                        self.assertEqual(metrics['pValueApproximate'],1)
                        self.assertEqual(metrics['qValueApproximate'],1)
                        self.assertNotEqual(metrics['evidence'],'moderate')
                        self.assertIn('rawNumericalComparison',metrics)
            self.assertEqual(count,186)

    def test_real_operations_model_matches_portable_batch_and_missing_history_removes_probability(self):
        folder=ROOT/'public/data/airport-weather/operations'
        if not (folder/'model.json').exists(): self.skipTest('National candidate not fitted')
        model=json.loads((folder/'model.json').read_text()); evaluation=json.loads((folder/'evaluation.json').read_text())
        cutoff=ts('2026-09-12T21:35'); generated='2026-09-12T21:35:00Z'
        taf={'raw':'TAF KDFW 121800Z 1218/1400 18010KT P6SM SKC','issuedAt':'2026-09-12T18:00:00Z','firstSeenAt':'2026-09-12T18:35:00Z'}
        snapshot={'generatedAt':generated,'sources':{'forecasts':{'status':'ok','fetchedAt':generated}},'stations':{'KDFW':{'tafs':[taf]}},'faaHistory':full_history(cutoff)}
        result=score(snapshot,model,evaluation)['airports']['DFW']['directions']['departures']['6']
        self.assertEqual(result['status'],'available')
        entry=model['airportModels']['DFW']['departures_6']
        vector=wx_features('DFW',cutoff+6*3600,result['weather'],entry['featureAirports'])+list(np.zeros(6))
        batch=predict_batch(entry['operations'],np.array([vector]))
        for name,p in result['probabilities'].items(): self.assertAlmostEqual(p,batch[name][0],places=12)
        snapshot['faaHistory']['status']='error'
        missing=score(snapshot,model,evaluation)['airports']['DFW']['directions']['departures']['6']
        self.assertEqual(missing['status'],'no-faa-history'); self.assertNotIn('probabilities',missing)


if __name__=='__main__': unittest.main()
