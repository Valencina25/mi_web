import sqlite3
import os

conn = sqlite3.connect("tienda.db")
cursor = conn.cursor()

password = os.environ.get("ADMIN_PASS", "1962")

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    password TEXT
)
""")

cursor.execute("DELETE FROM usuarios")
cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
               ("admin", password))

conn.commit()
conn.close()

print(f"Usuario creado: admin / {password}")
