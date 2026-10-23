#!/usr/bin/env python3
with open(r"C:\factory-service\v3\f3.py", "r", encoding="utf-8") as f:
    c = f.read()

print("reponse_vide in content:", "reponse_vide" in c)
print("attempts == 0 in content:", "attempts == 0" in c)
print('m["attempts"] == 0 in content:', 'm["attempts"] == 0' in c)
print('m[\'attempts\'] == 0 in content:', "m['attempts'] == 0" in c)
print('attempts == 0 anywhere:', "attempts == 0" in c)

# Find the reponse_vide section
idx = c.find("reponse_vide")
if idx >= 0:
    print("\nContext around reponse_vide:")
    print(c[idx:idx+300])