import { escapeHtml as e, utcLabel, type Airport, type DataSource, type Station } from './airport-weather.ts';

const FAA_URL = 'https://nasstatus.faa.gov/';
const RUNWAY_URL = 'https://ourairports.com/data/';
const titles: Record<string, string> = {
  'ground-stop': 'Ground stop', 'ground-delay': 'Ground delay program',
  closure: 'Closure / access restriction', 'arrival-departure-delay': 'Arrival / departure delays',
};

function recent(value: string | undefined, minutes: number, now: number) {
  const at = Date.parse(value ?? '');
  return Number.isFinite(at) && at <= now + 300000 && now - at <= minutes * 60000;
}

export function faaState(station: Station | undefined, source: DataSource | undefined, now = Date.now()) {
  if (!source?.fetchedAt || !station?.faa) return 'unavailable';
  if (source.status !== 'ok' || !recent(source.fetchedAt, 90, now) || !recent(source.issuedAt, 90, now)) return 'stale';
  if (!station.faa.identifierAvailable) return 'unmapped';
  return station.faa.events.length ? 'reported' : 'none-reported';
}

export function operationsPanel(airport: Airport, station: Station | undefined, sources: Record<string, DataSource>, now = Date.now()) {
  const faa = sources.faa;
  const state = faaState(station, faa, now);
  const events = station?.faa?.events ?? [];
  const labels = {
    unavailable: 'FAA status unavailable', stale: 'FAA status needs an update',
    unmapped: 'FAA identifier coverage unavailable', reported: `${events.length} FAA notice${events.length === 1 ? '' : 's'} reported`,
    'none-reported': 'No airport notices reported in this feed',
  };
  const faaTimes = faa?.fetchedAt ? `Feed updated ${e(utcLabel(faa.issuedAt ?? ''))} · downloaded ${e(utcLabel(faa.fetchedAt))}` : 'No FAA download in this snapshot.';
  const inventory = station?.runways;
  const runwaySource = sources.runways;
  const records = inventory?.runways ?? [];
  const open = records.filter(r => r.closed === false);
  const lengths = open.flatMap(r => r.lengthFt === null ? [] : [r.lengthFt]);
  const longest = lengths.length ? `${Math.max(...lengths).toLocaleString('en-US')} ft` : 'Not reported';
  const unknownStatus = records.filter(r => r.closed === null).length;
  const runwayOld = runwaySource?.status !== 'ok' || !recent(runwaySource?.fetchedAt, 45 * 1440, now);
  const runwayTimes = runwaySource?.fetchedAt ? `Downloaded ${e(utcLabel(runwaySource.fetchedAt))} · checked monthly${runwayOld ? ' · refresh overdue or failed' : ''}` : 'No runway download in this snapshot.';
  return `<section class="airport-operations" aria-labelledby="operations-${e(airport.icao)}">
    <div class="airport-operations-heading"><h3 id="operations-${e(airport.icao)}">Airport operations context</h3><span>Observed status + static inventory</span></div>
    <p class="airport-small">These details provide context for ${e(airport.iata || airport.icao)}. They are not included in the delay probabilities.</p>
    <div class="airport-operations-grid">
      <div class="airport-operations-card airport-faa" data-faa-state="${state}">
        <h4>FAA restrictions & delays</h4><p class="airport-operations-status">${e(labels[state])}</p>
        <p class="airport-small">${faaTimes}</p>
        ${state === 'stale' ? '<p class="airport-notice">The last report is old or its refresh failed. Notices below are historical context; current status is unknown.</p>' : ''}
        ${events.length ? `<ul class="airport-notices">${events.map(event => `<li><strong>${e(titles[event.type] ?? 'FAA notice')}</strong>
          ${['ground-stop', 'ground-delay'].includes(event.type) ? '<p class="airport-small">Can hold flights bound for this airport at their departure airports.</p>' : ''}
          <p class="airport-faa-reason">${e(event.reason || 'Reason not supplied')}</p>
          ${event.details.length ? `<dl class="airport-notice-details">${event.details.map(d => `<div><dt>${e(d.label)}</dt><dd>${e(d.value)}</dd></div>`).join('')}</dl>` : ''}
          ${event.type === 'closure' ? '<p class="airport-small">The FAA wording may limit this restriction to certain flights or list exceptions. This does not automatically mean the entire airport is closed.</p>' : ''}
        </li>`).join('')}</ul>` : ''}
        <p class="airport-small">Status is reported at the feed time, not forecast for your selected flight time. An absent notice does not establish normal operations. This feed is not a complete NOTAM or route briefing.${faa?.unassignedAirspaceGroups?.length ? ' En-route flow programs are present but are not assigned to individual airports here.' : ''}</p>
        <a href="${FAA_URL}" target="_blank" rel="noopener noreferrer">Check FAA NAS Status ↗</a>
      </div>
      <div class="airport-operations-card airport-runways">
        <h4>Runway inventory</h4><p class="airport-small">${runwayTimes}</p>
        ${records.length ? `<dl class="airport-metrics airport-runway-metrics"><div><dt>Listed open runways</dt><dd>${open.length}</dd></div><div><dt>Longest listed open runway</dt><dd>${longest}</dd></div></dl>
          ${unknownStatus ? `<p class="airport-small">Open/closed status is missing for ${unknownStatus} additional record${unknownStatus === 1 ? '' : 's'}.</p>` : ''}
          <details class="airport-raw"><summary>Runway dimensions & headings (${records.length} records)</summary><div class="airport-table-scroll"><table class="airport-forecast-table"><caption>OurAirports inventory · runway ends are one physical runway</caption><thead><tr><th scope="col">Runway</th><th scope="col">Dimensions</th><th scope="col">Surface / lighting</th><th scope="col">True headings</th></tr></thead><tbody>${records.map(r => `<tr><th scope="row">${e(r.ends.filter(Boolean).join(' / ') || 'Unnamed')}<span>${r.closed === true ? 'Listed closed' : r.closed === false ? 'Listed open' : 'Status not reported'}</span></th><td>${r.lengthFt === null ? 'Length unknown' : `${r.lengthFt.toLocaleString('en-US')} ft`}<span>${r.widthFt === null ? 'Width unknown' : `${r.widthFt.toLocaleString('en-US')} ft wide`}</span></td><td>${e(r.surface || 'Surface not reported')}<span>${r.lighted === null ? 'Lighting not reported' : r.lighted ? 'Listed lighted' : 'Listed unlighted'}</span></td><td>${r.headingsTrue.map(h => h === null ? 'Unknown' : `${h}°T`).join(' / ')}</td></tr>`).join('')}</tbody></table></div></details>
          ${inventory?.sourceIdent !== airport.icao ? `<p class="airport-small">Matched to source identifier ${e(inventory?.sourceIdent)} using the documented airport rename and runway coordinates.</p>` : ''}` : '<p class="airport-operations-status">No matching runway inventory available</p>'}
        <p class="airport-small">Inventory describes the airport’s layout, not the runways currently in use, temporary closures, aircraft suitability, or arrivals/departures per hour. More runways do not automatically mean more usable capacity.</p>
        <a href="${RUNWAY_URL}" target="_blank" rel="noopener noreferrer">Source: OurAirports ↗</a>
      </div>
    </div>
  </section>`;
}
