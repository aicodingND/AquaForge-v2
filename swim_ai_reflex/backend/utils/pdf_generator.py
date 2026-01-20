from fpdf import FPDF
import datetime

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Swim AI - Meet Optimization Report', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Generated on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 10, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_lineup_table(self, lineup_data, title):
        self.chapter_title(title)
        self.set_font('Arial', 'B', 10)
        
        # Table Header
        cols = [('Event', 40), ('Swimmer', 60), ('Time', 30), ('Points', 20)]
        for col, width in cols:
            self.cell(width, 7, col, 1)
        self.ln()
        
        # Table Body
        self.set_font('Arial', '', 10)
        for entry in lineup_data:
            self.cell(40, 7, str(entry.get('event', '')), 1)
            self.cell(60, 7, str(entry.get('swimmer', '')), 1)
            self.cell(30, 7, str(entry.get('time', '')), 1)
            self.cell(20, 7, str(entry.get('points', '')), 1)
            self.ln()
        self.ln()

def generate_pdf_report(seton_lineup, opponent_lineup, score_summary):
    pdf = PDFReport()
    pdf.add_page()
    
    # Summary Section
    pdf.chapter_title("Meet Summary")
    pdf.set_font('Arial', '', 12)
    
    seton_score = score_summary.get('seton', 0)
    opp_score = score_summary.get('opponent', 0)
    win_prob = score_summary.get('win_prob', 0) * 100
    
    pdf.cell(0, 10, f"Predicted Score: Seton {seton_score} - Opponent {opp_score}", 0, 1)
    
    # Color code win probability
    if win_prob > 50:
        pdf.set_text_color(0, 128, 0)
    else:
        pdf.set_text_color(255, 0, 0)
        
    pdf.cell(0, 10, f"Win Probability: {win_prob:.1f}%", 0, 1)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # Lineups
    pdf.add_lineup_table(seton_lineup, "Recommended Seton Lineup")
    
    if opponent_lineup:
        pdf.add_page()
        pdf.add_lineup_table(opponent_lineup, "Projected Opponent Lineup")
        
    # Output as bytes
    out = pdf.output(dest='S')
    if isinstance(out, str):
        return out.encode('latin-1')
    return out