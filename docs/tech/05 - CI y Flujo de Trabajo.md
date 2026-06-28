# 05 - CI y Flujo de Trabajo

## 1. Variables de entorno
La configuración sensible no vive en `config/settings.py`, se lee del entorno vía `django-environ`.

* `.env.example` → plantilla versionada en git, sin secretos reales.
* `.env` → copia local de `.env.example`, **ignorada por git** (`.gitignore`). Cada desarrollador la crea una sola vez:
  ```
  cp .env.example .env
  ```
* Variables soportadas hoy:
  * `SECRET_KEY` — clave de Django. Tiene un valor por defecto inseguro solo para que el proyecto arranque sin `.env`; en cualquier entorno real debe sobreescribirse.
  * `DEBUG` — `True`/`False`.
  * `ALLOWED_HOSTS` — lista separada por comas.
  * `DATABASE_URL` — opcional. Si no está definida, Django usa SQLite local (`db.sqlite3`). Cuando se conecte Neon, se setea aquí con el formato `postgres://usuario:password@host:5432/db` y no se toca código.

## 1.1. Zona horaria
`USE_TZ = True` hace que Django guarde toda fecha/hora en UTC en la base de datos, sin importar la hora de pared del servidor Postgres (Neon), del contenedor Docker, o de la máquina local — eso es lo que nos hace resilientes a que esos tres relojes no coincidan. `TIME_ZONE = 'America/Lima'` solo controla cómo se *muestra* la hora (admin, templates); el dato persistido siempre es UTC.

## 1.2. Neon (Postgres)
Proyecto creado en la región **US East** (Neon no tiene región en Sudamérica; es la de menor latencia disponible desde Perú). Al desplegar en Google Cloud, la región de Cloud Run debe quedar lo más cerca posible de esa misma región de Neon, para minimizar la latencia app↔DB.

## 2. Base de datos en cada entorno
* **Local (ahora):** SQLite, cero configuración. No se necesita Docker ni Postgres para empezar a programar.
* **Staging/Producción (futuro):** Postgres serverless (Neon o Supabase), seteado solo vía `DATABASE_URL`. El despliegue final corre en Google Cloud.
* Cuando el proyecto madure y se quiera paridad local-prod, se puede levantar Postgres con `docker-compose.yml` (hoy vacío, pendiente) y apuntar `DATABASE_URL` a `localhost`. No es necesario para el desarrollo inicial.

## 3. Cómo correr pruebas y lint en local
Con el entorno virtual activado:
```
pip install -r requirements/local.txt
python manage.py check
ruff check .
pytest
```
* `pytest` usa la configuración de `pyproject.toml` (`DJANGO_SETTINGS_MODULE=config.settings`), por lo que no requiere flags adicionales.
* `ruff` es el linter/formateador; corre exactamente las mismas reglas que el CI.

## 4. CI (GitHub Actions)
Definido en `.github/workflows/ci.yml`. Se dispara en:
* Cada `push` a `main`.
* Cada Pull Request contra `main`.

Pasos del job `test`:
1. Checkout del código.
2. Setup de Python 3.13.
3. Instala `requirements/local.txt` (incluye dependencias de producción + testing + lint).
4. `ruff check .` — falla el build si hay errores de lint.
5. `python manage.py makemigrations --check --dry-run` — falla si hay cambios de modelos sin migración generada.
6. `pytest` — corre la suite de tests contra SQLite (mismo motor que en local, por ahora). Mientras no exista ninguna app de negocio, `pytest` devuelve exit code 5 ("no tests collected"); el step lo trata como éxito en vez de fallo, porque no es un error real. En cuanto exista al menos un test, cualquier código de salida distinto de 0 o 5 sí rompe el build.

El CI **no usa Postgres todavía**: se mantiene simple mientras el proyecto recién empieza. Cuando se introduzca Postgres real en algún entorno, se debe:
1. Agregar el servicio `postgres` al job (imagen, env, healthcheck).
2. Setear `DATABASE_URL` en el job apuntando a ese servicio.
3. Agregar el driver (`psycopg`) a `requirements/base.txt`.

## 5. Flujo de trabajo con rama protegida
`main` está protegida en GitHub: no admite push directo, exige Pull Request y que el check `test` del CI esté en verde antes de mergear (ver Settings → Branches en el repo).

Flujo recomendado para cada feature:
```
git checkout -b feature/nombre-corto
# ... cambios ...
git push -u origin feature/nombre-corto
gh pr create --fill
```
El PR no se puede mergear hasta que el workflow de CI pase. Esto evita que código roto o sin lint llegue a `main`, incluso trabajando solo.

## 6. Convenciones relacionadas
Ver también [[04 - Convenciones de Desarrollo]] para la estructura de apps por dominio, y [[02 - Infraestructura y Operación]] para el plan de infraestructura a futuro (Docker local, Neon/Supabase, Google Cloud).
