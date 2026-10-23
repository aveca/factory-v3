#!/usr/bin/env python3
"""P3 integration: mission de niveau 'deep' traverse la file durable/verrous P1,
executee par la couche de raisonnement (deep, route verifie), relecture contradictoire,
verification, livraison. Instance isolee, aucune prod."""
import os, json, shutil, importlib.util, tempfile

# Isolation: separe sans toucher la file reale
ISOL = r"C:\test-factory-isolated\f3p3int"
if os.path.exists(ISOL):
    shutil.rmtree(ISOL, ignore_errors=True)
os.makedirs(ISOL, exist_ok=True)
ST = os.path.join(ISOL, "state")
for k, v in {
    "F3_ROOT": ISOL,
    "F3_STATE": ST,
    "F3_DB": os.path.join(ST, "f3_missions.db"),
    "F3_CONTROL": os.path.join(ST, "f3_control.json"),
    "F3_LOG": os.path.join(ST, "logs"),
    "F3_WORKSPACE": os.path.join(ISOL, "worktrees"),
    "F3_QUIET": "1",
}.items():
    os.environ[k] = v

spec = importlib.util.spec_from_file_location("f3", r"C:\factory-service\v3\f3.py")
f3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f3)
f3.init_db()

c = f3.default_control()
c.update({
    "mode": "AUTONOMOUS",
    "interactive_lock": False,
    "concurrency_limit": 1,
    "max_retries": 3,
    "lease_seconds": 120,
    "poll_seconds": 1,
})
f3.save_control(c)

# Enqueue a deep-level mission via the orch handler
mid = f3.enqueue(
    kind="dev",
    model="",  # empty model allowed for handler-level routing
    handler="orch",
    objective="debug complexe: planifier la correction d'un defaut de fuseau horaire dans 2 fichiers Python "
              "(parse + export). Revue contradictoire incluse.",
    expect_marker="ORCH_DONE"
)

r = f3.worker_tick(verbose=False)
m = f3.get_mission(mid)
ev = {}
try:
    ev = json.loads(m.get("evidence") or "{}")
except Exception:
    pass
ws = os.path.join(ISOL, "worktrees", mid)
ok = (
    m.get("state") == "completed"
    and os.path.exists(os.path.join(ws, "ORCH_DONE"))
    and ev.get("triage", {}).get("level") == "deep"
    and "nemotron-3-nano-omni" in (ev.get("plan", {}) or {}).get("model_used", "")
    and ev.get("deep_review", {}).get("verdict") in ("OK", "BLOQUANT")
    and ev.get("verify", {}).get("passed") is True
    and os.path.exists(os.path.join(ws, "patch.txt"))
)
print(json.dumps({
    "mission_state": m.get("state"),
    "triage_level": ev.get("triage", {}).get("level"),
    "plan_model": ev.get("plan", {}).get("model_used"),
    "deep_review_verdict": ev.get("deep_review", {}).get("verdict"),
    "deep_review_blocking": ev.get("deep_review", {}).get("blocking"),
    "verify_passed": ev.get("verify", {}).get("passed"),
    "marker_present": os.path.exists(os.path.join(ws, "ORCH_DONE")),
    "patch_present": os.path.exists(os.path.join(ws, "patch.txt")),
    "attempts": m.get("attempts"),
}, ensure_ascii=False, indent=2))
print("INTEGRATION_OK" if ok and m.get("state") == "completed" else "INTEGRATION_FAIL")
import sys; sys.exit(0 if ok and m.get("state") == "completed" else 1)