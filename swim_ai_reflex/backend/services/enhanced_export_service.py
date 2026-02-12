"""
Enhanced Export Service with Multiple Formats

Exports optimization results to PDF, Excel, CSV, and JSON with professional formatting.
"""

import csv
import io
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import optional libraries
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class EnhancedExportService:
    """Enhanced export service with multiple formats"""

    def export_to_pdf(
        self,
        lineup: list[dict],
        seton_score: float,
        opponent_score: float,
        metadata: dict | None = None,
    ) -> bytes:
        """Export lineup to PDF with professional formatting"""
        if not PDF_AVAILABLE:
            raise ImportError(
                "reportlab not available. Install with: pip install reportlab"
            )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()

        title = Paragraph(
            "<b>AquaForge Lineup Optimization Report</b>", styles["Title"]
        )
        elements.append(title)
        elements.append(Spacer(1, 12))

        date_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        meta_text = f"Generated: {date_str}"
        if metadata:
            meta_text += f"<br/>Meet: {metadata.get('meet_name', 'Unknown')}"
        elements.append(Paragraph(meta_text, styles["Normal"]))
        elements.append(Spacer(1, 12))

        score_text = (
            f"<b>Predicted Score: Seton {seton_score} - Opponent {opponent_score}</b>"
        )
        elements.append(Paragraph(score_text, styles["Heading2"]))
        elements.append(Spacer(1, 12))

        table_data = [["Event", "Swimmer", "Time", "Points", "Rank"]]
        for assignment in lineup:
            table_data.append(
                [
                    assignment.get("event", ""),
                    assignment.get("swimmer", ""),
                    f"{assignment.get('time', 0):.2f}",
                    str(assignment.get("points", 0)),
                    str(assignment.get("rank", "")),
                ]
            )

        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ]
            )
        )

        elements.append(table)

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

    def export_to_excel(
        self, lineup: list[dict], seton_score: float, opponent_score: float
    ) -> bytes:
        """Export lineup to Excel with multiple sheets"""
        if not PANDAS_AVAILABLE:
            raise ImportError(
                "pandas not available. Install with: pip install pandas openpyxl"
            )

        buffer = io.BytesIO()

        lineup_df = pd.DataFrame(lineup)

        summary_df = pd.DataFrame(
            [
                {"Metric": "Seton Score", "Value": seton_score},
                {"Metric": "Opponent Score", "Value": opponent_score},
                {"Metric": "Point Margin", "Value": seton_score - opponent_score},
                {"Metric": "Total Swims", "Value": len(lineup)},
            ]
        )

        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            lineup_df.to_excel(writer, sheet_name="Lineup", index=False)
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

        buffer.seek(0)
        return buffer.getvalue()

    def export_to_csv(self, lineup: list[dict]) -> str:
        """Export lineup to CSV string"""
        if not lineup:
            return ""

        output = io.StringIO()
        fieldnames = lineup[0].keys()
        writer = csv.DictWriter(output, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(lineup)

        return output.getvalue()

    def export_to_json(
        self,
        lineup: list[dict],
        seton_score: float,
        opponent_score: float,
        metadata: dict | None = None,
    ) -> str:
        """Export to JSON with full context"""
        export_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "generator": "AquaForge AI",
                **(metadata or {}),
            },
            "summary": {
                "seton_score": seton_score,
                "opponent_score": opponent_score,
                "point_margin": seton_score - opponent_score,
                "total_swims": len(lineup),
            },
            "lineup": lineup,
        }

        return json.dumps(export_data, indent=2)

    def export_to_text(
        self, lineup: list[dict], seton_score: float, opponent_score: float
    ) -> str:
        """Export to formatted plain text"""
        lines = []
        lines.append("=" * 80)
        lines.append("AQUAFORGE LINEUP OPTIMIZATION REPORT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
        lines.append("")
        lines.append(
            f"PREDICTED SCORE: Seton {seton_score} - Opponent {opponent_score}"
        )
        lines.append(f"MARGIN: {seton_score - opponent_score:+.1f} points")
        lines.append("")
        lines.append("-" * 80)
        lines.append(f"{'EVENT':<30} {'SWIMMER':<25} {'TIME':>10} {'PTS':>5}")
        lines.append("-" * 80)

        for assignment in lineup:
            lines.append(
                f"{assignment.get('event', ''):<30} "
                f"{assignment.get('swimmer', ''):<25} "
                f"{assignment.get('time', 0):>10.2f} "
                f"{assignment.get('points', 0):>5}"
            )

        lines.append("=" * 80)

        return "\n".join(lines)
