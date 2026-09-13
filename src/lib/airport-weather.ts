export interface Airport {
  icao: string; iata: string; name: string; city: string; country: string;
  size: string; lat: number | null; lon: number | null;
}
export const US_COUNTRIES = new Set(['US', 'PR', 'VI', 'GU', 'MP', 'AS']);
export const isUsAirport = (airport: Pick<Airport, 'country'>) => US_COUNTRIES.has(airport.country);
export interface Conditions {
  windDirection: string | null; windKt: number | null; gustKt: number | null;
  visibilityMi: string | null; weather: string | null;
  clouds: { cover: string | null; baseFt: number | null; type: string | null }[];
  verticalVisibilityFt: number | null;
}
export interface Period extends Conditions {
  from: string; to: string; change: string; becomingAt: string | null; probability: number | null;
}
export interface Observation extends Conditions {
  id: string; raw: string; observedAt: string; firstSeenAt: string;
  temperatureC: number | null; dewpointC: number | null;
}
export interface Forecast {
  id: string; raw: string; issuedAt: string; firstSeenAt: string;
  validFrom: string; validTo: string; periods: Period[];
}
export interface FaaEvent {
  id: string; type: string; airportCode: string; reason: string; firstSeenAt: string;
  details: { label: string; value: string }[];
}
export interface Runway {
  id: string; ends: string[]; lengthFt: number | null; widthFt: number | null;
  surface: string; lighted: boolean | null; closed: boolean | null; headingsTrue: (number | null)[];
}
export interface Station {
  observation: Observation | null; tafs: Forecast[];
  faa?: { events: FaaEvent[]; identifierAvailable: boolean };
  runways?: { sourceIdent: string; runways: Runway[] };
}
export interface DataSource {
  fetchedAt?: string; issuedAt?: string; attemptedAt?: string; status: string;
  unassignedAirspaceGroups?: string[];
}
export interface Snapshot {
  scope?: string;
  dataPrefix?: string;
  generatedAt: string; refreshMinutes: number;
  sources: Record<string, DataSource>;
  coverage: { airports: number; observations: number; forecasts: number; validatedAirports: number };
}

export const escapeHtml = (value: unknown) => String(value ?? "").replace(/[&<>"']/g,
  char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]!);

export function utcLabel(value: string | number, date = true) {
  const d = new Date(value);
  if (!Number.isFinite(d.getTime())) return "Unavailable";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC", ...(date ? { month: "short", day: "numeric" } as const : {}),
    hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).format(d) + " UTC";
}

export function ageMinutes(value: string | undefined, now = Date.now()) {
  return value ? Math.max(0, (now - Date.parse(value)) / 60000) : Infinity;
}

export function windLabel(c: Conditions) {
  if (c.windKt === null) return "Not reported";
  if (c.windKt === 0) return "Calm";
  const direction = c.windDirection === "VRB" ? "Variable" : c.windDirection ? `${c.windDirection}°` : "";
  return `${direction} ${c.windKt} kt${c.gustKt !== null ? ` · gust ${c.gustKt}` : ""}`.trim();
}

export function ceilingLabel(c: Conditions) {
  const ceilings = c.clouds.filter(c => ["BKN", "OVC", "VV"].includes(c.cover ?? "") && c.baseFt !== null).map(c => c.baseFt!);
  if (c.verticalVisibilityFt !== null) ceilings.push(c.verticalVisibilityFt);
  if (ceilings.length) return `${Math.min(...ceilings).toLocaleString("en-US")} ft AGL`;
  return c.clouds.length ? "No ceiling reported" : "Not reported";
}

export function weatherLabel(c: Conditions) {
  if (!c.weather) return "No weather code reported";
  const descriptions = [
    ["TS", "Thunderstorms"], ["FZ", "Freezing conditions"], ["RA", "Rain"],
    ["SN", "Snow"], ["GR", "Hail"], ["GS", "Small hail / snow pellets"],
    ["FG", "Fog"], ["BR", "Mist"], ["HZ", "Haze"], ["DZ", "Drizzle"],
  ].filter(([code]) => c.weather!.includes(code)).map(([, label]) => label);
  return descriptions.length ? `${descriptions.join(" · ")} (${c.weather})` : c.weather;
}

export function groupLabel(period: Period) {
  const probability = period.probability !== null ? `${period.probability}% weather group` : "Probability group";
  if (period.change.includes("PROB") || period.probability !== null) {
    return `${probability}${period.change.includes("TEMPO") ? " · temporary" : ""}`;
  }
  if (period.change === "TEMPO") return "Temporary";
  if (period.change === "BECMG") return "Transition";
  return "Prevailing";
}

export function isConditional(period: Period) {
  return period.change.includes("TEMPO") || period.change.includes("PROB") || period.probability !== null;
}

export function latestForecast(station: Station | undefined, asOf = Date.now()) {
  // A future issue/retrieval cannot be used, even if its validity includes the target.
  return station?.tafs.filter(f => Date.parse(f.issuedAt) <= asOf && Date.parse(f.firstSeenAt) <= asOf)
    .sort((a, b) => Date.parse(b.issuedAt) - Date.parse(a.issuedAt))[0];
}

export function forecastAt(station: Station | undefined, target: number, asOf = Date.now()) {
  const latest = latestForecast(station, asOf);
  // Never extend coverage with an older, superseded forecast just because it lasts longer.
  return latest && Date.parse(latest.validFrom) <= target && target < Date.parse(latest.validTo) ? latest : undefined;
}

export function periodsAt(forecast: Forecast | undefined, target: number) {
  return forecast?.periods.filter(p => Date.parse(p.from) <= target && target < Date.parse(p.to)) ?? [];
}

export function findAirport(airports: Airport[], input: string) {
  const code = input.trim().split(/\s|—/)[0].toUpperCase();
  if (!code) return undefined;
  return airports.find(a => a.icao === code) ?? airports.find(a => a.iata === code)
    ?? airports.find(a => a.name.toLowerCase() === input.trim().toLowerCase());
}
