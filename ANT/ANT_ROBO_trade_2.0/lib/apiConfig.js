const LOCAL_HOSTNAMES = ['localhost', '127.0.0.1', '::1'];
// Set NEXT_PUBLIC_API_URL at build time to point a deployed frontend at its API.
const PRODUCTION_API_URL = process.env.NEXT_PUBLIC_API_URL || 'https://api.antcryptotrade.example';
const LOCAL_API_URL = 'http://localhost:8000';

export function getApiBaseUrl() {
  if (typeof window === 'undefined') {
    return PRODUCTION_API_URL;
  }

  return LOCAL_HOSTNAMES.includes(window.location.hostname)
    ? LOCAL_API_URL
    : PRODUCTION_API_URL;
}

// response.json() throws "Unexpected end of JSON input" on a body that isn't
// valid JSON - an empty 204, or an HTML error page from a reverse proxy on a
// 502/504, which is otherwise an uncaught SyntaxError instead of the normal
// `data.detail || 'fallback message'` handling every page already has.
export async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

// Formatting helpers shared by every page. USDT amounts are shown to 2 decimals;
// prices adapt their precision to the coin (BTC at 2dp, SHIB at 8dp).
export function formatUsd(value, digits = 2) {
  const n = Number(value);
  return (Number.isFinite(n) ? n : 0).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function formatPrice(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  const abs = Math.abs(n);
  const digits = abs >= 1000 ? 2 : abs >= 1 ? 4 : abs >= 0.01 ? 6 : 8;
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: digits });
}

export function formatQty(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '-';
  return n.toLocaleString('en-US', { maximumFractionDigits: 8 });
}

// Server timestamps are naive local datetimes; parse as-is.
export function formatDateTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}
