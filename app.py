import os
import re
import sqlite3
import unicodedata
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


PALABRAS_VACIAS = {"clases", "clase", "curso", "ayuda", "del", "las", "los", "una",
                   "uno", "unos", "unas", "para", "con", "por", "que", "mis", "tus"}


def palabras_clave(texto):
    """Palabras relevantes de un texto: sin tildes, minúsculas, 3+ letras."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {p for p in re.findall(r"[a-z0-9]+", t)
            if len(p) >= 3 and p not in PALABRAS_VACIAS}


def calcular_diferencia(valor_doy, valor_recibo):
    """Devuelve (diferencia, texto) desde el punto de vista de quien da 'valor_doy'."""
    dif = valor_doy - valor_recibo
    if dif == 0:
        return 0, "Intercambio equilibrado: ambas habilidades tienen el mismo valor."
    if dif > 0:
        return dif, f"Lo que ofreces vale ${dif} más. La otra persona te compensa con ${dif}."
    return dif, f"Lo que recibes vale ${-dif} más. Tú compensas con ${-dif}."


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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS acuerdos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                proponente_id INTEGER NOT NULL,
                receptor_id INTEGER NOT NULL,
                nombre_prop TEXT NOT NULL,
                valor_prop INTEGER NOT NULL,
                nombre_rec TEXT NOT NULL,
                valor_rec INTEGER NOT NULL,
                estado TEXT NOT NULL DEFAULT 'propuesto'
                    CHECK (estado IN ('propuesto', 'aceptado', 'rechazado')),
                FOREIGN KEY (proponente_id) REFERENCES usuarios (id),
                FOREIGN KEY (receptor_id) REFERENCES usuarios (id)
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


@app.route("/matches")
@login_requerido
def matches():
    yo = session["usuario_id"]
    conn = get_db()
    mis_busco = conn.execute(
        "SELECT * FROM habilidades WHERE usuario_id = ? AND tipo = 'busco'", (yo,)
    ).fetchall()
    mis_ofrezco = conn.execute(
        "SELECT * FROM habilidades WHERE usuario_id = ? AND tipo = 'ofrezco'", (yo,)
    ).fetchall()
    ofrecen = conn.execute(
        "SELECT h.*, u.nombre AS usuario_nombre FROM habilidades h "
        "JOIN usuarios u ON u.id = h.usuario_id "
        "WHERE h.usuario_id != ? AND h.tipo = 'ofrezco'", (yo,)
    ).fetchall()
    buscan = conn.execute(
        "SELECT * FROM habilidades WHERE usuario_id != ? AND tipo = 'busco'", (yo,)
    ).fetchall()
    conn.close()

    mis_categorias = {h["categoria"] for h in mis_ofrezco}
    resultados = []
    for b in mis_busco:
        kw_b = palabras_clave(b["nombre"])
        for o in ofrecen:
            if o["categoria"] != b["categoria"]:
                continue
            comunes = sorted(kw_b & palabras_clave(o["nombre"]))
            mutuo_info = [x["nombre"] for x in buscan
                          if x["usuario_id"] == o["usuario_id"]
                          and x["categoria"] in mis_categorias]
            resultados.append({
                "otro_nombre": o["usuario_nombre"],
                "su_hab": o,
                "mi_busco": b,
                "score": 1 + len(comunes),
                "kw": comunes,
                "mutuo": bool(mutuo_info),
                "mutuo_info": mutuo_info,
            })
    resultados.sort(key=lambda m: (m["mutuo"], m["score"]), reverse=True)
    return render_template("matches.html", matches=resultados,
                           tiene_busco=bool(mis_busco))


@app.route("/acuerdo/<int:su_id>", methods=["GET", "POST"])
@login_requerido
def acuerdo(su_id):
    yo = session["usuario_id"]
    conn = get_db()
    su = conn.execute(
        "SELECT h.*, u.nombre AS usuario_nombre FROM habilidades h "
        "JOIN usuarios u ON u.id = h.usuario_id "
        "WHERE h.id = ? AND h.tipo = 'ofrezco' AND h.usuario_id != ?", (su_id, yo)
    ).fetchone()
    if su is None:
        conn.close()
        flash("Esa habilidad no está disponible para un acuerdo.")
        return redirect(url_for("matches"))

    mis_ofrezco = conn.execute(
        "SELECT * FROM habilidades WHERE usuario_id = ? AND tipo = 'ofrezco' ORDER BY id",
        (yo,),
    ).fetchall()

    try:
        mi_id = int(request.values.get("mi", ""))
    except ValueError:
        mi_id = None
    mi = next((h for h in mis_ofrezco if h["id"] == mi_id), None)

    if request.method == "POST":
        if mi is None:
            conn.close()
            flash("Elige una de tus habilidades para proponer el acuerdo.")
            return redirect(url_for("acuerdo", su_id=su_id))
        with conn:
            conn.execute(
                "INSERT INTO acuerdos (proponente_id, receptor_id, nombre_prop, "
                "valor_prop, nombre_rec, valor_rec) VALUES (?, ?, ?, ?, ?, ?)",
                (yo, su["usuario_id"], mi["nombre"], mi["valor"],
                 su["nombre"], su["valor"]),
            )
        conn.close()
        flash("Propuesta enviada.")
        return redirect(url_for("acuerdos"))

    conn.close()
    resultado = None
    if mi is not None:
        _, resultado = calcular_diferencia(mi["valor"], su["valor"])
    return render_template("acuerdo.html", su=su, mis_ofrezco=mis_ofrezco,
                           mi=mi, resultado=resultado)


@app.route("/acuerdos")
@login_requerido
def acuerdos():
    yo = session["usuario_id"]
    conn = get_db()
    filas = conn.execute(
        "SELECT a.*, up.nombre AS nombre_proponente, ur.nombre AS nombre_receptor "
        "FROM acuerdos a "
        "JOIN usuarios up ON up.id = a.proponente_id "
        "JOIN usuarios ur ON ur.id = a.receptor_id "
        "WHERE a.proponente_id = ? OR a.receptor_id = ? ORDER BY a.id DESC", (yo, yo)
    ).fetchall()
    conn.close()

    lista = []
    for a in filas:
        soy_proponente = a["proponente_id"] == yo
        if soy_proponente:
            doy_n, doy_v = a["nombre_prop"], a["valor_prop"]
            rec_n, rec_v = a["nombre_rec"], a["valor_rec"]
            otro = a["nombre_receptor"]
        else:
            doy_n, doy_v = a["nombre_rec"], a["valor_rec"]
            rec_n, rec_v = a["nombre_prop"], a["valor_prop"]
            otro = a["nombre_proponente"]
        _, texto = calcular_diferencia(doy_v, rec_v)
        lista.append({
            "id": a["id"], "estado": a["estado"], "soy_proponente": soy_proponente,
            "otro_nombre": otro, "doy_nombre": doy_n, "doy_valor": doy_v,
            "recibo_nombre": rec_n, "recibo_valor": rec_v, "resultado": texto,
        })
    return render_template("acuerdos.html", acuerdos=lista)


@app.route("/acuerdo/<int:acuerdo_id>/responder", methods=["POST"])
@login_requerido
def responder_acuerdo(acuerdo_id):
    accion = request.form.get("accion")
    if accion not in ("aceptado", "rechazado"):
        flash("Acción no válida.")
        return redirect(url_for("acuerdos"))
    conn = get_db()
    with conn:
        cur = conn.execute(
            "UPDATE acuerdos SET estado = ? "
            "WHERE id = ? AND receptor_id = ? AND estado = 'propuesto'",
            (accion, acuerdo_id, session["usuario_id"]),
        )
    conn.close()
    flash(f"Propuesta {'aceptada' if accion == 'aceptado' else 'rechazada'}." if cur.rowcount else "No se pudo actualizar esa propuesta.")
    return redirect(url_for("acuerdos"))


@app.route("/certificacion")
@login_requerido
def certificacion():
    return render_template("certificacion.html")


@app.route("/calificaciones")
@login_requerido
def calificaciones():
    return render_template("calificaciones.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
