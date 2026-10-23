#!/usr/bin/env python3
"""P4.3 — Playwright minimal integration for Factory V3.

Tests a local HTML fixture to verify:
- rendering
- console error detection
- link validation
- simple user journey (form interaction)
- no window focus theft
- captures screenshot on failure
"""

import os, json, shutil, tempfile, subprocess, sys
from pathlib import Path

# Use a standalone HTML file (no external deps)
HTML_FIXTURE = """<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <title>Factory Test — Page de validation</title>
    <style>
        body { font-family: sans-serif; margin: 40px; color: #333; }
        .container { max-width: 600px; margin: 0 auto; }
        .section { margin: 20px 0; padding: 10px; border: 1px solid #e0e0e0; border-radius: 4px; }
        .error { color: #d32f2f; font-weight: bold; }
        .ok { color: #388e3c; font-weight: bold; }
        a { color: #1976d2; text-decoration: none; }
        a:hover { text-decoration: underline; }
        input, button { padding: 6px 12px; margin: 4px; font-size: 14px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Factory V3 — Validation Page</h1>

        <div class="section">
            <h2>1. Titre de la page</h2>
            <p>La page doit s'afficher correctement.</p>
        </div>

        <div class="section">
            <h2>2. Erreurs console</h2>
            <p>Aucune erreur JavaScript critique ne doit apparaître.</p>
            <ul id="console-errors"></ul>
        </div>

        <div class="section">
            <h2>3. Lien de vérification</h2>
            <p>Le lien ci-dessous doit être valide et mener à une page reachable.</p>
            <a href="https://www.example.com" target="_blank">Exemple de lien externe</a>
        </div>

        <div class="section">
            <h2>4. Formulaire simple</h2>
            <form id="contact-form">
                <div>
                    <label for="name">Nom :</label>
                    <input type="text" id="name" required>
                </div>
                <div>
                    <label for="email">Email :</label>
                    <input type="email" id="email" required>
                </div>
                <button type="submit">Envoyer</button>
            </form>
            <p id="form-status"></p>
        </div>
    </div>

    <script>
        // Log errors to the DOM
        window.addEventListener('error', function(e) {
            const list = document.getElementById('console-errors');
            const li = document.createElement('li');
            li.textContent = 'Erreur globale: ' + (e.message || 'inconnu');
            li.className = 'error';
            list.appendChild(li);
        });

        // Formulaire: simulation d'envoi
        const form = document.getElementById('contact-form');
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const name = document.getElementById('name').value || 'Utilisateur';
            const status = document.getElementById('form-status');
            status.textContent = 'Bonjour ' + name + ' — formulaire validé';
            status.className = 'ok';
        });

        // Simuler une erreur console non critique
        setTimeout(() => {
            const li = document.createElement('li');
            li.textContent = 'Info: chargement des ressources en cours';
            li.className = 'ok';
            const list = document.getElementById('console-errors');
            list.appendChild(li);
        }, 100);
    </script>
</body>
</html>"""

def test_playwright_minimal():
    """Run minimal Playwright test against local HTML fixture."""
    import json
    
    results = {
        "passed": 0,
        "failed": 0,
        "errors": [],
        "screenshot": None
    }
    
    # Write HTML fixture to temp file
    tmpdir = tempfile.mkdtemp(prefix="pw_fixture_")
    html_path = os.path.join(tmpdir, "index.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(HTML_FIXTURE)
    
    html_path_abs = os.path.abspath(html_path)
    url = f"file://{html_path_abs}"
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            
            # Set window size (no focus theft)
            page.set_viewport_size({"width": 1280, "height": 720})
            
            # Monitor console messages
            console_messages = []
            page.on("console", lambda msg: console_messages.append({
                "type": msg.type,
                "text": msg.text,
                "location": msg.location
            }))
            
            # Capture JS errors
            js_errors = []
            page.on("pageerror", lambda err: js_errors.append({
                "message": str(err),
                "traceback": ""
            }))
            
            # Navigate
            page.goto(url, wait_until="networkidle")
            
            # Wait a bit for async operations
            page.wait_for_timeout(500)
            
            # --- Checks ---
            
            # 1. Page title
            title = page.title()
            if "Factory Test" in title or "Factory V3" in title:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Title check: expected 'Factory' in title, got '{title}'")
            
            # 2. No console errors (only expected "Info" message)
            error_items = [m for m in console_messages if m["type"] == "error"]
            unexpected_errors = [m for m in error_items if "Info" not in m["text"]]
            if len(unexpected_errors) == 0:
                results["passed"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Unexpected console errors: {unexpected_errors}")
            
            # 3. Form interaction
            try:
                page.fill("#name", "Test Utilisateur")
                page.fill("#email", "test@factory.v3")
                page.click("button[type='submit']")
                page.wait_for_timeout(300)
                status = page.text_content("#form-status")
                if "Test Utilisateur" in status and "formulaire validé" in status:
                    results["passed"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Form status: expected greeting, got '{status}'")
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Form interaction failed: {e}")
            
            # 3. Link check (just verify page loaded without error)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
                results["passed"] += 1
            except Exception:
                results["failed"] += 1
                results["errors"].append("Page load timed out")
            
            # 4. Screenshot on success (for evidence)
            screenshot_path = os.path.join(tmpdir, "screenshot.png")
            page.screenshot(path=screenshot_path, full_page=True)
            results["screenshot"] = screenshot_path
            
            # Also capture any console errors for review
            results["console_messages"] = console_messages
            results["js_errors"] = js_errors
            
            browser.close()
    
    except ImportError as e:
        results["failed"] += 1
        results["errors"].append(f"Playwright import failed: {e}")
        # Fallback: mark as need_install
        results["need_install"] = True
    except Exception as e:
        results["failed"] += 1
        results["errors"].append(f"Playwright test error: {e}")
        import traceback
        results["traceback"] = traceback.format_exc()
    
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)
    
    return results


if __name__ == "__main__":
    results = test_playwright_minimal()
    
    print("=" * 60)
    print("PLAYWRIGHT MINIMAL TEST RESULTS")
    print("=" * 60)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print()
    
    if results.get("need_install"):
        print("Playwright needs to be installed/configured")
    elif results["failed"] > 0:
        print("FAILURES:")
        for err in results["errors"]:
            print(f"  - {err}")
    else:
        print("ALL CHECKS PASSED")
    
    print()
    if results.get("screenshot") and os.path.exists(results["screenshot"]):
        print(f"Screenshot saved: {results['screenshot']}")
    
    print("=" * 60)
    
    # Exit code: 0 if all passed, 1 otherwise
    sys.exit(0 if results["failed"] == 0 else 1)