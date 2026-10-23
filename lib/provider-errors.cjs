'use strict';
// Classification deterministe des erreurs provider (quota guard P5.7).
// Categories: rate_limit | daily_quota_exhausted | transient | auth_denied | permanent | unknown
// FIX P5.7: un epuisement de quota (429/402) n'est JAMAIS confondu avec un refus
// d'autorisation (401/403). L'autorisation est permanente => aucun retry.
const TRANSIENT_STATUS = new Set([408, 425, 429, 500, 502, 503, 504, 509, 522, 524, 599]);
const AUTH_STATUS = new Set([401, 403]);
const PAYMENT_STATUS = new Set([402]);
const PERMANENT_STATUS = new Set([400, 404, 405, 409, 410, 413, 415, 422]);
const DAILY_HINTS = ['daily', 'per day', 'per-day', 'quota exhausted', 'quota exceeded',
  'rate limit exceeded', 'limit reached', 'too many requests', 'insufficient credits',
  'insufficient balance', 'credits exhausted', 'out of credits', 'free tier', 'quota',
  'monthly limit', 'requests per'];
const AUTH_HINTS = ['invalid api key', 'unauthorized', 'forbidden', 'api key',
  'authentication', 'not authorized', 'access denied', 'permission denied',
  'invalid token', 'expired token', 'invalid credentials'];

function parseRetryAfter(v) {
  if (v === undefined || v === null || v === '') return null;
  const s = String(v).trim();
  if (/^\d+$/.test(s)) return Math.max(0, Number(s) * 1000);
  const d = Date.parse(s);
  if (!Number.isNaN(d)) return Math.max(0, d - Date.now());
  return null;
}
function contains(text, hints) {
  if (!text) return false;
  const t = String(text).toLowerCase();
  return hints.some((h) => t.includes(h));
}
function classifyProviderError(err) {
  const e = err || {};
  const status = Number.isFinite(e.status) ? e.status
    : (Number.isFinite(e.statusCode) ? e.statusCode : null);
  const headers = e.headers || {};
  const bodyText = typeof e.body === 'string' ? e.body : (e.body ? JSON.stringify(e.body) : '');
  const text = `${bodyText} ${e.message || ''}`;
  const ra = headers['retry-after'] !== undefined ? headers['retry-after'] : headers['Retry-After'];
  const retryAfterMs = parseRetryAfter(ra);
  const base = { status, retryAfterMs, reason: text.slice(0, 300) };
  // Autorisation AVANT quota : 401/403 => jamais confondu avec un epuisement de quota.
  // Exception documentee : 403 portant un message de solde/credits epuise reste un quota,
  // pas un refus d'autorisation (les deux ne sont pas interchangeables).
  if (AUTH_STATUS.has(status) && !contains(text, DAILY_HINTS))
    return { ...base, category: 'auth_denied', retryAfterMs: null };
  if (contains(text, AUTH_HINTS) && !contains(text, DAILY_HINTS) && !AUTH_STATUS.has(status))
    return { ...base, category: 'auth_denied', retryAfterMs: null };
  if (status === 429) {
    const daily = contains(text, DAILY_HINTS) || (retryAfterMs !== null && retryAfterMs >= 3600000);
    return { ...base, category: daily ? 'daily_quota_exhausted' : 'rate_limit' };
  }
  if (PAYMENT_STATUS.has(status) || contains(text, DAILY_HINTS))
    return { ...base, category: 'daily_quota_exhausted' };
  if (TRANSIENT_STATUS.has(status) || (status !== null && status >= 500))
    return { ...base, category: 'transient' };
  if (PERMANENT_STATUS.has(status) || (status !== null && status >= 400 && status < 500))
    return { ...base, category: 'permanent' };
  if (/timeout|timed out|ECONNRESET|ETIMEDOUT|ENOTFOUND|ECONNREFUSED|socket hang up|EPIPE/i.test(text))
    return { ...base, category: 'transient' };
  if (/invalid api key|bad request|not found/i.test(text))
    return { ...base, category: 'permanent' };
  return { ...base, category: 'unknown' };
}
module.exports = { classifyProviderError, parseRetryAfter };
