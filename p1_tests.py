#!/usr/bin/env python3
"""Tests d'acceptation Factory V3 (mission P1) — instance ISOLEE, donnees de test.
Ne modifie aucun projet de production. """
import os, sys, json, time, threading, importlib.util, subprocess, shutil, ctypes

ISOL = r"C:\test-factory-isolated\f3test"
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
    "F3_STEP_DELAY": "0.25",
})
F3PATH = r"C:\factory-service\v3\f3.py"
spec = importlib.util.spec_from_file_location("f3", F3PATH)
f3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f3)

RESULTS = []
def check(name, cond, ev):
    RESULTS.append((name, bool(cond)))
    print(("PASS" if cond else "  FAIL") + " | " + name + " | " + json.dumps(ev, ensure_ascii=False, default=str)[:420])

f3.init_db()
def set_ctl(**kw):
    c = f3.load_control(); c.update(kw); c["updated_by"] = "test"; c["updated_at"] = f3.now_iso(); f3.save_control(c); return c
def ws(mid): return os.path.join(ISOL, "worktrees", mid)

set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1, max_retries=5,
        lease_seconds=60, poll_seconds=1)

# ---- T1 : mise en file, execution, validation ----
m1 = f3.enqueue(kind="maintenance", model="router/fast", handler="emit", objective="T1 maintenance", expect_marker="DONE.txt")
r1 = f3.worker_tick(verbose=False)
mm = f3.get_mission(m1)
check("T1 mission en file/executee/validee",
      mm["state"] == "completed" and os.path.exists(os.path.join(ws(m1), "DONE.txt")) and os.path.exists(os.path.join(ws(m1), "REPORT.txt")),
      {"state": mm["state"], "attempts": mm["attempts"], "report": os.path.exists(os.path.join(ws(m1), "REPORT.txt"))})

# ---- T7 : echec borne par max_retries ----
set_ctl(max_retries=3)
m7 = f3.enqueue(kind="tests", model="", handler="boom", objective="T7 boom")
seq = []
for _ in range(6):
    f3.worker_tick(); mm = f3.get_mission(m7); seq.append((mm["state"], mm["attempts"]))
    if mm["state"] == "failed": break
mm = f3.get_mission(m7)
check("T7 echec termine en 'failed' apres N tentatives", mm["state"] == "failed" and mm["attempts"] >= 3, {"seq": seq, "final": mm["state"], "attempts": mm["attempts"]})

# ---- T4 : interactif bloque NOUVELLE mutation ----
set_ctl(mode="AUTONOMOUS", interactive_lock=False, max_retries=5)
m4 = f3.enqueue(kind="maintenance", model="ollama/qwen2.5-coder:7b", handler="emit", objective="T4", expect_marker="X")
set_ctl(mode="INTERACTIVE", interactive_lock=True)
r4 = f3.worker_tick(verbose=False); mm = f3.get_mission(m4)
check("T4 mode interactif bloque nouvelle mutation", mm["state"] == "queued" and r4 == "idle", {"state": mm["state"], "tick": r4})
set_ctl(mode="AUTONOMOUS", interactive_lock=False)
f3.worker_tick(); mm = f3.get_mission(m4)
check("T4b deblocage apres retour auto", mm["state"] == "completed", {"state": mm["state"]})

# ---- T5 : pause bloque, resume relance ----
set_ctl(mode="PAUSED")
m5 = f3.enqueue(kind="maintenance", model="", handler="emit", objective="T5", expect_marker="P")
r5 = f3.worker_tick(verbose=False); mm = f3.get_mission(m5)
check("T5 pause bloque execution", mm["state"] == "queued" and r5 == "idle", {"state": mm["state"], "tick": r5})
set_ctl(mode="AUTONOMOUS", interactive_lock=False); f3.worker_tick(); mm = f3.get_mission(m5)
check("T5b resume relance", mm["state"] == "completed", {"state": mm["state"]})

# ---- T2 : checkpoint + reprise apres interruption interactive (threads) ----
set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=1, max_retries=20, lease_seconds=60)
m2 = f3.enqueue(kind="dev", model="router/fast", handler="steps", objective="T2 steps", expect_marker="STEPS")
out = {}
th = threading.Thread(target=lambda: out.update(res=f3.worker_tick(verbose=False))); th.start()
time.sleep(0.7)
set_ctl(mode="INTERACTIVE", interactive_lock=True)   # retour utilisateur -> arret cooperatif
th.join(12)
mm = f3.get_mission(m2)
check("T2 checkpoint apres retour interactif", mm["state"] == "checkpointed", {"state": mm["state"], "attempts": mm["attempts"], "tick": out.get("res")})
set_ctl(mode="AUTONOMOUS", interactive_lock=False)
f3.worker_tick(); mm = f3.get_mission(m2)
check("T2b reprise complete apres auto", mm["state"] == "completed" and os.path.exists(os.path.join(ws(m2), "STEPS")), {"state": mm["state"]})

# ---- T3 : pas de double reclamation (claim atomique sous concurrence) ----
set_ctl(mode="AUTONOMOUS", interactive_lock=False, concurrency_limit=5, max_retries=50)
ids = [f3.enqueue(kind="tests", model="router/fast", handler="steps", objective=f"T3-{i}", expect_marker=f"S{i}", priority=0) for i in range(5)]
claimed = []; lk = threading.Lock(); bar = threading.Barrier(12)
def tc():
    bar.wait()
    m = f3.claim("ctx", 60)
    if m:
        with lk: claimed.append(m["id"])
ths = [threading.Thread(target=tc) for _ in range(12)]
[t.start() for t in ths]; [t.join(20) for t in ths]
uniq = len(set(claimed)); run_n = f3.counts().get("running", 0)
check("T3 aucune double reclamation de la meme mission", uniq == len(claimed) and uniq == 5, {"claimed": sorted(claimed), "uniq": uniq, "running_now": run_n})
# nettoyage controle pour la suite
with f3.db() as con:
    con.execute("UPDATE missions SET state='queued', owner=NULL, lease_expires_at=NULL WHERE state='running'")
    con.execute("DELETE FROM missions")

# ---- T8 : file vide reste inactive ----
set_ctl(mode="AUTONOMOUS", interactive_lock=False)
r8 = f3.worker_tick(verbose=False)
check("T8 file vide reste inactive", r8 == "idle" and f3.counts() == {}, {"tick": r8, "counts": f3.counts()})

# ---- T9 : aucun modele payant (refus structurel) ----
refused_model = refused_handler = False
try:
    f3.enqueue(kind="dev", model="openai/gpt-4o", handler="emit", objective="paid", expect_marker="Z")
except PermissionError:
    refused_model = True
try:
    f3.enqueue(kind="dev", model="router/fast", handler="opencode", objective="bad handler", expect_marker="Z")
except PermissionError:
    refused_handler = True
# routeur strict-free toujours en vigueur
try:
    import urllib.request
    hl = json.loads(urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=8).read().decode())
    router_ok = hl.get("openrouterFreeModel", "").endswith(":free")
except Exception as e:
    router_ok = False; hl = str(e)
check("T9 aucun modele payant (refus enqueue + handler + routeur :free)", refused_model and refused_handler and router_ok,
      {"refused_paid_model": refused_model, "refused_bad_handler": refused_handler, "router_primary_free": hl.get("openrouterFreeModel") if isinstance(hl, dict) else hl})

# ---- T10 : aucun processus/fenetre interactive non autorise ----
def pid_alive(pid):
    PROCESS_QUERY_LIMITED = 0x1000
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED, False, int(pid))
    if h: ctypes.windll.kernel32.CloseHandle(h); return True
    return False
def snap():
    n = {}
    p = subprocess.run("tasklist /fo csv /nh", capture_output=True, text=True, shell=False)
    for line in p.stdout.splitlines():
        if not line.strip(): continue
        name = line.split(",")[0].strip('"').lower()
        n[name] = n.get(name, 0) + 1
    return n
before = snap()
set_ctl(mode="AUTONOMOUS", interactive_lock=False)
mm10 = [f3.enqueue(kind="maintenance", handler="emit", objective=f"T10-{i}", expect_marker="D") for i in range(4)]
for _ in range(4): f3.worker_tick()
time.sleep(0.5)
after = snap()
console_apps = ("npx.exe", "cmd.exe", "opencode.exe", "opencode-cli.exe", "aider.exe", "conhost.exe", "pwsh.exe", "powershell.exe", "wscript.exe", "cscript.exe")
growth = {k: after.get(k, 0) - before.get(k, 0) for k in console_apps if after.get(k, 0) - before.get(k, 0) > 0}
check("T10 aucun processus console/interactif genere par l'execution autonome", growth == {}, {"growth": growth})

# ---- T6a : bail expire -> reprise (crash simule) ----
with f3.db() as con:
    con.execute("DELETE FROM missions")
set_ctl(mode="AUTONOMOUS", interactive_lock=False, max_retries=5, lease_seconds=60)
m6 = f3.enqueue(kind="maintenance", handler="emit", objective="T6", expect_marker="R")
# simule un crash: l'orphelin reste 'running' avec un bail deja expire
with f3.db() as con:
    con.execute("UPDATE missions SET state='running', owner='ghost', lease_expires_at=? WHERE id=?", (time.time() - 5, m6))
n6 = f3.reclaim_stale()
mm = f3.get_mission(m6)
check("T6a bail expire reclame -> reprise (pas de perte)", n6 == 1 and mm["state"] == "queued", {"reclaimed": n6, "state": mm["state"]})
f3.worker_tick(); mm = f3.get_mission(m6)
check("T6b reprise => complete une seule fois", mm["state"] == "completed" and os.path.exists(os.path.join(ws(m6), "R")), {"state": mm["state"]})

print("\n==== RESUME ====")
ok = sum(1 for _, c in RESULTS if c); tot = len(RESULTS)
for n, c in RESULTS:
    print(("PASS " if c else "FAIL ") + n)
print(f"\n{ok}/{tot} tests PASS")
sys.exit(0 if ok == tot else 1)
