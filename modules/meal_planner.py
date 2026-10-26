"""Epic 5: TDEE calculator and adaptive 7-day meal planner with grocery list."""
import random
from collections import defaultdict

from .utils import safe_float

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = ["Breakfast", "Lunch", "Snack", "Dinner"]
SLOT_SPLIT = {"Breakfast": 0.25, "Lunch": 0.33, "Snack": 0.12, "Dinner": 0.30}

ACTIVITY = {
    "Sedentary (little exercise)": 1.2,
    "Lightly active (1-3 days/week)": 1.375,
    "Moderately active (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
    "Extra active (athlete / physical job)": 1.9,
}
GOALS = {"Fat Loss": -0.20, "Maintenance": 0.0, "Muscle Gain": 0.10}
PROTEIN_PER_KG = {"Fat Loss": 2.0, "Maintenance": 1.4, "Muscle Gain": 1.8}
CONSTRAINTS = ["Vegetarian", "Vegan", "Keto", "Diabetic-Friendly"]
_TAG = {"Vegetarian": "vegetarian", "Vegan": "vegan", "Keto": "keto", "Diabetic-Friendly": "diabetic"}


# ----- energy targets -------------------------------------------------------
def calc_bmr(age: int, gender: str, weight_kg: float, height_cm: float) -> float:
    """Mifflin-St Jeor equation."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if gender == "Male":
        return base + 5
    if gender == "Female":
        return base - 161
    return base - 78


def calc_targets(age, gender, weight_kg, height_cm, activity, goal, constraints) -> dict:
    bmr = calc_bmr(age, gender, weight_kg, height_cm)
    tdee = bmr * ACTIVITY[activity]
    target = tdee * (1 + GOALS[goal])
    floor = 1500 if gender == "Male" else 1200
    floor_applied = target < floor
    target = max(target, floor)
    protein_g = weight_kg * PROTEIN_PER_KG[goal]
    if "Keto" in constraints:
        fat_share = 0.70
    elif "Diabetic-Friendly" in constraints:
        fat_share = 0.33
    else:
        fat_share = 0.28
    fat_g = target * fat_share / 9
    carbs_g = max((target - protein_g * 4 - fat_g * 9) / 4, 0)
    if "Keto" in constraints:
        carbs_g = min(carbs_g, 50)
    return {
        "bmr": round(bmr), "tdee": round(tdee), "target": round(target),
        "protein_g": round(protein_g), "fat_g": round(fat_g), "carbs_g": round(carbs_g),
        "floor_applied": floor_applied,
    }


# ----- offline meal bank ----------------------------------------------------
def _m(name, slot, kcal, p, c, f, tags, ings):
    return {"name": name, "slot": slot, "calories": kcal, "protein_g": p, "carbs_g": c, "fat_g": f,
            "tags": set(tags), "ingredients": [{"name": n, "quantity": q, "unit": u} for n, q, u in ings]}


V, VG, K, D = "vegetarian", "vegan", "keto", "diabetic"
MEAL_BANK = [
    # Breakfast
    _m("Vegetable poha with peanuts", "Breakfast", 380, 10, 58, 12, [V, VG], [("Poha", 70, "g"), ("Onion", 40, "g"), ("Peanuts", 15, "g"), ("Green peas", 30, "g"), ("Lemon", 0.25, "pc")]),
    _m("Moong dal chilla with mint chutney", "Breakfast", 330, 20, 40, 9, [V, VG, D], [("Moong dal", 60, "g"), ("Onion", 30, "g"), ("Mint", 10, "g"), ("Oil", 5, "ml")]),
    _m("Oats with berries and chia", "Breakfast", 350, 12, 52, 10, [V, VG], [("Rolled oats", 50, "g"), ("Mixed berries", 80, "g"), ("Chia seeds", 10, "g"), ("Almond milk", 200, "ml")]),
    _m("Masala omelette (3 eggs) with veggies", "Breakfast", 360, 24, 6, 26, [V, K, D], [("Eggs", 3, "pc"), ("Onion", 30, "g"), ("Tomato", 40, "g"), ("Oil", 5, "ml")]),
    _m("Greek yogurt bowl with nuts", "Breakfast", 340, 22, 24, 16, [V, D], [("Greek yogurt", 200, "g"), ("Mixed nuts", 20, "g"), ("Seeds mix", 10, "g")]),
    _m("Paneer bhurji with multigrain roti", "Breakfast", 420, 24, 28, 24, [V, D], [("Paneer", 100, "g"), ("Onion", 40, "g"), ("Tomato", 40, "g"), ("Multigrain atta", 40, "g")]),
    _m("Tofu scramble with spinach", "Breakfast", 310, 22, 10, 20, [V, VG, K, D], [("Firm tofu", 150, "g"), ("Spinach", 60, "g"), ("Onion", 30, "g"), ("Oil", 5, "ml")]),
    _m("Chicken sausage and egg plate", "Breakfast", 400, 30, 6, 28, [K, D], [("Chicken sausage", 100, "g"), ("Eggs", 2, "pc"), ("Spinach", 40, "g")]),
    # Lunch
    _m("Rajma with brown rice and salad", "Lunch", 520, 20, 85, 8, [V, VG], [("Rajma (dry)", 50, "g"), ("Brown rice", 60, "g"), ("Cucumber", 80, "g"), ("Onion", 40, "g"), ("Tomato", 60, "g")]),
    _m("Dal tadka, 2 phulka, cucumber salad", "Lunch", 480, 18, 70, 12, [V, VG], [("Toor dal", 50, "g"), ("Atta", 60, "g"), ("Cucumber", 80, "g"), ("Oil", 8, "ml")]),
    _m("Grilled chicken with quinoa and roasted veg", "Lunch", 540, 45, 48, 16, [D], [("Chicken breast", 150, "g"), ("Quinoa (dry)", 50, "g"), ("Mixed vegetables", 150, "g"), ("Oil", 8, "ml")]),
    _m("Paneer tikka salad bowl", "Lunch", 470, 30, 18, 30, [V, K, D], [("Paneer", 130, "g"), ("Capsicum", 60, "g"), ("Cucumber", 80, "g"), ("Curd", 50, "g"), ("Lettuce", 50, "g")]),
    _m("Chickpea and veg quinoa bowl", "Lunch", 500, 20, 70, 14, [V, VG, D], [("Chickpeas (dry)", 50, "g"), ("Quinoa (dry)", 50, "g"), ("Mixed vegetables", 120, "g"), ("Olive oil", 8, "ml")]),
    _m("Egg curry with cauliflower rice", "Lunch", 430, 26, 14, 28, [V, K, D], [("Eggs", 3, "pc"), ("Cauliflower", 200, "g"), ("Onion", 40, "g"), ("Tomato", 80, "g"), ("Oil", 8, "ml")]),
    _m("Fish curry with brown rice", "Lunch", 520, 35, 55, 16, [], [("Fish fillet", 150, "g"), ("Brown rice", 60, "g"), ("Onion", 40, "g"), ("Tomato", 80, "g"), ("Oil", 8, "ml")]),
    _m("Tofu and broccoli stir-fry", "Lunch", 400, 28, 16, 24, [V, VG, K, D], [("Firm tofu", 180, "g"), ("Broccoli", 150, "g"), ("Garlic", 8, "g"), ("Oil", 10, "ml")]),
    # Snack
    _m("Roasted chana with an apple", "Snack", 190, 8, 32, 3, [V, VG, D], [("Roasted chana", 40, "g"), ("Apple", 1, "pc")]),
    _m("Almonds and walnuts", "Snack", 190, 6, 6, 17, [V, VG, K, D], [("Almonds", 15, "g"), ("Walnuts", 15, "g")]),
    _m("Buttermilk with hummus and cucumber sticks", "Snack", 150, 7, 15, 7, [V, D], [("Buttermilk", 250, "ml"), ("Hummus", 40, "g"), ("Cucumber", 100, "g")]),
    _m("Two boiled eggs", "Snack", 156, 13, 1, 11, [V, K, D], [("Eggs", 2, "pc")]),
    _m("Banana peanut butter toast", "Snack", 250, 8, 36, 9, [V, VG], [("Whole wheat bread", 2, "pc"), ("Banana", 1, "pc"), ("Peanut butter", 15, "g")]),
    _m("Pea-protein shake with almond milk", "Snack", 160, 24, 6, 3, [V, VG, K, D], [("Pea protein powder", 30, "g"), ("Almond milk", 250, "ml")]),
    # Dinner
    _m("Palak paneer with one roti", "Dinner", 470, 24, 34, 26, [V, D], [("Paneer", 100, "g"), ("Spinach", 200, "g"), ("Atta", 40, "g"), ("Onion", 40, "g")]),
    _m("Vegetable khichdi with curd", "Dinner", 430, 16, 70, 9, [V], [("Rice", 40, "g"), ("Moong dal", 40, "g"), ("Mixed vegetables", 120, "g"), ("Curd", 100, "g")]),
    _m("Grilled fish with greens and sweet potato", "Dinner", 470, 38, 36, 16, [D], [("Fish fillet", 160, "g"), ("Sweet potato", 150, "g"), ("Green beans", 100, "g"), ("Oil", 8, "ml")]),
    _m("Chicken tikka with mint raita and salad", "Dinner", 450, 46, 10, 24, [K, D], [("Chicken breast", 180, "g"), ("Curd", 80, "g"), ("Cucumber", 80, "g"), ("Mint", 10, "g")]),
    _m("Tofu and mixed veg curry with one roti", "Dinner", 430, 24, 40, 18, [V, VG, D], [("Firm tofu", 150, "g"), ("Mixed vegetables", 150, "g"), ("Atta", 40, "g"), ("Oil", 8, "ml")]),
    _m("Lentil soup with multigrain toast", "Dinner", 400, 22, 58, 8, [V, VG, D], [("Masoor dal", 60, "g"), ("Carrot", 50, "g"), ("Onion", 40, "g"), ("Multigrain bread", 2, "pc")]),
    _m("Zucchini noodles with paneer and pesto", "Dinner", 440, 26, 12, 32, [V, K, D], [("Zucchini", 250, "g"), ("Paneer", 100, "g"), ("Basil pesto", 30, "g")]),
    _m("Egg bhurji with veggies and roti", "Dinner", 410, 25, 32, 20, [V, D], [("Eggs", 3, "pc"), ("Onion", 40, "g"), ("Tomato", 60, "g"), ("Atta", 40, "g")]),
]


def _eligible(slot, constraints, excludes):
    need = {_TAG[c] for c in constraints}
    notes = []
    for relax in ([], ["diabetic"], ["diabetic", "keto"], ["diabetic", "keto", "vegan"]):
        req = need - set(relax)
        pool = [m for m in MEAL_BANK if m["slot"] == slot and req <= m["tags"]]
        if excludes:
            pool = [m for m in pool
                    if not any(x in m["name"].lower() or any(x in i["name"].lower() for i in m["ingredients"])
                               for x in excludes)]
        if pool:
            if relax:
                notes.append(f"Limited {slot.lower()} options: relaxed {', '.join(relax)}.")
            return pool, notes
    return [], [f"No {slot.lower()} options matched your filters."]


def _scale_meal(m, slot_target):
    factor = max(0.6, min(1.8, slot_target / m["calories"]))
    return {
        "slot": m["slot"], "name": m["name"], "portion": round(factor, 2),
        "calories": round(m["calories"] * factor),
        "protein_g": round(m["protein_g"] * factor), "carbs_g": round(m["carbs_g"] * factor),
        "fat_g": round(m["fat_g"] * factor),
        "ingredients": [{"name": i["name"], "quantity": round(i["quantity"] * factor, 1), "unit": i["unit"]}
                        for i in m["ingredients"]],
    }


def build_offline_plan(targets: dict, constraints, excludes, seed: int = 7) -> dict:
    rng = random.Random(seed)
    excludes = [e.strip().lower() for e in excludes if e.strip()]
    pools, notes = {}, []
    for s in SLOTS:
        pool, n = _eligible(s, constraints, excludes)
        notes += n
        rng.shuffle(pool)
        pools[s] = pool
    days = []
    for d, day in enumerate(DAYS):
        meals = []
        for s in SLOTS:
            pool = pools[s]
            if not pool:
                continue
            meals.append(_scale_meal(pool[d % len(pool)], targets["target"] * SLOT_SPLIT[s]))
        days.append({"day": day, "meals": meals})
    return {"days": days, "tips": notes, "_demo": True}


# ----- LLM plan -------------------------------------------------------------
PROMPT = """Create a 7-day meal plan (Monday-Sunday) for this person.
Profile: {profile}
Daily targets: {cal} kcal, protein {p} g, carbs {c} g, fat {f} g.
Dietary constraints: {constraints}. Foods to avoid or allergies: {excludes}. Preferred cuisine: {cuisine}.
Each day has exactly 4 meals with slot in [Breakfast, Lunch, Snack, Dinner]; each day should total close to the calorie target.
Return JSON: {{"days": [{{"day": str, "meals": [{{"slot": str, "name": str, "calories": number,
 "protein_g": number, "carbs_g": number, "fat_g": number,
 "ingredients": [{{"name": str, "quantity": number, "unit": str}}]}}]}}], "tips": [str]}}"""


def build_llm_plan(client, targets, profile_text, constraints, excludes, cuisine) -> dict:
    raw = client.generate_json(PROMPT.format(
        profile=profile_text, cal=targets["target"], p=targets["protein_g"], c=targets["carbs_g"],
        f=targets["fat_g"], constraints=", ".join(constraints) or "none",
        excludes=excludes or "none", cuisine=cuisine or "any"))
    days = []
    for i, d in enumerate(raw.get("days", []) or []):
        meals = []
        for m in d.get("meals", []) or []:
            ings = []
            for ing in m.get("ingredients", []) or []:
                if isinstance(ing, dict):
                    ings.append({"name": str(ing.get("name", "item")),
                                 "quantity": safe_float(ing.get("quantity"), 1),
                                 "unit": str(ing.get("unit", ""))})
            meals.append({"slot": str(m.get("slot", "Meal")), "name": str(m.get("name", "Meal")),
                          "portion": 1.0, "calories": round(safe_float(m.get("calories"))),
                          "protein_g": round(safe_float(m.get("protein_g"))),
                          "carbs_g": round(safe_float(m.get("carbs_g"))),
                          "fat_g": round(safe_float(m.get("fat_g"))), "ingredients": ings})
        days.append({"day": str(d.get("day", DAYS[i] if i < 7 else f"Day {i+1}")), "meals": meals})
    if not days:
        raise ValueError("The model returned an empty plan.")
    return {"days": days, "tips": [str(t) for t in raw.get("tips", []) or []], "_demo": False}


def generate_plan(client, targets, profile_text, constraints, excludes_text, cuisine) -> dict:
    excludes = [e for e in excludes_text.split(",") if e.strip()]
    if client.is_demo:
        return build_offline_plan(targets, constraints, excludes)
    return build_llm_plan(client, targets, profile_text, constraints, excludes_text, cuisine)


# ----- helpers --------------------------------------------------------------
def day_totals(day: dict) -> dict:
    keys = ("calories", "protein_g", "carbs_g", "fat_g")
    return {k: sum(m[k] for m in day["meals"]) for k in keys}


def grocery_list(plan: dict) -> list:
    agg = defaultdict(float)
    for d in plan["days"]:
        for m in d["meals"]:
            for i in m["ingredients"]:
                agg[(i["name"].strip().title(), i["unit"].strip())] += float(i["quantity"])
    rows = [{"Item": n, "Quantity": round(q, 1), "Unit": u} for (n, u), q in sorted(agg.items())]
    return rows
