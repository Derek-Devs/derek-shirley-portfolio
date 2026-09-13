"""Prepare a reproducible DFW historical replay, not a trained disruption model.

Downloads one requested BTS reporting-carrier month and DFW TAF issues with
48-hour lookback. Raw downloads stay in .airport-data; only aggregates publish.
Arrival dates are reconstructed using destination clock time and scheduled elapsed
time, with an explicit DST check. Airport windows are anchored in DFW local time.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from zoneinfo import ZoneInfo
import zipfile

from airport_weather import ROOT, USER_AGENT, atomic_json, stamp

DATA = ROOT / ".airport-data" / "history"
ZONE = ZoneInfo("America/Chicago")
MAX_ARCHIVE_BYTES = 96 * 1024 * 1024
MAX_EXPANDED_BYTES = 768 * 1024 * 1024


def download(url, path, max_bytes):
    if path.exists():
        return path.read_bytes()
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=50) as response:
        raw = response.read(max_bytes + 1)
    if len(raw) > max_bytes:
        raise ValueError("Research download exceeds its size ceiling")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw


def parse_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=timezone.utc)


def scalar(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def clock_minutes(value):
    minutes = int(float(value))
    hours, minute = divmod(minutes, 100)
    if minute > 59 or hours > 24 or (hours == 24 and minute):
        raise ValueError("Invalid BTS clock")
    return hours * 60 + minute


def local_to_utc(value, zone):
    """Reject ambiguous/nonexistent local times rather than silently pick a fold."""
    candidates = {value.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
                  for fold in (0, 1)
                  if value.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == value}
    if len(candidates) != 1:
        raise ValueError("Ambiguous or nonexistent scheduled local time")
    return candidates.pop()


def outcome(row, direction):
    if scalar(row.get("Cancelled")) == 1:
        return "cancelled"
    if direction == "arrivals" and scalar(row.get("Diverted")) == 1:
        return "diverted"
    delay = scalar(row.get("ArrDelay" if direction == "arrivals" else "DepDelay"))
    if delay is None:
        return "unknown"
    return "delayed" if delay >= 15 else "onTime"


def scheduled_dfw(row, direction):
    day = datetime.fromisoformat(row["FlightDate"][:10])
    if direction == "departures":
        return local_to_utc(day + timedelta(minutes=clock_minutes(row["CRSDepTime"])), ZONE)
    # FlightDate is the origin departure date, not necessarily DFW arrival date.
    # Enumerate arrival day offsets using scheduled elapsed time and U.S. origin zones.
    origin = ORIGIN_ZONES.get(row["OriginState"])
    if not origin:
        raise ValueError("Origin timezone not mapped")
    departure = local_to_utc(day + timedelta(minutes=clock_minutes(row["CRSDepTime"])), ZoneInfo(origin))
    elapsed = scalar(row.get("CRSElapsedTime"))
    if elapsed is None:
        raise ValueError("Missing scheduled elapsed time")
    expected = departure + timedelta(minutes=elapsed)
    candidates = []
    for offset in (-1, 0, 1, 2):
        local_arrival = day + timedelta(days=offset, minutes=clock_minutes(row["CRSArrTime"]))
        try:
            candidate = local_to_utc(local_arrival, ZONE)
        except ValueError:
            continue
        if abs((candidate - expected).total_seconds()) <= 60:
            candidates.append(candidate)
    if len(candidates) != 1:
        raise ValueError("Scheduled arrival clock / elapsed time mismatch")
    return candidates[0]


# States spanning timezones need airport overrides. Never infer all airports in such a state.
ORIGIN_ZONES = {
    **dict.fromkeys("CT DE DC GA MA MD ME NC NH NJ NY OH PA RI SC VA VT WV".split(), "America/New_York"),
    **dict.fromkeys("AL AR IA IL LA MN MO MS OK WI".split(), "America/Chicago"),
    **dict.fromkeys("CO MT NM UT WY".split(), "America/Denver"),
    **dict.fromkeys("CA WA".split(), "America/Los_Angeles"),
    "AZ": "America/Phoenix", "HI": "Pacific/Honolulu", "PR": "America/Puerto_Rico", "VI": "America/St_Thomas",
}
AIRPORT_ZONES = {
    **dict.fromkeys("DFW DAL AUS IAH HOU SAT LBB MAF AMA ABI ACT GRK CLL SJT TYR GGG SPS TXK BPT LRD MFE HRL BRO CRP DRT ELP".split(), "America/Chicago"),
    "ELP": "America/Denver",
    **dict.fromkeys("MIA FLL PBI MCO TPA RSW SRQ EYW GNV JAX DAB MLB TLH".split(), "America/New_York"),
    **dict.fromkeys("PNS VPS ECP".split(), "America/Chicago"),
    **dict.fromkeys("LAS RNO PDX EUG MFR RDM".split(), "America/Los_Angeles"),
    **dict.fromkeys("DTW GRR LAN FNT TVC AZO MQT CIU PLN".split(), "America/Detroit"),
    **dict.fromkeys("IND FWA SBN EVV".split(), "America/Indiana/Indianapolis"), "EVV": "America/Chicago",
    **dict.fromkeys("SDF LEX CVG".split(), "America/New_York"),
    **dict.fromkeys("BNA MEM CHA".split(), "America/Chicago"), "CHA": "America/New_York", "TYS": "America/New_York", "TRI": "America/New_York",
    **dict.fromkeys("MCI ICT MHK GCK OMA LNK GRI FSD FAR BIS GFK RAP".split(), "America/Chicago"), "RAP": "America/Denver",
    **dict.fromkeys("BOI IDA SUN".split(), "America/Boise"), "LWS": "America/Los_Angeles",
    **dict.fromkeys("ANC FAI JNU KTN SIT".split(), "America/Anchorage"),
}


def flight_windows(raw, month):
    totals = defaultdict(Counter)
    qa = Counter()
    seen = set()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [f for f in archive.infolist() if f.filename.lower().endswith(".csv")]
        if len(members) != 1 or members[0].file_size > MAX_EXPANDED_BYTES:
            raise ValueError("Unexpected BTS archive contents or size")
        with archive.open(members[0]) as member:
            rows = csv.DictReader(io.TextIOWrapper(member, encoding="utf-8-sig"))
            required = {"FlightDate", "Origin", "Dest", "CRSDepTime", "CRSArrTime", "Cancelled", "Diverted", "DepDelay", "ArrDelay", "CRSElapsedTime", "OriginState"}
            if not required.issubset(set(rows.fieldnames or [])):
                raise ValueError("BTS schema changed: " + str(required - set(rows.fieldnames or [])))
            for row in rows:
                if "DFW" not in (row["Origin"], row["Dest"]):
                    continue
                qa["dfwRows"] += 1
                key = tuple(row.get(k) for k in ["FlightDate", "Reporting_Airline", "Flight_Number_Reporting_Airline", "Origin", "Dest", "CRSDepTime"])
                if key in seen:
                    qa["duplicatesSkipped"] += 1
                    continue
                seen.add(key)
                direction = "departures" if row["Origin"] == "DFW" else "arrivals"
                # Override a split-state mapping with a confirmed airport timezone.
                if direction == "arrivals" and row["Origin"] in AIRPORT_ZONES:
                    row = {**row, "OriginState": row["Origin"]}
                    ORIGIN_ZONES[row["Origin"]] = AIRPORT_ZONES[row["Origin"]]
                try:
                    event = scheduled_dfw(row, direction)
                except (ValueError, KeyError) as error:
                    qa[f"excluded_{direction}_time"] += 1
                    qa[f"timeIssue_{row['Origin']}"] += 1
                    continue
                local = event.astimezone(ZONE)
                if local.strftime("%Y-%m") != month:
                    qa["outsideLocalMonth"] += 1
                    continue
                # 2-hour airport windows. Arrival boundary days have source-month limitations.
                start = local.replace(hour=(local.hour // 2) * 2, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
                counts = totals[(stamp(start), direction)]
                counts["scheduled"] += 1
                counts[outcome(row, direction)] += 1
                delay = scalar(row.get("ArrDelay" if direction == "arrivals" else "DepDelay"))
                if outcome(row, direction) == "cancelled" or (delay is not None and delay >= 60):
                    counts["severe"] += 1
    windows = [{"start": start, "end": stamp(parse_time(start) + timedelta(hours=2)), "direction": direction,
                "counts": {k: counts[k] for k in ("scheduled", "onTime", "delayed", "cancelled", "diverted", "unknown", "severe")}}
               for (start, direction), counts in sorted(totals.items())]
    return windows, dict(qa)


def taf_datetime(day_hour, issue_time):
    day, hour = int(day_hour[:2]), int(day_hour[2:])
    candidates = []
    for offset in (-1, 0, 1):
        year = issue_time.year + (issue_time.month - 1 + offset) // 12
        month = (issue_time.month - 1 + offset) % 12 + 1
        try:
            candidates.append(datetime(year, month, day, tzinfo=timezone.utc) + timedelta(hours=hour))
        except ValueError:
            continue
    return min(candidates, key=lambda d: abs((d - issue_time).total_seconds()))


def load_bulletin(product):
    if not re.fullmatch(r"[A-Z0-9-]+", product):
        raise ValueError("Invalid product identifier")
    path = DATA / "bulletins" / f"{product}.txt"
    cached = path.exists()
    raw = download("https://mesonet.agron.iastate.edu/api/1/nwstext/" + product, path, 128 * 1024).decode()
    if not cached:
        time.sleep(0.5)  # Three workers; bounded, polite archive retrieval.
    return product, raw


def taf_issues(raw, bulletins):
    issues = {}
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    for row in rows:
        if row["station"] != "KDFW":
            continue
        product = row["product_id"]
        issue = issues.setdefault(product, {"id": product, "issuedAt": stamp(parse_time(row["valid"])), "periods": []})
        issue["periods"].append({"from": stamp(parse_time(row["fx_valid"])), "to": stamp(parse_time(row["fx_valid_end"])) if row["fx_valid_end"] else None,
                                 "type": row["ftype"], "raw": row["raw"],
                                 "windKt": scalar(row["sknt"]), "gustKt": scalar(row["gust"]),
                                 "visibilityMi": scalar(row["visibility"]), "weather": row["presentwx"],
                                 "amendment": row["is_amendment"] == "True"})
    for issue in issues.values():
        bulletin = bulletins[issue["id"]]
        header = re.search(r"KDFW\s+(\d{6})Z\s+(\d{4})/(\d{4})", bulletin)
        if not header:
            raise ValueError("Unparsed TAF validity header: " + issue["id"])
        issue_time = parse_time(issue["issuedAt"])
        valid_from = taf_datetime(header[2], issue_time)
        valid_to = taf_datetime(header[3], valid_from)
        if not valid_from < valid_to <= valid_from + timedelta(hours=36):
            raise ValueError("Invalid terminal forecast validity")
        issue.update({"validFrom": stamp(valid_from), "validTo": stamp(valid_to), "raw": bulletin.strip()})
        prevailing = sorted([p for p in issue["periods"] if p["type"] != "Temporary"], key=lambda p: p["from"])
        for index, period in enumerate(prevailing):
            if period["type"] == "Observation":
                # IEM calls the initial forecast group 'Observation'; it is NOT an actual METAR.
                period["from"] = stamp(valid_from)
                period["type"] = "Prevailing"
            if period["to"] is None:
                period["to"] = prevailing[index + 1]["from"] if index + 1 < len(prevailing) else stamp(valid_to)
        for period in issue["periods"]:
            if not period["to"]:
                raise ValueError("Conditional group is missing its explicit end time")
    return sorted(issues.values(), key=lambda p: (p["issuedAt"], p["id"]))


def as_of(issues, target, hours, latency_minutes=10):
    cutoff = target - timedelta(hours=hours)
    available = [i for i in issues if parse_time(i["issuedAt"]) + timedelta(minutes=latency_minutes) <= cutoff]
    if not available:
        return None
    # Select latest issue first; do not cherry-pick an older forecast if it has better coverage.
    latest = available[-1]
    overlap = [p for p in latest["periods"] if parse_time(p["from"]) < target + timedelta(hours=2) and parse_time(p["to"]) > target]
    if not overlap:
        return None
    full = parse_time(latest["validFrom"]) <= target and parse_time(latest["validTo"]) >= target + timedelta(hours=2)
    return {"cutoff": stamp(cutoff), "issuedAt": latest["issuedAt"], "productId": latest["id"],
            "coverage": "full" if full else "partial", "periods": overlap}


def build(year, month):
    label = f"{year:04d}-{month:02d}"
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    bts_name = f"On_Time_Reporting_Carrier_On_Time_Performance_1987_present_{year}_{month}.zip"
    bts_url = "https://transtats.bts.gov/PREZIP/" + urllib.parse.quote(bts_name)
    taf_url = "https://mesonet.agron.iastate.edu/cgi-bin/request/taf.py?" + urllib.parse.urlencode({
        "station": "DFW", "sts": stamp(start - timedelta(days=2)), "ets": stamp(end + timedelta(days=1)), "fmt": "csv", "tz": "UTC"})
    print(f"Downloading BTS {label} (one bounded research month)", flush=True)
    bts = download(bts_url, DATA / f"bts-{label}.zip", MAX_ARCHIVE_BYTES)
    print("Downloading archived DFW forecasts", flush=True)
    taf = download(taf_url, DATA / f"taf-{label}.csv", 16 * 1024 * 1024)
    windows, qa = flight_windows(bts, label)
    products = sorted({r["product_id"] for r in csv.DictReader(io.StringIO(taf.decode("utf-8-sig")))})
    if len(products) > 500:
        raise ValueError("Too many bulletins for a bounded one-month research run")
    print(f"Checking {len(products)} original TAF bulletins for validity boundaries", flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        bulletins = dict(pool.map(load_bulletin, products))
    issues = taf_issues(taf, bulletins)
    missing = Counter()
    for window in windows:
        target = parse_time(window["start"])
        window["forecasts"] = {str(h): as_of(issues, target, h) for h in (24, 12, 6)}
        for h, forecast in window["forecasts"].items():
            if forecast is None:
                missing[h] += 1
    # Reference shared issues, rather than repeating the same raw report in every window.
    for window in windows:
        window["forecasts"] = {h: {k: v for k, v in f.items() if k != "periods"} if f else None for h, f in window["forecasts"].items()}
    result = {"schemaVersion": 1, "generatedAt": stamp(), "airport": "DFW", "month": label,
              "timezone": "America/Chicago", "windowHours": 2, "availabilityAssumptionMinutes": 10,
              "status": "descriptive-replay-only", "qa": qa, "forecastIssues": len(issues),
              "missingForecastWindows": dict(missing), "windows": windows, "issues": issues,
              "sources": [{"url": bts_url, "sha256": hashlib.sha256(bts).hexdigest()},
                          {"url": taf_url, "sha256": hashlib.sha256(taf).hexdigest()},
                          {"url": "https://mesonet.agron.iastate.edu/api/1/nwstext/", "products": len(bulletins),
                           "sha256": hashlib.sha256(json.dumps(bulletins, sort_keys=True).encode()).hexdigest()}],
              "limitations": [
                  "Reporting-carrier U.S. domestic flights only; not all DFW operations.",
                  "Arrival windows near month boundaries can omit flights departing in an adjacent source month.",
                  "TAF issuance plus 10 minutes approximates availability; historical delivery timestamps are unverified.",
                  "A month is a pipeline sample, not a validation period or representative annual baseline.",
                  "Descriptive outcomes are not predictions or causal estimates of weather impact.",
                  "BTS final records do not establish when cancellations became publicly known.",
              ]}
    atomic_json(DATA / f"replay-{label}.json", result)
    atomic_json(ROOT / "public/data/airport-weather/replay.json", result)
    print(json.dumps({"windows": len(windows), "forecastIssues": len(issues), "qa": qa, "missingForecastWindows": dict(missing)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--month", type=int, choices=range(1, 13), default=5)
    args = parser.parse_args()
    build(args.year, args.month)
