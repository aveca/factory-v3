#!/usr/bin/env python3
"""Improve quota backoff with jitter — P5.2 implementation.

Adds [-2s, +2s] random jitter to the existing min(2^attempts, 30s) backoff
in f3.py's refuse_quota category, to prevent coordinated omission when
multiple workers experience quota exhaustion simultaneously.

This is a localized, reversible improvement to f3.py only.
"""

import json, os, random, sys

# Read f3.py
f3_path = r"C:\factory-service\v3\f3.py"
with open(f3_path, "r", encoding="utf-8") as f:
    content = f.read()

# The backoff line in the quota guard section:
# Current: backoff = min(2 ** m["attempts"], 30)
# New: backoff = min(2 ** m["attempts"], 30) + random.uniform(-2, 2)
# But we need to ensure backoff doesn't go negative (unlikely but safe)
# And we clip to 0 minimum

old_backoff = "backoff = min(2 ** m[\"attempts\"], 30)"
new_backoff = 'backoff = max(0, min(2 ** m["attempts"], 30) + random.uniform(-2, 2))'

if old_backoff in content:
    content = content.replace(old_backoff, new_backoff)
    print(f"Replaced backoff line in {f3_path}")
else:
    print(f"Old backoff pattern not found in {f3_path}")
    # Show what except block looks like
    idx = content.find('except Exception as e:')
    if idx >= 0:
        print(f"except Exception found at position {idx}")

# Write back
with open(f3_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"f3.py updated. Size: {os.path.getsize(f3_path)} bytes")