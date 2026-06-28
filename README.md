# ERP Logístico (SaaS)

Monolito modular en Django. Documentación de negocio y técnica en [`docs/`](docs).

## Quickstart local

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements/local.txt

cp .env.example .env            # primera vez; SQLite por defecto, sin Postgres

python manage.py migrate
python manage.py runserver
```

## Tests y lint

```bash
ruff check .
pytest
```

Ver [`docs/tech/05 - CI y Flujo de Trabajo.md`](docs/tech/05%20-%20CI%20y%20Flujo%20de%20Trabajo.md) para el detalle de variables de entorno, CI y el flujo de ramas/PR.
