'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');
const assert = require('assert');
const { QuotaStore } = require('../quota-store.cjs');
const { QuotaGuard, EXECUTE, WAIT, PARK, FAIL } = require('../quota-guard.cjs');
const { classifyProviderError } = require('../provider-errors.cjs');
const TMP = path.join(os.tmpdir(), 'qg-test-' + Date.now() + '.json');
let failures = 0;
function ok(label, cond) { if (cond) { console.log('PASS', label); } else { failures++; console.log('FAIL', label); } }

// 1. Classification 429 sans Retry-After = rate_limit
let c = classifyProviderError({ status: 429, body: 'rate limited', headers: {} });
ok('429 sans Retry-After -> rate_limit', c.category === 'rate_limit' && c.status === 429);

// 2. Classification 429 avec indice quotidien = daily_quota_exhausted
c = classifyProviderError({ status: 429, body: 'quota exhausted daily limit', headers: {} });
ok('429 + daily -> daily_quota_exhausted', c.category === 'daily_quota_exhausted');

// 3. Classification 429 avec Retry-After long = daily_quota_exhausted
c = classifyProviderError({ status: 429, body: 'rate limit', headers: { 'retry-after': '5000' } });
ok('429 + Retry-After 5000s -> daily_quota_exhausted', c.category === 'daily_quota_exhausted');

// 4. Classification 500 = transient
c = classifyProviderError({ status: 500, body: 'internal error', headers: {} });
ok('500 -> transient', c.category === 'transient');

// 5. Classification 400 = permanent
c = classifyProviderError({ status: 400, body: 'bad request', headers: {} });
ok('400 -> permanent', c.category === 'permanent');

// 6. ECONNREFUSED -> transient
c = classifyProviderError({ message: 'connect ECONNREFUSED', headers: {} });
ok('ECONNREFUSED -> transient', c.category === 'transient');

// 7. parseRetryAfter secondes
const ra = classifyProviderError({ status: 429, body: 'x', headers: { 'retry-after': '30' } });
ok('retry-after 30s = 30000ms', ra.retryAfterMs === 30000);

// 8. Quota store: canUse / cooldown
const s = new QuotaStore(TMP);
s.model('m1').cooldownUntil = Date.now() + 60000;
ok('canUse cooldown -> false', s.canUse('m1') === false);
s.model('m2').cooldownUntil = 0;
ok('canUse ok -> true', s.canUse('m2') === true);

// 9. QuotaGuard beforeAttempt EXECUTE
const g = new QuotaGuard(s, { maxTotalAttempts: 4 });
const m = g.open('mission-1', ['ollama:qwen', 'ollama:deepseek'], { text: 'hello' });
ok('mission opened running', m.status === 'running');
const b = g.beforeAttempt('mission-1');
ok('beforeAttempt EXECUTE fresh', b.action === EXECUTE && b.model === 'ollama:qwen' && b.attempt === 1);

// 10. Failures: exhaust model then switch
for (let i = 0; i < 3; i++) g.afterFailure('mission-1', 'ollama:qwen', { status: 429, body: 'quota daily', headers: {} });
ok('after 3 failures model exhausted', s.model('ollama:qwen').consecutiveFailures === 3);
const b2 = g.beforeAttempt('mission-1');
ok('beforeAttempt switches model', b2.action === EXECUTE && b2.model === 'ollama:deepseek');

// 11. Permanent error -> FAIL
const g2 = new QuotaGuard(s, { maxTotalAttempts: 4 });
const m2 = g2.open('mission-2', ['ollama:x'], { text: 'y' });
const res2 = g2.afterFailure('mission-2', 'ollama:x', { status: 400, body: 'bad' });
ok('permanent -> FAIL', res2.action === FAIL);

// 12. No model available -> PARK pending
const g3 = new QuotaGuard(s, { maxTotalAttempts: 4 });
const m3 = g3.open('mission-3', ['ollama:dead'], { text: 'z' });
for (let i = 0; i < 4; i++) g3.afterFailure('mission-3', 'ollama:dead', { status: 429, body: 'daily', headers: {} });
const b3 = g3.beforeAttempt('mission-3');
ok('no model usable -> PARK', b3.action === PARK);

// 13. Total attempts exhausted -> FAIL (no false success)
const g4 = new QuotaGuard(s, { maxTotalAttempts: 2 });
const m4 = g4.open('mission-4', ['ollama:a', 'ollama:b'], { text: 'w' });
for (let i = 0; i < 2; i++) {
  const b = g4.beforeAttempt('mission-4');
  g4.afterFailure('mission-4', b.model, { status: 500 });
}
const b4 = g4.beforeAttempt('mission-4');
ok('attempts exhausted -> FAIL (no false success)', b4.action === FAIL);

// 14. Success marks mission succeeded
const g5 = new QuotaGuard(s, { maxTotalAttempts: 4 });
const m5 = g5.open('mission-5', ['ollama:good'], { text: 'done' });
g5.afterSuccess('mission-5', 'ollama:good');
ok('success -> mission succeeded', s.state.missions['mission-5'].status === 'succeeded');

// 15. Durable persistence: reload state
const s2 = new QuotaStore(TMP);
ok('persistent: mission kept', s2.state.missions['mission-1'] !== undefined);
ok('persistent: model failures kept', s2.state.models['ollama:qwen'].consecutiveFailures === 3);

fs.unlinkSync(TMP);
console.log(failures === 0 ? 'ALL TESTS PASSED' : failures + ' TESTS FAILED');
process.exit(failures === 0 ? 0 : 1);
