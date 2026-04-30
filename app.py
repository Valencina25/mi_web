from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import DictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mi_web_secret_key_fija_2024")

# PostgreSQL en Render, SQLite local
DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = False

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    # Verificar que no sea localhost (configuración errónea)
    if "127.0.0.1" not in DATABASE_URL and "localhost" not in DATABASE_URL:
        USE_POSTGRES = True
    else:
        print("WARNING: DATABASE_URL apunta a localhost, usando SQLite")
        DATABASE_URL = None

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


def get_db():
    if USE_POSTGRES:
        try:
            conn = psycopg2.connect(DATABASE_URL, cursor_factory=DictCursor)
            return conn
        except Exception as e:
            print(f"PostgreSQL connection failed: {e}, falling back to SQLite")
    import sqlite3
    conn = sqlite3.connect("tienda.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    print(f"Initializing database... USE_POSTGRES={USE_POSTGRES}")
    conn = get_db()
    cursor = conn.cursor()

    if USE_POSTGRES:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                precio REAL,
                imagen TEXT,
                categoria TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                usuario TEXT UNIQUE,
                password TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carrito (
                id SERIAL PRIMARY KEY,
                usuario TEXT,
                producto_id INTEGER,
                cantidad INTEGER DEFAULT 1,
                UNIQUE(usuario, producto_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compras (
                id SERIAL PRIMARY KEY,
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
                id SERIAL PRIMARY KEY,
                compra_id INTEGER,
                producto_nombre TEXT,
                cantidad INTEGER,
                precio_unitario REAL,
                FOREIGN KEY (compra_id) REFERENCES compras(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id SERIAL PRIMARY KEY,
                nombre TEXT,
                email TEXT,
                mensaje TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        import sqlite3
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT, precio REAL, imagen TEXT, categoria TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE, password TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carrito (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT, producto_id INTEGER, cantidad INTEGER DEFAULT 1,
                UNIQUE(usuario, producto_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT, nombre TEXT, telefono TEXT, direccion TEXT,
                email TEXT, total REAL, fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compra_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                compra_id INTEGER, producto_nombre TEXT, cantidad INTEGER,
                precio_unitario REAL, FOREIGN KEY (compra_id) REFERENCES compras(id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mensajes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT, email TEXT, mensaje TEXT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Crear admin si no existe
    cursor.execute("SELECT id, password FROM usuarios WHERE usuario=%s", ("admin",))
    admin = cursor.fetchone()

    if not admin:
        cursor.execute("INSERT INTO usuarios (usuario, password) VALUES (%s, %s)",
                       ("admin", generate_password_hash("1962")))
    elif not admin["password"].startswith("pbkdf2:sha256"):
        cursor.execute("UPDATE usuarios SET password=%s WHERE usuario=%s",
                       (generate_password_hash("1962"), "admin"))

    conn.commit()
    conn.close()


init_db()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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
        cursor.execute("SELECT id, password FROM usuarios WHERE usuario=%s", (usuario,))
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
        cursor.execute("""
            SELECT p.id, p.nombre, p.precio, p.imagen, c.cantidad
            FROM carrito c
            JOIN productos p ON c.producto_id = p.id
            WHERE c.usuario = %s
        """, (usuario,))
        items = cursor.fetchall()
        total = sum(i["precio"] * i["cantidad"] for i in items)
    else:
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
        cursor.execute("SELECT id FROM productos WHERE id=%s", (producto_id,))
        if not cursor.fetchone():
            flash("Producto no encontrado", "error")
            conn.close()
            return redirect(url_for("inicio"))

        cursor.execute("""
            INSERT INTO carrito (usuario, producto_id, cantidad)
            VALUES (%s, %s, 1)
            ON CONFLICT(usuario, producto_id) DO UPDATE SET cantidad = carrito.cantidad + 1
        """, (usuario, producto_id))
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
        cursor = conn.cursor()
        cursor.execute("DELETE FROM carrito WHERE usuario=%s AND producto_id=%s", (usuario, producto_id))
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
        cursor.execute("DELETE FROM carrito WHERE usuario=%s", (usuario,))
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
            WHERE c.usuario=%s
        """, (usuario,))
        items = cursor.fetchall()
        total = sum(i["precio"] * i["cantidad"] for i in items)

        cursor.execute("""
            INSERT INTO compras (usuario, nombre, telefono, direccion, email, total)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (usuario, nombre, telefono, direccion, email, total))
        compra_id = cursor.lastrowid

        for item in items:
            cursor.execute("""
                INSERT INTO compra_detalle (compra_id, producto_nombre, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s)
            """, (compra_id, item["nombre"], item["cantidad"], item["precio"]))

        cursor.execute("DELETE FROM carrito WHERE usuario=%s", (usuario,))
    else:
        items = session.get("carrito", [])
        total = sum(i["precio"] * i.get("cantidad", 1) for i in items) if items else 0

        cursor.execute("""
            INSERT INTO compras (nombre, telefono, direccion, email, total)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre, telefono, direccion, email, total))
        compra_id = cursor.lastrowid

        for item in items:
            cursor.execute("""
                INSERT INTO compra_detalle (compra_id, producto_nombre, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s)
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
               STRING_AGG(d.producto_nombre || ' x' || d.cantidad, ', ') as productos
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
        VALUES (%s, %s, %s, %s)
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

    cursor.execute("SELECT imagen FROM productos WHERE id=%s", (id,))
    producto = cursor.fetchone()

    if producto and producto["imagen"]:
        ruta_img = os.path.join("static/uploads", producto["imagen"])
        if os.path.exists(ruta_img):
            os.remove(ruta_img)

    cursor.execute("DELETE FROM productos WHERE id=%s", (id,))

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
    cursor.execute("INSERT INTO mensajes (nombre, email, mensaje) VALUES (%s, %s, %s)",
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
    cursor.execute("UPDATE usuarios SET password=%s WHERE usuario=%s",
                   (generate_password_hash(nueva), session["usuario"]))
    conn.commit()
    conn.close()

    flash("Contraseña actualizada", "success")
    return redirect(url_for("admin"))


# -------------------------
# 🚀 RUN
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
