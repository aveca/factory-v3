'use strict';
// provider-chain.cjs — chaine de fournisseurs reelle pour Factory V3.
// Ordre : NVIDIA direct en principal si une cle existe reellement, puis
// Ollama local en secours. OmniRoute reste facultatif (jamais obligatoire).
// La politique de retry (backoff, plafonds, bascule, park) est portee par
// lib/quota-guard.cjs : cette couche execute ce que le guard autorise.
const { QuotaGuard } = require('./quota-guard.cjs');
const { QuotaStore } = require('./quota-store.cjs');

const NVIDIA_ENDPOINT = 'https://integrate.api.nvidia.com/v1/chat/completions';

// Modeles NVIDIA NIM reellement confirmes (GET /v1/models -> 200, 84 modeles).
const NVIDIA_MODELS = [
  'ibm/granite-34b-code-instruct',
  'mistralai/codestral-22b-instruct-v0.1',
  'bigcode/starcoder2-15b',
  'deepseek-ai/deepseek-coder-6.7b-instruct',
];

class ProviderChain {
  constructor(opts = {}) {
    this.opts = opts;
    this.store = opts.store || new QuotaStore(opts.stateFile || 'C:/factory/quota-state.json');
    this.guard = new QuotaGuard(this.store, opts);
    // Une cle vide PASSEE explicitement desactive NVIDIA (pas de repli implicite
    // vers l'environement) : sans quoi on ne peut pas tester le mode local seul.
    this.nvidiaKey = Object.prototype.hasOwnProperty.call(opts, 'nvidiaKey')
      ? opts.nvidiaKey
      : (process.env.NVIDIA_API_KEY || '');
    this.ollamaModels = opts.ollamaModels || ['qwen2.5-coder:7b'];
    this.log = opts.log || (() => {});
    this._prompt = null;
  }
  // NVIDIA utilisable UNIQUEMENT si une cle est presente (jamais inventee).
  nvidiaUsable() { return Boolean(this.nvidiaKey); }
  chain() {
    const c = [];
    if (this.nvidiaUsable()) for (const m of NVIDIA_MODELS) c.push('nvidia/' + m);
    for (const m of this.ollamaModels) c.push('ollama/' + m);
    return c;
  }

  // executeFn(model, prompt) est injecte : il est le SEUL endroit qui parle
  // au fournisseur. Il doit rejeter avec un objet portant status/headers.
  async execute(missionId, task, executeFn) {
    this.guard.open(missionId, this.chain(), task);
    const history = [];
    while (true) {
      const d = this.guard.decide(missionId);
      if (d.action === 'execute') {
        history.push({ model: d.model, attempt: d.attempt });
        this.log('execute', { mission: missionId, model: d.model, attempt: d.attempt });
        try {
          const out = await executeFn(d.model, task);
          this.guard.recordSuccess(missionId, d.model);
          return { ok: true, model: d.model, attempts: d.attempt, output: out, history };
        } catch (err) {
          const r = this.guard.recordFailure(missionId, d.model, err);
          history.push({ model: d.model, failed: true, category: r.classification && r.classification.category, waitMs: r.waitMs });
          if (r.action === 'fail_permanent') {
            return { ok: false, reason: 'provider failure', classification: r.classification, attempts: d.attempt, history };
          }
          continue;
        }
      }
      if (d.action === 'fail_permanent') {
        this.guard.fail(missionId, d.reason);
        return { ok: false, reason: d.reason, attempts: d.attempt || 0, history };
      }
      // park_pending : aucun fournisseur utilisable -> mission mise en attente,
      // recuperable plus tard. Aucun succes fictif n est possible ici.
      this.guard.park({ missionId, task, history });
      this.guard.fail(missionId, 'no usable provider - parked');
      return { ok: false, reason: 'parked', waitMs: d.waitMs, history };
    }
  }
}

module.exports = { ProviderChain, NVIDIA_MODELS, NVIDIA_ENDPOINT };