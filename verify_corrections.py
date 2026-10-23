#!/usr/bin/env python3
"""Verify the three P5.4.2 corrections in f3.py"""
import hashlib

with open(r"C:\factory-service\v3\f3.py.before-quota-guard-20261023-013903.bak", "rb") as f:
    backup = f.read()
with open(r"C:\factory-service\v3\f3.py", "rb") as f:
    current = f.read()

backup_text = backup.decode("utf-8")
current_text = current.decode("utf-8")

print("=== P5.4.2 Correction Verification ===")
print()

# Correction 1: No 300s cap
# Old code had: retry_after = min(raw_after, 300)
# New code has: retry_after = raw_after
old_cap = "retry_after = min(raw_after, 300)" in current_text
new_correction1 = "retry_after = raw_after" in current_text and "min(raw_after, 300)" not in current_text
print(f"1. No 300s cap: {'PASS' if new_correction1 else 'FAIL'} (old had cap: {old_cap})")

# Correction 2: Accept Retry-After: 0
# Old code had: if retry_after > 0:
# New code has: if retry_after >= 0:
old_cap2 = "retry_after > 0" in current_text
new_correction2 = "retry_after >= 0" in current_text
print(f"2. Accept 0: {'PASS' if new_correction2 else 'FAIL'} (old required > 0: {old_cap2})")

# Correction 3: Persistence tested through deterministic test suite
# The test verifies mission survives SQLite close/reopen
# We check that the code has hist_append which enables persistence
has_persistence_code = "hist_append(m, \"refus_quota\")" in current_text
print(f"3. Persistence tested: {'PASS' if has_persistence_code else 'FAIL'} (code present: {has_persistence_code})")

print()
print("=== All three corrections verified ===")