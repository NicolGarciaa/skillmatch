"""Carga usuarios y habilidades de ejemplo para la demostración de SkillMatch.

Uso (con el entorno virtual activado):
    python datos_demo.py

Es seguro correrlo varias veces: no duplica usuarios que ya existen.
Contraseña de todas las cuentas demo: demo1234
"""
import sqlite3
from werkzeug.security import generate_password_hash

import app as skillmatch

PASSWORD = "demo1234"

# (nombre, correo, [(tipo, categoría, habilidad, valor), ...])
DEMO = [
    ("Laura Gómez", "laura@demo.com", [
        ("ofrezco", "Programación", "Clases de Python", 50000),
        ("busco", "Diseño", "Diseño de logo", 30000),
        ("busco", "Marketing", "Publicidad en redes", 20000),
    ]),
    ("Mateo Ruiz", "mateo@demo.com", [
        ("ofrezco", "Diseño", "Logo y branding", 40000),
        ("busco", "Programación", "Aprender Python", 0),
    ]),
    ("Sofía Pérez", "sofia@demo.com", [
        ("ofrezco", "Marketing", "Publicidad en redes sociales", 30000),
        ("busco", "Programación", "Página web sencilla", 0),
    ]),
    ("Andrés Torres", "andres@demo.com", [
        ("ofrezco", "Idiomas", "Clases de inglés", 25000),
        ("busco", "Música", "Clases de guitarra", 0),
    ]),
]


# Intercambios ya realizados entre usuarios demo, con sus calificaciones:
# (proponente, receptor, habilidad_prop, valor_prop, habilidad_rec, valor_rec,
#  (puntuación del proponente al receptor, comentario), (del receptor al proponente, comentario))
HISTORIAL = [
    ("sofia@demo.com", "andres@demo.com", "Publicidad en redes sociales", 30000,
     "Clases de inglés", 25000,
     (5, "Muy puntual y clara explicando."), (5, "Excelente campaña, la recomiendo.")),
    ("mateo@demo.com", "andres@demo.com", "Logo y branding", 40000,
     "Clases de inglés", 25000,
     (4, "Buen intercambio."), (5, "Diseño impecable y rápido.")),
    ("mateo@demo.com", "sofia@demo.com", "Logo y branding", 40000,
     "Publicidad en redes sociales", 30000,
     (5, "Muy profesional."), (4, "Buen trabajo, entregado a tiempo.")),
]


def cargar_historial(conn):
    """Crea intercambios aceptados con calificaciones de ejemplo (sin duplicarlos)."""
    ids = {f["correo"]: f["id"] for f in conn.execute("SELECT id, correo FROM usuarios")}
    nuevos = 0
    for prop, rec, hp, vp, hr, vr, cal_prop, cal_rec in HISTORIAL:
        if prop not in ids or rec not in ids:
            continue
        existe = conn.execute(
            "SELECT 1 FROM acuerdos WHERE proponente_id = ? AND receptor_id = ? "
            "AND nombre_prop = ? AND nombre_rec = ? AND estado = 'aceptado'",
            (ids[prop], ids[rec], hp, hr),
        ).fetchone()
        if existe:
            continue
        with conn:
            cur = conn.execute(
                "INSERT INTO acuerdos (proponente_id, receptor_id, nombre_prop, valor_prop, "
                "nombre_rec, valor_rec, estado) VALUES (?, ?, ?, ?, ?, ?, 'aceptado')",
                (ids[prop], ids[rec], hp, vp, hr, vr),
            )
            for calificador, calificado, (punt, com) in (
                (ids[prop], ids[rec], cal_prop), (ids[rec], ids[prop], cal_rec)
            ):
                conn.execute(
                    "INSERT INTO calificaciones (acuerdo_id, calificador_id, calificado_id, "
                    "puntuacion, comentario) VALUES (?, ?, ?, ?, ?)",
                    (cur.lastrowid, calificador, calificado, punt, com),
                )
        nuevos += 1
    return nuevos


CERTIFICADOR = ("Certificador Demo", "certificador@demo.com")


def cargar_certificaciones(conn):
    """Crea la cuenta de certificador y deja una certificación aprobada y una pendiente."""
    with conn:
        try:
            conn.execute(
                "INSERT INTO usuarios (nombre, correo, password, rol) VALUES (?, ?, ?, 'certificador')",
                (CERTIFICADOR[0], CERTIFICADOR[1], generate_password_hash(PASSWORD)),
            )
        except sqlite3.IntegrityError:
            conn.execute("UPDATE usuarios SET rol = 'certificador' WHERE correo = ?", (CERTIFICADOR[1],))
    ids = {f["correo"]: f["id"] for f in conn.execute("SELECT id, correo FROM usuarios")}
    cert_id = ids[CERTIFICADOR[1]]
    # (correo del dueño, habilidad, estado, evidencia, observación)
    casos = [
        ("mateo@demo.com", "Logo y branding", "aprobada",
         "Portafolio con 15 marcas diseñadas y 4 años de experiencia.", "Portafolio verificado."),
        ("andres@demo.com", "Clases de inglés", "pendiente",
         "Certificado TOEFL (100 puntos) y 3 años dando clases particulares.", ""),
    ]
    nuevos = 0
    for correo, hab, estado, evidencia, obs in casos:
        fila = conn.execute(
            "SELECT * FROM habilidades WHERE usuario_id = ? AND nombre = ? AND tipo = 'ofrezco'",
            (ids.get(correo), hab),
        ).fetchone()
        if fila is None:
            continue
        if conn.execute("SELECT 1 FROM certificaciones WHERE habilidad_id = ?", (fila["id"],)).fetchone():
            continue
        with conn:
            conn.execute(
                "INSERT INTO certificaciones (habilidad_id, solicitante_id, certificador_id, "
                "nombre_habilidad, categoria, evidencia, estado, observacion) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (fila["id"], ids[correo], cert_id if estado != "pendiente" else None,
                 fila["nombre"], fila["categoria"], evidencia, estado, obs),
            )
        nuevos += 1
    return nuevos


def main():
    skillmatch.init_db()
    conn = skillmatch.get_db()
    creados = 0
    for nombre, correo, habilidades in DEMO:
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO usuarios (nombre, correo, password) VALUES (?, ?, ?)",
                    (nombre, correo, generate_password_hash(PASSWORD)),
                )
        except sqlite3.IntegrityError:
            continue  # ya existe
        with conn:
            for tipo, categoria, hab, valor in habilidades:
                conn.execute(
                    "INSERT INTO habilidades (usuario_id, tipo, categoria, nombre, valor) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (cur.lastrowid, tipo, categoria, hab, valor),
                )
        creados += 1
    historial = cargar_historial(conn)
    certificaciones = cargar_certificaciones(conn)
    conn.close()
    print(f"Certificador: {CERTIFICADOR[1]} (certificaciones de ejemplo creadas: {certificaciones}).")
    print(f"Intercambios con calificaciones de ejemplo creados: {historial}.")
    print(f"Usuarios demo creados: {creados} (los que ya existían se omitieron).")
    print(f"Correos: {', '.join(c for _, c, _ in DEMO)}  |  Contraseña: {PASSWORD}")


if __name__ == "__main__":
    main()
