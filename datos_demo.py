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
    conn.close()
    print(f"Usuarios demo creados: {creados} (los que ya existían se omitieron).")
    print(f"Correos: {', '.join(c for _, c, _ in DEMO)}  |  Contraseña: {PASSWORD}")


if __name__ == "__main__":
    main()
