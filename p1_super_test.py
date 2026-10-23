import os, sys, json, time, subprocess, importlib.util, shutil
ISOL = r"C:\test-factory-isolated\f3super"
if os.path.exists(ISOL):
    shutil.rmtree(ISOL, ignore_errors=True)
os.makedirs(ISOL, exist_ok=True)
ST = os.path.join(ISOL, "state")
env = dict(os.environ)
env.update({
    "F3_ROOT": ISOL, "F3_STATE": ST, "F3_DB": os.path.join(ST, "f3_missions.db"),
    "F3_CONTROL": os.path.join(ST, "f3_control.json"), "F3_LOG": os.path.join(ST, "logs"),
    "F3_WORKSPACE": os.path.join(ISOL, "worktrees"), "F3_QUIET": "1", "F3_STEP_DELAY": "0.2",
    "F3_HB_TAKEOVER": "2",
})
os.environ.update({k: v for k, v in env.items() if k.startswith("F3_")})
spec = importlib.util.spec_from_file_location("f3", r"C:\factory-service\v3\f3.py")
f3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(f3)
f3.init_db()
c = f3.default_control(); c.update({"mode": "AUTONOMOUS", "interactive_lock": False,
    "concurrency_limit": 1, "lease_seconds": 6, "poll_seconds": 0.4, "max_retries": 5})
f3.save_control(c)
CREATE_NO_WINDOW = 0x08000000
F3PATH = r"C:\factory-service\v3\f3.py"

def start_sup(tag):
    return subprocess.Popen([sys.executable, F3PATH, "supervise", "--interval", "0.4"],
                            env=env, stdout=open(os.path.join(ISOL, tag + ".log"), "w"),
                            stderr=subprocess.STDOUT, creationflags=CREATE_NO_WINDOW)

def wait_state(mid, states, timeout):
    t = time.time() + timeout
    while time.time() < t:
        m = f3.get_mission(mid)
        if m and m["state"] in states: return m
        time.sleep(0.25)
    return f3.get_mission(mid)

RES = []
def check(n, cond, ev): RES.append((n, bool(cond))); print(("PASS" if cond else "  FAIL") + " | " + n + " | " + json.dumps(ev, default=str)[:360])

# --- 1) deux superviseurs simultanes -> un seul actif ---
ids = [f3.enqueue(kind="maintenance", handler="emit", objective=f"up-{i}", expect_marker="D") for i in range(2)]
A = start_sup("A")
for mid in ids: wait_state(mid, {"completed"}, 6)
B = start_sup("B")
time.sleep(1.2)
logtxt = open(os.path.join(ST, "logs", "f3.log"), encoding="utf-8", errors="ignore").read()
starts = logtxt.count("SUPERVISEUR start")
standby = logtxt.count("SUPERVISEUR standby")
check("superviseur: deux lances simultanement -> un seul actif (l'autre standby)",
      starts == 1 and standby >= 1 and (B.poll() is not None),
      {"SUPERVISEUR start": starts, "standby": standby, "B_retour": B.poll()})

# --- 2) crash (kill) puis reprise sans double execution ---
def count_starts():
    return open(os.path.join(ST, "logs", "f3.log"), encoding="utf-8", errors="ignore").read().count("SUPERVISEUR start")
fc = f3.load_control(); fc["lease_seconds"] = 30; f3.save_control(fc)  # bail long pour isoler le test
A.kill(); A.wait(timeout=5)   # panne brutale de l'instance active (handle relache)
time.sleep(float(env["F3_HB_TAKEOVER"]) + 0.6)   # laisse le heartbeat d'A devenir perime -> relais possible
mc = f3.enqueue(kind="dev", model="router/fast", handler="steps", objective="crash-steps", expect_marker="CRASH")
A2 = start_sup("A2")
m = wait_state(mc, {"running", "completed"}, 6)
ghost_owner = m["owner"] if m else None
check("pre-crash: mission en execution sous A2", m and m["state"] == "running" and ghost_owner, {"state": m and m["state"], "owner": ghost_owner})
A2.kill(); A2.wait(timeout=5)   # <-- PANNE SIMULEE en cours d'execution (bail de 30s encore valide)
time.sleep(float(env["F3_HB_TAKEOVER"]) + 0.6)   # le heartbeat d'A2 devient perime
starts_before = count_starts()
C = start_sup("C")              # nouveau superviseur: doit PRENDRE LE RELAIS (heartbeat perime)
time.sleep(1.2)
m = f3.get_mission(mc)
check("apres crash: nouveau superviseur prend le relais SANS re-executer (bail encore valide)",
      count_starts() > starts_before and m["state"] == "running" and m["owner"] == ghost_owner
      and not os.path.exists(os.path.join(ISOL, "worktrees", mc, "CRASH")),
      {"starts_before": starts_before, "starts_after": count_starts(), "state": m["state"],
       "owner": m["owner"], "marker_absent": not os.path.exists(os.path.join(ISOL, "worktrees", mc, "CRASH"))})
# expiration du bail -> reprise bornee, terminee UNE fois
with f3.db() as con:
    con.execute("UPDATE missions SET lease_expires_at=? WHERE id=?", (time.time() - 1, mc))
m = wait_state(mc, {"completed"}, 8)
ws_dir = os.path.join(ISOL, "worktrees", mc)
reports = [x for x in os.listdir(ws_dir) if x == "REPORT.txt"] if os.path.isdir(ws_dir) else []
check("apres expiration du bail -> reprise terminee UNE fois", m and m["state"] == "completed" and len(reports) == 1,
      {"state": m and m["state"], "attempts": m and m["attempts"], "reports": reports})

C.kill(); C.wait(timeout=5)
print("\n==== RESUME superviseur ====")
ok = sum(1 for _, x in RES if x); tot = len(RES)
for n, x in RES: print(("PASS " if x else "FAIL ") + n)
print(f"\n{ok}/{tot} tests superviseur PASS")
sys.exit(0 if ok == tot else 1)
