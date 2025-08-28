import numpy as np
from typing import Dict, List, Tuple, Any


class Algorithm:
    @staticmethod
    def _normalize_weights_array(raw_weights, n_items):
        weights = np.array(raw_weights, dtype=float) if raw_weights is not None else np.ones(n_items, dtype=float)
        if not np.isfinite(weights).all() or weights.sum() <= 0:
            return np.ones(n_items, dtype=float) / max(n_items, 1)
        return weights / weights.sum()

    @staticmethod
    def _normalize_meal_weights(meals, provided):
        provided = provided or {}
        filtered = {m: float(provided.get(m, 0.0)) for m in meals}
        total = sum(v for v in filtered.values() if v > 0)
        if total <= 0:
            equal = 1.0 / len(meals) if meals else 0.0
            return {m: equal for m in meals}
        return {m: (v / total if v > 0 else 0.0) for m, v in filtered.items()}

    def optimize_meal(self, meal_recipes: List[Dict[str, Any]], target_calories: float) -> List[Dict[str, Any]]:
        if not meal_recipes:
            return []

        weights = self._normalize_weights_array([r.get("weight", 1.0) for r in meal_recipes], len(meal_recipes))
        calories = np.array([float(r.get("calories", 0.0)) for r in meal_recipes], dtype=float)
        meal_cal = float(np.dot(calories, weights))
        factor = (float(target_calories) / meal_cal) if meal_cal > 1e-9 else 0.0

        optimized = []
        for i, r in enumerate(meal_recipes):
            portion = round(float(weights[i]) * factor, 2)
            optimized.append({
                "name": r.get("name", f"Dish {i+1}"),
                "calories": round(float(r.get("calories", 0.0)) * portion, 2),
                "portion": portion,
                "protein": round(float(r.get("protein", 0.0)) * portion, 2),
                "fat": round(float(r.get("fat", 0.0)) * portion, 2),
                "carbs": round(float(r.get("carbs", 0.0)) * portion, 2)
            })
        return optimized

    def generate_menu_with_weights(
        self,
        menu_dict: Dict[str, List[Dict[str, Any]]],
        target_calories: float,
        meal_weights: Dict[str, float] | None = None
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], float]:
        meals = list(menu_dict.keys())
        weights_norm = self._normalize_meal_weights(meals, meal_weights)

        menu = {}
        for meal, dishes in menu_dict.items():
            weight = weights_norm.get(meal, 0.0)
            target_meal_cal = float(target_calories) * weight
            menu[meal] = self.optimize_meal(dishes, target_meal_cal)

        total_calories = sum(r["calories"] for meal in menu.values() for r in meal)
        return menu, float(round(total_calories, 2))

    def run_menu(
        self,
        target_calories: float,
        breakfast_weight: float,
        first_snack_weight: float,
        lunch_weight: float,
        second_snack_weight: float,
        dinner_weight: float,
        menu_from_llm: Dict[str, List[Dict[str, Any]]] | None = None
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], float]:
        meal_weights = {
            "breakfast": breakfast_weight,
            "first_snack": first_snack_weight,
            "lunch": lunch_weight,
            "second_snack": second_snack_weight,
            "dinner": dinner_weight,
        }

        default_menu = {
            "breakfast": [{"name": "Омлет", "calories": 250, "protein": 18, "fat": 20, "carbs": 2}],
            "first_snack": [{"name": "Банан", "calories": 150, "protein": 10, "fat": 0, "carbs": 50}],
            "lunch": [{"name": "Салат з куркою", "calories": 350, "protein": 30, "fat": 15, "carbs": 10}],
            "second_snack": [{"name": "Банан", "calories": 150, "protein": 10, "fat": 0, "carbs": 50}],
            "dinner": [{"name": "Смажене філе курки", "calories": 450, "protein": 50, "fat": 10, "carbs": 10}]
        }

        effective_menu = menu_from_llm if menu_from_llm is not None else default_menu
        return self.generate_menu_with_weights(effective_menu, target_calories, meal_weights)