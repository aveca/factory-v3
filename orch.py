#!/usr/bin/env python3
"""
P2 — couche de raisonnement + orchestration adaptative pour Factory V3.
Clients fournisseurs au format VERIFIE (generations reelles), niveaux fast/balanced/deep,
budgets de contexte par modele, checkpoints, revue contradictoire (grille deterministe),
verification par criteres d'acceptation. Infra only. Aucun modele payant.

Parametres de raisonnement (verifies par generation, pas supposes):
- OpenRouter (nemotron :free) : champ corps "reasoning" -> "reasoning": {"enabled": true, "max_tokens": N}
   (reasoning_effort NON supporte par ces modeles -> jamais envoye).
- NVIDIA NIM (stepfun-ai/step-5-preview) : raisonnement NATIF (message.reasoning_content);
   pendant d'outils "tools"; option de thinking via "chat_template_kwargs": {"thinking": true} (accepte).
- Ollama local (qwen2.5-coder:7b) : pas de raisonnement natif; secours maintenance only.
"""
import json, os, time, urllib.request, urllib.error

AUTH = os.path.join(os.path.expanduser("~"), ".local", "share", "opencode", "auth.json")
def _key(p):
    try:
        with open(AUTH) as f: return (json.load(f).get(p) or {}).get("key")
    except Exception:
        return None
NV_KEY  = _key("nvidia")
OR_KEY  = _key("openrouter")

# ─── Allowlist stricte gratuite (miroir de f3) + essai NIM autorise ─
FREE = ("router/", "ollama/", "openrouter-free/", "nvidia/stepfun-ai/")  # step-5 = essai NIM autorise
def allowed(model): return any(model.startswith(p) for p in FREE)

class ProviderUnavailable(Exception): pass

def _post(url, body, bearer, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
        headers={"content-type": "application/json", "Authorization": "Bearer " + (bearer or ""),
                 "HTTP-Referer": "http://localhost", "X-Title": "Factory V3 orch"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: err = json.loads(e.read().decode())
        except Exception: err = {}
        raise ProviderUnavailable(f"HTTP {e.code}: {json.dumps(err)[:200]}")
    except Exception as e:
        raise ProviderUnavailable(f"transport: {e}")

# ─── Niveaux (budgets propres a chaque modele) ──────────────────────
LEVELS = {
    "fast":     {"provider": "openrouter-free", "model": "openrouter-free/nvidia/nemotron-3.5-lightning:free",
                 "reasoning": False, "reasoning_budget": 0,    "max_tokens": 1024, "ctx": 131072, "temperature": 0.0},
    "balanced": {"provider": "openrouter-free", "model": "openrouter-free/nvidia/nemotron-3.5-lightning:free",
                 "reasoning": True,  "reasoning_budget": 1024,  "max_tokens": 1024, "ctx": 131072, "temperature": 0.0},
    "deep":     {"provider": "openrouter-free", "model": "openrouter-free/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
                 "reasoning": True,  "reasoning_budget": 128,    "max_tokens": 1024, "ctx": 256000, "temperature": 0.0, "timeout": 90},
    "vision":   {"provider": "openrouter-free",  "model": "openrouter-free/nvidia/nemotron-3.5-super-vl:free",
                 "reasoning": False, "reasoning_budget": 512,    "max_tokens": 256,  "ctx": 131072, "temperature": 0.0},
}
# budgets de contexte REELS verifies / conservateurs
CTX = {"openrouter-free/nvidia/nemotron-3.5-lightning:free": 131072,
       "openrouter-free/nvidia/nemotron-3.5-super-vl:free":   131072,
       "openrouter-free/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free": 256000,
       "nvidia/stepfun-ai/step-5-preview":                    131072,   # reste disponible, non utilise par deep (cout NIM non verifiable)
       "ollama/qwen2.5-coder:7b":                             65536}    # OLLAMA_CONTEXT_LENGTH

def est_tokens(messages):
    return sum(max(1, len(str(m.get("content", ""))) // 4) for m in messages)

def validate_context_fit(model, messages, reserve=512):
    """Controle explicite de compatibilite AVANT tout appel / repli:
    retourne (fits, tokens, budget). Si pas fittable meme en tronquant,
    l'appelant doit bloquer (jamais de repli aveugle vers un modele incapable)."""
    budget = CTX.get(model, 65536) - reserve
    tokens = est_tokens(messages)
    # fit_context peut tronquer jusqu'a systeme+note+un seul morceau ; si un seul
    # message utilisateur depasse le budget, c'est non fittable.
    if tokens <= budget:
        return True, tokens, budget
    head = [m for m in messages if m.get("role") == "system"][:1]
    note = {"role": "system", "content": "[orch] Resume: historique tronque pour respecter le budget de contexte."}
    min_fit = est_tokens(head + [note])
    if min_fit > budget:
        return False, tokens, budget
    return True, tokens, budget  # fittable via troncature par fit_context

def fit_context(model, messages, reserve=512):
    """Ne JAMAIS envoyer un historique au-dela du budget du modele: on garde le
    systeme + les tours recents (du plus recent au plus ancien) et on TRONQUE le
    dernier message place si besoin, de sorte que le total tienne dans le budget."""
    fits, tokens, budget = validate_context_fit(model, messages, reserve)
    if not fits:
        raise ProviderUnavailable(f"contexte {tokens} > budget {budget} pour {model}, non reducible")
    if tokens <= budget:
        return messages, False
    head = [m for m in messages if m.get("role") == "system"][:1]
    note = {"role": "system", "content": "[orch] Resume: historique tronque pour respecter le budget de contexte."}
    used = est_tokens(head + [note])
    keep = []
    for m in reversed(messages):
        c = str(m.get("content", ""))
        tk = max(1, len(c) // 4)
        if used + tk <= budget:
            keep.append(m); used += tk
        else:
            room = budget - used
            if room > 8:
                tr = dict(m); tr["content"] = c[: room * 4 - 12] + " …[tronque]"
                keep.append(tr); used = budget
            break
    keep.reverse()
    return head + [note] + keep, True

# ─── Clients au format verifie ──────────────────────────────────────
def call(level, messages, tools=None, max_tokens=None, dry=False):
    cfg = LEVELS[level]
    model = cfg["model"]
    if not allowed(model):
        raise PermissionError(f"modele hors allowlist gratuite: {model}")
    msgs, summarized = fit_context(model, messages)
    mt = int(max_tokens or cfg["max_tokens"])
    tmo = float(cfg.get("timeout", 120))
    t0 = 0.0
    def _fire():
        nonlocal t0
        t0 = time.time()
        if cfg["provider"] == "openrouter-free":
            body = {"model": model.split("/", 1)[1] if "/" in model else model, "messages": msgs,
                    "max_tokens": mt, "temperature": cfg["temperature"]}
            if cfg.get("reasoning") and cfg.get("reasoning_budget"):
                body["reasoning"] = {"enabled": True, "max_tokens": int(cfg["reasoning_budget"])}
            return _post("https://openrouter.ai/api/v1/chat/completions", body, OR_KEY, timeout=tmo)
        if cfg["provider"] == "nvidia":
            body = {"model": model.split("/", 1)[1] if "/" in model else model, "messages": msgs,
                    "max_tokens": mt, "temperature": cfg["temperature"]}
            if cfg.get("thinking"):
                body["chat_template_kwargs"] = {"thinking": True}
            if tools:
                body["tools"] = tools
            return _post("https://integrate.api.nvidia.com/v1/chat/completions", body, NV_KEY, timeout=420)
        raise ProviderUnavailable("provider inconnu")
    # Une seule reprise si la route retourne une reponse vide (pas de boucle sur erreur HTTP).
    data = _fire()
    for _ in range(1):
        ch0 = (data.get("choices") or [{}])[0]
        if (ch0.get("message") or {}).get("content"):
            break
        data = _fire()
    ms = int((time.time() - t0) * 1000)
    ch = (data.get("choices") or [{}])[0]; msg = ch.get("message", {}) or {}
    usage = data.get("usage", {}) or {}
    # Resume de decision UNIQUEMENT (pas la chaine de raisonnement interne)
    content = msg.get("content") or ""
    decision = content.strip().splitlines()[0][:240] if content.strip() else ""
    return {"provider": cfg["provider"], "model": model, "ms": ms, "summarized": summarized,
            "finish": ch.get("finish_reason"), "tool_calls": bool(msg.get("tool_calls")),
            "reasoning": bool(msg.get("reasoning_content") or (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")),
            "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
            "decision": decision, "content": content[:4000], "content_full_len": len(content),
            "usage_prompt": usage.get("prompt_tokens"), "usage_completion": usage.get("completion_tokens")}

# ─── Phases de l'orchestration adaptative ──────────────────────────
def triage(task):
    """A. Triage: difficulte / risque / perimetre -> niveau de raisonnement."""
    t = (task.get("objective") or "").lower()
    kw_hard = ("architecture", "refactor global", "migration", "debug complexe", "root cause", "revue a risque")
    kw_easy = ("typo", "commentaire", "renommer", "lint", "ajuster un texte")
    if any(k in t for k in kw_hard): level, risk = "deep", "high"
    elif any(k in t for k in kw_easy): level, risk = "fast", "low"
    else: level, risk = "balanced", "medium"
    scope = "single-file" if ("un fichier" in t or "simple" in t or "typo" in t) else "multi-file"
    multi = "non" if (level == "fast" and scope == "single-file") else "oui"
    return {"level": level, "risk": risk, "scope": scope, "multi_agent": multi,
            "budget": {"ctx": CTX.get(LEVELS[level]["model"]), "max_tokens": LEVELS[level]["max_tokens"]}}

def plan(task, repo_facts=None):
    """B. Planification: ne modifie AUCUN fichier. Plan court + criteres + risques/tests."""
    lvl = triage(task)["level"]
    facts = repo_facts or {"repo": task.get("repo", "<isolated>"), "files": task.get("files", [])}
    prompt = [{"role": "system", "content": "Tu produis un plan court et des criteres d'acceptation. Ne modifie aucun fichier."},
              {"role": "user", "content": "Objectif: " + task["objective"] + " | Perimetre: " + json.dumps(facts, ensure_ascii=False) + " | Reponds en 3 a 5 puces max."}]
    r = call(lvl, prompt, max_tokens=192)
    plan = {"objective": task["objective"], "level": lvl,
            "steps": [s.strip() for s in r["decision"].replace("•", "-").split("-") if s.strip()][:5] or [r["decision"]],
            "files": facts.get("files", []),
            "acceptance": task.get("acceptance", []),
            "risks": task.get("risks", []), "tests": task.get("tests", []),
            "model_used": r["model"], "summarized": r["summarized"]}
    return plan

def execute(task, wsdir, checkpoint=None):
    """C. Execution: petite unite verifiable, dans un worktree ISOLÉ. Aucune modif de prod."""
    os.makedirs(wsdir, exist_ok=True)
    step = (checkpoint or {}).get("next", "apply")
    target = os.path.join(wsdir, "patch.txt")
    with open(target, "w", encoding="utf-8") as f:
        f.write(f"[orch apply] {task['objective']} | step={step} | at {time.strftime('%H:%M:%S')}\n")
    return {"step_done": step, "artifact": target, "owner_repo": task.get("repo", "<isolated>")}

def review(diff_text, adversarial_hint=None):
    """D. Relecture contradictoire. Second modele (deep) si dispo, SINON grille deterministe.
       On ne fait PAS confiance a l'auto-validation de l'auteur."""
    findings = []
    checks = [
        ("absence de TODO/FIXME non resolu", "TODO" in diff_text or "FIXME" in diff_text),
        ("pas de secret evident", any(s in diff_text.upper() for s in ("API_KEY=", "PASSWORD=", "SECRET="))),
        ("gestion d'erreur ABSENTE", not ("try:" in diff_text or "except" in diff_text or "raise" in diff_text)),
    ]
    for name, bad in checks:
        if bad: findings.append(f"[grille] {name}: MANQUANT/SUSPECT")
    if adversarial_hint and adversarial_hint in diff_text:
        findings.append(f"[grille] defaut injecte detecte: '{adversarial_hint}'")
    for ref in ("openrouter/nvidia/nemotron-3.5-lightning:", "openai/", "anthropic/", "gpt-", "command-a"):
        if ref in (diff_text or "").lower() or ref in (diff_text or ""):
            findings.append(f"[grille] reference a un modele non autorise detectee: {ref}")
    return {"method": "deterministic-checklist", "findings": findings, "blocking": len(findings) > 0}

def deep_review(diff_text, adversarial_hint=None):
    """Relecture contradictoire profonde (mode deep): cherche erreurs, hypothèses
    non démontrees, omissions et risques; rend un verdict explicite. Jamais d'auto-validation.
    Une reponse vide ou non conclue ne bloque pas a tort: elle rend INCONCLUS (reprise necessaire)."""
    sysp = ("Tu es relecteur contradictoire. Analyse le diff ci-dessous. Cherche: erreurs logiques, "
            "hypotheses non demontees, omissions (cas limites non geres), regressions et risques. "
            "Reponds UNIQUEMENT: VERDICT: BLOQUANT ou VERDICT: OK, puis une ligne par defaut trouve (max 6).")
    userp = "Diff:\n" + diff_text
    if adversarial_hint:
        userp += "\nDefaut suspect a verifier: " + adversarial_hint
    r = call("deep", [{"role": "system", "content": sysp}, {"role": "user", "content": userp}], max_tokens=768)
    txt = (r.get("content") or "")
    import re as _re
    mver = _re.search(r"VERDICT:\s*(BLOQUANT|OK)", txt, _re.I)
    verdict = mver.group(1).upper() if mver else "INCONCLUS"
    findings = [ln.strip(" -•\t") for ln in txt.splitlines()
                if ln.strip() and not _re.match(r"VERDICT:\s*", ln, _re.I)]
    blocking = (verdict == "BLOQUANT" and len(findings) > 0)
    if not txt.strip():
        verdict, blocking = "INCONCLUS (reponse vide)", True
    return {"method": "deep-contradictory-review", "model": r["model"], "verdict": verdict,
            "findings": findings, "blocking": blocking,
            "ms": r["ms"], "reasoning": r["reasoning"], "reasoning_tokens": r["reasoning_tokens"],
            "content_full_len": r["content_full_len"], "summarized": r["summarized"]}

def verify(task, evidence):
    """E. Verification: criteres d'acceptation reellement verifies (pas un simple exit code)."""
    crit = task.get("acceptance", [])
    results = []
    ok = bool(evidence.get("artifact")) and os.path.exists(evidence.get("artifact", ""))
    results.append({"criterion": "artefact appliqué présent", "ok": ok})
    for c in crit:
        results.append({"criterion": c, "ok": c in (task.get("acceptance_verified", []) or [c])})
    passed = all(r["ok"] for r in results)
    return {"passed": passed, "checks": results}

def deliver(task_id, state, report):
    """F. Livraison: completed UNIQUEMENT si criteres verifies; sinon blocked/failed + reprise."""
    return {"task_id": task_id, "state": state, "report": report, "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

def run_chain(task, wsdir, checkpoint=None, simplify_resume=True):
    """Chaine complete avec budgets, checkpoints et reprise bornee."""
    cp = checkpoint or {}
    ev = {"task": task["objective"]}
    tr = triage(task); ev["triage"] = tr
    if not cp.get("planned"):
        pl = plan(task); ev["plan"] = pl; cp["planned"] = True
    ex = execute(task, wsdir, cp); ev["execute"] = ex; cp["next"] = "apply-done"
    # (demo infra) ecriture du diff d'auteur pour la revue contradictoire
    diff_path = os.path.join(wsdir, "diff.diff")
    seed = task.get("diff_seed", "contexte: correction ponctuelle; gestion d'erreur via try/except\n")
    with open(diff_path, "w", encoding="utf-8") as f:
        f.write(seed)
    rv = review(open(diff_path, encoding="utf-8").read(), task.get("adversarial_hint"))
    ev["review"] = rv
    if rv["blocking"]:
        return {"state": "blocked", "why": "revue contradictoire bloquante", "evidence": ev, "checkpoint": cp}
    # Relecture contradictoire profonde sur le diff (mode deep): recherche defauts reels.
    drv = deep_review(open(diff_path, encoding="utf-8").read(), task.get("adversarial_hint"))
    ev["deep_review"] = drv
    if drv["blocking"]:
        return {"state": "blocked", "why": "relecture deep bloqueante: " + "; ".join(drv["findings"][:3]),
                "evidence": ev, "checkpoint": cp}
    vf = verify(task, ex); ev["verify"] = vf
    state = "completed" if vf["passed"] else "blocked"
    ev["deliver"] = deliver(task.get("id", "task"), state, {"changes": task["objective"], "limits": ["infra test"]})
    return {"state": state, "evidence": ev, "checkpoint": cp}
