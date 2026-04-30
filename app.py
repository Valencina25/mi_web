from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
from os import environ
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mi_web_secret_key_fija_2024")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tienda.db")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def init_db():
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

    # Crear o actualizar admin (migrar password a hash si es necesario)
    cursor.execute("SELECT id, password FROM usuarios WHERE usuario=?", ("admin",))
    admin = cursor.fetchone()
    if not admin:
        cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
                       ("admin", generate_password_hash("1962")))
    elif not admin["password"].startswith("pbkdf2:sha256"):
        cursor.execute("UPDATE usuarios SET password=? WHERE usuario=?",
                       (generate_password_hash("1962"), "admin"))

    conn.commit()
    conn.close()


init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------
# 🏠 TIENDA
# -------------------------
@app.route("/")
def inicio():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nombre, precio, imagen, categoria FROM productos")
    productos = cursor.fetchall()

    cursor.execute("SELECT DISTINCT categoria FROM productos")
    categorias = [c[0] for c in cursor.fetchall()]

    conn.close()
    return render_template("index.html", productos=productos, categorias=categorias)


# -------------------------
# 🔐 LOGIN
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")

        if not usuario or not password:
            flash("Completa todos los campos", "error")
            return redirect(url_for("login"))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT id, password FROM usuarios WHERE usuario=?", (usuario,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["usuario"] = usuario
            flash("Bienvenido " + usuario, "success")
            return redirect(url_for("admin"))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html")


# -------------------------
# 🚪 LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.pop("usuario", None)
    session.pop("carrito", None)
    flash("Sesión cerrada", "info")
    return redirect(url_for("inicio"))


# -------------------------
# 🛒 CARRITO (persistente)
# -------------------------
@app.route("/carrito")
def carrito():
    usuario = session.get("usuario")
    conn = get_db()
    cursor = conn.cursor()

    if usuario:
        items = session.get("carrito", [])
        total = sum(i["precio"] * i.get("cantidad", 1) for i in items)

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
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM productos WHERE id=?", (producto_id,))
        if not cursor.fetchone():
            flash("Producto no encontrado", "error")
            conn.close()
            return redirect(url_for("inicio"))

        cursor.execute("""
            INSERT INTO carrito (usuario, producto_id, cantidad)
            VALUES (?, ?, 1)
            ON CONFLICT(usuario, producto_id) DO UPDATE SET cantidad = cantidad + 1
        """, (usuario, producto_id))
        conn.commit()
        conn.close()
        flash("Añadido al carrito", "success")
    else:
        if "carrito" not in session:
            session["carrito"] = []
        carrito = session["carrito"]
        # Check if product already exists
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
        cursor = conn.cursor()
        cursor.execute("DELETE FROM carrito WHERE usuario=? AND producto_id=?", (usuario, producto_id))
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
        cursor = conn.cursor()
        cursor.execute("DELETE FROM carrito WHERE usuario=?", (usuario,))
        conn.commit()
        conn.close()
    else:
        session.pop("carrito", None)
    flash("Carrito vaciado", "info")
    return redirect(url_for("carrito"))


# -------------------------
# 💳 CHECKOUT
# -------------------------
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
    cursor = conn.cursor()

    if usuario:
        cursor.execute("""
            SELECT p.nombre, p.precio, c.cantidad
            FROM carrito c
            JOIN productos p ON c.producto_id = p.id
            WHERE c.usuario=?
        """, (usuario,))
        items = cursor.fetchall()

        total = sum(i["precio"] * i["cantidad"] for i in items)

        cursor.execute("""
            INSERT INTO compras (usuario, nombre, telefono, direccion, email, total)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (usuario, nombre, telefono, direccion, email, total))
        compra_id = cursor.lastrowid

        for item in items:
            cursor.execute("""
                INSERT INTO compra_detalle (compra_id, producto_nombre, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
            """, (compra_id, item["nombre"], item["cantidad"], item["precio"]))

        cursor.execute("DELETE FROM carrito WHERE usuario=?", (usuario,))
    else:
        items = session.get("carrito", [])
        total = sum(i["precio"] * i.get("cantidad", 1) for i in items) if items else 0

        cursor.execute("""
            INSERT INTO compras (nombre, telefono, direccion, email, total)
            VALUES (?, ?, ?, ?, ?)
        """, (nombre, telefono, direccion, email, total))
        compra_id = cursor.lastrowid

        for item in items:
            cursor.execute("""
                INSERT INTO compra_detalle (compra_id, producto_nombre, cantidad, precio_unitario)
                VALUES (?, ?, ?, ?)
            """, (compra_id, item["nombre"], item.get("cantidad", 1), item["precio"]))

        session["carrito"] = []

    conn.commit()
    conn.close()
    flash("Pedido realizado correctamente", "success")
    return render_template("checkout.html", total_checkout=total or 0)


# -------------------------
# 🧑‍🌾 ADMIN (PROTEGIDO)
# -------------------------
@app.route("/admin")
def admin():

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, nombre, precio, imagen, categoria FROM productos")
    productos = cursor.fetchall()

    cursor.execute("""
        SELECT c.id, c.usuario, c.nombre, c.telefono, c.direccion, c.email, c.total, c.fecha,
               GROUP_CONCAT(d.producto_nombre || ' x' || d.cantidad) as productos
        FROM compras c
        LEFT JOIN compra_detalle d ON c.id = d.compra_id
        GROUP BY c.id
        ORDER BY c.fecha DESC
    """)
    compras = cursor.fetchall()

    cursor.execute("SELECT id, nombre, email, mensaje, fecha FROM mensajes ORDER BY fecha DESC")
    mensajes = cursor.fetchall()

    conn.close()

    return render_template("admin.html", productos=productos, compras=compras, mensajes=mensajes)


# -------------------------
# ➕ AÑADIR PRODUCTO
# -------------------------
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
    except:
        flash("Precio inválido", "error")
        return redirect(url_for("admin"))

    filename = None
    if imagen and imagen.filename:
        if not allowed_file(imagen.filename):
            flash("Formato de imagen no permitido", "error")
            return redirect(url_for("admin"))

        filename = secure_filename(imagen.filename)
        os.makedirs("static/uploads", exist_ok=True)
        imagen.save(os.path.join("static/uploads", filename))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO productos (nombre, precio, imagen, categoria)
        VALUES (?, ?, ?, ?)
    """, (nombre, precio, filename, categoria))

    conn.commit()
    conn.close()

    flash("Producto añadido", "success")
    return redirect(url_for("admin"))


# -------------------------
# 🗑️ BORRAR
# -------------------------
@app.route("/delete/<int:id>")
def delete(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT imagen FROM productos WHERE id=?", (id,))
    producto = cursor.fetchone()

    if producto and producto["imagen"]:
        ruta_img = os.path.join("static/uploads", producto["imagen"])
        if os.path.exists(ruta_img):
            os.remove(ruta_img)

    cursor.execute("DELETE FROM productos WHERE id=?", (id,))

    conn.commit()
    conn.close()

    flash("Producto eliminado", "success")
    return redirect(url_for("admin"))


# -------------------------
# 📩 CONTACTO
# -------------------------
@app.route("/contacto", methods=["POST"])
def contacto():

    nombre = request.form.get("nombre", "").strip()
    email = request.form.get("email", "").strip()
    mensaje = request.form.get("mensaje", "").strip()

    if not nombre or not email or not mensaje:
        flash("Completa todos los campos", "error")
        return redirect(url_for("inicio"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO mensajes (nombre, email, mensaje) VALUES (?, ?, ?)",
                   (nombre, email, mensaje))
    conn.commit()
    conn.close()

    flash("Mensaje enviado correctamente", "success")
    return redirect(url_for("inicio"))


# -------------------------
# 🔑 CAMBIAR CONTRASEÑA
# -------------------------
@app.route("/cambiar_password", methods=["POST"])
def cambiar_password():

    if "usuario" not in session:
        return redirect(url_for("login"))

    nueva = request.form.get("nueva", "").strip()
    if not nueva:
        flash("Contraseña vacía", "error")
        return redirect(url_for("admin"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE usuarios SET password=? WHERE usuario=?", (generate_password_hash(nueva), session["usuario"]))
    conn.commit()
    conn.close()

    flash("Contraseña actualizada", "success")
    return redirect(url_for("admin"))


# -------------------------
# 🚀 RUN
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)