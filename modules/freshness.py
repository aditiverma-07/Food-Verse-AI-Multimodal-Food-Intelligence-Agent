"""Epic 3: Freshness and spoilage detection.

Two layers:
  1. Local OpenCV colour/texture heuristics (works with no API key).
  2. Optional multimodal LLM diagnosis that refines the verdict.
"""
import numpy as np

CATEGORIES = ["Fruit", "Vegetable", "Meat / Poultry", "Fish / Seafood", "Dairy", "Bakery", "Other"]

STAGES = ["Fresh", "Moderately Fresh", "Spoiled"]
ACTION = {
    "Fresh": "Safe to consume",
    "Moderately Fresh": "Consume within 24h",
    "Spoiled": "Discard immediately",
}

STORAGE_TIPS = {
    "Fruit": ["Store ripe fruit in the fridge crisper; keep bananas and apples apart.",
              "Wash only right before eating to avoid mould."],
    "Vegetable": ["Keep leafy greens wrapped in a dry towel inside a container.",
                  "Store root vegetables in a cool, dark, ventilated place."],
    "Meat / Poultry": ["Refrigerate at or below 4 C and use raw poultry within 1-2 days.",
                       "Freeze portions you will not cook soon; thaw in the fridge."],
    "Fish / Seafood": ["Keep on ice or at 0-2 C and cook within 24 hours.",
                       "Fresh fish should smell mild, not sour or ammonia-like."],
    "Dairy": ["Keep below 4 C and never leave out over 2 hours.",
              "Discard anything with off smell, sliminess or non-surface mould."],
    "Bakery": ["Store in a dry, airtight container; refrigerate in humid weather.",
               "Any visible mould means discarding the whole item."],
    "Other": ["Keep refrigerated, covered and away from raw meat.",
          "When in doubt, throw it out."],
}


def local_cv_signals(img) -> dict:
    """Colour/texture cues from OpenCV. Heuristic, not a lab test."""
    import cv2

    small = np.array(img.convert("RGB").resize((256, 256)))
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    dark = float((v < 55).mean())
    brown = float(((h >= 5) & (h <= 25) & (s > 60) & (v < 140)).mean())
    pale = float(((s < 35) & (v > 150) & (v < 225)).mean())
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    texture = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    issue = dark * 2.0 + brown * 1.6 + pale * 0.8
    if issue < 0.12:
        stage = "Fresh"
    elif issue < 0.35:
        stage = "Moderately Fresh"
    else:
        stage = "Spoiled"
    return {
        "dark_spot_ratio": round(dark, 3),
        "brown_ratio": round(brown, 3),
        "pale_patch_ratio": round(pale, 3),
        "texture_variance": round(texture, 1),
        "issue_index": round(issue, 3),
        "stage": stage,
    }


PROMPT = """You are inspecting a perishable food item ({category}). Evaluate surface texture, colour,
discoloration, wrinkling, slime, bruising and mould. Local computer-vision hints: {hints}
Return JSON with exactly this schema:
{{
  "item": str,
  "stage": "Fresh" | "Moderately Fresh" | "Spoiled",
  "confidence": number 0-100,
  "freshness_score": number 0-100,
  "observations": {{"texture": str, "discoloration": str, "wrinkling": str, "mold": str}},
  "recommendation": "Safe to consume" | "Consume within 24h" | "Discard immediately",
  "shelf_life_estimate": str,
  "storage_tips": [str]
}}"""


def analyze_freshness(client, image, category: str) -> dict:
    local = local_cv_signals(image)
    if client.is_demo:
        stage = local["stage"]
        score = int(max(0, min(100, 100 - local["issue_index"] * 170)))
        return {
            "item": f"{category} item (local analysis)",
            "stage": stage,
            "confidence": 55,
            "freshness_score": score,
            "observations": {
                "texture": f"Texture variance {local['texture_variance']}",
                "discoloration": f"{local['brown_ratio']*100:.1f}% brown and {local['dark_spot_ratio']*100:.1f}% dark pixels",
                "wrinkling": "Not assessed in demo mode",
                "mold": f"{local['pale_patch_ratio']*100:.1f}% pale/grey patches (possible mould)",
            },
            "recommendation": ACTION[stage],
            "shelf_life_estimate": {"Fresh": "Several days if stored properly",
                                    "Moderately Fresh": "About 1 day",
                                    "Spoiled": "None"}[stage],
            "storage_tips": STORAGE_TIPS.get(category, STORAGE_TIPS["Other"]),
            "local": local,
            "_demo": True,
        }
    hints = (f"dark={local['dark_spot_ratio']}, brown={local['brown_ratio']}, "
             f"pale={local['pale_patch_ratio']}, heuristic stage={local['stage']}")
    raw = client.generate_json(PROMPT.format(category=category, hints=hints), images=[image])
    stage = raw.get("stage", local["stage"])
    if stage not in STAGES:
        stage = local["stage"]
    tips = raw.get("storage_tips") or STORAGE_TIPS.get(category, STORAGE_TIPS["Other"])
    obs = raw.get("observations") or {}
    return {
        "item": str(raw.get("item", category)),
        "stage": stage,
        "confidence": float(raw.get("confidence") or 0),
        "freshness_score": float(raw.get("freshness_score") or 0),
        "observations": {k: str(obs.get(k, "n/a")) for k in ("texture", "discoloration", "wrinkling", "mold")},
        "recommendation": ACTION[stage],
        "shelf_life_estimate": str(raw.get("shelf_life_estimate", "Unknown")),
        "storage_tips": [str(t) for t in tips],
        "local": local,
        "_demo": False,
    }
