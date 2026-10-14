import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash

app = Flask(__name__)
app.secret_key = "cambia-esta-clave"

# La base de datos queda en la carpeta "instance", que el .gitignore de Python ya excluye
os.makedirs(app.instance_path, exist_ok=True)
DB = os.path.join(app.instance_path, "skillmatch.db")


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
    conn.close()


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

        flash("Registro exitoso.")
        return redirect(url_for("inicio"))

    return render_template("registro.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
