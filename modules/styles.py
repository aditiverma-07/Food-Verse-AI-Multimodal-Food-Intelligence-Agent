"""Styling helpers for the FoodVerse AI UI."""

CSS = """
<style>
.fv-hero {
    background: linear-gradient(120deg, #7C3AED 0%, #EC4899 55%, #F59E0B 100%);
    padding: 1.6rem 1.8rem; border-radius: 18px; color: white; margin-bottom: 1rem;
    box-shadow: 0 8px 24px rgba(124, 58, 237, .25);
}
.fv-hero h1 { margin: 0; font-size: 2rem; color: white; }
.fv-hero p { margin: .3rem 0 0 0; opacity: .95; }
.fv-card {
    background: #ffffff; border: 1px solid #E9D5FF; border-radius: 14px;
    padding: 1rem 1.2rem; margin-bottom: .8rem;
    box-shadow: 0 2px 10px rgba(124, 58, 237, .08);
}
.fv-badge {
    display: inline-block; padding: .25rem .75rem; border-radius: 999px;
    color: white; font-weight: 600; font-size: .85rem; margin: 0 .35rem .35rem 0;
}
.fv-demo {
    background: #FEF3C7; border-left: 5px solid #F59E0B; padding: .6rem 1rem;
    border-radius: 8px; margin-bottom: .8rem; color: #78350F;
}
.fv-big { font-size: 2.4rem; font-weight: 800; line-height: 1.1; }
</style>
"""

GREEN = "#10B981"
AMBER = "#F59E0B"
RED = "#EF4444"
PURPLE = "#7C3AED"
BLUE = "#3B82F6"
GREY = "#6B7280"


def badge(text: str, color: str = PURPLE) -> str:
    return f'<span class="fv-badge" style="background:{color}">{text}</span>'


def score_color(score: float) -> str:
    if score >= 75:
        return GREEN
    if score >= 50:
        return AMBER
    return RED


def hero(title: str, subtitle: str) -> str:
    return f'<div class="fv-hero"><h1>{title}</h1><p>{subtitle}</p></div>'
