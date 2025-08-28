# Menu Shuffler

Menu Shuffler is a small Gradio-based app that helps generate a daily meal plan and automatically compute portions to match a target calorie budget. It can:

- Generate a draft menu with the help of a local LLM (via Ollama) using the included recipes dataset.
- Adjust meal portions for breakfast, snacks, lunch, and dinner to meet a total calorie goal.
- Display results in a simple web UI with per-meal tables and total calories.

The UI labels are in Ukrainian; the app works regardless of the interface language you use in your browser.

## Demo (What it does)

1. Click "Згенерувати меню" to ask the local LLM to propose dishes for each meal using the recipes.json database.
2. Set your total calories and the relative weights of each meal (e.g., breakfast 25%, lunch 40%, etc.).
3. Click "Порахувати порції" to automatically scale the portions so that the total matches your calorie target.

Under the hood:
- The LLM step (optional) retrieves relevant recipes and asks the local model to output a JSON menu referencing recipe IDs. The output is sanitized to include only valid recipes.
- The optimization step uses a simple numeric procedure to scale dish portions to match the target calories per meal, based on the meal weights you provide.

## Project structure

- menu_shuffler.py — Gradio UI and app entry point.
- algorithm.py — Calorie/portion allocation logic.
- llm.py — Light-weight retrieval + Ollama chat call and JSON sanitization.
- recipes.json — Example recipes database with nutrition info.
- requirements.txt — Python dependencies.

## Requirements

- Python 3.12+ recommended
- pip
- Optional: Ollama installed locally if you want LLM menu generation
  - Model name used by default: `hetg/llama3-nutrition`

If you do not install or run Ollama, the app still works using a built-in default menu; you can skip the "Згенерувати меню" step and go straight to portion calculation.

## Installation

It is recommended to use a virtual environment.

- Linux/macOS
  - python3 -m venv .venv
  - source .venv/bin/activate
- Windows (PowerShell)
  - python -m venv .venv
  - .venv\\Scripts\\Activate.ps1

Then install dependencies:

- pip install -r requirements.txt

Optional (for LLM features):

- Install Ollama: https://ollama.com/download
- Pull or create the local model referenced by `llm.py` (default `hetg/llama3-nutrition`). If you have a custom model name, edit `MODEL` in llm.py.

## Running the app

From the project root:

- python menu_shuffler.py

Gradio will print a local URL in the console (e.g., http://127.0.0.1:7860). Open it in your browser.

## Usage tips

- Total calories: set the overall daily target (e.g., 1800).
- Meal weights: enter relative weights (fractions, not percentages). For example, 0.25 means 25% of your daily calories for that meal. The app normalizes weights, so absolute values aren’t critical as long as they are non‑negative.
- LLM is optional: if unavailable or returns invalid JSON, the app falls back to a safe default menu or ignores bad entries.

## Data model

recipes.json entries look like this:

[
  {"id": 1, "name": "Omelette", "calories": 250, "protein": 18, "fat": 20, "carbs": 2, "ingredients": ["eggs", "milk", "butter"]}
]

The LLM is expected to return a JSON object like:

{
  "breakfast": [{"id": 1}],
  "first_snack": [{"id": 4}],
  "lunch": [{"id": 2}],
  "second_snack": [{"id": 4}],
  "dinner": [{"id": 3}]
}

llm.py sanitizes this to ensure only known recipe IDs are used.

## Troubleshooting

- Ollama not running / missing model:
  - Start Ollama (ollama serve) and ensure the model name in llm.py exists (e.g., `ollama run hetg/llama3-nutrition`).
  - If you prefer no-LLM usage, just skip the "Згенерувати меню" button and use the portion calculator.
- Port already in use: Gradio picks the next available port or you can pass parameters to `MenuUI().launch(server_port=xxxx)`.
- Missing packages: Re-run `pip install -r requirements.txt` in the active virtual environment.

## Development

- Code style: the repo includes ruff in requirements. You can run ruff if installed globally or via the venv.
- Minimal algorithm details: see Algorithm.generate_menu_with_weights() for the normalization and scaling steps.
