#!/usr/bin/env python3
"""Integration P2: une mission 'orch' traverse la file durable/verrous de Factory V3 (P1)
et est executee par la couche de raisonnement (fast, gen reelle). Instance isolee."""
import os, json, shutil, importlib.util
ISOL = r"C:\test-factory-isolated\f3p2int"
if os.path.exists(ISOL): shutil.rmtree(ISOL, ignore_errors=True)
os.makedirs(ISOL, exist_ok=True)
ST = os.path.join(ISOL, "state")
for k, v in {"F3_ROOT": ISOL, "F3_STATE": ST, "F3_DB": os.path.join(ST, "f3_missions.db"),
             "F3_CONTROL": os.path.join(ST, "f3_control.json"), "F3_LOG": os.path.join(ST, "logs"),
             "F3_WORKSPACE": os.path.join(ISOL, "worktrees"), "F3_QUIET": "1"}.items():
    os.environ[k] = v
spec = importlib.util.spec_from_file_location("f3", r"C:\factory-service\v3\f3.py")
f3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f3)
f3.init_db()
c = f3.default_control(); c.update({"mode": "AUTONOMOUS", "interactive_lock": False, "concurrency_limit": 1,
    "max_retries": 3, "lease_seconds": 120, "poll_seconds": 1}); f3.save_control(c)

# mission refusee si modele payant (garde)
refused = False
try: f3.enqueue(kind="dev", model="openai/gpt-4o", handler="orch", objective="x", expect_marker="M")
except PermissionError: refused = True
print("paid_model_refused_in_f3:", refused)

mid = f3.enqueue(kind="maintenance", model="openrouter-free/nvidia/nemotron-3.5-lightning:free",
                 handler="orch", objective="typo simple: corriger un commentaire dans un fichier",
                 expect_marker="ORCH_DONE")
r = f3.worker_tick(verbose=False)
m = f3.get_mission(mid)
ev = {}
try: ev = json.loads(m["evidence"] or "{}")
except Exception: pass
ws = os.path.join(ISOL, "worktrees", mid)
ok = (m["state"] == "completed" and os.path.exists(os.path.join(ws, "ORCH_DONE"))
      and ev.get("triage", {}).get("level") == "fast"
      and "nemotron" in (ev.get("plan", {}).get("model_used") or ""))
print(json.dumps({
    "paid_model_refused_in_f3": refused,
    "tick": r, "state": m["state"], "attempts": m["attempts"],
    "triage_level": ev.get("triage", {}).get("level"),
    "plan_model": ev.get("plan", {}).get("model_used"),
    "review_method": ev.get("review", {}).get("method"),
    "verify_passed": ev.get("verify", {}).get("passed"),
    "marker_present": os.path.exists(os.path.join(ws, "ORCH_DONE"))
}, ensure_ascii=False, indent=2))
print("INTEGRATION_OK" if ok and refused else "INTEGRATION_FAIL")
import sys; sys.exit(0 if ok and refused else 1)
