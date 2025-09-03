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
    _weekly_template = [
        {"breakfast": [], "first_snack": [], "lunch": [], "second_snack": [], "dinner": []}
        for _ in range(7)
    ]
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
    def extract_json(text: str) -> Dict[str, Any] | List[Any]:
        s = (text or "")
        # Remove UTF-8 BOM if present, then trim
        s = s.lstrip("\ufeff").strip()
        if not s:
            raise ValueError("Empty response, no JSON found")

        # Strip Markdown code fences if the text is wrapped in them
        s = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", s, flags=re.IGNORECASE | re.DOTALL).strip()

        # Find the first JSON start delimiter
        m = re.search(r"[\{\[]", s)
        if not m:
            raise ValueError("No JSON start delimiter found")

        # Start decoding from the first { or [
        s2 = s[m.start():]

        try:
            obj, idx = json.JSONDecoder().raw_decode(s2)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}") from e

        return obj

    @staticmethod
    def sanitize_menu(menu_json: Dict[str, Any] | List[Dict[str, Any]], recipes: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any] | List[Dict[str, Any]]:
        LLMClient.load_recipes()
        source = recipes if recipes is not None else LLMClient._recipes
        valid_ids = {r.get("id") for r in source}
        id_to_recipe = {r.get("id"): r for r in source}

        def sanitize_day(day_json: Dict[str, Any]) -> Dict[str, Any]:
            result = LLMClient._result.copy()
            for meal in ["breakfast", "first_snack", "lunch", "second_snack", "dinner"]:
                filtered = []
                for dish in (day_json or {}).get(meal, []) or []:
                    rid = dish.get("id") if isinstance(dish, dict) else None
                    if rid in valid_ids:
                        filtered.append(id_to_recipe[rid])
                result[meal] = filtered
            return result

        if isinstance(menu_json, list):
            # List of days
            days = [sanitize_day(day) for day in menu_json[:7]]
            # Ensure exactly 7 days
            while len(days) < 7:
                days.append(LLMClient._result.copy())
            return days
        else:
            return sanitize_day(menu_json)

    def generate(self) -> List[Dict[str, Any]]:
        relevant_recipes = self.retrieve_recipes(query_text="Generate menu for 7 days", k=20)
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
            print(bot_message)

            menu_json = self.extract_json(bot_message)
            sanitized = self.sanitize_menu(menu_json, LLMClient._recipes)
            # If a single day was returned, replicate to 7 days minimally
            if isinstance(sanitized, dict):
                sanitized = [sanitized.copy() for _ in range(7)]
            # Ensure exactly 7 days
            if isinstance(sanitized, list):
                if len(sanitized) > 7:
                    sanitized = sanitized[:7]
                while len(sanitized) < 7:
                    sanitized.append(LLMClient._result.copy())
            return sanitized
        except Exception as e:
            print(f"Error: {e}")
            return self._weekly_template.copy()