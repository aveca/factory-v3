#!/usr/bin/env python3
"""Find the backoff line in f3.py quota guard section."""
import sys

with open(r"C:\factory-service\v3\f3.py", "r", encoding="utf-8") as f:
    content = f.read()

# Search patterns for the backoff in the refused_quota section
patterns = [
    "backoff = min",
    "2 ** m[\"attempts\"]",
    "time.sleep",
    "min(2 **",
]

for p in patterns:
    idx = content.find(p)
    if idx >= 0:
        print(f"Found '{p}' at position {idx}")
        print(f"Context (200 chars): {content[idx-50:idx+150]}")
        print()
    else:
        print(f"'{p}' NOT found")
        print()

# Also look for the specific line numbers from the original design
# The except block was at lines 440-445 originally, but may have shifted
print(f"File size: {len(content)} bytes")
print(f"Lines: {content.count(chr(10)) + 1}")