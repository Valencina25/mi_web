import sqlite3

conn = sqlite3.connect("tienda.db")
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

conn.commit()
conn.close()

print("BD creada correctamente 🌱")
