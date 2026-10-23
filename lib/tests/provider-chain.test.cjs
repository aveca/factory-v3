'use strict';
// Test: le quota guard est bien branche sur le parcours d'appel fournisseur.
// Aucun appel reseau : executeFn est injecte (fournisseur simule).
const os = require('os');
const path = require('path');
const fs = require('fs');
const { ProviderChain } = require('../provider-chain.cjs');

let failures = 0;
function ok(l, c) { if (c) console.log('PASS ' + l); else { failures++; console.log('FAIL ' + l); } }

const STATEBASE = path.join(os.tmpdir(), `pc-${process.pid}-${Date.now()}`);
let stateSeq = 0;
// Fichier d'etat UNIQUE par scenario : aucune fuite d'etat entre tests.
function stateFor() { return `${STATEBASE}-${stateSeq++}.json`; }
function chain(opts) {
  return new ProviderChain({
    stateFile: stateFor(),
    nvidiaKey: 'test-key-not-a-secret',
    ollamaModels: ['qwen2.5-coder:7b'],
    maxAttemptsPerModel: 2,
    maxTotalAttempts: 4,
    minWaitMs: 1,
    ...opts,
  });
}
function flaky(failFor, seen) {
  let n = 0;
  return async (m) => {
    seen.push(m);
    n += 1;
    if (n <= failFor) { const e = new Error('429 rate limited'); e.status = 429; throw e; }
    return 'OUTPUT_FOR_' + m;
  };
}
function alwaysFail(seen, status) {
  return async (m) => { seen.push(m); const e = new Error('fail ' + status); e.status = status; throw e; };
}

(async () => {
  // 1. Sans cle NVIDIA : la chaine ne contient que Ollama.
  const c0 = new ProviderChain({ stateFile: stateFor(), nvidiaKey: '', ollamaModels: ['qwen2.5-coder:7b'] });
  ok('sans cle NVIDIA -> chaine Ollama seule', JSON.stringify(c0.chain()) === JSON.stringify(['ollama/qwen2.5-coder:7b']));
  ok('nvidiaUsable faux sans cle', c0.nvidiaUsable() === false);

  // 2. Avec cle NVIDIA : NVIDIA est en tete (fournisseur principal).
  const c1 = chain();
  ok('avec cle NVIDIA -> nvidia en tete', c1.chain()[0].startsWith('nvidia/'));
  ok('ollama present en secours', c1.chain().some(x => x.startsWith('ollama/')));

  // 3. Succes immediat.
  {
    const c = chain();
    const seen = [];
    const r = await c.execute('m-ok', { t: 1 }, async (m) => { seen.push(m); return 'OUT'; });
    ok('succes immediat', r.ok === true && r.output === 'OUT');
    ok('modele NVIDIA utilise en principal', seen[0].startsWith('nvidia/'));
    ok('aucune bascule inutile', seen.length === 1);
  }

  // 4. Echec 429 sur NVIDIA -> bascule sur le modele suivant (jamais succes fictif).
  {
    const c = chain({ maxAttemptsPerModel: 1 });
    const seen = [];
    const r = await c.execute('m-fallback', { t: 2 }, alwaysFail(seen, 429));
    ok('echec total => ok false', r.ok === false);
    ok('plusieurs modeles tentes (bascule)', seen.length >= 2);
    ok('aucun succès fictif', r.output === undefined);
  }

  // 5. Erreur transitoire puis succes sur le meme modele (retry borne).
  {
    const c = chain({ maxAttemptsPerModel: 3, maxTotalAttempts: 6, minWaitMs: 1, baseBackoffMs: 1 });
    const seen = [];
    const r = await c.execute('m-retry', { t: 3 }, flaky(2, seen));
    ok('reprise apres erreur transitoire', r.ok === true);
    ok('bascule/retry borne et sans succes fictif', r.attempts >= 1 && r.output !== undefined);
    ok('plusieurs modeles tentes (chaine reelle)', seen.length >= 2);
  }

  // 6. 403 autorisation => echec immediat, pas de retry sur les autres modeles.
  {
    const c = chain({ maxAttemptsPerModel: 1 });
    const seen = [];
    const r = await c.execute('m-auth', { t: 4 }, alwaysFail(seen, 403));
    ok('403 => ok false', r.ok === false);
    ok('403 => classification auth_denied', r.classification && r.classification.category === 'auth_denied');
    ok('403 => aucun retry (1 seul essai)', seen.length === 1);
  }

  // 7. Aucun fournisseur utilisable (pas de cle, pas d'ollama) -> parked.
  {
    const c = new ProviderChain({ stateFile: stateFor(), nvidiaKey: '', ollamaModels: [], maxTotalAttempts: 4, minWaitMs: 1 });
    const seen = [];
    const r = await c.execute('m-none', { t: 5 }, alwaysFail(seen, 500));
    ok('aucun fournisseur => ok false', r.ok === false);
    ok('aucun appel fournisseur effectue', seen.length === 0);
    ok('raison explicite (aucun fournisseur)', /aucun fournisseur|parked/.test(r.reason));
  }

  // 8. Persistance : l'etat des modeles survit a un nouveau ProviderChain.
  {
    const f = stateFor();
    const c = new ProviderChain({ stateFile: f, nvidiaKey: 'x', ollamaModels: ['qwen2.5-coder:7b'], maxAttemptsPerModel: 1 });
    const seen = [];
    await c.execute('m-persist', { t: 6 }, alwaysFail(seen, 429));
    const reloaded = new (require('../quota-store.cjs').QuotaStore)(f, { maxAttemptsPerModel: 1 });
    const anyFailed = Object.values(reloaded.state.models).some(m => m.attempts > 0);
    ok('etat fournisseur persiste sur disque', anyFailed === true);
  }

  for (let i = 0; i < stateSeq; i++) { try { fs.unlinkSync(`${STATEBASE}-${i}.json`); } catch (_) {} }
  console.log(failures === 0 ? 'ALL PROVIDER CHAIN TESTS PASSED' : failures + ' PROVIDER_CHAIN_FAILURES');
  process.exit(failures === 0 ? 0 : 1);
})();
