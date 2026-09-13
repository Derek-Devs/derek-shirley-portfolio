import csv
import io
import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest import TestCase, main
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import airport_operations as ops

NOW = datetime(2026, 9, 12, 18, 5, tzinfo=timezone.utc)
AIRPORTS = [{'icao': 'KLAX', 'iata': 'LAX'}, {'icao': 'KDFW', 'iata': 'DFW'},
            {'icao': 'KDJT', 'iata': 'DJT', 'lat': 26.683201, 'lon': -80.095596},
            {'icao': 'PANC', 'iata': 'ANC'}, {'icao': 'KZZZ', 'iata': ''}]


def faa(body='', at='Sat Sep 12 18:02:01 2026 GMT'):
    return f'<AIRPORT_STATUS_INFORMATION><Update_Time>{at}</Update_Time>{body}</AIRPORT_STATUS_INFORMATION>'.encode()


def group(container, entries):
    return f'<Delay_type><Name>fixture</Name><{container}>{entries}</{container}></Delay_type>'


def runway_csv(rows):
    defaults = dict(id='1', airport_ident='KLAX', length_ft='10000', width_ft='150', surface='CON',
                    closed='0', lighted='1', le_ident='09', he_ident='27', le_heading_degT='90',
                    he_heading_degT='270', le_latitude_deg='26.6832', le_longitude_deg='-80.1084')
    out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=defaults)
    writer.writeheader(); writer.writerows([{**defaults, **r} for r in rows])
    return out.getvalue().encode()


class OperationsTests(TestCase):
    def test_all_airport_categories_and_closure_exceptions_are_preserved(self):
        raw = faa(group('Airport_Closure_List', '<Airport><ARPT>LAX</ARPT><Reason>CLSD TO NON SKED GA EXC PPR</Reason><Reopen>May 28 at 16:00 UTC.</Reopen></Airport>')
                  + group('Ground_Stop_List', '<Program><ARPT>DFW</ARPT><Reason>weather</Reason><End_Time>19:00</End_Time></Program>')
                  + group('Ground_Delay_List', '<Ground_Delay><ARPT>PBI</ARPT><Avg>30 minutes</Avg><Max>1 hour</Max></Ground_Delay>')
                  + group('Arrival_Departure_Delay_List', '<Delay><ARPT>ANC</ARPT><Reason>volume</Reason><Arrival_Departure Type="Arrival"><Min>15 minutes</Min><Max>30 minutes</Max><Trend>Increasing</Trend></Arrival_Departure><Arrival_Departure Type="Departure"><Min>10 minutes</Min></Arrival_Departure></Delay>'))
        result, meta = ops.parse_faa(raw, AIRPORTS, NOW)
        self.assertEqual(meta['eventCount'], 4)
        self.assertEqual(result['KLAX']['events'][0]['reason'], 'CLSD TO NON SKED GA EXC PPR')
        self.assertEqual(result['KDJT']['events'][0]['type'], 'ground-delay')
        details = result['PANC']['events'][0]['details']
        self.assertEqual(details[0], {'label': 'Arrival minimum delay', 'value': '15 minutes'})
        self.assertEqual(details[-1]['label'], 'Departure minimum delay')
        self.assertFalse(result['KZZZ']['identifierAvailable'])

    def test_empty_valid_feed_is_distinct_from_invalid_missing_time_or_unknown_schema(self):
        result, _ = ops.parse_faa(faa(), AIRPORTS, NOW)
        self.assertEqual(result['KDFW']['events'], [])
        for raw in (b'<html/>', b'<AIRPORT_STATUS_INFORMATION/>', faa(group('New_Unknown_List', '')),
                    b'<!DOCTYPE x [<!ENTITY x "oops">]>' + faa(), faa(at='Sat Sep 12 20:02:01 2026 GMT'), b'x' * (ops.MAX_FAA_BYTES + 1)):
            with self.assertRaises((ValueError, ops.ET.ParseError)): ops.parse_faa(raw, AIRPORTS, NOW)

    def test_airspace_and_unknown_airports_do_not_get_assigned_to_every_airport(self):
        raw = faa(group('Airspace_Flow_List', '<Airspace_Flow><CTL_Element>FCA123</CTL_Element></Airspace_Flow>')
                  + group('Ground_Stop_List', '<Program><ARPT>YUL</ARPT></Program>'))
        result, meta = ops.parse_faa(raw, AIRPORTS, NOW)
        self.assertTrue(all(not s['events'] for s in result.values()))
        self.assertEqual(meta['unmatchedAirportCodes'], ['YUL'])
        self.assertEqual(meta['unassignedAirspaceGroups'], ['Airspace_Flow_List'])

    def test_runway_ends_count_once_and_missing_is_not_zero(self):
        result, _ = ops.parse_runways(runway_csv([{}, {'id': '2', 'closed': '1'},
                                   {'id': '3', 'closed': '', 'length_ft': '', 'lighted': '', 'he_heading_degT': 'nan'}]), AIRPORTS[:1])
        records = result['KLAX']['runways']
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]['ends'], ['09', '27'])
        unknown = next(r for r in records if r['id'] == '3')
        self.assertIsNone(unknown['lengthFt']); self.assertIsNone(unknown['lighted'])
        self.assertIsNone(unknown['closed']); self.assertIsNone(unknown['headingsTrue'][1])

    def test_runway_rename_requires_matching_coordinates(self):
        raw = runway_csv([{'airport_ident': 'KPBI'}])
        result, _ = ops.parse_runways(raw, [AIRPORTS[2]])
        self.assertEqual(result['KDJT']['sourceIdent'], 'KPBI')
        with self.assertRaises(ValueError): ops.parse_runways(runway_csv([{'airport_ident': 'KPBI', 'le_latitude_deg': '40'}]), [AIRPORTS[2]])

    def test_truncated_runway_catalog_and_duplicate_records_do_not_replace_cache(self):
        for raw, airports in [(runway_csv([{}]), AIRPORTS), (b'id,airport_ident\n1,KLAX', AIRPORTS[:1]),
                              (runway_csv([{}, {}]), AIRPORTS[:1])]:
            with self.assertRaises(ValueError): ops.parse_runways(raw, airports)

    def test_monthly_inventory_survives_ephemeral_runs_and_failed_attempts_do_not_retry_hourly(self):
        fetch = Mock(side_effect=lambda kind: faa() if kind == 'faa' else runway_csv([{}]))
        stations, sources = {'KLAX': {}}, {}
        ops.enrich(stations, sources, {}, AIRPORTS[:1], fetch, NOW)
        self.assertEqual(fetch.call_count, 2)
        previous = {'stations': stations, 'sources': sources}
        fetch.reset_mock(); next_stations, next_sources = {'KLAX': {}}, {}
        ops.enrich(next_stations, next_sources, previous, AIRPORTS[:1], fetch, NOW)
        self.assertEqual([c.args[0] for c in fetch.call_args_list], ['faa'])
        self.assertEqual(next_stations['KLAX']['runways'], stations['KLAX']['runways'])
        self.assertEqual(next_sources['runways']['fetchedAt'], sources['runways']['fetchedAt'])
        previous['sources']['runways']['status'] = 'error'
        failed_fetch = Mock(side_effect=OSError)
        ops.enrich({'KLAX': {}}, {}, previous, AIRPORTS[:1], failed_fetch, NOW)
        self.assertEqual([c.args[0] for c in failed_fetch.call_args_list], ['faa'])
        tomorrow = NOW.replace(month=10)
        failed_sources = {}; fetch = Mock(side_effect=OSError)
        ops.enrich({'KLAX': {}}, failed_sources, previous, AIRPORTS[:1], fetch, tomorrow)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(failed_sources['runways']['status'], 'error')
        self.assertEqual(failed_sources['runways']['fetchedAt'], sources['runways']['fetchedAt'])

    def test_removed_notice_is_removed_and_unchanged_notice_keeps_first_seen(self):
        raw = faa(group('Ground_Stop_List', '<Program><ARPT>LAX</ARPT><Reason>weather</Reason></Program>'))
        stations, sources = {'KLAX': {}}, {}
        ops.enrich(stations, sources, {}, AIRPORTS[:1], lambda k: raw if k == 'faa' else runway_csv([{}]), NOW)
        stations['KLAX']['faa']['events'][0]['firstSeenAt'] = '2026-09-12T17:30:00Z'
        previous = {'stations': stations, 'sources': sources}
        new, meta = {'KLAX': {}}, {}
        ops.enrich(new, meta, previous, AIRPORTS[:1], lambda k: raw, NOW)
        self.assertEqual(new['KLAX']['faa']['events'][0]['firstSeenAt'], '2026-09-12T17:30:00Z')
        ops.enrich(new, meta, previous, AIRPORTS[:1], lambda k: faa(), NOW)
        self.assertEqual(new['KLAX']['faa']['events'], [])

    def test_low_runtime_defers_context_without_network_and_preserves_old_timestamps(self):
        previous = {'stations': {'KLAX': {'faa': {'events': [], 'identifierAvailable': True}}},
                    'sources': {'faa': {'fetchedAt': '2026-09-12T16:00:00Z', 'status': 'ok'}}}
        fetch = Mock(); new, meta = {'KLAX': {}}, {}
        ops.enrich(new, meta, previous, AIRPORTS[:1], fetch, NOW, lambda: 20000)
        fetch.assert_not_called()
        self.assertEqual(meta['faa']['status'], 'deferred')
        self.assertEqual(meta['faa']['fetchedAt'], previous['sources']['faa']['fetchedAt'])
        self.assertNotIn('attemptedAt', meta['runways'])


if __name__ == '__main__': main()
