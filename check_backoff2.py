with open(r"C:\factory-service\v3\f3.py", "r", encoding="utf-8") as f:
    content = f.read()

# Search for the backoff pattern
idx = content.find("2 ** m[\"attempts\"]")
if idx >= 0:
    print("Found '2 ** m[\"attempts\"]' at position", idx)
    print("Context (300 chars):")
    print(content[idx-100:idx+200])
else:
    print("'2 ** m[\"attempts\"]' NOT found")
    
# Also search for 'min(2'
idx2 = content.find('min(2')
if idx2 >= 0:
    print("\nFound 'min(2' at position", idx2)
    print("Context (300 chars):")
    print(content[idx2-100:idx2+200])