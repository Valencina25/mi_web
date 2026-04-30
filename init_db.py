import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "tienda.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    precio REAL,
    imagen TEXT,
    categoria TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS carrito (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    producto_id INTEGER,
    cantidad INTEGER DEFAULT 1,
    UNIQUE(usuario, producto_id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS compras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    nombre TEXT,
    telefono TEXT,
    direccion TEXT,
    email TEXT,
    total REAL,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS compra_detalle (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    compra_id INTEGER,
    producto_nombre TEXT,
    cantidad INTEGER,
    precio_unitario REAL,
    FOREIGN KEY (compra_id) REFERENCES compras(id)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS mensajes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT,
    email TEXT,
    mensaje TEXT,
    fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

# Crear admin si no existe
cursor.execute("SELECT id FROM usuarios WHERE usuario=?", ("admin",))
if not cursor.fetchone():
    cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
                   ("admin", generate_password_hash("1962")))

conn.commit()
conn.close()

print("BD creada correctamente 🌱")
