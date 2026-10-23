import sqlite3
import os

# Vérifier si la base existe
db_path = r'C:\factory-service\v3\state\f3_missions.db'
print('Base de données existante :', os.path.exists(db_path))

# Ouvrir la base réelle
con = sqlite3.connect(db_path)
# Obtenir le schéma
schema = con.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='missions'").fetchone()
print('SCHEMA REAL :')
print(schema[0] if schema else 'Non trouvé')
print()
# Obtenir les colonnes
cols = con.execute('PRAGMA table_info(missions)').fetchall()
print('COLONNES :')
for c in cols:
    print('  ', c)
print()
# Quelques lignes d'exemple
rows = con.execute('SELECT * FROM missions LIMIT 3').fetchall()
print('EXEMPLES (3 premières lignes) :')
for r in rows:
    print('  ', r)
con.close()