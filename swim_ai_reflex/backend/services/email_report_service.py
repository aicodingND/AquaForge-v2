"""
Automated Email Report Generator

Sends professional HTML email reports with optimization results.
"""

import logging
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


class EmailReportService:
    """Automated email report generation and delivery"""

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int = 587,
        username: str | None = None,
        password: str | None = None,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.enabled = bool(self.username and self.password)

        if self.enabled:
            logger.info("Email service configured")
        else:
            logger.warning("Email service not configured (missing credentials)")

    def send_optimization_report(
        self,
        to_email: str,
        lineup: list[dict],
        seton_score: float,
        opponent_score: float,
        meet_name: str = "Swim Meet",
        attachments: list[str] | None = None,
    ) -> bool:
        """Send optimization results via email."""
        if not self.enabled:
            logger.warning("Email service not enabled")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.username
            msg["To"] = to_email
            msg["Subject"] = f"AquaForge Lineup Report - {meet_name}"

            html_content = self._generate_html_report(
                lineup, seton_score, opponent_score, meet_name
            )

            html_part = MIMEText(html_content, "html")
            msg.attach(html_part)

            if attachments:
                for file_path in attachments:
                    self._attach_file(msg, file_path)

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email report sent to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _generate_html_report(
        self,
        lineup: list[dict],
        seton_score: float,
        opponent_score: float,
        meet_name: str,
    ) -> str:
        """Generate professional HTML email report"""

        lineup_rows = ""
        for assignment in lineup:
            lineup_rows += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">{assignment.get("event", "")}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd;">{assignment.get("swimmer", "")}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: center;">{assignment.get("time", 0):.2f}</td>
                <td style="padding: 12px; border-bottom: 1px solid #ddd; text-align: center; font-weight: bold;">{assignment.get("points", 0)}</td>
            </tr>
            """

        margin = seton_score - opponent_score
        margin_color = "#4CAF50" if margin > 0 else "#F44336"

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f5f5f5;">
            <div style="background: linear-gradient(135deg, #0A1428 0%, #1e3a5f 100%); padding: 30px; border-radius: 10px; color: white; margin-bottom: 20px;">
                <h1 style="margin: 0; font-size: 32px;">AquaForge</h1>
                <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">Lineup Optimization Report</p>
            </div>

            <div style="background: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <h2 style="color: #0A1428; margin-top: 0;">{meet_name}</h2>
                <p style="color: #666; margin-bottom: 20px;">Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}</p>

                <div style="display: flex; gap: 20px; margin-bottom: 30px;">
                    <div style="flex: 1; text-align: center; padding: 20px; background: #e8f5e9; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Seton Score</div>
                        <div style="font-size: 36px; font-weight: bold; color: #2e7d32;">{seton_score}</div>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 20px; background: #ffebee; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Opponent Score</div>
                        <div style="font-size: 36px; font-weight: bold; color: #c62828;">{opponent_score}</div>
                    </div>
                    <div style="flex: 1; text-align: center; padding: 20px; background: #f3e5f5; border-radius: 8px;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 5px;">Margin</div>
                        <div style="font-size: 36px; font-weight: bold; color: {margin_color};">{margin:+.0f}</div>
                    </div>
                </div>

                <h3 style="color: #0A1428; margin-bottom: 15px;">Optimized Lineup</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                    <thead>
                        <tr style="background: #0A1428; color: white;">
                            <th style="padding: 12px; text-align: left;">Event</th>
                            <th style="padding: 12px; text-align: left;">Swimmer</th>
                            <th style="padding: 12px; text-align: center;">Time</th>
                            <th style="padding: 12px; text-align: center;">Points</th>
                        </tr>
                    </thead>
                    <tbody>
                        {lineup_rows}
                    </tbody>
                </table>
            </div>

            <div style="background: white; padding: 20px; border-radius: 10px; text-align: center; color: #666; font-size: 14px;">
                <p style="margin: 0;">Powered by <strong>AquaForge.ai</strong></p>
                <p style="margin: 5px 0 0 0;">AI-Powered Swim Meet Optimization</p>
            </div>
        </body>
        </html>
        """

        return html

    def _attach_file(self, msg: MIMEMultipart, file_path: str):
        """Attach file to email"""
        try:
            with open(file_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())

            encoders.encode_base64(part)
            filename = os.path.basename(file_path)
            part.add_header("Content-Disposition", f"attachment; filename= {filename}")
            msg.attach(part)
        except Exception as e:
            logger.error(f"Failed to attach file {file_path}: {e}")
