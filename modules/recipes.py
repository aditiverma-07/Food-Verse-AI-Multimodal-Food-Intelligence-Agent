"""Epic 4b: Smart kitchen recipe assistant."""
import re

PROMPT = """Create {k} creative, nutritious recipes using mainly these pantry ingredients: {pantry}.
Diet preference: {diet}. Max cooking time: {time} minutes. Servings: {servings}.
Mark each ingredient "have": true only if it is in the pantry. Return JSON:
{{"recipes": [{{"name": str, "cook_time_min": number, "difficulty": "Easy"|"Medium"|"Hard",
  "servings": number, "calories_per_serving": number,
  "ingredients": [{{"name": str, "quantity": str, "have": bool}}],
  "steps": [str], "substitutions": [{{"missing": str, "substitute": str}}], "tip": str}}]}}"""

# Offline fallback recipe bank (ingredient keywords are matched against the pantry text).
BANK = [
    {"name": "Veg Fried Rice", "time": 20, "difficulty": "Easy", "cal": 380, "tags": ["vegetarian", "vegan"],
     "ingredients": [("rice", "1.5 cups cooked"), ("carrot", "1"), ("peas", "1/2 cup"), ("onion", "1"), ("garlic", "3 cloves"), ("soy sauce", "1.5 tbsp"), ("oil", "1 tbsp")],
     "steps": ["Heat oil on high; saute garlic and onion for 1 minute.", "Add chopped carrot and peas; stir-fry 3 minutes.", "Add cooked rice and soy sauce; toss 3-4 minutes.", "Season and serve hot."],
     "subs": {"soy sauce": "salt plus a little lemon juice", "peas": "beans or corn"}},
    {"name": "Dal Tadka", "time": 30, "difficulty": "Easy", "cal": 320, "tags": ["vegetarian", "vegan"],
     "ingredients": [("lentils", "1 cup toor/masoor dal"), ("onion", "1"), ("tomato", "2"), ("garlic", "4 cloves"), ("cumin", "1 tsp"), ("turmeric", "1/2 tsp"), ("oil", "1 tbsp")],
     "steps": ["Boil lentils with turmeric and salt until soft (15-20 min).", "Heat oil; crackle cumin; fry garlic, onion and tomato until soft.", "Mix the tadka into the dal and simmer 5 minutes.", "Garnish with coriander."],
     "subs": {"lentils": "split moong or chickpeas", "cumin": "mustard seeds"}},
    {"name": "Masala Omelette", "time": 10, "difficulty": "Easy", "cal": 290, "tags": ["vegetarian", "keto"],
     "ingredients": [("egg", "3"), ("onion", "1/2"), ("tomato", "1"), ("chili", "1"), ("oil", "1 tsp")],
     "steps": ["Beat eggs with salt, chopped onion, tomato and chili.", "Heat oil in a pan on medium.", "Pour the mix, cook 2 minutes per side.", "Serve with toast or roti."],
     "subs": {"chili": "black pepper", "egg": "gram flour batter (besan chilla)"}},
    {"name": "Paneer Bhurji", "time": 15, "difficulty": "Easy", "cal": 340, "tags": ["vegetarian", "keto"],
     "ingredients": [("paneer", "200 g"), ("onion", "1"), ("tomato", "1"), ("capsicum", "1/2"), ("turmeric", "1/4 tsp"), ("oil", "1 tbsp")],
     "steps": ["Saute onion and capsicum for 3 minutes.", "Add tomato and turmeric; cook until soft.", "Crumble in paneer, cook 3 minutes.", "Finish with coriander."],
     "subs": {"paneer": "crumbled firm tofu", "capsicum": "grated carrot"}},
    {"name": "Aloo Gobi", "time": 35, "difficulty": "Medium", "cal": 260, "tags": ["vegetarian", "vegan"],
     "ingredients": [("potato", "2"), ("cauliflower", "1 small"), ("onion", "1"), ("tomato", "1"), ("turmeric", "1/2 tsp"), ("cumin", "1 tsp"), ("oil", "1.5 tbsp")],
     "steps": ["Heat oil, crackle cumin, fry onion until golden.", "Add tomato, turmeric and spices.", "Add potato and cauliflower pieces with a splash of water.", "Cover and cook 15-20 minutes until tender."],
     "subs": {"cauliflower": "broccoli or green beans"}},
    {"name": "Chickpea Salad Bowl", "time": 10, "difficulty": "Easy", "cal": 310, "tags": ["vegetarian", "vegan"],
     "ingredients": [("chickpeas", "1 cup boiled"), ("cucumber", "1"), ("tomato", "1"), ("onion", "1/2"), ("lemon", "1"), ("olive oil", "1 tsp")],
     "steps": ["Combine chickpeas and chopped vegetables.", "Dress with lemon, oil, salt and pepper.", "Rest 5 minutes and serve."],
     "subs": {"chickpeas": "boiled rajma or sprouts", "olive oil": "any cooking oil"}},
    {"name": "Chicken Stir-Fry", "time": 25, "difficulty": "Medium", "cal": 360, "tags": ["keto"],
     "ingredients": [("chicken", "250 g"), ("capsicum", "1"), ("onion", "1"), ("garlic", "3 cloves"), ("soy sauce", "1 tbsp"), ("oil", "1 tbsp")],
     "steps": ["Cut chicken into strips; season with salt and pepper.", "Sear chicken on high heat for 5 minutes; remove.", "Stir-fry garlic, onion, capsicum 3 minutes.", "Return chicken, add soy sauce, toss 2 minutes."],
     "subs": {"chicken": "paneer or tofu", "soy sauce": "salt and lemon"}},
]


def _match(bank_recipe, pantry: str):
    have, missing = [], []
    for name, qty in bank_recipe["ingredients"]:
        (have if name in pantry else missing).append((name, qty))
    return have, missing


def demo_recipes(pantry: str, diet: str, max_time: int, k: int = 3) -> list:
    pantry = pantry.lower()
    ranked = []
    for r in BANK:
        if diet in ("Vegetarian", "Vegan", "Keto") and diet.lower() not in r["tags"]:
            continue
        if r["time"] > max_time:
            continue
        have, missing = _match(r, pantry)
        ranked.append((len(have) / len(r["ingredients"]), r, have, missing))
    ranked.sort(key=lambda x: -x[0])
    out = []
    for _, r, have, missing in ranked[:k]:
        out.append({
            "name": r["name"], "cook_time_min": r["time"], "difficulty": r["difficulty"],
            "servings": 2, "calories_per_serving": r["cal"],
            "ingredients": [{"name": n, "quantity": q, "have": True} for n, q in have]
                           + [{"name": n, "quantity": q, "have": False} for n, q in missing],
            "steps": r["steps"],
            "substitutions": [{"missing": m, "substitute": r["subs"][m]} for m, _ in missing if m in r["subs"]],
            "tip": "Demo recipe from the built-in bank. Add an API key for AI-created recipes.",
        })
    return out


def generate_recipes(client, pantry: str, diet: str, max_time: int, servings: int, k: int = 3) -> dict:
    pantry = re.sub(r"\s+", " ", pantry).strip()
    if not pantry:
        raise ValueError("Please list at least one pantry ingredient.")
    if client.is_demo:
        return {"recipes": demo_recipes(pantry, diet, max_time, k), "_demo": True}
    raw = client.generate_json(PROMPT.format(k=k, pantry=pantry, diet=diet, time=max_time, servings=servings))
    return {"recipes": raw.get("recipes", []) or [], "_demo": False}
