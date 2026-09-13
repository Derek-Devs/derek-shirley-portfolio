"""Scientific invariants for model selection, export, calibration, and publication."""
from pathlib import Path
import sys
import unittest
import json
import tempfile
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import airport_train_v2 as train
from airport_models import logit_many,logit_one,predict_batch,interval_offsets
from airport_predict import predict


class ExperimentTests(unittest.TestCase):
    def test_all_folds_have_real_temporal_gaps_and_final_test_is_unused(self):
        from datetime import date
        for spec in [train.P,*train.P['folds']]:
            keys=['train','probabilityCalibration','intervalCalibration','test']
            for a,b in zip(keys,keys[1:]): self.assertLess(spec[a][1],spec[b][0])
            self.assertGreater((date.fromisoformat(spec['test'][0])-date.fromisoformat(spec['intervalCalibration'][1])).days,90)
        self.assertLess(max(f['test'][1] for f in train.P['folds']),train.P['intervalCalibration'][0])
        self.assertEqual(train.P['test'],['2026-01-03','2026-02-26'])

    def test_data_loader_does_not_open_final_calibration_or_test_during_selection(self):
        entries=[{'month':f'{year}-{month:02d}'} for year in (2023,2024,2025,2026) for month in range(1,13)]
        opened=[]
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'inventory.json').write_text(json.dumps(entries))
            import gzip
            for entry in entries:
                (root/f"joined-{entry['month']}.json.gz").write_bytes(gzip.compress(b'{"rows":[]}'))
            original=Path.read_bytes
            def tracked(path): opened.append(path.name); return original(path)
            with patch.object(train,'DATA',root),patch.object(Path,'read_bytes',tracked): train.load_rows(False)
        self.assertEqual(len(opened),24)
        self.assertFalse(any('2025' in name or '2026' in name for name in opened))

    def test_histogram_export_matches_native_at_thresholds_and_extremes(self):
        rng=np.random.default_rng(18); x=rng.normal(size=(600,5))
        total=np.full(600,100.); rate=1/(1+np.exp(-(x[:,0]*2+x[:,1]*x[:,2])))
        head=train.fit_head(x,np.round(total*rate),total,'boosted')
        native=head.pop('_native'); probes=[x]
        for tree in head['trees'][:10]:
            for feature,threshold,*_ in tree:
                if feature>=0:
                    p=np.zeros((3,5)); p[:,feature]=[np.nextafter(threshold,-np.inf),threshold,np.nextafter(threshold,np.inf)]; probes.append(p)
        probes=np.concatenate(probes)
        np.testing.assert_allclose(logit_many(head,probes),native.decision_function(probes),atol=1e-10,rtol=0)
        for i in range(0,len(probes),17): self.assertAlmostEqual(logit_one(head,probes[i]),native.decision_function(probes[i:i+1])[0],places=10)

    def test_airport_calibrator_and_tree_serving_conserve_probability(self):
        head={'trees':[[[0,.5,1,2,0],[-1,0,0,0,-.3],[-1,0,0,0,.2]]],'intercept':-.8,
              'calibration':{'coef':[1.,.1,-.2],'intercept':.1,'airportCount':2}}
        model={'mean':[0.,0.],'scale':[1.,1.],'heads':{name:head for name in ('cancelled','diverted','delayed')}}
        for vector in ([1.,0.],[0.,1.]):
            one=predict(model,vector); batch=predict_batch(model,np.array([vector]))
            self.assertAlmostEqual(sum(one[k] for k in ('cancelled','diverted','delayed','onTime')),1.)
            for key in one: self.assertAlmostEqual(one[key],batch[key][0],places=12)

    def test_asymmetric_intervals_use_risk_bin_then_airport_fallback(self):
        spec={'global':[-.1,.3],'bins':{'0':[-.03,.2]}}
        self.assertEqual(interval_offsets(spec,.2),[-.03,.2]); self.assertEqual(interval_offsets(spec,.6),[-.1,.3])
        self.assertEqual(interval_offsets(.15,.2),(-.15,.15))

    def test_multiple_testing_adjustment_cannot_make_p_values_smaller(self):
        reports=[{'pValueApproximate':p,'days':60,'flights':10000,'skillInterval95':[.01,.1],'calibrationError':.02,'bandCoverage':.81} for p in (.001,.02,.09,.8)]
        train.adjust_evidence(reports)
        for r in reports: self.assertGreaterEqual(r['qValueApproximate'],r['pValueApproximate'])
        self.assertEqual(reports[-1]['evidence'],'limited')
        self.assertEqual(reports[0]['evidence'],'moderate')

    def test_bands_are_checked_with_interval_score_not_width_alone(self):
        rows=[{'airport':'DFW','localDate':f'2026-01-{i+3:02d}','block':i//3,'n':100,'cancelled':0,'diverted':0,'delayed':40,'onTime':60,'weather':{'6':[0]*14}} for i in range(20)]
        p={k:np.full(20,v) for k,v in {'cancelled':0.,'diverted':0.,'delayed':.4,'onTime':.6,'disruption':.4}.items()}
        train.metrics.horizon=6
        narrow=train.metrics(rows,p,p,{'global':[-.1,.1],'bins':{},'windows':200})
        wide=train.metrics(rows,p,p,{'global':[-.4,.6],'bins':{},'windows':200})
        self.assertLess(narrow['intervalScore'],wide['intervalScore'])
        self.assertEqual(narrow['bandCoverage'],wide['bandCoverage'])


if __name__=='__main__': unittest.main()
