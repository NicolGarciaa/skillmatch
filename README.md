# SkillMatch

**Conectando talentos, impulsando proyectos.**

SkillMatch es una plataforma web de intercambio de habilidades y servicios profesionales. Cada persona publica lo que ofrece y lo que busca, el sistema encuentra coincidencias y calcula un acuerdo económico justo cuando las habilidades intercambiadas no tienen el mismo valor.

Proyecto Integrador de Área (PIA) — Fundación Universitaria INPAHU (UNINPAHU), Facultad de Ingeniería, sexto semestre. Desarrollado de forma individual dentro del semillero Club de Programación.

## Estado del proyecto

MVP funcional (en desarrollo). 

### Funcionalidades implementadas

- **Registro e inicio de sesión** de usuarios, con contraseñas almacenadas de forma segura (hash).
- **Perfil con habilidades:** cada usuario registra las habilidades que ofrece y las que busca, con categoría y valor aproximado en pesos.
- **Coincidencias (matching):** muestra quién ofrece algo de la misma categoría que lo que el usuario busca. Calcula una afinidad según las palabras en común y marca los **matches mutuos** (cuando ambos ofrecen lo que el otro busca).
- **Acuerdos económicos:** el usuario elige qué ofrece a cambio, el sistema calcula la diferencia de valor y se envía una propuesta. Quien la recibe puede aceptarla o rechazarla.
- **Certificación y calificaciones:** pantallas de diseño (prototipo visual) para las siguientes fases.

### Fuera del alcance de esta fase

- Pagos con dinero real.
- Validaciones legales o notariales externas.
- Certificación y calificaciones con lógica funcional (solo existen como diseño de pantalla).
- Modelo de Machine Learning para el matching (por ahora se usan reglas simples por categoría y palabras clave).

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

## Estructura del proyecto

```
skillmatch/
├── app.py            # Aplicación Flask: rutas, base de datos y lógica
├── requirements.txt  # Dependencias de Python
└── templates/        # Páginas HTML
    ├── base.html
    ├── inicio.html
    ├── registro.html
    ├── login.html
    ├── perfil.html
    ├── matches.html
    ├── acuerdo.html
    ├── acuerdos.html
    ├── certificacion.html
    └── calificaciones.html
```

## Autora

Nicol — [@NicolGarciaa](https://github.com/NicolGarciaa)
