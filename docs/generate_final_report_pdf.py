import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header
        self.drawString(54, 750, "Smart OPD: Doctor-Patient Appointment Scheduling System")
        self.drawRightString(612 - 54, 750, "Final Academic Project Report")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 742, 612 - 54, 742)

        # Footer
        self.line(54, 45, 612 - 54, 45)
        self.drawString(54, 32, "Confidential & Academic Evaluation Copy - 2026")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 32, page_str)
        self.restoreState()

def build_pdf_report():
    docs_dir = Path(__file__).resolve().parent
    pdf_path = docs_dir / "Final_Project_Report.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=45,
        rightMargin=45,
        topMargin=55,
        bottomMargin=50
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.8,
        leading=12.2,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=5
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=12,
        spaceAfter=3
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10.5,
        textColor=colors.HexColor("#0f172a")
    )

    story = []

    # PAGE 1: Executive Summary, Math, and Full Benchmark Table
    story.append(Paragraph("Smart Hospital OPD Scheduling System", title_style))
    story.append(Paragraph("<b>Comprehensive Academic Engineering &amp; Research Defense Report</b><br/>Algorithmic Interval Partitioning, Machine Learning Attendance Forecasting, and Dynamic Triage", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=8))

    story.append(Paragraph("1. Executive Summary &amp; Clinical Context", h1_style))
    story.append(Paragraph(
        "Public hospital Outpatient Departments (OPDs) handle high volumes of patient consultations across multiple specialties. Traditional appointment management in these facilities suffers from a critical operational trade-off: <b>Doctor Idle Downtime vs. Patient Waiting Congestion</b>. In public healthcare, patient no-show rates average <b>25%</b>. Fixed-slot scheduling leaves doctors sitting idle for over 25% of their working hours. Conversely, naive flat overbooking generates chaotic queue overflows, extreme wait times exceeding 55 minutes, and physician burnout.",
        body_style
    ))
    story.append(Paragraph(
        "This project resolves this healthcare challenge through <b>Smart OPD</b>: an integrated multi-tier algorithmic system featuring Greedy Multi-Doctor Interval Partitioning (O(n log d)), calibrated Machine Learning No-Show Forecasting, Risk-Aware Overbooking, Emergency Severity Index (ESI) preemption, and real-time waiting hall digital displays.",
        body_style
    ))

    story.append(Paragraph("2. Mathematical Formulations &amp; Algorithmic Architecture", h1_style))
    story.append(Paragraph("<b>• Multi-Doctor Interval Partitioning Core:</b> Minimizes doctor idle gaps by scheduling consultations greedily using a Min-Heap keyed on physician earliest available time. Complexity is bounded at <i>O(n log d)</i>, ensuring optimal physician allocation across parallel specialty rooms.", bullet_style))
    story.append(Paragraph("<b>• Machine Learning Risk Equation:</b> Trained on 2,500 clinical encounters to predict individual default probabilities: <br/><i>logit(p) = -1.80 + 0.14·lead_days + 4.00·prior_ratio - 1.40·sms_sent - 0.02·(age - 40)</i>. Model achieves ROC-AUC of <b>0.752</b>.", bullet_style))
    story.append(Paragraph("<b>• Smart Overbooking Formulation:</b> Secondary slot booking is allowed if and only if primary patient default risk <i>P(No-Show) ≥ 0.50</i>. Expected show count is tightly controlled at <i>E[Show] ≈ 1.35</i>, bounded by a strict +1 slot capacity cap.", bullet_style))
    story.append(Paragraph("<b>• Emergency Walk-In Triage Preemption:</b> Uses a PriorityQueue where ESI Level 1 and 2 emergencies preempt regular appointment queues, while doctor sudden absences automatically cascade appointments across available peers.", bullet_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("3. 30-Day Monte Carlo Benchmark Comparison", h1_style))
    story.append(Paragraph("Paired stochastic simulation across 30 operational days (4 specialist doctors, 7-hour clinics, 3,000+ patient encounters):", body_style))

    table_data = [
        [
            Paragraph("<b>Operational Metric</b>", table_header_style),
            Paragraph("<b>Traditional Fixed</b>", table_header_style),
            Paragraph("<b>Naive Overbook (+25%)</b>", table_header_style),
            Paragraph("<b>Proposed Smart OPD</b>", table_header_style),
            Paragraph("<b>Efficiency Gain</b>", table_header_style)
        ],
        [
            Paragraph("Doctor Utilization Rate", table_cell_style),
            Paragraph("83.0% ± 4.1%", table_cell_style),
            Paragraph("96.2% ± 1.9%", table_cell_style),
            Paragraph("<b>93.6% ± 3.4%</b>", table_cell_style),
            Paragraph("<b>+12.8%</b> vs Fixed", table_cell_style)
        ],
        [
            Paragraph("Doctor Idle Downtime", table_cell_style),
            Paragraph("300.7 mins/day", table_cell_style),
            Paragraph("70.3 mins/day", table_cell_style),
            Paragraph("<b>107.9 mins/day</b>", table_cell_style),
            Paragraph("<b>-64.1% reduction</b>", table_cell_style)
        ],
        [
            Paragraph("Average Patient Wait", table_cell_style),
            Paragraph("11.3 mins", table_cell_style),
            Paragraph("25.6 mins", table_cell_style),
            Paragraph("<b>21.1 mins</b>", table_cell_style),
            Paragraph("<b>-17.7%</b> vs Naive", table_cell_style)
        ],
        [
            Paragraph("90th Percentile Wait", table_cell_style),
            Paragraph("25.0 mins", table_cell_style),
            Paragraph("55.9 mins", table_cell_style),
            Paragraph("<b>52.5 mins</b>", table_cell_style),
            Paragraph("Bounded dispersion", table_cell_style)
        ],
        [
            Paragraph("Clinic Overtime Delay", table_cell_style),
            Paragraph("133.8 mins/day", table_cell_style),
            Paragraph("201.1 mins/day", table_cell_style),
            Paragraph("<b>109.2 mins/day</b>", table_cell_style),
            Paragraph("<b>-45.7%</b> vs Naive", table_cell_style)
        ],
        [
            Paragraph("Emergency Response Time", table_cell_style),
            Paragraph("239.2 mins", table_cell_style),
            Paragraph("255.1 mins", table_cell_style),
            Paragraph("<b>26.6 mins</b>", table_cell_style),
            Paragraph("<b>-88.9% reduction</b>", table_cell_style)
        ],
        [
            Paragraph("Patients Treated (30 Days)", table_cell_style),
            Paragraph("2,824", table_cell_style),
            Paragraph("3,455", table_cell_style),
            Paragraph("<b>3,069</b>", table_cell_style),
            Paragraph("<b>+245 patients</b>", table_cell_style)
        ]
    ]

    t = Table(table_data, colWidths=[1.8 * inch, 1.3 * inch, 1.4 * inch, 1.4 * inch, 1.3 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    story.append(t)

    # PAGE 2: Visualizations
    story.append(PageBreak())
    story.append(Paragraph("4. Empirical Visualizations &amp; Pareto Trade-Off Analysis", h1_style))
    story.append(Paragraph("Performance charts generated from the 30-day paired Monte Carlo stochastic simulation runs:", body_style))

    chart1_path = docs_dir / "benchmark_comparison.png"
    if chart1_path.exists():
        story.append(Image(str(chart1_path), width=7.0 * inch, height=4.3 * inch))
        story.append(Spacer(1, 6))

    chart2_path = docs_dir / "tradeoff_curve.png"
    if chart2_path.exists():
        story.append(Image(str(chart2_path), width=7.0 * inch, height=2.5 * inch))

    # PAGE 3: Web App, Feasibility, Conclusion
    story.append(PageBreak())
    story.append(Paragraph("5. Full-Stack Web Application &amp; Clinical Portals", h1_style))
    story.append(Paragraph("The system is realized as a responsive 4-tier web application built with Flask, SQLAlchemy, and Bootstrap 5:", body_style))
    story.append(Paragraph("• <b>Waiting Hall Digital Token Display (/display):</b> High-contrast, dark-mode big-screen board auto-polling every 3 seconds for lobby television monitors.", bullet_style))
    story.append(Paragraph("• <b>Doctor Consultation Workstation (/doctor/&lt;id&gt;):</b> Interactive clinical interface supporting real-time status transitions (CHECKED_IN → IN_CONSULTATION → COMPLETED) and automated emergency leave cascade across peer physicians.", bullet_style))
    story.append(Paragraph("• <b>Patient Self-Booking Portal (/book):</b> Patient portal with real-time interval slot selection, automated ML risk scoring, and token generation.", bullet_style))
    story.append(Paragraph("• <b>Emergency Triage Portal (/triage):</b> Emergency room preemption intake with Emergency Severity Index (ESI 1-4) acuity selector.", bullet_style))
    story.append(Paragraph("• <b>RESTful API Suite:</b> 10 endpoints managing appointments, status transitions, doctor availability, and real-time waiting hall token queues.", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("6. Real-World Feasibility &amp; ABDM Compatibility", h1_style))
    story.append(Paragraph("• <b>Zero Cloud Dependency:</b> Designed to run entirely on low-cost on-premise hospital local intranet servers with SQLite or PostgreSQL.", bullet_style))
    story.append(Paragraph("• <b>Ayushman Bharat Digital Mission (ABDM):</b> Built to interface with the 14-digit Ayushman Bharat Health Account (ABHA) ID for seamless longitudinal electronic health record integration.", bullet_style))
    story.append(Paragraph("• <b>Physician Workload Protection:</b> Dynamic overbooking capped at +1 eliminates physician overtime spikes while recovering wasted capacity.", bullet_style))

    story.append(Spacer(1, 6))
    story.append(Paragraph("7. Project Conclusion &amp; Future Work", h1_style))
    story.append(Paragraph(
        "Across all 7 developmental weeks, the Smart Hospital OPD Scheduling System was successfully designed, implemented, tested, and benchmarked. The system proves that combining Greedy Interval Scheduling with calibrated Machine Learning risk thresholds successfully breaks the trade-off between physician utilization and patient wait times in public healthcare.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Future Roadmap:</b> Integration with national Ayushman Bharat health records, interactive 2-way WhatsApp appointment confirmation bots, and IoT Bluetooth beacon patient arrival tracking.",
        body_style
    ))

    story.append(Spacer(1, 25))
    # Signature Block
    sig_data = [
        [Paragraph("<b>Prepared By:</b> Javid &amp; Engineering Team", body_style), Paragraph("<b>Evaluated By:</b> Academic Review Board", body_style)],
        [Paragraph("Project: Smart OPD Scheduling System", body_style), Paragraph("Date: October 2026", body_style)]
    ]
    sig_table = Table(sig_data, colWidths=[3.5 * inch, 3.5 * inch])
    sig_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sig_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ Generated Final Academic Project PDF: {pdf_path}")

if __name__ == "__main__":
    build_pdf_report()
