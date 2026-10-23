#!/usr/bin/env python3
"""Measure the backoff with jitter effect (P5.2).

Simulates the backoff calculation for 50 missions with quota exhaustion
and compares total wait time with vs without jitter.
"""
import random
import statistics

print("=== Backoff Jitter Measurement (P5.2) ===")
print("Simulating backoff for 50 missions with quota exhaustion...")
print()

# The backoff formula from f3.py quota guard:
# backoff = max(0, min(2 ** attempts, 30) + random.uniform(-2, 2))

results = []

for trial in range(5):
    # 50 missions, each going through attempts 0, 1, 2 (roughly 17 each)
    mission_count = 50
    attempts_per_mission = [0] * 17 + [1] * 17 + [2] * 16  # 50 total
    
    total_with_jitter = 0
    total_without_jitter = 0
    
    for attempts in attempts_per_mission:
        backoff_with = max(0, min(2 ** attempts, 30) + random.uniform(-2, 2))
        backoff_without = max(0, min(2 ** attempts, 30))
        total_with_jitter += backoff_with
        total_without_jitter += backoff_without
    
    jitter_saved = total_without_jitter - total_with_jitter
    results.append({
        "trial": trial,
        "total_with_jitter": total_with_jitter,
        "total_without_jitter": total_without_jitter,
        "jitter_saved": jitter_saved
    })
    print(f"Trial {trial}: with={total_with_jitter:.1f}s, without={total_without_jitter:.1f}s, saved={jitter_saved:.1f}s")

# Summary
print()
print("=== SUMMARY ===")
avg_with = sum(r["total_with_jitter"] for r in results) / len(results)
avg_without = sum(r["total_without_jitter"] for r in results) / len(results)
avg_saved = avg_without - avg_with
pct_reduction = 100 * avg_saved / avg_without

print(f"Average backoff with jitter:    {avg_with:.2f}s")
print(f"Average backoff without jitter: {avg_without:.2f}s")
print(f"Average jitter savings:         {avg_saved:.2f}s")
print(f"Percentage reduction:           {pct_reduction:.1f}%")
print()
print("=== INTERPRETATION ===")
print("Jitter spreads the retry wait times across a window of ~4s (from ±2s)")
print("around each exponential backoff value, preventing synchronized")
print("retries when multiple workers experience quota exhaustion simultaneously.")
print("A reduction of " + f"{pct_reduction:.1f}" + "% in average wait time is expected.")
print()
print("=== Per-attempt backoff comparison ===")
for attempts in [0, 1, 2, 3]:
    base = max(0, min(2 ** attempts, 30))
    with_jitter_values = [max(0, min(2 ** attempts, 30) + random.uniform(-2, 2)) for _ in range(1000)]
    without = [base] * 1000
    print(f"Attempt {attempts}: base={base}s, "
          f"with_jitter_mean={statistics.mean(with_jitter_values):.2f}s, "
          f"without_jitter={base}s, "
          f"spread={max(with_jitter_values)-min(with_jitter_values):.2f}s")

print("\n=== Measurement complete ===")