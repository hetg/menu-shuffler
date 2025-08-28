import gradio as gr
import pandas as pd
from typing import Dict, List, Any

from algorithm import Algorithm
from llm import LLM

MENU_TABLE_HEADERS = ["Страва", "Порція", "КБЖВ"]
MEAL_TABS = [
    ("Сніданок", "breakfast_table"),
    ("Перший перекус", "first_snack_table"),
    ("Обід", "lunch_table"),
    ("Другий перекус", "second_snack_table"),
    ("Вечеря", "dinner_table"),
]


class MenuUI:
    _menu_from_llm: Dict[str, Any] | None = None

    def __init__(self, algo: Algorithm | None = None):
        self.algo = algo or Algorithm()
        self.demo = None

    @staticmethod
    def _make_weight_input(label: str, value: float):
        return gr.Number(label=label, value=value)

    @staticmethod
    def _make_table():
        return gr.Dataframe(headers=MENU_TABLE_HEADERS, interactive=False)

    @staticmethod
    def _dishes_to_df(dishes: List[Dict[str, Any]]) -> pd.DataFrame:
        rows = []
        for d in dishes:
            kbzhv = f"{d.get('calories', 0)} / {d.get('protein', 0)} / {d.get('fat', 0)} / {d.get('carbs', 0)}"
            rows.append({"Страва": d.get("name", ""), "Порція": d.get("portion", 0), "КБЖВ": kbzhv})
        return pd.DataFrame(rows, columns=MENU_TABLE_HEADERS)

    def _on_generate(
        self,
        target_calories: float,
        breakfast_weight: float,
        first_snack_weight: float,
        lunch_weight: float,
        second_snack_weight: float,
        dinner_weight: float
    ):
        menu, total = self.algo.run_menu(
            target_calories,
            breakfast_weight,
            first_snack_weight,
            lunch_weight,
            second_snack_weight,
            dinner_weight,
            self._menu_from_llm
        )

        breakfast_df = self._dishes_to_df(menu.get("breakfast", []))
        first_snack_df = self._dishes_to_df(menu.get("first_snack", []))
        lunch_df = self._dishes_to_df(menu.get("lunch", []))
        second_snack_df = self._dishes_to_df(menu.get("second_snack", []))
        dinner_df = self._dishes_to_df(menu.get("dinner", []))

        return breakfast_df, first_snack_df, lunch_df, second_snack_df, dinner_df, float(total), gr.update(visible=True), gr.update(visible=True)

    @classmethod
    def _get_menu_from_llm(cls):
        yield (
            None, None, None, None, None,
            gr.update(interactive=False),
            gr.update(interactive=False),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=False),
        )
        llm = LLM()
        cls._menu_from_llm = llm.generate_menu()

        breakfast_df = cls._dishes_to_df(cls._menu_from_llm.get("breakfast", []))
        first_snack_df = cls._dishes_to_df(cls._menu_from_llm.get("first_snack", []))
        lunch_df = cls._dishes_to_df(cls._menu_from_llm.get("lunch", []))
        second_snack_df = cls._dishes_to_df(cls._menu_from_llm.get("second_snack", []))
        dinner_df = cls._dishes_to_df(cls._menu_from_llm.get("dinner", []))

        yield (
            breakfast_df,
            first_snack_df,
            lunch_df,
            second_snack_df,
            dinner_df,
            gr.update(interactive=True),
            gr.update(interactive=True),
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
        )

    def algorithm_ui(self):
        with gr.Row():
            calories_input = gr.Number(label="Кількість калорій", value=1800)
            breakfast_weight = self._make_weight_input("Сніданок (%)", 0.25)
            first_snack_weight = self._make_weight_input("Перший перекус (%)", 0.05)
            lunch_weight = self._make_weight_input("Обід (%)", 0.4)
            second_snack_weight = self._make_weight_input("Другий перекус (%)", 0.05)
            dinner_weight = self._make_weight_input("Вечеря (%)", 0.25)

        run_btn = gr.Button("Порахувати порції", interactive=False)
        total_calories_box = gr.Number(label="Загальна кількість калорій (kcal)", interactive=False, visible=False)

        menu_tabs = gr.Tabs(visible=False)
        with menu_tabs:
            meal_tables: Dict[str, Any] = {}
            for title, key in MEAL_TABS:
                with gr.Tab(title):
                    meal_tables[key] = self._make_table()

        breakfast_table = meal_tables["breakfast_table"]
        first_snack_table = meal_tables["first_snack_table"]
        lunch_table = meal_tables["lunch_table"]
        second_snack_table = meal_tables["second_snack_table"]
        dinner_table = meal_tables["dinner_table"]

        run_btn.click(
            self._on_generate,
            inputs=[
                calories_input,
                breakfast_weight,
                first_snack_weight,
                lunch_weight,
                second_snack_weight,
                dinner_weight
            ],
            outputs=[
                breakfast_table,
                first_snack_table,
                lunch_table,
                second_snack_table,
                dinner_table,
                total_calories_box,
                total_calories_box,
                menu_tabs,
            ],
        )
        return run_btn, menu_tabs, total_calories_box

    def llm_ui(self):
        run_btn_llm = gr.Button("Згенерувати меню")

        llm_tabs = gr.Tabs(visible=False)
        with llm_tabs:
            llm_meal_tables: Dict[str, Any] = {}
            for title, key in MEAL_TABS:
                with gr.Tab(title):
                    llm_meal_tables[key] = self._make_table()

        return run_btn_llm, llm_meal_tables, llm_tabs

    def build(self):
        with gr.Blocks() as demo:
            gr.Markdown("## Генератор меню")
            run_btn_llm, llm_meal_tables, llm_tabs = self.llm_ui()
            run_btn, menu_tabs, total_calories_box = self.algorithm_ui()

            llm_breakfast_table = llm_meal_tables["breakfast_table"]
            llm_first_snack_table = llm_meal_tables["first_snack_table"]
            llm_lunch_table = llm_meal_tables["lunch_table"]
            llm_second_snack_table = llm_meal_tables["second_snack_table"]
            llm_dinner_table = llm_meal_tables["dinner_table"]

            run_btn_llm.click(
                self._get_menu_from_llm,
                outputs=[
                    llm_breakfast_table,
                    llm_first_snack_table,
                    llm_lunch_table,
                    llm_second_snack_table,
                    llm_dinner_table,
                    run_btn,
                    run_btn_llm,
                    llm_tabs,
                    total_calories_box,
                    menu_tabs,
                ],
                show_progress="full",
            )

        self.demo = demo
        return demo

    def launch(self, *args, **kwargs):
        if self.demo is None:
            self.build()
        self.demo.launch(*args, **kwargs)


if __name__ == "__main__":
    MenuUI().launch()
