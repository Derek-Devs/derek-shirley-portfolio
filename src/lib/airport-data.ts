/** Optional public static CDN. This contains no credentials and never invokes a compute endpoint. */
export function normalizeDataBase(value?: string) {
  if (!value) return '/data/airport-weather';
  const url = new URL(value);
  if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash
      || !/^[a-z0-9]+\.cloudfront\.net$/.test(url.hostname) || url.pathname !== '/') {
    throw new Error('Airport data must use the reviewed HTTPS CloudFront distribution.');
  }
  return url.origin;
}

export function generationPath(prefix?: string) {
  if (!prefix) return '';
  if (!/^snapshots\/\d{8}T\d{6}Z$/.test(prefix)) throw new Error('Invalid airport snapshot generation');
  return '/' + prefix;
}

export const AIRPORT_DATA_BASE = normalizeDataBase(import.meta.env?.PUBLIC_AIRPORT_DATA_URL);
let generation = '';
export function setAirportGeneration(prefix?: string) { generation = generationPath(prefix); }
export function airportDataUrl(path: string, shared = false) {
  return `${AIRPORT_DATA_BASE}${shared ? '' : generation}/${path}`;
}
