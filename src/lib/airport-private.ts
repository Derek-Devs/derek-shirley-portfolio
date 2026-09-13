import { ageMinutes, groupLabel, isConditional, latestForecast, periodsAt, utcLabel,
  type Conditions, type Period, type Station } from './airport-weather.ts';

export type FlightCategory = 'VFR' | 'MVFR' | 'IFR' | 'LIFR' | 'unknown';
export type WeatherSummary = {
  category: FlightCategory;
  status: 'available' | 'partial' | 'no-forecast' | 'outside-coverage' | 'stale' | 'unavailable';
  label: string;
  detail: string;
  prevailing?: Period;
  conditional: { category: FlightCategory; label: string }[];
};

// NOAA AWC ceiling/visibility categories: https://aviationweather.gov/gfa/help/
// These are weather descriptors, not aircraft operating minima or safety scores.
export function flightCategory(conditions: Conditions): FlightCategory {
  const text = conditions.visibilityMi?.trim();
  const match = text?.match(/^(\d+(?:\.\d+)?)([+-]?)$/);
  if (!match) return 'unknown';
  // A censored range that crosses category thresholds cannot establish a category.
  if ((match[2] === '+' && Number(match[1]) < 5) || (match[2] === '-' && (Number(match[1]) > 1 || Number(match[1]) === 0))) return 'unknown';
  const visibility = Number(match[1]) + (match[2] === '+' ? .000001 : match[2] === '-' ? -.000001 : 0);
  if (!Number.isFinite(visibility) || visibility < 0) return 'unknown';
  const ceilingLayers = conditions.clouds.filter(c => ['BKN', 'OVC', 'VV', 'OVX'].includes(c.cover || ''));
  if (ceilingLayers.some(c => c.baseFt === null && !(['VV', 'OVX'].includes(c.cover || '') && conditions.verticalVisibilityFt !== null))) return 'unknown';
  const knownSky = conditions.clouds.length > 0 && conditions.clouds.every(c => ['CLR', 'SKC', 'NSC', 'NCD', 'CAVOK', 'FEW', 'SCT', 'BKN', 'OVC', 'VV', 'OVX'].includes(c.cover || ''));
  if (!knownSky && conditions.verticalVisibilityFt === null) return 'unknown';
  const ceilings = ceilingLayers.filter(c => c.baseFt !== null).map(c => c.baseFt!);
  if (conditions.verticalVisibilityFt !== null) ceilings.push(conditions.verticalVisibilityFt);
  const ceiling = Math.min(...ceilings); // An explicit clear / non-ceiling sky is unbounded.
  if (ceiling < 500 || visibility < 1) return 'LIFR';
  if (ceiling < 1000 || visibility < 3) return 'IFR';
  if (ceiling <= 3000 || visibility <= 5) return 'MVFR';
  return 'VFR';
}

export function privateWeather(station: Station | undefined, target: number, snapshotAt: string,
  asOf = Date.now(), loadError = false): WeatherSummary {
  const empty = { category: 'unknown' as const, conditional: [] };
  if (loadError) return { ...empty, status: 'unavailable', label: 'Weather unavailable', detail: 'This airport’s weather download failed. Refresh data to try again.' };
  if (!snapshotAt || !Number.isFinite(Date.parse(snapshotAt)) || ageMinutes(snapshotAt, asOf) > 90) {
    return { ...empty, status: 'stale', label: 'Older snapshot', detail: 'The shared snapshot is older than 90 minutes. Forecast categories are withheld until it refreshes.' };
  }
  const latest = latestForecast(station, asOf);
  if (!latest) return { ...empty, status: 'no-forecast', label: 'No airport forecast', detail: station?.observation
    ? 'An observation is available, but this snapshot has no airport forecast. Current conditions cannot fill a future forecast gap.'
    : 'This snapshot has no airport forecast or observation for this airport.' };
  const from = Date.parse(latest.validFrom); const to = Date.parse(latest.validTo);
  if (!(from <= target && target < to)) return { ...empty, status: 'outside-coverage', label: 'Outside forecast coverage',
    detail: `${target >= to ? 'Latest forecast ends' : 'Latest forecast starts'} ${utcLabel(target >= to ? to : from)}; selected time is ${utcLabel(target)}. ${target >= to ? 'Try an earlier look-ahead or wait for a later forecast issue.' : 'Choose a time within this forecast’s valid period.'}` };
  const periods = periodsAt(latest, target);
  const bases = periods.filter(p => !isConditional(p));
  const prevailing = bases.length === 1 && bases[0].change !== 'BECMG' ? bases[0] : undefined;
  if (!prevailing) return { ...empty, status: 'partial', label: 'Forecast needs review', detail: 'No unambiguous prevailing group covers this time. Review the original forecast and its change groups below.' };
  const category = flightCategory(prevailing);
  const conditional = periods.filter(isConditional).map(p => ({ label: groupLabel(p), category: flightCategory({
    ...p, visibilityMi: p.visibilityMi ?? prevailing.visibilityMi,
    // Only a change group inherits omitted fields; never fill a missing prevailing field.
    clouds: p.clouds.length || p.verticalVisibilityFt !== null ? p.clouds : prevailing.clouds,
    verticalVisibilityFt: p.clouds.length ? p.verticalVisibilityFt : p.verticalVisibilityFt ?? prevailing.verticalVisibilityFt,
  }) }));
  return { category, conditional, prevailing, status: category === 'unknown' ? 'partial' : 'available',
    label: category === 'unknown' ? 'Ceiling / visibility incomplete' : `${category} prevailing`,
    detail: `Forecast issued ${utcLabel(latest.issuedAt)} · covers through ${utcLabel(latest.validTo)}.${conditional.length ? ' Temporary / probability groups are shown separately, not treated as certain.' : ''}` };
}

export function lookaheadTime(hours: number, mode: string, now: number, modeledTime: number) {
  return mode === 'airline' && Number.isFinite(modeledTime) && modeledTime > now ? modeledTime : now + hours * 3600000;
}
