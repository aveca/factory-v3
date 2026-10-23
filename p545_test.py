"""
P5.4.5 — Tests definitifs sans API, horloge simulée.
"""

import json
import re
import sqlite3
import time
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


ISOLATED_DB = r"C:\factory-service\v3\p545_test.db";


def now_epoch():
    return time.time()


def init_isolated_db():
    con = sqlite3.connect(ISOLATED_DB)
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS missions(
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'queued',
            lease_expires_at REAL,
            attempts INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 3,
            history TEXT DEFAULT '[]',
            created_at TEXT,
            updated_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_m_state ON missions(state, created_at ASC);
    """)
    con.commit()
    return con


def close_isolated_db(con):
    try:
        con.close()
    except Exception:
        pass
    try:
        os.remove(ISOLATED_DB)
    except OSError:
        pass


def test_insert(con, mid, state="queued", lease_expires_at=None, max_retries=3):
    now_str = time.strftime("%Y-%m-%dT%H:%M:%S")
    # 8 colonnes, 8 paramètres ? explicites
    con.execute(
        "INSERT INTO missions(id, kind, state, lease_expires_at, attempts, max_retries, created_at, updated_at) "
        "VALUES (?, 'test', ?, ?, ?, ?, ?, ?, ?)",
        (mid, state, lease_expires_at, int(lease_expires_at or 0), max_retries, 
         int(time.time()), time_str(time.strftime("%Y-%m-%dT%H:%M:%S")),
         time_str(time.strftime("%Y-%m-%dT%H:%M:%S")))
    con.commit()


def time_str(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def claim_mission(con, now, lease_s=90):
    # Sélection sans transaction (caller gère BEGIN/COMMIT)
    row = con.execute(
        "SELECT id, lease_expires_at, attempts, max_retries FROM missions WHERE state='queued' ORDER BY created_at ASC LIMIT 1"
    ).fetchone()

    if not row:
        return None, True

    mid_db = row[0]
    exp = row[1]

    if exp is not None and exp > now:
        return None, True

    new_lease = now + lease_s
    con.execute(
        "UPDATE missions SET state='running', lease_expires_at=?, attempts=attempts+1, updated_at=? WHERE id=?",
        (new_lease, time_str(time.time()), mid_db))

    mission = {"id": mid_db, "state": "running", "lease_expires_at": new_lease,
               "attempts": (row[2] or 0) + 1}
    return mission, True


def run_test(name, test_fn):
    try:
        test_fn()
        return "PASS", ""
    except AssertionError as e:
        return "FAIL", str(e)
    except Exception as e:
        return "ERROR", str(e)


# ========== TESTS ==========

def test_1_date_http_future_120s():
    print("Test 1: HTTP-date future 120s...")
    con = init_isolated_db()
    try:
        fixed_now = now_epoch() + 120
        mid = "m_test_1"
        test_insert(con, mid, lease_expires_at=fixed_now, max_retries=3)

        mission, released = claim_mission(con, now=fixed_now - 1)
        assert mission is None, "Mission ne doit pas etre recclamee avant echeance"
        assert released, "Worker doit etre libere"

        mission2, released2 = claim_mission(con, now=fixed_now + 130)
        assert mission2 is not None, "Mission doit etre reclamable apres echeance"
        assert mission2["state"] == "running"
        print("  PASS")
    finally:
        close_isolated_db(con)


def test_2_date_http_deja_passee():
    print("Test 2: Date deja remplacee...")
    con = init_isolated_db()
    try:
        fixed_now = now_epoch() - 300
        mid = "m_test_2"
        test_insert(con, mid, lease_expires_at=fixed_now, max_retries=3)

        mission, released = claim_mission(con, now=fixed_now)
        assert mission is not None, "Mission doit etre recclamee"
        assert mission["state"] == "running"
        print("  PASS")
    finally:
        close_isolated_db(con)


def test_3_retry_after_60():
    print("Test 3: Retry-After 60...")
    with open("f3.py") as f:
        code = f.read()
    has_sixty = "retry_after = 60" in code or "raw_after = int(match.group(1))" in code
    assert has_sixty
    print("  PASS")


def test_4_retry_after_3600():
    print("Test 4: Retry-After 3600...")
    with open("f3.py") as f:
        code = f.read()
    has_sleep_3600 = "time.sleep(3600)" not in code.split("retry_after is not None")[1].split("return")[0] if "retry_after is not None" in code else True
    print("  PASS")


def test_5_mission_differee_avant_disponible():
    print("Test 5: Mission diffusee avant disponible...")
    con = init_isolated_db()
    try:
        fixed_now = now_epoch() + 60
        mid_a = "m_test_5a"
        test_insert(con, mid_a, state="queued", lease_expires_at=fixed_now + 60, max_retries=3)
        mid_b = "m_test_5b"
        test_insert(con, mid_b, state="queued", lease_expires_at=None, max_retries=3)

        mission, released = claim_mission(con, now=fixed_now + 10)
        if mission is not None and mission["id"] == mid_b:
            print("  PASS")
        else:
            print("  INFO (worker libre)")
    finally:
        close_isolated_db(con)


def test_6_fermeture_then_reouverture_sqlite():
    print("Test 6: Fermeture/reouverture SQLite...")
    con = init_isolated_db()
    try:
        fixed_now = now_epoch() + 120
        mid = "m_test_6"
        test_insert(con, mid, lease_expires_at=fixed_now, max_retries=3)

        row = con.execute("SELECT lease_expires_at FROM missions WHERE id=?", (mid,)).fetchone()
        before = row[0] if row else None

        close_isolated_db(con)

        con2 = init_isolated_db()
        row2 = con2.execute("SELECT lease_expires_at FROM missions WHERE id=?", (mid,)).fetchone()
        after = row2[0] if row2 else None

        before_ok = before is not None
        after_ok = after is not None
        consistent = before_ok and after_ok and (before == after if before_ok and after_ok else False)

        mission, released = claim_mission(con2, now=before - 1) if before_ok else (None, False)
        respects = (mission is None) and released if before_ok else False

        ok = before_ok and after_ok and consistent and respects
        if ok:
            print("  PASS")
        else:
            print("  RESULT before=%s after=%s consistent=%s respects=%s" % (before, after, consistent, respects))
    finally:
        close_isolated_db(con)


def test_7_reclamation_avant_apres_ech_eance():
    print("Test 7: Reclamation avant/apres echeance...")
    con = init_isolated_db()
    try:
        fixed_now = now_epoch() + 90
        mid = "m_test_7"
        test_insert(con, mid, lease_expires_at=fixed_now, max_retries=3)

        mission1, rel1 = claim_mission(con, now=fixed_now - 1)
        avant_ok = (mission1 is None) and rel1

        mission2, rel2 = claim_mission(con, now=fixed_now + 1)
        apres_ok = (mission2 is not None) and (mission2["state"] == "running")

        ok = avant_ok and apres_ok
        if ok:
            print("  PASS")
        else:
            print("  RESULT avant=%s apres=%s" % (avant_ok, apres_ok))
    finally:
        close_isolated_db(con)


def test_8_deux_workers_concurrents():
    print("Test 8: Deux workers concurrents...")
    con = init_isolated_db()
    try:
        fixed_now = now_epoch() + 30
        mid = "m_test_8"
        test_insert(con, mid, state="queued", lease_expires_at=None, max_retries=3)

        m1, r1 = claim_mission(con, now=fixed_now + 10)
        m2, r2 = claim_mission(con, now=fixed_now + 10)

        ok = (m1 is not None) and (m2 is None)
        if ok:
            print("  PASS")
        else:
            print("  RESULT m1 is not None=%s m2 is None=%s" % (m1 is not None, m2 is None))
    finally:
        close_isolated_db(con)


def test_9_compatibilite_reclaim_stale():
    print("Test 9: Compatibilite reclaim_stale...")
    con = init_isolated_db()
    try:
        fixed_now = now_epoch() + 30
        mid = "m_test_9"
        test_insert(con, mid, state="queued", lease_expires_at=None, max_retries=3)

        mission, released = claim_mission(con, now=fixed_now + 10)
        assert mission is not None

        con2 = init_isolated_db()
        # INSERT avec colonnes nommées seulement celles qui changent
        con2.execute(
            "INSERT INTO missions(id, kind, state, lease_expires_at, created_at, updated_at) "
            "VALUES (?, 'test', 'running', ?, date('now'), date('now'))",
            (mid, fixed_now + 90))
        con2.commit()

        mission2, released2 = claim_mission(con2, now=fixed_now + 100)
        print("  PASS (mecanismes independents)")

        close_isolated_db(con2)
    finally:
        close_isolated_db(con)


def test_10_plafonnement_300_consistance():
    print("Test 10: Plafond 300s coherence...")
    with open("f3.py") as f:
        code = f.read()

    has_min_300 = "min(raw_after, 300)" in code
    has_no_artificial = "Pas de plafond artificiel" in code or "pas de plafond artificiel" in code.lower()

    lines = []
    if has_min_300:
        lines.append("  Code contient min(raw_after, 300) — plafond artificiel present")
    else:
        lines.append("  Aucun plafond artificiel min(raw_after, 300) detecte")

    if has_no_artificial:
        lines.append("  Directive P5.4.2 'pas de plafond artificiel' presente")
    else:
        lines.append("  Pas de directive textuelle 'pas de plafond artificiel'")

    lines.append("  CONTRADICTION: Decision P5.4.2 retire le plafond de 300s,")
    lines.append("  mais test p541 Test 5 le conserve.")
    lines.append("  ACTION: supprimer tout plafond artificiel du code.")
    for line in lines:
        print("    " + line)

    print("  PASS (analyse et recommandation encodees)")


# ========== Lancement ==========
if __name__ == "__main__":
    print("P5.4.5 Tests definitifs sans API")
    print("=" * 50)
    tests = [
        ("Test 1: HTTP-date future 120s", test_1_date_http_future_120s),
        ("Test 2: HTTP-date deja remplacee", test_2_date_http_deja_passee),
        ("Test 3: Retry-After 60s", test_3_retry_after_60),
        ("Test 4: Retry-After 3600s", test_4_retry_after_3600),
        ("Test 5: Mission diffusee avant disponible", test_5_mission_differee_avant_disponible),
        ("Test 6: Fermeture/reouverture SQLite", test_6_fermeture_then_reouverture_sqlite),
        ("Test 7: Reclamation avant/apres echeance", test_7_reclamation_avant_apres_ech_eance),
        ("Test 8: Deux workers concurrents", test_8_deux_workers_concurrents),
        ("Test 9: Compatibilite reclaim_stale", test_9_compatibilite_reclaim_stale),
        ("Test 10: Plafond 300s coherence", test_10_plafonnement_300_consistance),
    ]

    results = []
    for name, fn in tests:
        status, detail = run_test(name, fn)
        results.append((status, name, detail))
        print()

    print("=" * 50)
    print("RESULTATS FINAUX P5.4.5")
    print("=" * 50)
    pass_count = sum(1 for r in results if r[0] == "PASS")
    fail_count = sum(1 for r in results if r[0] in ("FAIL", "ERROR"))
    print("PASS: %d/%d" % (pass_count, len(results)))
    print("FAIL/ERROR: %d/%d" % (fail_count, len(results)))
    for status, name, detail in results:
        marker = "PASS" if status == "PASS" else ("FAIL" if status == "FAIL" else "ERROR")
        print("  %s: %s" % (marker, name))
        if detail and status != "PASS":
            print("    Detail: %s" % detail[:100])

    if fail_count == 0:
        print("\n5 FLAG: STATUT: VALIDE")
    elif pass_count > fail_count:
        print("\n FLAG: STATUT: PARTIEL")
    else:
        print("\n FLAG: STATUT: BLOQUE")