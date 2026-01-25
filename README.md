<!-- Readme v0.01 -->
<div align="center">
  <a href="#">
    <img src="apikit-logo.png" alt="Logo" width="450" height=200">
  </a>
  <p align="center">
      APIKit no es una librería ni un framework adicional, es una plantilla de arquitectura limpia y escalable para proyectos FastAPI, inspirada en principios de diseño como separación de responsabilidades, modularidad y mantenibilidad.
    <br />
  </p>

  [![Python](https://img.shields.io/badge/Python-v3.11.9-yellow?logo=python)](https://www.python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-v0.115.14-green?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Pydantic](https://img.shields.io/badge/Pydantic-v2.11.7-orange?logo=pydantic)](https://docs.pydantic.dev/)
  [![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-v2.0.41-red?logo=sqlalchemy)](https://www.sqlalchemy.org/)
  [![PyTest](https://img.shields.io/badge/Pytest-v8.4.1-red?logo=pytest)](https://docs.pytest.org/en/stable/)

</div>

  ## 📁 Estructura del Proyecto

  ```
  alembic                   # Migraciones
  api/
  ├── config/               # Configuraciones globales
  ├── utils/                # Funciones auxiliares generales
  ├── v1/                   # Versionamiento de la API
  │   ├── assets/           # Recursos estáticos (opcional)
  │   ├── auth/             # Autenticación y permisos
  │   ├── config/           # Configuraciones específicas de v1
  │   ├── dependencies/     # Inyección de dependencias para FastAPI
  │   ├── handlers/         # Lógica que maneja las peticiones
  │   ├── middleware/       # Middleware personalizados
  │   ├── models/           # Modelos ORM
  │   ├── routes/           # Definición de rutas y endpoints
  │   ├── schemas/          # Validaciones con Pydantic
  │   ├── services/         # Lógica de negocio
  │   ├── utils/            # Utilidades internas de v1
  │   └── constants.py      # Constantes

  tests/                 # Pruebas automatizadas
  ├── v1/                # Pruebas para la API v1
  │   ├── conftest.py
  │   └── test_tickets.py

  .env-example              # Ejemplo de variables de entorno
  .gitignore
  alembic.ini               # Configuracion de alembic
  apikit-logo.png           # Logo (opcional)
  apikit.png                # Imagen ilustrativa (opcional)
  docker-compose.yml        # Docker Compose setup
  dockerfile                # Dockerfile para la API
  main.py                   # Punto de entrada
  pytest.ini                # Configuración de Pytest
  README.md                 # Documentación principal
  requirements.txt          # Dependencias de Python
  test.db                   # Base de datos para testing
  traefik-config.yml        # Configuración de Traefik
  ```

  ---

  ## 🚀 Inicio Rápido

  1. **Clonar el repositorio:**

  ```bash
  git clone git@srv-git.mides.gob.gt:basemides/apikit.git
  cd apikit
  ```

  2. **Crear entorno virtual e instalar dependencias:**

```bash
python -m venv .venv
```

```bash
# Linux/macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

```bash
pip install -r requirements.txt
```

  3. **Configurar entorno:**

  - Copiar `.env-example` como `.env`
  - Modificar los valores según sea necesario

  4. **Ejecutar el servidor:**

  ```bash
  uvicorn main:app --reload
  ```

  5. **Acceder a la documentación interactiva:**

  - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

  ---

  ## 💪 Infraestructura


  - [Docker & Docker Compose](https://www.docker.com/) - Contenedores
  - [Traefik - v3.3](https://doc.traefik.io/traefik/v3.3/) - Proxy reverso

  ---

  ## Dependencias del Proyecto

  ### 🔧 Dependencias Principales

  | Dependencia | Versión | Descripción |
  |-------------|---------|-------------|
  | **FastAPI** | `0.115.14` | Framework web moderno y rápido para APIs REST |
  | **Pydantic** | `2.11.7` | Validación de datos y serialización con Python type hints |
  | **SQLAlchemy** | `2.0.41` | ORM (Object-Relational Mapping) para bases de datos |
  | **Alembic** | `1.16.5` | Herramienta para migraciones de base de datos |
  | **Uvicorn** | `0.35.0` | Servidor ASGI para FastAPI |

  ### 🗄️ Bases de Datos

  | Dependencia | Versión | Descripción |
  |-------------|---------|-------------|
  | **psycopg2** | `2.9.10` | Adaptador PostgreSQL para Python |
  | **asyncpg** | `0.30.0` | Cliente PostgreSQL asíncrono |
  | **aiosqlite** | `0.21.0` | Adaptador SQLite asíncrono |
  | **pyodbc** | `5.1.0` | Adaptador ODBC para SQL Server |

  ### 🧪 Testing y Desarrollo

  | Dependencia | Versión | Descripción |
  |-------------|---------|-------------|
  | **pytest** | `8.4.1` | Framework para pruebas automatizadas |
  | **black** | `25.1.0` | Formateador de código Python |
  | **httpx** | `0.28.1` | Cliente HTTP para testing de APIs |

  ### 🔐 Seguridad y Autenticación

  | Dependencia | Versión | Descripción |
  |-------------|---------|-------------|
  | **python-jose** | `3.5.0` | Implementación de JWT (JSON Web Tokens) |
  | **cryptography** | `45.0.6` | Librería de criptografía |
  | **python-multipart** | `0.0.20` | Soporte para formularios multipart |

  ### ⚙️ Utilidades y Configuración

  | Dependencia | Versión | Descripción |
  |-------------|---------|-------------|
  | **python-decouple** | `3.8` | Separación de configuración del código |
  | **fastapi-pagination** | `0.14.0` | Paginación para FastAPI |
  | **email-validator** | `2.2.0` | Validación de direcciones de email |
  | **rich** | `14.0.0` | Formateo de texto en terminal |

  ### 🔄 Actualización de Dependencias

  Para actualizar las dependencias a sus versiones más recientes:

  ```bash
  pip install --upgrade -r requirements.txt
  ```

  **Nota**: Siempre verifica la compatibilidad entre versiones antes de actualizar en producción.

  ---

  ## 🔮 Pruebas Automatizadas

  Ejecuta las pruebas con:

  ```bash
  pytest
  ```

  ---

  ## 🛠️ Si vas a usar Docker

  Levanta el entorno con:

  ```bash
  docker-compose up --build
  ```

  Variables importantes se definen en el archivo `.env`. Puedes usar `.env-example` como referencia.

  ---

  ## 💡 Notas

  - El proyecto está versionado bajo `v1/` y preparado para escalar a `v2/`, `v3/`, etc.

  ---

  ## ✨ Contribuciones

  - Consulta el reglamento interno para hacer tus Pull Requests (Merge Request).

