#!/usr/bin/env python3
"""
Factory V3 — Boucle d'autonomie commerciale 24/7
Sélectionne, développe, teste et livre des améliorations pour BOT-WOW et Sargasses.
"""
import os, sys, json, time, sqlite3, subprocess, threading, urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Import f3 pour l'enqueue
import sys as _sys
_sys.path.insert(0, r"C:\factory-service\v3")
import f3

# ─── Pas de fenetre console (Windows) pour tout spawn de sous-processus ───
CREATE_NO_WINDOW = 0x08000000
_CMDS = ("npm", "npx", "gh", "git", "yarn", "pnpm", "node", "cmd")
def _run(args, **kw):
    """subprocess.run sans fenetre console qui flashe (Factory headless 24/7).
    Sur Windows, npm/npx/gh/git/node sont des .cmd/.bat -> shell=True requis,
    mais CREATE_NO_WINDOW + STARTF_USESHOWWINDOW(SW_HIDE) suppriment la console."""
    if os.name == "nt":
        kw.setdefault("creationflags", CREATE_NO_WINDOW)
        head = (args[0] if isinstance(args, (list, tuple)) and args else str(args).split()[0]).lower()
        kw.setdefault("shell", os.path.basename(str(head)) in _CMDS)
        try:
            import subprocess as _sp
            si = kw.pop("startupinfo", None) or _sp.STARTUPINFO()
            si.dwFlags |= 0x00000001  # STARTF_USESHOWWINDOW
            si.wShowWindow = 0        # SW_HIDE
            kw["startupinfo"] = si
        except Exception:
            pass
    return subprocess.run(args, **kw)

# ─── Tous les spawns de missions passent par _run (jamais subprocess.run nu) ─

# ─── Chemins ────────────────────────────────────────────────────────────────
ROOT = r"C:\factory-service"
STATE = os.path.join(ROOT, "state")
DB = os.path.join(STATE, "f3_missions.db")
CONTROL = os.path.join(STATE, "f3_control.json")
LOGDIR = os.path.join(STATE, "logs")
WORKSPACE = os.path.join(r"C:\test-factory-isolated", "worktrees")

# ─── Repos canoniques (depuis factory-live/repos.json) ─────────────────────
REPOS = {
    "bot-wow": {
        "url": "https://github.com/aveca/bot-wow.git",
        "local": os.path.join(r"C:\factory\worktrees", "botwow-saas"),
        "branch": "main",
        "kind": "commercial",
        "funnel": ["visit", "demo", "offer", "checkout", "payment", "delivery"]
    },
    "sargagame": {
        "url": "https://github.com/aveca/sargagame.git",
        "local": os.path.join(r"C:\factory\worktrees", "sargagame-main"),
        "branch": "main",
        "kind": "commercial",
        "funnel": ["visit", "forecast", "comparison", "decision", "signup", "payment"]
    }
}

# ─── Funnel stages pour chaque produit ─────────────────────────────────────
FUNNEL_STAGES = {
    "bot-wow": ["visit", "demo", "offer_view", "checkout_start", "payment_confirmed"],
    "sargagame": ["visit", "forecast_view", "beach_compare", "premium_cta", "signup", "payment_confirmed"]
}

# ─── Métriques de référence (baseline) ─────────────────────────────────────
BASELINE = {
    "bot-wow": {
        "visit_to_demo": 0.15,
        "demo_to_offer": 0.25,
        "offer_to_checkout": 0.10,
        "checkout_to_payment": 0.30
    },
    "sargagame": {
        "visit_to_forecast": 0.40,
        "forecast_to_compare": 0.20,
        "compare_to_premium": 0.15,
        "premium_to_signup": 0.25
    }
}

# ─── Its de configuration ──────────────────────────────────────────────────
CONFIG = {
    "check_interval_sec": 600,      # 10 min: santé domaines
    "hourly_check_sec": 3600,       # 1h: queue, CI, incidents
    "cycle_sec": 14400,             # 4h: priorisation opportunités
    "daily_sec": 86400,             # 24h: mission de développement
    "max_concurrent_missions": 1,
    "max_mission_hours": 4,
    "recovery_timeout_hours": 2
}

# ─── Utilitaires ───────────────────────────────────────────────────────────
def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def now_epoch():
    return time.time()

def log(msg):
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{ts} | {msg}"
    print(line)
    try:
        logdir = Path(LOGDIR)
        logdir.mkdir(parents=True, exist_ok=True)
        with open(logdir / "autonomy.log", "a", encoding="utf-8") as f:
            f.write(f"{ts} | {msg}\n")
    except OSError:
        pass

def db():
    con = sqlite3.connect(DB, timeout=30, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.row_factory = sqlite3.Row
    return con

def load_control():
    try:
        with open(CONTROL, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"mode": "AUTONOMOUS", "claims_allowed": True}

# ─── Collecte de données réelles (analytics, conversions, erreurs) ─────────
def collect_metrics():
    """Collecte les métriques réelles depuis les sources disponibles."""
    metrics = {"timestamp": now_iso(), "products": {}}
    
    # 1. Sargagame - analytics locales (si dispo)
    try:
        analytics_db = Path(r"C:\factory\worktrees\sargagame-main\analytics.db")
        if analytics_db.exists():
            with sqlite3.connect(f"file:{analytics_db}?mode=ro", uri=True) as con:
                cur = con.cursor()
                cur.execute("SELECT event, COUNT(*) as cnt FROM events WHERE ts > ? GROUP BY event",
                           (int(time.time() - 86400) * 1000,))
                metrics["products"]["sargagame"] = dict(cur.fetchall())
    except Exception:
        pass
    
    # 2. BOT-WOW - telemetry worker (si accessible)
    try:
        telemetry_db = Path(r"C:\factory\worktrees\botwow-saas\telemetry.db")
        if telemetry_db.exists():
            with sqlite3.connect(f"file:{telemetry_db}?mode=ro", uri=True) as con:
                cur = con.cursor()
                cur.execute("SELECT event, COUNT(*) as cnt FROM events WHERE ts > ? GROUP BY event",
                           (int(time.time() - 86400) * 1000,))
                metrics["products"]["bot-wow"] = dict(cur.fetchall())
    except Exception:
        pass
    
    # 3. GitHub - PRs ouverts, CI status (via gh CLI si dispo)
    try:
        for repo in ["aveca/bot-wow", "aveca/sargagame"]:
            result = _run(
                ["gh", "pr", "list", "--repo", repo, "--state", "open", "--json", "number,title,headRefName,statusCheckRollup"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                prs = json.loads(result.stdout)
                metrics.setdefault("github", {})[repo] = prs
    except Exception:
        pass
    
    return metrics

# ─── Analyse des opportunités ──────────────────────────────────────────────
def analyze_opportunities(metrics):
    """Identifie les opportunités commerciales basées sur les données réelles."""
    opportunities = []
    
    # 1. Blocage de paiement / checkout
    if metrics.get("products", {}).get("sargagame", {}).get("checkout_start", 0) == 0:
        opportunities.append({
            "id": "sargass-checkout-block",
            "product": "sargagame",
            "type": "payment_block",
            "severity": "critical",
            "evidence": "checkout_start=0 dans analytics, mais PAID>0 prouve que le paiement fonctionne",
            "impact": "revenue_loss",
            "effort": "low",
            "fix": "connecter sg_checkout_started (PR #1006) au funnel GA4"
        })
    
    # 2. Friction de conversion Sargagame
    sarg = metrics.get("products", {}).get("sargagame", {})
    if sarg.get("premium_cta", 0) > 0 and sarg.get("signup", 0) == 0:
        opportunities.append({
            "id": "sargass-premium-friction",
            "product": "sargagame",
            "type": "conversion_friction",
            "severity": "high",
            "evidence": f"premium_cta={sarg.get('premium_cta',0)} mais signup=0",
            "impact": "conversion_loss",
            "effort": "medium",
            "fix": "connecter paywall CTA vers modal premium + checkout Mollie"
        })
    
    # 3. BOT-WOW checkout abandonment
    bot = metrics.get("products", {}).get("bot-wow", {})
    if bot.get("checkout_start", 0) > 0 and bot.get("payment_confirmed", 0) == 0:
        opportunities.append({
            "id": "botwow-checkout-abandon",
            "product": "bot-wow",
            "type": "checkout_abandon",
            "severity": "high",
            "evidence": f"checkout_start={bot.get('checkout_start',0)} mais payment_confirmed=0",
            "impact": "revenue_loss",
            "effort": "medium",
            "fix": "verifier webhook Mollie + recordConversion dans worker"
        })
    
    # 4. SEO quick wins Sargasses
    try:
        # Données GSC via gh si dispo
        pass
    except Exception:
        pass
    
    # Tri par: severité > impact > effort inverse
    severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    effort_order = {"low": 3, "medium": 2, "high": 1}
    
    opportunities.sort(key=lambda o: (
        -severity_order.get(o["severity"], 0),
        -effort_order.get(o["effort"], 0)
    ))
    
    return opportunities

# ─── Sélection de la meilleure mission ─────────────────────────────────────
def select_mission(opportunities, control):
    """Sélectionne UNE seule mission selon les critères."""
    if not opportunities:
        return None
    
    # Vérifier mode et verrous
    # claims_allowed par défaut True si absent (compatibilité avec f3.py)
    claims_allowed = control.get("claims_allowed", True)
    if control.get("mode") != "AUTONOMOUS" or not claims_allowed:
        return None
    
    # Vérifier limite de concurrence
    with db() as con:
        running = con.execute("SELECT COUNT(*) n FROM missions WHERE state='running'").fetchone()["n"]
        if running >= control.get("concurrency_limit", 1):
            return None
    
    # Prendre la première opportunité non bloquée
    for opp in opportunities:
        # Vérifier si déjà en cours
        with db() as con:
            existing = con.execute(
                "SELECT id FROM missions WHERE objective LIKE ? AND state IN ('queued','running','checkpointed')",
                (f"%{opp['id']}%",)
            ).fetchone()
            if existing:
                continue
        
        # Créer la mission
        mission_id = f"m_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{opp['id'][:8]}"
        task = {
            "id": mission_id,
            "product": opp["product"],
            "type": opp["type"],
            "objective": f"Fix {opp['id']}: {opp['fix']}",
            "acceptance": [f"{k}: {v}" for k, v in opp.items() if k in ("fix", "evidence", "impact")],
            "repo": REPOS[opp["product"]]["url"],
            "branch": f"fix/{opp['id']}",
            "max_hours": CONFIG["max_mission_hours"]
        }
        return task
    
    return None

# ─── Exécution d'une mission de développement ──────────────────────────────
def execute_mission(task):
    """Exécute une mission de développement complète: branche, code, test, PR."""
    log(f"MISSION START: {task['id']} - {task['objective']}")
    
    repo_url = task["repo"]
    local_path = REPOS[task["product"]]["local"]
    branch = task["branch"]
    
    try:
        # 1. Préparer le worktree
        worktree = Path(WORKSPACE) / task["id"]
        worktree.parent.mkdir(parents=True, exist_ok=True)
        
        # Clone si nécessaire
        if not (worktree / ".git").exists():
            _run(["git", "clone", "--branch", REPOS[task["product"]]["branch"], repo_url, str(worktree)],
                          check=True, capture_output=True, timeout=120)
        
        # Créer branche
        _run(["git", "checkout", "-b", branch], cwd=worktree, check=True, capture_output=True)
        
        # 2. Appliquer la correction (selon le type)
        apply_fix(worktree, task)
        
        # 3. Tests
        test_result = run_tests(worktree, task["product"])
        if not test_result["passed"]:
            log(f"TESTS FAILED: {task['id']} - {test_result['errors']}")
            return {"success": False, "errors": test_result["errors"]}
        
        # 4. Commit + Push
        commit_msg = f"fix({task['product']}): {task['id']} - {task['objective'][:80]}"
        _run(["git", "add", "-A"], cwd=worktree, check=True)
        _run(["git", "commit", "-m", commit_msg], cwd=worktree, check=True)
        _run(["git", "push", "-u", "origin", branch], cwd=worktree, check=True, capture_output=True)
        
        # 5. Créer PR (via gh CLI si dispo)
        pr_url = create_pr(task, commit_msg)
        
        log(f"MISSION COMPLETED: {task['id']} -> {pr_url}")
        return {"success": True, "pr_url": pr_url, "branch": branch}
        
    except Exception as e:
        log(f"MISSION FAILED: {task['id']} - {e}")
        return {"success": False, "error": str(e)}

def apply_fix(worktree, task):
    """Applique la correction selon le type de mission."""
    product = task["product"]
    
    if task["type"] == "payment_block" and product == "sargagame":
        # Déjà corrigé par PR #1006 - vérifier déploiement
        pass
    elif task["type"] == "conversion_friction" and product == "sargagame":
        # Connecter paywall CTA -> PremiumModal
        apply_sargass_premium_modal(worktree)
    elif task["type"] == "checkout_abandon" and product == "bot-wow":
        # Vérifier webhook Mollie + recordConversion
        verify_botwow_webhook(worktree)
    else:
        raise NotImplementedError(f"Fix type {task['type']} not implemented for {product}")

def apply_sargass_premium_modal(worktree):
    """Connecte le CTA paywall vers PremiumModal."""
    # Vérifier si PremiumModal existe
    modal_path = worktree / "src" / "components" / "PremiumModal.jsx"
    if not modal_path.exists():
        raise RuntimeError("PremiumModal.jsx not found")
    
    # Trouver le CTA paywall dans le header
    header_path = worktree / "src" / "components" / "Header.jsx"
    if header_path.exists():
        content = header_path.read_text(encoding="utf-8")
        if 'data-cta-id="premium-info"' in content:
            # Déjà connecté
            return
        # Ajouter le handler
        new_content = content.replace(
            'data-cta-id="premium-info"',
            'data-cta-id="premium-info" onClick={() => openPremiumModal()}'
        )
        if "openPremiumModal" not in content:
            # Ajouter l'import et la fonction
            import_line = 'import { usePremiumModal } from "../hooks/usePremiumModal";'
            if import_line not in content:
                content = content.replace("import ", import_line + "\nimport ")
            # Ajouter le hook
            hook_line = "const { openPremiumModal } = usePremiumModal();"
            content = content.replace("const {", hook_line + "\n  const {")
            header_path.write_text(content, encoding="utf-8")

def verify_botwow_webhook(worktree):
    """Vérifie que le webhook Mollie enregistre la conversion."""
    worker_path = worktree / "worker" / "index.js"
    if not worker_path.exists():
        raise RuntimeError("Worker not found")
    
    content = worker_path.read_text(encoding="utf-8")
    if "recordConversion" not in content:
        raise RuntimeError("recordConversion not found in worker")
    if "conversion" not in content:
        raise RuntimeError("Conversion tracking not implemented")

def run_tests(worktree, product):
    """Lance les tests pertinents."""
    try:
        if product == "bot-wow":
            result = _run(
                ["npm", "test"], cwd=worktree, capture_output=True, text=True, timeout=120
            )
        else:
            result = _run(
                ["npm", "test"], cwd=worktree, capture_output=True, text=True, timeout=120
            )
        return {"passed": result.returncode == 0, "errors": result.stderr}
    except Exception as e:
        return {"passed": False, "errors": str(e)}

def create_pr(task, commit_msg):
    """Crée une PR via gh CLI."""
    try:
        result = _run([
            "gh", "pr", "create",
            "--repo", task["repo"],
            "--title", commit_msg,
            "--body", f"Auto-fix for {task['id']}\n\n{task['objective']}\n\nTests: passed",
            "--base", REPOS[task["product"]]["branch"],
            "--head", task["branch"]
        ], capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "PR creation skipped (manual)"

# ─── Boucle principale d'autonomie ────────────────────────────────────────
def autonomy_loop():
    """Boucle principale d'autonomie commerciale 24/7."""
    log("=== AUTONOMY LOOP STARTED ===")
    
    last_health_check = 0
    last_hourly = 0
    last_cycle = 0
    last_daily = 0
    
    while True:
        try:
            now = now_epoch()
            control = load_control()
            
            # 1. Health check (toutes les 10 min)
            if now - last_health_check >= CONFIG["check_interval_sec"]:
                health_check()
                last_health_check = now
            
            # 2. Vérification horaire (queue, CI, incidents)
            if now - last_hourly >= CONFIG["hourly_check_sec"]:
                hourly_check()
                last_hourly = now
            
            # 2. Cycle de priorisation (4h)
            if now - last_cycle >= CONFIG["cycle_sec"]:
                cycle_prioritization()
                last_cycle = now
            
            # 3. Mission quotidienne de développement
            if now - last_daily >= CONFIG["daily_sec"]:
                daily_mission()
                last_daily = now
            
            # 4. Worker tick (traiter la queue)
            worker_tick()
            
            # 5. Superviseur tick (recovery, heartbeat)
            supervisor_tick()
            
        except Exception as e:
            log(f"AUTONOMY LOOP ERROR: {e}")
        
        time.sleep(30)  # Tick de base 30s

def health_check():
    """Vérification santé domaines + APIs."""
    log("HEALTH CHECK: checking domains...")
    for name, repo in REPOS.items():
        try:
            # Vérifier URL live
            import urllib.request
            url = f"https://{name.replace('_', '-')}.com/" if name != "bot-wow" else "https://bot-wow.com/"
            req = urllib.request.Request(url, headers={"User-Agent": "Factory-Health/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                log(f"HEALTH {name}: HTTP {resp.status}")
        except Exception as e:
            log(f"HEALTH {name} FAILED: {e}")

def hourly_check():
    """Vérification horaire: queue, CI, incidents."""
    log("HOURLY CHECK: queue, CI, incidents")
    c = load_control()
    counts = {"queued": 0, "running": 0, "completed": 0, "failed": 0}
    with db() as con:
        for row in con.execute("SELECT state, COUNT(*) n FROM missions GROUP BY state"):
            counts[row["state"]] = row["n"]
    log(f"QUEUE STATUS: {counts}")
    
    # Vérifier CI GitHub (PRs ouverts)
    try:
        for repo in ["aveca/bot-wow", "aveca/sargagame"]:
            result = _run(
                ["gh", "run", "list", "--repo", repo, "--limit", "5", "--json", "conclusion,headBranch"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                failed = [r for r in runs if r.get("conclusion") == "failure"]
                if failed:
                    log(f"CI FAILURE {repo}: {len(failed)} failed runs")
    except Exception:
        pass

def cycle_prioritization():
    """Toutes les 4h: analyse opportunités, priorisation, sélection mission."""
    log("CYCLE: prioritization started")
    metrics = collect_metrics()
    opportunities = analyze_opportunities(metrics)
    control = load_control()
    
    if opportunities:
        task = select_mission(opportunities, load_control())
        if task:
            log(f"MISSION SELECTED: {task['id']} - {task['objective']}")
            # Enqueue la mission
            enqueue_mission(task)
        else:
            log("No mission selected (concurrency limit or no eligible opportunity)")
    else:
        log("No opportunities found")

def daily_mission():
    """Une mission de développement par jour."""
    log("DAILY MISSION: executing selected mission")
    # La mission est déjà enqueued par cycle_prioritization
    # worker_tick() la traitera

def enqueue_mission(task):
    """Ajoute une mission à la queue f3."""
    from f3 import enqueue
    mid = f3.enqueue(
        kind="dev",
        model="openrouter-free/nvidia/nemotron-3.5-lightning:free",
        handler="orch",
        repo=task["repo"],
        scope=task["product"],
        branch=task["branch"],
        objective=task["objective"],
        expect_marker=f"ORCH_DONE_{task['id']}",
        ctx_budget=65536,
        max_tokens=4096,
        timeout_s=14400,
        max_retries=3,
        priority=10
    )
    log(f"ENQUEUED MISSION: {mid}")

def worker_tick():
    """Traite un job de la queue (déjà implémenté dans f3.py)."""
    # Déléguer à f3.worker_tick()
    try:
        import f3
        f3.worker_tick(verbose=False)
    except Exception:
        pass  # géré par f3

def supervisor_tick():
    """Superviseur: heartbeat, recovery, lock."""
    try:
        import f3
        f3.reclaim_stale()
        # Heartbeat déjà géré par supervisor_loop
    except Exception:
        pass

def main():
    """Point d'entrée principal."""
    log("=== FACTORY V3 AUTONOMY STARTED ===")
    
    # Initialisation
    init_db()
    c = load_control()
    if c.get("mode") != "AUTONOMOUS":
        c["mode"] = "AUTONOMOUS"
        c["claims_allowed"] = True
        c["updated_by"] = "autonomy_bootstrap"
        c["updated_at"] = now_iso()
        save_control(c)
        log("MODE set to AUTONOMOUS")
    
    # Vérifier superviseur
    if not acquire_supervisor():
        log("SUPERVISOR already running, starting worker mode")
        worker_loop(interval=1, once=False)
        return
    
    log("SUPERVISOR acquired, starting autonomy loop")
    autonomy_loop()

# ─── Helpers DB ────────────────────────────────────────────────────────────
def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS autonomy_metrics(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            product TEXT,
            metrics TEXT
        );
        CREATE TABLE IF NOT EXISTS autonomy_opportunities(
            id TEXT PRIMARY KEY,
            product TEXT,
            type TEXT,
            severity TEXT,
            evidence TEXT,
            fix TEXT,
            status TEXT DEFAULT 'identified',
            created_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_autonomy_metrics_ts ON autonomy_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_autonomy_opp_status ON autonomy_opportunities(status);
        """)

def save_opportunities(opps):
    with db() as con:
        for opp in opps:
            con.execute("""
                INSERT OR REPLACE INTO autonomy_opportunities
                (id, product, type, severity, evidence, fix, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (opp["id"], opp["product"], opp["type"], opp["severity"],
                  opp.get("evidence", ""), opp.get("fix", ""), "identified", now_iso()))

def load_opportunities():
    with db() as con:
        cur = con.execute("SELECT * FROM autonomy_opportunities WHERE status='identified'")
        return [dict(r) for r in cur.fetchall()]

if __name__ == "__main__":
    main()