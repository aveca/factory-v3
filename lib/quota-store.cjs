'use strict';
// Store durable d'etat de quota. Correctifs P5.7 (issue #7).
const fs = require('fs');
const path = require('path');
const DEFAULTS = {
  baseBackoffMs: 2000, maxBackoffMs: 3600000, maxAttemptsPerModel: 3,
  maxTotalAttempts: 12, defaultDailyResetMs: 86400000, minWaitMs: 1000, jitterRatio: 0.2,
};
const now = () => Date.now();
function atomicWrite(file, data) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.${process.pid}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(data, null, 2));
  fs.renameSync(tmp, file);
}
class QuotaStore {
  constructor(file, opts = {}) {
    this.opts = { ...DEFAULTS, ...opts };
    this.memoryOnly = !file || file === ':memory:';
    this.file = this.memoryOnly ? null : file;
    this.state = { models: {}, pending: [], missions: {} };
    if (!this.memoryOnly) {
      try {
        if (fs.existsSync(this.file)) {
          this.state = { ...this.state, ...JSON.parse(fs.readFileSync(this.file, 'utf8')) };
        }
      } catch (_) { /* corrompu: etat propre */ }
    }
  }
  save() { if (!this.memoryOnly) atomicWrite(this.file, this.state); }
  model(name) {
    if (!this.state.models[name])
      this.state.models[name] = { cooldownUntil: 0, failures: 0, attempts: 0, lastError: null, lastOkAt: 0 };
    return this.state.models[name];
  }
  canUse(name) {
    const m = this.model(name);
    return m.cooldownUntil <= now() && m.attempts < this.opts.maxAttemptsPerModel;
  }
  modelAttempts(name) { return this.model(name).attempts; }
  attemptsLeft(name) { return Math.max(0, this.opts.maxAttemptsPerModel - this.model(name).attempts); }
  attemptsExhausted(name) { return this.model(name).attempts >= this.opts.maxAttemptsPerModel; }
  cooldownRemaining(name) { return Math.max(0, this.model(name).cooldownUntil - now()); }
  // Attente effective jamais nulle : plancher minWaitMs + jitter borne.
  effectiveWait(baseMs) {
    const jitter = Math.floor(baseMs * this.opts.jitterRatio * Math.random());
    return Math.max(this.opts.minWaitMs, baseMs + jitter);
  }
  backoffFor(category, retryAfterMs, attempt) {
    const exp = Math.min(this.opts.maxBackoffMs, this.opts.baseBackoffMs * 2 ** attempt);
    if (category === 'daily_quota_exhausted') return this.effectiveWait(this.opts.defaultDailyResetMs);
    if (category === 'rate_limit' && retryAfterMs != null) return this.effectiveWait(Math.min(retryAfterMs, this.opts.maxBackoffMs));
    return this.effectiveWait(exp);
  }
  recordFailure(name, category, retryAfterMs) {
    const m = this.model(name);
    const ms = this.backoffFor(category, retryAfterMs, m.attempts);
    m.attempts += 1; m.failures += 1;
    m.lastError = { category, at: now() };
    m.cooldownUntil = now() + ms;
    this.save();
    return { waitMs: ms, attempts: m.attempts };
  }
  recordSuccess(name) {
    const m = this.model(name);
    m.attempts = 0; m.failures = 0; m.cooldownUntil = 0; m.lastOkAt = now();
    this.save();
  }
  nextUsable(names) {
    const usable = names.filter((n) => this.canUse(n));
    if (usable.length) return { model: usable[0], waitMs: 0 };
    if (!names.length) return { model: null, waitMs: this.opts.minWaitMs };
    // Un modele dont le plafond de tentatives est atteint n'est JAMAIS une
    // reprise automatique : on ne le propose pas comme "prochain disponible".
    const revivable = names.filter((n) => !this.attemptsExhausted(n));
    if (!revivable.length) return { model: null, waitMs: this.opts.maxBackoffMs };
    let best = null;
    for (const n of revivable) {
      const w = this.cooldownRemaining(n);
      if (best === null || w < best.waitMs) best = { model: n, waitMs: w };
    }
    return best || { model: null, waitMs: this.opts.minWaitMs };
  }
  addPending(task) { this.state.pending.push({ task, parkedAt: now() }); this.save(); }
  pendingCount() { return this.state.pending.length; }
  mission(id) {
    if (!this.state.missions[id])
      this.state.missions[id] = { attempts: 0, tried: [], status: 'pending', artifacts: null };
    return this.state.missions[id];
  }
}
module.exports = { QuotaStore, DEFAULTS };