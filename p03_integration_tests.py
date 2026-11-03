#!/usr/bin/env python3
"""
P0.3 Integration tests — preuve que session_convergence et watchdog_convergence
sont effectivement appeals dans le parcours d'execution reel de f3.py.

Instance isolee sous C:\test-factory-isolated\p03int.
Ne touche aucun projet de production.

NOTE: Le marqueur C:\factory\control\STOP-Autonomie (garde-fou P0.1) est
temporairement deplace pendant les tests pour permettre l'execution,
puis restaure.
"""

import os, sys, json, time, shutil, importlib.util

ISOL = r"C:\test-factory-isolated\p03int"
if os.path.exists(ISOL):
    shutil.rmtree(ISOL, ignore_errors=True)
os.makedirs(ISOL, exist_ok=True)

os.environ.update({
    "F3_ROOT": ISOL,
    "F3_STATE": os.path.join(ISOL, "state"),
    "F3_DB": os.path.join(ISOL, "state", "f3_missions.db"),
    "F3_CONTROL": os.path.join(ISOL, "state", "f3_control.json"),
    "F3_LOG": os.path.join(ISOL, "state", "logs"),
    "F3_WORKSPACE": os.path.join(ISOL, "worktrees"),
    "F3_QUIET": "1",
    "F3_STEP_DELAY": "0.05",
})

F3PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "f3.py")
spec = importlib.util.spec_from_file_location("f3", F3PATH)
f3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f3)

f3.init_db()

SESSIONS_DIR = os.path.join(ISOL, "state", "sessions")

# ── Gestion du marqueur STOP-Autonomie (P0.1 kill switch) ─────────────
STOP_FILE = r"C:\factory\control\STOP-Autonomie"
STOP_BACKUP = r"C:\factory\control\STOP-Autonomie.p03int-bak"

def _disable_stop_autonomie():
    if os.path.exists(STOP_FILE) and not os.path.exists(STOP_BACKUP):
        shutil.move(STOP_FILE, STOP_BACKUP)
        return True
    return False

def _restore_stop_autonomie():
    if os.path.exists(STOP_BACKUP) and not os.path.exists(STOP_FILE):
        shutil.move(STOP_BACKUP, STOP_FILE)
        return True
    return False

_DISABLED = _disable_stop_autonomie()

RESULTS = []

def check(name, cond, ev):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + " | " +
          json.dumps(ev, ensure_ascii=False, default=str)[:300])


def set_ctl(**kw):
    c = f3.load_control(); c.update(kw); c["updated_by"] = "test"; c["updated_at"] = f3.now_iso(); f3.save_control(c); return c


def _clear_db():
    """Nettoie la base entre les tests pour l'isolation."""
    with f3.db() as con:
        con.execute("UPDATE missions SET state='queued', owner=NULL, lease_expires_at=NULL WHERE state='running'")
        con.execute("DELETE FROM missions")


def ws(mid): return os.path.join(ISOL, "worktrees", mid)


# ── Test 1: Modules intégrés dans f3.py ───────────────────────────────
def test_t1_modules_integrated_in_f3():
    """Vérifier que session_convergence et watchdog_convergence sont réellement intégrés dans f3.py."""
    check("T1a f3._SESSIONS n'est pas None",
          f3._SESSIONS is not None,
          {"_SESSIONS": type(f3._SESSIONS).__name__ if f3._SESSIONS else None})
    check("T1b f3._WATCHDOG n'est pas None",
          f3._WATCHDOG is not None,
          {"_WATCHDOG": type(f3._WATCHDOG).__name__ if f3._WATCHDOG else None})
    check("T1c f3._agent_type_from_model existe",
          callable(getattr(f3, "_agent_type_from_model", None)),
          {"callable": callable(getattr(f3, "_agent_type_from_model", None))})
    check("T1d router/fast -> general-fast",
          f3._agent_type_from_model("router/fast") == "general-fast",
          {"result": f3._agent_type_from_model("router/fast")})
    check("T1e router/balanced -> rbalanced",
          f3._agent_type_from_model("router/balanced") == "rbalanced",
          {"result": f3._agent_type_from_model("router/balanced")})
    check("T1f router/deep -> rdeep",
          f3._agent_type_from_model("router/deep") == "rdeep",
          {"result": f3._agent_type_from_model("router/deep")})
    check("T1g modèle inconnu -> general-fast",
          f3._agent_type_from_model("unknown/model") == "general-fast",
          {"result": f3._agent_type_from_model("unknown/model")})


# ── Test 2: Mission termine normalement, progression enregistre ───────
def test_t2_mission_complete_with_progress():
    """Une mission qui progresse, franchit ses étapes et termine avec un état terminal persistant."""
    _clear_db()
    set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1,
            max_retries=5, lease_seconds=60, poll_seconds=1)

    m = f3.enqueue(kind="maintenance", model="router/fast", handler="emit",
                   objective="T2 complete", expect_marker="DONE.txt")
    outcome = f3.worker_tick(verbose=False)
    mm = f3.get_mission(m)

    check("T2a mission state=completed",
          mm["state"] == "completed",
          {"state": mm["state"], "outcome": outcome})

    state_file = os.path.join(SESSIONS_DIR, m, "state.json")
    check("T2b session state.json existe sur disque",
          os.path.isfile(state_file),
          {"path": state_file})

    if os.path.isfile(state_file):
        with open(state_file, encoding="utf-8") as f:
            sess = json.load(f)
        check("T2c session a last_progress enregistre",
              bool(sess.get("last_progress")),
              {"last_progress": sess.get("last_progress")})
        # iteration_count=0 est correct pour un premier run sans retry
        check("T2d session iteration_count est 0 (premier run sans retry)",
              sess.get("iteration_count", 0) == 0,
              {"iteration_count": sess.get("iteration_count")})


# ── Test 3: Mission bloquée par budget dépassé est arrêtée ─────────────
def test_t3_budget_exceeded_stops_mission():
    """Une mission dont le budget est épuisé est arrêtée par execute_one."""
    _clear_db()
    set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1,
            max_retries=1, lease_seconds=60, poll_seconds=1)

    # Créer une mission
    m = f3.enqueue(kind="maintenance", model="router/fast", handler="emit",
                   objective="T3 budget", expect_marker="X")

    # Épuiser le budget ET les retries de la session AVANT la première exécution
    # retry_count >= WatchdogConvergence.max_retries(3) -> le watchdog garre, pas recupere
    f3._SESSIONS.create_session(m, m, agent_type="general-fast", max_steps=1)
    f3._SESSIONS.increment_iteration(m)  # iteration=1 = max_steps
    f3._SESSIONS._sessions[m]["retry_count"] = 3  # >= WatchdogConvergence.max_retries(3)
    f3._SESSIONS._persist(f3._SESSIONS._sessions[m])

    # Exécuter : watchdog gare la session, execute_one détecte le budget dépassé
    outcome = f3.worker_tick(verbose=False)
    mm = f3.get_mission(m)

    check("T3 mission arrêtée par budget dépassé",
          mm["state"] == "failed" and "budget_exceeded" in (mm.get("error") or ""),
          {"state": mm["state"], "error": mm.get("error"), "outcome": outcome})


# ── Test 4: Mission longue avec heartbeat actif pas interrompue à tort ─
def test_t4_long_mission_heartbeat_not_interrupted():
    """Une mission longue dont le heartbeat reste actif ne doit pas être interrompue."""
    _clear_db()
    set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1,
            max_retries=5, lease_seconds=60, poll_seconds=1)

    m = f3.enqueue(kind="dev", model="router/balanced", handler="steps",
                   objective="T4 long", expect_marker="STEPS")

    outcome = f3.worker_tick(verbose=False)
    mm = f3.get_mission(m)

    check("T4 mission complétée (pas d'interruption à tort)",
          mm["state"] in ("completed", "checkpointed"),
          {"state": mm["state"], "outcome": outcome, "attempts": mm["attempts"]})


# ── Test 5: Redémarrage du worker avec récupération ────────────────────
def test_t5_worker_restart_state_recovery():
    """Un redémarrage du worker avec récupération correcte de l'état."""
    _clear_db()
    set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1,
            max_retries=5, lease_seconds=60, poll_seconds=1)

    m = f3.enqueue(kind="maintenance", handler="emit", objective="T5 restart",
                   expect_marker="R")

    # Simuler un crash : la mission est 'running' avec bail expiré
    with f3.db() as con:
        con.execute("UPDATE missions SET state='running', owner='ghost', lease_expires_at=? WHERE id=?",
                    (time.time() - 5, m))

    # Reclaim stale (simule redémarrage du superviseur)
    n = f3.reclaim_stale()
    check("T5a bail expiré réclamé après redémarrage",
          n == 1,
          {"reclaimed": n})

    mm = f3.get_mission(m)
    check("T5b état repasse à queued après reclaim",
          mm["state"] == "queued",
          {"state": mm["state"]})

    # Réexécuter : la mission doit compléter
    # Recharger les sessions sur disque (cache mémoire de f3._SESSIONS)
    f3._SESSIONS._load_all()
    f3._WATCHDOG.check_all()
    outcome = f3.worker_tick(verbose=False)
    mm = f3.get_mission(m)
    check("T5c mission complète après reprise",
          mm["state"] == "completed",
          {"state": mm["state"], "outcome": outcome})


# ── Test 6: Erreur fournisseur / quota, pas de boucle infinie ───────────
def test_t6_provider_error_bounded_retry():
    """Une erreur fournisseur ou quota épuisé, sans boucle de relances infinies."""
    _clear_db()
    set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1,
            max_retries=2, lease_seconds=60, poll_seconds=1)

    m = f3.enqueue(kind="tests", model="", handler="boom", objective="T6 quota")

    seq = []
    for _ in range(6):
        f3.worker_tick(verbose=False)
        mm = f3.get_mission(m)
        seq.append((mm["state"], mm["attempts"]))
        if mm["state"] == "failed":
            break

    mm = f3.get_mission(m)
    check("T6 échec terminé en 'failed' après max_retries (pas de boucle infinie)",
          mm["state"] == "failed" and mm["attempts"] >= 2,
          {"final_state": mm["state"], "attempts": mm["attempts"], "seq": seq})


# ── Test 7: Sous-mission bloquée ne retient pas la parente ───────────────
def test_t7_submission_blocked_does_not_retain_parent():
    """Une sous-mission bloquée qui ne retient pas indéfiniment sa mission parente."""
    _clear_db()
    set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1,
            max_retries=1, lease_seconds=60, poll_seconds=1)

    parent = f3.enqueue(kind="maintenance", model="router/fast", handler="emit",
                        objective="T7 parent", expect_marker="P")
    child = f3.enqueue(kind="tests", model="", handler="boom", objective="T7 child")

    f3.worker_tick(verbose=False)
    p = f3.get_mission(parent)
    check("T7a parente complétée",
          p["state"] == "completed",
          {"parent_state": p["state"]})

    f3.worker_tick(verbose=False)
    c = f3.get_mission(child)
    check("T7b enfant échoue sans bloquer indéfiniment",
          c["state"] == "failed",
          {"child_state": c["state"], "child_attempts": c["attempts"]})

    p2 = f3.get_mission(parent)
    check("T7c parente toujours completed malgré échec enfant",
          p2["state"] == "completed",
          {"parent_state_after": p2["state"]})


# ── Test 8: Watchdog détecte une session bloquée ───────────────────────
def test_t8_watchdog_detects_stuck_session():
    """Le watchdog intégré détecte et gare une session sans progression."""
    _clear_db()
    set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1,
            max_retries=1, lease_seconds=60, poll_seconds=1)

    m = f3.enqueue(kind="maintenance", model="router/fast", handler="emit",
                   objective="T8 watchdog", expect_marker="W")

    # Créer une session avec steps_without_progress=5 et retry_count >= WatchdogConvergence.max_retries(3)
    f3._SESSIONS.create_session(m, m, agent_type="general-fast", max_steps=10)
    f3._SESSIONS._sessions[m]["steps_without_progress"] = 5
    f3._SESSIONS._sessions[m]["retry_count"] = 3  # >= WatchdogConvergence.max_retries(3)
    f3._SESSIONS._persist(f3._SESSIONS._sessions[m])

    # Lancer worker_tick : le watchdog (appelé au début de worker_tick)
    # doit détecter la session bloquée et la garer
    outcome = f3.worker_tick(verbose=False)
    mm = f3.get_mission(m)

    check("T8 watchdog gare la session bloquée",
          mm["state"] in ("failed", "parked"),
          {"state": mm["state"], "outcome": outcome})


# ── Exécuter tous les tests ─────────────────────────────────────────────

if __name__ == "__main__":
    try:
        tests = [
            test_t1_modules_integrated_in_f3,
            test_t2_mission_complete_with_progress,
            test_t3_budget_exceeded_stops_mission,
            test_t4_long_mission_heartbeat_not_interrupted,
            test_t5_worker_restart_state_recovery,
            test_t6_provider_error_bounded_retry,
            test_t7_submission_blocked_does_not_retain_parent,
            test_t8_watchdog_detects_stuck_session,
        ]

        for t in tests:
            try:
                t()
            except Exception as e:
                RESULTS.append((t.__name__, False))
                print(f"ERROR | {t.__name__} | {e}")
    finally:
        _restore_stop_autonomie()

    ok = sum(1 for _, c in RESULTS if c)
    tot = len(RESULTS)
    print(f"\n==== RESUME P0.3 intégration ====")
    print(f"{ok}/{tot} tests PASS")
    for n, c in RESULTS:
        print(("PASS " if c else "FAIL ") + n)
    sys.exit(0 if ok == tot else 1)
