"""One strict US TAF feature extractor shared by historical training and live scoring.

Supported: initial prevailing, FM, TEMPO, PROB30/40 (optionally TEMPO).
BECMG, NIL, cancellation, or missing mandatory prevailing fields fail closed.
No observed weather or flight outcome is accepted by this feature interface.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import math
import re
from zoneinfo import ZoneInfo

WEATHER_NAMES = ["wind_max", "gust_max", "visibility_min", "ceiling_min", "low_visibility",
                 "low_ceiling", "thunderstorm", "temporary_thunderstorm", "prob_thunderstorm",
                 "rain", "snow_ice", "conditional_low_visibility", "conditional_low_ceiling", "forecast_age"]
CHANGE = re.compile(r"\b(FM\d{6}|(?:PROB(?:30|40)(?:\s+TEMPO)?|TEMPO|BECMG)\s+\d{4}/\d{4})\b")


def day_time(token, reference, minutes=False):
    day = int(token[:2]); hour = int(token[2:4]); minute = int(token[4:]) if minutes else 0
    dates = []
    for offset in (-1, 0, 1):
        year = reference.year + (reference.month - 1 + offset) // 12
        month = (reference.month - 1 + offset) % 12 + 1
        try:
            dates.append(datetime(year, month, day, tzinfo=timezone.utc) + timedelta(hours=hour, minutes=minute))
        except ValueError:
            pass
    return min(dates, key=lambda value: abs((value-reference).total_seconds()))


def conditions(text):
    wind = re.search(r"(?:^|\s)(?:\d{3}|VRB)(\d{2,3})(?:G(\d{2,3}))?KT\b", text)
    visibility = re.search(r"(?:^|\s)(P?)(\d+\s+\d/\d|\d/\d|\d+(?:\.\d+)?)SM\b", text)
    vis = None
    if visibility:
        def fraction(value):
            if '/' in value:
                a, b = value.split('/'); return float(a)/float(b)
            return float(value)
        vis = min(6., sum(fraction(v) for v in visibility[2].split()))
    cloud = re.findall(r"\b(FEW|SCT|BKN|OVC|VV)(\d{3}|///)(?:CB|TCU)?\b", text)
    ceiling = None
    if cloud or re.search(r"\b(SKC|CLR|NSC)\b", text):
        ceiling = 10000.
        for cover, base in cloud:
            if cover in ('BKN', 'OVC', 'VV'):
                if base == '///':
                    ceiling = None; break
                ceiling = min(ceiling, int(base)*100)
    return {"wind":float(wind[1]) if wind else None,
            "gust":float(wind[2] or wind[1]) if wind else None,
            "vis":vis, "ceiling":ceiling, "ts":float('TS' in text),
            "rain":float(bool(re.search(r'RA|DZ',text))), "ice":float(bool(re.search(r'SN|FZ|PL',text)))}


def parse_taf(raw, reference):
    text = ' '.join(raw.replace('=', ' ').split())
    header = re.search(r"\b([A-Z][A-Z0-9]{3})\s+(\d{6})Z\s+(\d{4})/(\d{4})\s+", text)
    if not header or re.search(r'\b(NIL|CNL|BECMG)\b', text):
        return None
    issued = day_time(header[2], reference, True)
    start = day_time(header[3], issued)
    end = day_time(header[4], start)
    if not start < end <= start + timedelta(hours=36):
        return None
    body = text[header.end():]
    matches = list(CHANGE.finditer(body))
    prevailing = [{"start":start.timestamp(), "end":end.timestamp(), "conditions":conditions(body[:matches[0].start()] if matches else body)}]
    conditional = []
    for index, match in enumerate(matches):
        label = match[1]; segment = body[match.end():matches[index+1].start() if index+1<len(matches) else len(body)]
        if label.startswith('FM'):
            at = day_time(label[2:], start, True).timestamp()
            prevailing[-1]['end'] = at
            prevailing.append({"start":at, "end":end.timestamp(), "conditions":conditions(segment)})
        else:
            interval = re.search(r'(\d{4})/(\d{4})',label)
            a = day_time(interval[1],start); b = day_time(interval[2],a)
            if not a < b:
                return None
            conditional.append({"start":a.timestamp(),"end":b.timestamp(),"conditions":conditions(segment),
                                "probability":int(label[4:6])/100 if label.startswith('PROB') else None})
    for part in prevailing:
        if part['start'] >= part['end'] or any(part['conditions'][k] is None for k in ('wind','gust','vis','ceiling')):
            return None
    return {"station":header[1], "issued":issued.timestamp(), "productTime":reference.timestamp(),
            "start":start.timestamp(),"end":end.timestamp(),"prevailing":prevailing,"conditional":conditional}


def weather_features(forecast, target, cutoff, hours=2):
    end = target + hours*3600
    if not forecast or forecast['start'] > target or forecast['end'] < end or forecast['issued'] > cutoff:
        return None
    base = [p for p in forecast['prevailing'] if p['start'] < end and p['end'] > target]
    if not base or sum(max(0,min(end,p['end'])-max(target,p['start'])) for p in base) < hours*3600-1:
        return None
    c = [p['conditions'] for p in base]
    conditional = [p for p in forecast['conditional'] if p['start'] < end and p['end'] > target]
    wind = max(p['wind'] for p in c); gust = max(p['gust'] for p in c)
    vis = min(p['vis'] for p in c); ceiling = min(p['ceiling'] for p in c)
    tmp_ts = 0.; prob_ts = 0.; cond_vis = 0.; cond_ceiling = 0.
    rain = max(p['rain'] for p in c); ice = max(p['ice'] for p in c)
    for p in conditional:
        q = p['conditions']
        if q['gust'] is not None: gust = max(gust,q['gust'])
        if q['wind'] is not None: wind = max(wind,q['wind'])
        cond_vis = max(cond_vis,float(q['vis'] is not None and q['vis']<3))
        cond_ceiling = max(cond_ceiling,float(q['ceiling'] is not None and q['ceiling']<1000))
        if p['probability'] is None: tmp_ts = max(tmp_ts,q['ts'])
        else: prob_ts = max(prob_ts,q['ts']*p['probability'])
        rain = max(rain,q['rain']); ice = max(ice,q['ice'])
    return [wind,gust,vis,ceiling/1000,float(vis<3),float(ceiling<1000),max(p['ts'] for p in c),
            tmp_ts,prob_ts,rain,ice,cond_vis,cond_ceiling,max(0,(cutoff-forecast['issued'])/3600)]


def feature_names(airports, weather=True):
    names = [f'airport_{a}' for a in airports] + ['hour_sin','hour_cos','week_sin','week_cos','month_sin','month_cos']
    names += [f'{a}_{v}' for a in airports for v in ('hour_sin','hour_cos')]
    if weather:
        names += WEATHER_NAMES + [f'{a}_{v}' for a in airports for v in ('thunder','low_ceiling','gust')]
    return names


def features(airport, timestamp, weather, zones, include_weather=True):
    local = datetime.fromtimestamp(timestamp,timezone.utc).astimezone(ZoneInfo(zones[airport]))
    angles = [(local.hour+local.minute/60)/24*2*math.pi,local.weekday()/7*2*math.pi,(local.month-1)/12*2*math.pi]
    calendar = [v for angle in angles for v in (math.sin(angle),math.cos(angle))]
    result = [float(a==airport) for a in zones] + calendar
    result += [calendar[i] if a==airport else 0. for a in zones for i in (0,1)]
    if include_weather:
        result += weather
        result += [value if a==airport else 0. for a in zones for value in (max(weather[6:9]), max(weather[5],weather[12]),weather[1])]
    return result
