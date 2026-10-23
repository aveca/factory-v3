'use strict';
// Classification deterministe des erreurs provider (quota guard).
// Categories: rate_limit | daily_quota_exhausted | transient | permanent | unknown
const TRANSIENT = new Set([408, 425, 500, 502, 503, 504, 509, 522, 524, 599]);
const PAYMENT = new Set([402, 403]);
const DAILY = ['daily', 'per day', 'per-day', 'quota exhausted', 'quota exceeded',
  'rate limit exceeded', 'limit reached', 'too many requests', 'insufficient credits',
  'credits exhausted', 'out of credits', 'free tier', 'quota', '429'];

function parseRetryAfter(v) {
  if (v === undefined || v === null || v === '') return null;
  const s = String(v).trim();
  if (/^\d+$/.test(s)) return Math.max(0, Number(s) * 1000);
  const d = Date.parse(s);
  if (!Number.isNaN(d)) return Math.max(0, d - Date.now());
  return null;
}
function looksDaily(t) {
  if (!t) return false;
  t = String(t).toLowerCase();
  return DAILY.some((h) => t.includes(h));
}
function classifyProviderError(err) {
  const e = err || {};
  let status = Number.isFinite(e.status) ? e.status
    : (Number.isFinite(e.statusCode) ? e.statusCode : null);
  const headers = e.headers || {};
  const bodyText = typeof e.body === 'string' ? e.body : (e.body ? JSON.stringify(e.body) : '');
  const text = `${bodyText} ${e.message || ''}`;
  const ra = headers['retry-after'] !== undefined ? headers['retry-after'] : headers['Retry-After'];
  const retryAfterMs = parseRetryAfter(ra);
  if (status === 429) {
    if (looksDaily(text) || (retryAfterMs !== null && retryAfterMs >= 3600000))
      return { category: 'daily_quota_exhausted', status, retryAfterMs, reason: text.slice(0, 200) };
    return { category: 'rate_limit', status, retryAfterMs, reason: text.slice(0, 200) };
  }
  if (PAYMENT.has(status))
    return { category: 'daily_quota_exhausted', status, retryAfterMs, reason: text.slice(0, 200) };
  if (TRANSIENT.has(status))
    return { category: 'transient', status, retryAfterMs, reason: text.slice(0, 200) };
  if (status !== null && status >= 500)
    return { category: 'transient', status, retryAfterMs, reason: text.slice(0, 200) };
  if (status !== null && status >= 400 && status < 500)
    return { category: 'permanent', status, retryAfterMs, reason: text.slice(0, 200) };
  if (/timeout|timed out|ECONNRESET|ETIMEDOUT|ENOTFOUND|ECONNREFUSED|socket hang up/i.test(text))
    return { category: 'transient', status, retryAfterMs, reason: text.slice(0, 200) };
  if (/invalid api key|unauthorized|forbidden|not found|bad request/i.test(text))
    return { category: 'permanent', status, retryAfterMs, reason: text.slice(0, 200) };
  return { category: 'unknown', status, retryAfterMs, reason: text.slice(0, 200) };
}
module.exports = { classifyProviderError, parseRetryAfter };
