# Menu Shuffler (Django)

Menu Shuffler is now a Django web application that helps generate a daily meal plan and automatically compute portions to match a target calorie budget. It can:

- Generate a draft menu with the help of a local LLM (via Ollama) using the included recipes dataset.
- Adjust meal portions for breakfast, snacks, lunch, and dinner to meet a total calorie goal.
- Display results in a simple web UI (Ukrainian labels).

The app is structured as a standard Django project with an app `apps/menu` that contains the UI, views, and services.

## Demo (What it does)

1. Click "Згенерувати меню" to ask the local LLM to propose dishes for each meal using the bundled `recipes.json` database.
2. Set your total calories and the relative weights of each meal (e.g., breakfast 25%, lunch 40%, etc.).
3. Click "Порахувати порції" to automatically scale the portions so that the total matches your calorie target.

Under the hood:
- The LLM step (optional) retrieves relevant recipes and asks the local model to output a JSON menu referencing recipe IDs. The output is sanitized to include only valid recipes.
- The optimization step uses a simple numeric procedure to scale dish portions to match the target calories per meal, based on the meal weights you provide.

## Project structure

- manage.py — Django management entry point
- menu_shuffler/ — Django project (settings, URLs, WSGI)
- apps/menu/ — Main app (templates, views, services)
  - templates/index.html — Single-page UI (Ukrainian)
  - services/llm.py — Retrieval + Ollama chat + JSON sanitization
  - services/calculator.py — Portion/Calorie allocation logic
  - services/recipes.json — Example recipes database
- ops/docker/* — Dockerfiles and scripts for web and Ollama
- ops/llm/llama3-nutrition/Modelfile — Example Ollama Modelfile
- docker-compose.yml — Orchestration for web, db, nginx, ollama
- staticfiles/ — Collected static (volume when running in Docker)
- requirements.txt — Python dependencies

## Requirements

- Python 3.11+ (Docker image uses 3.11-slim)
- pip
- MySQL server (only for Docker-compose setup). For local development you can use SQLite by configuring settings.
- Optional: Ollama installed locally or use the provided Docker service
  - Default model: `hetg/llama3-nutrition`

## Running with Docker Compose (recommended)

This repository includes a Compose setup for web (Gunicorn), MySQL, Nginx, and Ollama.

1) Prepare environment

Create a `.env` file in the project root. You can start from the provided template:

```bash
cp .env.example .env
```

Then adjust values as needed. Example configuration for Docker Compose:

```
DEBUG=False
SECRET_KEY=please-change
ALLOWED_HOSTS=*
DATABASE_URL=mysql://menu_user:menu_pass@db:3306/menu_db
# Ollama service URL inside the compose network
OLLAMA_HOST=http://ollama:11434
```

2) Build and start services

```bash
docker compose up --build
```

Services:
- web: Gunicorn serving Django on port 8000 (exposed to nginx only)
- db: MySQL 8.0 on port 3306 (exposed to host for convenience)
- nginx: public entrypoint on http://localhost/ (port 80)
- ollama: Ollama server on port 11434 (exposed to host)

Static files are collected into a shared `static_volume` mounted at `/app/staticfiles` (served by nginx config under `ops/nginx/conf.d`).

## Quickstart (Local, without Docker)

1) Create and activate a virtual environment

- Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Environment variables

This project uses `django-environ`. Create a `.env` file in the project root (same level as `manage.py`). You can copy the example and adjust:

```bash
cp .env.example .env
```

Example minimal configuration for local development:

```
DEBUG=True
SECRET_KEY=dev-secret-key-change-me
ALLOWED_HOSTS=127.0.0.1,localhost
# Database (comment out to use Django default SQLite if project settings allow)
# DATABASE_URL=mysql://user:password@127.0.0.1:3306/menu_shuffler
# Ollama URL (if running locally)
OLLAMA_HOST=http://127.0.0.1:11434
```

Note: If settings are strictly configured for MySQL, you will need a running MySQL and a proper DATABASE_URL. If SQLite is supported, you can omit DATABASE_URL.

4) Apply migrations

```bash
python manage.py migrate
```

5) (Optional) Collect static files

```bash
python manage.py collectstatic --noinput
```

6) Run the development server

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/ in your browser.

### Optional: Enable LLM locally (without Docker)

Install Ollama and run the model:

```bash
# Install: https://ollama.com/download
ollama serve
ollama pull hetg/llama3-nutrition
```

The app will call the Ollama HTTP API (default http://127.0.0.1:11434). If Ollama is not available, the app falls back to a built-in default menu for calculations.

## Usage

Open the site (either http://127.0.0.1:8000/ for local dev or http://localhost/ via nginx in Docker). The main page offers:
- "Згенерувати меню" — generates a draft menu using the LLM (if available).
- Inputs for total calories and meal weights.
- "Порахувати порції" — computes portions per meal to meet your target.
- A clear button to reset the session data.

Notes:
- Meal weights are fractions (e.g., 0.25 means 25%). They are normalized automatically.
- If LLM is unavailable, you can still use the portion calculator with the default menu.

## Data model

`apps/menu/services/recipes.json` entries look like this:

```json
[
  { "id": 1, "name": "Omelette", "calories": 250, "protein": 18, "fat": 20, "carbs": 2, "ingredients": ["eggs", "milk", "butter"] }
]
```

The LLM is expected to return JSON like:

```json
{
  "breakfast": [{"id": 1}],
  "first_snack": [{"id": 4}],
  "lunch": [{"id": 2}],
  "second_snack": [{"id": 4}],
  "dinner": [{"id": 3}]
}
```

`LLMClient.sanitize_menu()` ensures only known recipe IDs are used and expands them to full recipe entries.

## Key modules

- `apps/menu/views.py` — handles POST actions: `llm` (generate via Ollama), `calc` (portion calculation), `clear` (reset session).
- `apps/menu/services/llm.py` — deterministic retrieval over recipes + Ollama chat + JSON extraction, sanitization.
- `apps/menu/services/calculator.py` — weight normalization and per-meal optimization; returns total calories.
- `apps/menu/templates/index.html` — UI and JS for tabs and AJAX calls.

## Troubleshooting

- Ollama not running / missing model
  - Local: start Ollama and pull the model
    ```bash
    ollama serve
    ollama pull hetg/llama3-nutrition
    ```
  - Docker: the `ollama` service starts automatically and pulls the model on startup (see `ops/docker/ollama/start-ollama.sh`).
- Nginx 502 / web not reachable
  - Ensure `web` is healthy and Django started; check logs with `docker compose logs -f web nginx`.
- Database issues
  - Verify `DATABASE_URL` in `.env`. For a clean start, remove the `db_data` volume: `docker compose down -v` (this deletes DB data!).
- Static files missing
  - Run `python manage.py collectstatic` (in Docker you can `docker compose exec web python manage.py collectstatic --noinput`). Ensure nginx mounts `static_volume`.
- Missing packages / build issues
  - Re-run `pip install -r requirements.txt` locally, or rebuild: `docker compose build --no-cache web`.

## Development tips

- Run server locally with auto-reload:
  ```bash
  python manage.py runserver
  ```
- Run migrations:
  ```bash
  python manage.py makemigrations
  python manage.py migrate
  ```
- Lint (ruff is in requirements):
  ```bash
  ruff check .
  ```