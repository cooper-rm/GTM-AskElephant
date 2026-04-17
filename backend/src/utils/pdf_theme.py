"""
AskElephant brand theme for handoff-package PDFs.

Design language (derived from askelephant.ai):
  - Ink near-black on white
  - Bright SaaS blue accent (#2C5CE8)
  - Bold sans-serif headings, generous whitespace
  - Minimal chrome — no decorative bars; one hairline rule
  - Dedicated cover page per document; content starts on page 2

Exports:
  - Colors and paragraph styles
  - make_doc()         → branded document with cover + inside page templates
  - cover_page()       → full-page hero cover (flowables)
  - section_header()   → section title with colored sidebar
  - risk_badge()       → stat-card risk badge
  - card()             → light-bg card for grouped content
  - bullet_list()      → native-feeling bullet paragraphs
  - html_escape()      → safe for reportlab Paragraph text
"""
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak,
    NextPageTemplate,
)


# ── AskElephant palette ────────────────────────────────────────────────────

ACCENT = colors.HexColor('#2C5CE8')          # bright SaaS blue
ACCENT_DARK = colors.HexColor('#1E3FA6')     # deeper blue for accents
ACCENT_TINT = colors.HexColor('#EEF2FE')     # very light blue — card bg

INK = colors.HexColor('#111111')             # near-black body / titles
INK_2 = colors.HexColor('#2A2A2A')           # slightly softer body
MUTED = colors.HexColor('#5E6578')           # metadata / muted labels
MUTED_LIGHT = colors.HexColor('#9AA0AE')     # footers / smallest
HAIRLINE = colors.HexColor('#E6E8EE')        # subtle borders
BORDER = HAIRLINE                             # alias for back-compat

CARD_BG = colors.HexColor('#FAFBFC')         # near-white card bg
CARD_BORDER = colors.HexColor('#EEF0F4')     # card border

# Risk palette — coherent with blue primary
GOOD = colors.HexColor('#0C7F5F')
GOOD_TINT = colors.HexColor('#E6F4EE')
WARN = colors.HexColor('#AF6B00')
WARN_TINT = colors.HexColor('#FBF1E0')
BAD = colors.HexColor('#B32531')
BAD_TINT = colors.HexColor('#FAE7E9')

RISK_COLORS = {
    'very_low': (GOOD, GOOD_TINT),
    'low':      (GOOD, GOOD_TINT),
    'average':  (WARN, WARN_TINT),
    'elevated': (WARN, WARN_TINT),
    'high':     (BAD,  BAD_TINT),
    'very_high': (BAD, BAD_TINT),
}


# ── Paragraph styles ───────────────────────────────────────────────────────

_ss = getSampleStyleSheet()


def styles() -> dict:
    """Return a fresh dict of styles."""
    return {
        # Cover page
        'cover_wordmark': ParagraphStyle(
            'cover_wordmark', parent=_ss['Normal'],
            fontName='Helvetica-Bold', fontSize=10, textColor=ACCENT,
            leading=12, spaceAfter=0,
        ),
        'cover_kicker': ParagraphStyle(
            'cover_kicker', parent=_ss['Normal'],
            fontName='Helvetica-Bold', fontSize=10, textColor=MUTED,
            leading=13, spaceAfter=6,
        ),
        'cover_title': ParagraphStyle(
            'cover_title', parent=_ss['Heading1'],
            fontName='Helvetica-Bold', fontSize=40, textColor=INK,
            leading=44, spaceAfter=8,
        ),
        'cover_subtitle': ParagraphStyle(
            'cover_subtitle', parent=_ss['Normal'],
            fontName='Helvetica', fontSize=13, textColor=MUTED,
            leading=18, spaceAfter=0,
        ),
        'meta_label': ParagraphStyle(
            'meta_label', parent=_ss['Normal'],
            fontName='Helvetica-Bold', fontSize=8, textColor=MUTED,
            leading=10, spaceAfter=2,
        ),
        'meta_value': ParagraphStyle(
            'meta_value', parent=_ss['Normal'],
            fontName='Helvetica-Bold', fontSize=13, textColor=INK,
            leading=16,
        ),
        # Inside page
        'h1': ParagraphStyle(
            'h1', parent=_ss['Heading1'],
            fontName='Helvetica-Bold', fontSize=22, textColor=INK,
            leading=26, spaceAfter=6, spaceBefore=0,
        ),
        'h3': ParagraphStyle(
            'h3', parent=_ss['Heading3'],
            fontName='Helvetica-Bold', fontSize=10.5, textColor=INK_2,
            leading=14, spaceAfter=4, spaceBefore=10,
        ),
        'body': ParagraphStyle(
            'body', parent=_ss['Normal'],
            fontName='Helvetica', fontSize=10.5, textColor=INK_2,
            leading=15, spaceAfter=4,
        ),
        'body_tight': ParagraphStyle(
            'body_tight', parent=_ss['Normal'],
            fontName='Helvetica', fontSize=10.5, textColor=INK_2,
            leading=14, spaceAfter=2,
        ),
        'muted': ParagraphStyle(
            'muted', parent=_ss['Normal'],
            fontName='Helvetica', fontSize=9, textColor=MUTED,
            leading=12, spaceAfter=2,
        ),
        'quote': ParagraphStyle(
            'quote', parent=_ss['Normal'],
            fontName='Helvetica-Oblique', fontSize=10.5, textColor=INK_2,
            leading=15, leftIndent=12, spaceAfter=4, spaceBefore=2,
        ),
        'bullet': ParagraphStyle(
            'bullet', parent=_ss['Normal'],
            fontName='Helvetica', fontSize=10.5, textColor=INK_2,
            leading=15, leftIndent=14, bulletIndent=2, spaceAfter=2,
        ),
        'email_body': ParagraphStyle(
            'email_body', parent=_ss['Normal'],
            fontName='Helvetica', fontSize=11, textColor=INK_2,
            leading=16, spaceAfter=6,
        ),
    }


# ── Document + page templates ──────────────────────────────────────────────

def make_doc(buf, title: str, author: str = 'AskElephant') -> BaseDocTemplate:
    """
    Build a document with two page templates:
      - 'cover'  : full-bleed clean page, no header/footer chrome
      - 'inside' : content pages with minimal typographic header + footer
    Use PageBreak or NextPageTemplate inside the story to switch.
    """
    doc = BaseDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.85 * inch, bottomMargin=0.75 * inch,
        title=title, author=author,
    )
    main_frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id='main', leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
    )
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[main_frame], onPage=_draw_cover_chrome),
        PageTemplate(id='inside', frames=[main_frame], onPage=_draw_inside_chrome),
    ])
    return doc


def _draw_cover_chrome(canvas, doc):
    """Cover page: intentionally blank — let the content breathe."""
    return


def _draw_inside_chrome(canvas, doc):
    """Inside pages: small typographic header + minimal footer."""
    w, h = LETTER

    # Thin hairline at top (below margin)
    canvas.setStrokeColor(HAIRLINE)
    canvas.setLineWidth(0.5)
    canvas.line(0.85 * inch, h - 0.55 * inch, w - 0.85 * inch, h - 0.55 * inch)

    # Wordmark (left)
    canvas.setFont('Helvetica-Bold', 8)
    canvas.setFillColor(ACCENT)
    canvas.drawString(0.85 * inch, h - 0.48 * inch, 'ASKELEPHANT')

    # Doc title (right)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(w - 0.85 * inch, h - 0.48 * inch, doc.title)

    # Footer: page number (centered) + date (right)
    canvas.setFont('Helvetica', 7.5)
    canvas.setFillColor(MUTED_LIGHT)
    today = datetime.now(timezone.utc).strftime('%b %d, %Y')
    canvas.drawString(0.85 * inch, 0.45 * inch, today)
    canvas.drawCentredString(w / 2, 0.45 * inch, f'{doc.page:02d}')
    canvas.drawRightString(w - 0.85 * inch, 0.45 * inch, 'AskElephant Confidential')


# ── Cover page ─────────────────────────────────────────────────────────────

def cover_page(
    kicker: str,
    company_name: str,
    subtitle: str,
    meta_pairs: "list[tuple[str, str]]",
    prepared_for: str = '',
) -> list:
    """
    Return a list of flowables for a dedicated cover page.

    Layout (top→bottom):
      [wordmark]
      [generous spacer]
      [kicker — document type]
      [company name — huge hero]
      [subtitle]
      [generous spacer]
      [hairline rule]
      [meta strip — key/value spec sheet]
      [hairline rule]
      [prepared_for caption]
      [PageBreak]
    """
    st = styles()
    out: list = []

    # Wordmark at top
    out.append(Paragraph('ASKELEPHANT', st['cover_wordmark']))
    out.append(Spacer(1, 2.1 * inch))

    # Kicker + title + subtitle — hero block
    out.append(Paragraph(kicker.upper(), st['cover_kicker']))
    out.append(Paragraph(html_escape(company_name), st['cover_title']))
    if subtitle:
        out.append(Paragraph(html_escape(subtitle), st['cover_subtitle']))

    out.append(Spacer(1, 1.6 * inch))

    # Hairline above meta strip
    out.append(_hairline_full_width())
    out.append(Spacer(1, 0.18 * inch))

    # Meta spec strip — 3-4 columns, label above value
    if meta_pairs:
        out.append(_meta_spec_strip(meta_pairs))
        out.append(Spacer(1, 0.18 * inch))
        out.append(_hairline_full_width())

    if prepared_for:
        out.append(Spacer(1, 0.25 * inch))
        out.append(Paragraph(prepared_for, st['muted']))

    # Switch to 'inside' template for subsequent pages
    out.append(NextPageTemplate('inside'))
    out.append(PageBreak())
    return out


def _meta_spec_strip(pairs: "list[tuple[str, str]]") -> Table:
    """Spec-sheet style row of key/value pairs, evenly distributed."""
    st = styles()
    cells = []
    for label, value in pairs:
        cells.append([
            Paragraph(label.upper(), st['meta_label']),
            Paragraph(html_escape(str(value)), st['meta_value']),
        ])
    col_w = 6.8 / max(len(pairs), 1) * inch
    t = Table([cells], colWidths=[col_w] * len(pairs))
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def _hairline_full_width() -> Table:
    """Thin hairline rule spanning the content width."""
    t = Table([['']], colWidths=[6.8 * inch], rowHeights=[0.5])
    t.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), HAIRLINE)]))
    return t


# ── Building-block helpers ────────────────────────────────────────────────

def section_header(label: str) -> Table:
    """
    Section header with accent left-bar — keeps a steady visual beat.
    """
    label_style = ParagraphStyle(
        'sec', fontName='Helvetica-Bold', fontSize=13.5,
        textColor=INK, leading=17,
    )
    t = Table(
        [[Paragraph(html_escape(label), label_style)]],
        colWidths=[6.8 * inch],
    )
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LINEBEFORE', (0, 0), (0, -1), 3, ACCENT),
    ]))
    return t


def risk_badge(tier: str, multiplier: float, churn_prob: float) -> Table:
    """
    Hero stat card: big multiplier number as visual anchor,
    tier label below, probability muted on the right.
    """
    tier_key = (tier or '').lower()
    fg, bg = RISK_COLORS.get(tier_key, (ACCENT_DARK, ACCENT_TINT))
    tier_label = tier_key.replace('_', ' ').upper()

    multiplier_style = ParagraphStyle(
        'mult', fontName='Helvetica-Bold', fontSize=38,
        textColor=fg, leading=40, alignment=TA_LEFT,
    )
    tier_style = ParagraphStyle(
        'tier', fontName='Helvetica-Bold', fontSize=9,
        textColor=fg, leading=11, alignment=TA_LEFT, spaceBefore=4,
    )
    label_style = ParagraphStyle(
        'lbl', fontName='Helvetica-Bold', fontSize=8, textColor=MUTED,
        leading=10, alignment=TA_RIGHT, spaceAfter=2,
    )
    val_style = ParagraphStyle(
        'val', fontName='Helvetica-Bold', fontSize=14, textColor=INK,
        leading=18, alignment=TA_RIGHT,
    )

    left_cell = [
        Paragraph(f"{multiplier:.1f}&times;", multiplier_style),
        Paragraph(f"{tier_label} CHURN RISK", tier_style),
    ]
    right_cell = [
        Paragraph("RISK LEVEL", label_style),
        Paragraph(f"{tier_label}", val_style),
        Spacer(1, 6),
        Paragraph("VS AVERAGE", label_style),
        Paragraph(f"{multiplier:.1f}\u00d7 churn rate", val_style),
    ]

    t = Table(
        [[left_cell, right_cell]],
        colWidths=[3.8 * inch, 3.0 * inch],
    )
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 18),
        ('RIGHTPADDING', (0, 0), (-1, -1), 18),
        ('TOPPADDING', (0, 0), (-1, -1), 16),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 16),
        ('LINEBEFORE', (0, 0), (0, -1), 3, fg),
    ]))
    return t


def card(title_flow, body_flows: list, bg=CARD_BG, border=CARD_BORDER) -> KeepTogether:
    """Light-background grouping container. Keeps title + body together."""
    inner = [[title_flow]] if title_flow is not None else [[]]
    inner += [[b] for b in body_flows]
    t = Table(inner, colWidths=[6.8 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg),
        ('BOX', (0, 0), (-1, -1), 0.5, border),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return KeepTogether(t)


def bullet_list(items: list, style=None) -> list:
    if style is None:
        style = styles()['bullet']
    return [
        Paragraph(f"•&nbsp;&nbsp;{html_escape(str(item))}", style)
        for item in items if item
    ]


def html_escape(s) -> str:
    if not s:
        return ''
    return (
        str(s).replace('&', '&amp;')
              .replace('<', '&lt;')
              .replace('>', '&gt;')
    )
