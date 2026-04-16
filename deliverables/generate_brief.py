"""
Part 1 Brief PDF Generator — AskElephant Outside-In Read
Usage: python generate_brief.py
Output: part1_brief.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Flowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


class ArchitectureDiagram(Flowable):
    """Draws the first section of the architecture: webhook → feature eng → XGB + HNSW."""

    def __init__(self, width=460, height=630):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W = self.width
        # Colors
        bg = HexColor("#f5f5f5")
        border = HexColor("#333333")
        accent = HexColor("#C4A882")
        text_color = HexColor("#222222")
        light_gray = HexColor("#999999")
        doc_color = HexColor("#e8e0d4")

        def box(x, y, w, h, label, sublabel=None, fill=bg):
            c.setFillColor(fill)
            c.setStrokeColor(border)
            c.setLineWidth(1.2)
            c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
            c.setFillColor(text_color)
            c.setFont("Helvetica-Bold", 10)
            if sublabel:
                c.drawCentredString(x + w/2, y + h/2 + 6, label)
                c.setFont("Helvetica", 8)
                c.setFillColor(light_gray)
                c.drawCentredString(x + w/2, y + h/2 - 8, sublabel)
            else:
                c.drawCentredString(x + w/2, y + h/2 - 3, label)

        def arrow_down(x, y1, y2):
            c.setStrokeColor(border)
            c.setLineWidth(1.2)
            c.line(x, y1, x, y2 + 6)
            # arrowhead
            c.setFillColor(border)
            path = c.beginPath()
            path.moveTo(x, y2)
            path.lineTo(x - 4, y2 + 8)
            path.lineTo(x + 4, y2 + 8)
            path.close()
            c.drawPath(path, fill=1)

        def arrow_down_split(x_from, y1, x_to, y2):
            c.setStrokeColor(border)
            c.setLineWidth(1.2)
            mid_y = (y1 + y2) / 2
            c.line(x_from, y1, x_from, mid_y)
            c.line(x_from, mid_y, x_to, mid_y)
            c.line(x_to, mid_y, x_to, y2 + 6)
            c.setFillColor(border)
            path = c.beginPath()
            path.moveTo(x_to, y2)
            path.lineTo(x_to - 4, y2 + 8)
            path.lineTo(x_to + 4, y2 + 8)
            path.close()
            c.drawPath(path, fill=1)

        def doc_icon(x, y):
            """Draw a small document icon with folded corner, no label."""
            w, h = 50, 40
            fold = 10
            c.setFillColor(doc_color)
            c.setStrokeColor(border)
            c.setLineWidth(0.8)
            # doc body
            path = c.beginPath()
            path.moveTo(x, y)
            path.lineTo(x + w - fold, y)
            path.lineTo(x + w, y + fold)
            path.lineTo(x + w, y + h)
            path.lineTo(x, y + h)
            path.close()
            c.drawPath(path, fill=1)
            # fold triangle
            path2 = c.beginPath()
            path2.moveTo(x + w - fold, y)
            path2.lineTo(x + w - fold, y + fold)
            path2.lineTo(x + w, y + fold)
            path2.close()
            c.setFillColor(HexColor("#d4cabb"))
            c.drawPath(path2, fill=1)
            # text lines inside doc
            c.setStrokeColor(light_gray)
            c.setLineWidth(0.5)
            for i in range(3):
                lx = x + 6
                ly = y + h - 14 - (i * 7)
                c.line(lx, ly, x + w - 10, ly)

        # ── Layout positions (top to bottom) ──
        top = self.height - 10
        left_x = W/2 - 100
        right_x = W/2 + 100
        bw = 180  # box width for split columns
        center_bw = 280  # box width for centered items

        # Section title
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(text_color)
        c.drawCentredString(W/2, top, "Data Management Layer")

        # Consistent spacing
        gap = 75
        bh = 45

        # 1. Webhook / API Entry
        bx = (W - center_bw) / 2
        by = top - 50
        box(bx, by, center_bw, bh, "POST /activate",
            "Webhook \u2014 Deal Record (JSON)", fill=accent)

        # Arrow down
        by2 = by - gap
        arrow_down(W/2, by, by2 + bh)

        # 2. Feature Engineering (center)
        box(bx, by2, center_bw, bh, "Feature Engineering",
            "Raw fields \u2192 tabular features")

        # Split arrow to XGBoost (left) and Embedding Model (right)
        xgb_y = by2 - gap
        embed_y = by2 - gap

        arrow_down_split(W/2, by2, left_x, xgb_y + bh)
        arrow_down_split(W/2, by2, right_x, embed_y + bh)

        # 3a. XGBoost (left)
        box(left_x - bw/2, xgb_y, bw, bh,
            "XGBoost Classifier",
            "churn_prob + SHAP importance")

        # 3b. Embedding Model (right)
        box(right_x - bw/2, embed_y, bw, bh,
            "Embedding Model",
            "features \u2192 dense vector")

        # Arrow from Embedding Model down to HNSW
        hnsw_y = embed_y - gap
        arrow_down(right_x, embed_y, hnsw_y + bh)

        # 4. HNSW Index (right)
        box(right_x - bw/2, hnsw_y, bw, bh,
            "HNSW Index",
            "ef_search = \u03b1\u00d7k (\u03b1\u22651)")

        # Arrow from HNSW down to documents
        docs_y = hnsw_y - gap
        arrow_down(right_x, hnsw_y, docs_y + 45)

        # 5. Five document icons in a row under HNSW with labels
        doc_total_w = 5 * 50 + 4 * 8
        doc_start_x = right_x - doc_total_w/2
        for i in range(5):
            dx = doc_start_x + i * 58
            doc_icon(dx, docs_y)
            c.setFillColor(text_color)
            c.setFont("Helvetica", 7)
            c.drawCentredString(dx + 25, docs_y - 10, f"Deal {i+1}")

        # ── Risk Calibration node (between XGBoost and merge) ──
        calib_y = xgb_y - 60
        calib_w = 180
        # Arrow XGBoost → Risk Calibration
        arrow_down(left_x, xgb_y, calib_y + bh)
        box(left_x - calib_w/2, calib_y, calib_w, bh,
            "Risk Calibration",
            "prob \u2192 multiplier + tier")

        # ── Convergence: both sides merge into ML Context Package ──
        merge_y = min(calib_y, docs_y - 15) - 55

        # Arrow from Risk Calibration down to merge
        arrow_down(left_x, calib_y, merge_y + bh)

        # Arrow from docs area down to merge
        arrow_down(right_x, docs_y - 15, merge_y + bh)

        # ML Context Package (center, wide)
        ctx_w = 320
        box((W - ctx_w)/2, merge_y, ctx_w, bh,
            "ML Context Package",
            "risk multiplier + tier + SHAP + k neighbors", fill=accent)

        # Arrow down to orchestrator box
        orch_y = merge_y - gap
        arrow_down(W/2, merge_y, orch_y + bh)

        # Agent Orchestrator box
        orch_w = 280
        box((W - orch_w)/2, orch_y, orch_w, bh,
            "Agent Orchestrator",
            "deal record + ML context \u2192 parallel agent calls")



class CombinedAgentDiagram(Flowable):
    """Draws the full agent pipeline: ML Context → Analysis Agents → Output Agents → Manifest."""

    def __init__(self, width=460, height=630):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def wrap(self, availWidth, availHeight):
        return self.width, self.height

    def draw(self):
        c = self.canv
        W = self.width
        border = HexColor("#333333")
        accent = HexColor("#C4A882")
        text_color = HexColor("#222222")
        light_gray = HexColor("#999999")
        analysis_color = HexColor("#dce4f0")

        def box(x, y, w, h, label, sublabel=None, fill=HexColor("#f5f5f5")):
            c.setFillColor(fill)
            c.setStrokeColor(border)
            c.setLineWidth(1.2)
            c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
            c.setFillColor(text_color)
            c.setFont("Helvetica-Bold", 9)
            if sublabel:
                c.drawCentredString(x + w/2, y + h/2 + 6, label)
                c.setFont("Helvetica", 7)
                c.setFillColor(light_gray)
                c.drawCentredString(x + w/2, y + h/2 - 7, sublabel)
            else:
                c.drawCentredString(x + w/2, y + h/2 - 3, label)

        def arrow_down(x, y1, y2):
            c.setStrokeColor(border)
            c.setLineWidth(1.2)
            c.line(x, y1, x, y2 + 6)
            c.setFillColor(border)
            path = c.beginPath()
            path.moveTo(x, y2)
            path.lineTo(x - 4, y2 + 8)
            path.lineTo(x + 4, y2 + 8)
            path.close()
            c.drawPath(path, fill=1)

        top = self.height - 10
        left_x = W/2 - 110
        right_x = W/2 + 110
        bw = 190

        # Section label
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(text_color)
        c.drawCentredString(W/2, top, "Agent Orchestration Layer")

        # Consistent gap size
        gap = 75
        bh = 45  # standard box height

        # ML Context Package
        ctx_y = top - 50
        ctx_w = 300
        box((W - ctx_w)/2, ctx_y, ctx_w, bh,
            "ML Context Package", "risk score + SHAP + k neighbors + urgency", fill=accent)

        # Split arrows to two analysis agents
        qa_y = ctx_y - gap
        risk_y = ctx_y - gap

        # Arrow to Q&A History (left)
        c.setStrokeColor(border)
        c.setLineWidth(1.2)
        mid_y = ctx_y - (gap - bh) / 2
        c.line(W/2, ctx_y, W/2, mid_y)
        c.line(W/2, mid_y, left_x, mid_y)
        c.line(left_x, mid_y, left_x, qa_y + bh + 6)
        c.setFillColor(border)
        path = c.beginPath()
        path.moveTo(left_x, qa_y + bh)
        path.lineTo(left_x - 4, qa_y + bh + 8)
        path.lineTo(left_x + 4, qa_y + bh + 8)
        path.close()
        c.drawPath(path, fill=1)

        # Arrow to Risk Narrative (right)
        c.line(W/2, mid_y, right_x, mid_y)
        c.line(right_x, mid_y, right_x, risk_y + bh + 6)
        c.setFillColor(border)
        path = c.beginPath()
        path.moveTo(right_x, risk_y + bh)
        path.lineTo(right_x - 4, risk_y + bh + 8)
        path.lineTo(right_x + 4, risk_y + bh + 8)
        path.close()
        c.drawPath(path, fill=1)

        # Q&A History Agent (left)
        box(left_x - bw/2, qa_y, bw, bh,
            "Q&A History Agent",
            "Parses transcripts \u2192 structured Q&A",
            fill=analysis_color)

        # Risk Narrative Agent (right)
        box(right_x - bw/2, risk_y, bw, bh,
            "Risk Narrative Agent",
            "XGB + SHAP + NN outcomes \u2192 plain English",
            fill=analysis_color)

        # Merge arrows down to Enriched Context Package
        enrich_y = qa_y - gap
        arrow_down(left_x, qa_y, enrich_y + bh)
        arrow_down(right_x, risk_y, enrich_y + bh)

        enrich_w = 320
        box((W - enrich_w)/2, enrich_y, enrich_w, bh,
            "Enriched Context Package",
            "deal + ML scores + Q&A history + risk narrative", fill=accent)

        # ── Arrow down from Enriched Context, branching to 6 agents ──
        agent_fill = HexColor("#e3ede8")

        def agent_box(x, y, w, h, title, desc):
            c.setFillColor(agent_fill)
            c.setStrokeColor(border)
            c.setLineWidth(1)
            c.roundRect(x, y, w, h, 5, fill=1, stroke=1)
            c.setFillColor(text_color)
            c.setFont("Helvetica-Bold", 8)
            c.drawCentredString(x + w/2, y + h - 13, title)
            c.setFont("Helvetica", 6.5)
            c.setFillColor(light_gray)
            words = desc.split()
            mid = len(words) // 2
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:])
            c.drawCentredString(x + w/2, y + h - 24, line1)
            c.drawCentredString(x + w/2, y + h - 33, line2)

        agents = [
            ("Welcome Email", "Customer-facing welcome in brand voice, personalized to use case"),
            ("CSM Brief", "Risk narrative, Q&A history, NN outcomes, what to watch"),
            ("Slack Announce", "Internal team notification with deal context and key contacts"),
            ("Kickoff Meeting", "Agenda, invite draft, priorities calibrated to risk profile"),
            ("CRM Updates", "Stage/field changes queued as structured JSON, ready to push"),
            ("30-Day Plan", "MEDDIC \u2192 TTFV milestones, gated by risk and deal segment"),
        ]

        aw = 200
        ah = 45
        gap_x = 20
        gap_y = 12
        col1_x = (W - 2*aw - gap_x) / 2
        col2_x = col1_x + aw + gap_x

        # Starting y for first row of agents
        row_start_y = enrich_y - 60

        # Draw the trunk line down from enriched context
        trunk_bottom = row_start_y + ah/2
        trunk_x = W/2
        c.setStrokeColor(border)
        c.setLineWidth(1.2)
        c.line(trunk_x, enrich_y, trunk_x, trunk_bottom)

        # For each row, draw a horizontal branch and arrows to left/right agent
        for row in range(3):
            ry = row_start_y - row * (ah + gap_y)
            branch_y = ry + ah/2

            # Horizontal branch line
            c.setStrokeColor(border)
            c.setLineWidth(1.2)
            c.line(trunk_x, branch_y, col1_x + aw/2, branch_y)
            c.line(trunk_x, branch_y, col2_x + aw/2, branch_y)

            # Vertical trunk continues down (except last row)
            if row < 2:
                next_branch_y = (row_start_y - (row+1) * (ah + gap_y)) + ah/2
                c.line(trunk_x, branch_y, trunk_x, next_branch_y)

            # Arrowheads pointing at agent boxes (left)
            c.setFillColor(border)
            p = c.beginPath()
            lx = col1_x + aw
            p.moveTo(lx, branch_y)
            p.lineTo(lx + 6, branch_y - 3)
            p.lineTo(lx + 6, branch_y + 3)
            p.close()
            c.drawPath(p, fill=1)

            # Arrowheads pointing at agent boxes (right)
            p2 = c.beginPath()
            rx = col2_x
            p2.moveTo(rx, branch_y)
            p2.lineTo(rx - 6, branch_y - 3)
            p2.lineTo(rx - 6, branch_y + 3)
            p2.close()
            c.drawPath(p2, fill=1)

            # Draw agent boxes
            idx_l = row * 2
            idx_r = row * 2 + 1
            agent_box(col1_x, ry, aw, ah, agents[idx_l][0], agents[idx_l][1])
            agent_box(col2_x, ry, aw, ah, agents[idx_r][0], agents[idx_r][1])

        # Confidence Manifest below
        last_row_y = row_start_y - 2 * (ah + gap_y)
        manifest_y = last_row_y - 45
        c.setFillColor(accent)
        c.setStrokeColor(border)
        c.setLineWidth(1.2)
        manifest_w = 320
        c.roundRect((W - manifest_w)/2, manifest_y, manifest_w, 35, 6, fill=1, stroke=1)
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W/2, manifest_y + 20, "Confidence Manifest")
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#555555"))
        c.drawCentredString(W/2, manifest_y + 8,
            "overall_confidence | flags | blocked_artifacts | escalation_triggers")

        # Arrow from last row down to manifest
        c.setStrokeColor(border)
        c.setLineWidth(1.2)
        c.line(trunk_x, last_row_y + ah/2, trunk_x, manifest_y + 35 + 6)
        c.setFillColor(border)
        p = c.beginPath()
        p.moveTo(trunk_x, manifest_y + 35)
        p.lineTo(trunk_x - 4, manifest_y + 35 + 8)
        p.lineTo(trunk_x + 4, manifest_y + 35 + 8)
        p.close()
        c.drawPath(p, fill=1)

# ─── CONFIG ───────────────────────────────────────────────────────────
OUTPUT_FILE = "part1_brief.pdf"
TITLE = "AskElephant \u2014 GTM Engineer Pre-Work"
AUTHOR = "Morgan Cooper, M.S."
DATE = "April 2026"

FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_BOLD_ITALIC = "Helvetica-BoldOblique"
FONT_SIZE = 11
LEADING = 15
MARGIN = 1 * inch
LINK_COLOR = HexColor("#1a0dab")

# ─── REFERENCES ───────────────────────────────────────────────────────
# Add references here as you build out the brief.
# Format: (person, title, company, source_label, url)

REFERENCES = [
    {
        "id": 1,
        "person": "Kevin",
        "title": "RevOps",
        "company": "Prophetic Software",
        "source": "Customer testimonial",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 2,
        "person": "Brittany Vandall-Miller",
        "title": "Director of Sales and Business Development",
        "company": "Trailway Growth",
        "source": "Customer testimonial",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 3,
        "person": "Italo Leiva",
        "title": "Partner",
        "company": "Peddle",
        "source": "Customer testimonial",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 4,
        "person": "Multiple customers",
        "title": "Various",
        "company": "Vendilli, alldemand, Revvy, hapily, 1406 Consulting, Mind and Metrics",
        "source": "HubSpot ecosystem customers identified from testimonials and case studies",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 5,
        "person": "Multiple customers",
        "title": "Various",
        "company": "Finally, Copper, Peddle, Intelligent Technical Solutions",
        "source": "Mid-market customers identified from public company data",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 6,
        "person": "Greg Larsen",
        "title": "Consultant",
        "company": "Catalyst Sales Consulting",
        "source": "Website testimonial on Gong limitations",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 7,
        "person": "Eric Maida",
        "title": "VP of Growth",
        "company": "TrustModel",
        "source": "Website testimonial on Gong comparison",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 8,
        "person": "Kyleah Etherton",
        "title": "RevOps",
        "company": "Tilt",
        "source": "Website testimonial on cancelling Gong",
        "url": "https://www.askelephant.ai/customers",
    },
    {
        "id": 9,
        "person": "Clay",
        "title": "",
        "company": "Clay",
        "source": "Product description \u2014 data enrichment and outbound prospecting platform",
        "url": "https://www.clay.com",
    },
    {
        "id": 10,
        "person": "11x",
        "title": "",
        "company": "11x",
        "source": "Product description \u2014 AI-powered autonomous SDR platform",
        "url": "https://www.11x.ai",
    },
    {
        "id": 11,
        "person": "Cognism",
        "title": "",
        "company": "Cognism",
        "source": "State of Cold Calling Report \u2014 cold call success rates dropped from 4.82% to 2.3%",
        "url": "https://www.cognism.com/blog/cold-calling-success-rates",
    },
    {
        "id": 12,
        "person": "Landbase",
        "title": "",
        "company": "Landbase (citing Gartner)",
        "source": "B2B contact data accuracy \u2014 70% of CRM data is outdated, incomplete, or inaccurate",
        "url": "https://www.landbase.com/blog/b2b-contact-data-accuracy-statistic",
    },
    {
        "id": 13,
        "person": "Gartner",
        "title": "",
        "company": "Gartner",
        "source": "Data quality research \u2014 poor data costs organizations $12.9\u201315M annually",
        "url": "https://www.gartner.com/en/data-analytics/topics/data-quality",
    },
    {
        "id": 14,
        "person": "Salesforce",
        "title": "",
        "company": "Salesforce",
        "source": "2024 State of Sales Report \u2014 reps spend 70% of time on non-selling tasks",
        "url": "https://www.salesforce.com/news/stories/sales-research-2023/",
    },
    {
        "id": 15,
        "person": "Cooper, M.R. & Busch, M.",
        "title": "",
        "company": "Regis University",
        "source": "Capacity-Limited Failure in Approximate Nearest Neighbor Search on Image Embedding Spaces. J. Imaging 2026, 12, 55",
        "url": "https://doi.org/10.3390/jimaging12020055",
    },
]


def ref(n):
    """Inline reference marker: [1], [2], etc."""
    return f'<super><font size="8">[{n}]</font></super>'


def link(url, text):
    """Clickable hyperlink."""
    return f'<a href="{url}" color="#{LINK_COLOR.hexval()[2:]}">{text}</a>'


def quote(text):
    """Italic quote."""
    return f'<i>\u201c{text}\u201d</i>'


# ─── STYLES ───────────────────────────────────────────────────────────

def build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="DocTitle",
        fontName=FONT_BOLD,
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle",
        fontName=FONT_BODY,
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=HexColor("#555555"),
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeader",
        fontName=FONT_BOLD,
        fontSize=13,
        leading=18,
        spaceBefore=16,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Body",
        fontName=FONT_BODY,
        fontSize=FONT_SIZE,
        leading=LEADING,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="BodyBold",
        fontName=FONT_BOLD,
        fontSize=FONT_SIZE,
        leading=LEADING,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="RefItem",
        fontName=FONT_BODY,
        fontSize=10,
        leading=13,
        leftIndent=24,
        firstLineIndent=-24,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        name="Placeholder",
        fontName=FONT_ITALIC,
        fontSize=FONT_SIZE,
        leading=LEADING,
        textColor=HexColor("#999999"),
        spaceAfter=8,
    ))
    return styles


# ─── CONTENT ──────────────────────────────────────────────────────────
# Edit your brief content here. Use ref(n) for citations, quote() for
# direct quotes, link() for hyperlinks, and <b>...</b> for bold.

def build_content(styles):
    story = []
    s = styles

    # ── Title page ──
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("AskElephant", s["DocTitle"]))
    story.append(Spacer(1, 24))
    story.append(HRFlowable(
        width="40%", thickness=1,
        color=HexColor("#333333"), spaceAfter=24
    ))
    story.append(Paragraph("GTM Engineer Pre-Work", s["DocSubtitle"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(AUTHOR, s["DocSubtitle"]))
    story.append(Paragraph(DATE, s["DocSubtitle"]))
    story.append(PageBreak())

    # ── Question 1 ──
    story.append(Paragraph(
        "1. Who does AskElephant sell to?", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "Based on AskElephant\u2019s public customer base, the current core is "
        "clearly <b>SMB</b> \u2014 sales and CS leaders at 20\u2013100 person B2B "
        "companies running HubSpot, with heavy concentration in the HubSpot "
        "ecosystem itself " + ref(4) + ". There\u2019s a mild tilt toward "
        "<b>mid-market (100\u20131,000 employees)</b> with customers like Finally, "
        "Copper, Peddle, and ITS already on the platform " + ref(5) + ", and "
        "signals that a GTM play targeting mid-market is in motion. That\u2019s "
        "where the real opportunity lives: companies that use technology daily "
        "but don\u2019t have the technical depth to build automation themselves, "
        "with distinct sales, CS, implementation, and RevOps teams that create 50+ seat "
        "expansion opportunities. The trigger is <b>post-call-recorder "
        "disillusionment</b>: these teams adopted Fathom and Fireflies for "
        "recording but nobody is closing the loop from transcript to CRM "
        "update, follow-up, and pipeline accuracy \u2014 automatically "
        + ref(1) + ref(2) + ref(3) + ".",
        s["Body"],
    ))

    # ── Question 2 ──
    story.append(Paragraph(
        "2. What is AskElephant actually building?", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "AskElephant is building autonomous infrastructure that captures, "
        "routes, and acts on revenue data end-to-end \u2014 AI is the engine, "
        "not the product. It starts with the call, but the value is everything "
        "that happens after: CRM fields written, follow-ups drafted, next "
        "steps pushed, forecasts updated, handoffs generated \u2014 without a "
        "rep touching it. Today, every competitor owns a slice: Gong owns "
        "conversation intelligence but charges enterprise prices and struggles "
        "with accurate CRM field writes " + ref(6) + ref(7) + ref(8)
        + "; Fathom and Fireflies own the transcript but the data stays in a "
        "silo " + ref(3) + "; Clay " + ref(9) + " and 11x " + ref(10)
        + " own pre-sale prospecting and outbound; Clari owns forecasting but "
        "reads from the same dirty CRM data everyone else ignores. AskElephant "
        "is positioning to own the entire revenue operations layer \u2014 pre-sale, "
        "active selling, and post-sale \u2014 not just the connective tissue between "
        "these tools, but the replacement for needing them separately at all. "
        "The lane is: one system that makes the CRM accurate, acts on that "
        "data, and does it at a price point any company size can afford.",
        s["Body"],
    ))

    # ── Question 3 ──
    story.append(Paragraph(
        "3. Three revenue-work problems customers actually feel.",
        s["SectionHeader"],
    ))
    story.append(Paragraph(
        "<b>Outbound is dying a slow death.</b> Cold call success rates "
        "collapsed 52% in a single year \u2014 from 4.82% to 2.3% "
        + ref(11) + ". Less than 1 in 50 calls converts. Revenue teams are "
        "doing more work for fewer results.",
        s["Body"],
    ))
    story.append(Paragraph(
        "<b>Revenue data is a swamp, not a structured lake.</b> 70% of CRM "
        "data is outdated, incomplete, or inaccurate " + ref(12) + ". "
        "Gartner estimates poor data quality costs organizations "
        "$12.9\u201315 million annually " + ref(13) + ". Reps don\u2019t update "
        "fields. Notes live in someone\u2019s head. Forecasts are built on "
        "whatever someone remembers to enter.",
        s["Body"],
    ))
    story.append(Paragraph(
        "<b>Reps spend more time on admin than selling.</b> 70% of a sales "
        "rep\u2019s time goes to non-selling tasks \u2014 54% of the workweek is "
        "just data handling " + ref(14) + ". That\u2019s over 21 hours a week "
        "managing information instead of engaging customers. The systems "
        "revenue teams use create busywork instead of eliminating it.",
        s["Body"],
    ))

    # ── Question 4 ──
    story.append(Paragraph(
        "4. The sharpest thing I\u2019d change about the story.",
        s["SectionHeader"],
    ))
    story.append(Paragraph(
        "<b>Stop leading with AI. Lead with data.</b>",
        s["Body"],
    ))
    story.append(Paragraph(
        "AskElephant\u2019s current story is \u201cAI employees for revenue teams.\u201d "
        "The problem is that every tool in this space says the same thing. "
        "What actually makes AskElephant defensible isn\u2019t the AI \u2014 it\u2019s the "
        "data layer underneath. AskElephant sits on every call, every CRM "
        "field, every follow-up, every handoff across the entire revenue "
        "cycle. That\u2019s a proprietary data asset that compounds over time. "
        "The AI is replaceable \u2014 models get commoditized, prompts get copied, "
        "agents get rebuilt. The structured revenue data that feeds them is not.",
        s["Body"],
    ))
    story.append(Paragraph(
        "If I had one call to change the narrative: position AskElephant as "
        "the revenue data platform that happens to automate with AI, not the "
        "AI platform that happens to touch data. The moat isn\u2019t the model. "
        "The moat is that no competitor has the same depth of structured, "
        "cross-functional revenue data to train against, score with, or act "
        "on. When the AI layer is grounded in real data, the outputs get "
        "better over time. When it\u2019s not, it\u2019s just another prompt wrapper "
        "waiting to be replaced.",
        s["Body"],
    ))

    # ── Part 2: Motion Pick ──
    story.append(PageBreak())
    story.append(Paragraph(
        "Part 2 \u2014 Pick Your Motion", s["DocTitle"]
    ))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<b>Motion: C \u2014 Closed-Won Activation</b>", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "I ruled out Motion A due to external data access \u2014 mapping a buying "
        "committee requires LinkedIn, Apollo, and ZoomInfo, all paywalled or "
        "rate-limited. Building the system would mean fighting data access, not "
        "demonstrating architecture. Motion B requires time series anomaly "
        "detection to identify when and why a deal went dark \u2014 that needs "
        "sequential activity data that\u2019s difficult to synthesize realistically, "
        "and the complexity of the detection layer would dominate the build time.",
        s["Body"],
    ))
    story.append(Paragraph(
        "Motion C has a fixed, consistent trigger: the deal closes, the handoff "
        "runs. The variance is in the deal attributes, not the process shape. I "
        "can engineer tabular features from raw deal data (notes, CRM fields, "
        "contacts, call context) and train real models on it. Rather than "
        "building an AI system that happens to touch data, I wanted to "
        "demonstrate a <b>data system that incorporates agent orchestration.</b> "
        "The ML models make the judgment calls \u2014 an XGBoost churn classifier "
        "scores risk with SHAP explainability, and an HNSW-indexed embedding "
        "space retrieves historically similar deals with their actual outcomes "
        "as grounded context for agents. The HNSW parameter tuning draws on my "
        "own published research on capacity-limited failure in approximate "
        "nearest neighbor search " + ref(15) + ". The agents are downstream: "
        "they generate artifacts based on what the data already decided, not "
        "what a prompt guessed.",
        s["Body"],
    ))
    story.append(Paragraph(
        "<b>Working vs. shipped:</b> the system produces a different handoff "
        "for a high-risk, single-threaded deal than for a smooth enterprise "
        "close \u2014 because the models learned the difference, not because someone "
        "wrote two templates.",
        s["Body"],
    ))

    # ── Design Doc: Architecture ──
    story.append(PageBreak())
    story.append(ArchitectureDiagram())

    # Combined agent layer — one continuous block
    story.append(PageBreak())
    story.append(CombinedAgentDiagram())

    # ── Design Note — Written Sections ──
    story.append(PageBreak())
    story.append(Paragraph(
        "Design Note \u2014 Architecture & Judgment Calls", s["DocTitle"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Data Sources", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 Where does the system get its data? "
        "CRM deal records, AskElephant AI-processed call data, public company enrichment, "
        "historical outcomes for model training.]",
        s["Placeholder"]))

    story.append(Paragraph("Judgment Calls", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 Why XGBoost + HNSW instead of a single "
        "model? Why one-shot LLM per deal vs. per-touch? Why synthetic outcomes for "
        "training vs. real CRM history? Why did we split analysis and output agents?]",
        s["Placeholder"]))

    story.append(Paragraph("What Fails at Scale", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 JSON files hit a wall around 10K deals. "
        "HNSW index rebuild becomes expensive at volume. LLM rate limits on parallel "
        "agents. What specifically breaks and at what point.]",
        s["Placeholder"]))

    story.append(Paragraph("What We'd Harden in v2", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 Move state to Postgres. Switch delivery "
        "to real Gmail/Slack/HubSpot with retries. Add drift monitoring. Active learning "
        "from CSM feedback on flagged artifacts. Per-industry model variants.]",
        s["Placeholder"]))

    story.append(Paragraph("Unsupervised vs. Human-in-the-Loop", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 Which agent outputs can auto-send? "
        "Which require CSM review? CRM updates and Slack announcements: safe to auto. "
        "Welcome email to customer: held when high-risk flagged. CSM brief: always "
        "reviewed before kickoff. Confidence manifest drives the gates.]",
        s["Placeholder"]))

    # ── Part 4: First 90 Days ──
    story.append(PageBreak())
    story.append(Paragraph(
        "Part 4 \u2014 First 90 Days", s["DocTitle"]
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "The next three AI employees I'd build in my first 90 days, "
        "and which gets priority week one.",
        s["Body"],
    ))
    story.append(Spacer(1, 12))

    # AI Employee #1 (already built)
    story.append(Paragraph(
        "AI Employee #1 \u2014 Closed-Won Activation (Shipped)",
        s["SectionHeader"]
    ))
    story.append(Paragraph("[To be completed \u2014 Owns: the deal just closed, run the handoff. "
        "Triggers on closed-won webhook. Consumes deal record + call data. Produces 6 "
        "handoff artifacts. Makes decisions on risk escalation, artifact blocking, "
        "human review routing. 30/60/90 success: % of handoffs that go out without "
        "CSM edits; time-to-kickoff; day-90 retention lift vs. control. Hands off to "
        "CSM when: high risk, compound risk, or low model confidence.]",
        s["Placeholder"]))
    story.append(Spacer(1, 10))

    # AI Employee #2
    story.append(Paragraph(
        "AI Employee #2 \u2014 Stale Deal Re-Engagement",
        s["SectionHeader"]
    ))
    story.append(Paragraph("[To be completed \u2014 Owns: 'This deal went dark. Get it moving "
        "or kill it honestly.' Triggers on no-activity thresholds. Consumes deal history. "
        "Produces re-engagement play OR close-lost recommendation with reasoning. "
        "30/60/90 success: % of stale deals moved; % correctly killed; revenue recovered. "
        "Hands off when: deal has legal/procurement blocker, or when AE overrides.]",
        s["Placeholder"]))
    story.append(Spacer(1, 10))

    # AI Employee #3
    story.append(Paragraph(
        "AI Employee #3 \u2014 Expansion Opportunity Detection",
        s["SectionHeader"]
    ))
    story.append(Paragraph("[To be completed \u2014 Owns: surfaces upsell/cross-sell signals "
        "from customer call data. Triggers on usage patterns + conversation signals. "
        "Consumes CS call transcripts, product usage, account health. Produces prioritized "
        "expansion opportunities with talking points. 30/60/90: expansion ARR sourced; "
        "win rate on AI-flagged opportunities vs. baseline. Hands off to CSM/AM for the "
        "actual conversation \u2014 AI identifies, human closes.]",
        s["Placeholder"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Which Gets Priority Week One", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 Stale Deal Re-Engagement. Why: it's the "
        "highest-leverage use case, directly recovers revenue, and has the clearest "
        "feedback loop. Every sales org has a graveyard of dark deals that are worth "
        "money if correctly re-engaged \u2014 or worth closing out if not.]",
        s["Placeholder"]))

    # ── Part 5: Your One Question ──
    story.append(PageBreak())
    story.append(Paragraph(
        "Part 5 \u2014 Your One Question", s["DocTitle"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("The Question", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 One question for Woody, Sam, or Ben "
        "before deciding to take this role.]",
        s["Placeholder"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("What the Answer Would Change", s["SectionHeader"]))
    story.append(Paragraph("[To be completed \u2014 1-2 sentences on how the answer "
        "shapes the work I'd do here.]",
        s["Placeholder"]))

    # ── References page ──
    story.append(PageBreak())
    story.append(Paragraph("References", s["SectionHeader"]))
    story.append(HRFlowable(
        width="100%", thickness=0.5,
        color=HexColor("#cccccc"), spaceAfter=12
    ))

    for r in REFERENCES:
        ref_text = (
            f"[{r['id']}] {r['person']}, {r['title']} at {r['company']}. "
            f"{r['source']}. {link(r['url'], r['url'])}"
        )
        story.append(Paragraph(ref_text, s["RefItem"]))

    return story


# ─── BUILD PDF ────────────────────────────────────────────────────────

def main():
    doc = SimpleDocTemplate(
        OUTPUT_FILE,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
        title=TITLE,
        author=AUTHOR,
    )
    styles = build_styles()
    story = build_content(styles)
    doc.build(story)
    print(f"Generated: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
