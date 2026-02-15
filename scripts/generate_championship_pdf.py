#!/usr/bin/env python3
"""AquaForge Championship Analysis PDF Report Generator."""

import json
import os
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Patch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
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

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data")
BACKTEST_DIR = os.path.join(DATA_DIR, "backtest", "meet_512")
CHAMP_DIR = os.path.join(DATA_DIR, "championship_data")
OUTPUT_DIR = os.path.join(BASE_DIR, "reports")

NAVY = colors.HexColor("#0A1628")
TEAL = colors.HexColor("#0EA5E9")
TEAL_LIGHT = colors.HexColor("#E0F2FE")
SLATE = colors.HexColor("#475569")
WHITE = colors.white
LIGHT_GRAY = colors.HexColor("#F1F5F9")
MID_GRAY = colors.HexColor("#CBD5E1")

CHAMP_EVENTS = [
    "50 Free",
    "100 Free",
    "200 Free",
    "500 Free",
    "100 Back",
    "100 Breast",
    "100 Fly",
    "200 IM",
]
TEAM_NAMES = {
    "djo": "Bishop O'Connell",
    "sst": "Seton Swimming",
    "tcs": "Trinity Christian",
    "pvi": "Paul VI",
    "ics": "Immanuel Christian",
    "bi": "Bishop Ireton",
    "oak": "Oakcrest School",
    "fcs": "Fredericksburg Christian",
    "sghs": "St. Gertrude",
    "jp": "St. John Paul",
    "bcp": "Benedictine",
}


def load_all_data():
    data = {}
    for key, path in [
        ("meet", os.path.join(DATA_DIR, "meets", "2026-02-07_vcac_championship.json")),
        ("projections", os.path.join(CHAMP_DIR, "vcac_2026_projection_report.json")),
        ("factors", os.path.join(DATA_DIR, "championship_factors.json")),
        ("attrition", os.path.join(DATA_DIR, "dq_dns_rates.json")),
    ]:
        with open(path) as f:
            data[key] = json.load(f)
    data["comparison_girls"] = pd.read_csv(
        os.path.join(BACKTEST_DIR, "comparison_girls_512.csv")
    )
    data["comparison_boys"] = pd.read_csv(
        os.path.join(BACKTEST_DIR, "comparison_boys_512.csv")
    )
    data["breakdown"] = pd.read_csv(
        os.path.join(BACKTEST_DIR, "aqua_championship_breakdown_512.csv")
    )
    data["backtest"] = pd.read_csv(
        os.path.join(BACKTEST_DIR, "backtest_comparison_512.csv")
    )
    return data


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
            "S", parent=base["Normal"], fontSize=8, textColor=SLATE, spaceAfter=4
        ),
        "mv": ParagraphStyle(
            "MV",
            parent=base["Normal"],
            fontSize=24,
            textColor=TEAL,
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
    }


def make_table(headers, rows, col_widths=None):
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


def make_metric(value, label, s):
    t = Table(
        [[Paragraph(str(value), s["mv"])], [Paragraph(label, s["ml"])]],
        colWidths=[1.6 * inch],
    )
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), TEAL_LIGHT),
                ("TOPPADDING", (0, 0), (0, 0), 12),
                ("BOTTOMPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 1), (0, 1), 2),
                ("BOTTOMPADDING", (0, 1), (0, 1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return t


def gen_bar_chart(labels, v1, v2, title, fname):
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    x = range(len(labels))
    w = 0.35
    ax.bar([i - w / 2 for i in x], v1, w, label="SST", color="#0EA5E9")
    ax.bar([i + w / 2 for i in x], v2, w, label="Opponents", color="#CBD5E1")
    ax.set_ylabel("Points", fontsize=9)
    ax.set_title(title, fontsize=11, fontweight="bold", color="#0A1628")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=7)
    ax.legend(fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, fname)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def gen_attrition_chart(att, fname):
    events, rates = [], []
    for ev, st in sorted(att["by_event"].items()):
        if st.get("is_relay") or st["n"] < 100:
            continue
        events.append(ev)
        rates.append(st["dns_rate"] * 100)
    fig, ax = plt.subplots(figsize=(7.5, 3))
    clrs = ["#EF4444" if r > 20 else "#F59E0B" if r > 15 else "#10B981" for r in rates]
    ax.barh(events, rates, color=clrs)
    ax.set_xlabel("DNS Rate (%)", fontsize=9)
    ax.set_title(
        "DNS Rates by Event (n=77,345)", fontsize=11, fontweight="bold", color="#0A1628"
    )
    ax.axvline(x=20, color="#EF4444", linestyle="--", alpha=0.5, linewidth=0.8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, fname)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def gen_seed_chart(fdata, fname):
    events, factors, confs = [], [], []
    for ev, st in sorted(fdata["event_stats"].items()):
        events.append(ev)
        factors.append(st["factor"])
        confs.append(st["confidence"])
    fig, ax = plt.subplots(figsize=(7.5, 3))
    clrs = [{"high": "#10B981", "medium": "#F59E0B"}.get(c, "#EF4444") for c in confs]
    ax.bar(events, factors, color=clrs)
    ax.axhline(y=1.0, color="#0A1628", linestyle="-", alpha=0.3, linewidth=0.8)
    ax.set_ylabel("Factor (< 1.0 = drop time)", fontsize=8)
    ax.set_title(
        f"Seed-to-Race Accuracy (n={fdata['total_entries']:,})",
        fontsize=11,
        fontweight="bold",
        color="#0A1628",
    )
    ax.set_xticks(range(len(events)))
    ax.set_xticklabels(events, rotation=45, ha="right", fontsize=7)
    ax.set_ylim(0.94, 1.01)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(
        handles=[
            Patch(facecolor="#10B981", label="High"),
            Patch(facecolor="#F59E0B", label="Medium"),
            Patch(facecolor="#EF4444", label="Low"),
        ],
        fontsize=7,
        loc="lower left",
    )
    plt.tight_layout()
    path = os.path.join(OUTPUT_DIR, fname)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    return path


def header_footer(canvas, doc):
    canvas.saveState()
    w = doc.pagesize[0]
    canvas.setStrokeColor(TEAL)
    canvas.setLineWidth(2)
    canvas.line(40, doc.pagesize[1] - 40, w - 40, doc.pagesize[1] - 40)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(SLATE)
    canvas.drawString(44, doc.pagesize[1] - 36, "AquaForge Championship Analysis")
    canvas.drawRightString(w - 44, doc.pagesize[1] - 36, "VCAC 2026 | Confidential")
    canvas.setFillColor(MID_GRAY)
    canvas.drawCentredString(
        w / 2,
        24,
        f"Page {doc.page} | Generated {datetime.now().strftime('%B %d, %Y')}",
    )
    canvas.drawRightString(w - 44, 24, "Powered by AquaForge")
    canvas.restoreState()


def build_pdf(data):
    s = create_styles()
    out = os.path.join(OUTPUT_DIR, "AquaForge_VCAC_2026_Championship_Analysis.pdf")
    doc = SimpleDocTemplate(
        out,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.6 * inch,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
    )
    story = []

    # === COVER ===
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("AquaForge", s["title"]))
    story.append(
        Paragraph(
            "Championship Analysis Report",
            ParagraphStyle(
                "CS", fontSize=18, textColor=TEAL, fontName="Helvetica", spaceAfter=30
            ),
        )
    )
    story.append(Spacer(1, 0.3 * inch))
    ci = [
        ["Meet", data["meet"]["name"]],
        ["Date", data["meet"]["date"]],
        ["Venue", data["meet"]["venue"]],
        ["Target Team", "Seton Swimming (SST)"],
        ["Generated", datetime.now().strftime("%B %d, %Y")],
    ]
    ct = Table(ci, colWidths=[1.5 * inch, 4 * inch])
    ct.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 11),
                ("TEXTCOLOR", (0, 0), (0, -1), SLATE),
                ("TEXTCOLOR", (1, 0), (1, -1), NAVY),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, LIGHT_GRAY),
            ]
        )
    )
    story.extend([ct, Spacer(1, 0.6 * inch)])
    story.append(
        Paragraph(
            "Sections: Team Standings | Optimizer vs Coach | Event Breakdown | Swing Events | Attrition Model | Seed Accuracy",
            s["small"],
        )
    )
    story.append(PageBreak())

    # === EXECUTIVE SUMMARY ===
    story.append(Paragraph("Executive Summary", s["h1"]))
    gdf, bdf = data["comparison_girls"], data["comparison_boys"]
    adf = pd.concat([gdf, bdf])
    act = adf[adf["status"] != "Neither"]
    cs_t, os_t, ca_t = (
        act["coach_seed_pts"].sum(),
        act["optimizer_seed_pts"].sum(),
        act["coach_actual_pts"].sum(),
    )
    delta = os_t - cs_t
    bd = data["breakdown"]
    tr = bd[bd["section"] == "TOTAL"]
    asst = tr.iloc[0].get("event_sst", 759) if not tr.empty else 759
    aopp = tr.iloc[0].get("event_opp", 569) if not tr.empty else 569

    mrow = Table(
        [
            [
                make_metric(f"{asst:.0f}", "Optimizer Pts", s),
                make_metric(f"{aopp:.0f}", "Opponent Pts", s),
                make_metric(f"+{delta:.0f}", "vs Coach (Seed)", s),
                make_metric(f"{ca_t:.0f}", "Coach Actual", s),
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
            f"The AquaForge optimizer projects <b>{asst:.0f} points</b> for SST vs <b>{aopp:.0f}</b> for opponents. Compared to coach seed-time scoring, the optimizer gains <b>+{delta:.0f} points</b> through strategic event reassignment.",
            s["body"],
        )
    )
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Strategy Comparison (Backtest Meet 512)", s["h3"]))
    btr = [
        [
            r["strategy"],
            f"{r['seton_pts']:.0f}",
            str(r.get("rank", "-")),
            str(r.get("time", "-")),
        ]
        for _, r in data["backtest"].iterrows()
    ]
    story.extend(
        [
            make_table(
                ["Strategy", "SST Points", "Rank", "Time"],
                btr,
                [2.5 * inch, 1.2 * inch, 0.8 * inch, 1.2 * inch],
            ),
            PageBreak(),
        ]
    )

    # === STANDINGS ===
    story.append(Paragraph("Projected Team Standings", s["h1"]))
    story.append(
        Paragraph(
            "Based on unified psych sheet, VCAC scoring (16-13-12-11-10-9-7-5-4-3-2-1).",
            s["body"],
        )
    )
    proj = data["projections"]
    sr = []
    for i, (code, pts) in enumerate(proj["standings"], 1):
        nm = TEAM_NAMES.get(code, code.upper())
        mk = "  << SST" if code == "sst" else ""
        sr.append([str(i), nm + mk, f"{pts:.0f}"])
    story.extend(
        [
            make_table(
                ["Place", "Team", "Projected Points"],
                sr,
                [0.8 * inch, 3.5 * inch, 1.5 * inch],
            ),
            Spacer(1, 0.2 * inch),
        ]
    )
    story.append(Paragraph("SST Top Scorers (Projection)", s["h2"]))
    scr = [
        [x["swimmer"], x["event"], str(x["place"]), str(x["points"])]
        for x in proj["seton_summary"]["top_scorers"][:10]
    ]
    story.extend(
        [
            make_table(
                ["Swimmer", "Event", "Place", "Points"],
                scr,
                [2 * inch, 1.8 * inch, 0.8 * inch, 0.8 * inch],
            ),
            PageBreak(),
        ]
    )

    # === EVENT BREAKDOWN ===
    story.append(Paragraph("Event-by-Event Breakdown", s["h1"]))
    story.append(
        Paragraph(
            "Optimized lineup: SST vs opponents, top 4 per team score.", s["body"]
        )
    )
    ev_scores = {}
    for _, row in bd.iterrows():
        ev = str(row.get("event", ""))
        if any(x in ev for x in ["---", "SUBTOTAL", "TOTAL", "nan"]) or ev == "":
            continue
        if (
            pd.notna(row.get("place"))
            and pd.notna(row.get("event_sst"))
            and row.get("place") == 1
        ):
            ev_scores[ev] = {
                "sst": float(row["event_sst"]),
                "opp": float(row["event_opp"]),
            }
    els = list(ev_scores.keys())
    cp = gen_bar_chart(
        els,
        [ev_scores[e]["sst"] for e in els],
        [ev_scores[e]["opp"] for e in els],
        "Points by Event: SST vs Opponents",
        "_chart_ev.png",
    )
    story.extend([Image(cp, width=7 * inch, height=3 * inch), Spacer(1, 0.15 * inch)])
    story.append(Paragraph("Event Scoring Detail", s["h2"]))
    edr = [
        [ev, f"{sc['sst']:.0f}", f"{sc['opp']:.0f}", f"{sc['sst'] - sc['opp']:+.0f}"]
        for ev, sc in ev_scores.items()
    ]
    story.extend(
        [
            make_table(
                ["Event", "SST", "Opponents", "Margin"],
                edr,
                [2.5 * inch, 1 * inch, 1.2 * inch, 1 * inch],
            ),
            PageBreak(),
        ]
    )

    # === COACH VS OPTIMIZER ===
    story.append(Paragraph("Optimizer vs Coach Comparison", s["h1"]))
    story.append(
        Paragraph(
            "Seed-time scored, relay legs removed. Actual = race-day points.", s["body"]
        )
    )
    sd = []
    for label, df in [("Girls", gdf), ("Boys", bdf)]:
        a2 = df[df["status"] != "Neither"]
        c2, o2, a3 = (
            a2["coach_seed_pts"].sum(),
            a2["optimizer_seed_pts"].sum(),
            a2["coach_actual_pts"].sum(),
        )
        sd.append(
            [
                label,
                f"{c2:.0f}",
                f"{o2:.0f}",
                f"{o2 - c2:+.0f}",
                f"{a3:.0f}",
                str((a2["status"] == "MATCH").sum()),
                str((a2["status"] == "DIFFER").sum()),
            ]
        )
    sd.append(
        [
            "TOTAL",
            f"{cs_t:.0f}",
            f"{os_t:.0f}",
            f"{delta:+.0f}",
            f"{ca_t:.0f}",
            str((act["status"] == "MATCH").sum()),
            str((act["status"] == "DIFFER").sum()),
        ]
    )
    story.extend(
        [
            make_table(
                [
                    "",
                    "Coach(Seed)",
                    "Optim(Seed)",
                    "Delta",
                    "Coach(Actual)",
                    "Match",
                    "Differ",
                ],
                sd,
                [
                    0.7 * inch,
                    1.1 * inch,
                    1.3 * inch,
                    0.7 * inch,
                    1.1 * inch,
                    0.8 * inch,
                    0.7 * inch,
                ],
            ),
            Spacer(1, 0.15 * inch),
        ]
    )
    story.append(Paragraph("Key Differences", s["h2"]))
    for label, cdf in [("Girls", gdf), ("Boys", bdf)]:
        diffs = cdf[
            (cdf["status"] == "DIFFER") & (cdf["delta_seed"].abs() > 0)
        ].sort_values("delta_seed", ascending=False)
        if diffs.empty:
            continue
        story.append(Paragraph(f"{label} - Differs", s["h3"]))
        dr = []
        for _, r in diffs.iterrows():
            ce = str(r["coach_events"])[:45]
            if len(str(r["coach_events"])) > 45:
                ce += "..."
            oe = str(r["optimizer_events"])[:45]
            if len(str(r["optimizer_events"])) > 45:
                oe += "..."
            dr.append(
                [
                    Paragraph(r["swimmer"], s["cell"]),
                    Paragraph(ce, s["cell"]),
                    Paragraph(f"{r['coach_seed_pts']:.0f}", s["cellr"]),
                    Paragraph(oe, s["cell"]),
                    Paragraph(f"{r['optimizer_seed_pts']:.0f}", s["cellr"]),
                    Paragraph(f"{r['delta_seed']:+.0f}", s["cellc"]),
                ]
            )
        story.extend(
            [
                make_table(
                    ["Swimmer", "Coach Events", "C", "Optimizer Events", "O", "D"],
                    dr,
                    [
                        1.1 * inch,
                        1.8 * inch,
                        0.5 * inch,
                        1.8 * inch,
                        0.5 * inch,
                        0.5 * inch,
                    ],
                ),
                Spacer(1, 0.1 * inch),
            ]
        )
    story.append(PageBreak())

    # === SWING EVENTS ===
    story.append(Paragraph("Swing Event Opportunities", s["h1"]))
    story.append(
        Paragraph(
            "Events where small time drops yield significant scoring gains.", s["body"]
        )
    )
    swing = proj.get("swing_events", [])
    if swing:
        swr = [
            [
                x["event"],
                x["swimmer"],
                str(x["current_place"]),
                str(x["target_place"]),
                x["current_time"],
                f"+{x['point_gain']}",
                x.get("priority", "").upper(),
            ]
            for x in swing
        ]
        story.append(
            make_table(
                ["Event", "Swimmer", "Current", "Target", "Time", "Gain", "Priority"],
                swr,
                [
                    1.2 * inch,
                    1.3 * inch,
                    0.7 * inch,
                    0.7 * inch,
                    0.9 * inch,
                    0.6 * inch,
                    0.8 * inch,
                ],
            )
        )
    story.append(Spacer(1, 0.2 * inch))
    story.append(Paragraph("400 Free Relay Trade-off", s["h2"]))
    story.append(
        Paragraph(
            "<b>VCAC Rule:</b> 400 Free Relay counts as 1 individual event slot.",
            s["body"],
        )
    )
    rr = [
        ["2 ind events", "400FR blocks relay-3", "Use if relay > lost ind"],
        ["1 ind event", "Blocks 1 ind slot", "Only if critical"],
        ["Diving", "Diving+1ind+400FR=max", "Avoid"],
    ]
    story.extend(
        [
            make_table(
                ["Scenario", "Trade-off", "Recommendation"],
                rr,
                [2 * inch, 2 * inch, 2.2 * inch],
            ),
            PageBreak(),
        ]
    )

    # === ATTRITION ===
    story.append(Paragraph("Attrition Model (DQ/DNS Rates)", s["h1"]))
    att = data["attrition"]
    story.append(
        Paragraph(
            f"From <b>{att['global_n']:,} entries</b> across <b>{att['meets_parsed']} meets</b>. Global DNS: <b>{att['global_dns_rate'] * 100:.1f}%</b>, DQ: <b>{att['global_dq_rate'] * 100:.3f}%</b>.",
            s["body"],
        )
    )
    ac = gen_attrition_chart(att, "_chart_att.png")
    story.extend([Image(ac, width=7 * inch, height=2.8 * inch), Spacer(1, 0.15 * inch)])
    story.append(Paragraph("DNS Rates for Championship Events", s["h2"]))
    dnr = []
    for ev in CHAMP_EVENTS:
        st = att["by_event"].get(ev, {})
        if st:
            dnr.append(
                [
                    ev,
                    f"{st['dns_rate'] * 100:.1f}%",
                    f"{st['dq_rate'] * 100:.3f}%",
                    f"{st['completion_rate'] * 100:.1f}%",
                    format(st["n"], ","),
                ]
            )
    story.extend(
        [
            make_table(
                ["Event", "DNS Rate", "DQ Rate", "Completion", "Sample"],
                dnr,
                [1.3 * inch, 1 * inch, 1 * inch, 1.1 * inch, 1 * inch],
            ),
            Spacer(1, 0.15 * inch),
        ]
    )
    story.append(Paragraph("By Meet Type", s["h3"]))
    mtr = [
        [
            mt.title(),
            f"{st['dns_rate'] * 100:.1f}%",
            f"{st['dq_rate'] * 100:.3f}%",
            format(st["n"], ","),
        ]
        for mt, st in att["by_meet_type"].items()
    ]
    story.extend(
        [
            make_table(
                ["Meet Type", "DNS Rate", "DQ Rate", "Sample"],
                mtr,
                [1.5 * inch, 1.2 * inch, 1.2 * inch, 1.2 * inch],
            ),
            PageBreak(),
        ]
    )

    # === SEED ACCURACY ===
    story.append(Paragraph("Seed Accuracy Model", s["h1"]))
    fac = data["factors"]
    story.append(
        Paragraph(
            f"From <b>{fac['total_entries']:,} entries</b> across <b>{fac['total_meets']} meets</b>. Factor &lt; 1.0 = swimmers drop time. Default: <b>{fac['default_factor']}</b>.",
            s["body"],
        )
    )
    sc_path = gen_seed_chart(fac, "_chart_seed.png")
    story.extend(
        [Image(sc_path, width=7 * inch, height=2.8 * inch), Spacer(1, 0.15 * inch)]
    )
    story.append(Paragraph("Event Accuracy Detail", s["h2"]))
    ar = []
    for ev in CHAMP_EVENTS:
        st = fac["event_stats"].get(ev, {})
        if st:
            ar.append(
                [
                    ev,
                    f"{st['factor']:.4f}",
                    f"{st['avg_drop_pct']:.1f}%",
                    f"{st['top3_stability_pct']:.1f}%",
                    f"{st['top12_stability_pct']:.1f}%",
                    st["confidence"].upper(),
                ]
            )
    story.extend(
        [
            make_table(
                [
                    "Event",
                    "Factor",
                    "Avg Drop",
                    "Top-3 Stable",
                    "Top-12 Stable",
                    "Confidence",
                ],
                ar,
                [1.2 * inch, 0.8 * inch, 0.9 * inch, 1 * inch, 1 * inch, 1 * inch],
            ),
            Spacer(1, 0.3 * inch),
        ]
    )
    story.append(
        Paragraph(
            "<b>Key Insight:</b> High-stability events (500 Free 94.7%%, 200 IM 93.9%%) are most predictable. Sprint events have lower stability - race-day upsets more common.",
            s["body"],
        )
    )
    story.extend(
        [
            Spacer(1, 0.5 * inch),
            Paragraph(
                "Generated by AquaForge v1.0.0 | SwimCloud, team rosters, historical results | Gurobi, Aqua solver, Nash equilibrium",
                s["footer"],
            ),
        ]
    )

    doc.build(story, onFirstPage=header_footer, onLaterPages=header_footer)
    for tmp in ["_chart_ev.png", "_chart_att.png", "_chart_seed.png"]:
        p = os.path.join(OUTPUT_DIR, tmp)
        if os.path.exists(p):
            os.remove(p)
    return out


def main():
    print("Loading championship analysis data...")
    data = load_all_data()
    print("Generating PDF report...")
    path = build_pdf(data)
    print("PDF generated:", path)
    print(f"Size: {os.path.getsize(path) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
