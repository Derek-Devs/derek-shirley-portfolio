import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { ageMinutes, escapeHtml as e, utcLabel, isUsAirport, type Airport, type Station } from "../lib/airport-weather";
import { privateWeather } from "../lib/airport-private";
import { airportDataUrl } from "../lib/airport-data";

type Probabilities = { cancelled: number; delayed: number; diverted: number; onTime: number; disruption: number };
type Outlook = { start: string; end: string; status: string; reason: string | null; probabilities?: Probabilities; baseline?: number; band?: number[]; bandCoverage?: number; evidence?: string; outsideTrainingRange?: boolean; weather?: number[] };
type Risk = { generatedAt: string; version: string; modelBuiltAt: string; airports: Record<string, { directions: Record<string, Record<string, Outlook>> }> };
type Metrics = { flights: number; windows: number; days: number; observedRate: number; predictedRate: number; brier: number; baselineBrier: number; brierSkill: number; skillInterval95: number[]; mae: number; baselineMae: number; logLoss: number; calibrationError: number; bandCoverage: number; bandMeanWidth: number; evidence: string; calibration: { predicted: number; observed: number; flights: number; windows: number }[]; components: Record<string, { brier: number; observedRate: number; predictedRate: number }>; deliverySensitivity?: { coverage: number; brier: number; mainBrierSameWindows: number }; weatherGroups: Record<string, { windows: number; flights: number; observedRate: number }>; previousModel?: { brier: number; bandCoverage: number; predictedCancellation: number; bandMeanWidth: number; intervalScore: number; mae: number }; qValueApproximate?: number; bootstrapBlocks?: number; intervalScore?: number; method?: string; multipleTestingComparisons?: number; cohorts?: Record<string, { airportWindows: number; flightEvents: number }>; matchedHorizon?: { windows: number; flights: number; brier: number; baselineBrier: number } };
type AirportEvidence = Record<string, { directions: Record<string, Record<string, Metrics>> }>;
type Coverage = Record<string, { method: string; directions: Record<string, Record<string, { status: string; reason?: string; windows?: Record<string, number> }>> }>;
type Evaluation = { coverage?: Coverage; evaluationLabel?: string; coverageSummary?: { targetAirports: number; testedAirports: number }; version: string; generatedAt: string; airports: AirportEvidence; stressAirports?: AirportEvidence; protocol: { test: string[]; previouslySeenStressTest?: string[] }; cohorts: Record<string, { airportWindows: number; flightEvents: number }>; selection?: { selected: string; meanBrier: Record<string, number>; results: { fold: string; direction: string; horizon: number; candidate: string; brier: number }[] } };
const get = (id: string) => document.getElementById(id)!;
const pct = (value: number, digits = 0) => `${(value * 100).toFixed(digits)}%`;
const pp = (value: number) => `${(value * 100).toFixed(1)} pp`;
const count = (value: number) => value.toLocaleString("en-US");
const readableReason = (value: string) => value.replace(/probabilityCalibration/g, "probability calibration").replace(/intervalCalibration/g, "uncertainty calibration").replace(/train:/g, "training:").replace(/test:/g, "backtest:");
let risk: Risk | undefined;
let evaluation: Evaluation | undefined;
let map: L.Map | undefined;
let catalog: Airport[] = [];
let onSelect: (airport: Airport) => void;
let state: { airport: Airport; direction: string; mode: string; horizon: number | null; target: number } | undefined;
const markers = new Map<string, L.Marker>();
let lastAirport = "";
let snapshotAt = "";
let wasStale = false;
let evidencePeriod = "test";
let modelChoice = (get('forecast-model') as HTMLSelectElement).value;
let riskRequest = 0;
const operationsMode = () => modelChoice === 'operations';
type OperationsMetrics = Metrics & { trainingWindowsWithFaaActivity: number; faaActivityWindows: number;
  weatherComparator: { brier: number; logLoss: number; calibrationError: number; bandCoverage: number };
  productionComparator: { brier: number; logLoss: number };
  faaDeliverySensitivity?: { coverage: number; brier: number; mainBrierSameWindows: number } };
let mapWeather: { stations: Record<string, Station>; at: string; loading: boolean; failed: Set<string> } | undefined;

export function setMapWeather(stations: Record<string, Station>, at: string, loading: boolean, failed: Set<string>) {
  mapWeather = { stations, at, loading, failed };
  if (state?.mode === 'private') updateMap();
}

async function json<T>(path: string): Promise<T> {
  const r = await fetch(path === 'world.geojson' ? '/data/airport-weather/world.geojson' : airportDataUrl(path), { signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error(`Unavailable: ${path}`);
  return r.json();
}

export function riskTarget(horizon: number) {
  return Date.parse(risk?.generatedAt || snapshotAt) + horizon * 3600000;
}

export async function refreshRisk(generatedAt: string) {
  snapshotAt = generatedAt;
  const request = ++riskRequest;
  const prefix = operationsMode() ? 'operations/' : '';
  try {
    const next = await json<Risk>(`${prefix}risk.json?v=${encodeURIComponent(generatedAt)}`);
    if (next.generatedAt !== generatedAt) throw new Error("Snapshot updating");
    const evidence = !evaluation || evaluation.version !== next.version || evaluation.generatedAt !== next.modelBuiltAt
      ? await json<Evaluation>(`${prefix}evaluation.json?v=${encodeURIComponent(next.modelBuiltAt)}`) : evaluation;
    if (evidence.version !== next.version || evidence.generatedAt !== next.modelBuiltAt) throw new Error("Model and evaluation differ");
    if (request !== riskRequest) return;
    evaluation = evidence; risk = next;
  } catch { if (request === riskRequest) { risk = undefined; evaluation = undefined; } }
}

function current(airport: Airport): Outlook | undefined {
  if (!state || state.mode === "private" || state.horizon === null || !risk || ageMinutes(risk.generatedAt) > 90) return;
  const value = risk.airports[airport.iata]?.directions[state.direction]?.[String(state.horizon)];
  if (!value || Math.abs(Date.parse(value.start) - state.target) > 60000) return;
  return value;
}

function band(value: number) { return value < .15 ? 0 : value < .3 ? 1 : value < .45 ? 2 : 3; }

function selectMapAirport(fallback: Airport, event: L.LeafletMouseEvent) {
  if (!map || !(event.originalEvent instanceof MouseEvent)) { onSelect(fallback); return; }
  // At national zoom, nearby dots overlap. Leaflet snaps marker event coordinates
  // to the top marker; use the actual pointer to select the nearest visible dot.
  const point = map.mouseEventToContainerPoint(event.originalEvent);
  let nearest = fallback; let distance = Infinity;
  for (const airport of catalog) {
    if (!markers.has(airport.icao) || airport.lat === null || airport.lon === null) continue;
    const next = point.distanceTo(map.latLngToContainerPoint([airport.lat, airport.lon]));
    if (next < distance) { nearest = airport; distance = next; }
  }
  onSelect(nearest);
}

function updateMap() {
  if (!map || !state) return;
  const privateMode = state.mode === 'private';
  const bounds = map.getBounds().pad(.1);
  const visible = catalog.filter(a => a.lat !== null && a.lon !== null && bounds.contains([a.lat, a.lon]) && (a.size === "large_airport" || a.icao === state!.airport.icao || (privateMode ? map!.getZoom() >= 5 : evaluation?.airports[a.iata])));
  const visibleIds = new Set(visible.map(a => a.icao));
  for (const [id, marker] of markers) if (!visibleIds.has(id)) { marker.remove(); markers.delete(id); }
  const selectedPoint = state.airport.lat !== null && state.airport.lon !== null ? map.latLngToContainerPoint([state.airport.lat, state.airport.lon]) : null;
  const labelPoints: L.Point[] = selectedPoint ? [selectedPoint] : [];
  for (const a of visible) {
    if (a.lat === null || a.lon === null) continue;
    const outlook = current(a); const p = outlook?.probabilities;
    const selected = a.icao === state.airport.icao;
    const modeled = privateMode ? a.size === 'large_airport' : Object.values(evaluation?.airports[a.iata]?.directions || {}).some(horizons => Object.keys(horizons).length > 0);
    const weather = privateMode ? privateWeather(mapWeather?.stations[a.icao], state.target, mapWeather?.at === snapshotAt ? snapshotAt : '', Date.now(), mapWeather?.failed.has(a.icao.slice(0,2))) : undefined;
    const weatherLoading = privateMode && (!mapWeather || mapWeather.at !== snapshotAt || mapWeather.loading) && !mapWeather?.stations[a.icao];
    const lowData = outlook?.status === "low-data" || outlook?.status === "insufficient-evidence";
    const bandMiss = outlook?.bandCoverage !== undefined && outlook.bandCoverage < .8;
    const point = map.latLngToContainerPoint([a.lat, a.lon]);
    const showLabel = selected || (modeled && (map.getZoom() >= 5 || !labelPoints.some(p => Math.abs(p.x - point.x) < 32 && Math.abs(p.y - point.y) < 24)));
    if (showLabel && !selected) labelPoints.push(point);
    const label = a.iata || a.icao;
    const status = weatherLoading ? 'Loading weather' : weather ? `${weather.label}${weather.conditional.length ? ` · ${weather.conditional.map(c => `${c.label}: ${c.category}`).join('; ')}` : ''}` : p ? `${pct(p.disruption)} disruption · ${outlook!.evidence} ${operationsMode() ? "FAA" : "weather"} evidence${bandMiss ? ' · band below coverage target' : ''}` : outlook?.status === "insufficient-evidence" ? "Insufficient historical evidence · no estimate" : outlook?.status === 'low-data' ? "Low data at these local hours · no estimate" : "No current estimate";
    const color = weather ? `weather-${weather.category.toLowerCase()}` : p ? `risk-${band(p.disruption)}` : 'risk-none';
    const title = `${label} · ${a.name} · ${status}`;
    const icon = L.divIcon({ className: "airport-map-marker", iconSize: [24, 24], iconAnchor: [12, 12],
      html: `<span class="airport-pin ${color} ${lowData || weather?.status === 'partial' ? "airport-pin-low" : ""} ${outlook?.evidence === "limited" || bandMiss || weather?.conditional.length ? "airport-pin-limited" : ""} ${selected ? "airport-pin-selected" : ""} ${modeled || selected ? "airport-pin-main" : ""}"></span>${showLabel ? `<span class="airport-pin-label">${e(label)}</span>` : ""}` });
    let marker = markers.get(a.icao);
    if (!marker) {
      marker = L.marker([a.lat, a.lon], { icon, title, alt: title, keyboard: true, zIndexOffset: modeled ? 500 : 0 }).addTo(map);
      marker.on("click", (event: L.LeafletMouseEvent) => selectMapAirport(a, event));
      marker.on("keydown", (event: L.LeafletKeyboardEvent) => {
        if (event.originalEvent.key === "Enter" || event.originalEvent.key === " ") {
          event.originalEvent.preventDefault(); event.originalEvent.stopPropagation(); onSelect(a);
        }
      });
      marker.bindTooltip("", { direction: "top", offset: [0, -9] });
      markers.set(a.icao, marker);
    } else marker.setIcon(icon);
    marker.setTooltipContent(`<strong>${e(label)} · ${e(a.city || a.name)}</strong><br>${e(status)}${weather && !weatherLoading ? `<br>${e(weather.detail)}` : ''}<br>${privateMode ? 'Select airport · zoom for medium airports' : 'Select for weather and evidence'}`);
    marker.getElement()?.setAttribute("aria-label", title);
    marker.getElement()?.setAttribute("title", title);
    // Search reaches every listed U.S. airport; keep map tab order manageable.
    marker.getElement()?.setAttribute("tabindex", modeled || selected ? "0" : "-1");
    marker.setZIndexOffset(selected ? 1000 : modeled ? 500 : 0);
  }
  if (lastAirport !== state.airport.icao) {
    lastAirport = state.airport.icao;
    const { lat, lon } = state.airport;
    if (lat !== null && lon !== null && !map.getBounds().contains([lat, lon])) map.setView([lat, lon], Math.max(3, map.getZoom()), { animate: false });
  }
  get("map-title").textContent = privateMode ? 'Ceiling & visibility forecast' : 'Where is disruption more likely?';
  get('airport-map').setAttribute('aria-label', privateMode ? 'Interactive airport ceiling and visibility map' : 'Interactive airport disruption map');
  get('airline-map-legend').hidden = privateMode;
  get('private-map-legend').hidden = !privateMode;
  get('airline-map-note').hidden = privateMode;
  get('private-map-note').hidden = !privateMode;
  get("map-description").textContent = privateMode ? `${state.direction === 'arrivals' ? 'Arrivals' : 'Departures'} · weather at ${utcLabel(state.target)} at every airport. ${mapWeather?.loading ? 'Loading the shared weather files…' : ageMinutes(snapshotAt) > 90 ? 'Snapshot older than 90 minutes; categories withheld.' : 'Select an airport; zoom in for medium airports.'}${mapWeather?.failed.size ? ' Some weather downloads failed; refresh to retry.' : ''}`
    : state.horizon === null ? "Custom time: weather is available below. Choose +6h, +12h, or +24h to see modeled windows."
    : !risk ? "Risk snapshot unavailable or updating. Airport search and weather remain available."
    : ageMinutes(risk.generatedAt) > 90 ? `Risk snapshot is older than 90 minutes (${utcLabel(risk.generatedAt)}). Colors are withheld until it refreshes.`
    : `${state.direction === "arrivals" ? "Arrivals" : "Departures"} · +${state.horizon}h from ${utcLabel(risk.generatedAt)} · select an airport; zoom in to separate nearby dots.`;
}

export async function initRisk(airports: Airport[], select: (airport: Airport) => void) {
  catalog = airports.filter(isUsAirport); onSelect = select;
  get("evaluation-period").addEventListener("change", event => { evidencePeriod = (event.target as HTMLSelectElement).value; renderEvidence(); });
  map = L.map("airport-map", { scrollWheelZoom: false, minZoom: 1, maxZoom: 8, zoomSnap: .25, worldCopyJump: false, maxBounds: [[-85, -200], [85, 200]], maxBoundsViscosity: .5 });
  const regions: Record<string, L.LatLngBoundsExpression> = {
    mainland: [[24, -126], [50, -66]], alaska: [[50, -180], [72, -129]],
    hawaii: [[18.5, -161], [22.8, -154]], caribbean: [[17.3, -68], [19.1, -64.3]],
    pacific: [[12.5, 143], [21.5, 147]], samoa: [[-15, -172], [-13.5, -168]],
  };
  const showRegion = (region: string) => map!.fitBounds(regions[region] || regions.mainland, { padding: [24, 24], animate: false });
  showRegion('mainland');
  map.on("moveend", updateMap);
  get("map-region").addEventListener("change", event => showRegion((event.target as HTMLSelectElement).value));
  new ResizeObserver(() => map?.invalidateSize({ pan: false })).observe(get("airport-map"));
  map.attributionControl.setPrefix(false);
  map.attributionControl.addAttribution('<a href="https://www.naturalearthdata.com/">Natural Earth</a> · <a href="https://leafletjs.com/">Leaflet</a>');
  try {
    const world = await json<GeoJSON.GeoJsonObject>("world.geojson");
    L.geoJSON(world, { interactive: false, style: { className: "airport-land", color: "#aeb9b3", weight: .7, fillColor: "#e5e9df", fillOpacity: 1 } }).addTo(map).bringToBack();
  } catch { get("map-description").textContent = "Map geography unavailable. Airport markers and search still work."; }
  updateMap();
}

function calibrationPlot(metrics: Metrics) {
  const x = (v: number) => 38 + v * 270;
  const y = (v: number) => 204 - v * 170;
  return `<svg class="airport-calibration-plot" viewBox="0 0 340 244" role="img" aria-label="Calibration: predicted disruption share on the horizontal axis and observed share on the vertical axis. Points near the diagonal are better calibrated.">
    ${[0, .25, .5, .75, 1].map(v => `<line x1="38" x2="308" y1="${y(v)}" y2="${y(v)}" class="plot-grid"/><text x="30" y="${y(v) + 4}" text-anchor="end">${pct(v)}</text><text x="${x(v)}" y="220" text-anchor="middle">${pct(v)}</text>`).join("")}
    <line x1="38" y1="204" x2="308" y2="34" class="plot-ideal"/>
    ${metrics.calibration.map(b => `<circle cx="${x(b.predicted)}" cy="${y(b.observed)}" r="${Math.min(11, 3 + Math.sqrt(b.flights / metrics.flights) * 9)}" class="plot-observed"><title>Predicted ${pct(b.predicted, 1)}; observed ${pct(b.observed, 1)}; ${count(b.flights)} flights</title></circle>`).join("")}
    <text x="38" y="18">Observed</text><text x="175" y="240" text-anchor="middle">Predicted disruption share</text></svg>`;
}

function renderEvidence() {
  if (!state) return;
  if (operationsMode() && state.mode !== 'private') { renderOperationsEvidence(); return; }
  const { airport, direction, mode } = state;
  const stress = evidencePeriod === "stress" && Boolean(evaluation?.stressAirports);
  const table = stress ? evaluation?.stressAirports : evaluation?.airports;
  const horizons = table?.[airport.iata]?.directions[direction];
  const airportCount = evaluation?.coverageSummary?.testedAirports || Object.keys(evaluation?.airports || {}).length;
  const audit = evaluation?.coverage?.[airport.iata]?.directions[direction];
  get("evaluation-picker").hidden = !evaluation?.stressAirports || mode === "private";
  const h = state.horizon || 6; const m = horizons?.[String(h)];
  get("evidence-title").textContent = `${airport.iata || airport.icao} · what does the evidence say?`;
  if (mode === "private" || !m) {
    get("evidence-content").innerHTML = `<p class="airport-notice">${mode === "private" ? "Private aviation needs its own flight-outcome dataset. Airline backtest metrics do not establish private-flight reliability or safety." : audit ? `This airport was assessed. T−${h}: ${e(readableReason(audit[String(h)]?.reason || "This evaluation period has no sufficient tested sample."))} ${horizons && Object.keys(horizons).length ? "Try another tested horizon." : "No tested horizon is available for this direction."} Weather coverage alone does not establish a calibrated estimate.` : evaluation ? `This airport is outside the major-airport outcome study. Weather coverage is not evidence of a calibrated delay estimate.` : "The backtest artifact could not be loaded. No accuracy or confidence figures are inferred."}</p><p>Airport weather remains available above. ${evaluation ? `The study assesses ${evaluation.coverageSummary?.targetAirports || airportCount} major airports; ${airportCount} have at least one tested forecast horizon.` : ''}</p>`;
    return;
  }
  const positive = m.skillInterval95[0] > 0;
  const storm = m.weatherGroups.thunderMentioned; const normal = m.weatherGroups.noThunderMentioned;
  const cohorts = m.cohorts || evaluation!.cohorts;
  const dates = stress ? evaluation!.protocol.previouslySeenStressTest! : evaluation!.protocol.test;
  const periodName = stress ? "Previously seen stress re-evaluation" : evaluation?.evaluationLabel || (evaluation?.selection ? "Fresh winter holdout" : "Held-out test");
  const positiveAdjusted = positive && (m.qValueApproximate === undefined || m.qValueApproximate <= .1);
  get("evidence-content").innerHTML = `<p class="airport-evidence-lead">${direction === "arrivals" ? "Arrivals" : "Departures"} · T−${h} · ${periodName} · ${e(dates[0])} to ${e(dates[1])}. ${positiveAdjusted ? "Weather improved probability accuracy beyond the matched calendar baseline in this test." : "The test does not establish a reliable improvement from adding weather at this airport and horizon."}</p>${stress ? '<p class="airport-notice">These spring dates were inspected during v1. This is a disclosed stress re-evaluation, not a new independent test. Live confidence labels use the winter backtest.</p>' : ''}
    <dl class="airport-story-metrics"><div><dt>Flights in the test</dt><dd>${count(m.flights)}</dd><span>${count(m.windows)} windows · ${m.days} days</span></div><div><dt>Actually disrupted</dt><dd>${pct(m.observedRate, 1)}</dd><span>${pct(m.predictedRate, 1)} predicted on average</span></div><div><dt>Typical window error</dt><dd>${pp(m.mae)}</dd><span>Percentage points · mean absolute error</span></div><div><dt>Evidence for weather’s added value</dt><dd class="airport-evidence-word">${m.evidence === "moderate" ? "Moderate" : "Limited"}</dd><span>Based on held-out support and calibration</span></div></dl>
    <p class="airport-small">${m.method === "airport-local-linear" ? "This model is fitted and calibrated using this airport’s outcomes only. Each horizon keeps its available forecast windows; small windows receive weight according to their flight count." : "This airport retains its original v2 model and airport-specific calibration and backtest. Its original common-horizon eligibility rule still applies."} These are retrospective evaluations; connected flight outcomes and the test dates have been inspected in earlier experiments.</p><div class="airport-evidence-grid"><article><h3>Does getting closer help?</h3><p class="airport-small">${m.method === "airport-local-linear" ? "Available windows differ by horizon, so this first table does not isolate the effect of getting closer." : "Same test windows at every horizon."} Brier improvement compares weather + calendar with calendar alone. Positive is better; a 95% interval crossing zero is inconclusive.</p><div class="airport-table-scroll"><table class="airport-forecast-table airport-horizon-table"><thead><tr><th>Horizon</th><th>Brier improvement</th><th>95% interval</th><th>Window error</th></tr></thead><tbody>${[24, 12, 6].map(hour => { const v = horizons![String(hour)]; if (!v) return `<tr><th>T−${hour}</th><td colspan="3">Insufficient forecast or backtest coverage</td></tr>`; return `<tr class="${h === hour ? "airport-selected-row" : ""}"><th>T−${hour}</th><td>${pct(v.brierSkill, 1)}</td><td>${pct(v.skillInterval95[0], 1)} to ${pct(v.skillInterval95[1], 1)}</td><td>${pp(v.mae)}</td></tr>`; }).join("")}</tbody></table></div>${m.method === "airport-local-linear" ? `<p class="airport-small">Where all three forecasts overlap, compare the supported models on identical windows:</p>${Object.values(horizons!).some(v => v.matchedHorizon) ? `<table class="airport-forecast-table"><thead><tr><th>Horizon</th><th>Matched windows</th><th>Weather Brier ↓</th><th>Calendar Brier ↓</th></tr></thead><tbody>${[24,12,6].map(hour => { const v=horizons![String(hour)]?.matchedHorizon; return v ? `<tr><th>T−${hour}</th><td>${count(v.windows)}</td><td>${v.brier.toFixed(3)}</td><td>${v.baselineBrier.toFixed(3)}</td></tr>` : ""; }).join("")}</tbody></table>` : "<p>No supported three-horizon comparison is available at this airport.</p>"}` : ""}<p>At T−${h}, the model’s Brier score is <strong>${m.brier.toFixed(3)}</strong>, versus <strong>${m.baselineBrier.toFixed(3)}</strong> for the baseline. The calendar-only window error is ${pp(m.baselineMae)}.</p><p class="airport-small">Brier score measures squared probability error across flights. It rewards useful, calibrated probabilities; it is not “percent correct.”</p></article>
    <article><h3>Do the probabilities match reality?</h3>${calibrationPlot(m)}<p class="airport-small">Each circle is a prediction bin; larger circles contain more flights. The diagonal is perfect calibration. Average bin gap: <strong>${pp(m.calibrationError)}</strong>.</p><details><summary>Read the chart as a table</summary><table class="airport-forecast-table"><thead><tr><th>Predicted</th><th>Observed</th><th>Flights</th></tr></thead><tbody>${m.calibration.map(b => `<tr><td>${pct(b.predicted, 1)}</td><td>${pct(b.observed, 1)}</td><td>${count(b.flights)}</td></tr>`).join("")}</tbody></table></details></article></div>
    <div class="airport-evidence-grid"><article><h3>How wide is the uncertainty?</h3><p>The nominal 80% prediction band contained the observed disruption share in <strong>${pct(m.bandCoverage, 1)}</strong> of test windows. Its average width was <strong>${pp(m.bandMeanWidth)}</strong>.</p><p class="airport-small">This is an empirical range for a two-hour airport population. It is neither an individual flight guarantee nor an 80% probability that the model is correct. Seasonal change and correlated disruptions can reduce coverage.</p></article><article><h3>What does the weather story suggest?</h3>${storm && normal ? `<p>When the available TAF mentioned thunderstorms, <strong>${pct(storm.observedRate, 1)}</strong> of flights were disrupted (${count(storm.flights)} flights, ${storm.windows} windows). With no thunderstorm mention: <strong>${pct(normal.observedRate, 1)}</strong> (${count(normal.flights)} flights).</p><p class="airport-small">A descriptive association, not a causal effect. Airport timing, season, and other weather differ between these groups. A missing thunderstorm mention does not mean clear weather.</p>` : '<p>Too few contrasting forecast groups to summarize thunderstorms for this test slice.</p>'}</article></div>
    ${m.previousModel ? `<article class="airport-version-comparison"><h3>Did this version improve on v1?</h3><p>Compared on exactly the same ${count(m.flights)} flight events in this period. Training and calibration dates also changed, so this comparison measures the whole model version.</p><div class="airport-table-scroll"><table class="airport-forecast-table"><thead><tr><th>Metric</th><th>Original v1</th><th>Current model</th></tr></thead><tbody><tr><th>Disruption Brier ↓</th><td>${m.previousModel.brier.toFixed(4)}</td><td>${m.brier.toFixed(4)}</td></tr><tr><th>Band coverage · 80% target</th><td>${pct(m.previousModel.bandCoverage, 1)}</td><td>${pct(m.bandCoverage, 1)}</td></tr><tr><th>Average band width</th><td>${pp(m.previousModel.bandMeanWidth)}</td><td>${pp(m.bandMeanWidth)}</td></tr><tr><th>Interval score ↓</th><td>${m.previousModel.intervalScore.toFixed(3)}</td><td>${m.intervalScore!.toFixed(3)}</td></tr><tr><th>Window error ↓</th><td>${pp(m.previousModel.mae)}</td><td>${pp(m.mae)}</td></tr><tr><th>Cancellation predicted</th><td>${pct(m.previousModel.predictedCancellation, 1)}</td><td>${pct(m.components.cancelled.predictedRate, 1)}</td></tr><tr><th>Cancellation observed</th><td colspan="2">${pct(m.components.cancelled.observedRate, 1)}</td></tr></tbody></table></div><p class="airport-small">V1 used later outcome months and may not have had those releases available by this winter test. Treat it as a retrospective benchmark. Wider intervals alone are not proof of better uncertainty estimates.</p></article>` : ''}
    ${evaluation?.selection ? `<details class="airport-metric-details"><summary>How the model was selected</summary><p>Three earlier seasonal folds compared linear and gradient-boosted weather models at all horizons and directions. Selected: <strong>${evaluation.selection.selected === 'boosted' ? 'gradient-boosted trees' : 'linear logistic model'}</strong>. Mean development Brier: linear ${evaluation.selection.meanBrier.linear.toFixed(4)}; boosted ${evaluation.selection.meanBrier.boosted.toFixed(4)}. The 2026 outcome files were not opened during selection. The current calendar baseline uses the same selected learner and calibration procedure.</p><div class="airport-table-scroll"><table class="airport-forecast-table"><thead><tr><th>Earlier seasonal fold</th><th>Linear Brier</th><th>Boosted Brier</th></tr></thead><tbody>${[...new Set(evaluation.selection.results.map(r => r.fold))].map(fold => { const relevant = evaluation!.selection!.results.filter(r => r.fold === fold && r.direction === direction && r.horizon === h); return `<tr><th>${e(fold)} · ${direction} · T−${h}</th>${['linear','boosted'].map(kind => `<td>${relevant.find(r => r.candidate === kind)?.brier.toFixed(4) || '—'}</td>`).join('')}</tr>`; }).join('')}</tbody></table></div></details>` : ''}
    <details class="airport-metric-details"><summary>More metrics, sample design, and reproducibility</summary><p>Flight-weighted disruption log loss: ${m.logLoss.toFixed(3)}. Lower is better. Cancellation Brier: ${m.components.cancelled.brier.toFixed(4)}; delay Brier: ${m.components.delayed.brier.toFixed(4)}${direction === "arrivals" ? `; diversion Brier: ${m.components.diverted.brier.toFixed(4)}` : ""}. These component probabilities use all scheduled flights as the denominator.</p>${m.qValueApproximate !== undefined ? `<p>The 95% skill interval resamples ${m.bootstrapBlocks} calendar blocks of up to three days. Approximate adjusted q-value: ${m.qValueApproximate.toFixed(3)} across ${m.multipleTestingComparisons || airportCount * 6} comparisons in this period. These exploratory bootstrap calculations do not prove causality. Interval score: ${m.intervalScore!.toFixed(3)} (lower rewards narrow bands that contain the outcome).</p>` : ''}${m.deliverySensitivity ? `<p>With a 60-minute historical weather-delivery lag, ${pct(m.deliverySensitivity.coverage, 1)} of this test’s windows remain covered. Brier score: ${m.deliverySensitivity.brier.toFixed(4)}, compared with ${m.deliverySensitivity.mainBrierSameWindows.toFixed(4)} at the main 10-minute lag on those same windows. The model is not refitted for this check.</p>` : ""}<p>${m.cohorts ? "For this airport, direction, and horizon:" : "For the original 25-airport training cohort, across both directions:"} ${count(cohorts.train.airportWindows)} training windows; ${count(cohorts.probabilityCalibration.airportWindows)} probability-calibration windows; ${count(cohorts.intervalCalibration.airportWindows)} interval-calibration windows; ${count(cohorts[stress ? 'previouslySeenStressTest' : 'test'].airportWindows)} evaluation windows in this period. A flight can contribute an origin and a destination event. ${m.method === "airport-local-linear" ? "All nonempty known-outcome windows are eligible; flights weight the loss. Missing forecasts exclude only the affected horizon." : "Windows with fewer than ten scheduled flights, unknown outcomes, or incomplete forecast coverage at any horizon are excluded."} Source-month edge days and split boundaries are purged.</p><p>These figures describe covered, eligible windows, not every flight at this airport. The JSON includes month-by-month exclusions, source URLs and hashes, the frozen protocol, all assessed major airports, and component metrics.</p><a href="/data/airport-weather/evaluation.json" download>Download the full evaluation</a> · <a href="/data/airport-weather/model.json" download>Download portable model weights</a>${evaluation?.selection ? ' · <a href="/data/airport-weather/versions/v1/evaluation.json" download>Original v1 evaluation</a>' : ''}</details>`;
}

function renderOperationsEvidence() {
  if (!state) return;
  const { airport, direction } = state;
  const stress = evidencePeriod === 'stress';
  const horizons = (stress ? evaluation?.stressAirports : evaluation?.airports)?.[airport.iata]?.directions[direction];
  const h = state.horizon || 6;
  const m = horizons?.[String(h)] as OperationsMetrics | undefined;
  get('evaluation-picker').hidden = !evaluation?.stressAirports;
  get('evidence-title').textContent = `${airport.iata || airport.icao} · does FAA history help?`;
  if (!m) {
    const reason = evaluation?.coverage?.[airport.iata]?.directions[direction]?.[String(h)]?.reason;
    get('evidence-content').innerHTML = `<p class="airport-notice">${reason ? e(readableReason(reason)) : 'No supported operations backtest is available for this airport and horizon.'} Missing outcome evidence is not evidence of low disruption risk.</p>`;
    return;
  }
  const positive = m.skillInterval95[0] > 0 && (m.qValueApproximate ?? 1) <= .1;
  const noFaaSignal = m.trainingWindowsWithFaaActivity === 0;
  const dates = stress ? evaluation!.protocol.previouslySeenStressTest! : evaluation!.protocol.test;
  get('evidence-content').innerHTML = `<p class="airport-evidence-lead">${direction === 'arrivals' ? 'Arrivals' : 'Departures'} · T−${h} · ${e(dates[0])} to ${e(dates[1])}. ${noFaaSignal ? 'No FAA activity occurred in training, so this airport has no learned FAA effect.' : positive ? 'FAA history improved on the matched weather model in this retrospective comparison.' : m.brierSkill < 0 ? 'Adding FAA history increased probability error at this airport and horizon.' : 'The observed gain does not establish a reliable local improvement after uncertainty and multiple comparisons.'}</p>
    <p class="airport-notice">Operations is experimental. These winter and spring periods were examined in earlier research. Models are fitted and calibrated separately at each airport; airline results do not establish private-jet accuracy.</p>
    <dl class="airport-story-metrics"><div><dt>Flight events tested</dt><dd>${count(m.flights)}</dd><span>${count(m.windows)} windows · ${m.days} days</span></div><div><dt>FAA’s added value</dt><dd>${pct(m.brierSkill,2)}</dd><span>Relative Brier-error reduction · negative is worse</span></div><div><dt>Calibration gap</dt><dd>${pp(m.calibrationError)}</dd><span>Predicted versus observed risk bins</span></div><div><dt>Evidence for FAA history</dt><dd class="airport-evidence-word">${m.evidence === 'moderate' ? 'Moderate' : 'Limited'}</dd><span>Winter evidence drives the live label</span></div></dl>
    <div class="airport-evidence-grid"><article><h3>Does FAA information help?</h3><p>Operations Brier error: <strong>${m.brier.toFixed(5)}</strong>. Matched weather: <strong>${m.baselineBrier.toFixed(5)}</strong>. Original served weather model on the same windows: <strong>${m.productionComparator.brier.toFixed(5)}</strong>. Lower is better.</p>
    <p>${noFaaSignal ? 'An FAA improvement interval is not reported: without training activity, tiny fitting differences cannot establish added value. Raw prediction errors remain visible above.' : `The 95% interval for added FAA value is ${pct(m.skillInterval95[0],2)} to ${pct(m.skillInterval95[1],2)}. An interval crossing zero is inconclusive. Approximate adjusted q: ${(m.qValueApproximate ?? 1).toFixed(3)} across ${m.multipleTestingComparisons} comparisons.`}</p>
    <div class="airport-table-scroll"><table class="airport-forecast-table"><thead><tr><th>Horizon</th><th>FAA improvement</th><th>95% interval</th><th>Windows</th></tr></thead><tbody>${[24,12,6].map(hour => {const v=horizons?.[String(hour)] as OperationsMetrics | undefined; return v ? `<tr><th>T−${hour}</th><td>${v.trainingWindowsWithFaaActivity === 0 ? 'No learned effect' : pct(v.brierSkill,2)}</td><td>${v.trainingWindowsWithFaaActivity === 0 ? 'Not estimated' : `${pct(v.skillInterval95[0],2)} to ${pct(v.skillInterval95[1],2)}`}</td><td>${count(v.windows)}</td></tr>` : `<tr><th>T−${hour}</th><td colspan="3">Insufficient evidence</td></tr>`;}).join('')}</tbody></table></div><p class="airport-small">Each row compares identical windows between models. Windows can differ across horizons, so this table does not isolate the benefit of waiting.</p></article>
    <article><h3>Do probabilities match outcomes?</h3>${calibrationPlot(m)}<p>${pct(m.observedRate,1)} were disrupted; ${pct(m.predictedRate,1)} predicted on average. Mean window error: ${pp(m.mae)}.</p><p>Nominal 80% outcome-rate bands covered <strong>${pct(m.bandCoverage,1)}</strong> of windows, with average width ${pp(m.bandMeanWidth)}. ${m.bandCoverage < .8 ? 'Coverage missed the target.' : 'This period met the coverage target.'} These bands describe airport populations, not an individual flight guarantee.</p></article></div>
    <details class="airport-metric-details"><summary>FAA activity, other metrics, and reproducibility</summary><p>${count(m.trainingWindowsWithFaaActivity)} training windows and ${count(m.faaActivityWindows)} evaluation windows had recent FAA messages. ${m.trainingWindowsWithFaaActivity === 0 ? 'No local FAA-message signal was present during fitting; this model cannot learn an FAA effect here.' : 'Counts measure messages, including program revisions and cancellations, rather than distinct events or active restrictions.'} A quiet listing does not rule out congestion, restrictions outside the feed, or operational problems.</p><p>Flight-weighted log loss: ${m.logLoss.toFixed(4)}; matched weather: ${m.weatherComparator.logLoss.toFixed(4)}. Cancellation Brier: ${m.components.cancelled.brier.toFixed(4)}; delay Brier: ${m.components.delayed.brier.toFixed(4)}${direction === 'arrivals' ? `; diversion Brier: ${m.components.diverted.brier.toFixed(4)}` : ''}. Interval score: ${m.intervalScore!.toFixed(3)}. Lower is better.</p>
    ${m.faaDeliverySensitivity ? `<p>With an extra hour of FAA delivery lag, Brier is ${m.faaDeliverySensitivity.brier.toFixed(5)}, versus ${m.faaDeliverySensitivity.mainBrierSameWindows.toFixed(5)} on the same windows with the main lag; ${pct(m.faaDeliverySensitivity.coverage,1)} remain covered.</p>` : ''}
    <p>Publication timestamps and the hourly collection schedule determine what was available. Missing archive days exclude the window from every comparison. Future notices, future observed weather, actual flight volume, and flight outcomes cannot enter earlier features. The dataset uses final-vintage reporting-carrier domestic outcomes.</p><p><a href="/data/airport-weather/operations/evaluation.json" download>Operations evaluation</a> · <a href="/data/airport-weather/operations/model.json" download>Portable weights</a> · <a href="/data/airport-weather/experiments/operations-us-v1.json" download>Nationwide comparison and default decision</a></p></details>`;
}

get('forecast-model').addEventListener('change', async event => {
  modelChoice = (event.target as HTMLSelectElement).value;
  risk = undefined; evaluation = undefined;
  get('forecast-model-note').textContent = operationsMode() ? 'Operations uses weather and recent FAA advisory activity. Local gains and regressions remain visible below.' : 'Weather uses airport forecasts and calendar patterns. FAA notices remain available as context.';
  if (state) renderRisk(state);
  await refreshRisk(snapshotAt);
  if (state) renderRisk(state);
});

export function renderRisk(selection: NonNullable<typeof state>) {
  state = selection;
  wasStale = Boolean(risk && ageMinutes(risk.generatedAt) > 90);
  const { airport, direction, mode } = state;
  get('forecast-model-controls').hidden = mode === 'private';
  const outlook = current(airport); const p = outlook?.probabilities;
  get("outcome-title").textContent = `${airport.iata || airport.icao} ${mode === 'private' ? 'private ' : ''}${direction === "arrivals" ? "arrival" : "departure"} outlook`;
  get("probability-list").hidden = mode === "private";
  get('private-airport-summary').hidden = mode !== 'private';
  get('outcome-kicker').textContent = mode === 'private' ? 'Private-jet airport context' : 'Disruption outlook';
  get('evidence-link').hidden = mode === 'private';
  get("probability-list").innerHTML = (direction === "arrivals" ? ["delayed", "cancelled", "diverted", "onTime"] : ["delayed", "cancelled", "onTime"]).map(key => `<div><dt>${({ delayed: "Delayed ≥15 minutes", cancelled: "Cancelled", diverted: "Diverted", onTime: "Within 15 minutes / early" } as Record<string, string>)[key]}</dt><dd>${p ? pct(p[key as keyof Probabilities], 1) : "—"}${p ? "" : "<span>No estimate</span>"}</dd></div>`).join("");
  document.querySelector(".airport-validation-label")!.textContent = mode === "private" ? "Weather context only" : p ? `Experimental · ${outlook!.evidence} evidence for ${operationsMode() ? 'FAA history’s' : 'weather’s'} added value${outlook!.outsideTrainingRange ? " · unusual input" : ""}` : "No disruption estimate for this selection";
  const m = evaluation?.airports[airport.iata]?.directions[direction]?.[String(state.horizon)];
  get("risk-interval").innerHTML = p ? `<div class="airport-risk-total"><span>Any modeled disruption</span><strong>${pct(p.disruption)}</strong><span>${pct(outlook!.baseline!)} ${operationsMode() ? "matched weather baseline" : "calendar baseline"}</span></div><p class="airport-window">${e(utcLabel(outlook!.start))}–${e(utcLabel(outlook!.end, false))}<br>Experimental range: <strong>${pct(outlook!.band![0])}–${pct(outlook!.band![1])}</strong> of scheduled flights</p>${m ? `<p class="airport-confidence-note"><strong>Coverage check: ${pct(m.bandCoverage)} achieved / 80% target.</strong> ${m.bandCoverage < .8 ? "The band missed its coverage target in the backtest." : "Coverage met the target in this test; it is not guaranteed for future windows."}<br>Cancellation averaged ${pct(m.components.cancelled.predictedRate, 1)} predicted vs ${pct(m.components.cancelled.observedRate, 1)} observed.</p>` : ""}` : "";
  get("model-explanation").textContent = mode === "private" ? "Both aviation views share weather reports, FAA airport notices, and runway inventory. Airline delay probabilities use airline flight outcomes and have not been validated for private jets. Weather categories describe ceiling and visibility, not aircraft operating limits."
    : p ? operationsMode() ? "Estimated shares of scheduled domestic airline flights using weather, calendar patterns, and recent FAA ground-stop/GDP advisory messages. Messages include revisions and cancellations; they do not apply to every flight. Traffic demand, actual runway capacity, and aircraft rotations are not modeled." : "Estimated shares of reporting carriers’ scheduled domestic flights in this two-hour window, using airport weather and calendar patterns. Actual traffic volume and live congestion are not inputs. Includes cancellations already announced; does not look up an individual flight. Percentages are rounded."
    : !evaluation ? "Model evidence is temporarily unavailable. Weather context remains available below."
    : !evaluation.airports[airport.iata] ? "No outcome model has been tested at this airport. Its available weather appears below."
    : state.horizon === null ? "Choose +6h, +12h, or +24h to view a modeled window. Custom times show weather context only."
    : !risk || ageMinutes(risk.generatedAt) > 90 ? "The risk snapshot is unavailable, updating, or older than 90 minutes. Estimates resume after a fresh shared snapshot is available."
    : outlook?.reason ? readableReason(outlook.reason) : "The forecast does not cover the complete modeled window. Missing coverage is not low risk.";
  updateMap(); renderEvidence();
}

export function ageRisk() { if (state && wasStale !== Boolean(risk && ageMinutes(risk.generatedAt) > 90)) renderRisk(state); }
