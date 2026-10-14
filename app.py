import os
import sqlite3
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "cambia-esta-clave"

# La base de datos queda en la carpeta "instance", que el .gitignore de Python ya excluye
os.makedirs(app.instance_path, exist_ok=True)
DB = os.path.join(app.instance_path, "skillmatch.db")

CATEGORIAS = ["Programación", "Diseño", "Idiomas", "Música",
              "Marketing", "Matemáticas", "Otro"]


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                correo TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS habilidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK (tipo IN ('ofrezco', 'busco')),
                categoria TEXT NOT NULL,
                nombre TEXT NOT NULL,
                valor INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
            )
        """)
    conn.close()


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "usuario_id" not in session:
            flash("Inicia sesión para continuar.")
            return redirect(url_for("login"))
        return vista(*args, **kwargs)
    return envoltura


@app.route("/")
def inicio():
    return render_template("inicio.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        correo = request.form["correo"].strip().lower()
        password = request.form["password"]

        if not nombre or not correo or len(password) < 6:
            flash("Completa todos los campos. La contraseña debe tener mínimo 6 caracteres.")
            return render_template("registro.html")

        conn = get_db()
        try:
            with conn:
                conn.execute(
                    "INSERT INTO usuarios (nombre, correo, password) VALUES (?, ?, ?)",
                    (nombre, correo, generate_password_hash(password)),
                )
        except sqlite3.IntegrityError:
            flash("Ese correo ya está registrado.")
            return render_template("registro.html")
        finally:
            conn.close()

        flash("Registro exitoso. Ahora inicia sesión.")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"].strip().lower()
        password = request.form["password"]

        conn = get_db()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE correo = ?", (correo,)
        ).fetchone()
        conn.close()

        if usuario and check_password_hash(usuario["password"], password):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["nombre"] = usuario["nombre"]
            return redirect(url_for("perfil"))

        flash("Correo o contraseña incorrectos.")
        return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.")
    return redirect(url_for("inicio"))


@app.route("/perfil", methods=["GET", "POST"])
@login_requerido
def perfil():
    usuario_id = session["usuario_id"]
    conn = get_db()

    if request.method == "POST":
        tipo = request.form["tipo"]
        categoria = request.form["categoria"]
        nombre = request.form["nombre"].strip()
        try:
            valor = int(request.form.get("valor") or 0)
        except ValueError:
            valor = -1

        if (tipo not in ("ofrezco", "busco") or categoria not in CATEGORIAS
                or not nombre or valor < 0):
            flash("Revisa los datos de la habilidad.")
        else:
            with conn:
                conn.execute(
                    "INSERT INTO habilidades (usuario_id, tipo, categoria, nombre, valor) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (usuario_id, tipo, categoria, nombre, valor),
                )
            flash("Habilidad agregada.")
        conn.close()
        return redirect(url_for("perfil"))

    filas = conn.execute(
        "SELECT * FROM habilidades WHERE usuario_id = ? ORDER BY id", (usuario_id,)
    ).fetchall()
    conn.close()
    ofrezco = [f for f in filas if f["tipo"] == "ofrezco"]
    busco = [f for f in filas if f["tipo"] == "busco"]
    return render_template("perfil.html", ofrezco=ofrezco, busco=busco,
                           categorias=CATEGORIAS)


@app.route("/habilidad/<int:habilidad_id>/eliminar", methods=["POST"])
@login_requerido
def eliminar_habilidad(habilidad_id):
    conn = get_db()
    with conn:
        conn.execute(
            "DELETE FROM habilidades WHERE id = ? AND usuario_id = ?",
            (habilidad_id, session["usuario_id"]),
        )
    conn.close()
    flash("Habilidad eliminada.")
    return redirect(url_for("perfil"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
