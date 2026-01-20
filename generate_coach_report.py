#!/usr/bin/env python3
"""
VCAC Championship Coach Report Generator

Produces a printable, coach-friendly strategy report for the
VCAC Championship meet, including projections, swing events,
and relay trade-off analysis.

Usage:
    python3 generate_coach_report.py

Output:
    reports/VCAC_2026_Coach_Report.md
    reports/VCAC_2026_Coach_Report.html
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import sys

sys.path.insert(0, str(Path(__file__).parent))


def load_projection_data() -> Dict[str, Any]:
    """Load the projection results."""
    project_root = Path(__file__).parent
    standings_path = (
        project_root / "data" / "vcac" / "VCAC_2026_standings_projection.json"
    )

    if not standings_path.exists():
        print("ERROR: Run run_vcac_projection.py first!")
        return {}

    with open(standings_path, "r") as f:
        return json.load(f)


def format_time(seconds: float) -> str:
    """Format time as MM:SS.ss or SS.ss."""
    if seconds >= 60:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"
    return f"{seconds:.2f}"


def generate_markdown_report(data: Dict[str, Any]) -> str:
    """Generate the markdown report content."""
    standings = data.get("standings", [])
    swing_events = data.get("swing_events", [])

    # Find Seton's position and details
    seton = next((t for t in standings if t["team_code"] == "SST"), None)
    seton_pos = next(
        (i for i, t in enumerate(standings, 1) if t["team_code"] == "SST"), None
    )

    # Header
    report = f"""# 🏊 VCAC Championship 2026 - Strategy Report
## Prepared for Coach Koehr
**Generated:** {datetime.now().strftime("%B %d, %Y at %I:%M %p")}

---

## 📊 Projected Team Standings

| Place | Team | Projected Points |
|-------|------|-----------------|
"""

    # Add standings
    for i, team in enumerate(standings, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else ""
        seton_mark = " ← SETON" if team["team_code"] == "SST" else ""
        report += f"| {i}. {medal} | **{team['team_name']}** | {team['total_points']:.0f} pts{seton_mark} |\n"

    # Seton Summary
    if seton:
        report += f"""

---

## 🔵 Seton Swimming Analysis

**Projected Finish:** {seton_pos}{"st" if seton_pos == 1 else "nd" if seton_pos == 2 else "rd" if seton_pos == 3 else "th"} Place
**Projected Points:** {seton["total_points"]:.0f}

### Top Scorers
"""
        for i, scorer in enumerate(seton.get("top_scorers", [])[:5], 1):
            report += f"{i}. **{scorer['name']}** - {scorer['points']:.0f} points\n"

        # Strengths
        if seton.get("strengths"):
            report += "\n### 💪 Strength Events\n"
            for event in seton["strengths"]:
                pts = seton.get("event_breakdown", {}).get(event, 0)
                report += f"- {event}: {pts:.0f} pts\n"

        # Weaknesses
        if seton.get("weaknesses"):
            report += "\n### ⚠️ Events Needing Focus\n"
            for event in seton["weaknesses"]:
                pts = seton.get("event_breakdown", {}).get(event, 0)
                report += f"- {event}: {pts:.0f} pts\n"

    # Swing Events
    if swing_events:
        report += """

---

## 🎯 Swing Event Opportunities

*Events where small time drops could significantly improve scoring*

"""
        for i, se in enumerate(swing_events[:10], 1):
            report += f"""### {i}. {se["event"]}

| Swimmer | Current | Target | Gap | Potential Gain |
|---------|---------|--------|-----|----------------|
| **{se["seton_swimmer"]}** | {se["seton_place"]}th ({format_time(se["seton_time"])}) | {se["target_place"]}th | {se["time_gap"]:.2f}s | **+{se["potential_points_gain"]} pts** |

*Beat {se["target_swimmer"]} ({se["target_team"]}) at {format_time(se["target_time"])}*

"""

    # Relay Trade-off Section
    report += """
---

## 🏃 400 Free Relay Trade-off Analysis

**VCAC Rule Reminder:** 
- First 2 relays (200 Medley, 200 Free) = FREE
- 3rd relay (400 Free) counts as 1 individual event slot

### Decision Framework

| Scenario | Trade-off | Recommendation |
|----------|-----------|----------------|
| Swimmer with 2 individual events | 400 FR blocks them from relay-3 | ✅ Use if relay placement > lost individual |
| Swimmer with 1 individual event | 400 FR blocks 1 individual slot | ⚠️ Only if relay placement is critical |
| Swimmer with diving | Diving + 1 individual + 400 FR = maxed | ❌ Avoid unless no alternatives |

### Key Questions for Each Swimmer:
1. How many individual events are they swimming?
2. Are they on the 400 Free Relay?
3. If diving, are they aware of the individual count impact?

---

## 📋 Pre-Meet Checklist

- [ ] Confirm all swimmer grades (7th graders = non-scoring)
- [ ] Verify diver individual event counts
- [ ] Review 400 FR roster against individual assignments
- [ ] Check for back-to-back conflicts
- [ ] Print psych sheet for coach reference
"""

    # Calculate days remaining
    vcac_date = datetime(2026, 2, 7)
    days_remaining = (vcac_date - datetime.now()).days

    report += f"""
---

## 📞 Notes

*This report is based on seed times from SwimCloud and coach-provided data.*
*Actual results may vary based on race-day performance.*

**Days until VCAC Championship:** {days_remaining} days

---

*Generated by AquaForge Championship Module*
"""

    return report


def generate_html_report(markdown_content: str) -> str:
    """Convert markdown to styled HTML."""
    try:
        import markdown

        html_body = markdown.markdown(markdown_content, extensions=["tables", "extra"])
    except ImportError:
        # Fallback: basic conversion
        html_body = f"<pre>{markdown_content}</pre>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VCAC Championship 2026 - Coach Report</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
            color: #1a1a1a;
            background: #f8f9fa;
        }}
        
        h1 {{
            color: #1a365d;
            border-bottom: 3px solid #2b6cb0;
            padding-bottom: 0.5rem;
        }}
        
        h2 {{
            color: #2b6cb0;
            margin-top: 2rem;
        }}
        
        h3 {{
            color: #4a5568;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            background: white;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border: 1px solid #e2e8f0;
        }}
        
        th {{
            background: #2b6cb0;
            color: white;
            font-weight: 600;
        }}
        
        tr:nth-child(even) {{
            background: #f7fafc;
        }}
        
        tr:hover {{
            background: #edf2f7;
        }}
        
        strong {{
            color: #2b6cb0;
        }}
        
        hr {{
            border: none;
            border-top: 2px solid #e2e8f0;
            margin: 2rem 0;
        }}
        
        blockquote {{
            background: #ebf8ff;
            border-left: 4px solid #2b6cb0;
            padding: 1rem;
            margin: 1rem 0;
        }}
        
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        
        li {{
            padding: 0.25rem 0;
        }}
        
        li:before {{
            content: "▸ ";
            color: #2b6cb0;
        }}
        
        @media print {{
            body {{
                background: white;
                color: black;
            }}
            
            h1, h2, strong {{
                color: #1a365d;
            }}
            
            table {{
                box-shadow: none;
            }}
        }}
    </style>
</head>
<body>
{html_body}
</body>
</html>
"""
    return html


def main():
    """Generate the coach report."""
    print("=" * 60)
    print("🏊 VCAC Coach Report Generator")
    print("=" * 60)

    # Load projection data
    print("\n[1] Loading projection data...")
    data = load_projection_data()

    if not data:
        print("No projection data available. Run run_vcac_projection.py first.")
        return

    print(f"  Loaded standings for {len(data.get('standings', []))} teams")
    print(f"  Found {len(data.get('swing_events', []))} swing events")

    # Generate reports
    print("\n[2] Generating markdown report...")
    markdown_content = generate_markdown_report(data)

    # Create reports directory
    reports_dir = Path(__file__).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # Save markdown
    md_path = reports_dir / "VCAC_2026_Coach_Report.md"
    with open(md_path, "w") as f:
        f.write(markdown_content)
    print(f"  ✅ Saved: {md_path}")

    # Generate HTML
    print("\n[3] Generating HTML report...")
    html_content = generate_html_report(markdown_content)

    html_path = reports_dir / "VCAC_2026_Coach_Report.html"
    with open(html_path, "w") as f:
        f.write(html_content)
    print(f"  ✅ Saved: {html_path}")

    print("\n" + "=" * 60)
    print("✅ Coach Report Generated!")
    print("=" * 60)
    print(f"\n📄 Markdown: {md_path}")
    print(f"🌐 HTML:     {html_path}")
    print("\nOpen the HTML file in a browser to view or print.")


if __name__ == "__main__":
    main()
