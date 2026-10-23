#!/usr/bin/env python3
"""P5.4 Final Validation: Quota resumption validation"""
import json, os, random, time, hashlib

with open(r"C:\factory-service\v3\f3.py", "r", encoding="utf-8") as f:
    content = f.read()

results = {}

# 1. Quota guard with jitter present
results["quota_guard_jitter"] = "refus_quota" in content and "random.uniform" in content
print(f"1. Quota guard + jitter: {results['quota_guard_jitter']}")

# 2. time.sleep in quota context
results["sleep_in_quota"] = "time.sleep" in content and "refus_quota" in content
print(f"2. time.sleep in quota: {results['sleep_in_quota']}")

# 3. max_retries guard
results["max_retries_guard"] = "max_retries" in content and "retry" in content.lower()
print(f"3. max_retries guard: {results['max_retries_guard']}")

# 4. Durable report (hist_append)
results["durable_report"] = "hist_append(m, \"refus_quota\")" in content
print(f"4. Durable report: {results['durable_report']}")

# 5. 402 -> blocked
results["402_blocked"] = "paiement_requis" in content and "blocked" in content
print(f"5. 402 -> blocked: {results['402_blocked']}")

# 6. Empty response single retry
results["empty_retry"] = 'm["attempts"] == 0' in content
print(f"6. Empty retry at attempts=0: {results['empty_retry']}")

# 7. timeout bounded
results["timeout_bounded"] = "timeout" in content.lower() and "max_retries" in content
print(f"7. Timeout bounded: {results['timeout_bounded']}")

# 8. File modified
with open(r"C:\factory-service\v3\f3.py.before-quota-guard-20261023-013903.bak", "rb") as f:
    backup_hash = hashlib.sha256(f.read()).hexdigest()
with open(r"C:\factory-service\v3\f3.py", "rb") as f:
    current_hash = hashlib.sha256(f.read()).hexdigest()
results["file_modified"] = backup_hash != current_hash
print(f"8. File modified from backup: {results['file_modified']}")

# 9. Check that refus_quota has both backoff AND retry logic
has_backoff = "min(2 ** m" in content and "random.uniform" in content
has_retry = 'return "retry" if m["attempts"]' in content
results["backoff_and_retry"] = has_backoff and has_retry
print(f"9. Backoff + retry logic: {results['backoff_and_retry']}")

# 10. Check for Retry-After mention (or lack thereof)
results["retry_after_mentioned"] = "Retry-After" in content or "retry-after" in content.lower()
print(f"10. Retry-After mentioned: {results['retry_after_mentioned']}")

# Summary
print("\n=== P5.4 VALIDATION RESULTS ===")
all_pass = all(results.values())
for key, value in sorted(results.items()):
    status = "PASS" if value else "FAIL"
    print(f"  {key}: {status}")

print(f"\nOverall: {'VALIDÉ' if all_pass else 'PARTIEL'}")
print(f"\nDetailed results dict:")
for k, v in results.items():
    print(f"  {k}: {v}")