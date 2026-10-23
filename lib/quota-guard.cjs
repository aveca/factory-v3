'use strict';
const { classifyProviderError } = require('./provider-errors.cjs');
const { QuotaStore } = require('./quota-store.cjs');
const EXECUTE = 'execute', WAIT = 'wait_retry', PARK = 'park_pending', FAIL = 'fail_permanent';
class QuotaGuard {
  constructor(store, opts = {}) {
    this.store = store || new QuotaStore(':memory:');
    this.total = opts.maxTotalAttempts || 12;
  }
  open(id, chain, task) {
    const m = this.store.mission(id);
    if (m.status !== 'running') { m.chain = chain; m.task = task || null; m.status = 'running'; this.store.save(); }
    return m;
  }
  beforeAttempt(missionId) {
    const m = this.store.mission(missionId);
    if (m.attempts >= this.total) return { action: FAIL, reason: 'maxTotalAttempts sans succes provider', artifacts: m.artifacts };
    const chain = m.chain || [];
    const fresh = chain.filter((x) => this.store.canUse(x) && !m.triedModels.includes(x));
    if (fresh.length) {
      const model = fresh[0];
      m.triedModels.push(model); m.attempts += 1; this.store.save();
      return { action: EXECUTE, model, attempt: m.attempts, artifacts: m.artifacts };
    }
    const next = this.store.nextAvailableAt(chain);
    if (next.model && next.waitMs === 0)
      return { action: WAIT, waitMs: 0, reason: 'modele disponible mais reset d essais' };
    return { action: PARK, reason: 'aucun fournisseur utilisable', waitMs: next.waitMs, artifacts: m.artifacts };
  }
  afterFailure(missionId, model, err, retryAfterMs) {
    const classification = classifyProviderError(err);
    const res = this.store.recordFailure(model, classification.category, retryAfterMs || classification.retryAfterMs);
    const m = this.store.mission(missionId);
    m.triedModels.push(model); this.store.save();
    if (classification.category === 'permanent' || m.attempts >= this.total)
      return { action: FAIL, classification, artifacts: m.artifacts, cooldownMs: res.cooldownMs };
    return { action: WAIT, classification, cooldownMs: res.cooldownMs, artifacts: m.artifacts };
  }
  afterSuccess(missionId, model) { this.store.recordSuccess(model); const m = this.store.mission(missionId); m.status = 'succeeded'; this.store.save(); }
  park(task) { this.store.addPending(task); return { action: PARK, parked: true, count: this.store.pendingCount() }; }
}
module.exports = { QuotaGuard, EXECUTE, WAIT, PARK, FAIL };
