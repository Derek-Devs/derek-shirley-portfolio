"""Expansion invariants: local outcomes, partial horizons, mapped stations, no blind fallback."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
import io
import zipfile
from unittest.mock import patch
import numpy as np
import pandas as pd
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import airport_train_v3 as train
import airport_prepare_v3 as prep
from airport_features import parse_taf, weather_features
from airport_predict import score


class ExpansionTests(unittest.TestCase):
    def test_misfiled_forecast_is_quarantined_and_does_not_reuse_old_weather(self):
        import airport_prepare_v2 as base
        output=io.BytesIO()
        with zipfile.ZipFile(output,'w') as z:
            z.writestr('TAFLGA_202404170832.txt','TAF KJFK 170830Z 1709/1812 09010KT P6SM SKC')
            z.writestr('TAFLGA_202404170900.txt','TAF KLGA 170900Z 1709/1812 18015KT P6SM SKC')
        with patch.object(base,'fetch',return_value=output.getvalue()):
            forecasts,manifest=base.weather_batch('2024-04',['LGA'],0)
        self.assertEqual(manifest['qa']['stationMismatch'],1)
        self.assertEqual(len(forecasts['LGA']),2)
        self.assertEqual(forecasts['LGA'][0]['start'],0)
        self.assertEqual(forecasts['LGA'][1]['station'],'KLGA')

    def test_us_non_k_station_ids_are_parsed_without_changing_weather_units(self):
        ref=datetime(2026,9,12,0,tzinfo=timezone.utc)
        for station in ('PANC','PHNL','TJSJ','PGUM','NSTU'):
            taf=parse_taf(f'TAF {station} 112330Z 1200/1306 09010KT P6SM SCT025',ref)
            self.assertEqual(taf['station'],station)
            self.assertIsNotNone(weather_features(taf,ref.timestamp()+6*3600,ref.timestamp()))

    def test_missing_long_forecast_does_not_remove_valid_short_horizons(self):
        ref=datetime(2026,1,10,0,tzinfo=timezone.utc)
        taf=parse_taf('TAF KABQ 100000Z 1000/1100 09010KT P6SM SKC',ref)
        row={'airport':'ABQ','direction':'departures','start':ref.timestamp()+12*3600,
             'n':20,'cancelled':0,'diverted':0,'delayed':3,'onTime':17,'unknown':0}
        rows,qa=prep.join_rows(pd.DataFrame([row]),{'ABQ':[taf]},train.P)
        self.assertEqual(len(rows),1)
        self.assertIsNone(rows[0]['weather']['24'])
        self.assertIsNotNone(rows[0]['weather']['6'])
        self.assertEqual(qa['ABQ_departures_included_6'],1)

    def test_airport_local_fit_refuses_foreign_outcomes(self):
        with self.assertRaisesRegex(ValueError,'another airport'):
            train.fit_airport('ABQ',[{'airport':'DFW'}])

    def test_temporal_splits_never_fit_on_calibration_or_test_rows(self):
        rows=[{'airport':'ABQ','direction':'departures','localDate':train.P[k][0],'weather':{'6':[0]*14}} for k in train.P if k in train.PERIODS]
        splits=train.eligible_splits(rows,train.P,'departures',6)
        self.assertEqual(len(splits['train']),1)
        self.assertEqual(len(splits['test']),1)
        self.assertFalse(set(r['localDate'] for r in splits['train'])&set(r['localDate'] for r in splits['test']))

    def test_untested_airport_never_falls_back_to_pooled_model(self):
        protocol={**train.P,'airports':{'HNL':'Pacific/Honolulu'},'stations':{'HNL':'PHNL'}}
        model={'version':'test','generatedAt':'2026-09-12T00:00:00Z','protocol':protocol,
               'models':{f'{d}_{h}':{'invalid':'must never be used'} for d in ('departures','arrivals') for h in (6,12,24)},
               'airportModels':{'HNL':{}},'airportCoverage':{}}
        snapshot={'generatedAt':model['generatedAt'],'sources':{'forecasts':{'status':'ok','fetchedAt':model['generatedAt']}},
                  'stations':{'PHNL':{'tafs':[{'issuedAt':'2026-09-11T23:30:00Z','firstSeenAt':'2026-09-11T23:40:00Z',
                     'raw':'TAF PHNL 112330Z 1200/1306 09010KT P6SM SCT025'}]}}}
        result=score(snapshot,model,{'airports':{'HNL':{'directions':{}}}})
        for directions in result['airports']['HNL']['directions'].values():
            for value in directions.values():
                self.assertEqual(value['status'],'insufficient-evidence')
                self.assertNotIn('probabilities',value)

    def test_sparse_airport_records_specific_gate_failure(self):
        reason=train.support_reason({k:[] for k in train.PERIODS},train.P)
        self.assertIn('train: 0/300',reason)
        self.assertIn('test: 0/50',reason)


if __name__=='__main__': unittest.main()
