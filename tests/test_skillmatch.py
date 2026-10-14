"""Pruebas automáticas de SkillMatch.

Ejecutar desde la carpeta del proyecto, con el entorno virtual activado:
    python -m unittest tests.test_skillmatch -v

Cada prueba usa una base de datos temporal, así que no toca tus datos reales.
Formato del docstring: "ID | Descripción | Resultado esperado".
"""
import os
import re
import sqlite3
import tempfile
import unittest

import app as skillmatch


def texto(respuesta):
    return respuesta.get_data(as_text=True)


class BaseTest(unittest.TestCase):
    CSRF = False

    def setUp(self):
        fd, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        skillmatch.app.config["DB"] = self.ruta
        skillmatch.app.config["CSRF"] = self.CSRF
        skillmatch.app.config["TESTING"] = True
        skillmatch.init_db()

    def tearDown(self):
        skillmatch.app.config["CSRF"] = True
        os.remove(self.ruta)

    # ---- ayudas ----
    def cliente(self):
        return skillmatch.app.test_client()

    def registrar(self, c, nombre, correo, password="123456"):
        return c.post("/registro", data={"nombre": nombre, "correo": correo, "password": password},
                      follow_redirects=True)

    def entrar(self, c, correo, password="123456"):
        return c.post("/login", data={"correo": correo, "password": password}, follow_redirects=True)

    def usuario(self, nombre, correo):
        c = self.cliente()
        self.registrar(c, nombre, correo)
        self.entrar(c, correo)
        return c

    def agregar(self, c, tipo, categoria, nombre, valor=0):
        return c.post("/perfil", data={"tipo": tipo, "categoria": categoria,
                                       "nombre": nombre, "valor": str(valor)},
                      follow_redirects=True)

    def consulta(self, sql, params=()):
        conn = sqlite3.connect(self.ruta)
        conn.row_factory = sqlite3.Row
        try:
            return conn.execute(sql, params).fetchall()
        finally:
            conn.close()

    def id_habilidad(self, nombre):
        return self.consulta("SELECT id FROM habilidades WHERE nombre = ?", (nombre,))[0]["id"]


class PruebasRegistro(BaseTest):
    def test_registro_exitoso(self):
        """CP-01 | Registrar un usuario con datos válidos | Muestra 'Registro exitoso' y lo envía al login"""
        r = self.registrar(self.cliente(), "Ana", "ana@a.com")
        self.assertIn("Registro exitoso", texto(r))
        self.assertIn("Iniciar sesión", texto(r))

    def test_correo_duplicado(self):
        """CP-02 | Registrar dos veces el mismo correo | Rechaza con 'Ese correo ya está registrado'"""
        c = self.cliente()
        self.registrar(c, "Ana", "ana@a.com")
        r = self.registrar(c, "Otra", "ANA@a.com")
        self.assertIn("ya está registrado", texto(r))
        self.assertEqual(len(self.consulta("SELECT * FROM usuarios")), 1)

    def test_password_corta(self):
        """CP-03 | Registrar con contraseña de menos de 6 caracteres | Rechaza y no crea el usuario"""
        r = self.registrar(self.cliente(), "Ana", "ana@a.com", "123")
        self.assertIn("mínimo 6 caracteres", texto(r))
        self.assertEqual(len(self.consulta("SELECT * FROM usuarios")), 0)

    def test_correo_invalido(self):
        """CP-04 | Registrar con un correo sin formato válido | Rechaza y no crea el usuario"""
        r = self.registrar(self.cliente(), "Ana", "ana-sin-arroba")
        self.assertIn("formato válido", texto(r))
        self.assertEqual(len(self.consulta("SELECT * FROM usuarios")), 0)

    def test_password_cifrada(self):
        """CP-05 | Revisar cómo se guarda la contraseña | No está en texto plano (se guarda un hash)"""
        self.registrar(self.cliente(), "Ana", "ana@a.com", "secreta123")
        guardada = self.consulta("SELECT password FROM usuarios")[0]["password"]
        self.assertNotEqual(guardada, "secreta123")
        self.assertNotIn("secreta123", guardada)


class PruebasSesion(BaseTest):
    def test_login_correcto(self):
        """CP-06 | Iniciar sesión con credenciales correctas | Entra a 'Mi perfil'"""
        c = self.cliente()
        self.registrar(c, "Ana", "ana@a.com")
        self.assertIn("Mi perfil", texto(self.entrar(c, "ana@a.com")))

    def test_password_incorrecta(self):
        """CP-07 | Iniciar sesión con contraseña incorrecta | Muestra 'Correo o contraseña incorrectos'"""
        c = self.cliente()
        self.registrar(c, "Ana", "ana@a.com")
        self.assertIn("incorrectos", texto(self.entrar(c, "ana@a.com", "equivocada")))

    def test_correo_inexistente(self):
        """CP-08 | Iniciar sesión con un correo que no existe | Muestra 'Correo o contraseña incorrectos'"""
        self.assertIn("incorrectos", texto(self.entrar(self.cliente(), "nadie@a.com")))

    def test_rutas_protegidas(self):
        """CP-09 | Entrar sin sesión a perfil, coincidencias, acuerdos, certificación y calificaciones | Redirige al login"""
        c = self.cliente()
        for ruta in ["/perfil", "/matches", "/acuerdos", "/certificacion", "/calificaciones"]:
            r = c.get(ruta)
            self.assertEqual(r.status_code, 302, ruta)
            self.assertTrue(r.headers["Location"].endswith("/login"), ruta)

    def test_logout(self):
        """CP-10 | Cerrar sesión y volver a pedir el perfil | La sesión se cierra y pide iniciar sesión de nuevo"""
        c = self.usuario("Ana", "ana@a.com")
        c.get("/logout")
        self.assertEqual(c.get("/perfil").status_code, 302)


class PruebasPerfil(BaseTest):
    def test_agregar_habilidad(self):
        """CP-11 | Agregar una habilidad válida | Se guarda y aparece en el perfil"""
        c = self.usuario("Ana", "ana@a.com")
        r = self.agregar(c, "ofrezco", "Programación", "Clases de Python", 50000)
        self.assertIn("Habilidad agregada", texto(r))
        self.assertIn("Clases de Python", texto(c.get("/perfil")))

    def test_nombre_vacio(self):
        """CP-12 | Agregar una habilidad sin nombre | Rechaza con 'Revisa los datos'"""
        c = self.usuario("Ana", "ana@a.com")
        self.assertIn("Revisa los datos", texto(self.agregar(c, "ofrezco", "Programación", "   ", 10)))

    def test_valor_invalido(self):
        """CP-13 | Agregar una habilidad con valor negativo o con texto | Rechaza con 'Revisa los datos'"""
        c = self.usuario("Ana", "ana@a.com")
        self.assertIn("Revisa los datos", texto(self.agregar(c, "ofrezco", "Diseño", "Logo", -5)))
        self.assertIn("Revisa los datos", texto(self.agregar(c, "ofrezco", "Diseño", "Logo", "abc")))
        self.assertEqual(len(self.consulta("SELECT * FROM habilidades")), 0)

    def test_categoria_invalida(self):
        """CP-14 | Enviar una categoría que no existe en la lista | Rechaza con 'Revisa los datos'"""
        c = self.usuario("Ana", "ana@a.com")
        self.assertIn("Revisa los datos", texto(self.agregar(c, "ofrezco", "Inventada", "Algo", 1)))

    def test_eliminar_propia(self):
        """CP-15 | Eliminar una habilidad propia | Se elimina de la base de datos"""
        c = self.usuario("Ana", "ana@a.com")
        self.agregar(c, "ofrezco", "Diseño", "Logo", 10)
        c.post(f"/habilidad/{self.id_habilidad('Logo')}/eliminar")
        self.assertEqual(len(self.consulta("SELECT * FROM habilidades")), 0)

    def test_eliminar_ajena(self):
        """CP-16 | Intentar eliminar la habilidad de otro usuario | No se elimina"""
        ana = self.usuario("Ana", "ana@a.com")
        beto = self.usuario("Beto", "beto@a.com")
        self.agregar(ana, "ofrezco", "Diseño", "Logo", 10)
        beto.post(f"/habilidad/{self.id_habilidad('Logo')}/eliminar")
        self.assertEqual(len(self.consulta("SELECT * FROM habilidades")), 1)


class PruebasMatching(BaseTest):
    def test_palabras_clave(self):
        """CP-17 | Extraer palabras clave de un texto con tildes y palabras vacías | Ignora tildes y palabras como 'clases'"""
        self.assertEqual(skillmatch.palabras_clave("Clases de Programación Avanzada"), {"programacion", "avanzada"})

    def test_coincidencia_por_categoria(self):
        """CP-18 | Un usuario busca una categoría que otro ofrece | El otro aparece en Coincidencias"""
        ana = self.usuario("Ana", "ana@a.com")
        beto = self.usuario("Beto", "beto@a.com")
        self.agregar(ana, "busco", "Diseño", "Logo")
        self.agregar(beto, "ofrezco", "Diseño", "Afiches", 20000)
        self.assertIn("Beto", texto(ana.get("/matches")))

    def test_match_mutuo(self):
        """CP-19 | Ambos ofrecen lo que el otro busca | Se marca como 'Match mutuo'"""
        ana = self.usuario("Ana", "ana@a.com")
        beto = self.usuario("Beto", "beto@a.com")
        self.agregar(ana, "ofrezco", "Programación", "Python", 50000)
        self.agregar(ana, "busco", "Diseño", "Logo")
        self.agregar(beto, "ofrezco", "Diseño", "Logo y branding", 40000)
        self.agregar(beto, "busco", "Programación", "Aprender Python")
        self.assertIn("Match mutuo", texto(ana.get("/matches")))

    def test_sin_coincidencias(self):
        """CP-20 | Las categorías ofrecidas y buscadas no coinciden | No aparece ninguna coincidencia"""
        ana = self.usuario("Ana", "ana@a.com")
        beto = self.usuario("Beto", "beto@a.com")
        self.agregar(ana, "busco", "Música", "Guitarra")
        self.agregar(beto, "ofrezco", "Diseño", "Afiches", 20000)
        self.assertIn("nadie ofrece", texto(ana.get("/matches")))

    def test_no_se_empareja_con_uno_mismo(self):
        """CP-21 | Un usuario ofrece y busca la misma categoría | No aparece como coincidencia consigo mismo"""
        ana = self.usuario("Ana", "ana@a.com")
        self.agregar(ana, "ofrezco", "Diseño", "Afiches", 20000)
        self.agregar(ana, "busco", "Diseño", "Logo")
        self.assertIn("nadie ofrece", texto(ana.get("/matches")))


class PruebasAcuerdos(BaseTest):
    def preparar(self):
        ana = self.usuario("Ana", "ana@a.com")
        beto = self.usuario("Beto", "beto@a.com")
        self.agregar(ana, "ofrezco", "Programación", "Clases de Python", 50000)
        self.agregar(beto, "ofrezco", "Diseño", "Logo y branding", 40000)
        return ana, beto, self.id_habilidad("Clases de Python"), self.id_habilidad("Logo y branding")

    def test_calculo_diferencia(self):
        """CP-22 | Calcular la diferencia de valor entre dos habilidades | Devuelve positivo, negativo o cero según corresponda"""
        self.assertEqual(skillmatch.calcular_diferencia(50000, 40000)[0], 10000)
        self.assertEqual(skillmatch.calcular_diferencia(30000, 45000)[0], -15000)
        self.assertEqual(skillmatch.calcular_diferencia(20000, 20000)[0], 0)
        self.assertIn("equilibrado", skillmatch.calcular_diferencia(20000, 20000)[1])

    def test_vista_previa_del_acuerdo(self):
        """CP-23 | Calcular un acuerdo antes de enviarlo | Muestra a quién compensa y con cuánto"""
        ana, beto, py, logo = self.preparar()
        self.assertIn("te compensa con $10000", texto(ana.get(f"/acuerdo/{logo}?mi={py}")))

    def test_proponer_acuerdo(self):
        """CP-24 | Enviar una propuesta de acuerdo | Se guarda con estado 'propuesto'"""
        ana, beto, py, logo = self.preparar()
        ana.post(f"/acuerdo/{logo}", data={"mi": str(py)})
        filas = self.consulta("SELECT * FROM acuerdos")
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]["estado"], "propuesto")

    def test_no_con_habilidad_propia(self):
        """CP-25 | Proponer un acuerdo sobre la habilidad que uno mismo ofrece | Rechaza y no crea el acuerdo"""
        ana, beto, py, logo = self.preparar()
        r = ana.get(f"/acuerdo/{py}", follow_redirects=True)
        self.assertIn("no está disponible", texto(r))

    def test_propuesta_duplicada(self):
        """CP-26 | Enviar dos veces la misma propuesta pendiente | La segunda se rechaza"""
        ana, beto, py, logo = self.preparar()
        ana.post(f"/acuerdo/{logo}", data={"mi": str(py)})
        r = ana.post(f"/acuerdo/{logo}", data={"mi": str(py)}, follow_redirects=True)
        self.assertIn("Ya enviaste una propuesta", texto(r))
        self.assertEqual(len(self.consulta("SELECT * FROM acuerdos")), 1)

    def test_receptor_acepta(self):
        """CP-27 | El receptor acepta la propuesta | El estado cambia a 'aceptado'"""
        ana, beto, py, logo = self.preparar()
        ana.post(f"/acuerdo/{logo}", data={"mi": str(py)})
        r = beto.post("/acuerdo/1/responder", data={"accion": "aceptado"}, follow_redirects=True)
        self.assertIn("Propuesta aceptada", texto(r))
        self.assertEqual(self.consulta("SELECT estado FROM acuerdos")[0]["estado"], "aceptado")

    def test_proponente_no_responde(self):
        """CP-28 | Quien envió la propuesta intenta aceptarla | No se permite y el estado sigue 'propuesto'"""
        ana, beto, py, logo = self.preparar()
        ana.post(f"/acuerdo/{logo}", data={"mi": str(py)})
        ana.post("/acuerdo/1/responder", data={"accion": "aceptado"})
        self.assertEqual(self.consulta("SELECT estado FROM acuerdos")[0]["estado"], "propuesto")

    def test_no_responder_dos_veces(self):
        """CP-29 | Responder una propuesta que ya fue aceptada | No se permite cambiar la decisión"""
        ana, beto, py, logo = self.preparar()
        ana.post(f"/acuerdo/{logo}", data={"mi": str(py)})
        beto.post("/acuerdo/1/responder", data={"accion": "aceptado"})
        beto.post("/acuerdo/1/responder", data={"accion": "rechazado"})
        self.assertEqual(self.consulta("SELECT estado FROM acuerdos")[0]["estado"], "aceptado")

    def test_acuerdos_privados(self):
        """CP-30 | Un tercero revisa 'Mis acuerdos' | No ve acuerdos en los que no participa"""
        ana, beto, py, logo = self.preparar()
        ana.post(f"/acuerdo/{logo}", data={"mi": str(py)})
        caro = self.usuario("Caro", "caro@a.com")
        self.assertIn("Aún no tienes acuerdos", texto(caro.get("/acuerdos")))
        caro.post("/acuerdo/1/responder", data={"accion": "aceptado"})
        self.assertEqual(self.consulta("SELECT estado FROM acuerdos")[0]["estado"], "propuesto")


class PruebasSeguridad(BaseTest):
    def test_xss_escapado(self):
        """CP-31 | Guardar una habilidad con código <script> en el nombre | Se muestra como texto, no se ejecuta"""
        c = self.usuario("Ana", "ana@a.com")
        self.agregar(c, "ofrezco", "Otro", "<script>alert(1)</script>", 1)
        pagina = texto(c.get("/perfil"))
        self.assertNotIn("<script>alert(1)</script>", pagina)
        self.assertIn("&lt;script&gt;", pagina)

    def test_sql_injection(self):
        """CP-32 | Iniciar sesión con una inyección SQL en el correo | No permite entrar"""
        c = self.cliente()
        self.registrar(c, "Ana", "ana@a.com")
        r = self.entrar(c, "' OR '1'='1", "cualquiera")
        self.assertIn("incorrectos", texto(r))


class PruebasCalificaciones(BaseTest):
    def aceptado(self, a, b, hab_a, val_a, hab_b, val_b, cat_a="Programación", cat_b="Diseño"):
        """Crea un acuerdo aceptado: 'a' propone y 'b' acepta. Devuelve el id del acuerdo."""
        self.agregar(a, "ofrezco", cat_a, hab_a, val_a)
        self.agregar(b, "ofrezco", cat_b, hab_b, val_b)
        a.post(f"/acuerdo/{self.id_habilidad(hab_b)}", data={"mi": str(self.id_habilidad(hab_a))})
        acuerdo_id = self.consulta("SELECT MAX(id) AS m FROM acuerdos")[0]["m"]
        b.post(f"/acuerdo/{acuerdo_id}/responder", data={"accion": "aceptado"})
        return acuerdo_id

    def calificar(self, c, acuerdo_id, puntuacion, comentario=""):
        return c.post(f"/calificar/{acuerdo_id}",
                      data={"puntuacion": str(puntuacion), "comentario": comentario},
                      follow_redirects=True)

    def test_calificar_acuerdo_aceptado(self):
        """CP-35 | Calificar al otro usuario después de un acuerdo aceptado | La calificación se guarda"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        r = self.calificar(ana, ac, 5, "Excelente trabajo")
        self.assertIn("Gracias por tu calificación", texto(r))
        fila = self.consulta("SELECT * FROM calificaciones")[0]
        self.assertEqual((fila["puntuacion"], fila["comentario"]), (5, "Excelente trabajo"))

    def test_no_calificar_propuesta_pendiente(self):
        """CP-36 | Calificar un acuerdo que todavía no fue aceptado | No se permite"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        self.agregar(ana, "ofrezco", "Programación", "Clases de Python", 50000)
        self.agregar(beto, "ofrezco", "Diseño", "Logo y branding", 40000)
        ana.post(f"/acuerdo/{self.id_habilidad('Logo y branding')}", data={"mi": str(self.id_habilidad('Clases de Python'))})
        r = self.calificar(ana, 1, 5)
        self.assertIn("no está disponible", texto(r))
        self.assertEqual(len(self.consulta("SELECT * FROM calificaciones")), 0)

    def test_no_calificar_dos_veces(self):
        """CP-37 | Calificar dos veces el mismo intercambio | La segunda calificación se rechaza"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        self.calificar(ana, ac, 5)
        r = self.calificar(ana, ac, 1)
        self.assertIn("Ya calificaste", texto(r))
        self.assertEqual(len(self.consulta("SELECT * FROM calificaciones")), 1)

    def test_ambos_pueden_calificarse(self):
        """CP-38 | Cada participante califica al otro en el mismo intercambio | Se guardan dos calificaciones, una por persona"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        self.calificar(ana, ac, 5)
        self.calificar(beto, ac, 4)
        self.assertEqual(len(self.consulta("SELECT * FROM calificaciones")), 2)

    def test_tercero_no_califica(self):
        """CP-39 | Un usuario ajeno al intercambio intenta calificarlo | No se permite"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        caro = self.usuario("Caro", "caro@a.com")
        self.assertIn("no está disponible", texto(self.calificar(caro, ac, 5)))
        self.assertEqual(len(self.consulta("SELECT * FROM calificaciones")), 0)

    def test_puntuacion_invalida(self):
        """CP-40 | Enviar una puntuación fuera de 1 a 5 o un texto | Se rechaza y no se guarda"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        for malo in ("0", "6", "-1", "abc", ""):
            self.assertIn("Revisa la puntuación", texto(self.calificar(ana, ac, malo)), malo)
        self.assertEqual(len(self.consulta("SELECT * FROM calificaciones")), 0)

    def test_comentario_largo(self):
        """CP-41 | Enviar un comentario de más de 300 caracteres | Se rechaza y no se guarda"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        self.assertIn("Revisa la puntuación", texto(self.calificar(ana, ac, 5, "x" * 301)))
        self.assertEqual(len(self.consulta("SELECT * FROM calificaciones")), 0)

    def test_promedio_de_reputacion(self):
        """CP-42 | Un usuario recibe dos calificaciones (5 y 4) | Su promedio es 4.5 y se ve en Coincidencias y en su perfil"""
        ana, beto, caro = (self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com"),
                           self.usuario("Caro", "caro@a.com"))
        ac1 = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        ac2 = self.aceptado(caro, beto, "Clases de Java", 30000, "Afiches", 20000)
        self.calificar(ana, ac1, 5)
        self.calificar(caro, ac2, 4)
        conn = sqlite3.connect(self.ruta); conn.row_factory = sqlite3.Row
        self.assertEqual(skillmatch.reputaciones(conn)[2], (4.5, 2))
        conn.close()
        self.assertIn("4.5 (2 calificaciones)", texto(beto.get("/perfil")))
        dani = self.usuario("Dani", "dani@a.com")
        self.agregar(dani, "busco", "Diseño", "Logo")
        self.assertIn("4.5 (2)", texto(dani.get("/matches")))

    def test_calificacion_recibida_visible(self):
        """CP-43 | El usuario calificado revisa su sección de calificaciones | Ve la puntuación y el comentario recibido"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        self.calificar(ana, ac, 5, "Muy puntual")
        pagina = texto(beto.get("/calificaciones"))
        self.assertIn("Muy puntual", pagina)
        self.assertIn("★★★★★", pagina)

    def test_comentario_escapado(self):
        """CP-44 | Enviar un comentario con código <script> | Se muestra como texto, no se ejecuta"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        self.calificar(ana, ac, 3, "<script>alert(1)</script>")
        pagina = texto(beto.get("/calificaciones"))
        self.assertNotIn("<script>alert(1)</script>", pagina)
        self.assertIn("&lt;script&gt;", pagina)

    def test_pendientes_por_calificar(self):
        """CP-45 | Un acuerdo aceptado sin calificar | Aparece en 'Intercambios por calificar' hasta que se califica"""
        ana, beto = self.usuario("Ana", "ana@a.com"), self.usuario("Beto", "beto@a.com")
        ac = self.aceptado(ana, beto, "Clases de Python", 50000, "Logo y branding", 40000)
        self.assertIn(f"/calificar/{ac}", texto(ana.get("/calificaciones")))
        self.calificar(ana, ac, 5)
        self.assertNotIn(f"/calificar/{ac}", texto(ana.get("/calificaciones")))


class PruebasCSRF(BaseTest):
    CSRF = True

    def test_post_sin_token(self):
        """CP-33 | Enviar un formulario POST sin el token de seguridad | Se rechaza con error 400"""
        r = self.cliente().post("/registro", data={"nombre": "Ana", "correo": "ana@a.com", "password": "123456"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(len(self.consulta("SELECT * FROM usuarios")), 0)

    def test_post_con_token(self):
        """CP-34 | Enviar un formulario POST con el token de seguridad válido | Se acepta y registra al usuario"""
        c = self.cliente()
        pagina = texto(c.get("/registro"))
        token = re.search(r'name="_csrf" value="([0-9a-f]+)"', pagina).group(1)
        r = c.post("/registro", data={"_csrf": token, "nombre": "Ana", "correo": "ana@a.com", "password": "123456"},
                   follow_redirects=True)
        self.assertIn("Registro exitoso", texto(r))


if __name__ == "__main__":
    unittest.main()
