# SkillMatch

**Conectando talentos, impulsando proyectos.**

SkillMatch es una plataforma web de intercambio de habilidades y servicios profesionales. Cada persona publica lo que ofrece y lo que busca, el sistema encuentra coincidencias y calcula un acuerdo económico justo cuando las habilidades intercambiadas no tienen el mismo valor.

Proyecto Integrador de Área (PIA) — Fundación Universitaria INPAHU (UNINPAHU), Facultad de Ingeniería, sexto semestre. Desarrollado de forma individual dentro del semillero Club de Programación.

## Estado del proyecto

MVP funcional (en desarrollo). 

### Funcionalidades implementadas

- **Registro e inicio de sesión** de usuarios, con contraseñas almacenadas de forma segura (hash).
- **Perfil con habilidades:** cada usuario registra las habilidades que ofrece y las que busca, con categoría y valor aproximado en pesos.
- **Coincidencias (matching):** muestra quién ofrece algo de la misma categoría que lo que el usuario busca y calcula una **compatibilidad de 0 a 100 %** que suma categoría, similitud de texto (TF-IDF con coseno y términos relacionados), match mutuo, certificación, reputación y cercanía de valor. Se puede filtrar por categoría, match mutuo y habilidades certificadas.
- **Acuerdos económicos:** el usuario elige qué ofrece a cambio, el sistema calcula la diferencia de valor y se envía una propuesta. Quien la recibe puede aceptarla o rechazarla.
- **Calificaciones y comentarios:** tras un acuerdo aceptado, cada persona puede calificar a la otra (1 a 5 estrellas y un comentario, una vez por intercambio). El promedio se muestra en el perfil, en las coincidencias y al proponer un acuerdo.
- **Certificación de habilidades (versión simplificada):** el usuario solicita certificar una habilidad que ofrece, con una evidencia escrita; un usuario con rol *certificador* revisa la evidencia y la aprueba o la rechaza con una observación. Las habilidades aprobadas muestran la etiqueta **Certificada** en el perfil, las coincidencias y los acuerdos.

### Fuera del alcance de esta fase

- Pagos con dinero real.
- Validaciones legales o notariales externas.
- Verificación automática de documentos o títulos (la evidencia es texto que revisa un certificador).
- Modelo de Machine Learning entrenado para el matching (el actual usa similitud de texto TF-IDF y reglas ponderadas).

## Tecnologías

- Python 3 y Flask
- SQLite (base de datos incluida en Python)
- HTML con plantillas Jinja2
- Git y GitHub

## Cómo ejecutarlo (Windows)

1. Clona el repositorio y entra a la carpeta:

   ```
   git clone https://github.com/NicolGarciaa/skillmatch.git
   cd skillmatch
   ```

2. Crea y activa un entorno virtual:

   ```
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Instala las dependencias:

   ```
   pip install -r requirements.txt
   ```

4. Inicia la aplicación:

   ```
   python app.py
   ```

5. Abre en el navegador: http://127.0.0.1:5000

La base de datos (`instance/skillmatch.db`) se crea automáticamente la primera vez que se ejecuta la aplicación.

## Documentación

En la carpeta `docs/` están el **manual técnico** (arquitectura, modelo de datos, rutas, algoritmo de compatibilidad, seguridad e instalación), el **manual de usuario** (guía paso a paso con capturas) y el **informe de pruebas**.

## Pruebas

El proyecto incluye pruebas automáticas (74 casos, cobertura cercana al 95 %) que usan una base de datos temporal. Para ejecutarlas, con el entorno virtual activado:

```
python -m unittest tests.test_skillmatch -v
```

## Datos de demostración

Para cargar usuarios, habilidades e intercambios con calificaciones de ejemplo (contraseña de todos: `demo1234`):

```
python datos_demo.py
```

## Certificadores

Los usuarios nuevos se registran con el rol normal. Para convertir a un usuario ya registrado en certificador (acción administrativa, desde la consola):

```
python asignar_certificador.py correo@ejemplo.com
```

La persona debe cerrar sesión y volver a entrar. Los datos de demostración incluyen la cuenta `certificador@demo.com` (contraseña `demo1234`).

## Estructura del proyecto

```
skillmatch/
├── app.py            # Aplicación Flask: rutas, base de datos y lógica
├── datos_demo.py     # Datos de ejemplo para la demostración
├── asignar_certificador.py  # Convierte un usuario registrado en certificador
├── requirements.txt  # Dependencias de Python
├── static/           # Estilos (style.css)
├── tests/            # Pruebas automáticas
├── docs/             # Manuales e informe de pruebas
└── templates/        # Páginas HTML
    ├── base.html
    ├── inicio.html
    ├── registro.html
    ├── login.html
    ├── perfil.html
    ├── matches.html
    ├── acuerdo.html
    ├── acuerdos.html
    ├── calificar.html
    ├── certificacion.html
    └── calificaciones.html
```

## Autora

Nicol — [@NicolGarciaa](https://github.com/NicolGarciaa)
