import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import airport_weather as weather
import airport_history as history


class WeatherTests(unittest.TestCase):
    def test_us_scope_uses_country_and_includes_non_k_icao_codes(self):
        airports = [{'icao': 'KDFW', 'country': 'US'}, {'icao': 'PANC', 'country': 'US'},
                    {'icao': 'PHNL', 'country': 'US'}, {'icao': 'TJSJ', 'country': 'PR'},
                    {'icao': 'PGUM', 'country': 'GU'}, {'icao': 'CYVR', 'country': 'CA'},
                    {'icao': 'KZZZ', 'country': 'GB'}, {'icao': 'XXXX'}]
        scoped = weather.scope_catalog({'airports': airports})
        self.assertEqual([a['icao'] for a in scoped['airports']], ['KDFW', 'PANC', 'PHNL', 'TJSJ', 'PGUM'])
        self.assertEqual(len(airports), 8)
        old = {'generatedAt': '2025-05-01T00:00:00Z', 'stations': {a['icao']: {} for a in airports}}
        projected = weather.scope_snapshot(old, scoped)
        self.assertEqual(set(projected['stations']), {a['icao'] for a in scoped['airports']})
        self.assertEqual(projected['generatedAt'], old['generatedAt'])

    def test_legacy_global_catalog_and_feed_publish_only_us_weather(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(weather, 'STATE', root / 'state'), patch.object(weather, 'PUBLIC', root / 'public'):
                weather.atomic_json(weather.PUBLIC / 'airports.json', {'airports': [
                    {'icao': 'KDFW', 'country': 'US'}, {'icao': 'PANC', 'country': 'US'},
                    {'icao': 'EGLL', 'country': 'GB'}]})
                stale = weather.PUBLIC / 'stations' / 'EG.json'
                weather.atomic_json(stale, {'stations': {'EGLL': {}}})
                reports = {'KDFW': {'id': 'us', 'firstSeenAt': '2025-01-01T00:00:00Z'},
                           'EGLL': {'id': 'uk', 'firstSeenAt': '2025-01-01T00:00:00Z'}}
                with patch.object(weather, 'fetch', return_value=b'feed'), patch.object(weather, 'parse_xml', side_effect=[reports, reports]), patch('airport_predict.publish_risk', return_value=0):
                    weather.refresh()
                stored = weather.read_json(weather.STATE / 'latest.json', {})
                summary = weather.read_json(weather.PUBLIC / 'latest.json', {})
                self.assertEqual(set(stored['stations']), {'KDFW', 'PANC'})
                self.assertIsNone(stored['stations']['PANC']['observation'])
                self.assertEqual(summary['coverage']['airports'], 2)
                self.assertEqual(summary['coverage']['observations'], 1)
                self.assertEqual(summary['sources']['observations']['reportCount'], 1)
                self.assertFalse(stale.exists())

    def test_empty_or_entity_xml_does_not_replace_good_data(self):
        for xml in (b'<response><data/></response>', b'<!DOCTYPE response [<!ENTITY x "x">]><response/>'):
            with self.assertRaises(ValueError):
                weather.parse_xml(gzip.compress(xml), 'observations', '2025-05-01T00:00:00Z')

    def test_xml_preserves_censored_visibility_and_missing_wind(self):
        xml = b'<response><data><METAR><station_id>KDFW</station_id><raw_text>test</raw_text><observation_time>2025-05-01T00:00:00Z</observation_time><visibility_statute_mi>6+</visibility_statute_mi><sky_condition sky_cover="BKN" cloud_base_ft_agl="900"/></METAR></data></response>'
        parsed = weather.parse_xml(gzip.compress(xml), 'observations', '2025-05-01T00:05:00Z')['KDFW']
        self.assertEqual(parsed['visibilityMi'], '6+')
        self.assertIsNone(parsed['windKt'])
        self.assertEqual(parsed['clouds'][0]['baseFt'], 900)

    def test_quota_exhaustion_fails_before_network(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(weather, 'STATE', Path(directory)), patch('urllib.request.build_opener') as network:
            weather.atomic_json(weather.STATE / 'usage.json', {'month': weather.utc_now().strftime('%Y-%m'), 'requests':weather.MAX_REQUESTS_PER_MONTH})
            with self.assertRaises(RuntimeError):
                weather.fetch('observations')
            network.assert_not_called()

    def test_unknown_or_paid_provider_cannot_be_requested(self):
        with self.assertRaises(ValueError):
            weather.fetch('paid-flight-api')

    def test_existing_lock_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(weather, 'STATE', Path(directory)):
            (weather.STATE / 'collector.lock').write_text('other process')
            with self.assertRaises(RuntimeError):
                weather.locked(lambda: self.fail('Concurrent action ran'))

    def test_second_attempt_in_same_hour_does_not_fetch(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(weather, 'STATE', Path(directory)), patch.object(weather, 'fetch') as network:
            weather.atomic_json(weather.STATE / 'attempt.json', {'hour':weather.utc_now().strftime('%Y-%m-%dT%H')})
            weather.refresh()
            network.assert_not_called()

    def test_month_rollover_reserves_new_quota_before_failed_request(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(weather, 'STATE', Path(directory)), patch('urllib.request.build_opener', side_effect=OSError('offline')):
            weather.atomic_json(weather.STATE / 'usage.json', {'month':'2001-01','requests':1600})
            with self.assertRaises(OSError):
                weather.fetch('observations')
            self.assertEqual(weather.read_json(weather.STATE / 'usage.json', {})['requests'], 1)


class HistoryTests(unittest.TestCase):
    def test_outcomes_are_mutually_exclusive_and_missing_stays_unknown(self):
        row = {'Cancelled':'1','Diverted':'0','DepDelay':'','ArrDelay':''}
        self.assertEqual(history.outcome(row,'departures'),'cancelled')
        self.assertEqual(history.outcome({**row,'Cancelled':'0','Diverted':'1','ArrDelay':'90'},'arrivals'),'diverted')
        self.assertEqual(history.outcome({**row,'Cancelled':'0'},'arrivals'),'unknown')
        self.assertEqual(history.outcome({**row,'Cancelled':'0','DepDelay':'15'},'departures'),'delayed')
        self.assertEqual(history.outcome({**row,'Cancelled':'0','DepDelay':'14'},'departures'),'onTime')

    def test_midnight_and_dst_are_not_silently_shifted(self):
        self.assertEqual(history.clock_minutes('2400'), 1440)
        for date in (datetime(2025,3,9,2,30), datetime(2025,11,2,1,30)):
            with self.assertRaises(ValueError):
                history.local_to_utc(date, ZoneInfo('America/Chicago'))

    def test_arrival_date_uses_elapsed_time_and_origin_timezone(self):
        row = {'FlightDate':'2025-05-01','OriginState':'CA','CRSDepTime':'2300','CRSArrTime':'0400','CRSElapsedTime':'180'}
        self.assertEqual(history.scheduled_dfw(row,'arrivals'), datetime(2025,5,2,9,tzinfo=timezone.utc))

    def test_as_of_selects_only_available_issues_and_reports_partial_coverage(self):
        target = datetime(2025,5,2,18,tzinfo=timezone.utc)
        early = {'id':'early','issuedAt':'2025-05-01T17:00:00Z','validFrom':'2025-05-01T18:00:00Z','validTo':'2025-05-02T19:00:00Z',
                 'periods':[{'from':'2025-05-01T18:00:00Z','to':'2025-05-02T19:00:00Z'}]}
        late = {**early,'id':'late','issuedAt':'2025-05-01T17:55:00Z'}
        forecast = history.as_of([early,late],target,24)
        self.assertEqual(forecast['productId'],'early')
        self.assertEqual(forecast['coverage'],'partial')

    def test_taf_header_crosses_month_and_24_hour_boundary(self):
        issue = datetime(2025,5,31,18,tzinfo=timezone.utc)
        self.assertEqual(history.taf_datetime('0124',issue), datetime(2025,6,2,tzinfo=timezone.utc))

    def test_published_replay_reconciles_denominators_and_cutoffs(self):
        path = weather.PUBLIC / 'replay.json'
        if not path.exists():
            self.skipTest('Historical sample has not been prepared')
        data = json.loads(path.read_text(encoding='utf-8'))
        for window in data['windows']:
            counts = window['counts']
            self.assertEqual(sum(counts[k] for k in ['onTime','delayed','cancelled','diverted','unknown']), counts['scheduled'])
            for horizon, forecast in window['forecasts'].items():
                if forecast:
                    cutoff = history.parse_time(forecast['cutoff'])
                    self.assertEqual(cutoff, history.parse_time(window['start']) - timedelta(hours=int(horizon)))
                    self.assertLessEqual(history.parse_time(forecast['issuedAt']) + timedelta(minutes=10), cutoff)


if __name__ == '__main__':
    unittest.main()
