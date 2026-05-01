from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

load_dotenv()

app = Flask(__name__)
app.secret_key = "mi_web_secret_key_fija_2024"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "tienda.db")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, precio REAL, imagen TEXT, categoria TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS carrito (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT, producto_id INTEGER, cantidad INTEGER DEFAULT 1,
        UNIQUE(usuario, producto_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS compras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT, nombre TEXT, telefono TEXT, direccion TEXT,
        email TEXT, total REAL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS compra_detalle (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        compra_id INTEGER, producto_nombre TEXT, cantidad INTEGER,
        precio_unitario REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS mensajes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT, email TEXT, mensaje TEXT,
        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )""")
    # Insertar productos iniciales si la tabla está vacía
    c.execute("SELECT COUNT(*) FROM productos")
    if c.fetchone()[0] == 0:
        productos_iniciales = [
            ("pimiento italiano", 3.0, "pimiento italiano.jpg", "verduras"),
            ("cebollino", 2.0, "cebollino.jpg", "verduras"),
            ("berejana morada", 2.0, "berejena morada.jpg", "verduras"),
            ("calabazin", 2.0, "calabazin negro.jpg", "verduras"),
            ("cebolla", 2.0, "cebolla.jpg", "verduras"),
            ("puerro", 2.0, "puerro.jpg", "verduras"),
            ("zanahoria", 1.0, "zanohoria.jpg", "verduras"),
            ("aguacate", 5.0, "aguacate.jpg", "verduras"),
            ("espinaca", 2.0, "espinaca.jpg", "verduras"),
            ("patata", 1.0, "patata.jpg", "verduras"),
            ("acelga", 2.0, "acelga.jpg", "verduras"),
            ("lechuga", 1.5, "lechuga.jpg", "verduras"),
            ("ajos", 6.0, "ajos.jpg", "verduras"),
            ("Tomate rosa", 4.0, "tomate rosa.jpg", "verduras"),
            ("fresa", 5.0, "fresa.jpg", "frutas"),
            ("pera", 2.8, "pera.jpg", "frutas"),
            ("albaricoque", 5.0, "albaricoque.jpg", "frutas"),
            ("ciruela", 5.0, "ciruela.jpg", "frutas"),
            ("uvas", 4.5, "uvas.jpg", "frutas")
        ]
        c.executemany("INSERT INTO productos (nombre, precio, imagen, categoria) VALUES (?, ?, ?, ?)", productos_iniciales)
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def inicio():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, nombre, precio, imagen, categoria FROM productos")
    productos = c.fetchall()
    c.execute("SELECT DISTINCT categoria FROM productos")
    categorias = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template("index.html", productos=productos, categorias=categorias)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        if not usuario:
            flash("Escribe 'admin'", "error")
            return redirect(url_for("login"))
        if usuario == "juan1962":
            session["usuario"] = usuario
            flash("Bienvenido " + usuario, "success")
            return redirect(url_for("admin"))
        else:
            flash("Usuario incorrecto. Usa 'admin'", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("carrito", None)
    flash("Sesión cerrada", "info")
    return redirect(url_for("inicio"))

@app.route("/carrito")
def carrito():
    usuario = session.get("usuario")
    conn = get_db()
    c = conn.cursor()
    items = []
    total = 0
    if usuario:
        c.execute("""SELECT p.id, p.nombre, p.precio, p.imagen, c.cantidad
            FROM carrito c
            JOIN productos p ON c.producto_id = p.id
            WHERE c.usuario = ?""", (usuario,))
        items = c.fetchall()
        total = sum(row["precio"] * row["cantidad"] for row in items)
    else:
        items = session.get("carrito", [])
        total = sum(item["precio"] * item.get("cantidad", 1) for item in items)
    conn.close()
    return render_template("carrito.html", carrito=items, total=total)

@app.route("/add_carrito", methods=["POST"])
def add_carrito():
    producto_id = request.form.get("producto_id")
    nombre = request.form.get("nombre")
    precio = float(request.form.get("precio", 0))
    usuario = session.get("usuario")
    if not nombre or precio <= 0:
        flash("Datos inválidos", "error")
        return redirect(url_for("inicio"))
    if usuario:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id FROM productos WHERE id=?", (producto_id,))
        if not c.fetchone():
            flash("Producto no encontrado", "error")
            conn.close()
            return redirect(url_for("inicio"))
        c.execute("""INSERT INTO carrito (usuario, producto_id, cantidad)
            VALUES (?, ?, 1)
            ON CONFLICT(usuario, producto_id) DO UPDATE SET cantidad = cantidad + 1""",
            (usuario, producto_id))
        conn.commit()
        conn.close()
        flash("Añadido al carrito", "success")
    else:
        if "carrito" not in session:
            session["carrito"] = []
        carrito = session["carrito"]
        found = False
        for item in carrito:
            if item["nombre"] == nombre:
                item["cantidad"] = item.get("cantidad", 1) + 1
                found = True
                break
        if not found:
            carrito.append({"id": int(producto_id), "nombre": nombre, "precio": precio, "cantidad": 1})
        session["carrito"] = carrito
        flash("Añadido al carrito", "success")
    return redirect(url_for("inicio"))

@app.route("/remove_carrito/<int:producto_id>")
def remove_carrito(producto_id):
    usuario = session.get("usuario")
    if usuario:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM carrito WHERE usuario=? AND producto_id=?", (usuario, producto_id))
        conn.commit()
        conn.close()
    else:
        if "carrito" in session:
            session["carrito"] = [i for i in session["carrito"] if i.get("id") != producto_id]
    flash("Producto eliminado", "info")
    return redirect(url_for("carrito"))

@app.route("/vaciar_carrito")
def vaciar_carrito():
    usuario = session.get("usuario")
    if usuario:
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM carrito WHERE usuario=?", (usuario,))
        conn.commit()
        conn.close()
    else:
        session.pop("carrito", None)
    flash("Carrito vaciado", "info")
    return redirect(url_for("carrito"))

@app.route("/checkout")
def checkout():
    return redirect(url_for("datos_compra"))

@app.route("/datos_compra")
def datos_compra():
    if not session.get("usuario") and not session.get("carrito"):
        flash("Tu carrito está vacío", "error")
        return redirect(url_for("carrito"))
    return render_template("datos_compra.html")

@app.route("/procesar_compra", methods=["POST"])
def procesar_compra():
    nombre = request.form.get("nombre", "").strip()
    telefono = request.form.get("telefono", "").strip()
    direccion = request.form.get("direccion", "").strip()
    email = request.form.get("email", "").strip()
    usuario = session.get("usuario")
    if not nombre or not telefono or not direccion or not email:
        flash("Completa todos los campos", "error")
        return redirect(url_for("datos_compra"))
    conn = get_db()
    c = conn.cursor()
    if usuario:
        c.execute("""SELECT p.nombre, p.precio, c.cantidad
            FROM carrito c
            JOIN productos p ON c.producto_id = p.id
            WHERE c.usuario=?""", (usuario,))
        items = c.fetchall()
        total = sum(row["precio"] * row["cantidad"] for row in items)
        c.execute("""INSERT INTO compras (usuario, nombre, telefono, direccion, email, total)
            VALUES (?, ?, ?, ?, ?, ?)""", (usuario, nombre, telefono, direccion, email, total))
        compra_id = c.lastrowid
        for item in items:
            c.execute("""INSERT INTO compra_detalle (compra_id, producto_nombre, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)""", (compra_id, item["nombre"], item["cantidad"], item["precio"]))
        c.execute("DELETE FROM carrito WHERE usuario=?", (usuario,))
    else:
        items = session.get("carrito", [])
        total = sum(item["precio"] * item.get("cantidad", 1) for item in items) if items else 0
        c.execute("""INSERT INTO compras (nombre, telefono, direccion, email, total)
            VALUES (?, ?, ?, ?, ?)""", (nombre, telefono, direccion, email, total))
        compra_id = c.lastrowid
        for item in items:
            c.execute("""INSERT INTO compra_detalle (compra_id, producto_nombre, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)""", (compra_id, item["nombre"], item.get("cantidad", 1), item["precio"]))
        session["carrito"] = []
    conn.commit()
    conn.close()
    flash("Pedido realizado correctamente", "success")
    return render_template("checkout.html", total_checkout=total or 0)

@app.route("/admin")
def admin():
    if "usuario" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, nombre, precio, imagen, categoria FROM productos")
    productos = c.fetchall()
    c.execute("""SELECT c.id, c.usuario, c.nombre, c.telefono, c.direccion, c.email, c.total,
        strftime('%d/%m/%Y %H:%M', c.fecha) as fecha
        FROM compras c
        ORDER BY c.fecha DESC""")
    compras_raw = c.fetchall()
    compras = []
    for compra in compras_raw:
        c2 = conn.cursor()
        c2.execute("SELECT producto_nombre || ' x' || cantidad as item FROM compra_detalle WHERE compra_id=?", (compra["id"],))
        items = [row["item"] for row in c2.fetchall()]
        compra_dict = dict(compra)
        compra_dict["productos"] = ", ".join(items) if items else ""
        compras.append(compra_dict)
    c.execute("SELECT id, nombre, email, mensaje, strftime('%d/%m/%Y %H:%M', fecha) as fecha FROM mensajes ORDER BY fecha DESC")
    mensajes = c.fetchall()
    conn.close()
    return render_template("admin.html", productos=productos, compras=compras, mensajes=mensajes)

@app.route("/admin-test")
def admin_test():
    return "Admin route works!"

@app.route("/add", methods=["POST"])
def add():
    if "usuario" not in session:
        return redirect(url_for("login"))
    nombre = request.form.get("nombre", "").strip()
    precio = request.form.get("precio", "")
    categoria = request.form.get("categoria", "").strip()
    imagen = request.files.get("imagen")
    if not nombre or not precio or not categoria:
        flash("Completa todos los campos", "error")
        return redirect(url_for("admin"))
    try:
        precio = float(precio)
        if precio < 0:
            raise ValueError()
    except (ValueError, TypeError):
        flash("Precio inválido", "error")
        return redirect(url_for("admin"))
    filename = None
    if imagen and imagen.filename:
        if not allowed_file(imagen.filename):
            flash("Formato de imagen no permitido", "error")
            return redirect(url_for("admin"))
        filename = secure_filename(imagen.filename)
        upload_dir = os.path.join(BASE_DIR, "static", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        imagen.save(os.path.join(upload_dir, filename))
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO productos (nombre, precio, imagen, categoria) VALUES (?, ?, ?, ?)",
               (nombre, precio, filename, categoria))
    conn.commit()
    conn.close()
    flash("Producto añadido", "success")
    return redirect(url_for("admin"))

@app.route("/delete/<int:id>")
def delete(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT imagen FROM productos WHERE id=?", (id,))
    producto = c.fetchone()
    if producto and producto["imagen"]:
        ruta_img = os.path.join(BASE_DIR, "static", "uploads", producto["imagen"])
        if os.path.exists(ruta_img):
            os.remove(ruta_img)
    c.execute("DELETE FROM productos WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash("Producto eliminado", "success")
    return redirect(url_for("admin"))

@app.route("/contacto", methods=["POST"])
def contacto():
    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    mensaje = request.form.get("mensaje", "").strip()
    if not nombre or not email or not mensaje:
        flash("Completa todos los campos", "error")
        return redirect(url_for("inicio"))
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO mensajes (nombre, email, mensaje) VALUES (?, ?, ?)",
               (nombre, email, mensaje))
    conn.commit()
    conn.close()
    flash("Mensaje enviado correctamente", "success")
    return redirect(url_for("inicio"))

@app.route("/cambiar_password", methods=["POST"])
def cambiar_password():
    if "usuario" not in session:
        return redirect(url_for("login"))
    nueva = request.form.get("nueva", "").strip()
    if not nueva:
        flash("Contraseña vacía", "error")
        return redirect(url_for("admin"))
    flash("Contraseña cambiada (recuerda: admin / " + nueva + ")", "success")
    return redirect(url_for("admin"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host="0.0.0.0", port=port)
