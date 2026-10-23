'use strict';
// Store durable d'etat de quota (JSON, ecriture atomique). Aucune dependance.
const fs = require('fs');
const path = require('path');
const DEFAULTS = { baseBackoffMs: 2000, maxBackoffMs: 3600000, maxAttemptsPerModel: 3, maxTotalAttempts: 12, defaultDailyResetMs: 86400000 };
const now = () => Date.now();
function atomicWrite(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2));
  fs.renameSync(tmp, file);
}
class QuotaStore {
  constructor(file, opts = {}) {
    this.file = file;
    this.opts = { ...DEFAULTS, ...opts };
    this.state = { models: {}, pending: [], missions: {} };
    try { if (fs.existsSync(file)) { const raw = JSON.parse(fs.readFileSync(file, 'utf8')); this.state = { ...this.state, ...raw }; } } catch (_) {}
  }
  save() { atomicWrite(this.file, this.state); }
  model(name) {
    if (!this.state.models[name]) this.state.models[name] = { cooldownUntil: 0, consecutiveFailures: 0, lastError: null, lastOkAt: 0 };
    return this.state.models[name];
  }
  canUse(name) { return this.model(name).cooldownUntil <= now(); }
  cooldownRemaining(name) { return Math.max(0, this.model(name).cooldownUntil - now()); }
  nextAvailableAt(names) {
    const live = names.filter((n) => this.canUse(n));
    if (live.length) return { model: live[0], waitMs: 0 };
    let best = null;
    for (const n of names) { const w = this.cooldownRemaining(n); if (best === null || w < best.waitMs) best = { model: n, waitMs: w }; }
    return best || { model: null, waitMs: 0 };
  }
  backoffMs(category, retryAfterMs, attempts) {
    if (category === 'daily_quota_exhausted') return this.opts.defaultDailyResetMs;
    if (category === 'rate_limit') return retryAfterMs != null ? Math.min(retryAfterMs, this.opts.maxBackoffMs) : Math.min(this.opts.maxBackoffMs, this.opts.baseBackoffMs * 2 ** attempts);
    return Math.min(this.opts.maxBackoffMs, this.opts.baseBackoffMs * 2 ** attempts);
  }
  recordFailure(name, category, retryAfterMs) {
    const m = this.model(name);
    const attempts = m.consecutiveFailures;
    m.consecutiveFailures += 1;
    m.lastError = { category, at: now() };
    const ms = this.backoffMs(category, retryAfterMs, attempts);
    m.cooldownUntil = now() + ms;
    this.save();
    return { cooldownMs: ms, attempts: m.consecutiveFailures };
  }
  recordSuccess(name) { const m = this.model(name); m.consecutiveFailures = 0; m.lastOkAt = now(); m.cooldownUntil = 0; this.save(); }
  addPending(task) { this.state.pending.push({ task, parkedAt: now() }); this.save(); }
  pendingCount() { return this.state.pending.length; }
  mission(id) {
    if (!this.state.missions[id]) this.state.missions[id] = { attempts: 0, triedModels: [], status: 'pending', artifacts: null };
    return this.state.missions[id];
  }
}
module.exports = { QuotaStore, DEFAULTS };
