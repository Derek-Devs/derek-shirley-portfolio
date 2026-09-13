"""Observed FAA context and static runway inventory; never model inputs.

FAA schema: https://www.fly.faa.gov/fly/dtd/AirportStatus.dtd
Runways: https://ourairports.com/help/data-dictionary.html
No event in this feed is not an all-clear. Airport closures may have exceptions.
"""
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import io
import json
import math
import xml.etree.ElementTree as ET

FAA_URL = 'https://nasstatus.faa.gov/api/airport-status-information'
RUNWAYS_URL = 'https://davidmegginson.github.io/ourairports-data/runways.csv'
MAX_FAA_BYTES = 1024 * 1024
MAX_RUNWAY_BYTES = 8 * 1024 * 1024
# Documented airport rename; runway coordinates must also agree before applying it.
RUNWAY_ALIASES = {'KDJT': 'KPBI'}
FAA_ALIASES = {'PBI': 'KDJT'}
LISTS = {
    'Ground_Stop_List': ('Program', 'ground-stop'),
    'Ground_Delay_List': ('Ground_Delay', 'ground-delay'),
    'Airport_Closure_List': ('Airport', 'closure'),
    'Arrival_Departure_Delay_List': ('Delay', 'arrival-departure-delay'),
}
FIELDS = {'Avg': 'Average delay', 'Max': 'Maximum delay', 'Min': 'Minimum delay',
          'Start': 'Starts', 'Reopen': 'Reopens', 'End_Time': 'End time', 'Trend': 'Trend'}


def text(element, path, maximum=1600):
    value = element.findtext(path, '').strip()
    if len(value) > maximum:
        raise ValueError('FAA field exceeds its limit')
    return value


def stamp(value):
    return value.isoformat(timespec='seconds').replace('+00:00', 'Z')


def parse_faa(raw, airports, now):
    if len(raw) > MAX_FAA_BYTES or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('FAA XML size/entity guard')
    root = ET.fromstring(raw)
    if root.tag != 'AIRPORT_STATUS_INFORMATION':
        raise ValueError('Unexpected FAA response')
    issued = datetime.strptime(text(root, 'Update_Time', 100), '%a %b %d %H:%M:%S %Y GMT').replace(tzinfo=timezone.utc)
    if issued > now + timedelta(minutes=5):
        raise ValueError('FAA update time is in the future')
    codes = {a['icao'] for a in airports}
    lookup = {c: c for c in codes}
    # Reject ambiguous identifiers rather than assign an event to the wrong airport.
    for a in airports:
        code = a.get('iata', '')
        if code:
            lookup[code] = a['icao'] if code not in lookup or lookup[code] == a['icao'] else None
    lookup.update({alias: code for alias, code in FAA_ALIASES.items() if code in codes})
    result = {a['icao']: {'events': [], 'identifierAvailable': bool(a.get('iata'))} for a in airports}
    unmatched, omitted = set(), set()
    event_count = 0
    for group in root.findall('Delay_type'):
        containers = [el for el in group if el.tag != 'Name']
        if len(containers) != 1:
            raise ValueError('Unexpected FAA delay group')
        container = containers[0]
        if container.tag in ('CTOP_List', 'Airspace_Flow_List'):
            # These require route geometry; do not assign a national program to every airport.
            if len(container): omitted.add(container.tag)
            continue
        if container.tag not in LISTS:
            raise ValueError('Unrecognized FAA delay category')
        tag, kind = LISTS[container.tag]
        for entry in container:
            if entry.tag != tag:
                raise ValueError('Unexpected FAA delay entry')
            event_count += 1
            if event_count > 2000:
                raise ValueError('Too many FAA events')
            code = text(entry, 'ARPT', 8).upper()
            if not code or not code.isalnum():
                raise ValueError('Missing FAA airport identifier')
            event = {'type': kind, 'airportCode': code, 'reason': text(entry, 'Reason'), 'details': []}
            for field, label in FIELDS.items():
                value = text(entry, field, 200)
                if value: event['details'].append({'label': label, 'value': value})
            for direction in entry.findall('Arrival_Departure'):
                name = direction.get('Type')
                if name not in ('Arrival', 'Departure'):
                    raise ValueError('Unknown FAA delay direction')
                for field in ('Min', 'Max', 'Trend'):
                    value = text(direction, field, 200)
                    if value: event['details'].append({'label': f'{name} {FIELDS[field].lower()}', 'value': value})
            event['id'] = hashlib.sha256(json.dumps(event, sort_keys=True).encode()).hexdigest()[:20]
            destination = lookup.get(code)
            if destination:
                result[destination]['events'].append(event)
                result[destination]['identifierAvailable'] = True
            else: unmatched.add(code)
    return result, {'issuedAt': stamp(issued), 'eventCount': event_count,
                    'unmatchedAirportCodes': sorted(unmatched), 'unassignedAirspaceGroups': sorted(omitted)}


def number(value, minimum=0, maximum=25000):
    try:
        n = float(value)
        return n if math.isfinite(n) and minimum <= n <= maximum else None
    except (TypeError, ValueError):
        return None


def flag(value):
    return {'0': False, '1': True}.get(value)


def parse_runways(raw, airports):
    if len(raw) > MAX_RUNWAY_BYTES:
        raise ValueError('Runway download too large')
    rows = csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    required = {'id', 'airport_ident', 'length_ft', 'width_ft', 'surface', 'closed', 'lighted',
                'le_ident', 'he_ident', 'le_heading_degT', 'he_heading_degT', 'le_latitude_deg', 'le_longitude_deg'}
    if not required.issubset(rows.fieldnames or []):
        raise ValueError('Runway schema changed')
    by_code = {a['icao']: a for a in airports}
    aliases = {alias: code for code, alias in RUNWAY_ALIASES.items() if code in by_code}
    result = {code: {'sourceIdent': code, 'runways': []} for code in by_code}
    seen, count = set(), 0
    for row in rows:
        count += 1
        if count > 100000: raise ValueError('Runway row limit exceeded')
        ident = row['airport_ident']
        code = ident if ident in by_code else aliases.get(ident)
        if not code: continue
        if ident != code:
            airport = by_code[code]
            lat = number(row['le_latitude_deg'], -90, 90)
            lon = number(row['le_longitude_deg'], -180, 180)
            if lat is None or lon is None or airport.get('lat') is None or airport.get('lon') is None:
                raise ValueError('Runway alias coordinates unavailable')
            if abs(lat - airport['lat']) > .05 or abs(lon - airport['lon']) > .05:
                raise ValueError('Runway alias coordinates disagree')
        key = (code, row['id'])
        if not row['id'] or key in seen: raise ValueError('Duplicate runway record')
        seen.add(key)
        if result[code]['runways'] and result[code]['sourceIdent'] != ident:
            raise ValueError('Both current and historical runway identifiers need review')
        if any(len(row.get(k, '') or '') > 120 for k in ('le_ident', 'he_ident', 'surface')):
            raise ValueError('Runway field limit exceeded')
        result[code]['sourceIdent'] = ident
        result[code]['runways'].append({
            'id': row['id'], 'ends': [row['le_ident'], row['he_ident']],
            'lengthFt': number(row['length_ft'], 1), 'widthFt': number(row['width_ft'], 1, 1000),
            'surface': row['surface'], 'lighted': flag(row['lighted']), 'closed': flag(row['closed']),
            'headingsTrue': [number(row['le_heading_degT'], 0, 360), number(row['he_heading_degT'], 0, 360)],
        })
        if len(result[code]['runways']) > 30: raise ValueError('Runways per airport limit exceeded')
    # A truncated but syntactically valid CSV must not erase most of the inventory.
    matched = sum(bool(s['runways']) for s in result.values())
    if not count or matched < max(1, len(airports) * .9):
        raise ValueError('Runway catalog coverage unexpectedly low')
    for value in result.values():
        value['runways'].sort(key=lambda r: (r['closed'] is not False, -(r['lengthFt'] or 0), r['id']))
    return result, {'airportsWithRecords': matched, 'runwayRecords': len(seen)}


def enrich(stations, sources, previous, airports, fetch, now, remaining_ms=None):
    """Independent failures retain original timestamps; monthly runway attempts are cached.

    Cache lives in the existing durable snapshot, not an ephemeral Lambda directory.
    A failed publication can repeat the monthly attempt; the four-request/run ceiling
    and existing persistent hourly reservation still bound it.
    """
    at = stamp(now)
    for kind, url, parser, minimum_ms in (
        ('faa', FAA_URL, lambda raw: parse_faa(raw, airports, now), 30000),
        ('runways', RUNWAYS_URL, lambda raw: parse_runways(raw, airports), 30000),
    ):
        old_source = previous.get('sources', {}).get(kind, {})
        for code, station in stations.items():
            old = previous.get('stations', {}).get(code, {}).get(kind)
            if old is not None: station[kind] = old
        if kind == 'runways' and old_source.get('attemptedAt', '')[:7] == at[:7]:
            sources[kind] = old_source
            continue
        try:
            if remaining_ms and remaining_ms() < minimum_ms:
                sources[kind] = {**old_source, 'url': url, 'status': 'deferred'}
                continue
            raw = fetch(kind)
            # Timestamp after the download, so firstSeenAt cannot precede actual receipt.
            received = stamp(datetime.now(timezone.utc))
            values, coverage = parser(raw)
            for code, value in values.items():
                if kind == 'faa':
                    old_events = {event['id']: event for event in stations[code].get(kind, {}).get('events', [])}
                    for event in value['events']:
                        event['firstSeenAt'] = old_events.get(event['id'], {}).get('firstSeenAt', received)
                stations[code][kind] = value
            sources[kind] = {'url': url, 'status': 'ok', 'fetchedAt': received, 'attemptedAt': at,
                             'sha256': hashlib.sha256(raw).hexdigest(), **coverage}
        except Exception as error:
            sources[kind] = {**old_source, 'url': url, 'status': 'error', 'attemptedAt': at,
                             'error': type(error).__name__}
            print(f'{kind}: {type(error).__name__}', flush=True)
