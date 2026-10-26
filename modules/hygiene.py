"""Epic 4a: Kitchen hygiene and food safety compliance."""

CHECKS = {
    "hair_cover": ("Hair cap / hairnet / chef hat", 15),
    "gloves": ("Gloves worn when handling ready-to-eat food", 15),
    "apron_uniform": ("Clean apron / uniform", 10),
    "surfaces": ("Clean, sanitised work surfaces", 15),
    "cross_contamination": ("No cross-contamination (raw meat apart from produce)", 20),
    "food_storage": ("Food covered / stored properly", 10),
    "handwashing": ("Handwashing station accessible and in use", 10),
    "waste": ("Waste bins covered, floors clear", 5),
}

PROMPT = """You are a food-safety inspector reviewing {n} frame(s) from a commercial kitchen.
For EACH check id below decide: "compliant", "violation", or "not_visible" (if it cannot be judged).
Check ids: {ids}
Cross-contamination example: raw poultry placed next to vegetables or ready-to-eat food.
Return JSON with exactly this schema:
{{
  "checks": {{"<check_id>": {{"status": "compliant"|"violation"|"not_visible", "evidence": str,
                              "severity": "low"|"medium"|"high"}}}},
  "staff_count": number,
  "summary": str,
  "corrective_actions": [str]
}}"""

DEMO = {
    "checks": {
        "hair_cover": {"status": "compliant", "evidence": "Both staff wear hairnets.", "severity": "low"},
        "gloves": {"status": "violation", "evidence": "Bare hands handling cooked items.", "severity": "high"},
        "apron_uniform": {"status": "compliant", "evidence": "Clean aprons visible.", "severity": "low"},
        "surfaces": {"status": "compliant", "evidence": "Counters look wiped down.", "severity": "low"},
        "cross_contamination": {"status": "violation", "evidence": "Raw chicken tray beside chopped salad vegetables.", "severity": "high"},
        "food_storage": {"status": "violation", "evidence": "Uncovered containers on the counter.", "severity": "medium"},
        "handwashing": {"status": "not_visible", "evidence": "No sink in frame.", "severity": "low"},
        "waste": {"status": "compliant", "evidence": "Bins are covered.", "severity": "low"},
    },
    "staff_count": 2,
    "summary": "Demo sample: good personal presentation but risky food handling.",
    "corrective_actions": [
        "Separate raw poultry from produce; use colour-coded boards.",
        "Require gloves or utensils for ready-to-eat food.",
        "Cover all prepared food containers.",
    ],
}


def score_checks(checks: dict) -> dict:
    """Weighted compliance score; 'not_visible' checks are excluded from the denominator."""
    earned = possible = 0
    log = []
    for cid, (label, weight) in CHECKS.items():
        c = checks.get(cid) or {}
        status = c.get("status", "not_visible")
        if status not in ("compliant", "violation", "not_visible"):
            status = "not_visible"
        if status != "not_visible":
            possible += weight
            if status == "compliant":
                earned += weight
        log.append({
            "check": label,
            "status": status,
            "severity": c.get("severity", "low") if status == "violation" else "-",
            "evidence": str(c.get("evidence", "")),
        })
    score = round(earned / possible * 100) if possible else None
    return {"score": score, "log": log}


def grade(score):
    if score is None:
        return "Not enough visible evidence", "#6B7280"
    if score >= 90:
        return "Excellent", "#10B981"
    if score >= 75:
        return "Acceptable", "#3B82F6"
    if score >= 50:
        return "Needs improvement", "#F59E0B"
    return "Critical", "#EF4444"


def analyze_hygiene(client, frames) -> dict:
    if client.is_demo:
        raw = DEMO
    else:
        ids = ", ".join(CHECKS.keys())
        raw = client.generate_json(PROMPT.format(n=len(frames), ids=ids), images=frames)
    scored = score_checks(raw.get("checks", {}) or {})
    return {
        "score": scored["score"],
        "log": scored["log"],
        "staff_count": raw.get("staff_count", "n/a"),
        "summary": str(raw.get("summary", "")),
        "corrective_actions": [str(a) for a in raw.get("corrective_actions", []) or []],
        "_demo": client.is_demo,
    }
