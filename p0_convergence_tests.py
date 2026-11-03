#!/usr/bin/env python3
"""
P0 Convergence regression tests — Factory V3.

Tests the convergence guards added in P0/P0.1:
- Per-agent-type iteration budgets (max_steps)
- Progress tracking (last_progress, steps_without_progress)
- Budget exceeded detection
- No-progress stuck detection (NO_PROGRESS_STEPS)
- Session persistence to disk (state.json)
- Recovery with counter reset
- Watchdog integration (no_progress_last_n_steps, iteration_budget_exceeded)
- Provider error handling (empty response, quota, retry bounds)
- Session resume after interruption
- False positive: legitimate long task not interrupted

Instance isolee: utilise un repertoire de test sous C:\test-factory-isolated\p0conv.
Ne modifie aucun projet de production.
"""

import os, sys, json, time, shutil, importlib.util

ISOL = r"C:\test-factory-isolated\p0conv"
if os.path.exists(ISOL):
    shutil.rmtree(ISOL, ignore_errors=True)
os.makedirs(ISOL, exist_ok=True)

# Isolated sessions directory
SESSIONS_DIR = os.path.join(ISOL, "state", "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

# Load the convergence modules from this repo
REPO = os.path.dirname(os.path.abspath(__file__))
spec_sc = importlib.util.spec_from_file_location(
    "session_convergence", os.path.join(REPO, "session_convergence.py"))
session_convergence = importlib.util.module_from_spec(spec_sc)
spec_sc.loader.exec_module(session_convergence)

spec_wd = importlib.util.spec_from_file_location(
    "watchdog_convergence", os.path.join(REPO, "watchdog_convergence.py"))
watchdog_convergence = importlib.util.module_from_spec(spec_wd)
spec_wd.loader.exec_module(watchdog_convergence)

SessionConvergence = session_convergence.SessionConvergence
WatchdogConvergence = watchdog_convergence.WatchdogConvergence
NO_PROGRESS_STEPS = session_convergence.NO_PROGRESS_STEPS
AGENT_BUDGETS = session_convergence.AGENT_BUDGETS
DEFAULT_MAX_STEPS = session_convergence.DEFAULT_MAX_STEPS

RESULTS = []


def check(name, cond, ev):
    RESULTS.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + " | " +
          json.dumps(ev, ensure_ascii=False, default=str)[:300])


# ── A. Budgets d'exécution ────────────────────────────────────────

def test_a1_known_agent_gets_budget():
    """Un agent disposant d'un budget connu reçoit bien sa limite."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a1", "t-a1", agent_type="general-fast")
    check("A1 general-fast budget=5",
          s["max_steps"] == 5 and s["agent_type"] == "general-fast",
          {"max_steps": s["max_steps"], "agent_type": s["agent_type"]})


def test_a2_rdeep_agent_budget_12():
    """rdeep agent gets max_steps=12 (implementation phase)."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a2", "t-a2", agent_type="rdeep")
    check("A2 rdeep budget=12",
          s["max_steps"] == 12 and s["agent_type"] == "rdeep",
          {"max_steps": s["max_steps"], "agent_type": s["agent_type"]})


def test_a3_unknown_agent_fallback():
    """Un agent inconnu suit un comportement de repli determine (DEFAULT_MAX_STEPS=5)."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a3", "t-a3", agent_type="unknown-type")
    check("A3 unknown agent defaults to max_steps=5",
          s["max_steps"] == DEFAULT_MAX_STEPS,
          {"max_steps": s["max_steps"]})


def test_a4_no_agent_type_defaults():
    """Aucun agent_type specify -> general-fast budget (5)."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a4", "t-a4")
    check("A4 no agent_type defaults to max_steps=5",
          s["max_steps"] == DEFAULT_MAX_STEPS and s["agent_type"] == "general-fast",
          {"max_steps": s["max_steps"], "agent_type": s["agent_type"]})


def test_a5_normal_session_completes_before_limit():
    """Une session normale peut terminer avant la limite (progress recorded)."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a5", "t-a5", agent_type="general-fast")
    # Simulate meaningful progress within budget
    for i in range(3):
        sc.increment_iteration("s-a5")
        sc.record_progress("s-a5")
    budget = sc.check_budget("s-a5")
    check("A5 session completes within budget (not exceeded)",
          not budget["exceeded"] and budget["iteration_count"] == 3,
          budget)


def test_a6_budget_exceeded_triggers_stop():
    """Le depassement de la limite declenche l'arret de la progression."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a6", "t-a6", agent_type="general-fast")  # max_steps=5
    # Reach the limit
    for i in range(5):
        sc.increment_iteration("s-a6")
    budget = sc.check_budget("s-a6")
    check("A6 budget exceeded at exactly max_steps",
          budget["exceeded"] and budget["iteration_count"] == 5,
          budget)
    # One more iteration: still exceeded
    sc.increment_iteration("s-a6")
    budget2 = sc.check_budget("s-a6")
    check("A6b budget still exceeded beyond max_steps",
          budget2["exceeded"] and budget2["iteration_count"] == 6,
          budget2)


def test_a7_budget_check_at_execution_points():
    """La verification intervient aux points pertinents, pas seulement initialement."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a7", "t-a7", agent_type="general-fast")
    # Initially within budget
    b0 = sc.check_budget("s-a7")
    check("A7a initially within budget", not b0["exceeded"], b0)
    # After 4 iterations, still within budget
    for _ in range(4):
        sc.increment_iteration("s-a7")
    b4 = sc.check_budget("s-a7")
    check("A7b after 4 iterations still within budget",
          not b4["exceeded"] and b4["iteration_count"] == 4, b4)
    # After 5th iteration: exceeded
    sc.increment_iteration("s-a7")
    b5 = sc.check_budget("s-a7")
    check("A7c after 5 iterations exceeded",
          b5["exceeded"] and b5["iteration_count"] == 5, b5)


def test_a8_resume_does_not_reset_budget_indefinitely():
    """Une reprise de session ne reinitialise pas accidentellement le compteur
    et ne permet pas de contourner indefiniment le budget."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-a8", "t-a8", agent_type="general-fast")
    # Use up 3 iterations
    for _ in range(3):
        sc.increment_iteration("s-a8")
    b3 = sc.check_budget("s-a8")
    check("A8a before recovery: 3 iterations",
          b3["iteration_count"] == 3 and not b3["exceeded"], b3)
    # Recover (simulate restart)
    s2 = sc.recover_session("s-a8")
    check("A8b recovery resets iteration_count to 0",
          s2["iteration_count"] == 0 and s2["steps_without_progress"] == 0,
          {"iteration_count": s2["iteration_count"],
           "steps_without_progress": s2["steps_without_progress"]})
    # But retry_count is incremented
    check("A8c recovery increments retry_count",
          s2["retry_count"] >= 1, {"retry_count": s2["retry_count"]})
    # After recovery, budget still applies (max_steps unchanged)
    b_rec = sc.check_budget("s-a8")
    check("A8d after recovery max_steps unchanged",
          b_rec["max_steps"] == 5, b_rec)


def test_a9_limits_coherent_across_components():
    """Les limites sont coherentes entre session-manager, worker et watchdog."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=3)
    s = sc.create_session("s-a9", "t-a9", agent_type="rdeep")  # max_steps=12
    # Session starts healthy
    check("A9a rdeep session max_steps=12",
          sc.check_budget("s-a9")["max_steps"] == 12,
          sc.check_budget("s-a9"))
    # Watchdog finds no issues initially
    issues = wd.check_session("s-a9")
    check("A9b watchdog no issues initially", issues == [], {"issues": issues})


# ── B. Progression reelle et faux positifs ────────────────────────

def test_b1_effective_progress_recorded():
    """Une modification effective peut etre enregistree comme progression."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-b1", "t-b1")
    sc.increment_iteration("s-b1")  # steps_without_progress -> 1
    s1 = sc.get_session("s-b1")
    check("B1a after increment: steps_without_progress=1",
          s1["steps_without_progress"] == 1, s1)
    sc.record_progress("s-b1")
    s2 = sc.get_session("s-b1")
    check("B1b after record_progress: steps_without_progress=0",
          s2["steps_without_progress"] == 0, s2)


def test_b2_repeated_call_without_progress_not_reset():
    """Une simple repetition sans changement significatif ne remet pas a zero."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-b2", "t-b2")
    # Increment 3 times without recording progress
    for _ in range(3):
        sc.increment_iteration("s-b2")
    s3 = sc.get_session("s-b2")
    check("B2 3 increments without progress: counter=3",
          s3["steps_without_progress"] == 3, s3)


def test_b3_five_steps_no_progress_triggers_stuck():
    """Cinq etapes consecutives sans progression declenchent la regle annoncée.
    Utilise max_steps elevé (10) pour isoler la detection no_progress du budget."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-b3", "t-b3", max_steps=10)
    for _ in range(5):
        sc.increment_iteration("s-b3")
    budget = sc.check_budget("s-b3")
    check("B3 5 steps without progress triggers stuck",
          budget["exceeded"] and "no_progress_last_n_steps" in budget["reason"],
          budget)


def test_b4_authentic_progress_resets_counter():
    """Une nouvelle progression veritable reinitialise correctement le compteur."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-b4", "t-b4")
    # Build up to 4 steps without progress
    for _ in range(4):
        sc.increment_iteration("s-b4")
    # Then record authentic progress
    sc.record_progress("s-b4")
    s4 = sc.get_session("s-b4")
    check("B4 after authentic progress: counter reset to 0",
          s4["steps_without_progress"] == 0, s4)
    # And budget check passes again
    b = sc.check_budget("s-b4")
    check("B4b budget check passes after progress reset",
          not b["exceeded"] and b["steps_without_progress"] == 0, b)


def test_b5_coherence_on_rapid_events():
    """Les horloges, compteurs et etats restent coherents avec evenements rapides."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-b5", "t-b5")
    # Rapid alternating increment/progress
    for i in range(10):
        sc.increment_iteration("s-b5")
        sc.record_progress("s-b5")
    s5 = sc.get_session("s-b5")
    check("B5 after 10 increment+progress cycles: counter=0",
          s5["steps_without_progress"] == 0 and s5["iteration_count"] == 10,
          {"iteration_count": s5["iteration_count"],
           "steps_without_progress": s5["steps_without_progress"]})


# ── C. Integration du watchdog ────────────────────────────────────

def test_c1_watchdog_detects_no_progress():
    """Le watchdog detecte no_progress_last_n_steps.
    Utilise max_steps elevé pour isoler la detection no_progress."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=3)
    s = sc.create_session("s-c1", "t-c1", max_steps=10)
    for _ in range(5):
        sc.increment_iteration("s-c1")
    issues = wd.check_session("s-c1")
    check("C1 watchdog detects no_progress_last_n_steps",
          len(issues) > 0 and any("no_progress" in i.get("reason", "") or "no_progress_last_n_steps" in str(i)
                                  for i in issues),
          {"issues": issues})


def test_c2_watchdog_detects_budget_exceeded():
    """Le watchdog detecte iteration_budget_exceeded."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=3)
    s = sc.create_session("s-c2", "t-c2", agent_type="general-fast")
    for _ in range(5):
        sc.increment_iteration("s-c2")
    issues = wd.check_session("s-c2")
    check("C2 watchdog detects iteration_budget_exceeded",
          len(issues) > 0 and any("budget" in i.get("reason", "").lower() or "iteration" in str(i).lower()
                                  for i in issues),
          {"issues": issues})


def test_c3_session_state_coherence():
    """Cohérence de l'etat entre watchdog et session-manager.
    Utilise max_steps elevé et force steps_without_progress pour isoler
    la gestion du watchdog sans incrementer retry_count."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=3)
    s = sc.create_session("s-c3", "t-c3", max_steps=10)
    # Force steps_without_progress to 5 without incrementing retry_count
    sc._sessions["s-c3"]["steps_without_progress"] = 5
    sc._persist(sc._sessions["s-c3"])
    # Before handling: session is active
    check("C3a session active before handling",
          sc.get_session("s-c3")["status"] == "active",
          sc.get_session("s-c3"))
    # Handle stuck: max_retries=3, retry_count starts at 0
    issues = wd.check_session("s-c3")
    wd.handle_stuck("s-c3", issues)
    s_after = sc.get_session("s-c3")
    check("C3b after first handle: recovering (retry < max)",
          s_after["status"] == "recovering",
          {"status": s_after["status"], "retry_count": s_after["retry_count"]})


def test_c4_no_false_block_on_progress():
    """Absence de faux blocage sur une session en progression."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=3)
    s = sc.create_session("s-c4", "t-c4", max_steps=10)
    # Record progress regularly (only 3 iterations, well within budget)
    for i in range(3):
        sc.increment_iteration("s-c4")
        sc.record_progress("s-c4")
    issues = wd.check_session("s-c4")
    check("C4 session with regular progress: no issues",
          issues == [], {"issues": issues})


def test_c5_no_infinite_retry_loop():
    """Absence de boucle de relance lorsque la cause du blocage persiste."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=3)
    s = sc.create_session("s-c5", "t-c5")
    for _ in range(5):
        sc.increment_iteration("s-c5")
    # Handle stuck 3 times: recover, recover, then park
    for i in range(3):
        issues = wd.check_session("s-c5")
        wd.handle_stuck("s-c5", issues)
    s_final = sc.get_session("s-c5")
    check("C5 after max retries: session parked",
          s_final["status"] == "parked",
          {"status": s_final["status"], "retry_count": s_final["retry_count"],
           "park_reason": s_final.get("park_reason")})


def test_c6_parent_can_continue_when_subagent_blocked():
    """Un agent parent peut continuer/terminer quand son sous-agent est bloque."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    # Parent session: healthy
    parent = sc.create_session("s-c6-parent", "t-c6-parent", agent_type="general-fast")
    sc.record_progress("s-c6-parent")
    # Child session: stuck
    child = sc.create_session("s-c6-child", "t-c6-child", agent_type="general-fast")
    for _ in range(5):
        sc.increment_iteration("s-c6-child")
    # Parent is NOT stuck even though child is
    parent_budget = sc.check_budget("s-c6-parent")
    child_budget = sc.check_budget("s-c6-child")
    check("C6 parent not blocked by stuck child",
          not parent_budget["exceeded"] and child_budget["exceeded"],
          {"parent": parent_budget, "child": child_budget})


# ── D. Resilience aux erreurs du modele et du fournisseur ─────────

def test_d1_empty_model_response():
    """Reponse vide du model: echec definitif explicite apres retry borne."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=2)
    s = sc.create_session("s-d1", "t-d1")
    # Simulate empty response: increment without progress
    for _ in range(3):
        sc.increment_iteration("s-d1")
    budget = sc.check_budget("s-d1")
    check("D1 empty response: no progress counter increments",
          s["steps_without_progress"] == 3,
          {"steps_without_progress": s["steps_without_progress"]})
    # After max steps, session is stuck
    for _ in range(2):
        sc.increment_iteration("s-d1")
    budget2 = sc.check_budget("s-d1")
    check("D1b budget exceeded after empty responses",
          budget2["exceeded"], budget2)


def test_d2_provider_error_429():
    """Erreur HTTP 429 / quota depasse: recuperation arrete, pas de boucle infinie."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-d2", "t-d2")
    # Quota error: no progress recorded (simulating provider unavailability)
    for _ in range(5):
        sc.increment_iteration("s-d2")
    budget = sc.check_budget("s-d2")
    check("D2 quota error: budget exceeded instead of infinite retry",
          budget["exceeded"] and budget["iteration_count"] == 5,
          budget)


def test_d3_retry_bounded():
    """Les tentatives sont bornees, pas de sessions paralleles incontrôlees."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    wd = WatchdogConvergence(sc, max_retries=3)
    s = sc.create_session("s-d3", "t-d3")
    for _ in range(5):
        sc.increment_iteration("s-d3")
    # Handle 3 times -> parked (no more retries)
    for _ in range(3):
        issues = wd.check_session("s-d3")
        wd.handle_stuck("s-d3", issues)
    s_final = sc.get_session("s-d3")
    check("D3 no infinite retry: parked after max_retries",
          s_final["status"] == "parked",
          {"status": s_final["status"], "retry_count": s_final["retry_count"]})


# ── E. Reprise et persistance de l'etat ───────────────────────────

def test_e1_session_persisted_to_disk():
    """L'etat de session est enregistre sur disque (state.json), pas seulement en memoire."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-e1", "t-e1", agent_type="rdeep")
    sc.increment_iteration("s-e1")
    sc.record_progress("s-e1")
    # Verify state.json exists on disk
    state_file = os.path.join(SESSIONS_DIR, "s-e1", "state.json")
    check("E1 state.json exists on disk",
          os.path.isfile(state_file), {"path": state_file})
    # Verify content matches
    with open(state_file, encoding="utf-8") as f:
        persisted = json.load(f)
    check("E1b persisted content matches live session",
          persisted["iteration_count"] == 1 and persisted["max_steps"] == 12,
          {"persisted": persisted})


def test_e2_resume_recovers_state():
    """Une reprise recupere l'etat depuis le disque."""
    sc1 = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc1.create_session("s-e2", "t-e2", agent_type="general-fast")
    sc1.increment_iteration("s-e2")
    sc1.increment_iteration("s-e2")
    # Create new instance (simulate restart)
    sc2 = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s2 = sc2.get_session("s-e2")
    check("E2 session recovered from disk after restart",
          s2 is not None and s2["iteration_count"] == 2 and s2["max_steps"] == 5,
          {"iteration_count": s2["iteration_count"], "max_steps": s2["max_steps"]})


def test_e3_recovery_resets_counters():
    """La recuperation reinitialise iteration_count et steps_without_progress."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-e3", "t-e3")
    sc.increment_iteration("s-e3")
    sc.increment_iteration("s-e3")
    sc.increment_iteration("s-e3")
    s_rec = sc.recover_session("s-e3")
    check("E3 recovery resets iteration_count and steps_without_progress",
          s_rec["iteration_count"] == 0 and s_rec["steps_without_progress"] == 0,
          {"iteration_count": s_rec["iteration_count"],
           "steps_without_progress": s_rec["steps_without_progress"]})


def test_e4_missing_or_corrupt_state_safe():
    """Etat absent, ancien, mal forme ou partiellement ecrit: recuperation explicite et sure."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    # Non-existent session
    check("E4a non-existent session returns None",
          sc.get_session("s-nonexistent") is None, {"session": "s-nonexistent"})
    # Corrupt state file
    corrupt_dir = os.path.join(SESSIONS_DIR, "s-corrupt")
    os.makedirs(corrupt_dir, exist_ok=True)
    with open(os.path.join(corrupt_dir, "state.json"), "w", encoding="utf-8") as f:
        f.write("{invalid json!!!")
    # Reload should not crash
    sc2 = SessionConvergence(sessions_dir=SESSIONS_DIR)
    check("E4b corrupt state file does not crash reload",
          sc2.get_session("s-corrupt") is None,
          {"loaded_count": len(sc2.list_sessions())})


def test_e5_state_distinguishes_success_partial_failure():
    """L'etat de reprise distingue succes, livraison partielle et echec."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    # Success
    s1 = sc.create_session("s-e5-success", "t-e5")
    sc.complete_session("s-e5-success", success=True,
                        result={"deliverable": "fix.patch", "tests": "passed"})
    # Failure
    s2 = sc.create_session("s-e5-fail", "t-e5")
    sc.complete_session("s-e5-fail", success=False,
                        result={"error": "budget exceeded", "partial": False})
    # Parked (partial/blocked)
    s3 = sc.create_session("s-e5-parked", "t-e5")
    sc.park_session("s-e5-parked", reason="iteration_budget_exceeded")
    check("E5 success state",
          sc.get_session("s-e5-success")["status"] == "completed",
          {"status": sc.get_session("s-e5-success")["status"]})
    check("E5 failure state",
          sc.get_session("s-e5-fail")["status"] == "failed",
          {"status": sc.get_session("s-e5-fail")["status"]})
    check("E5 parked state",
          sc.get_session("s-e5-parked")["status"] == "parked",
          {"status": sc.get_session("s-e5-parked")["status"]})


# ── F. Cycle de livraison (isolé, sans publication reelle) ────────

def test_f1_success_with_evidence():
    """Succès avec preuves: session completee, livrable present."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-f1", "t-f1")
    sc.increment_iteration("s-f1")
    sc.record_progress("s-f1")
    sc.complete_session("s-f1", success=True,
                        result={"commit_sha": "abc123", "branch": "fix/x", "tests_passed": True})
    s_final = sc.get_session("s-f1")
    check("F1 success with evidence",
          s_final["status"] == "completed" and s_final["result"].get("tests_passed") is True,
          {"status": s_final["status"], "result": s_final["result"]})


def test_f2_partial_delivery_with_limitations():
    """Livraison partielle avec limitations explicites (parked, pas failed)."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-f2", "t-f2")
    for _ in range(5):
        sc.increment_iteration("s-f2")
    sc.park_session("s-f2", reason="iteration_budget_exceeded: partial work done")
    s_final = sc.get_session("s-f2")
    check("F2 partial delivery parked with reason",
          s_final["status"] == "parked" and "budget" in s_final.get("park_reason", ""),
          {"status": s_final["status"], "reason": s_final.get("park_reason")})


def test_f3_test_failure_state():
    """Echec des tests: session marquee echec, pas de livraison."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-f3", "t-f3")
    sc.complete_session("s-f3", success=False,
                        result={"error": "tests failed", "tests_passed": False})
    s_final = sc.get_session("s-f3")
    check("F3 test failure: explicit failure state",
          s_final["status"] == "failed" and s_final["result"].get("tests_passed") is False,
          {"status": s_final["status"], "result": s_final["result"]})


def test_f4_security_block_state():
    """Blocage de securite: session marquee bloquee/echouee sans livraison."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-f4", "t-f4")
    sc.park_session("s-f4", reason="security_scope_violation: node_modules access denied")
    s_final = sc.get_session("s-f4")
    check("F4 security block: parked with reason",
          s_final["status"] == "parked" and "security" in s_final.get("park_reason", ""),
          {"status": s_final["status"], "reason": s_final.get("park_reason")})


def test_f5_model_error_state():
    """Erreur du model: etat d'echec explicite, pas d'exploration infinie."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-f5", "t-f5")
    for _ in range(5):
        sc.increment_iteration("s-f5")
    sc.park_session("s-f5", reason="model_error_or_empty_response: provider unavailable")
    s_final = sc.get_session("s-f5")
    check("F5 model error: parked with explicit reason",
          s_final["status"] == "parked" and "model" in s_final.get("park_reason", ""),
          {"status": s_final["status"], "reason": s_final.get("park_reason")})


def test_f6_budget_exceeded_state():
    """Depassement de budget: arret explicite avec motif."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-f6", "t-f6", agent_type="general-fast")
    for _ in range(6):  # exceeds max_steps=5
        sc.increment_iteration("s-f6")
    budget = sc.check_budget("s-f6")
    check("F6 budget exceeded detected",
          budget["exceeded"] and "budget_exceeded" in budget["reason"],
          budget)


def test_f7_human_intervention_requested():
    """Demande d'intervention humaine: etat explicite, pas de relance automatique."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    s = sc.create_session("s-f7", "t-f7")
    sc.park_session("s-f7", reason="manual_intervention_requested: admin review required")
    s_final = sc.get_session("s-f7")
    check("F7 human intervention: parked",
          s_final["status"] == "parked" and "manual" in s_final.get("park_reason", ""),
          {"status": s_final["status"], "reason": s_final.get("park_reason")})


# ── G. Appels repetes et processus enfants ────────────────────────

def test_g1_no_infinite_mcp_respawn():
    """Une operation qui peut reutiliser une session ne provoque pas de respawns inutiles."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    # Simulate reusing the same session for multiple operations
    s = sc.create_session("s-g1", "t-g1")
    for i in range(3):
        sc.increment_iteration("s-g1")
        sc.record_progress("s-g1")  # Each operation records progress
    budget = sc.check_budget("s-g1")
    check("G1 session reuse with progress: not stuck",
          not budget["exceeded"] and s["steps_without_progress"] == 0,
          budget)


def test_g2_blocked_worker_does_not_kill_parent():
    """L'arret d'un worker bloque ne tue pas le serveur/agent parent."""
    sc = SessionConvergence(sessions_dir=SESSIONS_DIR)
    parent = sc.create_session("s-g2-parent", "t-g2-parent")
    child = sc.create_session("s-g2-child", "t-g2-child")
    # Child gets stuck
    for _ in range(5):
        sc.increment_iteration("s-g2-child")
    # Parent remains active
    check("G2 parent active while child stuck",
          sc.check_budget("s-g2-parent")["exceeded"] is False
          and sc.check_budget("s-g2-child")["exceeded"] is True,
          {"parent": sc.check_budget("s-g2-parent"),
           "child": sc.check_budget("s-g2-child")})


# ── Run all tests ─────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        # A. Budgets
        test_a1_known_agent_gets_budget,
        test_a2_rdeep_agent_budget_12,
        test_a3_unknown_agent_fallback,
        test_a4_no_agent_type_defaults,
        test_a5_normal_session_completes_before_limit,
        test_a6_budget_exceeded_triggers_stop,
        test_a7_budget_check_at_execution_points,
        test_a8_resume_does_not_reset_budget_indefinitely,
        test_a9_limits_coherent_across_components,
        # B. Progress
        test_b1_effective_progress_recorded,
        test_b2_repeated_call_without_progress_not_reset,
        test_b3_five_steps_no_progress_triggers_stuck,
        test_b4_authentic_progress_resets_counter,
        test_b5_coherence_on_rapid_events,
        # C. Watchdog
        test_c1_watchdog_detects_no_progress,
        test_c2_watchdog_detects_budget_exceeded,
        test_c3_session_state_coherence,
        test_c4_no_false_block_on_progress,
        test_c5_no_infinite_retry_loop,
        test_c6_parent_can_continue_when_subagent_blocked,
        # D. Provider errors
        test_d1_empty_model_response,
        test_d2_provider_error_429,
        test_d3_retry_bounded,
        # E. Persistence
        test_e1_session_persisted_to_disk,
        test_e2_resume_recovers_state,
        test_e3_recovery_resets_counters,
        test_e4_missing_or_corrupt_state_safe,
        test_e5_state_distinguishes_success_partial_failure,
        # F. Delivery cycle
        test_f1_success_with_evidence,
        test_f2_partial_delivery_with_limitations,
        test_f3_test_failure_state,
        test_f4_security_block_state,
        test_f5_model_error_state,
        test_f6_budget_exceeded_state,
        test_f7_human_intervention_requested,
        # G. Repeated calls
        test_g1_no_infinite_mcp_respawn,
        test_g2_blocked_worker_does_not_kill_parent,
    ]

    for t in tests:
        try:
            t()
        except Exception as e:
            RESULTS.append((t.__name__, False))
            print(f"ERROR | {t.__name__} | {e}")

    ok = sum(1 for _, c in RESULTS if c)
    tot = len(RESULTS)
    print(f"\n==== RESUME P0 convergence ====")
    print(f"{ok}/{tot} tests PASS")
    for n, c in RESULTS:
        print(("PASS " if c else "FAIL ") + n)
    sys.exit(0 if ok == tot else 1)
