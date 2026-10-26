"""Epic 2: Food recognition and nutrition audit."""
from .utils import safe_float

PROMPT = """Analyze this meal photo. {note}
Identify the dish, cuisine, visible ingredients and portion size, then estimate nutrition for the
WHOLE visible portion. Return JSON with exactly this schema:
{{
  "dish_name": str, "cuisine": str, "confidence": number 0-100, "portion_size": str,
  "items": [{{"name": str, "estimated_grams": number, "calories": number}}],
  "ingredients": [str],
  "nutrition": {{"calories": number, "protein_g": number, "carbs_g": number, "fat_g": number,
                 "fiber_g": number, "sugar_g": number, "sodium_mg": number}},
  "allergens": [str],
  "health_score": number 1-100,
  "health_notes": [str]
}}"""

DEMO_RESULT = {
    "dish_name": "Paneer Butter Masala with Naan (demo sample)",
    "cuisine": "North Indian",
    "confidence": 88,
    "portion_size": "1 plate (about 450 g)",
    "items": [
        {"name": "Paneer butter masala", "estimated_grams": 250, "calories": 430},
        {"name": "Butter naan", "estimated_grams": 90, "calories": 280},
        {"name": "Onion salad", "estimated_grams": 60, "calories": 25},
    ],
    "ingredients": ["paneer", "tomato", "butter", "cream", "cashew", "wheat flour", "onion", "spices"],
    "nutrition": {"calories": 735, "protein_g": 27, "carbs_g": 62, "fat_g": 42,
                  "fiber_g": 5, "sugar_g": 11, "sodium_mg": 980},
    "allergens": ["Dairy", "Gluten", "Tree nuts"],
    "health_score": 55,
    "health_notes": [
        "Good protein from paneer, but high in saturated fat from butter and cream.",
        "Swap butter naan for a plain roti to cut roughly 100 kcal.",
        "Add a vegetable side to raise fiber.",
    ],
}


def compute_health_score(n: dict) -> int:
    """Transparent rule-based health score (1-100) from macros."""
    cal = n["calories"]
    p, c, f = n["protein_g"], n["carbs_g"], n["fat_g"]
    kcal = max(p * 4 + c * 4 + f * 9, 1)
    p_share, f_share = p * 4 / kcal, f * 9 / kcal
    score = 65
    if 0.15 <= p_share <= 0.35:
        score += 10
    elif p_share < 0.10:
        score -= 8
    if f_share > 0.45:
        score -= 12
    elif f_share <= 0.35:
        score += 4
    if n["fiber_g"] >= 8:
        score += 12
    elif n["fiber_g"] >= 4:
        score += 6
    else:
        score -= 4
    if n["sugar_g"] > 25:
        score -= 10
    elif n["sugar_g"] <= 10:
        score += 3
    if n["sodium_mg"] > 1500:
        score -= 12
    elif n["sodium_mg"] > 800:
        score -= 6
    if cal > 1000:
        score -= 10
    elif cal < 150:
        score -= 3
    return int(max(1, min(100, score)))


def health_band(score: float):
    if score >= 80:
        return "Excellent", "#10B981"
    if score >= 60:
        return "Good", "#3B82F6"
    if score >= 40:
        return "Moderate", "#F59E0B"
    return "Poor", "#EF4444"


def normalize(raw: dict) -> dict:
    n_raw = raw.get("nutrition", {}) or {}
    n = {k: safe_float(n_raw.get(k)) for k in
         ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")}
    items = []
    for it in raw.get("items", []) or []:
        if isinstance(it, dict):
            items.append({"name": str(it.get("name", "Item")),
                          "estimated_grams": safe_float(it.get("estimated_grams")),
                          "calories": safe_float(it.get("calories"))})
    local = compute_health_score(n)
    model_score = safe_float(raw.get("health_score"), 0)
    final = round((local + model_score) / 2) if model_score else local
    return {
        "dish_name": str(raw.get("dish_name", "Unknown dish")),
        "cuisine": str(raw.get("cuisine", "Unknown")),
        "confidence": safe_float(raw.get("confidence"), 0),
        "portion_size": str(raw.get("portion_size", "Not estimated")),
        "items": items,
        "ingredients": [str(i) for i in raw.get("ingredients", []) or []],
        "nutrition": n,
        "allergens": [str(a) for a in raw.get("allergens", []) or []],
        "health_score": int(final),
        "health_notes": [str(x) for x in raw.get("health_notes", []) or []],
    }


def analyze_food(client, image, note: str = "") -> dict:
    if client.is_demo:
        res = normalize(DEMO_RESULT)
        res["_demo"] = True
        return res
    ctx = f"Extra context from the user: {note}" if note else ""
    raw = client.generate_json(PROMPT.format(note=ctx), images=[image])
    res = normalize(raw)
    res["_demo"] = False
    return res
