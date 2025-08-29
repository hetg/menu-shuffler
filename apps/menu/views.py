from django.shortcuts import render
from django.http import JsonResponse
from .services.llm import LLMClient
from .services.calculator import Calculator

def _is_ajax(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"

def index(request):
    menu_from_llm = request.session.get("menu_from_llm")
    menu_calculated = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "llm":
            llm = LLMClient()
            menu_from_llm = llm.generate()
            request.session["menu_from_llm"] = menu_from_llm
            if _is_ajax(request):
                return JsonResponse({"ok": True, "menu_from_llm": menu_from_llm})
        elif action == "calc":
            calc = Calculator()
            menu_source = menu_from_llm or request.session.get("menu_from_llm")
            calculated_menu, total_calories = calc.calculate(
                target_calories=request.POST.get("target_calories"),
                breakfast_weight=request.POST.get("breakfast_weight"),
                first_snack_weight=request.POST.get("first_snack_weight"),
                lunch_weight=request.POST.get("lunch_weight"),
                second_snack_weight=request.POST.get("second_snack_weight"),
                dinner_weight=request.POST.get("dinner_weight"),
                menu_from_llm=menu_source,
            )
            menu_calculated = (calculated_menu, total_calories)
            if _is_ajax(request):
                return JsonResponse({
                    "ok": True,
                    "menu_calculated": calculated_menu,
                    "total_calories": total_calories,
                })
        elif action == "clear":
            if "menu_from_llm" in request.session:
                del request.session["menu_from_llm"]
            menu_from_llm = None
            menu_calculated = None
            if _is_ajax(request):
                return JsonResponse({"ok": True, "cleared": True})

    return render(request, "index.html", {"menu_from_llm": menu_from_llm, "menu_calculated": menu_calculated})
