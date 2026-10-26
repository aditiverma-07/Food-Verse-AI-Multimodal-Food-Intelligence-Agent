"""Food Verse AI - Multimodal Food Intelligence Agent (Streamlit)."""
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from modules import food_recognition as fr
from modules import freshness as fh
from modules import hygiene as hy
from modules import meal_planner as mp
from modules import recipes as rc
from modules.llm import GEMINI_DEFAULT_MODEL, GROQ_DEFAULT_MODEL, LLMClient, LLMError
from modules.styles import AMBER, BLUE, CSS, GREEN, GREY, PURPLE, RED, badge, hero, score_color
from modules.utils import MAX_VIDEO_MB, InputError, extract_video_frames, load_image

st.set_page_config(page_title="Food Verse AI", page_icon="🥗", layout="wide")
st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- sidebar --
def _secret(name: str) -> str:
    try:
        return st.secrets.get(name, "") or os.environ.get(name, "")
    except Exception:  # noqa: BLE001  (no secrets file)
        return os.environ.get(name, "")


def build_client() -> LLMClient:
    st.sidebar.title("🥗 Food Verse AI")
    st.sidebar.caption("Multimodal Food Intelligence Agent")
    provider = st.sidebar.selectbox("AI provider", ["Demo (no key)", "Gemini", "Groq"])
    if provider.startswith("Demo"):
        st.sidebar.info("Demo mode: sample outputs and local OpenCV analysis, no API calls.")
        return LLMClient("Demo")
    env_key = _secret("GEMINI_API_KEY" if provider == "Gemini" else "GROQ_API_KEY")
    key = st.sidebar.text_input(f"{provider} API key", type="password", value=env_key,
                                help="Kept in memory for this session only.")
    default_model = GEMINI_DEFAULT_MODEL if provider == "Gemini" else GROQ_DEFAULT_MODEL
    model = st.sidebar.text_input("Model", value=default_model)
    client = LLMClient(provider, key, model)
    if client.is_demo:
        st.sidebar.warning("No key entered, so the app is running in demo mode.")
    else:
        st.sidebar.success(f"Live mode: {provider} / {client.model}")
    return client


client = build_client()
st.sidebar.divider()
st.sidebar.caption("Estimates only. This app is not medical advice or a certified food-safety audit.")

st.markdown(hero("Food Verse AI", "Recognize food, check freshness, audit kitchens, cook smarter and plan your week."),
            unsafe_allow_html=True)


def demo_banner(flag: bool, text: str = "Showing demo output. Add an API key in the sidebar for live AI analysis."):
    if flag:
        st.markdown(f'<div class="fv-demo">🧪 {text}</div>', unsafe_allow_html=True)


def run_safely(fn, *args, **kwargs):
    """Call fn and show friendly errors; returns None on failure."""
    try:
        return fn(*args, **kwargs)
    except (LLMError, InputError, ValueError) as exc:
        st.error(str(exc))
    except Exception as exc:  # noqa: BLE001
        st.error(f"Unexpected error: {exc}")
    return None


# ------------------------------------------------------------------ tab 1 --
def tab_food():
    st.subheader("🍽️ Food Recognition & Nutrition Audit")
    up = st.file_uploader("Upload a meal or dish photo", type=["jpg", "jpeg", "png", "webp"], key="food_up")
    note = st.text_input("Optional context", placeholder="e.g. restaurant portion, shared plate", key="food_note")
    if up is None:
        st.info("Upload a photo to get dish recognition, macros, allergens and a health score.")
        return
    try:
        img = load_image(up)
    except InputError as exc:
        st.error(str(exc))
        return
    left, right = st.columns([1, 1.5])
    left.image(img, caption=up.name)
    sig = f"{up.name}-{up.size}"
    if right.button("Analyze meal", type="primary", key="food_btn"):
        with st.spinner("Analyzing the meal..."):
            res = run_safely(fr.analyze_food, client, img, note)
        if res:
            st.session_state["food"] = {"sig": sig, "res": res}
    saved = st.session_state.get("food")
    if not saved or saved["sig"] != sig:
        return
    res = saved["res"]
    n = res["nutrition"]
    with right:
        demo_banner(res["_demo"])
        label, color = fr.health_band(res["health_score"])
        st.markdown(f"### {res['dish_name']}")
        st.markdown(badge(res["cuisine"], PURPLE) + badge(res["portion_size"], BLUE)
                    + badge(f"Confidence {res['confidence']:.0f}%", GREY)
                    + badge(f"Health {res['health_score']}/100 · {label}", color), unsafe_allow_html=True)
    c = st.columns(5)
    c[0].metric("Calories", f"{n['calories']:.0f} kcal")
    c[1].metric("Protein", f"{n['protein_g']:.0f} g")
    c[2].metric("Carbs", f"{n['carbs_g']:.0f} g")
    c[3].metric("Fat", f"{n['fat_g']:.0f} g")
    c[4].metric("Fiber", f"{n['fiber_g']:.0f} g")
    ch1, ch2 = st.columns(2)
    macro = pd.DataFrame({"Macro": ["Protein", "Carbs", "Fat"],
                          "kcal": [n["protein_g"] * 4, n["carbs_g"] * 4, n["fat_g"] * 9]})
    fig = px.pie(macro, names="Macro", values="kcal", hole=0.55, title="Calories by macronutrient",
                 color="Macro", color_discrete_map={"Protein": GREEN, "Carbs": AMBER, "Fat": PURPLE})
    ch1.plotly_chart(fig)
    if res["items"]:
        bar = px.bar(pd.DataFrame(res["items"]), x="calories", y="name", orientation="h",
                     title="Calories per item", color_discrete_sequence=[PURPLE])
        bar.update_layout(yaxis_title="", xaxis_title="kcal")
        ch2.plotly_chart(bar)
    gauge = go.Figure(go.Indicator(mode="gauge+number", value=res["health_score"],
                                   title={"text": "Health score"},
                                   gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}}))
    gauge.update_layout(height=260, margin=dict(t=50, b=10))
    g1, g2 = st.columns([1, 1.4])
    g1.plotly_chart(gauge)
    with g2:
        st.markdown("**Allergen alerts**")
        if res["allergens"]:
            st.markdown("".join(badge("⚠ " + a, RED) for a in res["allergens"]), unsafe_allow_html=True)
        else:
            st.markdown(badge("None detected", GREEN), unsafe_allow_html=True)
        st.markdown("**Ingredients:** " + (", ".join(res["ingredients"]) or "n/a"))
        st.markdown("**Health notes**")
        for note_ in res["health_notes"]:
            st.markdown(f"- {note_}")
        st.caption(f"Sugar ≈ {n['sugar_g']:.0f} g · Sodium ≈ {n['sodium_mg']:.0f} mg")


# ------------------------------------------------------------------ tab 2 --
def tab_freshness():
    st.subheader("🍎 Freshness & Spoilage Diagnostic")
    c1, c2 = st.columns([1, 1])
    category = c1.selectbox("Food category", fh.CATEGORIES, key="fresh_cat")
    up = c2.file_uploader("Upload a photo of the raw item", type=["jpg", "jpeg", "png", "webp"], key="fresh_up")
    if up is None:
        st.info("Upload a close, well-lit photo of a fruit, vegetable, meat or dairy item.")
        return
    try:
        img = load_image(up)
    except InputError as exc:
        st.error(str(exc))
        return
    left, right = st.columns([1, 1.5])
    left.image(img, caption=up.name)
    sig = f"{up.name}-{up.size}-{category}"
    if right.button("Check freshness", type="primary", key="fresh_btn"):
        with st.spinner("Inspecting texture, colour and mould..."):
            res = run_safely(fh.analyze_freshness, client, img, category)
        if res:
            st.session_state["fresh"] = {"sig": sig, "res": res}
    saved = st.session_state.get("fresh")
    if not saved or saved["sig"] != sig:
        return
    res = saved["res"]
    color = {"Fresh": GREEN, "Moderately Fresh": AMBER, "Spoiled": RED}[res["stage"]]
    with right:
        demo_banner(res["_demo"], "Demo mode: verdict comes from local OpenCV colour analysis only.")
        st.markdown(f"### {res['item']}")
        st.markdown(badge(res["stage"], color) + badge(res["recommendation"], color)
                    + badge(f"Confidence {res['confidence']:.0f}%", GREY), unsafe_allow_html=True)
        st.progress(int(max(0, min(100, res["freshness_score"]))) / 100,
                    text=f"Freshness score {res['freshness_score']:.0f}/100")
        st.markdown(f"**Estimated shelf life:** {res['shelf_life_estimate']}")
    o1, o2 = st.columns(2)
    with o1:
        st.markdown("**Observations**")
        for k, v in res["observations"].items():
            st.markdown(f"- **{k.title()}:** {v}")
    with o2:
        st.markdown("**Storage & preservation tips**")
        for t in res["storage_tips"]:
            st.markdown(f"- {t}")
    with st.expander("Local OpenCV signals"):
        st.json(res["local"])
    if res["stage"] == "Spoiled":
        st.error("Do not eat this item. Discard it and clean surfaces it touched.")
    elif res["stage"] == "Moderately Fresh":
        st.warning("Use soon, cook thoroughly, and do not rely on a photo for meat, fish or dairy.")
    st.caption("A photo cannot detect bacteria. Smell, texture and dates matter, so when in doubt, throw it out.")


# ------------------------------------------------------------------ tab 3 --
def tab_hygiene():
    st.subheader("🧑‍🍳 Kitchen Hygiene & Food Safety Compliance")
    up = st.file_uploader("Upload kitchen image(s) or a short video", key="hyg_up",
                          type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "avi", "mkv"],
                          accept_multiple_files=True)
    if not up:
        st.info("Upload up to 4 images, or one short video; frames are sampled automatically.")
        return
    frames = []
    try:
        for f in up[:4]:
            ext = f.name.rsplit(".", 1)[-1].lower()
            if ext in ("mp4", "mov", "avi", "mkv"):
                if f.size > MAX_VIDEO_MB * 1024 * 1024:
                    raise InputError(f"Video is over the {MAX_VIDEO_MB} MB limit.")
                frames += extract_video_frames(f.getvalue(), n=4, suffix="." + ext)
            else:
                frames.append(load_image(f))
    except InputError as exc:
        st.error(str(exc))
        return
    frames = frames[:6]
    st.image(frames, width=220, caption=[f"Frame {i+1}" for i in range(len(frames))])
    sig = "|".join(f"{f.name}-{f.size}" for f in up)
    if st.button("Run hygiene audit", type="primary", key="hyg_btn"):
        with st.spinner("Auditing the kitchen..."):
            res = run_safely(hy.analyze_hygiene, client, frames)
        if res:
            st.session_state["hyg"] = {"sig": sig, "res": res}
    saved = st.session_state.get("hyg")
    if not saved or saved["sig"] != sig:
        return
    res = saved["res"]
    demo_banner(res["_demo"])
    label, color = hy.grade(res["score"])
    a, b = st.columns([1, 1.6])
    with a:
        val = res["score"] if res["score"] is not None else 0
        fig = go.Figure(go.Indicator(mode="gauge+number", value=val, number={"suffix": "%"},
                                     title={"text": "Compliance score"},
                                     gauge={"axis": {"range": [0, 100]}, "bar": {"color": color}}))
        fig.update_layout(height=280, margin=dict(t=50, b=10))
        st.plotly_chart(fig)
        st.markdown(badge(label, color), unsafe_allow_html=True)
    with b:
        st.markdown(f"**Summary:** {res['summary']}")
        st.markdown(f"**Staff detected:** {res['staff_count']}")
        st.markdown("**Corrective actions**")
        for act in res["corrective_actions"]:
            st.markdown(f"- {act}")
    st.markdown("**Itemized compliance log**")
    df = pd.DataFrame(res["log"]).rename(columns=str.title)
    st.dataframe(df, hide_index=True)
    violations = [r for r in res["log"] if r["status"] == "violation"]
    if violations:
        st.error(f"{len(violations)} violation(s) logged.")
    st.caption("AI-assisted screening only; it does not replace an inspection by a qualified food-safety officer.")


# ------------------------------------------------------------------ tab 4 --
def tab_recipes():
    st.subheader("👩‍🍳 Smart Kitchen Recipe Assistant")
    pantry = st.text_area("What is in your pantry?", key="pantry",
                          placeholder="rice, onion, tomato, eggs, peas, garlic, soy sauce")
    c1, c2, c3 = st.columns(3)
    diet = c1.selectbox("Diet", ["Any", "Vegetarian", "Vegan", "Keto"], key="rec_diet")
    max_time = c2.slider("Max cooking time (min)", 10, 90, 40, 5, key="rec_time")
    servings = c3.number_input("Servings", 1, 10, 2, key="rec_serv")
    if st.button("Generate recipes", type="primary", key="rec_btn"):
        with st.spinner("Cooking up ideas..."):
            res = run_safely(rc.generate_recipes, client, pantry, diet, max_time, int(servings))
        if res is not None:
            st.session_state["recipes"] = res
    res = st.session_state.get("recipes")
    if not res:
        return
    demo_banner(res["_demo"], "Showing recipes from the built-in bank. Add an API key for AI-created recipes.")
    if not res["recipes"]:
        st.warning("No recipes matched. Try a longer time limit, another diet, or more ingredients.")
        return
    for r in res["recipes"]:
        title = f"{r.get('name', 'Recipe')} · {r.get('cook_time_min', '?')} min · {r.get('difficulty', '')}"
        with st.expander(title, expanded=True):
            st.markdown(badge(f"{r.get('calories_per_serving', '?')} kcal/serving", GREEN)
                        + badge(f"Serves {r.get('servings', '?')}", BLUE), unsafe_allow_html=True)
            i1, i2 = st.columns([1, 1.6])
            with i1:
                st.markdown("**Ingredients**")
                for ing in r.get("ingredients", []):
                    mark = "✅" if ing.get("have") else "🛒"
                    st.markdown(f"{mark} {ing.get('quantity', '')} {ing.get('name', '')}")
            with i2:
                st.markdown("**Steps**")
                for k, s in enumerate(r.get("steps", []), 1):
                    st.markdown(f"{k}. {s}")
            subs = r.get("substitutions", [])
            if subs:
                st.markdown("**Substitutions:** " + "; ".join(
                    f"{s.get('missing')} → {s.get('substitute')}" for s in subs))
            if r.get("tip"):
                st.caption("💡 " + str(r["tip"]))


# ------------------------------------------------------------------ tab 5 --
def tab_planner():
    st.subheader("📅 Personalized Meal Planner")
    with st.form("profile"):
        a, b, c, d = st.columns(4)
        age = a.number_input("Age", 14, 90, 25)
        gender = b.selectbox("Gender", ["Male", "Female", "Other"])
        weight = c.number_input("Weight (kg)", 30.0, 250.0, 70.0, 0.5)
        height = d.number_input("Height (cm)", 120.0, 230.0, 172.0, 0.5)
        e, f = st.columns(2)
        activity = e.selectbox("Activity level", list(mp.ACTIVITY), index=2)
        goal = f.selectbox("Fitness goal", list(mp.GOALS))
        constraints = st.multiselect("Dietary constraints", mp.CONSTRAINTS)
        g, h = st.columns(2)
        excludes = g.text_input("Allergies / foods to avoid (comma separated)", placeholder="peanut, fish")
        cuisine = h.text_input("Preferred cuisine (live AI mode)", placeholder="Indian")
        submitted = st.form_submit_button("Build my plan", type="primary")
    if submitted:
        if "Vegan" in constraints and "Vegetarian" not in constraints:
            constraints = constraints + ["Vegetarian"]
        targets = mp.calc_targets(age, gender, weight, height, activity, goal, constraints)
        profile = f"{age}y {gender}, {weight} kg, {height} cm, {activity}, goal {goal}"
        with st.spinner("Planning your week..."):
            plan = run_safely(mp.generate_plan, client, targets, profile, constraints, excludes, cuisine)
        if plan:
            st.session_state["plan"] = {"targets": targets, "plan": plan, "goal": goal}
    saved = st.session_state.get("plan")
    if not saved:
        st.info("Fill in your profile to get BMR/TDEE targets, a 7-day plan and a grocery list.")
        return
    targets, plan = saved["targets"], saved["plan"]
    demo_banner(plan["_demo"], "Demo plan built from the offline meal bank. Add an API key for AI-generated plans.")
    m = st.columns(5)
    m[0].metric("BMR", f"{targets['bmr']} kcal")
    m[1].metric("TDEE", f"{targets['tdee']} kcal")
    m[2].metric(f"Target ({saved['goal']})", f"{targets['target']} kcal")
    m[3].metric("Protein", f"{targets['protein_g']} g")
    m[4].metric("Carbs / Fat", f"{targets['carbs_g']} / {targets['fat_g']} g")
    if targets["floor_applied"]:
        st.warning("Your calculated target was below a safe minimum, so a floor was applied. "
                   "Please consult a professional for aggressive fat-loss plans.")
    for tip in plan.get("tips", []):
        st.caption("ℹ️ " + tip)
    day_tabs = st.tabs([d["day"][:3] for d in plan["days"]])
    for tab, day in zip(day_tabs, plan["days"]):
        with tab:
            tot = mp.day_totals(day)
            st.markdown(f"**{day['day']}** · {tot['calories']} kcal · P {tot['protein_g']} g · "
                        f"C {tot['carbs_g']} g · F {tot['fat_g']} g")
            df = pd.DataFrame([{"Meal": x["slot"], "Dish": x["name"], "Portion": f"x{x['portion']}",
                                "kcal": x["calories"], "P (g)": x["protein_g"],
                                "C (g)": x["carbs_g"], "F (g)": x["fat_g"]} for x in day["meals"]])
            st.dataframe(df, hide_index=True)
    st.markdown("### 🛒 Weekly grocery list")
    rows = mp.grocery_list(plan)
    gdf = pd.DataFrame(rows)
    st.dataframe(gdf, hide_index=True)
    d1, d2 = st.columns(2)
    d1.download_button("Download grocery list (CSV)", gdf.to_csv(index=False), "grocery_list.csv", "text/csv")
    d2.download_button("Download plan (JSON)",
                       json.dumps({"targets": targets, "plan": plan}, indent=2, default=list),
                       "meal_plan.json", "application/json")
    st.caption("Targets use the Mifflin-St Jeor equation. Estimates only; consult a dietitian for medical conditions.")


# ------------------------------------------------------------------- main --
tabs = st.tabs(["🍽️ Food & Nutrition", "🍎 Freshness", "🧑‍🍳 Kitchen Hygiene", "👩‍🍳 Recipe Coach", "📅 Meal Planner"])
for tab, fn in zip(tabs, (tab_food, tab_freshness, tab_hygiene, tab_recipes, tab_planner)):
    with tab:
        fn()
