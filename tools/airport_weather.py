"""Free public weather -> bounded, static snapshots. Python 3.10+, stdlib only.

No browser-triggered upstream requests, credentials, paid providers, or cloud jobs.
Run `python tools/airport_weather.py catalog` once, then `... watch` locally.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import time
from datetime import datetime, timezone
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from airport_operations import FAA_URL, RUNWAYS_URL, MAX_FAA_BYTES, MAX_RUNWAY_BYTES, enrich

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public" / "data" / "airport-weather"
STATE = ROOT / ".airport-data"
SOURCES = {
    "observations": "https://aviationweather.gov/data/cache/metars.cache.xml.gz",
    "forecasts": "https://aviationweather.gov/data/cache/tafs.cache.xml.gz",
    "catalog": "https://davidmegginson.github.io/ourairports-data/airports.csv",
    "faa": FAA_URL,
    "runways": RUNWAYS_URL,
}
MAX_REQUESTS_PER_MONTH = 3100  # 744 * 4 feeds + 31 finalized prior days + inventory/catalog margin.
MAX_DOWNLOAD_BYTES = 16 * 1024 * 1024
MAX_XML_BYTES = 32 * 1024 * 1024
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_HOURS = 14 * 24
USER_AGENT = "DerekDevs-AirportWeather/0.1 (+https://www.derekdevs.com)"
US_COUNTRIES = frozenset({'US', 'PR', 'VI', 'GU', 'MP', 'AS'})
US_SCOPE = 'us-and-territories'


def scope_catalog(catalog):
    """Country metadata, not an ICAO prefix, defines the supported geography."""
    return {**catalog, 'scope': US_SCOPE,
            'selection': 'Large and medium airports in the United States and U.S. territories with a four-character station identifier',
            'airports': [a for a in catalog['airports'] if a.get('country') in US_COUNTRIES]}


def scope_snapshot(snapshot, catalog):
    allowed = {a['icao'] for a in scope_catalog(catalog)['airports']}
    return {**snapshot, 'scope': US_SCOPE,
            'stations': {code: station for code, station in snapshot['stations'].items() if code in allowed}}


def utc_now():
    return datetime.now(timezone.utc)


def stamp(value=None):
    return (value or utc_now()).isoformat(timespec="seconds").replace("+00:00", "Z")


def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    os.replace(temp, path)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Upstream redirect refused; review the source URL before changing it.")


def fetch(source, day=None):
    """Reserve quota before network I/O. Caller holds the cross-process lock."""
    if source != 'faaHistory' and source not in SOURCES:
        raise ValueError("Source is not in the free-source allowlist")
    url = SOURCES.get(source)
    if source == 'faaHistory':
        from datetime import timedelta
        if day not in {(utc_now()-timedelta(days=i)).date().isoformat() for i in range(3)}:
            raise ValueError('Only current or previous FAA history dates are allowed')
        url = 'https://www.fly.faa.gov/adv/adv_list?' + urllib.parse.urlencode({'whichAdvisories':'ATCSCC','advisoryCategory':'All','date':day})
    month = utc_now().strftime("%Y-%m")
    ledger = read_json(STATE / "usage.json", {"month": month, "requests": 0})
    if ledger["month"] != month:
        ledger = {"month": month, "requests": 0}
    if ledger["requests"] >= MAX_REQUESTS_PER_MONTH:
        raise RuntimeError("Monthly request ceiling reached; keeping the last snapshot")
    ledger["requests"] += 1
    atomic_json(STATE / "usage.json", ledger)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    cap = {'faa': MAX_FAA_BYTES, 'runways': MAX_RUNWAY_BYTES, 'faaHistory':512*1024}.get(source, MAX_DOWNLOAD_BYTES)
    timeout = 8 if source == 'faaHistory' else 12 if source in ('faa', 'runways') else 35
    with urllib.request.build_opener(NoRedirect).open(request, timeout=timeout) as response:
        data = response.read(cap + 1)
    if len(data) > cap:
        raise ValueError("Download exceeds the byte ceiling")
    return data


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def conditions(element):
    return {
        "windDirection": element.findtext("wind_dir_degrees"),
        "windKt": number(element.findtext("wind_speed_kt")),
        "gustKt": number(element.findtext("wind_gust_kt")),
        # Keep censoring, e.g. 6+, instead of pretending it is an exact measurement.
        "visibilityMi": element.findtext("visibility_statute_mi"),
        "weather": element.findtext("wx_string"),
        "clouds": [{"cover": c.get("sky_cover"), "baseFt": number(c.get("cloud_base_ft_agl")),
                    "type": c.get("cloud_type")} for c in element.findall("sky_condition")],
        "verticalVisibilityFt": number(element.findtext("vert_vis_ft")),
    }


def parse_xml(data, kind, fetched_at):
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as compressed:
        raw = compressed.read(MAX_XML_BYTES + 1)
    if len(raw) > MAX_XML_BYTES or b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("XML rejected by size/entity guard")
    root = ET.fromstring(raw)
    if root.find("errors") is not None and len(root.find("errors")):
        raise ValueError("Source returned an error document")
    result = {}
    for element in root.findall(f"./data/{'METAR' if kind == 'observations' else 'TAF'}"):
        code = element.findtext("station_id")
        if not code:
            continue
        report = {"raw": element.findtext("raw_text", ""), "firstSeenAt": fetched_at}
        report["id"] = hashlib.sha256(report["raw"].encode()).hexdigest()[:20]
        if kind == "observations":
            report.update(conditions(element))
            report.update({"observedAt": element.findtext("observation_time"),
                           "temperatureC": number(element.findtext("temp_c")),
                           "dewpointC": number(element.findtext("dewpoint_c"))})
            sort_key = "observedAt"
        else:
            report.update({"issuedAt": element.findtext("issue_time"),
                           "validFrom": element.findtext("valid_time_from"),
                           "validTo": element.findtext("valid_time_to"),
                           "periods": []})
            for period in element.findall("forecast"):
                report["periods"].append({**conditions(period),
                    "from": period.findtext("fcst_time_from"), "to": period.findtext("fcst_time_to"),
                    "change": period.findtext("change_indicator", "BASE"),
                    "becomingAt": period.findtext("time_becoming"),
                    "probability": number(period.findtext("probability"))})
            report["periods"].sort(key=lambda p: (p["from"] or "", p["change"]))
            sort_key = "issuedAt"
        # Do not depend on provider document ordering when duplicate stations appear.
        if code not in result or (report.get(sort_key) or "") > (result[code].get(sort_key) or ""):
            result[code] = report
    if not result:
        raise ValueError("Empty source response; refusing to replace the last good snapshot")
    return result


def update_catalog():
    rows = csv.DictReader(io.StringIO(fetch("catalog").decode("utf-8-sig")))
    airports = []
    for row in rows:
        code = row.get("icao_code") or row.get("gps_code") or row["ident"]
        # Include medium airports for private aviation; describe this rule in the UI.
        if row["iso_country"] not in US_COUNTRIES or row["type"] not in {"large_airport", "medium_airport"} or len(code) != 4 or not code.isalnum():
            continue
        airports.append({"icao": code.upper(), "iata": row["iata_code"], "name": row["name"],
                         "city": row["municipality"], "country": row["iso_country"], "size": row["type"],
                         "lat": number(row["latitude_deg"]), "lon": number(row["longitude_deg"])})
    if len(airports) < 100:
        raise ValueError("Unexpectedly small airport catalog")
    # Use one deterministic entry per ICAO code, preferring a large airport.
    unique = {a["icao"]: a for a in sorted(airports, key=lambda a: a["size"], reverse=True)}
    output = {"generatedAt": stamp(), "source": "https://ourairports.com/data/",
              "selection": "Large and medium airports with a four-character station identifier",
              "airports": sorted(unique.values(), key=lambda a: (a["name"], a["icao"]))}
    atomic_json(PUBLIC / "airports.json", scope_catalog(output))
    print(json.dumps({"catalogAirports": len(unique)}), flush=True)


def prune_archive():
    archive = STATE / "snapshots"
    files = sorted(archive.glob("*.json.gz"))
    total = sum(p.stat().st_size for p in files)
    cutoff = time.time() - MAX_ARCHIVE_HOURS * 3600
    for path in files:
        size = path.stat().st_size
        if path.stat().st_mtime < cutoff or total > MAX_ARCHIVE_BYTES:
            path.unlink()
            total -= size


def publish(output):
    """Publish small U.S. station-prefix files; visitors never download the weather archive."""
    from airport_predict import publish_risk
    modeled = publish_risk(output)
    from airport_operations_score import publish as publish_operations
    publish_operations(output, PUBLIC)
    buckets = {}
    for code, station in output["stations"].items():
        buckets.setdefault(code[:2], {})[code] = station
    for prefix, stations in buckets.items():
        atomic_json(PUBLIC / "stations" / f"{prefix}.json", {
            "generatedAt": output["generatedAt"], "stations": stations})
    # These files are generated output. Drop obsolete international buckets after a scope change.
    for path in (PUBLIC / 'stations').glob('*.json'):
        if path.stem not in buckets:
            path.unlink()
    summary = {k: v for k, v in output.items() if k not in ("stations", "faaHistory")}
    summary["coverage"] = {
        "airports": len(output["stations"]),
        "observations": sum(bool(s["observation"]) for s in output["stations"].values()),
        "forecasts": sum(bool(s["tafs"]) for s in output["stations"].values()),
        "validatedAirports": 0,
        "experimentalModelAirports": modeled,
    }
    summary["model"] = {"status": "experimental-backtested" if modeled else "not-trained", "modeledAirports": modeled}
    atomic_json(PUBLIC / "latest.json", summary)


def scope_us():
    """Migrate local generated data without fetching or changing observation timestamps."""
    catalog = scope_catalog(read_json(PUBLIC / 'airports.json', {'airports': []}))
    if not catalog['airports']:
        raise ValueError('No U.S. airports found; rebuild the catalog before collecting')
    atomic_json(PUBLIC / 'airports.json', catalog)
    snapshot = read_json(STATE / 'latest.json', None)
    if snapshot:
        snapshot = scope_snapshot(snapshot, catalog)
        atomic_json(STATE / 'latest.json', snapshot)
        publish(snapshot)
    print(json.dumps({'scope': US_SCOPE, 'catalogAirports': len(catalog['airports'])}), flush=True)


def refresh(remaining_ms=None):
    now = utc_now()
    hour = now.strftime("%Y-%m-%dT%H")
    attempt = read_json(STATE / "attempt.json", {})
    if attempt.get("hour") == hour:
        return  # Across processes/restarts, at most one attempt per UTC hour; no retry storms.
    atomic_json(STATE / "attempt.json", {"hour": hour, "at": stamp(now)})
    previous = read_json(STATE / "latest.json", {"stations": {}, "sources": {}})
    catalog = scope_catalog(read_json(PUBLIC / "airports.json", {"airports": []}))
    if not catalog["airports"]:
        raise RuntimeError("Run the catalog command before refreshing weather")
    allowed = {a["icao"] for a in catalog["airports"]}
    fetched_at = stamp(now)
    stations = {c: {"observation": None, "tafs": []} for c in allowed}
    sources = {}
    for kind in ("observations", "forecasts"):
        try:
            reports = {code: report for code, report in parse_xml(fetch(kind), kind, fetched_at).items() if code in allowed}
            for code in allowed:
                report = reports.get(code)
                old = previous["stations"].get(code, {})
                if kind == "observations":
                    old_report = old.get("observation")
                    if report and old_report and report["id"] == old_report["id"]:
                        report["firstSeenAt"] = old_report["firstSeenAt"]
                    # Missing in a successful feed stays missing; never silently carry it forward.
                    stations[code]["observation"] = report
                else:
                    old_reports = old.get("tafs", [])
                    if report:
                        existing = next((p for p in old_reports if p["id"] == report["id"]), None)
                        if existing:
                            report["firstSeenAt"] = existing["firstSeenAt"]
                        # Earlier TAF may still cover the period before a new routine TAF begins.
                        retained = [p for p in old_reports if p["id"] != report["id"] and p["validTo"] > fetched_at]
                        stations[code]["tafs"] = [report, *retained][:4]
            sources[kind] = {"url": SOURCES[kind], "fetchedAt": fetched_at, "status": "ok", "reportCount": len(reports)}
        except Exception as error:
            field = "observation" if kind == "observations" else "tafs"
            for code in allowed:
                stations[code][field] = previous["stations"].get(code, {}).get(field, None if kind == "observations" else [])
            sources[kind] = {**previous.get("sources", {}).get(kind, {}), "status": "error",
                             "error": type(error).__name__, "attemptedAt": fetched_at}
            print(f"{kind}: {type(error).__name__}: {error}", flush=True)
    enrich(stations, sources, previous, catalog['airports'], fetch, now, remaining_ms)
    output = {"schemaVersion": 1, "scope": US_SCOPE, "generatedAt": fetched_at, "refreshMinutes": 60,
              "sources": sources, "stations": stations,
              "costPolicy": {"paidProvidersEnabled": False, "dataSubscriptionUsd": 0,
                             "monthlyRequestLimit": MAX_REQUESTS_PER_MONTH},
              "model": {"status": "not-trained", "validatedAirports": []}}
    if (PUBLIC/'operations/model.json').exists():
        from airport_faa_collect import collect as collect_history, metadata as history_metadata
        history = collect_history(previous.get('faaHistory'), [a['iata'] for a in catalog['airports'] if a.get('iata')], fetch, now, remaining_ms)
        output['faaHistory'] = history
        sources['faaHistory'] = history_metadata(history)
    atomic_json(STATE / "latest.json", output)
    publish(output)
    archive = STATE / "snapshots"
    archive.mkdir(parents=True, exist_ok=True)
    # Archive retrieval-time evidence; bounded rolling retention is not a multi-year research archive.
    path = archive / f"{now.strftime('%Y%m%dT%H%M%SZ')}.json.gz"
    path.write_bytes(gzip.compress(json.dumps(output, ensure_ascii=False).encode(), mtime=0))
    prune_archive()
    print(json.dumps({"generatedAt": fetched_at, "airports": len(stations),
                      "observations": sum(bool(s["observation"]) for s in stations.values()),
                      "forecasts": sum(bool(s["tafs"]) for s in stations.values()),
                      "snapshotBytes": (STATE / "latest.json").stat().st_size,
                      "sources": {k: v["status"] for k, v in sources.items()}}), flush=True)


def locked(action):
    STATE.mkdir(parents=True, exist_ok=True)
    lock = STATE / "collector.lock"
    # A crash deliberately leaves the lock behind: fail closed until inspected.
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError("Collector lock exists; another process is running or a previous run needs inspection")
    try:
        os.write(descriptor, str(os.getpid()).encode())
        os.close(descriptor)
        action()
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["catalog", "refresh", "watch", "scope-us"])
    args = parser.parse_args()
    if args.command == "catalog":
        locked(update_catalog)
    elif args.command == "refresh":
        locked(refresh)
    elif args.command == "scope-us":
        locked(scope_us)
    else:
        print("Local hourly weather collector running. Ctrl+C stops it. No paid services enabled.", flush=True)
        while True:
            try:
                locked(refresh)
            except Exception as error:
                print(f"Refresh paused: {error}", flush=True)
            time.sleep(60)
