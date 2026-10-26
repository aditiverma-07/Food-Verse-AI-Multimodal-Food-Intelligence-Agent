# 🥗 Food Verse AI – Multimodal Food Intelligence Agent

A Streamlit app that combines computer vision (OpenCV), multimodal LLMs (Gemini or Groq/LLaMA) and rule-based
nutrition science to cover five food-intelligence pillars:

| Tab | Epic | What it does |
|---|---|---|
| Food & Nutrition | 2 | Recognizes a dish from a photo; calories, protein, carbs, fat, fiber, allergens, composite health score |
| Freshness | 3 | Classifies Fresh / Moderately Fresh / Spoiled, gives safety advice and storage tips |
| Kitchen Hygiene | 4 | Audits kitchen images or video for hairnets, gloves, cross-contamination and more; compliance % and violation log |
| Recipe Coach | 4 | Pantry-based recipes with time, difficulty, steps and substitutions |
| Meal Planner | 5 | BMR/TDEE, macro targets, 7-day plan, grocery list |

Zero database dependencies. Works with **no API key** in Demo mode.

---

## 1. Quick start

```bash
cd foodverse_ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## 2. Getting an API key (optional, for live AI)

- **Gemini**: create a free key at https://aistudio.google.com/apikey
- **Groq**: create a free key at https://console.groq.com/keys

Paste the key in the sidebar, or preload it without typing:

```toml
# .streamlit/secrets.toml   (never commit this file)
GEMINI_API_KEY = "your-key"
GROQ_API_KEY = "your-key"
```

Model names are editable in the sidebar. If a default model is retired, type a current vision-capable one
(for example another `gemini-*-flash` model or a Groq vision model).

## 3. Demo mode vs live mode

| Feature | Demo (no key) | Live (key) |
|---|---|---|
| Food recognition | Fixed sample result | Real vision analysis |
| Freshness | **Real** local OpenCV colour/texture analysis | LLM diagnosis refined with OpenCV hints |
| Hygiene | Fixed sample audit | Real multi-frame analysis |
| Recipes | Built-in recipe bank matched to your pantry | AI-created recipes |
| Meal plan | Built-in meal bank (diet-filtered, calorie-scaled) | AI-generated plan |
| TDEE / macros / scores | Always computed locally in Python | Same |

## 4. Project structure

```
foodverse_ai/
├── app.py                  # Streamlit UI, 5 tabs + sidebar
├── requirements.txt
├── .streamlit/config.toml  # theme + 50 MB upload limit
└── modules/
    ├── llm.py              # Gemini/Groq REST client, JSON parsing, error handling
    ├── utils.py            # image/video validation, frame extraction (OpenCV), JSON extraction
    ├── food_recognition.py # prompt, normalisation, transparent health-score formula
    ├── freshness.py        # OpenCV heuristics + LLM diagnosis + storage tips
    ├── hygiene.py          # checklist, weighted compliance score, violation log
    ├── recipes.py          # LLM recipes + offline recipe bank
    ├── meal_planner.py     # Mifflin-St Jeor TDEE, macro split, meal bank, grocery aggregation
    └── styles.py           # CSS and badge helpers
```

## 5. How it works

- **JSON data contracts**: every prompt demands a strict JSON schema; `normalize()` functions coerce values so
  a sloppy model reply cannot crash the UI.
- **Health score**: averaged from the model's score and a rule-based score (protein share, fat share, fiber, sugar,
  sodium, calories), so it stays explainable.
- **Hygiene score**: weighted checklist (cross-contamination 20, gloves 15, hair cover 15, surfaces 15, ...).
  Items that are "not visible" are excluded from the denominator rather than counted as violations.
- **Freshness (OpenCV)**: HSV analysis measures dark, brown and pale/grey pixel ratios plus Laplacian texture variance
  and maps an issue index to a stage. It is a heuristic; the LLM refines it in live mode.
- **TDEE**: BMR (Mifflin-St Jeor) x activity factor, then -20% (fat loss) or +10% (muscle gain). A safety floor of
  1200 kcal (1500 for males) is enforced. Keto caps carbs at 50 g; diabetic-friendly raises the fat share.
- **Meal plan**: filters meals by constraints (relaxing gracefully and telling you), applies allergy exclusions,
  scales portions (x0.6 to x1.8) to hit each slot's calorie share, then sums ingredients into a grocery list.

## 6. Deploy on Streamlit Community Cloud (1 click)

1. Push this folder to a GitHub repo (keep `app.py` and `requirements.txt` at the root).
2. Go to https://share.streamlit.io, click **New app**, pick the repo, set main file to `app.py`.
3. In **Advanced settings → Secrets**, paste `GEMINI_API_KEY = "..."` (optional).
4. Deploy.

## 7. Testing checklist

- Demo mode: upload any food photo in tabs 1 and 2; upload any kitchen photo in tab 3; type pantry items in tab 4;
  build a plan in tab 5.
- Edge cases handled: oversize or corrupt images, unreadable video, empty pantry, no matching recipes, API errors
  (bad key, rate limit, timeout, malformed JSON), strict diets with few meals (filters relax with a notice).
- Try Vegan + Keto + Diabetic together to see the relaxation notices.

## 8. Mapping to the project epics

| Epic | Where |
|---|---|
| 1 Requirements & env | `requirements.txt`, sections 1-2 |
| 2 Recognition & nutrition | `modules/food_recognition.py`, Tab 1 |
| 3 Freshness | `modules/freshness.py`, Tab 2 |
| 4 Hygiene + Recipe Coach | `modules/hygiene.py`, `modules/recipes.py`, Tabs 3-4 |
| 5 TDEE meal planner | `modules/meal_planner.py`, Tab 5 |
| 6 Interface, edge cases, deployment | `app.py`, `styles.py`, section 6 |

## 9. Upgrading to the React + FastAPI architecture

The `modules/` package is UI-free, so each service can be exposed as an endpoint with minimal changes:

```python
# api.py (sketch)
from fastapi import FastAPI, UploadFile
from modules.llm import LLMClient
from modules import food_recognition as fr
from PIL import Image
import io

app = FastAPI()

@app.post("/api/food/analyze")
async def analyze(file: UploadFile, provider: str = "Gemini", api_key: str = ""):
    img = Image.open(io.BytesIO(await file.read())).convert("RGB")
    return fr.analyze_food(LLMClient(provider, api_key), img)
```

Then build a React frontend with one page per tab calling `/api/food`, `/api/freshness`, `/api/hygiene`,
`/api/recipes` and `/api/plan`. Further ideas: audio input (Whisper) for voice pantry entry, a trained
PyTorch freshness classifier, per-frame video timelines for hygiene, and persistent user profiles.

## 10. Disclaimer

Outputs are AI estimates for education and convenience. They are not medical advice, a laboratory freshness test,
or an official food-safety inspection.
