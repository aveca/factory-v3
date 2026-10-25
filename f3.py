#!/usr/bin/env python3
"""Factory V3 — moteur d'orchestration autonome (arbitrage interactif, file durable,
bail d'execution, verrous, acceptation, reprise). Infra only.

Chemins isolables par variables d'environnement (permet les tests d'acceptation
sur une instance separee sans toucher la file reelle) :
  F3_ROOT, F3_STATE, F3_DB, F3_CONTROL, F3_LOG, F3_WORKSPACE, F3_WORKER

Aucun modele payant : les modeles autorises sont limites a une allowlist stricte
(router/* , ollama/* , openrouter-free/*). Le routeur local ne tente jamais de
modele payant. Aucune Mission ne peut declarer un modele hors allowlist.
"""
import os, sys, json, time, uuid, re, sqlite3, argparse, threading, subprocess, ctypes, random
from datetime import datetime, timezone

# ─── Chemins (isolables) ───────────────────────────────────────────
ROOT       = os.environ.get("F3_ROOT", r"C:\factory-service")
STATE      = os.environ.get("F3_STATE", os.path.join(ROOT, "state"))
DB         = os.environ.get("F3_DB", os.path.join(STATE, "f3_missions.db"))
CONTROL    = os.environ.get("F3_CONTROL", os.path.join(STATE, "f3_control.json"))
LOGDIR     = os.environ.get("F3_LOG", os.path.join(STATE, "logs"))
WORKSPACE  = os.environ.get("F3_WORKSPACE", os.path.join(r"C:\test-factory-isolated", "worktrees"))
WORKER     = os.environ.get("F3_WORKER", "worker_" + str(os.getpid()))
LOG        = os.path.join(LOGDIR, "f3.log")
SUP_LOCK   = os.path.join(STATE, "f3_supervisor.lock")

for d in (STATE, LOGDIR, WORKSPACE):
    os.makedirs(d, exist_ok=True)

# ─── Politique stricte gratuite ────────────────────────────────────
FREE_PREFIXES = ("router/", "ollama/", "openrouter-free/")
def model_allowed(model):
    if not model:
        return True  # handler logique pur (pas d'appel modele)
    return model.startswith(FREE_PREFIXES)

VALID_STATES = ("queued", "running", "checkpointed", "blocked", "failed", "completed")
MODES = ("INTERACTIVE", "AUTONOMOUS", "PAUSED", "RECOVERING", "ERROR")
KINDS = ("audit", "maintenance", "dev", "tests", "seo", "delivery")

# ─── Journalisation avec rotation (simple, sans fenetre) ───────────
_loglock = threading.Lock()
def log(msg, echo=None):
    line = datetime.now(timezone.utc).isoformat(timespec="milliseconds") + " | " + str(msg)
    with _loglock:
        try:
            if os.path.getsize(LOG) > 2_000_000 if os.path.exists(LOG) else False:
                try: os.replace(LOG, LOG + ".1")
                except OSError: pass
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
    if echo is None:
        echo = os.environ.get("F3_QUIET") != "1"
    if echo:
        try: print(line)
        except Exception: pass  # pas de console (pythonw) -> on ignore

# ─── Temps ─────────────────────────────────────────────────────────
def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
def now_epoch():
    return time.time()

# ─── Contrôle (état explicite / arbitrage) ─────────────────────────
def default_control():
    return {
        "mode": "INTERACTIVE",            # defaut sur: priorité à l'utilisateur
        "interactive_lock": True,
        "concurrency_limit": 1,           # 1 seule execution à la fois
        "one_heavy_local": True,          # 1 génération locale lourde max
        "max_mission_seconds": 300,
        "max_retries": 3,
        "lease_seconds": 90,
        "poll_seconds": 5,
        "updated_by": "init", "updated_at": now_iso(), "reason": "default: interactive",
        "supervisor_pid": None, "supervisor_heartbeat_at": None,
    }
def load_control():
    try:
        with open(CONTROL, encoding="utf-8") as f:
            c = json.load(f)
        d = default_control(); d.update(c); return c
    except (OSError, ValueError):
        c = default_control(); save_control(c); return c
def save_control(c):
    tmp = CONTROL + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)
    os.replace(tmp, CONTROL)
    return c
def is_interactive(c):
    return c.get("mode") == "INTERACTIVE" or bool(c.get("interactive_lock"))
def claims_allowed(c):
    """Le superviseur/worker ne reclame de nouvelle mission que si aucune
    session interactive n'est prioritaire et que le mode le permet."""
    if c.get("mode") in ("PAUSED", "ERROR", "RECOVERING", "INTERACTIVE"):
        return False
    if bool(c.get("interactive_lock")):
        return False
    return True

# ─── Détection interactive fiable ──────────────────────────────────
# Signal FIABLE = verrou de priorité explicite (control.interactive_lock) OU
# mode INTERACTIVE. On NE déduit PAS "inactif" d'une fenêtre minimisée ni de la
# seule présence de processus. La présence d'un processus opencode n'est qu'un
# INDICE (logged), jamais un signal d'arret/relance.
def interactive_hint():
    """Indice fort: vérifie si un processus opencode tourne."""
    try:
        import psutil  # optionnel
    except ImportError:
        return False
    for p in psutil.process_iter(["name"]):
        n = (p.info.get("name") or "").lower()
        if n in ("opencode.exe", "opencode-cli.exe"):
            return True
    return False

# ─── Base de missions (SQLite durable) ─────────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS missions(
  id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  repo TEXT, scope TEXT, branch TEXT, worktree TEXT,
  objective TEXT,
  acceptance TEXT,            -- JSON {handler, expect_marker, expect_regex}
  model TEXT,
  ctx_budget INTEGER, max_tokens INTEGER,
  timeout_s INTEGER, max_retries INTEGER, priority INTEGER DEFAULT 0,
  state TEXT NOT NULL DEFAULT 'queued',
  owner TEXT, lease_expires_at REAL, heartbeat_at TEXT,
  attempts INTEGER DEFAULT 0,
  history TEXT DEFAULT '[]',
  evidence TEXT,
  error TEXT,
  interrupt_requested INTEGER DEFAULT 0,
  created_at TEXT, updated_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_m_state ON missions(state, priority DESC, created_at ASC);
"""
def db():
    con = sqlite3.connect(DB, timeout=30, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.row_factory = sqlite3.Row
    return con
def init_db():
    with db() as con:
        con.executescript(SCHEMA)
def hist_append(m, event):
    try:
        h = json.loads(m["history"] or "[]")
    except Exception:
        h = []
    h.append({"t": now_iso(), "e": event})
    return json.dumps(h[-200:])

def enqueue(kind, model="", handler=None, repo=None, scope=None, branch=None, worktree=None,
            objective="", expect_marker=None, expect_regex=None,
            ctx_budget=65536, max_tokens=4096, timeout_s=None, max_retries=None, priority=0):
    if kind not in KINDS:
        raise ValueError(f"kind invalide: {kind}")
    if not model_allowed(model):
        raise PermissionError(f"modele hors allowlist gratuite: {model}")
    if handler not in SAFE_HANDLERS:
        raise PermissionError(f"handler non autorise en autonomie: {handler}")
    c = load_control()
    timeout_s = int(timeout_s or c["max_mission_seconds"])
    max_retries = int(c["max_retries"] if max_retries is None else max_retries)
    mid = "m_" + datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    acc = {"handler": handler, "expect_marker": expect_marker, "expect_regex": expect_regex}
    with db() as con:
        con.execute("""INSERT INTO missions(id,kind,repo,scope,branch,worktree,objective,
            acceptance,model,ctx_budget,max_tokens,timeout_s,max_retries,priority,state,
            created_at,updated_at,history)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'queued', ?,?,?)""",
            (mid, kind, repo, scope, branch, worktree, objective, json.dumps(acc), model,
             ctx_budget, max_tokens, timeout_s, max_retries, priority, now_iso(), now_iso(),
             json.dumps([{"t": now_iso(), "e": "enqueued"}])))
    log(f"ENQUEUE {mid} kind={kind} handler={handler} model={model or '-'} prio={priority}")
    return mid

def get_mission(mid):
    with db() as con:
        con.row_factory = sqlite3.Row
        r = con.execute("SELECT * FROM missions WHERE id=?", (mid,)).fetchone()
        return dict(r) if r else None

def validate_acceptance(m, evidence):
    """Valide les critères d'acceptation d'une mission.
    Retourne (ok, why) où ok est True si tous les critères passent."""
    if not evidence:
        return False, "aucune preuve fournie"
    acc = json.loads(m["acceptance"]) if isinstance(m["acceptance"], str) else m["acceptance"]
    expect_marker = acc.get("expect_marker")
    expect_regex = acc.get("expect_regex")
    
    if expect_marker:
        import os
        if not os.path.exists(expect_marker):
            return False, f"marqueur attendu absent: {expect_marker}"
    if expect_regex:
        import re
        if not re.search(expect_regex, str(evidence)):
            return False, f"regex non matché: {expect_regex}"
    return True, "ok"

def set_state(mid, state, **fields):
    if "evidence" in fields and fields["evidence"] is not None and not isinstance(fields["evidence"], str):
        fields["evidence"] = json.dumps(fields["evidence"], ensure_ascii=False, default=str)
    fields = dict(fields)
    fields["state"] = state
    # Build SET clause dynamically
    set_clause = ", ".join(f"{k}=?" for k in fields.keys())
    values = list(fields.values()) + [mid]
    with db() as con:
        con.execute(f"UPDATE missions SET {set_clause} WHERE id=?", values)
    log(f"STATE {mid} -> {state} {({k:v for k,v in fields.items() if k in ('owner','attempts','error')}) or ''}")

def counts():
    with db() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT state, COUNT(*) n FROM missions GROUP BY state").fetchall()
        return {r["state"]: r["n"] for r in rows}

# ─── Reclamation atomique (empeche la double execution) ────────────
def claim(worker, lease_s):
    """Reclame atomiquement la prochaine mission eligible. Unseule connection
    obtient la ligne (UPDATE...RETURNING sous BEGIN IMMEDIATE) -> deux workers
    ne peuvent pas reclamer la meme mission (test 3)."""
    c = load_control()
    if not claims_allowed(c):
        return None
    running_now = 0
    with db() as con:
        con.row_factory = sqlite3.Row
        running_now = con.execute("SELECT COUNT(*) n FROM missions WHERE state='running'").fetchone()["n"]
    if running_now >= int(c.get("concurrency_limit", 1)):
        return None
    with db() as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE")
        try:
            running_in_txn = con.execute("SELECT COUNT(*) n FROM missions WHERE state='running'").fetchone()["n"]
            if running_in_txn >= int(c.get("concurrency_limit", 1)):
                con.execute("COMMIT"); return None
            row = con.execute(
                """SELECT id,acceptance,kind,model,worktree,attempts,timeout_s,max_retries,objective,history,lease_expires_at
                   FROM missions WHERE state IN ('queued','checkpointed')
                   ORDER BY priority DESC, created_at ASC LIMIT 1""").fetchone()
            if not row:
                con.execute("COMMIT"); return None
            mid = row["id"]
            exp = now_epoch() + float(lease_s)
            # Nouvelle vérification : si la mission a un lease_expires_at futur,
            # ne pas la réclamer avant cette échéance
            if row["lease_expires_at"] and row["lease_expires_at"] > now_epoch():
                con.execute("COMMIT"); return None
            upd = con.execute(
                """UPDATE missions SET state='running', owner=?, lease_expires_at=?,
                   heartbeat_at=?, attempts=attempts+1, interrupt_requested=0,
                   history=?, updated_at=?
                   WHERE id=? RETURNING id,kind,model,worktree,attempts,timeout_s,max_retries,objective,acceptance,history,evidence""",
                (worker, now_epoch() + float(lease_s), now_iso(),
                 json.dumps(json.loads(row["history"] or "[]") + [{"t": now_iso(), "e": "claimed"}]),
                 now_iso(), mid)).fetchone()
            con.execute("COMMIT")
            return dict(upd) if upd else None
        except Exception:
            con.execute("ROLLBACK"); raise

def heartbeat(mid, lease_s, worker):
    with db() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute("UPDATE missions SET lease_expires_at=?, heartbeat_at=? WHERE id=? AND owner=? AND state='running'",
                    (now_epoch() + float(lease_s), now_iso(), mid, worker))
        con.execute("COMMIT")

def reclaim_stale():
    """RECOVERING / reprise apres crash: les baux expires sont repris.
    Si attempts>=max_retries -> failed (borne). Sinon -> queued (reprise)."""
    now = now_epoch()
    with db() as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE")
        rows = con.execute("SELECT id,attempts,max_retries FROM missions WHERE state='running' AND lease_expires_at< ?", (now,)).fetchall()
        for r in rows:
            if r["attempts"] >= r["max_retries"]:
                con.execute("UPDATE missions SET state='failed', owner=NULL, lease_expires_at=NULL, error='lease-expired-max-retries', updated_at=? WHERE id=?", (now_iso(), r["id"]))
                log(f"RECOVER {r['id']} -> failed (bail expire, retries epuises)")
            else:
                con.execute("UPDATE missions SET state='queued', owner=NULL, lease_expires_at=NULL, updated_at=? WHERE id=?", (now_iso(), r["id"]))
                log(f"RECOVER {r['id']} -> queued (bail expire, reprise)")
        con.execute("COMMIT")
    return len(rows)

def requeue_checkpointed():
    """Les missions 'checkpointed' redeviennent reclaimables (reprise apres
    retour interactif)."""
    with db() as con:
        con.row_factory = sqlite3.Row
        con.execute("BEGIN IMMEDIATE")
        n = con.execute("UPDATE missions SET updated_at=? WHERE state='checkpointed'", (now_iso(),)).rowcount
        con.execute("COMMIT")
    return n

# ─── Handlers surs (testables, sans fenetre, sans modele payant) ───
# Reception d'un callback pour checkpoint/arret cooperatif.
def _ws(mid):
    d = os.path.join(WORKSPACE, mid)
    os.makedirs(d, exist_ok=True)
    return d

def h_emit(m, cb):
    d = _ws(m["id"])
    acc = json.loads(m["acceptance"])
    p = os.path.join(d, acc.get("expect_marker") or "MARKER")
    with open(p, "w", encoding="utf-8") as f:
        f.write(f"mission {m['id']} {m['objective']} completed at {now_iso()}\n")
    return {"state_out": "completed", "evidence": {"marker": p}}

def h_fail_first(m, cb):
    # echoue a la 1re tentative, reussit ensuite (test 1 + 7)
    if m["attempts"] <= 1:
        raise RuntimeError("echec volontaire premiere tentative")
    return h_emit(m, cb)

def h_steps(m, cb):
    # travail par etapes, checkpointable, sensible a l'arret interactif (test 2 + 4)
    d = _ws(m["id"])
    acc = json.loads(m["acceptance"])
    cp_path = os.path.join(d, "steps.json")
    steps = ["a", "b", "c", "d", "e"]
    state = {"done": [], "remaining": list(steps)}
    if m.get("evidence"):
        try:
            state = json.loads(m["evidence"])
        except Exception:
            pass
    while state["remaining"]:
        if cb.should_stop():
            return {"state_out": "checkpointed",
                    "checkpoint": state,
                    "evidence": json.dumps(state)}
        step = state["remaining"].pop(0)
        state["done"].append(step)
        cb.log(f"etape {step}")
        time.sleep(float(os.environ.get("F3_STEP_DELAY", "0.4")))
    marker = os.path.join(d, acc.get("expect_marker") or "MARKER")
    with open(marker, "w", encoding="utf-8") as f:
        f.write(json.dumps({"done": state["done"], "at": now_iso()}))
    return {"state_out": "completed", "evidence": json.dumps(state)}

def h_local_model(m, cb):
    # prouve la route locale gratuite (fallback) dans le moteur ; jamais payant
    body = json.dumps({"model": m["model"] or "qwen2.5-coder:7b",
                       "messages": [{"role": "user", "content": "Reply with exactly: PONG"}],
                       "max_tokens": 8, "temperature": 0, "stream": False}).encode()
    import urllib.request
    r = urllib.request.Request("http://127.0.0.1:11434/v1/chat/completions", data=body,
                               headers={"content-type": "application/json"}, method="POST")
    import urllib.error
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        raise RuntimeError(f"local model unavailable: {e}")
    content = (data.get("choices") or [{}])[0].get("message", {}).get("content")
    d = _ws(m["id"])
    acc = json.loads(m["acceptance"])
    marker = os.path.join(d, acc.get("expect_marker") or "MARKER")
    with open(marker, "w", encoding="utf-8") as f:
        f.write(json.dumps({"model": data.get("model"), "content": content,
                            "usage": data.get("usage"), "at": now_iso()}))
    return {"state_out": "completed", "evidence": json.dumps({"model": data.get("model"),
            "cost": "local/free", "content": content})}

def h_boom(m, cb):
    # echoue systematiquement: sert a prouver la borne de reprise (test 7)
    raise RuntimeError("boom: echec volontaire persistant")

def h_orch(m, cb):
    """Mission adaptative P2 (triage->plan->exec->revue->verify->deliver) via orch.py,
    executee sous la file/verrous/bail/arbitrage deja verifies (P1). Infra only."""
    import importlib.util
    acc = json.loads(m["acceptance"]) if isinstance(m["acceptance"], str) else (m["acceptance"] or {})
    task = acc.get("task") or {"objective": m["objective"], "acceptance": acc.get("acceptance", []),
                               "diff_seed": acc.get("diff_seed", "contexte: correction ponctuelle; gestion d'erreur via try/except")}
    task.setdefault("id", m["id"])
    spec = importlib.util.spec_from_file_location("orch_v3", r"C:\factory-service\v3\orch.py")
    orch = importlib.util.module_from_spec(spec); spec.loader.exec_module(orch)
    ws = os.path.join(WORKSPACE, m["id"]); os.makedirs(ws, exist_ok=True)
    res = orch.run_chain(task, ws)
    ev = res["evidence"]
    if res["state"] == "completed":
        marker = os.path.join(ws, acc.get("expect_marker", "ORCH_DONE"))
        try:
            with open(marker, "w", encoding="utf-8") as f:
                f.write(json.dumps({"state": "completed", "triage": ev.get("triage")}, ensure_ascii=False))
        except OSError: pass
        return {"state_out": "completed", "evidence": json.dumps(ev, ensure_ascii=False, default=str)}
    return {"state_out": "blocked", "evidence": json.dumps(ev, ensure_ascii=False, default=str)}

SAFE_HANDLERS = {"emit": h_emit, "steps": h_steps, "fail_first": h_fail_first,
                 "local_model": h_local_model, "boom": h_boom,
                 "orch": h_orch}

# ─── Contexte d'execution (cooperatif) ─────────────────────────────
class Ctx:
    def __init__(self, mid, worker, lease_s):
        self.mid = mid; self.worker = worker; self.lease_s = lease_s
        self._stop = threading.Event(); self._last = 0.0
    def should_stop(self):
        if time.time() - self._last > 3:
            self._last = time.time()
            try: heartbeat(self.mid, self.lease_s, self.worker)
            except Exception: pass
        c = load_control()
        if c.get("mode") in ("PAUSED", "ERROR"):
            return True
        return interactive_hint()
    def checkpoint(self, payload):
        with db() as con:
            con.execute("UPDATE missions SET evidence=?, interrupt_requested=0, updated_at=? WHERE id=?",
                        (json.dumps(payload) if not isinstance(payload, str) else payload, now_iso(), self.mid))

# ─── Execution d'une mission (pas de completion sur code retour seul) ─
def execute_one(m, worker, lease_s):
    acc = json.loads(m["acceptance"]) if isinstance(m["acceptance"], str) else m["acceptance"]
    handler = SAFE_HANDLERS.get(acc.get("handler"))
    if handler is None:
        set_state(m["id"], "blocked", error="handler non autorise",
                  history=hist_append(m, "blocked handler")); return "blocked"
    ctx = Ctx(m["id"], worker, lease_s)
    mid = m["id"]
    with db() as con:  # journalise l'etat running + objectif
        con.execute("UPDATE missions SET state='running', history=?, updated_at=? WHERE id=?",
                    (hist_append(m, "running"), now_iso(), mid))
    try:
        res = handler(m, ctx)
    except PermissionError as e:
        set_state(mid, "failed", error=str(e), history=hist_append(m, f"failed {e}"))
        return "failed"
    except Exception as e:
        err_str = str(e)
        # ------------------------------------------------------------------
        # Catégorisation d'erreur pour un handling contrôlé (quota guard)
        # ------------------------------------------------------------------
        if "429" in err_str or "rate limit" in err_str.lower() or "quota" in err_str.lower():
            error_category = "refus_quota"
        elif "402" in err_str:
            error_category = "paiement_requis"
        elif "timeout" in err_str.lower():
            error_category = "timeout"
        elif err_str.strip() == "" or "empty" in err_str.lower():
            error_category = "reponse_vide"
        else:
            error_category = "autre"

        # ------------------------------------------------------------------
        # Gestion spécifique par catégorie
        # ------------------------------------------------------------------
        if error_category == "refus_quota":
            # Backoff avec gestion de Retry-After (P5.4.2)
            # - Si Retry-After valide -> respecter le délai du serveur tel quel
            #   (sans plafonnement artificiel pour ne jamais autoriser un appel
            #   prématuré avant l'échéance du serveur).
            # - Si Retry-After absent/invalide -> jitter existant pour éviter
            #   le "thundering herd".
            # - Distinction quota journalier / 429 temporaire : seule une indication
            #   fiable (comme le texte "free-models-per-day" ou quota journalier
            #   explicite) permet de traiter comme épuisement quotidien (pas de retry
            #   automatique). Un 429 classique est traité comme temporaire.
            # - Le jitter reste appliqué lorsque le serveur ne fournit pas de délai
            #   fiable.
            # - Pas de plafond artificiel : on respecte le délai du serveur.
            # - Le worker n'est pas bloqué : le délai est enregistré durablement
            #   en SQLite et le worker est libéré immédiatement.
            retry_after = None
            # Extraction simple de Retry-After depuis le message d'erreur
            # (Dans un déploiement réel, ces informations viendraient des en-têtes HTTP)
            if "Retry-After" in err_str:
                # Tentative d'extraction du nombre de secondes
                import re
                match = re.search(r'Retry-After\s*:\s*(\d+)', err_str, re.IGNORECASE)
                if match:
                    raw_after = int(match.group(1))
                    # Pas de plafond artificiel : on respecte le délai du serveur
                    retry_after = raw_after
                # Tentative d'extraction d'une date HTTP
                # Format: Retry-After: Mon, 27 Jul 2025 12:00:00 GMT
                else:
                    try:
                        from email.utils import parsedate_to_datetime
                        dt = parsedate_to_datetime(
                            err_str.split('Retry-After')[1] \
                            if 'Retry-After' in err_str else None)
                        if dt:
                            # Calcul du délai avant la date d'expiration
                            now = now_epoch()
                            retry_at = dt.timestamp()
                            delay = max(0, retry_at - now)
                            retry_after = delay
                    except Exception:
                        pass
                # Si le format n'est pas reconnaissable, on laisse retry_after à None
                # et on utilise le jitter existant
            # Calcul du temps d'attente et enregistrement durable
            if retry_after is not None and retry_after >= 0:
                # Serveur fournit un délai fiable -> on enregistre l'échéance
                # backoff est le délai exact du serveur, pas de jitter supplémentaire
                # Pas de jitter supplémentaire : le délai est imposé par le serveur
                # et est déjà conçu pour éviter la congestion
                backoff = max(0, retry_after)
                # Enregistrement de l'échéance de reprise en SQLite.
                # Le worker sera libéré immédiatement (pas de time.sleep()).
                # La mission demeure en état 'queued' avec lease_expires_at fixé.
                with db() as con:
                    con.execute(
                        "UPDATE missions SET lease_expires_at=?, history=hist_append(m, 'refus_quota') WHERE id=?",
                        (now_epoch() + retry_after, mid))
            else:
                # Aucun Retry-After fiable -> jitter existant pour la répartition
                # Et on conserve le comportement de sleep existant pour compatibilité
                # avec les Retry-After absents ou invalides
                backoff = max(0, min(2 ** m["attempts"], 30) + random.uniform(-2, 2))
                time.sleep(backoff)
            # Remise en file avec like motif; le cycle principal gérera le prochain essai
            # La mission demeure en état 'queued' avec lease_expires_at fixé
            if retry_after is not None and retry_after >= 0:
                # Délai serveur fiable : on laisse lease_expires_at tel quel
                # (déjà fixé en SQLite juste au-dessus au line 488-490)
                set_state(mid, "queued", error=f"refus_quota: {err_str}", owner=None,
                          history=hist_append(m, "refus_quota"))
                # On ne définit pas lease_expires_at=None ici : il persiste en SQLite
                # et sera vérifié par claim() au prochain réclamage
            else:
                # Aucun Retry-After fiable : on efface lease_expires_at
                # pour permettre le prochain réclamage immédiat
                set_state(mid, "queued", error=f"refus_quota: {err_str}", owner=None,
                          lease_expires_at=None,
                          history=hist_append(m, "refus_quota"))
            return "retry" if m["attempts"] < m["max_retries"] else "failed"

        elif error_category == "paiement_requis":
            # 402 régle d'échec immédiat sans retry
            set_state(mid, "failed", error=f"paiement_requis: {err_str}", owner=None,
                      lease_expires_at=None,
                      history=hist_append(m, "paiement_requis"))
            return "failed"

        elif error_category == "timeout":
            # Timeout : bornes par max_retries, jitter léger
            backoff = max(0, min(2 ** m["attempts"], 30) + random.uniform(-1, 1))
            time.sleep(backoff)
            set_state(mid, "queued", error=f"timeout: {err_str}", owner=None,
                      lease_expires_at=None,
                      history=hist_append(m, "timeout"))
            return "retry" if m["attempts"] < m["max_retries"] else "failed"

        elif error_category == "reponse_vide":
            # Réponse vide : une seule reprise, pas d'enchaînement infini
            if m["attempts"] == 0:
                # Première tentative échouée avec réponse vide : nouvelle tentative immédiate
                return "retry"
            else:
                # Deuxième échec : abandon
                set_state(mid, "failed", error=f"reponse_vide: {err_str}", owner=None,
                          lease_expires_at=None,
                          history=hist_append(m, "reponse_vide"))
                return "failed"

        elif error_category == "autre":
            # Autre erreur : jitter + retry borné
            backoff = max(0, min(2 ** m["attempts"], 30) + random.uniform(-2, 2))
            time.sleep(backoff)
            set_state(mid, "queued", error=f"autre: {err_str}", owner=None,
                      lease_expires_at=None,
                      history=hist_append(m, "autre"))
            return "retry" if m["attempts"] < m["max_retries"] else "failed"

    state_out = res.get("state_out", "completed")
    if state_out == "checkpointed":
        set_state(mid, "checkpointed", evidence=res.get("evidence"),
                  owner=None, lease_expires_at=None, interrupt_requested=0,
                  history=hist_append(m, "checkpointed (arret interactif)"))
        log(f"CHECKPOINT {mid} (retour interactif -> etape sure) ")
        return "checkpointed"

    if state_out == "completed":
        ok, why = validate_acceptance(m, res.get("evidence"))
        if not ok:
            if m["attempts"] < m["max_retries"]:
                set_state(mid, "queued", error=f"acceptation echouee: {why}", owner=None,
                          lease_expires_at=None, history=hist_append(m, f"acceptation {why}"))
                return "retry"
            set_state(mid, "failed", error=f"acceptation echouee: {why}", owner=None,
                      lease_expires_at=None, evidence=res.get("evidence"),
                      history=hist_append(m, f"acceptation {why}"))
            return "failed"
        return "completed"

    if state_out == "blocked":
        # Handler a retourné blocked (ex: validation échouée, revue bloquante)
        # On respecte le max_retries pour retry automatique
        if m["attempts"] < m["max_retries"]:
            set_state(mid, "queued", error=f"blocked: {res.get('evidence', '')}", owner=None,
                      lease_expires_at=None, history=hist_append(m, "blocked retry"))
            return "retry"
        set_state(mid, "failed", error=f"blocked après {m['attempts']} essais: {res.get('evidence', '')}",
                  owner=None, lease_expires_at=None, evidence=res.get("evidence"),
                  history=hist_append(m, f"blocked failed after {m['attempts']}"))
        return "failed"

    # etat inconnu
    set_state(mid, "blocked", error=f"state_out inconnu {state_out}")
    return "blocked"

def NULL():
    return None

# ─── Boucle worker (un tick) ───────────────────────────────────────
def worker_tick(verbose=False):
    c = load_control()
    if c.get("mode") == "RECOVERING":
        reclaim_stale()
        c2 = dict(c); c2["mode"] = "AUTONOMOUS" if not is_interactive(c) else "INTERACTIVE"
        c2["updated_by"] = "recover-done"; c2["updated_at"] = now_iso()
        save_control(c2)
        log("RECOVERING -> reconciliation terminee, mode=" + c2["mode"]); return "recovered"
    reclaim_stale()
    if not claims_allowed(c):
        if verbose: log("TICK idle: claims_non_autorises (mode=%s lock=%s)" % (c["mode"], c.get("interactive_lock")))
        return "idle"
    m = claim(WORKER, c["lease_seconds"])
    if not m:
        if verbose: log("TICK idle: file vide ou concurrence saturee")
        return "idle"
    log(f"CLAIM {m['id']} par {WORKER} (attempt {m['attempts']})")
    return execute_one(m, WORKER, c["lease_seconds"])

def worker_loop(interval=None, once=False):
    c = load_control(); iv = float(interval or c["poll_seconds"])
    if once:
        return worker_tick(verbose=True)
    log(f"WORKER start {WORKER}")
    try:
        while True:
            worker_tick()
            time.sleep(iv)
    except KeyboardInterrupt:
        log("WORKER stop (KeyboardInterrupt)")
        try: os.remove(SUP_LOCK)
        except OSError: pass

# ─── Superviseur (instance unique, heartbeat, reprise, sans console) ─
def pid_alive(pid):
    if not pid: return False
    PROCESS_QUERY_LIMITED = 0x1000
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, int(pid))
    if h:
        ctypes.windll.kernel32.CloseHandle(h); return True
    return False

def acquire_supervisor():
    """Une seule instance active de superviseur; une 2e devient standby.
    Reprise automatique si l'instance precedente est morte OU si son heartbeat
    est perime (détection de processus bloque /HS), meme si son PID semble
    encore 'vivant' (cas Windows: handle encore ouvert)."""
    takeover_after = float(os.environ.get("F3_HB_TAKEOVER", "20"))
    c = load_control()
    hb_fresh = False
    try:
        hb = c.get("supervisor_heartbeat_at")
        if hb:
            age = time.time() - datetime.fromisoformat(hb.replace("Z", "+00:00")).timestamp()
            hb_fresh = age < takeover_after
    except Exception:
        hb_fresh = False
    if os.path.exists(SUP_LOCK):
        try:
            other = int(open(SUP_LOCK).read().strip())
        except Exception:
            other = None
        if other and other != os.getpid() and pid_alive(other) and hb_fresh:
            return False  # instance saine et active -> standby
    tmp = SUP_LOCK + ".tmp"
    with open(tmp, "w") as f: f.write(str(os.getpid()))
    os.replace(tmp, SUP_LOCK)
    return True

def supervisor_loop(interval=None):
    if not acquire_supervisor():
        log("SUPERVISEUR standby: une instance active existe deja")
        return "standby"
    c = load_control(); iv = float(interval or c["poll_seconds"])
    log(f"SUPERVISEUR start pid={os.getpid()} db={DB}")
    try:
        while True:
            try:
                c = load_control()
                hb = now_iso()
                with db() as con:
                    run = con.execute("SELECT COUNT(*) n FROM missions WHERE state='running'").fetchone()["n"]
                c["supervisor_pid"] = os.getpid(); c["supervisor_heartbeat_at"] = hb
                c["_running"] = run
                save_control(c)
                if c.get("mode") == "RECOVERING":
                    reclaim_stale()
                worker_tick()
            except Exception as e:
                log(f"SUPERVISEUR tick error: {e}")
            time.sleep(iv)
    except KeyboardInterrupt:
        log("SUPERVISEUR stop (KeyboardInterrupt)")
        try: os.remove(SUP_LOCK)
        except OSError: pass

# ─── CLI ───────────────────────────────────────────────────────────
def _print_json(o): print(json.dumps(o, ensure_ascii=False, indent=2))

def cmd_status(args):
    c = load_control(); n = counts()
    interactive = is_interactive(c)
    _print_json({
        "mode": c["mode"], "interactive_lock": c.get("interactive_lock"),
        "claims_allowed": claims_allowed(c), "interactive_hint": interactive_hint(),
        "concurrency_limit": c["concurrency_limit"], "max_retries": c["max_retries"],
        "counts": n,
        "supervisor": {"pid": c.get("supervisor_pid"), "heartbeat_at": c.get("supervisor_heartbeat_at"),
                       "alive": pid_alive(c.get("supervisor_pid"))},
        "db": DB, "workspace": WORKSPACE,
    })

def _set_mode(args, mode, reason):
    c = load_control()
    c["mode"] = mode
    c["interactive_lock"] = True if mode == "INTERACTIVE" else False
    c["updated_by"] = "cli"; c["updated_at"] = now_iso(); c["reason"] = reason or mode
    save_control(c)
    log(f"MODE -> {mode} ({reason or 'cli'})")
    _print_json({"mode": mode, "interactive_lock": c["interactive_lock"], "reason": c["reason"]})

def cmd_pause(args):   _set_mode(args, "PAUSED", "pause manuel")
def cmd_resume(args):  _set_mode(args, "AUTONOMOUS", "resume manuel")
def cmd_interactive(args): _set_mode(args, "INTERACTIVE", "priorité interactive manuelle")
def cmd_auto(args):    _set_mode(args, "AUTONOMOUS", "mode autonome manuel")
def cmd_recover(args): _set_mode(args, "RECOVERING", "recovery manuel")
def cmd_error(args):
    c = load_control(); c["mode"] = "ERROR"; c["updated_by"] = "cli"; c["updated_at"] = now_iso()
    c["reason"] = args.reason or "erreur"; save_control(c); log("MODE -> ERROR " + c["reason"])
    _print_json({"mode": "ERROR", "reason": c["reason"]})

def cmd_queue(args):
    q = "SELECT id,kind,state,priority,attempts,max_retries,owner,model,objective,updated_at FROM missions"
    params = ()
    if args.state:
        q += " WHERE state=?"; params = (args.state,)
    q += " ORDER BY priority DESC, created_at ASC"
    with db() as con:
        _print_json([dict(r) for r in con.execute(q, params).fetchall()])

def cmd_logs(args):
    if not os.path.exists(LOG):
        print("(aucun log)"); return
    with open(LOG, encoding="utf-8", errors="ignore") as f:
        print("".join(f.readlines()[-args.n:]))

def cmd_enqueue(args):
    try:
        mid = enqueue(kind=args.kind, model=args.model, handler=args.handler,
                      repo=args.repo, scope=args.scope, branch=args.branch, worktree=args.worktree,
                      objective=args.o or "", expect_marker=args.marker, expect_regex=args.regex,
                      ctx_budget=args.ctx, max_tokens=args.max_tokens, timeout_s=args.timeout,
                      max_retries=args.retries, priority=args.priority)
        _print_json({"enqueued": mid})
    except (PermissionError, ValueError) as e:
        print("REFUSE: " + str(e)); sys.exit(2)

def cmd_run(args):   worker_loop(args.interval, once=args.once)
def cmd_supervise(args): supervisor_loop(args.interval)
def cmd_recover_stale(args): _print_json({"reclaimed": reclaim_stale()})
def cmd_init(args):
    init_db(); save_control(default_control()); print("init ok"); _print_json({"db": DB, "control": CONTROL})

def build_parser():
    p = argparse.ArgumentParser(prog="factory", description="Factory V3 control/worker/supervisor")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("status"); 
    sub.add_parser("pause"); sub.add_parser("resume")
    sub.add_parser("interactive"); sub.add_parser("auto")
    sub.add_parser("recover"); e = sub.add_parser("error"); e.add_argument("--reason", default="")
    q = sub.add_parser("queue"); q.add_argument("--state", default=None)
    lg = sub.add_parser("logs"); lg.add_argument("-n", type=int, default=40)
    en = sub.add_parser("enqueue")
    en.add_argument("--kind", required=True); en.add_argument("--model", default="")
    en.add_argument("--handler", required=True); en.add_argument("--marker", default=None)
    en.add_argument("--regex", default=None); en.add_argument("--priority", type=int, default=0)
    en.add_argument("--ctx", type=int, default=65536); en.add_argument("--max-tokens", type=int, default=4096)
    en.add_argument("--timeout", type=int, default=None); en.add_argument("--retries", type=int, default=None)
    en.add_argument("--repo", default=None); en.add_argument("--scope", default=None)
    en.add_argument("--branch", default=None); en.add_argument("--worktree", default=None)
    en.add_argument("--o", dest="o", default="")
    r = sub.add_parser("run"); r.add_argument("--interval", type=float, default=None); r.add_argument("--once", action="store_true")
    s = sub.add_parser("supervise"); s.add_argument("--interval", type=float, default=None)
    sub.add_parser("reclaim")
    sub.add_parser("init")
    return p

def main(argv=None):
    args = build_parser().parse_args(argv)
    init_db()
    cmd = args.cmd
    table = {"status": cmd_status, "pause": cmd_pause, "resume": cmd_resume,
             "interactive": cmd_interactive, "auto": cmd_auto, "recover": cmd_recover,
             "error": cmd_error, "queue": cmd_queue, "logs": cmd_logs,
             "enqueue": cmd_enqueue, "run": cmd_run, "supervise": cmd_supervise,
             "reclaim": cmd_recover_stale, "init": cmd_init}
    if cmd not in table:
        build_parser().print_help(); sys.exit(1)
    table[cmd](args)

if __name__ == "__main__":
    main()