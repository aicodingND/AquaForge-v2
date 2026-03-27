import logging
import os
import shutil
from typing import Any

logger = logging.getLogger(__name__)


class PremiumReporter:
    """
    The 'AquaForge Elite' Reporting Engine.
    Generates high-fidelity HTML dashboards for championship meets.
    """

    def __init__(self, templates_dir: str = "reports/templates"):
        self.templates_dir = templates_dir
        self.base_output_dir = "reports"

    def generate_dashboard(self, context: dict[str, Any]):
        """
        Generate the executive dashboard for a specific meet.

        Args:
            context: Dictionary containing:
                - meet_name: str
                - profile: str
                - ai_score: float
                - legal_coach_score: float
                - rank_accuracy: float
                - illegal_points_removed: float
                - violations: List[str]
                - top_teams: List[Dict] {name, ai_points, coach_points, actual_points}
        """
        meet_name = context.get("meet_name", "Unknown Meet")
        safe_name = "".join(
            c for c in meet_name if c.isalnum() or c in (" ", "_")
        ).replace(" ", "_")
        output_dir = os.path.join(self.base_output_dir, safe_name)

        # 1. Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # 2. Copy CSS
        css_src = os.path.join(self.templates_dir, "styles.css")
        css_dst = os.path.join(output_dir, "styles.css")
        if os.path.exists(css_src):
            shutil.copy(css_src, css_dst)

        # 3. Render Template
        # We use a mini-renderer to avoid hard Jinja2 dependency if not present,
        # but ideally we'd use Jinja2. Here we'll do a robust custom render
        # to ensure it works out of the box.

        template_path = os.path.join(self.templates_dir, "dashboard.html")
        if not os.path.exists(template_path):
            logger.warning(f"Template not found at {template_path}")
            return

        with open(template_path) as f:
            template_content = f.read()

        rendered_html = self._render(template_content, context)

        output_path = os.path.join(output_dir, "index.html")
        with open(output_path, "w") as f:
            f.write(rendered_html)

        logger.info(f"Dashboard generated at: {output_path}")
        return output_path

    def _render(self, template: str, context: dict[str, Any]) -> str:
        """
        A lightweight template renderer that handles basic Jinja2-like syntax.
        Supports: {{ var }}, {% if var %}, {% for item in list %}
        """
        # 1. Handle Variables {{ var }}
        # We'll do this last actually, to process inside loops?
        # No, simple approach: linear processing.

        # Actually, implementing a full parser is complex.
        # Let's try to import Jinja2.
        try:
            from jinja2 import Template

            t = Template(template)
            return t.render(**context)
        except ImportError:
            logger.warning(
                "Jinja2 not found. Falling back to simple replacement (loops may fail)."
            )
            # Simple fallback for creating the file even if imperfect
            output = template
            for k, v in context.items():
                if isinstance(v, (str, int, float)):
                    output = output.replace(f"{{{{ {k} }}}}", str(v))
            return output

    def generate_roster(self, context: dict[str, Any]):
        """Generate the printable roster view."""
        meet_name = context.get("meet_name", "Unknown Meet")
        safe_name = "".join(
            c for c in meet_name if c.isalnum() or c in (" ", "_")
        ).replace(" ", "_")
        output_dir = os.path.join(self.base_output_dir, safe_name)

        # Ensure dir exists (should be created by dashboard, but safe to check)
        os.makedirs(output_dir, exist_ok=True)

        template_path = os.path.join(self.templates_dir, "roster.html")
        if not os.path.exists(template_path):
            logger.warning(f"Template not found at {template_path}")
            return

        with open(template_path) as f:
            template_content = f.read()

        rendered_html = self._render(template_content, context)

        output_path = os.path.join(output_dir, "roster.html")
        with open(output_path, "w") as f:
            f.write(rendered_html)

        logger.info(f"▸ Roster generated at: {output_path}")
        return output_path

    def generate_pdf(self, context: dict[str, Any]) -> str:
        """
        Generate PDF export from dashboard HTML.

        Uses weasyprint if available, otherwise falls back to pdfkit.
        Returns the path to the generated PDF.
        """
        # First generate the HTML dashboard
        html_path = self.generate_dashboard(context)
        if not html_path:
            return None

        meet_name = context.get("meet_name", "Unknown Meet")
        safe_name = "".join(
            c for c in meet_name if c.isalnum() or c in (" ", "_")
        ).replace(" ", "_")
        output_dir = os.path.join(self.base_output_dir, safe_name)
        pdf_path = os.path.join(output_dir, "report.pdf")

        # Try weasyprint first (better quality)
        try:
            from weasyprint import HTML

            HTML(filename=html_path).write_pdf(pdf_path)
            logger.info(f"PDF generated at: {pdf_path}")
            return pdf_path
        except ImportError:
            pass

        # Try pdfkit (wkhtmltopdf wrapper)
        try:
            import pdfkit

            pdfkit.from_file(html_path, pdf_path)
            logger.info(f"PDF generated at: {pdf_path}")
            return pdf_path
        except ImportError:
            pass

        # Fallback: save HTML with print-friendly CSS
        logger.warning("! No PDF library available. Install weasyprint or pdfkit.")
        logger.warning(f"HTML report available at: {html_path}")
        return html_path

    def export_all_formats(self, context: dict[str, Any]) -> dict[str, str]:
        """
        Generate all report formats: HTML, PDF, and roster.

        Returns dict of format -> file path.
        """
        results = {}

        # HTML Dashboard
        html_path = self.generate_dashboard(context)
        if html_path:
            results["html"] = html_path

        # PDF
        pdf_path = self.generate_pdf(context)
        if pdf_path and pdf_path != html_path:
            results["pdf"] = pdf_path

        # Roster
        if context.get("roster"):
            roster_path = self.generate_roster(context)
            if roster_path:
                results["roster"] = roster_path

        return results
