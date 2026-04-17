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


class UnifiedPipelineDiagram(Flowable):
    """Single-page diagram showing the complete pipeline flow from webhook to PDF delivery."""

    def __init__(self, width=480, height=636):
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
        gray = HexColor("#999999")
        analysis = HexColor("#dce4f0")
        agent = HexColor("#e3ede8")
        wave2 = HexColor("#e8dce8")
        gate_c = HexColor("#f0dada")

        bh = 24  # box height
        gap = 30  # gap between rows

        def box(x, y, w, h, label, sublabel=None, fill=bg):
            c.setFillColor(fill)
            c.setStrokeColor(border)
            c.setLineWidth(0.8)
            c.roundRect(x, y, w, h, 4, fill=1, stroke=1)
            c.setFillColor(text_color)
            if sublabel:
                c.setFont("Helvetica-Bold", 7)
                c.drawCentredString(x + w/2, y + h/2 + 3, label)
                c.setFont("Helvetica", 5.5)
                c.setFillColor(gray)
                c.drawCentredString(x + w/2, y + h/2 - 6, sublabel)
            else:
                c.setFont("Helvetica-Bold", 7)
                c.drawCentredString(x + w/2, y + h/2 - 2, label)

        def arrow(x, y1, y2):
            c.setStrokeColor(border)
            c.setLineWidth(0.8)
            c.line(x, y1, x, y2 + 4)
            c.setFillColor(border)
            p = c.beginPath()
            p.moveTo(x, y2)
            p.lineTo(x - 3, y2 + 6)
            p.lineTo(x + 3, y2 + 6)
            p.close()
            c.drawPath(p, fill=1)

        def split_arrows(cx, y1, lx, rx, y2, h):
            mid = y1 - (y1 - y2 - h) / 2
            c.setStrokeColor(border)
            c.setLineWidth(0.8)
            c.line(cx, y1, cx, mid)
            c.line(cx, mid, lx, mid)
            c.line(cx, mid, rx, mid)
            for ax in [lx, rx]:
                c.line(ax, mid, ax, y2 + h + 4)
                c.setFillColor(border)
                p = c.beginPath()
                p.moveTo(ax, y2 + h)
                p.lineTo(ax - 3, y2 + h + 6)
                p.lineTo(ax + 3, y2 + h + 6)
                p.close()
                c.drawPath(p, fill=1)

        def section_label(x, y, text):
            c.setFont("Helvetica-Bold", 6)
            c.setFillColor(gray)
            c.drawString(x, y, text)

        # ── Systematic layout: even vertical spacing, full page ──
        cw = 300    # center box width (wider)
        sw = 200    # split box width (wider)
        lx = W/2 - 115
        rx = W/2 + 115
        top = self.height - 10

        # 11 rows (gate removed), evenly spaced to fill entire page
        # Extra 20px gap after title before first box
        title_gap = 20
        usable = self.height - 40 - title_gap
        row_step = usable / 11

        def row_y(n):
            """Y position for row n (0-indexed from top)."""
            return top - 30 - title_gap - n * row_step

        # Title — matches other page titles
        c.setFont("Helvetica-Bold", 18)
        c.setFillColor(text_color)
        c.drawCentredString(W/2, top, "Architecture")

        # ── ROW 0: Webhook ──
        y0 = row_y(0)
        box((W - cw)/2, y0, cw, bh, "POST /activate", "Webhook: Deal Record (JSON)", fill=accent)

        # ── ROW 1: Feature Engineering ──
        y1 = row_y(1)
        arrow(W/2, y0, y1 + bh)
        box((W - cw)/2, y1, cw, bh, "Feature Engineering", "Raw deal \u2192 54 derived features")

        # ── ROW 2: XGBoost + Feature Scaling ──
        y2 = row_y(2)
        split_arrows(W/2, y1, lx, rx, y2, bh)
        box(lx - sw/2, y2, sw, bh, "XGBoost Classifier", "churn_prob + SHAP importance")
        box(rx - sw/2, y2, sw, bh, "Feature Scaling", "StandardScaler \u2192 54D vector")

        # ── ROW 3: Risk Calibration + HNSW ──
        y3 = row_y(3)
        arrow(lx, y2, y3 + bh)
        arrow(rx, y2, y3 + bh)
        box(lx - sw/2, y3, sw, bh, "Risk Calibration (SSM)", "prob \u2192 multiplier + tier")
        box(rx - sw/2, y3, sw, bh, "HNSW Index (k=5)", "ef_search = \u03b1\u00d7k, 5 neighbors")

        # ── ROW 4: ML Context Package ──
        y4 = row_y(4)
        arrow(lx, y3, y4 + bh)
        arrow(rx, y3, y4 + bh)
        box((W - 280)/2, y4, 280, bh,
            "ML Context Package",
            "risk tier + multiplier + SHAP + neighbors + churn rate", fill=accent)

        # ── ROW 5: 4 Analysis Agents ──
        y5 = row_y(5)
        a_spread = (W - 40) / 4  # evenly across full width
        a_positions = [20 + a_spread * i + a_spread/2 for i in range(4)]
        a_w = a_spread - 8  # fill with small gaps
        a_labels = [
            ("Q&A Agent", "LLM insight analysis"),
            ("Objection Agent", "LLM insight analysis"),
            ("Neighbor Agent", "LLM pattern analysis"),
            ("Risk Narrative", "LLM risk story"),
        ]

        mid5 = y4 - (y4 - y5 - bh) / 2
        c.setStrokeColor(border)
        c.setLineWidth(0.8)
        c.line(W/2, y4, W/2, mid5)
        for ax in a_positions:
            c.line(W/2, mid5, ax, mid5)
            c.line(ax, mid5, ax, y5 + bh + 4)
            c.setFillColor(border)
            p = c.beginPath()
            p.moveTo(ax, y5 + bh)
            p.lineTo(ax - 3, y5 + bh + 6)
            p.lineTo(ax + 3, y5 + bh + 6)
            p.close()
            c.drawPath(p, fill=1)

        for i, (lt, sub) in enumerate(a_labels):
            box(a_positions[i] - a_w/2, y5, a_w, bh, lt, sub, fill=analysis)

        # ── ROW 6: Enriched Context ──
        y6 = row_y(6)
        # Horizontal bar merging all 4 agents (same style as Wave 1)
        merge_y = y5 - (y5 - y6 - bh) / 2
        c.setStrokeColor(border)
        c.setLineWidth(0.6)
        c.line(a_positions[0], merge_y, a_positions[-1], merge_y)
        for ax in a_positions:
            c.line(ax, y5, ax, merge_y)
        c.line(W/2, merge_y, W/2, y6 + bh + 4)
        # Single arrowhead into Enriched Context
        c.setFillColor(border)
        p = c.beginPath()
        p.moveTo(W/2, y6 + bh)
        p.lineTo(W/2 - 3, y6 + bh + 6)
        p.lineTo(W/2 + 3, y6 + bh + 6)
        p.close()
        c.drawPath(p, fill=1)
        box((W - 280)/2, y6, 280, bh,
            "Enriched Context",
            "deal + ML context + Q&A + objections + neighbors + risk", fill=accent)

        # ── ROW 7: Wave 1 — 5 agents (same fan-out pattern as analysis agents) ──
        y7 = row_y(7)

        w1_spread = (W - 20) / 5
        aw = w1_spread - 6
        w1_positions = [10 + i * w1_spread + w1_spread/2 for i in range(5)]
        w1_names = ["Welcome\nEmail", "Slack\nAnnounce", "CSM\nBrief", "Kickoff\nDraft", "CRM\nUpdates"]

        # Fan-out: trunk → horizontal bar → drops with arrowheads (matches analysis layer)
        mid7 = y6 - (y6 - y7 - bh) / 2
        c.setStrokeColor(border)
        c.setLineWidth(0.8)
        c.line(W/2, y6, W/2, mid7)
        for wx in w1_positions:
            c.line(W/2, mid7, wx, mid7)
            c.line(wx, mid7, wx, y7 + bh + 4)
            c.setFillColor(border)
            p = c.beginPath()
            p.moveTo(wx, y7 + bh)
            p.lineTo(wx - 3, y7 + bh + 6)
            p.lineTo(wx + 3, y7 + bh + 6)
            p.close()
            c.drawPath(p, fill=1)

        for i, name in enumerate(w1_names):
            bx = w1_positions[i] - aw/2
            line1 = name.split('\n')[0]
            line2 = name.split('\n')[1] if '\n' in name else ''
            c.setFillColor(agent)
            c.setStrokeColor(border)
            c.setLineWidth(0.8)
            c.roundRect(bx, y7, aw, bh, 3, fill=1, stroke=1)
            c.setFillColor(text_color)
            c.setFont("Helvetica-Bold", 6.5)
            if line2:
                c.drawCentredString(bx + aw/2, y7 + bh/2 + 2, line1)
                c.setFont("Helvetica", 5.5)
                c.setFillColor(gray)
                c.drawCentredString(bx + aw/2, y7 + bh/2 - 7, line2)
            else:
                c.drawCentredString(bx + aw/2, y7 + bh/2 - 2, line1)

        # ── ROW 8: Wave 2 — Success Plan ──
        y9 = row_y(8)
        # Horizontal bar merge from all 5 agents (same pattern as analysis → enriched)
        merge7 = y7 - (y7 - y9 - bh) / 2
        c.setStrokeColor(border)
        c.setLineWidth(0.6)
        c.line(w1_positions[0], merge7, w1_positions[-1], merge7)
        for wx in w1_positions:
            c.line(wx, y7, wx, merge7)
        c.line(W/2, merge7, W/2, y9 + bh + 4)
        c.setFillColor(border)
        p = c.beginPath()
        p.moveTo(W/2, y9 + bh)
        p.lineTo(W/2 - 3, y9 + bh + 6)
        p.lineTo(W/2 + 3, y9 + bh + 6)
        p.close()
        c.drawPath(p, fill=1)
        box((W - cw)/2, y9, cw, bh,
            "30-Day Success Plan Agent",
            "Consumes CSM Brief structured output", fill=wave2)


        # ── ROW 9: Delivery Layer ──
        y10 = row_y(9)
        del_h = 34
        arrow(W/2, y9, y10 + del_h)
        del_w = W - 40  # fill width
        c.setFillColor(accent)
        c.setStrokeColor(border)
        c.setLineWidth(0.8)
        c.roundRect((W - del_w)/2, y10, del_w, del_h, 4, fill=1, stroke=1)
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(W/2, y10 + 22, "Delivery Layer")
        c.setFont("Helvetica", 5.5)
        c.setFillColor(HexColor("#555555"))
        c.drawCentredString(W/2, y10 + 12,
            "Gmail (welcome + invoice) | 4 Slack channels | HubSpot (log)")
        c.drawCentredString(W/2, y10 + 4,
            "Retry 3\u00d7 (1s/3s/9s) | Idempotency | Failure gate aborts all")

        # ── ROW 10: PDF Package ──
        y11 = row_y(10)
        arrow(W/2, y10, y11 + bh)
        box((W - cw - 40)/2, y11, cw + 40, bh,
            "PDF Handoff Package",
            "3 branded PDFs (Brief + Plan + Kickoff) \u2192 email to CSM", fill=accent)


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
            "Webhook: Deal Record (JSON)", fill=accent)

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

        # 3b. Feature Scaling (right)
        box(right_x - bw/2, embed_y, bw, bh,
            "Feature Scaling",
            "StandardScaler \u2192 54D vector")

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
    """Draws the full agent pipeline matching actual code flow:
    ML Context → Analysis Agents → Enriched Context →
    Wave 1 (5 parallel) → Gate → Wave 2 (plan consumes brief) →
    Delivery → PDF Package."""

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
        agent_fill = HexColor("#e3ede8")
        wave2_fill = HexColor("#e8dce8")
        gate_color = HexColor("#f0dada")
        deliver_color = accent

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

        def small_box(x, y, w, h, label, fill=agent_fill):
            c.setFillColor(fill)
            c.setStrokeColor(border)
            c.setLineWidth(1)
            c.roundRect(x, y, w, h, 4, fill=1, stroke=1)
            c.setFillColor(text_color)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawCentredString(x + w/2, y + h/2 - 3, label)

        def label(x, y, text, size=8, color=light_gray):
            c.setFont("Helvetica-Bold", size)
            c.setFillColor(color)
            c.drawString(x, y, text)

        top = self.height - 10
        left_x = W/2 - 110
        right_x = W/2 + 110
        bw = 190
        gap = 52
        bh = 36

        # Section title
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(text_color)
        c.drawCentredString(W/2, top, "Agent Orchestration & Delivery Layer")

        # ── ML Context Package ──
        ctx_y = top - 45
        ctx_w = 300
        box((W - ctx_w)/2, ctx_y, ctx_w, bh,
            "ML Context Package",
            "churn prob + SHAP factors + 5 neighbors + risk tier", fill=accent)

        # ── Analysis Agents (parallel) ──
        qa_y = ctx_y - gap
        mid_y = ctx_y - (gap - bh) / 2

        # Split arrows
        c.setStrokeColor(border)
        c.setLineWidth(1.2)
        c.line(W/2, ctx_y, W/2, mid_y)
        c.line(W/2, mid_y, left_x, mid_y)
        c.line(left_x, mid_y, left_x, qa_y + bh + 6)
        c.line(W/2, mid_y, right_x, mid_y)
        c.line(right_x, mid_y, right_x, qa_y + bh + 6)
        for ax in [left_x, right_x]:
            c.setFillColor(border)
            p = c.beginPath()
            p.moveTo(ax, qa_y + bh)
            p.lineTo(ax - 4, qa_y + bh + 8)
            p.lineTo(ax + 4, qa_y + bh + 8)
            p.close()
            c.drawPath(p, fill=1)

        box(left_x - bw/2, qa_y, bw, bh,
            "Q&A History Agent", "Pure Python \u2192 structured Q&A", fill=analysis_color)
        box(right_x - bw/2, qa_y, bw, bh,
            "Risk Narrative Agent", "LLM \u2192 plain-English risk story", fill=analysis_color)

        # ── Enriched Context ──
        enrich_y = qa_y - gap
        arrow_down(left_x, qa_y, enrich_y + bh)
        arrow_down(right_x, qa_y, enrich_y + bh)

        enrich_w = 320
        box((W - enrich_w)/2, enrich_y, enrich_w, bh,
            "Enriched Context Package",
            "deal + ML context + Q&A history + risk narrative", fill=accent)

        # ── WAVE 1: 5 agents in parallel ──
        w1_y = enrich_y - 58
        label(10, w1_y + 50, "WAVE 1", 9, text_color)
        label(10, w1_y + 40, "(parallel)", 7, light_gray)

        arrow_down(W/2, enrich_y, w1_y + 30 + 6)

        # 5 agent boxes in a row
        aw = 82
        ah = 30
        total_w = 5 * aw + 4 * 6
        start_x = (W - total_w) / 2
        w1_agents = ["Welcome\nEmail", "Slack\nAnnounce", "CSM\nBrief", "Kickoff\nDraft", "CRM\nUpdates"]
        for i, name in enumerate(w1_agents):
            bx = start_x + i * (aw + 6)
            small_box(bx, w1_y, aw, ah, name.split('\n')[0], fill=agent_fill)
            # Second line
            c.setFont("Helvetica", 6.5)
            c.setFillColor(light_gray)
            parts = name.split('\n')
            if len(parts) > 1:
                c.drawCentredString(bx + aw/2, w1_y + 5, parts[1])

        # Horizontal line connecting all 5
        c.setStrokeColor(border)
        c.setLineWidth(1)
        line_y = w1_y + ah + 4
        c.line(start_x + aw/2, line_y, start_x + 4*(aw+6) + aw/2, line_y)
        # Vertical drop from center to line
        c.line(W/2, w1_y + ah + 4, W/2, w1_y + ah + 10)

        # ── Failure Gate ──
        gate_y = w1_y - 26
        gate_w = 200
        box((W - gate_w)/2, gate_y, gate_w, 22,
            "Any agent failed? \u2192 Abort all delivery", fill=gate_color)
        arrow_down(W/2, w1_y, gate_y + 22)

        # ── WAVE 2: Success Plan (consumes CSM Brief) ──
        w2_y = gate_y - 48
        label(10, w2_y + 38, "WAVE 2", 9, text_color)
        label(10, w2_y + 28, "(sequential)", 7, light_gray)

        arrow_down(W/2, gate_y, w2_y + bh)

        box((W - 280)/2, w2_y, 280, bh,
            "30-Day Success Plan Agent",
            "Consumes CSM Brief structured output (Wave 2)", fill=wave2_fill)

        # Dashed arrow from CSM Brief to Success Plan (dependency)
        brief_center_x = start_x + 2 * (aw + 6) + aw/2  # CSM Brief is 3rd box
        c.setStrokeColor(HexColor("#8866aa"))
        c.setLineWidth(1)
        c.setDash([4, 3])
        # Curve from brief down-right to plan
        c.line(brief_center_x, w1_y, brief_center_x, w2_y + bh + 12)
        c.line(brief_center_x, w2_y + bh + 12, (W - 280)/2 + 40, w2_y + bh + 12)
        c.line((W - 280)/2 + 40, w2_y + bh + 12, (W - 280)/2 + 40, w2_y + bh + 4)
        c.setDash([])
        # Label the dependency
        c.setFont("Helvetica-Oblique", 6.5)
        c.setFillColor(HexColor("#8866aa"))
        c.drawString(brief_center_x + 3, w2_y + bh + 14, "structured JSON")

        # ── Delivery Layer ──
        del_y = w2_y - 48
        arrow_down(W/2, w2_y, del_y + 38)

        del_w = 380
        c.setFillColor(deliver_color)
        c.setStrokeColor(border)
        c.setLineWidth(1.2)
        c.roundRect((W - del_w)/2, del_y, del_w, 38, 6, fill=1, stroke=1)
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W/2, del_y + 24, "Delivery Layer")
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#555555"))
        c.drawCentredString(W/2, del_y + 12,
            "Gmail (welcome + invoice) | 4 Slack channels (Block Kit) | HubSpot (log)")
        c.drawCentredString(W/2, del_y + 3,
            "Retry 3\u00d7 backoff (1s/3s/9s) | Idempotency via _completed.json")

        # ── PDF Package ──
        pdf_y = del_y - 44
        arrow_down(W/2, del_y, pdf_y + 35)

        pdf_w = 340
        c.setFillColor(deliver_color)
        c.setStrokeColor(border)
        c.setLineWidth(1.2)
        c.roundRect((W - pdf_w)/2, pdf_y, pdf_w, 35, 6, fill=1, stroke=1)
        c.setFillColor(text_color)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(W/2, pdf_y + 21, "PDF Handoff Package")
        c.setFont("Helvetica", 7)
        c.setFillColor(HexColor("#555555"))
        c.drawCentredString(W/2, pdf_y + 9,
            "3 branded PDFs (Brief + Plan + Kickoff) \u2192 bundled email to CSM")

# ─── CONFIG ───────────────────────────────────────────────────────────
OUTPUT_FILE = "part1_brief.pdf"
TITLE = "AskElephant: GTM Engineer Pre-Work"
AUTHOR = "Morgan Cooper, M.S."
DATE = "April 2026"

FONT_BODY = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_ITALIC = "Helvetica-Oblique"
FONT_BOLD_ITALIC = "Helvetica-BoldOblique"
FONT_SIZE = 11
LEADING = 15
MARGIN = 0.75 * inch
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
        "source": "Product description: data enrichment and outbound prospecting platform",
        "url": "https://www.clay.com",
    },
    {
        "id": 10,
        "person": "11x",
        "title": "",
        "company": "11x",
        "source": "Product description: AI-powered autonomous SDR platform",
        "url": "https://www.11x.ai",
    },
    {
        "id": 11,
        "person": "Cognism",
        "title": "",
        "company": "Cognism",
        "source": "State of Cold Calling Report: cold call success rates dropped from 4.82% to 2.3%",
        "url": "https://www.cognism.com/blog/cold-calling-success-rates",
    },
    {
        "id": 12,
        "person": "Landbase",
        "title": "",
        "company": "Landbase (citing Gartner)",
        "source": "B2B contact data accuracy: 70% of CRM data is outdated, incomplete, or inaccurate",
        "url": "https://www.landbase.com/blog/b2b-contact-data-accuracy-statistic",
    },
    {
        "id": 13,
        "person": "Gartner",
        "title": "",
        "company": "Gartner",
        "source": "Data quality research: poor data costs organizations $12.9\u201315M annually",
        "url": "https://www.gartner.com/en/data-analytics/topics/data-quality",
    },
    {
        "id": 14,
        "person": "Salesforce",
        "title": "",
        "company": "Salesforce",
        "source": "2024 State of Sales Report: reps spend 70% of time on non-selling tasks",
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
    story.append(Spacer(1, 16))
    story.append(Paragraph(
        '<b>GitHub:</b> '
        '<a href="https://github.com/cooper-rm/GTM-AskElephant" color="#2C5CE8">'
        'cooper-rm/GTM-AskElephant</a>',
        s["DocSubtitle"]
    ))
    story.append(PageBreak())

    # ── Outside-In Read ──
    story.append(Paragraph(
        "Outside-In Read", s["DocTitle"]
    ))
    story.append(Spacer(1, 8))

    # ── Question 1 ──
    story.append(Paragraph(
        "1. Who does AskElephant sell to?", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "Based on AskElephant\u2019s public customer base, the current core is "
        "clearly SMB: sales and CS leaders at 20\u2013100 person B2B "
        "companies running HubSpot, with heavy concentration in the HubSpot "
        "ecosystem itself " + ref(4) + ". There\u2019s a mild tilt toward "
        "mid-market (100\u20131,000 employees) with customers like Finally, "
        "Copper, Peddle, and ITS already on the platform " + ref(5) + ", and "
        "signals that a GTM play targeting mid-market is in motion. That\u2019s "
        "where the real opportunity lives: companies that use technology daily "
        "but don\u2019t have the technical depth to build automation themselves, "
        "with distinct sales, CS, implementation, and RevOps teams that create 50+ seat "
        "expansion opportunities. The trigger is post-call-recorder "
        "disillusionment: these teams adopted Fathom and Fireflies for "
        "recording but nobody is closing the loop from transcript to CRM "
        "update, follow-up, and pipeline accuracy, automatically "
        + ref(1) + ref(2) + ref(3) + ".",
        s["Body"],
    ))

    # ── Question 2 ──
    story.append(Paragraph(
        "2. What is AskElephant actually building?", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "AskElephant is building autonomous infrastructure that captures, "
        "routes, and acts on revenue data end-to-end. Automation is the "
        "product, AI is the engine. It starts with the call, but the value is everything "
        "that happens after: CRM fields written, follow-ups drafted, next "
        "steps pushed, forecasts updated, handoffs generated, all without a "
        "rep touching it. Today, every competitor owns a slice: Gong owns "
        "conversation intelligence but charges enterprise prices and struggles "
        "with accurate CRM field writes " + ref(6) + ref(7) + ref(8)
        + "; Fathom and Fireflies own the transcript but the data stays in a "
        "silo " + ref(3) + "; Clay " + ref(9) + " and 11x " + ref(10)
        + " own pre-sale prospecting and outbound; Clari owns forecasting but "
        "reads from the same dirty CRM data everyone else ignores. AskElephant "
        "is positioning to own the entire revenue operations layer: pre-sale, "
        "active selling, and and post-sale. Not just the connective tissue between "
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
        "collapsed 52% in a single year, from 4.82% to 2.3% "
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
        "rep\u2019s time goes to non-selling tasks. 54% of the workweek is "
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
        "AskElephant\u2019s current story is \u201cAI automation for revenue teams.\u201d "
        "The problem is that every tool in this space says the same thing. "
        "What actually makes AskElephant defensible isn\u2019t the automation "
        "itself. Data is now incredibly cheap to acquire. The value is in "
        "the analysis. If you automate revenue work and collect structured "
        "data in the process, you get compounding insights that no one else "
        "has: which objections predict churn, which onboarding patterns drive "
        "expansion, which deal shapes close fastest by segment. Those insights "
        "feed better automations, which collect richer data, which surface "
        "sharper insights. That\u2019s a flywheel, not a feature.",
        s["Body"],
    ))
    story.append(Paragraph(
        "What I\u2019d change: position AskElephant around the insights that "
        "only exist because the automation is running. A VP of Sales doesn\u2019t "
        "cancel a product that tells them something about their pipeline they "
        "couldn\u2019t see without it. I\u2019d make every customer-facing touchpoint "
        "reinforce that: the dashboards show insight, the reports quantify "
        "what changed, the QBR deck writes itself from the data the system "
        "already collected. Without that focus, AskElephant is competing on "
        "execution speed. With it, every deal that runs through the system "
        "makes the next one smarter, and the customer feels that.",
        s["Body"],
    ))

    # ── Part 2: Motion Pick ──
    story.append(Paragraph(
        "Selected Motion: Closed-Won Handoff", s["SectionHeader"]
    ))
    story.append(Paragraph(
        "I ruled out Motion A due to external data access. Mapping a buying "
        "committee requires LinkedIn, Apollo, and ZoomInfo, all paywalled or "
        "rate-limited. Building the system would mean fighting data access, not "
        "demonstrating architecture. Motion B requires time series anomaly "
        "detection to identify when and why a deal went dark. That needs "
        "sequential activity data that\u2019s difficult to synthesize synthetically, "
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
        "The ML models make the judgment calls. An XGBoost churn classifier "
        "scores risk with SHAP explainability, and an HNSW-indexed embedding "
        "space retrieves historically similar deals with their actual outcomes "
        "as grounded context for agents. The HNSW parameter tuning draws on my "
        "own published research on capacity-limited failure in approximate "
        "nearest neighbor search " + ref(15) + ". The agents are downstream: "
        "every LLM call receives real data as context, scored features, SHAP "
        "explanations, neighbor outcomes, structured Q&A, so it generates from "
        "evidence, not hallucination.",
        s["Body"],
    ))
    story.append(Paragraph(
        "The difference between this system looking correct and being correct: "
        "if any agent fails, the pipeline aborts all delivery before a broken "
        "artifact reaches a customer. Every prediction is calibrated against "
        "empirical churn rates, not raw model output. And the system knows what "
        "it doesn\u2019t know. Feature drift monitoring, negative-space assertions, "
        "and retry logic with exponential backoff are what separate a working "
        "demo from a production system you\u2019d trust with real customers.",
        s["Body"],
    ))

    # ── Design Doc: Architecture (single-page unified diagram) ──
    story.append(PageBreak())
    story.append(UnifiedPipelineDiagram())

    # ── Design Note: Written Sections ──
    story.append(PageBreak())
    story.append(Paragraph(
        "Design Notes", s["DocTitle"]
    ))
    story.append(Spacer(1, 8))

    story.append(Paragraph(
        "LLMs hallucinate without grounded context, and ML scores are useless to CSMs "
        "without proper packaging. This pipeline solves both. XGBoost and HNSW provide "
        "the data foundation that keeps agents honest, while structured delivery transforms "
        "predictions into artifacts a CSM can actually act on.",
        s["Body"]
    ))

    story.append(Paragraph("Data Sources", s["SectionHeader"]))
    story.append(Paragraph(
        "1,000 synthetic deals were generated using stochastic distributions "
        "(Dirichlet for segments, beta for pricing, gamma for cycle length, "
        "geometric for SDR attempts, Poisson for stakeholders, logistic for "
        "outcomes) to simulate realistic CRM data with known ground truth. "
        "Each deal includes company profile, deal terms, stakeholder roster, "
        "and full touch history with AI-processed call summaries, Q&A exchanges, "
        "objections, and sentiment labels. These records are then passed through "
        "a feature engineering step that derives 54 features across six categories "
        ": deal, people, touch patterns, response behavior, engagement signals, "
        "and company and company profile, before entering the ML pipeline. At inference, "
        "the engineered features feed XGBoost (churn prediction + SHAP explanations) "
        "and HNSW (nearest-neighbor retrieval) simultaneously. The ML outputs are "
        "then injected into agent prompts as structured context, with a two-hop "
        "chain (deal \u2192 brief \u2192 plan) that keeps downstream agents grounded "
        "rather than hallucinating.",
        s["Body"]))

    story.append(Paragraph("Judgment Calls", s["SectionHeader"]))
    story.append(Paragraph(
        "The core architectural decision: why not just hand the deal JSON to an LLM "
        "and ask it to assess risk and write the handoff? Three reasons. First, LLMs "
        "can\u2019t do statistical inference. Churn probability requires a trained "
        "classifier on historical outcomes, not pattern-matching on a single deal\u2019s "
        "text. An LLM asked \u201chow risky is this deal?\u201d will produce plausible-sounding "
        "reasoning with no predictive validity. XGBoost trained on 990 labeled outcomes "
        "gives a calibrated probability; SHAP makes it explainable. Second, LLMs have "
        "no access to your deal corpus. They can\u2019t say \u201c3 of 5 similar deals "
        "churned, all from low-adoption\u201d because they\u2019ve never seen your data. HNSW "
        "retrieval solves this: real neighbor outcomes grounded in real history, not "
        "hallucinated comparisons. Third, feature engineering catches signals LLMs miss "
        "entirely: sentiment trend (enthusiasm fading late), touch frequency "
        "acceleration (deal momentum slowing), single-threaded champion risk. These are "
        "derived mathematically from the touch sequence, not inferred from vibes.",
        s["Body"]))
    story.append(Paragraph(
        "The LLM IS the right tool, but only after it\u2019s been given the right "
        "context. Agents consume ML outputs (risk tier, SHAP factors, neighbor stories) "
        "as structured prompt context, not raw deal JSON. The result: agents that write "
        "like humans but reason from data.",
        s["Body"]))

    story.append(Paragraph("Unsupervised vs. Human-in-the-Loop", s["SectionHeader"]))
    story.append(Paragraph(
        "The pipeline currently runs fully autonomous. One webhook, one pass, "
        "all artifacts delivered. No human approval gates. This is a deliberate "
        "choice for the demo, but the architecture cleanly separates where you\u2019d "
        "add gates in production. Internal artifacts (Slack announcement, CSM brief, "
        "CRM updates, success plan) are safe to auto-send. They go to your own "
        "team, worst case a CSM sees a mediocre brief and mentally discards it. The "
        "kickoff draft is already designed as a human-in-the-loop artifact. It "
        "posts to a Slack channel as a draft the CSM copies, edits, and sends "
        "manually. It never reaches the customer without a human choosing to send it. "
        "The welcome email is the riskiest artifact. It auto-sends directly to "
        "the customer. In production, high-risk deals (elevated/high churn tier) "
        "should hold the welcome email for CSM review before delivery. The gate "
        "logic is trivial: check risk_tier before calling send_email, but the "
        "judgment call is where to set the threshold. Too aggressive and you slow "
        "down every handoff. Too loose and a hallucinated email reaches a $50K "
        "customer. Start with gating only on high-risk + large-deal combinations, "
        "measure CSM override rate, and loosen as trust builds.",
        s["Body"]))

    story.append(Paragraph("What Fails at Scale", s["SectionHeader"]))
    story.append(Paragraph(
        "No real database. All artifacts persist as JSON files on an ephemeral "
        "filesystem (Heroku wipes on restart). Works for demo; breaks at volume. "
        "Needs Postgres for run state and S3 for PDFs. No test suite covering edge "
        "cases: missing fields, null stakeholders, zero-touch deals, and malformed "
        "webhook payloads would surface bugs we haven\u2019t seen yet. Minimal error "
        "handling beyond the agent-failure gate. No type assertions on feature "
        "engineering inputs, no schema validation on LLM JSON responses beyond "
        "try/parse/fallback. Real CRM data is messy: missing fields, inconsistent "
        "date formats, partial touch records. The pipeline has no imputation step "
        ". It assumes clean structured input because the synthetic data is clean. "
        "Feature drift is invisible. If the deal mix shifts (new industry, "
        "different price points, larger companies), the model degrades silently "
        "with no monitoring to trigger a retrain. The HNSW index must be rebuilt "
        "when new deals close, and rebuild cost grows with corpus size. A managed "
        "vector database (Pinecone, Weaviate) would handle incremental updates "
        "without full reindexing. At volume, LLM rate limits and single-dyno "
        "processing become bottlenecks requiring a job queue.",
        s["Body"]))

    story.append(Paragraph("What We'd Harden in v2", s["SectionHeader"]))
    story.append(Paragraph(
        "Postgres + S3 replaces the filesystem. Deal state, delivery receipts, "
        "and audit logs in Postgres; PDFs and artifact blobs in S3. This makes the "
        "pipeline stateless and horizontally scalable. Schema validation at the "
        "webhook boundary using Pydantic models. Reject malformed deals before "
        "they enter the pipeline instead of discovering missing fields mid-agent. "
        "Data imputation layer between raw CRM ingest and feature engineering. "
        "handles nulls, normalizes date formats, fills missing tenure with segment "
        "medians, flags records too incomplete to score. Drift monitoring on the 54 "
        "input features. Track distributions weekly against the training baseline, "
        "alert when KL divergence crosses a threshold, auto-trigger retrain when the "
        "calibration buckets go stale. Replace HNSW flat index with a managed vector "
        "database (Pinecone or Weaviate) that supports incremental upserts as new "
        "deals close. No full reindex needed. Add a job queue (Redis + Celery or "
        "SQS) so the webhook enqueues work and returns immediately. Multiple "
        "workers process deals in parallel without blocking. Active learning loop: "
        "when a CSM edits a brief or plan before sending, capture the diff as "
        "training signal for prompt refinement. Per-industry model variants once "
        "deal volume supports it. A SaaS deal and a healthcare deal have different "
        "churn drivers that a single model blurs together. "
        "Negative-space programming throughout the pipeline: assertions at every "
        "boundary (feature engineering outputs contain no NaNs, LLM JSON responses "
        "match the expected schema, deal records have all required fields) so invalid "
        "state crashes immediately with a clear message instead of propagating silently "
        "and producing garbage artifacts three steps later.",
        s["Body"]))

    # ── Part 4: First 90 Days ──
    story.append(PageBreak())
    story.append(Paragraph(
        "First 90 Days", s["DocTitle"]
    ))
    story.append(Spacer(1, 12))

    # AI Automation #1
    story.append(Paragraph(
        "AI Automation #1: Data Engineer (Week 1 Priority)",
        s["SectionHeader"]
    ))
    story.append(Paragraph(
        "The first thing I\u2019d build is an automated data engineering layer. "
        "AskElephant sits on a massive volume of call recordings, CRM interactions, "
        "deal histories, and customer touchpoints, but raw data isn\u2019t usable data. "
        "This automation would parse AskElephant\u2019s entire data history, extract "
        "structured features from unstructured sources (call transcripts, email "
        "threads, CRM notes), engineer derived signals (sentiment trends, engagement "
        "patterns, objection clusters), and store everything in a queryable, "
        "model-ready format. Without this, every downstream system is guessing. The "
        "churn models have nothing to train on. ICP definition is gut feel instead "
        "of data-driven segmentation because nobody has structured the historical "
        "win/loss patterns well enough to say which customers actually succeed. The "
        "agents have no grounded context to reference. The insight flywheel from Q4 "
        "never starts spinning. This is week one because it\u2019s the foundation "
        "everything else depends on.",
        s["Body"]))
    story.append(Spacer(1, 10))

    # AI Automation #2
    story.append(Paragraph(
        "AI Automation #2: Deal Intelligence",
        s["SectionHeader"]
    ))
    story.append(Paragraph(
        "Once the data layer exists, the next automation tracks active deals in "
        "real-time. This system monitors engagement signals throughout the sales "
        "cycle: sentiment shifts across touches, stakeholder involvement patterns, "
        "objection frequency and resolution, response time trends, and competitive "
        "mentions. It surfaces \u201cread between the lines\u201d insights to AEs while "
        "the deal is still open. When a champion\u2019s engagement drops or a technical "
        "evaluator raises the same objection twice, the system flags it before the "
        "AE notices. The real value: by the time a deal hits closed-won, the system "
        "already understands the stakeholder dynamics, knows which objections were "
        "parked versus resolved, and has a sentiment trajectory across the full "
        "cycle. The handoff doesn\u2019t start from scratch. It packages what the deal "
        "intelligence layer already learned.",
        s["Body"]))
    story.append(Spacer(1, 10))

    # AI Automation #3
    story.append(Paragraph(
        "AI Automation #3: Closed-Won Handoff (Shipped)",
        s["SectionHeader"]
    ))
    story.append(Paragraph(
        "This is the automation I built for this exercise. It triggers on a "
        "closed-won webhook, scores churn risk with XGBoost and SHAP, retrieves "
        "similar historical deals via HNSW, runs four analysis agents that read "
        "between the lines of the sales cycle (Q&A insights, objection signals, "
        "neighbor patterns, risk narrative), then produces six handoff artifacts "
        "delivered to real Slack channels and Gmail. The 30-day success plan "
        "consumes the CSM brief\u2019s structured output so it references specific "
        "people and known concerns rather than generating generic onboarding "
        "steps. It works end-to-end today, deployed on Heroku, accepting deal "
        "JSON via webhook. In the full 90-day vision, this automation gets "
        "dramatically better because automations #1 and #2 have already "
        "structured the data and tracked the deal. The handoff becomes a "
        "packaging step, not a discovery step.",
        s["Body"]))

    # ── Part 5: Your One Question ──
    story.append(PageBreak())
    story.append(Paragraph(
        "Part 5: Your One Question", s["DocTitle"]
    ))
    story.append(Spacer(1, 12))

    story.append(Paragraph("The Question", s["SectionHeader"]))
    story.append(Paragraph(
        "I took a non-traditional path to get here: years of sales, engineering, "
        "built a company, data science and published ML research. "
        "What about that combination are you actually hiring for?",
        s["Body"]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("What the Answer Would Change", s["SectionHeader"]))
    story.append(Paragraph(
        "I would want to hear them articulate what they think this unique combination "
        "is worth. If they value the full-stack engineering, ML, and sales "
        "intuition, then this role has a trajectory I\u2019d be excited about: owning "
        "and scaling a data-rooted revenue system. If they mostly see the sales "
        "background and think my technical skills are a bonus, then we\u2019re likely "
        "misaligned on what I specialize in and what the role is worth.",
        s["Body"]))

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
