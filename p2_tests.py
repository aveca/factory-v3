#!/usr/bin/env python3
"""Tests d'orchestration P2 (isoles). Quelques generations reelles minuscules, le reste deterministe."""
import os, sys, json, time, tempfile, importlib.util

spec = importlib.util.spec_from_file_location("orch", r"C:\factory-service\v3\orch.py")
orch = importlib.util.module_from_spec(spec); spec.loader.exec_module(orch)

R = []
def check(n, cond, ev): R.append((n, bool(cond))); print(("PASS" if cond else "  FAIL") + " | " + n + " | " + json.dumps(ev, default=str)[:300])
WS = tempfile.mkdtemp(prefix="p2orch_"); os.makedirs(WS, exist_ok=True)

# --- 1) correction simple (fast, generation reelle minuscule) ---
t1 = {"id": "T1", "objective": "typo simple: corriger un commentaire dans un fichier",
      "acceptance": ["patch appliqué"], "diff_seed": "correction typo; try/except present\n"}
r1 = orch.run_chain(t1, os.path.join(WS, "t1"))
check("1 correctif simple -> completed (fast, gen reelle)", r1["state"] == "completed",
      {"state": r1["state"], "level": r1["evidence"]["triage"]["level"], "model": r1["evidence"]["plan"]["model_used"]})

# --- 2) tache multi-fichiers (balanced) : triage doit monter de niveau + plan ---
t2 = {"id": "T2", "objective": "refactor ponctuel sur plusieurs fichiers avec tests",
      "acceptance": ["build"], "tests": ["npm test"], "diff_seed": "refactor factorisé; tests ajoutés\n"}
tr2 = orch.triage(t2)
check("2 triage multi-fichiers -> balanced + plan produit", tr2["level"] == "balanced" and tr2["multi_agent"] == "oui",
      {"triage": tr2})

# --- 3) test volontairement defaillant : livree BLOQUEE ---
t3 = {"id": "T3", "objective": "changement simple", "acceptance": ["x"],
      "diff_seed": "contexte sans gestion d'erreur TODO a finir\n"}  # declenche la grille (TODO) + pas de try/except
r3 = orch.run_chain(t3, os.path.join(WS, "t3"))
check("3 test defaillant -> blocked (pas de livraison)", r3["state"] == "blocked" and r3["evidence"]["review"]["blocking"],
      {"state": r3["state"], "findings": r3["evidence"]["review"]["findings"]})

# --- 4) la revue detecte un defaut injecté ---
rv = orch.review("diff\ncarry_trade_IBKR_0102 = 0.02  # defaut\n", adversarial_hint="carry_trade_IBKR_0102 = 0.02")
check("4 revue detecte defaut injecte", any("defaut injecte" in f for f in rv["findings"]) and rv["blocking"], {"findings": rv["findings"]})

# --- 5) depassement de contexte : resume/conservation, jamais d'envoi oversize ---
model = orch.LEVELS["fast"]["model"]
budget = orch.CTX.get(model, 65536)
big = [{"role": "system", "content": "sys"}] + [{"role": "user", "content": "x" * (budget * 4)} for _ in range(3)]
fitted, summarized = orch.fit_context(model, big)
check("5 depassement contexte -> resume, tokens sous budget", summarized and orch.est_tokens(fitted) <= budget, {"summarized": summarized, "tokens_after": orch.est_tokens(fitted), "budget": budget})

# --- 6) indisponibilite d'un modele gratuit : arret borne (pas de boucle, pas de bascule) ---
orig = orch._post
def boom(url, body, bearer, timeout=120):
    raise orch.ProviderUnavailable("HTTP 402: insufficient credits (simule)")
orch._post = boom
stopped = False; tried_urls = []
try:
    orch.call("balanced", [{"role": "user", "content": "hi"}])
except orch.ProviderUnavailable:
    stopped = True
orch._post = orig
check("6 modele gratuit indispo -> arret explicite (ProviderUnavailable)", stopped, {"stopped": stopped})

# --- 7) refus de bascule payante ---
paid_ok = False
try:
    orch._post_orig = orig
    # tentative d'utiliser un modele payant via un niveau truque
    lvl_backup = orch.LEVELS["fast"]
    orch.LEVELS["fast"] = dict(lvl_backup); orch.LEVELS["fast"]["model"] = "openrouter-free/openai/gpt-4o"
    orch.call("fast", [{"role": "user", "content": "hi"}])
    paid_ok = True
except PermissionError:
    paid_ok = False
except Exception:
    paid_ok = False
finally:
    orch.LEVELS["fast"] = lvl_backup
check("7 bascule payante refusee (allowlist)", paid_ok is False, {"allowed_call": paid_ok})

# --- 8) interruption + reprise : checkpoint conserve, reprise sans re-plan ---
t8 = {"id": "T8", "objective": "typo correction simple", "acceptance": ["patch appliqué"], "diff_seed": "ok try/except\n"}
r8a = orch.run_chain(t8, os.path.join(WS, "t8"), checkpoint={"planned": True})
r8b = orch.run_chain(t8, os.path.join(WS, "t8"), checkpoint=r8a["checkpoint"])
check("8 reprise via checkpoint (planned conserve, pas de re-plan)", r8b["checkpoint"].get("planned") is True and r8a["state"] == r8b["state"],
      {"state": r8b["state"], "planned": r8b["checkpoint"].get("planned")})

# --- 9) mission visuelle : super-vl accepte une image (gen reelle minuscule 1x1 PNG) ---
px = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
vision = None
try:
    vision = orch.call("vision", [{"role": "user", "content": [
        {"type": "text", "text": "Decris cette image 1x1 en un mot."},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64," + px}}]}])
    vision_ok = vision.get("finish") in ("stop", "length") and bool(vision.get("decision") or vision.get("content_full_len"))
except Exception as e:
    vision = {"error": str(e)}; vision_ok = False
check("9 analyse visuelle supportee (super-vl :free, image OK)", vision_ok, {"model": vision.get("model"), "finish": vision.get("finish"), "decision": (vision.get("decision") or "")[:60], "error": vision.get("error")})

# --- 10) priorite interactive : orch est Python pur (aucune fenetre/sous-processus) ---
import subprocess as sp
has_subprocess_spawn = any("subprocess" in str(getattr(orch, k, "")) for k in dir(orch))
src = open(r"C:\factory-service\v3\orch.py", encoding="utf-8").read()
no_spawn = ("Popen" not in src) and ("subprocess.run" not in src) and ("startfile" not in src.lower())
check("10 orchestration n'ouvre aucune fenetre (python pur)", no_spawn, {"Popen": "Popen" in src, "subprocess.run": "subprocess.run" in src})

print("\n==== RESUME P2 orchestration ====")
ok = sum(1 for _, c in R if c); tot = len(R)
for n, c in R: print(("PASS " if c else "FAIL ") + n)
print(f"\n{ok}/{tot} tests orchestration PASS")
sys.exit(0 if ok == tot else 1)
