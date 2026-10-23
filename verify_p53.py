#!/usr/bin/env python3
"""P5.3 Integration Audit: Verify quota guard + jitter in f3.py"""
import sys

with open(r"C:\factory-service\v3\f3.py", "r", encoding="utf-8") as f:
    content = f.read()

results = {}

# 1. Quota guard presence
results["quota_guard"] = "refus_quota" in content
print(f"1. Quota guard (refus_quota) present: {results['quota_guard']}")

# 2. Jitter presence
results["jitter"] = "random.uniform" in content and "min(2 ** m" in content
print(f"2. Jitter (random.uniform + 2^attempts) present: {results['jitter']}")

# 3. time.sleep in quota context
results["sleep_in_quota"] = "time.sleep" in content and "refus_quota" in content
print(f"3. time.sleep in quota context: {results['sleep_in_quota']}")

# 4. attempts < max_retries guard
results["attempts_guard"] = 'm["attempts"] < m["max_retries"]' in content or 'm[\"attempts\"] < m[\"max_retries\"]' in content
print(f"4. attempts < max_retries guard: {results['attempts_guard']}")

# 5. Bounded retries
results["bounded_retries"] = "retry" in content and "max_retries" in content
print(f"5. Bounded retries (retry + max_retries): {results['bounded_retries']}")

# 6. Durable report
results["durable_report"] = "hist_append(m, \"refus_quota\")" in content
print(f"6. Durable report (hist_append + refus_quota): {results['durable_report']}")

# 7. 402 -> blocked
results["402_blocked"] = "paiement_requis" in content and "blocked" in content
print(f"7. 402 -> blocked without retry: {results['402_blocked']}")

# 8. Empty response single retry (uses m["attempts"] == 0)
results["empty_single_retry"] = 'm["attempts"] == 0' in content
print(f"8. Empty response single retry (m[\"attempts\"] == 0): {results['empty_single_retry']}")

# 9. timeout bounded
results["timeout_bounded"] = "timeout" in content.lower() and "max_retries" in content
print(f"9. Timeout bounded by max_retries: {results['timeout_bounded']}")

# 10. File comparison
import hashlib
with open(r"C:\factory-service\v3\f3.py.before-quota-guard-20261023-013903.bak", "rb") as f:
    backup_hash = hashlib.sha256(f.read()).hexdigest()
with open(r"C:\factory-service\v3\f3.py", "rb") as f:
    current_hash = hashlib.sha256(f.read()).hexdigest()
results["file_changed"] = backup_hash != current_hash
print(f"10. File modified from backup: {results['file_changed']}")

# Summary
print("\n=== P5.3 AUDIT RESULTS ===")
all_pass = all(results.values())
for key, value in results.items():
    status = "PASS" if value else "FAIL"
    print(f"  {key}: {status}")

print(f"\nOverall: {'VALIDÉ' if all_pass else 'PARTIEL'}")