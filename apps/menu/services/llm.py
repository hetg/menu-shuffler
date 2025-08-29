import json
import numpy as np
import re
import ollama
from pathlib import Path
from django.conf import settings
from typing import Any, Dict, List, Optional

MODEL = "hetg/llama3-nutrition"

class LLMClient:
    _recipes: List[Dict[str, Any]] = []
    _recipe_vectors: Optional[np.ndarray] = None
    _dim: int = 128
    _result: Dict[str, Any] = {"breakfast": [], "first_snack": [], "lunch": [], "second_snack": [], "dinner": []}
    _model: str = MODEL

    def __init__(self, model: str = MODEL, dim: int = 128):
        self._dim = dim
        self._model = model

    @staticmethod
    def _deterministic_vector_from_text(text: str, dim: int = 128) -> np.ndarray:
        seed = abs(hash(text)) % (2**32)
        rng = np.random.default_rng(seed)
        v = rng.normal(size=dim).astype("float32")
        norm = np.linalg.norm(v) + 1e-8
        return v / norm

    @classmethod
    def _build_recipe_matrix(cls) -> None:
        if not cls._recipes:
            return
        vecs: List[np.ndarray] = []
        for r in cls._recipes:
            basis_text = f"{r.get('id','')}::{r.get('name','')}"
            vecs.append(cls._deterministic_vector_from_text(basis_text, dim=cls._dim))
        cls._recipe_vectors = np.vstack(vecs) if vecs else None

    @classmethod
    def load_recipes(cls) -> List[Dict[str, Any]]:
        if cls._recipes:
            return cls._recipes
        with open(Path(settings.BASE_DIR) / "apps/menu/services/recipes.json", "r", encoding="utf-8") as f:
            cls._recipes = json.load(f)
        cls._build_recipe_matrix()
        return cls._recipes

    @classmethod
    def retrieve_recipes(cls, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        cls.load_recipes()
        if not cls._recipes:
            return []
        if cls._recipe_vectors is None:
            cls._build_recipe_matrix()
        if cls._recipe_vectors is None or cls._recipe_vectors.size == 0:
            return []
        q = cls._deterministic_vector_from_text(query_text, dim=cls._dim)
        sims = cls._recipe_vectors @ q
        k = max(1, min(k, sims.shape[0]))
        top_idx = np.argpartition(-sims, kth=k - 1)[:k]
        top_idx = top_idx[np.argsort(-sims[top_idx])]
        return [cls._recipes[i] for i in top_idx]

    @staticmethod
    def extract_json(text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            raise ValueError("Empty response, no JSON found")
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.IGNORECASE | re.DOTALL).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object delimiters found")
        raw = text[start:end + 1]
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e

    @staticmethod
    def sanitize_menu(menu_json: Dict[str, Any], recipes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        LLMClient.load_recipes()
        source = recipes if recipes is not None else LLMClient._recipes
        valid_ids = {r.get("id") for r in source}
        id_to_recipe = {r.get("id"): r for r in source}
        result = LLMClient._result.copy()
        for meal in ["breakfast", "first_snack", "lunch", "second_snack", "dinner"]:
            filtered = []
            for dish in menu_json.get(meal, []) or []:
                rid = dish.get("id")
                if rid in valid_ids:
                    filtered.append(id_to_recipe[rid])
            result[meal] = filtered
        return result

    def generate(self) -> Dict[str, Any]:
        relevant_recipes = self.retrieve_recipes(query_text="Generate menu", k=20)
        retrieved_docs_text = "\n".join([
            f"ID: {r.get('id')} | Name: {r.get('name')} | {r.get('calories')} kcal | "
            f"P: {r.get('protein')} F: {r.get('fat')} C: {r.get('carbs')}"
            for r in relevant_recipes
        ])

        try:
            payload = [
                {"role": "user", "content": f"Available recipes:\n{retrieved_docs_text}"}
            ]
            response = ollama.chat(
                model=MODEL,
                messages=payload,
            )
            bot_message = response["message"]["content"]

            menu_json = self.extract_json(bot_message)
            sanitized = self.sanitize_menu(menu_json, LLMClient._recipes)
            return sanitized
        except Exception as e:
            print(f"Error: {e}")
            return self._result