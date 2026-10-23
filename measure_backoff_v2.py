#!/usr/bin/env python3
"""Measure P5.2 backoff jitter: synchronization prevention.

Key metric: without jitter, ALL missions retry at the exact same time.
With jitter, retries are spread across a ~4s window.
This prevents the 'thundering herd' problem on quota renewal.
"""
import random
import statistics

print("=== P5.2 Backoff Jitter: Synchronization Prevention ===")
print()
print("KEY METRIC: Spread of retry wait times (prevents synchronized retries)")
print()

# Simulate 50 missions retrying after quota exhaustion
# Without jitter: all 50 missions have identical backoff values
# With jitter: each mission gets a slightly different backoff

print("Scenario: 50 missions all experience quota exhaustion at attempt 1")
print("Base backoff at attempt 1: min(2^1, 30) = 2s")
print()

# Without jitter - all identical
backoffs_without = [2.0] * 50
spread_without = max(backoffs_without) - min(backoffs_without)
print(f"Without jitter: all 50 missions wait exactly 2.0s")
print(f"  Spread: {spread_without}s (0 = perfectly synchronized)")
print()

# With jitter - each mission gets different backoff
random.seed(42)  # Reproducible
backoffs_with = [max(0, min(2, 30) + random.uniform(-2, 2)) for _ in range(50)]
spread_with = max(backoffs_with) - min(backoffs_with)
avg_with = statistics.mean(backoffs_with)
print(f"With jitter (seed=42):")
print(f"  Individual wait times: {sorted(backoffs_with)}")
print(f"  Mean: {avg_with:.2f}s")
print(f"  Min: {min(backoffs_with):.2f}s, Max: {max(backoffs_with):.2f}s")
print(f"  Spread: {spread_with:.2f}s")
print(f"  Reduction in synchronization: perfectly synchronized -> spread of {spread_with:.2f}s")
print()

# At attempt 2
print("Scenario: 50 missions all experience quota exhaustion at attempt 2")
print("Base backoff at attempt 2: min(2^2, 30) = 4s")
print()

backoffs_without2 = [4.0] * 50
spread_without2 = max(backoffs_without2) - min(backoffs_without2)

random.seed(42)
backoffs_with2 = [max(0, min(4, 30) + random.uniform(-2, 2)) for _ in range(50)]
spread_with2 = max(backoffs_with2) - min(backoffs_with2)
avg_with2 = statistics.mean(backoffs_with2)

print(f"With jitter (seed=42):")
print(f"  Individual wait times: {sorted(backoffs_with2)}")
print(f"  Mean: {avg_with2:.2f}s")
print(f"  Min: {min(backoffs_with2):.2f}s, Max: {max(backoffs_with2):.2f}s")
print(f"  Spread: {spread_with2:.2f}s")
print()

# Summary of benefit
print("=== BENEFIT SUMMARY ===")
print("Without jitter:     50 missions retry simultaneously at 2s/4s intervals")
print("With jitter:      50 missions retry spread over ~4s window")
print("Benefit:          Prevents thundering herd on quota renewal")
print("                  Some missions succeed earlier, consume quota,")
print("                  others retry when more quota is available")
print()
print("=== Measurement complete ===")