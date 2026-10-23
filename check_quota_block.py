with open(r"C:\factory-service\v3\f3.py", "r", encoding="utf-8") as f:
    content = f.read()

# Search for 'backoff' or 'time.sleep' in the context of refused_quota
idx = content.find("refus_quota")
if idx >= 0:
    # Print a large chunk starting from refus_quota
    chunk = content[idx:idx+2000]
    print(chunk)