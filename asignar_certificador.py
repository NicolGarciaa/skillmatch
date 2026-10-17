"""Convierte a un usuario ya registrado en certificador.

Uso (con el entorno virtual activado):
    python asignar_certificador.py correo@ejemplo.com

El usuario debe cerrar sesión y volver a entrar para ver su vista de certificador.
"""
import sys

import app as skillmatch


def asignar(correo):
    """Marca como certificador al usuario con ese correo. Devuelve True si existía."""
    conn = skillmatch.get_db()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE usuarios SET rol = 'certificador' WHERE correo = ?",
                (correo.strip().lower(),),
            )
        return cur.rowcount > 0
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python asignar_certificador.py correo@ejemplo.com")
        sys.exit(1)
    skillmatch.init_db()
    if asignar(sys.argv[1]):
        print(f"{sys.argv[1]} ahora es certificador. Debe cerrar sesión y volver a entrar.")
    else:
        print(f"No existe ningún usuario registrado con el correo {sys.argv[1]}.")
        sys.exit(1)
