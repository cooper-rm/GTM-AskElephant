"""
30-Day Success Plan → PDF.

Consumes success_plan.structured + deal info. Risk info lives exclusively
in the CSM brief; the plan stays action-focused.
"""
import io

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from . import pdf_theme as T


def generate_plan_pdf(deal: dict, structured: dict) -> bytes:
    company = deal['company']
    deal_info = deal['deal']
    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"

    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(deal_info.get('product_tier', ''), deal_info.get('product_tier', ''))

    buf = io.BytesIO()
    doc = T.make_doc(buf, title=f"30-Day Success Plan · {company['name']}")
    st = T.styles()

    story = []

    # ── Cover page ────────────────────────────────────────────────────────
    story += T.cover_page(
        kicker="30-Day Success Plan · Recommendation",
        company_name=company['name'],
        subtitle=f"Use case: {deal_info.get('use_case', '—')}",
        meta_pairs=[
            ('ACV', acv_str),
            ('Seats', str(deal_info.get('seats', 0))),
            ('Plan', tier_label),
            ('Segment', (company.get('segment') or '—').upper()),
        ],
        prepared_for=(
            f"Prepared for Customer Success  ·  Deal "
            f"{deal_info.get('deal_id') or deal.get('deal_id', '—')}"
        ),
    )

    # ── Success criteria (inside pages) ──────────────────────────────────
    # Risk info lives in the brief (hero badge + Risk Assessment section).
    # The plan's cadence is already calibrated — no need to re-display risk here.
    story.append(Paragraph("Success Criteria", st['h1']))
    story.append(Spacer(1, 0.1 * inch))
    story.append(_criteria_banner(structured.get('success_criteria', 'TBD')))
    story.append(Spacer(1, 0.35 * inch))

    # ── Week-by-week ──────────────────────────────────────────────────────
    story.append(T.section_header("Week-by-Week Plan"))
    story.append(Spacer(1, 0.18 * inch))

    week_specs = [
        ('week_1', 1, 'Days 1–7'),
        ('week_2', 2, 'Days 8–14'),
        ('week_3', 3, 'Days 15–21'),
        ('week_4', 4, 'Days 22–30'),
    ]
    for key, num, date_range in week_specs:
        story.append(_week_card(num, date_range, structured.get(key, {}) or {}))
        story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    return buf.getvalue()


# ── Components ────────────────────────────────────────────────────────────

def _criteria_banner(text: str) -> Table:
    kicker = ParagraphStyle(
        'crit_kicker', fontName='Helvetica-Bold', fontSize=9,
        textColor=T.ACCENT_DARK, leading=11, spaceAfter=4,
    )
    body = ParagraphStyle(
        'crit_body', fontName='Helvetica-Oblique', fontSize=11.5,
        textColor=T.INK, leading=15,
    )
    inner = [
        [Paragraph("SUCCESS CRITERIA", kicker)],
        [Paragraph(T.html_escape(text), body)],
    ]
    t = Table(inner, colWidths=[6.75 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.ACCENT_TINT),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LINEBEFORE', (0, 0), (0, -1), 3, T.ACCENT),
    ]))
    return t


def _week_card(num: int, date_range: str, week: dict):
    # Header strip: "Week 1 · focus · Days 1-7"
    label_style = ParagraphStyle(
        'week_head', fontName='Helvetica-Bold', fontSize=12,
        textColor=colors.white, leading=15,
    )
    range_style = ParagraphStyle(
        'week_range', fontName='Helvetica', fontSize=9,
        textColor=colors.white, leading=11, alignment=2,  # right
    )
    focus = week.get('focus', '')

    head = Table(
        [[
            Paragraph(f"<b>Week {num}</b>&nbsp;&nbsp;·&nbsp;&nbsp;{T.html_escape(focus)}", label_style),
            Paragraph(date_range, range_style),
        ]],
        colWidths=[4.5 * inch, 2.25 * inch],
    )
    head.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.ACCENT),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    gate_label_style = ParagraphStyle(
        'gate_label', fontName='Helvetica-Bold', fontSize=8.5,
        textColor=T.MUTED, leading=11, spaceAfter=2,
    )
    gate_body_style = ParagraphStyle(
        'gate_body', fontName='Helvetica', fontSize=10, textColor=T.INK, leading=13,
    )
    owner_body_style = ParagraphStyle(
        'owner_body', fontName='Helvetica', fontSize=10, textColor=T.INK, leading=13,
    )

    gate_text = week.get('gate', '')
    owner = week.get('owner', 'CSM')

    gate_cell = [
        Paragraph("GATE", gate_label_style),
        Paragraph(T.html_escape(gate_text), gate_body_style),
    ]
    owner_cell = [
        Paragraph("OWNER", gate_label_style),
        Paragraph(T.html_escape(owner), owner_body_style),
    ]

    gate_table = Table(
        [[gate_cell, owner_cell]],
        colWidths=[4.75 * inch, 2 * inch],
    )
    gate_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('BACKGROUND', (0, 0), (-1, -1), T.CARD_BG),
    ]))

    bullet_style = ParagraphStyle(
        'bullet', fontName='Helvetica', fontSize=10,
        textColor=T.INK, leading=14, leftIndent=6, spaceAfter=2,
    )

    def _list_cell(kicker: str, items: list) -> list:
        out = [Paragraph(kicker, gate_label_style)]
        for item in items:
            out.append(Paragraph(
                f"•&nbsp;&nbsp;{T.html_escape(item)}",
                bullet_style,
            ))
        return out

    # Activities (full width row)
    activities = (week.get('activities') or [])[:4]
    if activities:
        act_cell = _list_cell("ACTIVITIES", activities)
        act_table = Table([[act_cell]], colWidths=[6.75 * inch])
        act_table.setStyle(TableStyle([
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, 0), (-1, -1), T.CARD_BG),
        ]))
    else:
        act_table = Spacer(1, 0)

    # Stakeholders + Expected outputs (2-column row)
    stakeholders = (week.get('customer_stakeholders') or [])[:3]
    outputs = (week.get('expected_outputs') or [])[:3]
    bottom_table = None
    if stakeholders or outputs:
        left = _list_cell("CUSTOMER STAKEHOLDERS", stakeholders) if stakeholders else [
            Paragraph("CUSTOMER STAKEHOLDERS", gate_label_style),
            Paragraph("<i>—</i>", ParagraphStyle('dash', parent=bullet_style, textColor=T.MUTED)),
        ]
        right = _list_cell("EXPECTED OUTPUTS", outputs) if outputs else [
            Paragraph("EXPECTED OUTPUTS", gate_label_style),
            Paragraph("<i>—</i>", ParagraphStyle('dash2', parent=bullet_style, textColor=T.MUTED)),
        ]
        bottom_table = Table(
            [[left, right]],
            colWidths=[3.375 * inch, 3.375 * inch],
        )
        bottom_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), T.CARD_BG),
            ('LINEBEFORE', (1, 0), (1, -1), 0.5, T.CARD_BORDER),
        ]))

    # Combine head + gate + activities + bottom row inside a bordered wrapper
    rows = [[head], [gate_table], [act_table]]
    if bottom_table is not None:
        rows.append([bottom_table])
    wrap = Table(
        rows,
        colWidths=[6.75 * inch],
    )
    wrap.setStyle(TableStyle([
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('BOX', (0, 0), (-1, -1), 0.5, T.CARD_BORDER),
    ]))
    return KeepTogether(wrap)


