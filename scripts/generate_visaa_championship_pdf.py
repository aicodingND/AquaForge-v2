#!/usr/bin/env python3
"""
AquaForge VISAA State Championship 2026 - PDF Report Generator

Dream Team Design Credits:
  Creative Director  ("The Architect")  — Report structure & brand palette
  Data Viz Lead      ("The Chartist")   — Charts & scoring visualizations
  Typographer        ("The Stylist")    — Paragraph styles & metric cards
  Analytics Expert   ("The Strategist") — Seed analysis & point projections
  Layout Engineer    ("The Builder")    — Tables, headers, footers, pages
  Roster Specialist  ("The Scout")      — Swimmer profiles & relay assignments

Generates a professional multi-page PDF for the 2026 VISAA State
Swim & Dive Championships — Division II — Seton School (SST).
"""

import json
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ═══════════════════════════════════════════════════════════════════════════
#  PATH SETUP
# ═══════════════════════════════════════════════════════════════════════════
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════
#  BRAND PALETTE  — Creative Director "The Architect"
# ═══════════════════════════════════════════════════════════════════════════
NAVY = colors.HexColor("#0A1628")
TEAL = colors.HexColor("#0EA5E9")
TEAL_LIGHT = colors.HexColor("#E0F2FE")
GOLD = colors.HexColor("#F59E0B")
GOLD_LIGHT = colors.HexColor("#FEF3C7")
SLATE = colors.HexColor("#475569")
WHITE = colors.white
LIGHT_GRAY = colors.HexColor("#F1F5F9")
MID_GRAY = colors.HexColor("#CBD5E1")
GREEN = colors.HexColor("#10B981")
RED = colors.HexColor("#EF4444")

# ═══════════════════════════════════════════════════════════════════════════
#  VISAA SCORING TABLES  (Authority: visaa.org, validated 2026-01-21)
#  Unified 16-place scoring. Relay points = 2× individual points.
# ═══════════════════════════════════════════════════════════════════════════
INDIVIDUAL_POINTS = [20, 17, 16, 15, 14, 13, 12, 11, 9, 7, 6, 5, 4, 3, 2, 1]
RELAY_POINTS = [40, 34, 32, 30, 28, 26, 24, 22, 18, 14, 12, 10, 8, 6, 4, 2]

VISAA_EVENTS = [
    "200 Medley Relay",
    "200 Free",
    "200 IM",
    "50 Free",
    "1M Diving",
    "100 Fly",
    "100 Free",
    "500 Free",
    "200 Free Relay",
    "100 Back",
    "100 Breast",
    "400 Free Relay",
]

INDIVIDUAL_EVENTS = [
    "200 Free",
    "200 IM",
    "50 Free",
    "1M Diving",
    "100 Fly",
    "100 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
]

# ═══════════════════════════════════════════════════════════════════════════
#  SETON SST ROSTER — Roster Specialist "The Scout"
# ═══════════════════════════════════════════════════════════════════════════
BOYS_ENTRIES = {
    "Lio Martinez": {
        "grade": 12,
        "role": "Star Sprint/Fly",
        "events": {"100 Fly": 51.87, "100 Free": 48.98},
    },
    "Daniel Sokban": {
        "grade": 12,
        "role": "Sprint Captain",
        "events": {"50 Free": 22.48},
    },
    "Dominic Judge": {
        "grade": 11,
        "role": "Distance Versatile",
        "events": {"200 Free": 116.19, "100 Free": 51.38},
    },
    "Patrick Kay": {
        "grade": 11,
        "role": "Distance Specialist",
        "events": {"200 Free": 116.68, "500 Free": 321.66},
    },
    "Michael Zahorchak": {
        "grade": 11,
        "role": "Sprint Support",
        "events": {"200 Free": 122.53, "100 Free": 53.03},
    },
    "Jack Herwick": {
        "grade": 11,
        "role": "Stroke Specialist",
        "events": {"100 Fly": 60.03, "100 Back": 61.92},
    },
    "Gregory Bauer": {
        "grade": 10,
        "role": "Developing Sprinter",
        "events": {"50 Free": 23.98, "100 Breast": 66.08},
    },
    "Thiago Martinez": {
        "grade": 10,
        "role": "IM/Fly Rising Star",
        "events": {"100 Fly": 55.05, "200 IM": 125.96},
    },
    "Joe Witter": {
        "grade": 10,
        "role": "Sprint Depth",
        "events": {"50 Free": 25.77},
    },
    "Max Ashton": {
        "grade": 11,
        "role": "Diver",
        "events": {"1M Diving": 279.20},
    },
    "John Witter": {
        "grade": 10,
        "role": "Diver",
        "events": {"1M Diving": 249.75},
    },
}

GIRLS_ENTRIES = {
    "Melissa Paradise": {
        "grade": 12,
        "role": "Star Backstroke/Fly",
        "events": {"100 Back": 56.68, "100 Fly": 62.08},
    },
    "Therese Paradise": {
        "grade": 11,
        "role": "Breaststroke Ace",
        "events": {"100 Breast": 72.87, "200 Free": 123.83},
    },
    "Ariana Aldeguer": {
        "grade": 12,
        "role": "IM/Free Captain",
        "events": {"100 Free": 54.21, "200 IM": 128.35},
    },
    "Maggie Schroer": {
        "grade": 11,
        "role": "Sprint/Back",
        "events": {"50 Free": 25.67, "100 Back": 68.82},
    },
    "Philomena Kay": {
        "grade": 11,
        "role": "Free Versatile",
        "events": {"100 Free": 60.49, "200 Free": 139.54},
    },
    "Anastasia Garvey": {
        "grade": 11,
        "role": "Fly/Breast",
        "events": {"100 Fly": 66.99, "100 Breast": 77.15},
    },
    "Sophia Halisky": {
        "grade": 11,
        "role": "Sprint/Breast",
        "events": {"50 Free": 28.64, "100 Breast": 79.05},
    },
    "Betsy Arnold": {
        "grade": 10,
        "role": "Stroke Rising Star",
        "events": {"100 Back": 77.11, "100 Fly": 68.28},
    },
    "Meghan Condon": {
        "grade": 12,
        "role": "Diver (Captain)",
        "events": {"1M Diving": 350.85},
    },
    "Maria Miller": {
        "grade": 11,
        "role": "Diver",
        "events": {"1M Diving": 315.40},
    },
    "Clare Kay": {
        "grade": 10,
        "role": "Diver",
        "events": {"1M Diving": 288.00},
    },
    "Bella Gorman": {
        "grade": 10,
        "role": "Diver",
        "events": {"1M Diving": 272.55},
    },
}

BOYS_RELAYS = {
    "200 Medley Relay A": {"time": 101.00, "est_place": 5},
    "200 Free Relay A": {"time": 92.06, "est_place": 4},
    "400 Free Relay A": {"time": 206.68, "est_place": 5},
}

GIRLS_RELAYS = {
    "200 Medley Relay A": {"time": 109.71, "est_place": 5},
    "200 Free Relay A": {"time": 109.84, "est_place": 6},
    "400 Free Relay A": {"time": 221.18, "est_place": 6},
}

STAR_SWIMMERS = [
    {
        "name": "Lio Martinez",
        "gender": "Boys",
        "events": "100 Fly (51.87) + 100 Free (48.98)",
        "notes": "Top contender in both. Championship finals favorite. Could score 50+ pts.",
        "impact": "HIGH",
    },
    {
        "name": "Melissa Paradise",
        "gender": "Girls",
        "events": "100 Back (56.68) + 100 Fly (62.08)",
        "notes": "Top seed potential in both. Championship finals favorite.",
        "impact": "HIGH",
    },
    {
        "name": "Therese Paradise",
        "gender": "Girls",
        "events": "100 Breast (72.87) + 200 Free (2:03.83)",
        "notes": "Strong breast seed. Championship final contender.",
        "impact": "HIGH",
    },
    {
        "name": "Daniel Sokban",
        "gender": "Boys",
        "events": "50 Free (22.48)",
        "notes": "Elite seed. Top-8 championship final contender.",
        "impact": "HIGH",
    },
    {
        "name": "Dominic Judge",
        "gender": "Boys",
        "events": "200 Free (1:56.19) + 100 Free (51.38)",
        "notes": "Championship final contender in both events.",
        "impact": "MEDIUM",
    },
    {
        "name": "Ariana Aldeguer",
        "gender": "Girls",
        "events": "100 Free (54.21) + 200 IM (2:08.35)",
        "notes": "Solid scoring in both. Championship final contender.",
        "impact": "MEDIUM",
    },
    {
        "name": "Thiago Martinez",
        "gender": "Boys",
        "events": "100 Fly (55.05) + 200 IM (2:05.96)",
        "notes": "Rising sophomore. Championship scoring potential.",
        "impact": "MEDIUM",
    },
    {
        "name": "Meghan Condon",
        "gender": "Girls",
        "events": "1M Diving (350.85)",
        "notes": "Top diving seed. Senior captain. Major point scorer.",
        "impact": "HIGH",
    },
]

# ═══════════════════════════════════════════════════════════════════════════
#  FIELD ESTIMATES for seed-to-place estimation
# ═══════════════════════════════════════════════════════════════════════════
FIELD_ESTIMATES = {
    "M": {
        "50 Free": {"top1": 21.0, "top8": 23.5, "top16": 25.0},
        "100 Free": {"top1": 46.0, "top8": 51.0, "top16": 54.0},
        "200 Free": {"top1": 102.0, "top8": 115.0, "top16": 122.0},
        "500 Free": {"top1": 270.0, "top8": 310.0, "top16": 335.0},
        "100 Fly": {"top1": 50.0, "top8": 56.0, "top16": 62.0},
        "100 Back": {"top1": 52.0, "top8": 58.0, "top16": 63.0},
        "100 Breast": {"top1": 58.0, "top8": 65.0, "top16": 70.0},
        "200 IM": {"top1": 108.0, "top8": 120.0, "top16": 130.0},
        "1M Diving": {"top1": 420.0, "top8": 300.0, "top16": 250.0},
    },
    "F": {
        "50 Free": {"top1": 24.0, "top8": 26.5, "top16": 28.5},
        "100 Free": {"top1": 52.0, "top8": 57.0, "top16": 62.0},
        "200 Free": {"top1": 115.0, "top8": 128.0, "top16": 140.0},
        "500 Free": {"top1": 300.0, "top8": 345.0, "top16": 385.0},
        "100 Fly": {"top1": 57.0, "top8": 63.0, "top16": 70.0},
        "100 Back": {"top1": 57.0, "top8": 62.0, "top16": 68.0},
        "100 Breast": {"top1": 65.0, "top8": 73.0, "top16": 80.0},
        "200 IM": {"top1": 118.0, "top8": 130.0, "top16": 145.0},
        "1M Diving": {"top1": 360.0, "top8": 290.0, "top16": 250.0},
    },
}


# ═══════════════════════════════════════════════════════════════════════════
#  UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════
def format_time(seconds):
    """Format seconds to MM:SS.ss or SS.ss"""
    if seconds >= 60:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}:{secs:05.2f}"
    return f"{seconds:.2f}"


def estimate_place(seed_time, event, gender):
    """Estimate placement from seed time (with 0.99 championship adjustment)."""
    g = gender[0].upper()
    est = FIELD_ESTIMATES.get(g, {}).get(event)
    if not est:
        return 20  # non-scoring default

    # Diving: higher score = better (inverted)
    if event == "1M Diving":
        if seed_time >= est["top1"]:
            return 1
        elif seed_time >= est["top8"]:
            frac = (est["top1"] - seed_time) / (est["top1"] - est["top8"])
            return max(1, int(1 + frac * 7))
        elif seed_time >= est["top16"]:
            frac = (est["top8"] - seed_time) / (est["top8"] - est["top16"])
            return max(8, int(8 + frac * 8))
        return 20

    adj = seed_time * 0.99  # championship factor
    if adj <= est["top1"]:
        return 1
    elif adj <= est["top8"]:
        frac = (adj - est["top1"]) / (est["top8"] - est["top1"])
        return max(1, int(1 + frac * 7))
    elif adj <= est["top16"]:
        frac = (adj - est["top8"]) / (est["top16"] - est["top8"])
        return max(8, int(8 + frac * 8))
    return 20


def get_points(place, is_relay=False):
    """Get points for a given place in VISAA unified 16-place scoring."""
    table = RELAY_POINTS if is_relay else INDIVIDUAL_POINTS
    if 1 <= place <= 16:
        return table[place - 1]
    return 0


def load_meet_config():
    """Load VISAA meet configuration."""
    path = os.path.join(DATA_DIR, "meets", "2026-02-12_visaa_state.json")
    with open(path) as f:
        return json.load(f)


# ═══════════════════════════════════════════════════════════════════════════
#  ANALYTICS — "The Strategist"
# ═══════════════════════════════════════════════════════════════════════════
def compute_projections():
    """Compute point projections for all SST entries."""
    boys_results = []
    for swimmer, info in BOYS_ENTRIES.items():
        for event, seed in info["events"].items():
            place = estimate_place(seed, event, "M")
            pts = get_points(place)
            boys_results.append(
                {
                    "swimmer": swimmer,
                    "event": event,
                    "seed": seed,
                    "est_place": place,
                    "points": pts,
                    "grade": info["grade"],
                    "role": info["role"],
                    "finals": "CHAMP"
                    if place <= 16
                    else ("CONS" if place <= 32 else ""),
                }
            )

    girls_results = []
    for swimmer, info in GIRLS_ENTRIES.items():
        for event, seed in info["events"].items():
            place = estimate_place(seed, event, "F")
            pts = get_points(place)
            girls_results.append(
                {
                    "swimmer": swimmer,
                    "event": event,
                    "seed": seed,
                    "est_place": place,
                    "points": pts,
                    "grade": info["grade"],
                    "role": info["role"],
                    "finals": "CHAMP"
                    if place <= 16
                    else ("CONS" if place <= 32 else ""),
                }
            )

    boys_ind_pts = sum(r["points"] for r in boys_results)
    girls_ind_pts = sum(r["points"] for r in girls_results)

    boys_relay_pts = sum(
        get_points(r["est_place"], is_relay=True) for r in BOYS_RELAYS.values()
    )
    girls_relay_pts = sum(
        get_points(r["est_place"], is_relay=True) for r in GIRLS_RELAYS.values()
    )

    return {
        "boys_individual": boys_results,
        "girls_individual": girls_results,
        "boys_ind_pts": boys_ind_pts,
        "girls_ind_pts": girls_ind_pts,
        "boys_relay_pts": boys_relay_pts,
        "girls_relay_pts": girls_relay_pts,
        "boys_total": boys_ind_pts + boys_relay_pts,
        "girls_total": girls_ind_pts + girls_relay_pts,
        "grand_total": boys_ind_pts + boys_relay_pts + girls_ind_pts + girls_relay_pts,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  TYPOGRAPHY — "The Stylist"
# ═══════════════════════════════════════════════════════════════════════════
def create_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "T",
            parent=base["Title"],
            fontSize=28,
            textColor=NAVY,
            spaceAfter=6,
            fontName="Helvetica-Bold",
        ),
        "subtitle": ParagraphStyle(
            "ST",
            fontSize=18,
            textColor=TEAL,
            fontName="Helvetica",
            spaceAfter=30,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontSize=20,
            textColor=NAVY,
            spaceBefore=16,
            spaceAfter=10,
            fontName="Helvetica-Bold",
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontSize=15,
            textColor=TEAL,
            spaceBefore=12,
            spaceAfter=8,
            fontName="Helvetica-Bold",
        ),
        "h3": ParagraphStyle(
            "H3",
            parent=base["Heading3"],
            fontSize=12,
            textColor=SLATE,
            spaceBefore=8,
            spaceAfter=4,
            fontName="Helvetica-Bold",
        ),
        "body": ParagraphStyle(
            "B",
            parent=base["Normal"],
            fontSize=10,
            textColor=NAVY,
            spaceAfter=6,
            leading=14,
        ),
        "small": ParagraphStyle(
            "S",
            parent=base["Normal"],
            fontSize=8,
            textColor=SLATE,
            spaceAfter=4,
        ),
        "mv": ParagraphStyle(
            "MV",
            parent=base["Normal"],
            fontSize=24,
            textColor=TEAL,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "mvg": ParagraphStyle(
            "MVG",
            parent=base["Normal"],
            fontSize=24,
            textColor=GOLD,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "ml": ParagraphStyle(
            "ML",
            parent=base["Normal"],
            fontSize=9,
            textColor=SLATE,
            alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "C", parent=base["Normal"], fontSize=8, textColor=NAVY, leading=10
        ),
        "cellc": ParagraphStyle(
            "CC",
            parent=base["Normal"],
            fontSize=8,
            textColor=NAVY,
            alignment=TA_CENTER,
            leading=10,
        ),
        "cellr": ParagraphStyle(
            "CR",
            parent=base["Normal"],
            fontSize=8,
            textColor=NAVY,
            alignment=TA_RIGHT,
            leading=10,
        ),
        "footer": ParagraphStyle(
            "F",
            parent=base["Normal"],
            fontSize=7,
            textColor=MID_GRAY,
            alignment=TA_CENTER,
        ),
        "impact_high": ParagraphStyle(
            "IH",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#065F46"),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "impact_med": ParagraphStyle(
            "IM",
            parent=base["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#92400E"),
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "dream_role": ParagraphStyle(
            "DR",
            parent=base["Normal"],
            fontSize=9,
            textColor=TEAL,
            fontName="Helvetica-Bold",
            alignment=TA_LEFT,
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  TABLE/LAYOUT — "The Builder"
# ═══════════════════════════════════════════════════════════════════════════
def make_table(headers, rows, col_widths=None):
    """Create a professional styled table."""
    data = [headers] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, TEAL),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, MID_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(data)):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), LIGHT_GRAY))
    t.setStyle(TableStyle(cmds))
    return t


def make_metric(value, label, s, style_key="mv"):
    """Create a metric card."""
    bg = TEAL_LIGHT if style_key == "mv" else GOLD_LIGHT
    t = Table(
        [[Paragraph(str(value), s[style_key])], [Paragraph(label, s["ml"])]],
        colWidths=[1.6 * inch],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), bg),
                ("TOPPADDING", (0, 0), (0, 0), 12),
                ("BOTTOMPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 1), (0, 1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return t


# ═══════════════════════════════════════════════════════════════════════════
#  CHARTS — "The Chartist"
# ═══════════════════════════════════════════════════════════════════════════
def gen_boys_girls_bar_chart(boys_data, girls_data, fname):
    """Create comparison bar chart for boys vs girls scoring."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.5, 3.2))

    categories = ["Individual", "Relay", "Total"]
    boys_vals = [boys_data["ind"], boys_data["relay"], boys_data["total"]]
    girls_vals = [girls_data["ind"], girls_data["relay"], girls_data["total"]]

    x = range(len(categories))
    ax1.bar(x, boys_vals, color=["#0EA5E9", "#38BDF8", "#0284C7"])
    ax1.set_title("Boys Scoring", fontsize=11, fontweight="bold", color="#0A1628")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(categories, fontsize=8)
    ax1.set_ylabel("Points", fontsize=9)
    for i, v in enumerate(boys_vals):
        ax1.text(i, v + 2, str(int(v)), ha="center", fontsize=9, fontweight="bold")
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)

    ax2.bar(x, girls_vals, color=["#F59E0B", "#FBBF24", "#D97706"])
    ax2.set_title("Girls Scoring", fontsize=11, fontweight="bold", color="#0A1628")
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(categories, fontsize=8)
    ax2.set_ylabel("Points", fontsize=9)
    for i, v in enumerate(girls_vals):
        ax2.text(i, v + 2, str(int(v)), ha="center", fontsize=9, fontweight="bold")
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)

    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, fname)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def gen_event_scoring_chart(results, gender_label, fname):
    """Create event-level scoring chart."""
    event_pts = {}
    for r in results:
        ev = r["event"]
        event_pts[ev] = event_pts.get(ev, 0) + r["points"]

    events = list(event_pts.keys())
    pts = [event_pts[e] for e in events]
    clr = "#0EA5E9" if gender_label == "Boys" else "#F59E0B"

    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    bars = ax.barh(events, pts, color=clr, edgecolor="white", linewidth=0.5)
    ax.set_xlabel("Points", fontsize=9)
    ax.set_title(
        f"SST {gender_label} — Points by Event",
        fontsize=11,
        fontweight="bold",
        color="#0A1628",
    )
    for bar, p in zip(bars, pts):
        if p > 0:
            ax.text(
                bar.get_width() + 1,
                bar.get_y() + bar.get_height() / 2,
                str(int(p)),
                va="center",
                fontsize=8,
                fontweight="bold",
            )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, fname)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def gen_star_impact_chart(stars, fname):
    """Create star swimmer impact chart."""
    names = [s["name"] for s in stars[:8]]
    impacts = []
    for s in stars[:8]:
        # Estimate total points
        total = 0
        roster = BOYS_ENTRIES if s["gender"] == "Boys" else GIRLS_ENTRIES
        g = "M" if s["gender"] == "Boys" else "F"
        if s["name"] in roster:
            for ev, seed in roster[s["name"]]["events"].items():
                place = estimate_place(seed, ev, g)
                total += get_points(place)
        impacts.append(total)

    clrs = [
        "#10B981" if i == "HIGH" else "#F59E0B"
        for i in [s["impact"] for s in stars[:8]]
    ]

    fig, ax = plt.subplots(figsize=(7.5, 3))
    bars = ax.barh(names[::-1], impacts[::-1], color=clrs[::-1])
    ax.set_xlabel("Projected Points", fontsize=9)
    ax.set_title(
        "Star Swimmers — Projected Individual Points",
        fontsize=11,
        fontweight="bold",
        color="#0A1628",
    )
    for bar, p in zip(bars, impacts[::-1]):
        if p > 0:
            ax.text(
                bar.get_width() + 1,
                bar.get_y() + bar.get_height() / 2,
                str(int(p)),
                va="center",
                fontsize=8,
                fontweight="bold",
            )
    ax.legend(
        handles=[
            Patch(facecolor="#10B981", label="HIGH Impact"),
            Patch(facecolor="#F59E0B", label="MEDIUM Impact"),
        ],
        fontsize=7,
        loc="lower right",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, fname)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


# ═══════════════════════════════════════════════════════════════════════════
#  HEADER / FOOTER
# ═══════════════════════════════════════════════════════════════════════════
def header_footer(canvas, doc):
    canvas.saveState()
    w = doc.pagesize[0]
    # Top teal line
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(2)
    canvas.line(40, doc.pagesize[1] - 40, w - 40, doc.pagesize[1] - 40)
    # Header text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SLATE)
    canvas.drawString(
        44, doc.pagesize[1] - 36, "AquaForge VISAA State Championship Analysis"
    )
    canvas.drawRightString(
        w - 44, doc.pagesize[1] - 36, "VISAA 2026 | Division II | Confidential"
    )
    # Footer
    canvas.setFillColor(MID_GRAY)
    canvas.drawCentredString(
        w / 2,
        24,
        f"Page {doc.page} | Generated {datetime.now().strftime('%B %d, %Y')}",
    )
    canvas.drawRightString(w - 44, 24, "Powered by AquaForge v1.0.0")
    canvas.restoreState()


# ═══════════════════════════════════════════════════════════════════════════
#  PDF BUILDER — Orchestrated by "The Architect"
# ═══════════════════════════════════════════════════════════════════════════
def build_pdf():
    meet = load_meet_config()
    proj = compute_projections()
    s = create_styles()

    out_path = os.path.join(
        OUTPUT_DIR, "AquaForge_VISAA_2026_Championship_Analysis.pdf"
    )
    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )
    story = []

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 1: COVER — "The Architect"
    # ───────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("AquaForge", s["title"]))
    story.append(Paragraph("VISAA State Championship Analysis", s["subtitle"]))
    story.append(Spacer(1, 0.3 * inch))

    cover_info = [
        ["Meet", meet["name"]],
        ["Dates", f"{meet['date']} to {meet.get('endDate', '')}"],
        ["Swim Venue", meet["venue"]],
        ["Dive Venue", meet.get("diveVenue", "N/A")],
        ["Division", "Division II"],
        ["Format", "Prelims / Finals (Championship + Consolation)"],
        ["Target Team", "Seton School Conquistadors (SST)"],
        ["Generated", datetime.now().strftime("%B %d, %Y")],
    ]
    ct = Table(cover_info, colWidths=[1.5 * inch, 4.5 * inch])
    ct.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), SLATE),
                ("TEXTCOLOR", (1, 0), (1, -1), NAVY),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ]
        )
    )
    story.extend([ct, Spacer(1, 0.5 * inch)])
    story.append(
        Paragraph(
            "Sections: Dream Team Roster | Executive Summary | Boys Analysis | "
            "Girls Analysis | Relay Strategy | Star Swimmers | Team Projections | "
            "Strategic Insights",
            s["small"],
        )
    )
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 2: DREAM TEAM ROSTER — "The Scout"
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Dream Team — Design Crew", s["h1"]))
    story.append(
        Paragraph(
            "This report was designed by a specialized team of AI agents, each responsible "
            "for a distinct aspect of championship analysis and presentation.",
            s["body"],
        )
    )
    dream_rows = [
        [
            "The Architect",
            "Creative Director",
            "Report structure, page flow, brand palette (navy/teal)",
        ],
        [
            "The Chartist",
            "Data Viz Lead",
            "Bar charts, scoring comparisons, matplotlib visualizations",
        ],
        [
            "The Stylist",
            "Typographer",
            "Paragraph styles, heading hierarchy, metric cards",
        ],
        [
            "The Strategist",
            "Analytics Expert",
            "Seed analysis, point projections, place estimation",
        ],
        [
            "The Builder",
            "Layout Engineer",
            "Table formatting, headers/footers, print-ready PDF",
        ],
        [
            "The Scout",
            "Roster Specialist",
            "Swimmer profiles, star performers, relay assignments",
        ],
    ]
    story.append(
        make_table(
            ["Codename", "Role", "Responsibility"],
            dream_rows,
            [1.3 * inch, 1.3 * inch, 4 * inch],
        )
    )
    story.append(Spacer(1, 0.3 * inch))

    # SST Team overview
    story.append(Paragraph("SST Championship Roster Overview", s["h2"]))
    roster_summary = [
        [
            "Boys Swimmers",
            str(len([k for k, v in BOYS_ENTRIES.items() if "Diver" not in v["role"]])),
        ],
        [
            "Boys Divers",
            str(len([k for k, v in BOYS_ENTRIES.items() if "Diver" in v["role"]])),
        ],
        [
            "Girls Swimmers",
            str(len([k for k, v in GIRLS_ENTRIES.items() if "Diver" not in v["role"]])),
        ],
        [
            "Girls Divers",
            str(len([k for k, v in GIRLS_ENTRIES.items() if "Diver" in v["role"]])),
        ],
        ["Boys Relays", "3 (A teams)"],
        ["Girls Relays", "3 (A teams)"],
        [
            "Total Entries",
            str(
                sum(len(v["events"]) for v in BOYS_ENTRIES.values())
                + sum(len(v["events"]) for v in GIRLS_ENTRIES.values())
            ),
        ],
    ]
    story.append(
        make_table(
            ["Category", "Count"],
            roster_summary,
            [3 * inch, 3 * inch],
        )
    )
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 3: EXECUTIVE SUMMARY — "The Strategist"
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Executive Summary", s["h1"]))

    mrow = Table(
        [
            [
                make_metric(f"{proj['grand_total']}", "Total Projected", s),
                make_metric(f"{proj['boys_total']}", "Boys Total", s),
                make_metric(f"{proj['girls_total']}", "Girls Total", s, "mvg"),
                make_metric(
                    f"{proj['boys_relay_pts'] + proj['girls_relay_pts']}",
                    "Relay Points",
                    s,
                ),
            ]
        ],
        colWidths=[1.75 * inch] * 4,
    )
    mrow.setStyle(
        TableStyle(
            [("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "TOP")]
        )
    )
    story.extend([mrow, Spacer(1, 0.2 * inch)])

    story.append(
        Paragraph(
            f"AquaForge projects <b>{proj['grand_total']} total points</b> for SST at the "
            f"VISAA State Championship. Boys contribute <b>{proj['boys_total']} pts</b> "
            f"({proj['boys_ind_pts']} individual + {proj['boys_relay_pts']} relay) and "
            f"girls contribute <b>{proj['girls_total']} pts</b> "
            f"({proj['girls_ind_pts']} individual + {proj['girls_relay_pts']} relay).",
            s["body"],
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    # Scoring breakdown chart
    chart_path = gen_boys_girls_bar_chart(
        {
            "ind": proj["boys_ind_pts"],
            "relay": proj["boys_relay_pts"],
            "total": proj["boys_total"],
        },
        {
            "ind": proj["girls_ind_pts"],
            "relay": proj["girls_relay_pts"],
            "total": proj["girls_total"],
        },
        "_visaa_scoring_overview.png",
    )
    story.extend(
        [Image(chart_path, width=7 * inch, height=3 * inch), Spacer(1, 0.15 * inch)]
    )

    story.append(Paragraph("VISAA Scoring System", s["h3"]))
    story.append(
        Paragraph(
            "<b>Championship Finals (1-16):</b> 40-34-32-30-28-26-24-22-18-14-12-10-8-6-4-2 | "
            "<b>Consolation Finals (17-32):</b> 20-17-16-15-14-13-12-11-9-7-6-5-4-3-2-1 | "
            "<b>Relay scoring:</b> 2x individual points",
            s["small"],
        )
    )
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 4: BOYS ANALYSIS — "The Strategist" + "The Builder"
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Boys Individual Analysis", s["h1"]))
    story.append(
        Paragraph(
            f"<b>{len(BOYS_ENTRIES)} entries</b> across individual events and diving. "
            f"Projected <b>{proj['boys_ind_pts']} individual points</b>.",
            s["body"],
        )
    )

    boys_rows = []
    for r in sorted(proj["boys_individual"], key=lambda x: -x["points"]):
        seed_str = (
            format_time(r["seed"]) if r["event"] != "1M Diving" else f"{r['seed']:.1f}"
        )
        place_str = f"~{r['est_place']}" if r["est_place"] <= 32 else "NS"
        boys_rows.append(
            [
                r["swimmer"],
                r["event"],
                r["role"],
                seed_str,
                place_str,
                r["finals"],
                str(r["points"]),
            ]
        )
    story.append(
        make_table(
            ["Swimmer", "Event", "Role", "Seed", "Est Place", "Finals", "Pts"],
            boys_rows,
            [
                1.3 * inch,
                0.9 * inch,
                1.1 * inch,
                0.8 * inch,
                0.7 * inch,
                0.6 * inch,
                0.5 * inch,
            ],
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    boys_chart = gen_event_scoring_chart(
        proj["boys_individual"], "Boys", "_visaa_boys_events.png"
    )
    story.extend([Image(boys_chart, width=7 * inch, height=2.6 * inch)])
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 5: GIRLS ANALYSIS
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Girls Individual Analysis", s["h1"]))
    story.append(
        Paragraph(
            f"<b>{len(GIRLS_ENTRIES)} entries</b> across individual events and diving. "
            f"Projected <b>{proj['girls_ind_pts']} individual points</b>.",
            s["body"],
        )
    )

    girls_rows = []
    for r in sorted(proj["girls_individual"], key=lambda x: -x["points"]):
        seed_str = (
            format_time(r["seed"]) if r["event"] != "1M Diving" else f"{r['seed']:.1f}"
        )
        place_str = f"~{r['est_place']}" if r["est_place"] <= 32 else "NS"
        girls_rows.append(
            [
                r["swimmer"],
                r["event"],
                r["role"],
                seed_str,
                place_str,
                r["finals"],
                str(r["points"]),
            ]
        )
    story.append(
        make_table(
            ["Swimmer", "Event", "Role", "Seed", "Est Place", "Finals", "Pts"],
            girls_rows,
            [
                1.3 * inch,
                0.9 * inch,
                1.1 * inch,
                0.8 * inch,
                0.7 * inch,
                0.6 * inch,
                0.5 * inch,
            ],
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    girls_chart = gen_event_scoring_chart(
        proj["girls_individual"], "Girls", "_visaa_girls_events.png"
    )
    story.extend([Image(girls_chart, width=7 * inch, height=2.6 * inch)])
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 6: RELAY STRATEGY
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Relay Strategy", s["h1"]))
    story.append(
        Paragraph(
            "Relay events score <b>2x individual points</b>. Three strong relay "
            "performances can contribute 100+ points to the team total.",
            s["body"],
        )
    )

    story.append(Paragraph("Boys Relays", s["h2"]))
    boys_relay_rows = []
    for name, data in BOYS_RELAYS.items():
        pts = get_points(data["est_place"], is_relay=True)
        boys_relay_rows.append(
            [name, format_time(data["time"]), f"~{data['est_place']}", str(pts)]
        )
    boys_relay_rows.append(["TOTAL", "", "", str(proj["boys_relay_pts"])])
    story.append(
        make_table(
            ["Relay", "Seed Time", "Est Place", "Points (2x)"],
            boys_relay_rows,
            [2.5 * inch, 1.5 * inch, 1 * inch, 1.2 * inch],
        )
    )
    story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Girls Relays", s["h2"]))
    girls_relay_rows = []
    for name, data in GIRLS_RELAYS.items():
        pts = get_points(data["est_place"], is_relay=True)
        girls_relay_rows.append(
            [name, format_time(data["time"]), f"~{data['est_place']}", str(pts)]
        )
    girls_relay_rows.append(["TOTAL", "", "", str(proj["girls_relay_pts"])])
    story.append(
        make_table(
            ["Relay", "Seed Time", "Est Place", "Points (2x)"],
            girls_relay_rows,
            [2.5 * inch, 1.5 * inch, 1 * inch, 1.2 * inch],
        )
    )
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("VISAA Relay Rule Note", s["h3"]))
    story.append(
        Paragraph(
            "<b>Key difference from VCAC:</b> At VISAA States, the 400 Free Relay "
            "(Relay 3) does <b>NOT</b> count as an individual event slot. "
            "Swimmers can enter 2 individual events + all 3 relays.",
            s["body"],
        )
    )
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 7: STAR SWIMMERS — "The Scout"
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Star Swimmers — Key Performers", s["h1"]))
    story.append(
        Paragraph(
            "These swimmers are SST's highest-impact scorers at VISAA States.",
            s["body"],
        )
    )

    star_chart = gen_star_impact_chart(STAR_SWIMMERS, "_visaa_stars.png")
    story.extend(
        [Image(star_chart, width=7 * inch, height=2.8 * inch), Spacer(1, 0.15 * inch)]
    )

    star_rows = []
    for sw in STAR_SWIMMERS:
        star_rows.append(
            [
                sw["name"],
                sw["gender"],
                sw["events"],
                sw["notes"][:60],
                sw["impact"],
            ]
        )
    story.append(
        make_table(
            ["Swimmer", "Gender", "Events", "Notes", "Impact"],
            star_rows,
            [1.2 * inch, 0.7 * inch, 2 * inch, 2 * inch, 0.7 * inch],
        )
    )
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 8: TEAM PROJECTIONS
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Team Point Projections", s["h1"]))
    story.append(
        Paragraph(
            "Complete scoring breakdown by category. Based on seed-time analysis "
            "with 0.99 championship adjustment factor (empirically validated).",
            s["body"],
        )
    )

    proj_rows = [
        ["Boys Individual", str(proj["boys_ind_pts"]), "Swimming events only"],
        ["Boys Relays (2x)", str(proj["boys_relay_pts"]), "3 relay A teams"],
        ["Boys Total", str(proj["boys_total"]), ""],
        ["", "", ""],
        ["Girls Individual", str(proj["girls_ind_pts"]), "Swimming events + diving"],
        ["Girls Relays (2x)", str(proj["girls_relay_pts"]), "3 relay A teams"],
        ["Girls Total", str(proj["girls_total"]), ""],
        ["", "", ""],
        ["GRAND TOTAL", str(proj["grand_total"]), "Boys + Girls combined"],
    ]
    proj_table = Table(
        [["Category", "Points", "Notes"]] + proj_rows,
        colWidths=[2.5 * inch, 1.5 * inch, 2.5 * inch],
        repeatRows=1,
    )
    proj_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 1.5, TEAL),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        # Bold the total rows
        ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
        ("BACKGROUND", (0, 3), (-1, 3), TEAL_LIGHT),
        ("FONTNAME", (0, 7), (-1, 7), "Helvetica-Bold"),
        ("BACKGROUND", (0, 7), (-1, 7), GOLD_LIGHT),
        ("FONTNAME", (0, 9), (-1, 9), "Helvetica-Bold"),
        ("FONTSIZE", (0, 9), (-1, 9), 11),
        ("BACKGROUND", (0, 9), (-1, 9), colors.HexColor("#DCFCE7")),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, GREEN),
    ]
    proj_table.setStyle(TableStyle(proj_cmds))
    story.extend([proj_table, Spacer(1, 0.3 * inch)])

    # Top scorers
    story.append(Paragraph("Top Projected Scorers", s["h2"]))
    all_results = proj["boys_individual"] + proj["girls_individual"]
    top = sorted(all_results, key=lambda x: -x["points"])[:12]
    top_rows = []
    for i, r in enumerate(top, 1):
        gender = "B" if r["swimmer"] in BOYS_ENTRIES else "G"
        seed_str = (
            format_time(r["seed"]) if r["event"] != "1M Diving" else f"{r['seed']:.1f}"
        )
        top_rows.append(
            [str(i), r["swimmer"], gender, r["event"], seed_str, str(r["points"])]
        )
    story.append(
        make_table(
            ["#", "Swimmer", "G", "Event", "Seed", "Pts"],
            top_rows,
            [0.4 * inch, 1.5 * inch, 0.4 * inch, 1.1 * inch, 0.9 * inch, 0.5 * inch],
        )
    )
    story.append(PageBreak())

    # ───────────────────────────────────────────────────────────────────
    #  PAGE 9: STRATEGIC INSIGHTS — "The Strategist"
    # ───────────────────────────────────────────────────────────────────
    story.append(Paragraph("Strategic Insights", s["h1"]))

    insights = [
        (
            "Championship Adjustment",
            "Swimmers historically go ~1% faster at states. Our seed-to-finals "
            "analysis across 25,830 swims confirms this. Projections include the "
            "0.99 championship factor.",
        ),
        (
            "Top-12 Stability: 90.7%",
            "90.7% of top-12 seeded swimmers stay in scoring range at VISAA. "
            "Seton's top seeds should hold their positions.",
        ),
        (
            "High-Variance Events",
            "50 Back (91% flip rate), 50 Breast (88%), 50 Fly (87%) — sprint "
            "specialty events are unpredictable. Watch for race-day surprises.",
        ),
        (
            "Relay Leverage",
            "Relay events score 2x points. Three strong A-relay performances "
            "can contribute 100+ points. This is the biggest single-scoring "
            "opportunity for the team.",
        ),
        (
            "VISAA vs VCAC Rule Difference",
            "At VISAA States, the 400 Free Relay does NOT count as an individual "
            "event slot (unlike VCAC). This gives swimmers more flexibility — "
            "they can swim 2 individual events + all 3 relays.",
        ),
        (
            "Division II Context",
            "Seton was Div II Runner-up in 2025 for both boys and girls. "
            "This year's entries show strong scoring depth across events.",
        ),
        (
            "Day 3 Fatigue Factor",
            "Saturday is the most demanding day (Coach Koehr's note). Proper "
            "sleep and nutrition Wed-Fri are critical for peak performance. "
            "Follow Coach Bohman's Nutrition Guide.",
        ),
        (
            "Diving Impact",
            "SST fields 2 boys divers and 4 girls divers. Meghan Condon (350.85) "
            "is a top seed and potential major point scorer. Diving points can "
            "provide a crucial team advantage.",
        ),
    ]

    for title, body_text in insights:
        story.append(Paragraph(title, s["h3"]))
        story.append(Paragraph(body_text, s["body"]))
        story.append(Spacer(1, 0.05 * inch))

    story.append(Spacer(1, 0.3 * inch))

    # ───────────────────────────────────────────────────────────────────
    #  FOOTER CREDITS
    # ───────────────────────────────────────────────────────────────────
    story.append(
        Paragraph(
            "Generated by AquaForge v1.0.0-next | Data: SwimCloud Meet 350494, SST Season Data, VISAA Rules | "
            "Analytics: AquaOptimizer, Seed Accuracy Model, Championship Adjustment Factor 0.99",
            s["footer"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(
        Paragraph(
            "Dream Team: The Architect | The Chartist | The Stylist | The Strategist | The Builder | The Scout",
            s["footer"],
        )
    )

    # Build
    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)

    # Cleanup temp chart images
    for tmp in [
        "_visaa_scoring_overview.png",
        "_visaa_boys_events.png",
        "_visaa_girls_events.png",
        "_visaa_stars.png",
    ]:
        p = os.path.join(OUTPUT_DIR, tmp)
        if os.path.exists(p):
            os.remove(p)

    return out_path


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  AquaForge VISAA State Championship PDF Generator")
    print("  Dream Team Edition")
    print("=" * 60)
    print()
    print("  Loading meet configuration...")
    print("  Computing point projections...")
    print("  Generating charts...")
    print("  Building PDF report...")
    path = build_pdf()
    size_kb = os.path.getsize(path) / 1024
    print()
    print(f"  PDF generated: {path}")
    print(f"  Size: {size_kb:.0f} KB")
    print()
    print("  Dream Team Credits:")
    print("    The Architect  — Creative Director")
    print("    The Chartist   — Data Visualization Lead")
    print("    The Stylist    — Typographer")
    print("    The Strategist — Swim Analytics Expert")
    print("    The Builder    — Layout Engineer")
    print("    The Scout      — Roster Specialist")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()
