import os
import re
import secrets
import sqlite3
import unicodedata
from functools import wraps
from flask import (Flask, render_template, request, redirect,
                   url_for, flash, session, abort)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SKILLMATCH_SECRET", "cambia-esta-clave")
app.config.setdefault("CSRF", True)

# La base de datos queda en la carpeta "instance", que el .gitignore de Python ya excluye
os.makedirs(app.instance_path, exist_ok=True)
app.config["DB"] = os.path.join(app.instance_path, "skillmatch.db")

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


def token_csrf():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


app.jinja_env.globals["csrf_token"] = token_csrf


@app.before_request
def verificar_csrf():
    """Rechaza cualquier POST que no traiga el token de seguridad de la sesión."""
    if request.method == "POST" and app.config["CSRF"]:
        enviado = request.form.get("_csrf", "")
        esperado = session.get("_csrf", "")
        if not enviado or not esperado or not secrets.compare_digest(enviado, esperado):
            abort(400)


@app.errorhandler(400)
def solicitud_invalida(error):
    return "Solicitud no válida (falta el token de seguridad). Vuelve atrás y recarga la página.", 400


def get_db():
    conn = sqlite3.connect(app.config["DB"])
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                acuerdo_id INTEGER NOT NULL,
                calificador_id INTEGER NOT NULL,
                calificado_id INTEGER NOT NULL,
                puntuacion INTEGER NOT NULL CHECK (puntuacion BETWEEN 1 AND 5),
                comentario TEXT NOT NULL DEFAULT '',
                UNIQUE (acuerdo_id, calificador_id),
                FOREIGN KEY (acuerdo_id) REFERENCES acuerdos (id),
                FOREIGN KEY (calificador_id) REFERENCES usuarios (id),
                FOREIGN KEY (calificado_id) REFERENCES usuarios (id)
            )
        """)
    conn.close()


def reputaciones(conn):
    """Promedio y cantidad de calificaciones por usuario: {usuario_id: (promedio, cantidad)}."""
    filas = conn.execute(
        "SELECT calificado_id, AVG(puntuacion) AS prom, COUNT(*) AS n "
        "FROM calificaciones GROUP BY calificado_id"
    ).fetchall()
    return {f["calificado_id"]: (round(f["prom"], 1), f["n"]) for f in filas}


@app.template_filter("estrellas")
def estrellas(valor):
    n = max(0, min(5, int(round(valor))))
    return "★" * n + "☆" * (5 - n)


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
        if (len(nombre) > 60 or len(correo) > 120 or len(password) > 128
                or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", correo)):
            flash("Revisa el nombre y el correo (el correo debe tener un formato válido).")
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
                or not nombre or len(nombre) > 80 or valor < 0 or valor > 100_000_000):
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
    rep = reputaciones(conn).get(usuario_id)
    conn.close()
    ofrezco = [f for f in filas if f["tipo"] == "ofrezco"]
    busco = [f for f in filas if f["tipo"] == "busco"]
    return render_template("perfil.html", ofrezco=ofrezco, busco=busco,
                           categorias=CATEGORIAS, rep=rep)


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
    reps = reputaciones(conn)
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
                "rep": reps.get(o["usuario_id"]),
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
        repetida = conn.execute(
            "SELECT 1 FROM acuerdos WHERE proponente_id = ? AND receptor_id = ? "
            "AND nombre_prop = ? AND nombre_rec = ? AND estado = 'propuesto'",
            (yo, su["usuario_id"], mi["nombre"], su["nombre"]),
        ).fetchone()
        if repetida:
            conn.close()
            flash("Ya enviaste una propuesta igual que sigue pendiente.")
            return redirect(url_for("acuerdos"))
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

    rep_su = reputaciones(conn).get(su["usuario_id"])
    conn.close()
    resultado = None
    if mi is not None:
        _, resultado = calcular_diferencia(mi["valor"], su["valor"])
    return render_template("acuerdo.html", su=su, mis_ofrezco=mis_ofrezco,
                           mi=mi, resultado=resultado, rep_su=rep_su)


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
    calificados = {r["acuerdo_id"] for r in conn.execute(
        "SELECT acuerdo_id FROM calificaciones WHERE calificador_id = ?", (yo,))}
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
            "ya_califique": a["id"] in calificados,
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
    yo = session["usuario_id"]
    conn = get_db()
    pendientes = conn.execute(
        "SELECT a.id, "
        "CASE WHEN a.proponente_id = ? THEN ur.nombre ELSE up.nombre END AS otro_nombre, "
        "CASE WHEN a.proponente_id = ? THEN a.nombre_rec ELSE a.nombre_prop END AS recibo_nombre "
        "FROM acuerdos a "
        "JOIN usuarios up ON up.id = a.proponente_id "
        "JOIN usuarios ur ON ur.id = a.receptor_id "
        "WHERE a.estado = 'aceptado' AND (a.proponente_id = ? OR a.receptor_id = ?) "
        "AND NOT EXISTS (SELECT 1 FROM calificaciones c "
        "WHERE c.acuerdo_id = a.id AND c.calificador_id = ?) ORDER BY a.id DESC",
        (yo, yo, yo, yo, yo),
    ).fetchall()
    recibidas = conn.execute(
        "SELECT c.*, u.nombre AS de_nombre FROM calificaciones c "
        "JOIN usuarios u ON u.id = c.calificador_id "
        "WHERE c.calificado_id = ? ORDER BY c.id DESC", (yo,)
    ).fetchall()
    hechas = conn.execute(
        "SELECT c.*, u.nombre AS para_nombre FROM calificaciones c "
        "JOIN usuarios u ON u.id = c.calificado_id "
        "WHERE c.calificador_id = ? ORDER BY c.id DESC", (yo,)
    ).fetchall()
    rep = reputaciones(conn).get(yo)
    conn.close()
    return render_template("calificaciones.html", pendientes=pendientes,
                           recibidas=recibidas, hechas=hechas, rep=rep)


@app.route("/calificar/<int:acuerdo_id>", methods=["GET", "POST"])
@login_requerido
def calificar(acuerdo_id):
    yo = session["usuario_id"]
    conn = get_db()
    a = conn.execute(
        "SELECT a.*, up.nombre AS nombre_proponente, ur.nombre AS nombre_receptor "
        "FROM acuerdos a "
        "JOIN usuarios up ON up.id = a.proponente_id "
        "JOIN usuarios ur ON ur.id = a.receptor_id "
        "WHERE a.id = ? AND a.estado = 'aceptado' "
        "AND (a.proponente_id = ? OR a.receptor_id = ?)", (acuerdo_id, yo, yo)
    ).fetchone()
    if a is None:
        conn.close()
        flash("Ese intercambio no está disponible para calificar.")
        return redirect(url_for("calificaciones"))

    ya = conn.execute(
        "SELECT 1 FROM calificaciones WHERE acuerdo_id = ? AND calificador_id = ?",
        (acuerdo_id, yo),
    ).fetchone()
    if ya:
        conn.close()
        flash("Ya calificaste este intercambio.")
        return redirect(url_for("calificaciones"))

    soy_proponente = a["proponente_id"] == yo
    otro_id = a["receptor_id"] if soy_proponente else a["proponente_id"]
    otro_nombre = a["nombre_receptor"] if soy_proponente else a["nombre_proponente"]
    recibo = a["nombre_rec"] if soy_proponente else a["nombre_prop"]

    if request.method == "POST":
        try:
            puntuacion = int(request.form.get("puntuacion", ""))
        except ValueError:
            puntuacion = 0
        comentario = request.form.get("comentario", "").strip()
        if not 1 <= puntuacion <= 5 or len(comentario) > 300:
            conn.close()
            flash("Revisa la puntuación (de 1 a 5) y el comentario (máximo 300 caracteres).")
            return render_template("calificar.html", acuerdo_id=acuerdo_id,
                                   otro_nombre=otro_nombre, recibo=recibo)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO calificaciones (acuerdo_id, calificador_id, calificado_id, "
                    "puntuacion, comentario) VALUES (?, ?, ?, ?, ?)",
                    (acuerdo_id, yo, otro_id, puntuacion, comentario),
                )
        except sqlite3.IntegrityError:
            flash("Ya calificaste este intercambio.")
        else:
            flash("Gracias por tu calificación.")
        finally:
            conn.close()
        return redirect(url_for("calificaciones"))

    conn.close()
    return render_template("calificar.html", acuerdo_id=acuerdo_id,
                           otro_nombre=otro_nombre, recibo=recibo)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
