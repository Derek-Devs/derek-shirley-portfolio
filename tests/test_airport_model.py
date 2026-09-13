import gzip
import json
import math
from pathlib import Path
import sys
import unittest
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from airport_features import parse_taf,weather_features,features,feature_names
from airport_predict import predict,score

ISSUE=datetime(2025,5,1,23,20,tzinfo=timezone.utc)
RAW='TAF KDFW 012320Z 0200/0306 18008KT P6SM SCT050 FM020800 22015G25KT 2SM RA BKN008 TEMPO 0210/0214 1SM TSRA BKN004CB PROB30 0214/0218 TSRA BKN010CB'


class FeatureTests(unittest.TestCase):
    def test_forecast_future_issue_and_partial_window_fail_closed(self):
        taf=parse_taf(RAW,ISSUE)
        self.assertIsNone(weather_features(taf,taf['start']+3600,ISSUE.timestamp()-1))
        self.assertIsNone(weather_features(taf,taf['end']-3600,ISSUE.timestamp()))
        self.assertIsNotNone(weather_features(taf,taf['end']-7200,ISSUE.timestamp()))

    def test_conditional_storm_is_a_feature_not_a_delay_probability(self):
        taf=parse_taf(RAW,ISSUE)
        v=weather_features(taf,datetime(2025,5,2,10,tzinfo=timezone.utc).timestamp(),ISSUE.timestamp())
        self.assertEqual(v[:6],[15.,25.,2.,.8,1.,1.])
        self.assertEqual(v[6:9],[0.,1.,0.])
        self.assertEqual(v[11:13],[1.,1.])
        prob=weather_features(taf,datetime(2025,5,2,14,tzinfo=timezone.utc).timestamp(),ISSUE.timestamp())
        self.assertEqual(prob[8],.3)

    def test_missing_or_unsupported_prevailing_fields_are_not_imputed_clear(self):
        for raw in [RAW.replace('18008KT ','',1),RAW.replace('SCT050',''),RAW.replace('SCT050','VV///'),RAW.replace('TEMPO','BECMG')]:
            self.assertIsNone(parse_taf(raw,ISSUE))

    def test_month_rollover_and_fractional_visibility(self):
        ref=datetime(2025,1,31,23,20,tzinfo=timezone.utc)
        taf=parse_taf('KDFW 312320Z 0100/0206 00000KT 1 1/2SM BKN010',ref)
        self.assertEqual(datetime.fromtimestamp(taf['start'],timezone.utc).date().isoformat(),'2025-02-01')
        self.assertEqual(weather_features(taf,taf['start'],ref.timestamp())[2],1.5)

    def test_feature_interface_uses_airport_local_clock_and_has_fixed_order(self):
        zones={'DFW':'America/Chicago','SEA':'America/Los_Angeles'}
        v=features('DFW',datetime(2025,5,1,17,tzinfo=timezone.utc).timestamp(),[0.]*14,zones)
        self.assertEqual(len(v),len(feature_names(zones)))
        self.assertEqual(v[:2],[1.,0.]); self.assertAlmostEqual(v[2],0.); self.assertAlmostEqual(v[3],-1.)


@unittest.skipUnless((ROOT/'public/data/airport-weather/model.json').exists(),'Run the documented training pipeline first')
class ArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((ROOT/'public/data/airport-weather/model.json').read_text())
        cls.evaluation=json.loads((ROOT/'public/data/airport-weather/evaluation.json').read_text())

    def test_probability_denominators_and_artifacts_are_consistent(self):
        self.assertEqual(self.model['version'],self.evaluation['version'])
        self.assertEqual(self.model['generatedAt'],self.evaluation['generatedAt'])
        entries=list(self.model['models'].values())+[entry for group in self.model.get('airportModels',{}).values() for entry in group.values()]
        for entry in entries:
            x=[0.]*len(entry['weather']['features']); p=predict(entry['weather'],x)
            self.assertAlmostEqual(sum(p[k] for k in ('cancelled','diverted','delayed','onTime')),1.,places=12)
            self.assertTrue(all(0<=v<=1 for v in p.values()))
            self.assertEqual(len(entry['weather']['features']),len(entry['weather']['mean']))
            self.assertTrue(all(math.isfinite(v) and v>0 for v in entry['weather']['scale']))

    def test_chronological_splits_and_common_horizon_denominators(self):
        p=self.model['protocol']; names=['train','probabilityCalibration','intervalCalibration','test']
        for a,b in zip(names,names[1:]): self.assertLess(p[a][1],p[b][0])
        for airport in self.evaluation['airports'].values():
            for horizons in airport['directions'].values():
                if any(m.get('method')=='airport-local-linear' for m in horizons.values()):
                    matched=[m['matchedHorizon'] for m in horizons.values() if 'matchedHorizon' in m]
                    if matched:
                        self.assertEqual(len(matched),len(horizons))
                        self.assertEqual(len({(m['flights'],m['windows']) for m in matched}),1)
                        for m in horizons.values(): self.assertLessEqual(m['matchedHorizon']['windows'],m['windows'])
                else:
                    self.assertEqual(len({m['flights'] for m in horizons.values()}),1)
                    self.assertEqual(len({m['windows'] for m in horizons.values()}),1)
                for m in horizons.values():
                    self.assertEqual(sum(b['flights'] for b in m['calibration']),m['flights'])
                    self.assertAlmostEqual(m['brierSkill'],1-m['brier']/m['baselineBrier'])
                    self.assertGreater(m['days'],0)
                    if m['evidence']=='moderate':
                        self.assertGreaterEqual(m['days'],p['minimumTestDaysForModerateEvidence'])

    def test_live_missing_stale_or_future_report_cannot_get_probability(self):
        snapshot={'generatedAt':'2025-05-02T10:00:00Z','sources':{'forecasts':{'status':'ok','fetchedAt':'2025-05-02T10:00:00Z'}},
                  'stations':{'KDFW':{'tafs':[{'raw':RAW,'issuedAt':'2025-05-01T23:20:00Z','firstSeenAt':'2025-05-02T10:01:00Z'}]}}}
        missing=score(snapshot,self.model,self.evaluation)
        self.assertNotIn('probabilities',missing['airports']['DFW']['directions']['departures']['6'])
        snapshot['stations']['KDFW']['tafs'][0]['firstSeenAt']='2025-05-01T23:30:00Z'
        fresh=score(snapshot,self.model,self.evaluation)
        self.assertIn('probabilities',fresh['airports']['DFW']['directions']['departures']['6'])
        snapshot['sources']['forecasts']['status']='error'
        stale=score(snapshot,self.model,self.evaluation)
        self.assertNotIn('probabilities',stale['airports']['DFW']['directions']['departures']['6'])

    def test_sparse_overnight_blocks_are_not_extrapolated(self):
        snapshot={'generatedAt':'2025-05-02T00:00:00Z','sources':{'forecasts':{'status':'ok','fetchedAt':'2025-05-02T00:00:00Z'}},
                  'stations':{'KDFW':{'tafs':[{'raw':RAW,'issuedAt':'2025-05-01T23:20:00Z','firstSeenAt':'2025-05-01T23:30:00Z'}]}}}
        item=score(snapshot,self.model,self.evaluation)['airports']['DFW']['directions']['departures']['6']
        self.assertEqual(item['status'],'low-data'); self.assertNotIn('probabilities',item)

    def test_portable_serving_matches_evaluation_math(self):
        import numpy as np
        from airport_train import predict as batch_predict
        rng=np.random.default_rng(8)
        for entry in self.model['models'].values():
            model=entry['weather']; x=np.array(model['mean'])+rng.normal(size=len(model['mean']))*np.array(model['scale'])
            one=predict(model,x); batch=batch_predict(model,x.reshape(1,-1))
            for name in one: self.assertAlmostEqual(one[name],batch[name][0],places=12)

    def test_changed_feature_schema_or_missing_numeric_value_fails_closed(self):
        model=self.model['models']['departures_6']['weather']
        with self.assertRaises(ValueError): predict(model,[0.])
        values=[0.]*len(model['mean']); values[0]=float('nan')
        with self.assertRaises(ValueError): predict(model,values)


if __name__=='__main__': unittest.main()
