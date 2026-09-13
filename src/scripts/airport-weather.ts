import {
  ageMinutes, ceilingLabel, escapeHtml as e, findAirport, forecastAt, groupLabel, isUsAirport,
  isConditional, periodsAt, utcLabel, weatherLabel, windLabel,
  type Airport, type Conditions, type Forecast, type Snapshot, type Station,
} from "../lib/airport-weather";
import { ageRisk, initRisk, refreshRisk, renderRisk, riskTarget, setMapWeather } from "./airport-risk";
import { AIRPORT_DATA_BASE, airportDataUrl, setAirportGeneration } from "../lib/airport-data";
import { lookaheadTime, privateWeather, type WeatherSummary } from "../lib/airport-private";
import { faaState, operationsPanel } from '../lib/airport-operations';

const get = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const input = (id: string) => get<HTMLInputElement>(id);
const form = get<HTMLFormElement>("airport-form");
const directory = AIRPORT_DATA_BASE;
let airports: Airport[] = [];
let snapshot: Snapshot;
let mode = "airline";
let horizon: number | null = 6;
let generation = 0;
let lastFetched = 0;
let selected: { airport: Airport; station: Station | undefined; target: number; loadError?: boolean } | undefined;
const bucketCache = new Map<string, { generatedAt: string; stations: Record<string, Station> }>();
const bucketRequests = new Map<string, Promise<{ generatedAt: string; stations: Record<string, Station> }>>();
let privateMapAt = '';

const isoInput = (value: number) => new Date(value).toISOString().slice(0, 16);
input("event-time").value = isoInput(Date.now() + 6 * 3600000);

function displayError(message = "") {
  get("airport-error").hidden = !message;
  get("airport-error").textContent = message;
}

function airportNames() {
  const airport = findAirport(airports, input('airport').value);
  get('airport-selection').textContent = airport ? `${airport.name}${airport.city ? ` · ${airport.city}` : ''}` : 'Select a listed airport';
}

async function fetchJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { signal: AbortSignal.timeout(20000) });
  if (!response.ok) throw new Error(`Snapshot unavailable (${response.status})`);
  return response.json();
}

function options(query = "") {
  const needle = query.trim().toLowerCase();
  const matching = airports.filter(a => !needle || `${a.iata} ${a.icao} ${a.name} ${a.city}`.toLowerCase().includes(needle));
  get<HTMLDataListElement>("airport-options").innerHTML = matching.slice(0, 30)
    .map(a => `<option value="${e(a.icao)}">${e(a.iata ? a.iata + " · " : "")}${e(a.name)} · ${e(a.city)}</option>`).join("");
}

async function stationBucket(prefix: string, at = snapshot.generatedAt) {
  let bucket = bucketCache.get(prefix);
  if (bucket?.generatedAt === at) return bucket;
  const key = `${at}:${prefix}`;
  let request = bucketRequests.get(key);
  if (!request) {
    request = fetchJson<NonNullable<typeof bucket>>(airportDataUrl(`stations/${prefix}.json?v=${encodeURIComponent(at)}`)).then(value => {
      if (value.generatedAt !== at) throw new Error("Weather snapshot is updating. Try again shortly.");
      if (snapshot.generatedAt === at) bucketCache.set(prefix, value);
      return value;
    }).finally(() => bucketRequests.delete(key));
    bucketRequests.set(key, request);
  }
  return request;
}

async function stationFor(airport: Airport) {
  return (await stationBucket(airport.icao.slice(0, 2))).stations[airport.icao];
}

async function loadPrivateMap() {
  const at = snapshot.generatedAt;
  if (privateMapAt === at) return;
  privateMapAt = at;
  const prefixes = [...new Set(airports.map(a => a.icao.slice(0, 2)))];
  const stations: Record<string, Station> = {};
  const failed = new Set<string>();
  for (const bucket of bucketCache.values()) if (bucket.generatedAt === at) Object.assign(stations, bucket.stations);
  setMapWeather(stations, at, true, failed);
  // Reuse the existing static weather files. Four downloads at a time, one per
  // station prefix per snapshot; map interactions never invoke AWS compute.
  let next = 0;
  await Promise.all(Array.from({ length: 4 }, async () => {
    while (next < prefixes.length && snapshot.generatedAt === at) {
      const prefix = prefixes[next++];
      try { Object.assign(stations, (await stationBucket(prefix, at)).stations); }
      catch { failed.add(prefix); }
    }
  }));
  if (snapshot.generatedAt === at) setMapWeather(stations, at, false, failed);
}

function weatherSummary(summary: WeatherSummary) {
  return `<div class="airport-weather-summary"><strong class="airport-category weather-${summary.category.toLowerCase()}">${e(summary.label)}</strong><p class="airport-small">${e(summary.detail)}</p>${summary.conditional.map(c => `<p class="airport-small">${e(c.label)}: <strong>${e(c.category === 'unknown' ? 'category incomplete' : c.category)}</strong></p>`).join('')}</div>`;
}

function privateAirportSummary() {
  if (!selected || mode !== 'private') return;
  const { station, target, loadError } = selected;
  const operation = get<HTMLSelectElement>('direction').value === 'arrivals' ? 'arrival' : 'departure';
  const now = Date.now();
  const anchor = horizon === null ? now : target - horizon * 3600000;
  const conditions = privateWeather(station, target, snapshot.generatedAt, now, loadError);
  get('private-airport-summary').innerHTML = `<h3>Conditions at ${operation}</h3><p class="airport-small">${e(utcLabel(target))}</p>${weatherSummary(conditions)}<h3>Forecast coverage by look-ahead</h3><table class="airport-forecast-table airport-private-horizons"><thead><tr><th scope="col">Look ahead</th><th scope="col">${operation === 'arrival' ? 'Arrival' : 'Departure'} time (UTC)</th><th scope="col">Conditions</th></tr></thead><tbody>${[6,12,24].map(h => {
    const time = anchor + h * 3600000;
    const summary = privateWeather(station, time, snapshot.generatedAt, now, loadError);
    return `<tr class="${h === horizon ? 'airport-selected-row' : ''}"><th scope="row">+${h}h</th><td>${e(utcLabel(time))}</td><td>${e(summary.label)}</td></tr>`;
  }).join('')}</tbody></table><p class="airport-small">The map and selected airport use the same ${operation} time. Arrival and departure views share the airport forecast; this selection does not create a private-jet delay probability.</p>`;
}

function metrics(c: Conditions | undefined, temperature?: number | null) {
  const cells = [
    ["Wind", c ? windLabel(c) : "Unavailable"],
    ["Visibility", c?.visibilityMi ? `${c.visibilityMi} mi` : "Not reported"],
    ["Ceiling", c ? ceilingLabel(c) : "Not reported"],
    ["Temperature", temperature !== undefined && temperature !== null ? `${temperature} °C` : "Not reported"],
  ];
  return `<dl class="airport-metrics">${cells.map(([label, value]) => `<div><dt>${label}</dt><dd>${e(value)}</dd></div>`).join("")}</dl>`;
}

function forecastTable(forecast: Forecast | undefined, target: number) {
  if (!forecast) return `<p class="airport-notice">No downloaded airport forecast covers ${e(utcLabel(target))}. This is a coverage gap, not a low-risk result.</p>`;
  const periods = periodsAt(forecast, target);
  if (!periods.length) return `<p class="airport-notice">The forecast is valid, but its parsed periods do not cover this time. Refer to the original report below.</p>`;
  return `<p class="airport-small">Forecast issued ${e(utcLabel(forecast.issuedAt))} · valid through ${e(utcLabel(forecast.validTo))}</p>
    <div class="airport-table-scroll"><table class="airport-forecast-table"><caption>Conditions covering ${e(utcLabel(target))}</caption><thead><tr><th scope="col">Forecast group</th><th scope="col">Wind</th><th scope="col">Visibility / ceiling</th><th scope="col">Weather</th></tr></thead><tbody>${periods.map(p =>
      `<tr class="${isConditional(p) ? "airport-conditional" : ""}"><th scope="row">${e(groupLabel(p))}<span>${e(utcLabel(p.from))}–${e(utcLabel(p.to))}</span>${p.change === "BECMG" && p.becomingAt ? `<span>Becoming by ${e(utcLabel(p.becomingAt))}</span>` : ""}</th><td>${e(windLabel(p))}</td><td>${e(p.visibilityMi ? p.visibilityMi + " mi" : "Not specified")}<span>${e(ceilingLabel(p))}</span></td><td>${e(weatherLabel(p))}</td></tr>`).join("")}</tbody></table></div>
    <p class="airport-small">Change groups can omit unchanged fields. Weather probabilities describe conditions, not flight outcomes.</p>`;
}

function timeline(station: Station | undefined) {
  // These are current forecasts for future valid times, not historical T-minus model evaluations.
  const now = Date.now();
  return `<div class="airport-timeline" aria-label="Current forecast at future times">${[6, 12, 24].map(h => {
    const target = now + h * 3600000;
    const forecast = forecastAt(station, target);
    const periods = periodsAt(forecast, target);
    const base = periods.find(p => !isConditional(p));
    const conditional = periods.filter(isConditional);
    return `<div><span class="airport-timeline-hour">+${h}h <small>${e(utcLabel(target))}</small></span><strong>${base ? e(windLabel(base)) : "Forecast unavailable"}</strong><span>${base ? e(base.visibilityMi ? base.visibilityMi + " mi visibility" : "Visibility not specified") : "Outside available coverage"}</span><span>${base ? e(ceilingLabel(base)) : ""}</span><span class="airport-small">${base?.change === "BECMG" ? "Transition period · " : ""}${conditional.length ? `${conditional.length} conditional group${conditional.length > 1 ? "s" : ""}` : ""}</span></div>`;
  }).join("")}</div>`;
}

function airportPanel(airport: Airport, station: Station | undefined, target: number, label: string, loadError = false) {
  const observation = station?.observation ?? undefined;
  const oldObservation = ageMinutes(observation?.observedAt) > 120;
  const forecast = forecastAt(station, target);
  const newest = station?.tafs.slice().sort((a, b) => Date.parse(b.issuedAt) - Date.parse(a.issuedAt))[0];
  const country = new Intl.DisplayNames(["en"], { type: "region" }).of(airport.country) ?? airport.country;
  return `<article class="airport-station">
    <div class="airport-station-heading"><div class="airport-code">${e(airport.iata || airport.icao)}</div><div><p class="airport-kicker">${e(label)} · ${e(airport.icao)}</p><h2>${e(airport.name)}</h2><p>${e(airport.city || country)}${airport.city ? `, ${e(country)}` : ""}</p></div></div>
    ${operationsPanel(airport, station, snapshot.sources)}
    <div class="airport-observation-heading"><h3>Latest observation</h3><span class="${oldObservation ? "airport-old" : ""}">${observation ? `${e(utcLabel(observation.observedAt))}${oldObservation ? " · older than 2 hours" : ""}` : "No report available"}</span></div>
    ${metrics(observation, observation?.temperatureC)}
    <p class="airport-weather-description">${observation ? e(weatherLabel(observation)) : "Observation coverage is missing at this airport."}</p>
    <h3 class="airport-target-heading">${e(label)} at ${e(utcLabel(target))}</h3>
    ${mode === 'private' ? weatherSummary(privateWeather(station, target, snapshot.generatedAt, Date.now(), loadError)) : ''}
    ${forecastTable(forecast, target)}
    ${mode === "airline" ? timeline(station) : ""}
    <details class="airport-raw"><summary>Original weather reports</summary><h4>METAR / SPECI observation</h4><pre>${e(observation?.raw || "No observation available")}</pre><h4>TAF airport forecast${forecast ? " used for the selected time" : " · latest available"}</h4><pre>${e((forecast || newest)?.raw || "No forecast available")}</pre><p class="airport-small">${forecast || newest ? `First downloaded ${e(utcLabel((forecast || newest)!.firstSeenAt))}. ` : ""}Raw reports retain information not summarized above.</p></details>
    </article>`;
}

function renderFreshness() {
  if (!snapshot) return;
  const old = ageMinutes(snapshot.generatedAt) > 90;
  const errors = ['observations', 'forecasts'].some(key => snapshot.sources[key]?.status !== 'ok');
  get("data-state").textContent = `${old ? "Older snapshot" : errors ? "Partial weather update" : "Weather snapshot"} · ${utcLabel(snapshot.generatedAt)}`;
  get("data-state").classList.toggle("airport-old", old || errors);
  get("provenance").innerHTML = `<span>NOAA Aviation Weather Center</span><span>Observations downloaded: ${snapshot.sources.observations?.fetchedAt ? e(utcLabel(snapshot.sources.observations.fetchedAt)) : "unavailable"}</span><span>Forecasts downloaded: ${snapshot.sources.forecasts?.fetchedAt ? e(utcLabel(snapshot.sources.forecasts.fetchedAt)) : "unavailable"}</span>${old || errors ? '<strong>The collection is old or incomplete. Check report times before interpreting these conditions.</strong>' : ""}`;
}

function ageOperations() {
  if (!selected || !snapshot) return;
  const { airport, station } = selected;
  const card = document.getElementById(`operations-${airport.icao}`)?.closest('.airport-operations')?.querySelector<HTMLElement>('.airport-faa');
  if (!card || card.dataset.faaState === faaState(station, snapshot.sources.faa)) return;
  // Update only the FAA card when its status ages; leave opened runway details intact.
  const template = document.createElement('template');
  template.innerHTML = operationsPanel(airport, station, snapshot.sources);
  card.replaceWith(template.content.querySelector('.airport-faa')!);
}

function render() {
  if (!selected) return;
  const { airport, station, target, loadError } = selected;
  const direction = get<HTMLSelectElement>("direction").value;
  get("weather-result").innerHTML = airportPanel(airport, station, target, direction === "arrivals" ? "Arrivals" : "Departures", loadError);
  renderRisk({ airport, direction, mode, horizon, target });
  privateAirportSummary();
  if (mode === 'private') void loadPrivateMap();
  document.querySelectorAll<HTMLButtonElement>("[data-horizon]").forEach(button => button.setAttribute("aria-pressed", String(Number(button.dataset.horizon) === horizon)));
  renderFreshness();
}

async function showSelection() {
  const requestId = ++generation;
  get("airport-results").setAttribute("aria-busy", "false");
  get<HTMLButtonElement>("show-weather").disabled = false;
  const airport = findAirport(airports, input("airport").value);
  const target = Date.parse(input("event-time").value + "Z");
  airportNames();
  if (!airport) {
    displayError("Choose a listed airport using its IATA or ICAO code, or select a name from the search suggestions."); return;
  }
  if (!Number.isFinite(target)) {
    displayError("Enter a valid UTC airport time."); return;
  }
  if (target < Date.now() - 60000) {
    displayError("Choose a future airport time, or use the historical replay further down this page."); return;
  }
  displayError();
  get("airport-results").setAttribute("aria-busy", "true");
  get<HTMLButtonElement>("show-weather").disabled = true;
  // Risk and backtests are already loaded; do not leave the previous airport's
  // evidence or airline probabilities visible while station weather downloads.
  renderRisk({ airport, direction: get<HTMLSelectElement>("direction").value, mode, horizon, target });
  get("weather-result").innerHTML = `<p class="airport-notice">Loading weather for ${e(airport.iata || airport.icao)}…</p>`;
  if (mode === 'private') get('private-airport-summary').innerHTML = `<p>Loading ${e(airport.iata || airport.icao)} airport conditions…</p>`;
  try {
    const [result] = await Promise.allSettled([stationFor(airport)]);
    if (requestId !== generation) return;
    const loadError = result.status === 'rejected';
    selected = { airport, station: result.status === 'fulfilled' ? result.value : undefined, target, loadError };
    if (loadError) displayError(`${airport.icao} weather could not be downloaded. Refresh to retry.`);
    input("airport").value = airport.icao;
    render();
  } catch (error) {
    if (requestId !== generation) return;
    displayError(error instanceof Error ? error.message : "Weather could not be loaded. Try again shortly.");
  } finally {
    if (requestId === generation) {
      get("airport-results").setAttribute("aria-busy", "false");
      get<HTMLButtonElement>("show-weather").disabled = false;
    }
  }
}

async function refresh() {
  try {
    snapshot = await fetchJson<Snapshot>(`${directory}/latest.json?t=${Math.floor(Date.now() / 60000)}`);
    lastFetched = Date.now();
    if (!snapshot.coverage || !snapshot.generatedAt) throw new Error("Weather snapshot format is not supported.");
    setAirportGeneration(snapshot.dataPrefix);
    const c = snapshot.coverage;
    const majorCount = airports.filter(a => a.size === 'large_airport').length;
    get("coverage-summary").textContent = `${airports.length.toLocaleString()} airports in the United States and U.S. territories, including ${majorCount} classified as large. ${c.airports === airports.length ? `${c.observations.toLocaleString()} have an observation and ${c.forecasts.toLocaleString()} have an airport forecast in this snapshot.` : 'U.S. weather is shown for each selection; aggregate weather counts will appear after the next U.S. collection.'} Weather availability does not establish model accuracy.`;
    await refreshRisk(snapshot.generatedAt);
    if (horizon !== null) setHorizon(horizon);
    await showSelection();
  } catch {
    get("data-state").textContent = "Weather connection unavailable";
    displayError("The weather snapshot could not be loaded. The last displayed results, if any, retain their original timestamps.");
    if (!selected) get("weather-result").innerHTML = '<p class="airport-notice">Weather is temporarily unavailable. No disruption estimate is inferred from missing data.</p>';
  }
}

form.addEventListener("submit", event => { event.preventDefault(); privateMapAt = ''; void refresh(); });
for (const id of ["airport"]) {
  let timer: ReturnType<typeof setTimeout>;
  input(id).addEventListener("input", () => {
    options(input(id).value);
    airportNames();
    clearTimeout(timer);
    timer = setTimeout(() => {
      if (snapshot && findAirport(airports, input(id).value)) void showSelection();
    }, 300);
  });
  input(id).addEventListener("change", () => {
    clearTimeout(timer);
    if (snapshot) void showSelection();
  });
  input(id).addEventListener("focus", () => options(input(id).value));
}
input('event-time').addEventListener('change', () => {
  horizon = null;
  if (snapshot) void showSelection();
});
document.querySelectorAll<HTMLInputElement>('input[name="aviation-mode"]').forEach(radio => radio.addEventListener("change", () => {
  mode = radio.value;
  // Apply the view even if the airport field is currently incomplete.
  if (selected) renderRisk({ airport: selected.airport, direction: get<HTMLSelectElement>('direction').value, mode, horizon, target: selected.target });
  if (horizon !== null) setHorizon(horizon);
  void showSelection();
}));
get("direction").addEventListener("change", () => { void showSelection(); });
function setHorizon(value: number) {
  horizon = value;
  const modeledTime = riskTarget(value);
  const time = lookaheadTime(value, mode, Date.now(), modeledTime);
  input("event-time").value = isoInput(time);
}
document.querySelectorAll<HTMLButtonElement>("[data-horizon]").forEach(button => button.addEventListener("click", () => {
  setHorizon(Number(button.dataset.horizon));
  void showSelection();
}));

async function init() {
  try {
    const catalog = await fetchJson<{ airports: Airport[] }>(`${directory}/airports.json`);
    // Also enforce scope when an older CDN catalog is still cached.
    airports = catalog.airports.filter(isUsAirport);
    if (!airports.length) throw new Error('No U.S. airports available');
    options("DFW");
    void initRisk(airports, airport => { input("airport").value = airport.icao; if (snapshot) void showSelection(); });
    await refresh();
  } catch {
    get("data-state").textContent = "Airport catalog unavailable";
    get("weather-result").innerHTML = '<p class="airport-notice">The airport catalog could not be loaded. Please reload this page.</p>';
  }
}
void init();
setInterval(() => { if (!document.hidden && airports.length) void refresh(); }, 3600000);
setInterval(() => { renderFreshness(); ageRisk(); if (mode === 'private') render(); else ageOperations(); }, 60000);
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && airports.length && Date.now() - lastFetched >= 3600000) void refresh();
});
