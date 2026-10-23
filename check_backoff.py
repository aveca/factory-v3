with open(r"C:\factory-service\v3\f3.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find the quota guard section - look for 'refus_quota'
idx = content.find("refus_quota")
if idx >= 0:
    print("refus_quota found at line", idx // 80 + 1, "position", idx)
    print("Context (400 chars):")
    print(content[idx:idx+400])
else:
    print("refus_quota NOT found in f3.py")