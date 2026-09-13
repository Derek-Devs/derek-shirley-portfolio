from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from airport_operations_history import parse_listing, requested_dates, SPEC
from airport_operations_pilot_features import parse_direction_taf, directional_features, faa_features
from airport_features import parse_taf, weather_features
from airport_operations_pilot import matrix, VARIANTS, paired_blocks


def ts(text):
    return datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()


def listing(rows,day='2024-01-01'):
    body=''.join('<tr>'+''.join(f'<td>{c}</td>' for c in row)+'</tr>' for row in rows)
    return (f'<th>ATCSCC ADVISORIES FOR {day}</th>'+body).encode()


def advisory(number,element,title,sent='01/01/24 09:50'):
    return [f'<a href="/adv/adv_otherdis?adv_date=01012024&amp;advn={number}">{number}</a>',element,'01/01/24',title,sent]


class OperationsPilotTests(unittest.TestCase):
    def test_faa_exact_airport_and_program_match(self):
        raw=listing([advisory(1,'DFW/ZFW','CDM GROUND STOP'),advisory(2,'DFW/ZFW','CDM GS CNX'),
            advisory(3,'JFK/ZNY','CDM GROUND DELAY PROGRAM'),advisory(4,'DCC','DFW DAL CDRS_FYI'),
            advisory(5,'DFWX','CDM GROUND STOP')])
        parsed=parse_listing(raw,'2024-01-01')
        self.assertEqual(parsed['totalAdvisories'],5)
        self.assertEqual([(r['airport'],r['kind'],r['cancelled']) for r in parsed['records']],
            [('DFW','gs',False),('DFW','gs',True),('JFK','gdp',False)])

    def test_untrusted_missing_or_ambiguous_archive_never_becomes_zero(self):
        for raw in (b'error',listing([]),listing([advisory(1,'DFW','CDM GROUND STOP')],day='2024-01-02'),
            listing([advisory(1,'DFW','CDM GROUND STOP')]*2),listing([advisory(1,'DFW','CDM GROUND STOP','01/02/24 00:01')])):
            with self.assertRaises(ValueError): parse_listing(raw,'2024-01-01')

    def test_faa_publication_embargo_hourly_replay_and_future_invariance(self):
        times=[ts('2024-01-01T09:49'),ts('2024-01-01T09:51'),ts('2024-01-01T12:00')]
        records=[{'published':t,'kind':'gs','cancelled':False} for t in times]
        days={'2023-12-31','2024-01-01'}; index={'DFW':(times,records)}
        first=faa_features('DFW',ts('2024-01-01T10:00'),days,index)
        np.testing.assert_allclose(first[:2],np.log(2))
        np.testing.assert_array_equal(first,faa_features('DFW',ts('2024-01-01T10:59'),days,index))
        np.testing.assert_array_equal(first,faa_features('DFW',ts('2024-01-01T10:00'),days,{'DFW':(times[:1],records[:1])}))
        self.assertIsNone(faa_features('DFW',ts('2024-01-01T10:00'),{'2024-01-01'},index))
        np.testing.assert_array_equal(faa_features('DFW',ts('2024-01-01T10:00'),days,index,70),np.zeros(6))

    def test_direction_extension_preserves_original_weather_values(self):
        raw='TAF KDFW 010000Z 0100/0206 09010KT P6SM SKC FM011200 18020G30KT P6SM BKN020 TEMPO 0112/0114 27025G35KT 2SM TSRA BKN008'
        ref=datetime(2024,1,1,tzinfo=timezone.utc); target=ts('2024-01-01T12:00'); cutoff=ts('2024-01-01T06:00')
        a=parse_taf(raw,ref); b=parse_direction_taf(raw,ref)
        self.assertEqual(weather_features(a,target,cutoff),weather_features(b,target,cutoff))
        self.assertEqual([p['direction'] for p in b['prevailing']],[90,180])
        self.assertEqual(b['conditional'][0]['direction'],270)
        v=directional_features(b,target,cutoff,[{'heading':0}])
        self.assertAlmostEqual(v['runway'][0],35)
        self.assertEqual(v['runway'][0],v['runway'][2])

    def test_crosswind_alignment_and_reciprocal_runway(self):
        ref=datetime(2024,1,1,tzinfo=timezone.utc)
        f=parse_direction_taf('TAF KDFW 010000Z 0100/0206 09020G30KT P6SM SKC',ref)
        args=(f,ts('2024-01-01T12:00'),ts('2024-01-01T06:00'))
        self.assertAlmostEqual(directional_features(*args,[{'heading':0}])['runway'][0],30)
        self.assertAlmostEqual(directional_features(*args,[{'heading':90}])['runway'][0],0)
        self.assertAlmostEqual(directional_features(*args,[{'heading':270}])['runway'][0],0)
        self.assertAlmostEqual(directional_features(*args,[{'heading':0},{'heading':90}])['runway'][1],15)

    def test_variable_and_unspecified_conditional_wind_are_distinct(self):
        ref=datetime(2024,1,1,tzinfo=timezone.utc)
        f=parse_direction_taf('TAF KDFW 010000Z 0100/0206 VRB10G20KT P6SM SKC TEMPO 0112/0114 2SM RA BKN008',ref)
        v=directional_features(f,ts('2024-01-01T12:00'),ts('2024-01-01T06:00'),[{'heading':0}])
        self.assertEqual(v['direction'],[0,0,20])
        self.assertEqual(v['runway'],[20,20,20])
        self.assertIsNone(directional_features(f,ts('2024-01-02T06:00'),ts('2024-01-01T06:00'),[{'heading':0}]))

    def test_targets_and_actual_volume_do_not_enter_features(self):
        row={'start':ts('2024-01-01T12:00'),'airport':'DFW','n':50,'cancelled':2,
            'weather':{'6':[10,15,6,5,0,0,0,0,0,0,0,0,0,2]},
            'operations':{'6':{'direction':[1,2,0],'runway':[2,3,0],'faa':[0]*6,'faaDelayed':[0]*6}}}
        altered={**row,'n':9999,'cancelled':9999,'delayed':9999,'diverted':9999}
        for variant in VARIANTS:
            np.testing.assert_array_equal(matrix([row],'DFW',6,variant),matrix([altered],'DFW',6,variant))

    def test_paired_blocks_retain_same_flight_weights(self):
        rows=[{'n':10,'cancelled':1,'delayed':1,'diverted':0,'block':1},
            {'n':20,'cancelled':2,'delayed':2,'diverted':0,'block':1}]
        predictions={v:{'disruption':np.array([.2,.2])} for v in VARIANTS}
        block=paired_blocks(rows,predictions)['1']
        np.testing.assert_allclose(block[:-1],4.8)
        self.assertEqual(block[-1],30)

    def test_bounded_dates_and_disjoint_chronological_splits(self):
        self.assertLess(len(requested_dates()),SPEC['budget']['maxHttpAttempts'])
        periods=['train','probabilityCalibration','intervalCalibration','test','previouslySeenStressTest']
        for a,b in zip(periods,periods[1:]): self.assertLess(SPEC[a][1],SPEC[b][0])


if __name__=='__main__': unittest.main()
