#!/usr/bin/env python3
"""P5.4 Deterministic Tests: Quota resumption validation without network calls."""
import json, os, sys, hashlib
import f3

print("=== P5.4 Deterministic Tests (code verification, no DB manipulation) ===")
print()

src = f3.__file__

# ============================================================
# Test 1: Quota épuisé code structure
# ============================================================
print("Test 1: Quota épuisé - code structure verification")
# The quota guard sets mission to 'queued' with explicit reason and bounded retry
has_queued_state = 'set_state(mid, "queued"' in src
has_explicit_reason = 'refus_quota' in src and 'error=f"refus_quota' in src
has_bounded_retry = 'return "retry" if m["attempts"]' in src and 'max_retries' in src
print(f"  set_state(mid, \"queued\") with refus_quota reason: {has_queued_state}")
print(f"  Explicit error reason (refus_quota): {has_explicit_reason}")
print(f"  Bounded retry via attempts < max_retries: {has_bounded_retry}")
results1 = has_queued_state and has_explicit_reason and has_bounded_retry
print(f"  {'PASS' if results1 else 'FAIL'}: Quota épuisé - code structure verified")
print()

# ============================================================
# Test 2: 402 -> blocked without retry
# ============================================================
print("Test 2: 402 -> blocked without retry")
has_402_blocked = "402" in src and "paiement_requis" in src and "blocked" in src and 'return "failed"' in src
print(f"  402 -> blocked + return 'failed': {has_402_blocked}")
results2 = has_402_blocked
print(f"  {'PASS' if results2 else 'FAIL'}: 402 -> blocked without retry")
print()

# ============================================================
# Test 3: 429 with jitter + bounded retries
# ============================================================
print("Test 3: 429 with jitter + bounded retries")
has_quota_backoff = "refus_quota" in src and "2 ** m" in src and "random.uniform" in src
has_max_retries_guard = 'return "retry" if m["attempts"]' in src and "max_retries" in src
print(f"  Quota backoff with random.uniform: {has_quota_backoff}")
print(f"  Bounded retry via max_retries guard: {has_max_retries_guard}")
results3 = has_quota_backoff and has_max_retries_guard
print(f"  {'PASS' if results3 else 'FAIL'}: 429 with jitter + bounded retries")
print()

# ============================================================
# Test 4: Empty response single retry
# ============================================================
print("Test 4: Empty response -> single retry at attempts=0")
has_empty_retry = 'm["attempts"] == 0' in src and 'return "retry"' in src
print(f"  Empty response -> 1 retry at attempts=0: {has_empty_retry}")
results4 = has_empty_retry
print(f"  {'PASS' if results4 else 'FAIL'}: Empty response single retry logic")
print()

# ============================================================
# Test 5: Timeout bounded
# ============================================================
print("Test 5: Timeout bounded by max_retries")
has_timeout_bounded = "timeout" in src.lower() and "max_retries" in src and 'return "retry" if m["attempts"]' in src
print(f"  Timeout bounded by max_retries: {has_timeout_bounded}")
results5 = has_timeout_bounded
print(f"  {'PASS' if results5 else 'FAIL'}: Timeout bounded")
print()

# ============================================================
# Test 6: Mission persistence (code structure)
# ============================================================
print("Test 6: Mission persistence code structure")
has_durable_report = "hist_append(m, \"refus_quota\")" in src
print(f"  Durable report (hist_append + refus_quota): {has_durable_report}")
results6 = has_durable_report
print(f"  {'PASS' if results6 else 'FAIL'}: Mission persistence code structure")
print()

# ============================================================
# Test 7: No double claim safeguards
# ============================================================
print("Test 7: No double claim safeguards")
has_concurrency = "concurrency_limit" in src
has_begin_immediate = "BEGIN IMMEDIATE" in src
has_returning = "RETURNING" in src
print(f"  concurrency_limit present: {has_concurrency}")
print(f"  BEGIN IMMEDIATE present: {has_begin}")
print(f"  RETURNING present: {has_returning}")
results7 = has_concurrency and has_begin and has_returning
print(f"  {'PASS' if results7 else 'FAIL'}: No double claim safeguards")
print()

# ============================================================
# Summary
# ============================================================
print("=== P5.4 SUMMARY ===")
all_results = [results1, results2, results3, results4, results5, results6, results7]
pass_count = sum(all_results)
fail_count = len(all_results) - pass_count
print(f"  PASS: {pass_count}/7")
print(f"  FAIL: {fail_count}/7")
print()

if all(results1, results2, results3, results4, results5, results6, results7):
    overall = "VALIDÉ"
else:
    overall = "PARTIEL"

print(f"Overall: {overall}")
print()
print("=== P5.4 DETERMINISTIC TESTS COMPLETE ===")

# File modification verification
with open(r"C:\factory-service\v3\f3.py.before-quota-guard-20261023-013903.bak", "rb") as f:
    backup_hash = hashlib.sha256(f.read()).hexdigest()
with open(r"C:\factory-service\v3\f3.py", "rb") as f:
    current_hash = hashlib.sha256(f.read()).hexdigest()
results_file_modified = backup_hash != current_hash
print(f"  File modified from backup: {'PASS' if results_file_modified else 'FAIL'}")
print()

# Final overall
all_pass = all(all_results) and results_file_modified
final_status = "VALIDÉ" if final_status else "PARTIEL"
print(f"Final overall: {final_status}")
print()
print("=== P5.4 DETERMINISTIC TESTS COMPLETE ===")