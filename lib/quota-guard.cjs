'use strict';
// QuotaGuard: politique d'execution resiliente autour d'une chaine de modeles.
// Correctifs P5.7 (issue #7): plafond maxAttemptsPerModel reellement applique,
// aucun WAIT a delai nul permanant, auth (401/403) distingue du quota (429/402),
// jamais de succes fictif apres echec fournisseur, artefacts preserves.
const { classifyProviderError } = require('./provider-errors.cjs');
const { QuotaStore } = require('./quota-store.cjs');
const EXECUTE = 'execute', WAIT = 'wait_retry', PARK = 'park_pending', FAIL = 'fail_permanent';

class QuotaGuard {
  constructor(store, opts = {}) {
    this.store = store || new QuotaStore(':memory:');
    // Source unique de verite : les plafonds vivent dans le store. Une valeur
    // explicite passee au guard reste prioritaire (tests, surcharge ponctuelle).
    this.maxTotalAttempts = opts.maxTotalAttempts || this.store.opts.maxTotalAttempts || 12;
  }
  open(missionId, chain, task) {
    const m = this.store.mission(missionId);
    if (m.status !== 'running') {
      m.chain = chain; m.task = task || null; m.status = 'running';
      this.store.save();
    }
    return m;
  }
  // Choisit la prochaine action. Ne renvoie JAMAIS waitMs:0 en boucle :
  // si aucun modele n'est utilisable -> PARK (recuperable) ou FAIL (plafonds atteints).
  decide(missionId) {
    const m = this.store.mission(missionId);
    if (m.attempts >= this.maxTotalAttempts)
      return { action: FAIL, reason: `plafond global ${this.maxTotalAttempts} atteint`, artifacts: m.artifacts };
    const chain = m.chain || [];
    if (!chain.length)
      return { action: FAIL, reason: 'aucun fournisseur configure (chaine vide)', artifacts: m.artifacts };
    // Candidats = modeles reellement utilisables (cooldown expire ET plafond
    // de tentatives par modele non atteint). Un modele deja tente PEUT etre
    // reessaye apres expiration de son cooldown : 'tried' ne l'exclut pas.
    const candidates = chain.filter((x) => this.store.canUse(x));
    if (candidates.length) {
      const fresh = candidates.filter((x) => !m.tried.includes(x));
      const model = fresh.length ? fresh[0] : candidates[0];
      if (!m.tried.includes(model)) m.tried.push(model);
      m.attempts += 1;
      this.store.save();
      return { action: EXECUTE, model, attempt: m.attempts, artifacts: m.artifacts };
    }
    // Tous les modeles sont epuises (tentatives par modele) ou en cooldown :
    // on ne renvoie pas un WAIT a delai nul, on PARK pour reprise ulterieure.
    const nxt = this.store.nextUsable(chain);
    if (nxt.model && nxt.waitMs === 0)
      return { action: WAIT, waitMs: this.store.opts.minWaitMs, reason: 'cooldown expire, attente minimale' };
    return { action: PARK, reason: 'aucun modele utilisisable (tentatives/quota)', waitMs: nxt.waitMs, artifacts: m.artifacts };
  }
  // Enregistre un echec fournisseur. auth_denied/permanent => echec immediat.
  recordFailure(missionId, model, err) {
    const c = classifyProviderError(err);
    const res = this.store.recordFailure(model, c.category, c.retryAfterMs);
    const m = this.store.mission(missionId);
    if (!m.tried.includes(model)) m.tried.push(model);
    this.store.save();
    if (c.category === 'auth_denied' || c.category === 'permanent')
      return { action: FAIL, classification: c, waitMs: 0, artifacts: m.artifacts };
    return { action: WAIT, classification: c, waitMs: res.waitMs, artifacts: m.artifacts };
  }
  recordSuccess(missionId, model) {
    this.store.recordSuccess(model);
    const m = this.store.mission(missionId);
    m.status = 'succeeded';
    this.store.save();
  }
  // Marque explicitement un echec (aucun succes fictif possible apres ce point).
  fail(missionId, reason) {
    const m = this.store.mission(missionId);
    m.status = 'failed';
    m.failureReason = reason || 'provider failure';
    this.store.save();
  }
  park(task) { this.store.addPending(task); return { action: PARK, parked: true, count: this.store.pendingCount() }; }
  pending() { return this.store.state.pending.map((p) => p.task); }
}
module.exports = { QuotaGuard, EXECUTE, WAIT, PARK, FAIL };