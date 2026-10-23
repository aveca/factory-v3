'use strict';
// Tests de non-regression des correctifs P5.7 (issue #7).
// Executes par la CI : node lib/tests/regression-p5.7.test.cjs
const fs = require('fs');
const os = require('os');
const path = require('path');
const { QuotaStore } = require('../quota-store.cjs');
const { QuotaGuard, EXECUTE, WAIT, PARK, FAIL } = require('../quota-guard.cjs');
const { classifyProviderError } = require('../provider-errors.cjs');

let failures = 0;
function ok(label, cond) {
  if (cond) console.log('PASS ' + label);
  else { failures++; console.log('FAIL ' + label); }
}
const TMPBASE = path.join(os.tmpdir(), `qg-${process.pid}-${Date.now()}`);
let seq = 0;
// Fichier unique par bloc : aucune fuite d'etat entre scenarios.
function fresh(opts) {
  const f = `${TMPBASE}-${seq++}.json`;
  return new QuotaStore(f, opts || { maxAttemptsPerModel: 2, maxTotalAttempts: 5, minWaitMs: 1000 });
}

// --- FIX (c) : distinction quota / autorisation ---------------------------
ok('429 simple -> rate_limit', classifyProviderError({ status: 429, body: 'slow down' }).category === 'rate_limit');
ok('429 + indice journalier -> daily_quota_exhausted',
  classifyProviderError({ status: 429, body: 'daily quota exhausted' }).category === 'daily_quota_exhausted');
ok('401 -> auth_denied (PAS quota)', classifyProviderError({ status: 401, body: 'no key' }).category === 'auth_denied');
ok('403 -> auth_denied (PAS quota)', classifyProviderError({ status: 403, body: 'forbidden' }).category === 'auth_denied');
ok('403 texte "insufficient credits" -> daily_quota_exhausted',
  classifyProviderError({ status: 403, body: 'insufficient credits' }).category === 'daily_quota_exhausted');
ok('402 -> daily_quota_exhausted', classifyProviderError({ status: 402, body: 'payment required' }).category === 'daily_quota_exhausted');
ok('500 -> transient', classifyProviderError({ status: 500, body: 'boom' }).category === 'transient');
ok('400 -> permanent', classifyProviderError({ status: 400, body: 'bad request' }).category === 'permanent');
ok('ECONNREFUSED -> transient', classifyProviderError({ message: 'connect ECONNREFUSED 127.0.0.1' }).category === 'transient');
ok('retry-after 30s -> 30000ms', classifyProviderError({ status: 429, body: 'x', headers: { 'retry-after': '30' } }).retryAfterMs === 30000);

// --- FIX (a) : ':memory:' ne cree AUCUN fichier ---------------------------
const before = fs.existsSync(':memory:');
new QuotaStore(':memory:').save();
ok("':memory:' ne cree pas de fichier nomme ':memory:'", fs.existsSync(':memory:') === before);
ok("':memory:' signale memoryOnly=true", new QuotaStore(':memory:').memoryOnly === true);
ok('chemin vide -> memoryOnly', new QuotaStore('').memoryOnly === true);
new (require('../quota-store.cjs').QuotaStore)(null);
ok('null -> memoryOnly', new QuotaStore(null).memoryOnly === true);

// --- FIX (c) : attente effective jamais nulle -----------------------------
{
  const st = new QuotaStore(':memory:', { minWaitMs: 1000, jitterRatio: 0.2, baseBackoffMs: 2000 });
  for (let i = 0; i < 30; i++) {
    const w = st.effectiveWait(0);
    if (w <= 0) { ok('effectiveWait jamais <= 0', false); break; }
    if (i === 29) ok('effectiveWait jamais <= 0 (30 tirages)', true);
  }
  ok('effectiveWait plancher respecte', st.effectiveWait(100) >= 1000);
}

// --- FIX (b) : plafond maxAttemptsPerModel reellement applique -------------
{
  const st = fresh({ maxAttemptsPerModel: 2, maxTotalAttempts: 10, minWaitMs: 1000, baseBackoffMs: 0 });
  const g = new QuotaGuard(st);
  g.open('m1', ['ollama:a'], { t: 1 });
  let d = g.decide('m1');
  ok('1re tentative EXECUTE ollama:a', d.action === EXECUTE && d.model === 'ollama:a');
  g.recordFailure('m1', 'ollama:a', { status: 500 });
  ok('apres 1 echec: modele en cooldown (backoff respecte)', st.cooldownRemaining('ollama:a') > 0);
  d = g.decide('m1');
  ok('pendant le cooldown: PAS d EXECUTE (respect du backoff)', d.action !== EXECUTE);
  // Expiration manuelle du cooldown : le modele reste reessayable (2e tentative).
  st.model('ollama:a').cooldownUntil = 0;
  d = g.decide('m1');
  ok('2e tentative EXECUTE apres expiration cooldown', d.action === EXECUTE && d.model === 'ollama:a');
  g.recordFailure('m1', 'ollama:a', { status: 500 });
  ok('compteur tentatives modele = 2', st.modelAttempts('ollama:a') === 2);
  ok('plafond par modele atteint', st.attemptsLeft('ollama:a') === 0);
  st.model('ollama:a').cooldownUntil = 0;
  ok('canUse faux apres plafond modele (meme sans cooldown)', st.canUse('ollama:a') === false);
  d = g.decide('m1');
  ok('plus de EXECUTE sur modele epuise (PAS de boucle)', d.action === PARK);
  ok('PARK porte waitMs > 0 (pas de delai nul)', d.waitMs > 0);
}

// --- Pas de WAIT a delai nul permanent, meme apres expiration cooldown ----
{
  const st = fresh({ maxAttemptsPerModel: 3, maxTotalAttempts: 10, minWaitMs: 500 });
  const g = new QuotaGuard(st);
  g.open('m2', ['ollama:a', 'ollama:b'], { t: 2 });
  g.decide('m2'); g.recordFailure('m2', 'ollama:a', { status: 500 });
  g.decide('m2'); g.recordFailure('m2', 'ollama:b', { status: 500 });
  g.decide('m2'); g.recordFailure('m2', 'ollama:a', { status: 500 });
  // Tous les modeles epuises en tentatives -> pas de WAIT 0
  const d = g.decide('m2');
  ok('chaine epuise -> PARK (jamais WAIT 0)', d.action === PARK);
  ok('PARK waitMs >= minWaitMs', d.waitMs >= st.opts.minWaitMs);
}

// --- Bascule automatique vers un modele de secours -------------------------
{
  const st = fresh({ maxAttemptsPerModel: 3, maxTotalAttempts: 10, minWaitMs: 1000 });
  const g = new QuotaGuard(st);
  g.open('m3', ['ollama:good', 'ollama:backup'], { t: 3 });
  const d1 = g.decide('m3');
  g.recordFailure('m3', 'ollama:good', { status: 429, body: 'daily quota exhausted', headers: { 'retry-after': '7200' } });
  const d2 = g.decide('m3');
  ok('bascule sur le modele de secours', d2.action === EXECUTE && d2.model === 'ollama:backup');
  ok('modele primaire en cooldown long', st.cooldownRemaining('ollama:good') > 600000);
}

// --- auth_denied => echec immediat, aucun retry -----------------------------
{
  const st = fresh({ maxAttemptsPerModel: 3, maxTotalAttempts: 10, minWaitMs: 1000 });
  const g = new QuotaGuard(st);
  g.open('m4', ['ollama:a'], { t: 4 });
  g.decide('m4');
  const r = g.recordFailure('m4', 'ollama:a', { status: 403, body: 'forbidden' });
  ok('403 -> FAIL immediat (auth non retentee)', r.action === FAIL);
  ok('classification auth_denied remontee', r.classification && r.classification.category === 'auth_denied');
}

// --- Plafond global => FAIL, jamais succes fictif ---------------------------
{
  const st = fresh({ maxAttemptsPerModel: 1, maxTotalAttempts: 3, minWaitMs: 1000 });
  const g = new QuotaGuard(st);
  g.open('m5', ['ollama:a', 'ollama:b', 'ollama:c'], { t: 5 });
  for (let i = 0; i < 3; i++) { const d = g.decide('m5'); g.recordFailure('m5', d.model, { status: 500 }); }
  const d = g.decide('m5');
  ok('plafond global -> FAIL', d.action === FAIL);
  ok('mission non marquee succes', st.state.missions.m5.status !== 'succeeded');
}

// --- Persistance et reprise apres redemarrage -------------------------------
{
  const st = fresh({ maxAttemptsPerModel: 2, maxTotalAttempts: 5, minWaitMs: 1000 });
  const g = new QuotaGuard(st);
  g.open('m6', ['ollama:a'], { t: 6 });
  g.decide('m6');
  g.recordFailure('m6', 'ollama:a', { status: 429, body: 'quota', headers: { 'retry-after': '7200' } });
  g.park({ id: 'm6', note: 'quota epuise' });
  const before2 = JSON.parse(fs.readFileSync(st.file, 'utf8')).missions.m6;
  // Simulation redemarrage : nouveau store sur le meme fichier
  const st2 = new QuotaStore(st.file, { maxAttemptsPerModel: 2, maxTotalAttempts: 5, minWaitMs: 1000 });
  const g2 = new QuotaGuard(st2);
  ok('etat mission persiste apres redemarrage', JSON.stringify(st2.state.missions.m6) === JSON.stringify(before2));
  ok('tentatives persistees', st2.state.missions.m6.tried.length === 1);
  ok('tache parkee recuperable', g2.pending().length === 1 && g2.pending()[0].id === 'm6');
  const d = g2.decide('m6');
  ok('apres reprise: pas de succes fictif (PARK/WAIT)', d.action === PARK || d.action === WAIT);
}

// --- Succes reel remet le compteur a zero -----------------------------------
{
  const st = fresh({ maxAttemptsPerModel: 2, maxTotalAttempts: 5, minWaitMs: 1000 });
  const g = new QuotaGuard(st);
  g.open('m7', ['ollama:a'], { t: 7 });
  g.decide('m7'); g.recordFailure('m7', 'ollama:a', { status: 500 });
  g.decide('m7'); g.recordSuccess('m7', 'ollama:a');
  ok('succes reel => compteur remis a zero', st.modelAttempts('ollama:a') === 0);
  ok('succes reel => statut succeeded', st.state.missions.m7.status === 'succeeded');
  ok('modele redevient utilisable', st.canUse('ollama:a') === true);
}

// Nettoyage des fichiers temporaires de tous les scenarios.
for (let i = 0; i < seq; i++) { try { fs.unlinkSync(`${TMPBASE}-${i}.json`); } catch (_) {} }
console.log(failures === 0 ? 'ALL REGRESSION TESTS PASSED' : failures + ' REGRESSION_FAILURES');
process.exit(failures === 0 ? 0 : 1);
