import { escapeHtml as e, utcLabel } from "../lib/airport-weather";

interface ReplayForecast { cutoff: string; issuedAt: string; productId: string; coverage: "full" | "partial" }
interface ReplayWindow {
  start: string; end: string; direction: string; counts: Record<string, number>;
  forecasts: Record<string, ReplayForecast | null>;
}
interface ReplayIssue { id: string; raw: string; periods: { from: string; to: string; type: string; raw: string }[] }
interface ReplayData {
  month: string; windows: ReplayWindow[]; issues: ReplayIssue[]; qa: Record<string, number>;
  forecastIssues: number; availabilityAssumptionMinutes: number;
}
const element = <T extends HTMLElement>(id: string) => document.getElementById(id) as T;
const value = (id: string) => element<HTMLInputElement>(id).value;
let data: ReplayData;

function localParts(utc: string) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Chicago", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", hourCycle: "h23",
  }).formatToParts(new Date(utc));
  const part = (type: string) => parts.find(p => p.type === type)?.value;
  return { date: `${part("year")}-${part("month")}-${part("day")}`, hour: Number(part("hour")) };
}

function render() {
  const date = value("replay-date");
  const hour = Number(value("replay-window"));
  const direction = value("replay-direction");
  const window = data.windows.find(w => {
    const local = localParts(w.start);
    return w.direction === direction && local.date === date && local.hour === hour;
  });
  if (!window) {
    element("replay-result").innerHTML = '<p class="airport-notice">No scheduled flights are represented in this sample for that window. No rate is calculated.</p>';
    return;
  }
  const categories = [["onTime", "Less than 15m late"], ["delayed", "Delayed ≥15m"], ["cancelled", "Cancelled"],
    ...(direction === "arrivals" ? [["diverted", "Diverted"]] : []), ...(window.counts.unknown ? [["unknown", "Outcome missing"]] : [])];
  const total = window.counts.scheduled;
  element("replay-result").innerHTML = `
    <div class="airport-replay-outcomes"><p class="airport-kicker">Observed afterward · ${e(utcLabel(window.start))}–${e(utcLabel(window.end))}</p><h3>${total} scheduled ${e(direction)} in the sample</h3>
    <dl class="airport-replay-rates">${categories.map(([key, label]) => `<div><dt>${e(label)}</dt><dd>${(window.counts[key] / total * 100).toFixed(1)}%<span>${window.counts[key]} of ${total} flights</span></dd></div>`).join("")}</dl>
    <p class="airport-small">These percentages are historical observations, not forecast probabilities. “Less than 15m late” includes early flights. Severe delay (≥60m) or cancellation: ${window.counts.severe} flights.${date === "2025-05-01" && direction === "arrivals" ? " Month-boundary coverage may be incomplete." : ""}</p></div>
    <div class="airport-replay-forecasts">${[24, 12, 6].map(h => {
      const forecast = window.forecasts[String(h)];
      const issue = data.issues.find(i => i.id === forecast?.productId);
      if (!forecast || !issue) return `<article><h3>T−${h} hours</h3><p>No forecast coverage found at this cutoff.</p></article>`;
      const periods = issue.periods.filter(p => Date.parse(p.from) < Date.parse(window.end) && Date.parse(p.to) > Date.parse(window.start));
      return `<article><h3>T−${h} hours</h3><p class="airport-small">Cutoff ${e(utcLabel(forecast.cutoff))}<br>Issued ${e(utcLabel(forecast.issuedAt))}</p><p class="airport-replay-coverage">${forecast.coverage === "full" ? "Covers the full window" : "Partial window coverage"}</p>${periods.map(p => `<div class="airport-replay-period"><span>${e(p.type === "Forecast" ? "Prevailing change" : p.type)} · ${e(utcLabel(p.from))}–${e(utcLabel(p.to))}</span><code>${e(p.raw)}</code></div>`).join("")}<details><summary>Original forecast bulletin</summary><pre>${e(issue.raw)}</pre></details></article>`;
    }).join("")}</div>`;
}

element("load-replay").addEventListener("click", async () => {
  const button = element<HTMLButtonElement>("load-replay");
  button.disabled = true;
  button.textContent = "Loading the historical sample…";
  try {
    const response = await fetch("/data/airport-weather/replay.json", { signal: AbortSignal.timeout(20000) });
    if (!response.ok) throw new Error("Unavailable");
    data = await response.json();
    const represented = data.windows.reduce((sum, w) => sum + w.counts.scheduled, 0);
    const excludedTime = (data.qa.excluded_arrivals_time || 0) + (data.qa.excluded_departures_time || 0);
    element("replay-audit").textContent = `${data.qa.dfwRows.toLocaleString()} DFW-related source records; ${represented.toLocaleString()} represented across ${data.windows.length} nonempty airport windows. ${data.qa.outsideLocalMonth || 0} fall outside the DFW local month; ${excludedTime} could not be placed in time; ${data.qa.duplicatesSkipped || 0} duplicates were excluded. ${data.forecastIssues} original forecast bulletins were checked. Windows without flights are not assigned a zero disruption rate.`;
    element("replay-content").hidden = false;
    element("replay-error").hidden = true;
    button.hidden = true;
    render();
  } catch {
    button.disabled = false;
    button.textContent = "Try loading the historical sample again";
    element("replay-error").textContent = "The historical sample could not be loaded. Live weather and the research design remain available.";
    element("replay-error").hidden = false;
  }
});
element("replay-form").addEventListener("submit", event => { event.preventDefault(); if (data) render(); });
