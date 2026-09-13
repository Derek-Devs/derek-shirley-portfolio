import calendar
from datetime import date,datetime,timedelta
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import airport_traffic_proxy as proxy


class TrafficProxyTests(unittest.TestCase):
    def test_release_embargo_excludes_target_and_future_months(self):
        available=[f'{y}-{m:02d}' for y in (2023,2024,2025,2026) for m in range(1,13)]
        for target in available:
            cutoff=datetime.strptime(target+'-01','%Y-%m-%d').date()-timedelta(days=1)
            chosen=proxy.source_months(target,available)
            self.assertLessEqual(len(chosen),12)
            for month in chosen:
                y,m=map(int,month.split('-')); last=date(y,m,calendar.monthrange(y,m)[1])
                self.assertLess(last+timedelta(days=120),cutoff)
                self.assertLess(month,target)

    def test_missing_months_are_not_inserted_as_zero(self):
        available=['2025-06','2025-07','2025-08','2025-09','2026-01']
        chosen=proxy.source_months('2026-03',available)
        self.assertNotIn('2026-01',chosen)
        self.assertNotIn('2025-10',chosen)

    def test_source_exposure_includes_zero_flight_blocks_but_not_excluded_dates(self):
        exposure=proxy.month_exposure('2024-02','America/Chicago',2)
        self.assertEqual(exposure.sum(),25*12)
        spring=proxy.month_exposure('2024-03','America/Chicago',2)
        self.assertEqual(spring.sum(),27*12-1)

    def test_profiles_are_immune_to_future_traffic_and_include_zero_windows(self):
        months={m:{'sums':np.ones((7,12,2))*12,'exposure':np.ones((7,12))*6} for m in ['2023-01','2023-02','2023-03','2023-04']}
        first=proxy.traffic_profile('2023-09',months)
        self.assertIsNotNone(first)
        np.testing.assert_allclose(first['expected'],2)
        months['2023-08']={'sums':np.ones((7,12,2))*999999,'exposure':np.ones((7,12))}
        second=proxy.traffic_profile('2023-09',months)
        np.testing.assert_array_equal(first['expected'],second['expected'])
        months['2023-01']['sums'][0,0]=0
        self.assertLess(proxy.traffic_profile('2023-09',months)['expected'][0,0,0],2)

    def test_actual_window_outcomes_and_volume_do_not_enter_predictors(self):
        r={'start':1704207600,'airport':'DFW','n':50,'cancelled':2,'weather':{'6':[10,15,6,5,0,0,0,0,0,0,0,0,0,2]},'traffic':[2,3,1.1,4]}
        changed={**r,'n':999999,'cancelled':999999}
        for variant in proxy.VARIANTS:
            np.testing.assert_array_equal(proxy.matrix([r],'DFW',6,variant),proxy.matrix([changed],'DFW',6,variant))


if __name__=='__main__': unittest.main()
