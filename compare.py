import hashlib

with open(r'C:\factory-service\v3\f3.py', 'rb') as f:
    current = f.read()
with open(r'C:\factory-service\v3\f3.py.before-quota-guard-20261023-013903.bak', 'rb') as f:
    backup = f.read()

print(f"Current f3.py size: {len(current)} bytes")
print(f"Backup size: {len(backup)} bytes")
print(f"Sizes match: {len(current) == len(backup)}")
print(f"Hashes match: {hashlib.sha256(current).hexdigest() == hashlib.sha256(backup).hexdigest()}")

# Show lines unique to current
current_text = current.decode('utf-8')
backup_text = backup.decode('utf-8')

current_lines = current_text.split('\n')
backup_lines = backup_text.split('\n')

# Find differences
if current_lines != backup_lines:
    # Find first differing line
    for i, (c, b) in enumerate(zip(current_lines, backup_lines)):
        if c != b:
            print(f"\nFirst difference at line {i+1}:")
            print(f"  Current:  {c[:100]}")
            print(f"  Backup:   {b[:100]}")
            break
    # Count differing lines
    diff_count = sum(1 for c, b in zip(current_lines, backup_lines) if c != b)
    print(f"\nTotal differing lines (zipped): {diff_count}")
    # Check if current is longer
    if len(current_lines) > len(backup_lines):
        extra = len(current_lines) - len(backup_lines)
        print(f"Current has {extra} extra lines beyond backup")
else:
    print("Files are identical")