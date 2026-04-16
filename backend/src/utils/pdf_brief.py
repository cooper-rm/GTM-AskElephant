"""
CSM Handoff Brief → PDF.

Consumes csm_brief.structured (the LLM's JSON) + ml_context + deal info
and renders a multi-page, branded PDF matching the Block Kit brief.
"""
import io

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from . import pdf_theme as T


ROLE_ICON = {
    'champion': '★',
    'exec_sponsor': '◆',
    'technical_evaluator': '⚙',
    'economic_buyer': '$',
    'end_user': '•',
}


def generate_brief_pdf(deal: dict, ml_context: dict, structured: dict) -> bytes:
    company = deal['company']
    deal_info = deal['deal']
    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"

    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(deal_info.get('product_tier', ''), deal_info.get('product_tier', ''))

    buf = io.BytesIO()
    doc = T.make_doc(buf, title=f"CSM Handoff Brief · {company['name']}")
    st = T.styles()

    story = []

    # ── Cover page ────────────────────────────────────────────────────────
    story += T.cover_page(
        kicker="CSM Handoff Brief",
        company_name=company['name'],
        subtitle=(
            f"{company.get('industry', '—')}  ·  "
            f"{company.get('employee_count', 0)} employees  ·  "
            f"{(company.get('segment') or '').upper()}"
        ),
        meta_pairs=[
            ('ACV', acv_str),
            ('Seats', str(deal_info.get('seats', 0))),
            ('Plan', tier_label),
            ('Use case', deal_info.get('use_case', '—')),
        ],
        prepared_for=(
            f"Prepared for Customer Success  ·  Deal "
            f"{deal_info.get('deal_id') or deal.get('deal_id', '—')}"
        ),
    )

    # ── Inside pages start here ──────────────────────────────────────────
    ctx = structured.get('customer_context', {}) or {}

    # ── 1. Customer Context ───────────────────────────────────────────────
    story.append(T.section_header("1.  Customer Context"))
    story.append(Spacer(1, 0.14 * inch))

    if ctx.get('business_summary'):
        story.append(Paragraph(T.html_escape(ctx['business_summary']), st['body']))
        story.append(Spacer(1, 0.15 * inch))

    # Stakeholders — cap at 4 to match Slack rendering
    sm = (ctx.get('stakeholder_map') or [])[:4]
    if sm:
        story.append(Paragraph("Stakeholders", st['h3']))
        story.append(Spacer(1, 4))
        story.append(_stakeholder_table(sm))
        story.append(Spacer(1, 0.18 * inch))

    # Problems + solutions in 2 columns
    problems = (ctx.get('current_problems') or [])[:4]
    solutions = (ctx.get('solutions_delivered') or [])[:4]
    if problems or solutions:
        story.append(_two_column_lists(
            left_label="What they're solving",
            left_items=problems,
            right_label="What we're delivering",
            right_items=solutions,
        ))
        story.append(Spacer(1, 0.18 * inch))

    # Objections
    objs = (ctx.get('objections') or [])[:4]
    if objs:
        story.append(Paragraph("Objections & how they were handled", st['h3']))
        story.append(Spacer(1, 4))
        for o in objs:
            story.append(_objection_card(o))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 0.1 * inch))

    # Q&A highlights
    qas = (ctx.get('qa_highlights') or [])[:4]
    if qas:
        story.append(Paragraph("Key Q&A from sales", st['h3']))
        story.append(Spacer(1, 4))
        for q in qas:
            story.append(_qa_card(q))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 0.1 * inch))

    # Expectations
    exp = [e for e in (ctx.get('expectations_to_manage') or []) if e][:3]
    if exp:
        story.append(Paragraph("Expectations to manage", st['h3']))
        story += T.bullet_list([T.html_escape(x) for x in exp])
        story.append(Spacer(1, 0.15 * inch))

    # ── 2. Risk Assessment ────────────────────────────────────────────────
    story.append(T.section_header("2.  Risk Assessment"))
    story.append(Spacer(1, 0.14 * inch))

    # Hero badge lives inside this section (headline stat before the details)
    story.append(T.risk_badge(
        tier=ml_context.get('risk_tier', 'average'),
        multiplier=ml_context.get('risk_multiplier', 1.0),
        churn_prob=ml_context.get('churn_risk_prob', 0),
    ))
    story.append(Spacer(1, 0.2 * inch))

    ra = structured.get('risk_assessment', {}) or {}
    risks = (ra.get('key_risks') or [])[:3]
    if risks:
        story.append(Paragraph("Key risks identified", st['h3']))
        story.append(Spacer(1, 4))
        for r in risks:
            story.append(_risk_card(r))
            story.append(Spacer(1, 6))
        story.append(Spacer(1, 0.1 * inch))

    if ra.get('similar_deal_patterns') or ra.get('neighbor_highlights'):
        story.append(Paragraph("Similar historical deals", st['h3']))
        if ra.get('similar_deal_patterns'):
            story.append(Paragraph(T.html_escape(ra['similar_deal_patterns']), st['body']))
            story.append(Spacer(1, 4))
        for n in (ra.get('neighbor_highlights') or [])[:3]:
            story.append(Paragraph(f"•&nbsp;&nbsp;{T.html_escape(n)}", st['bullet']))
        story.append(Spacer(1, 0.15 * inch))

    # ── 3. 30-Day Agenda ──────────────────────────────────────────────────
    agenda = structured.get('agenda_30d', {}) or {}
    themes = (agenda.get('themes') or [])[:4]
    crit = (agenda.get('critical_dates') or [])[:3]
    if themes or crit:
        story.append(T.section_header("3.  First 30 Days · High-Level Agenda"))
        story.append(Spacer(1, 0.12 * inch))

        if themes:
            story.append(_theme_table(themes))
            story.append(Spacer(1, 0.15 * inch))

        if crit:
            story.append(Paragraph("Critical dates", st['h3']))
            story += T.bullet_list([T.html_escape(x) for x in crit])
            story.append(Spacer(1, 0.1 * inch))

        story.append(Paragraph(
            "<i>Detailed week-by-week plan attached separately.</i>",
            st['muted'],
        ))
        story.append(Spacer(1, 0.15 * inch))

    # ── 4. Handoff Notes ──────────────────────────────────────────────────
    hn = structured.get('handoff_notes', {}) or {}
    tips = (hn.get('customer_specific_tips') or [])[:4]
    if tips:
        story.append(T.section_header("4.  Handoff Notes for CSM"))
        story.append(Spacer(1, 0.12 * inch))
        story.append(Paragraph("Customer-specific tips", st['h3']))
        story += T.bullet_list([T.html_escape(t) for t in tips])

    doc.build(story)
    return buf.getvalue()


# ── Card / table helpers ──────────────────────────────────────────────────

def _stakeholder_table(sm: list) -> Table:
    """Stakeholders rendered as a compact table."""
    st = T.styles()
    header = [
        Paragraph("<b>Name</b>", st['muted']),
        Paragraph("<b>Role</b>", st['muted']),
        Paragraph("<b>Tenure</b>", st['muted']),
        Paragraph("<b>Notes</b>", st['muted']),
    ]
    rows = [header]
    for p in sm:
        role = (p.get('role') or '').lower()
        icon = ROLE_ICON.get(role, '•')
        role_label = role.replace('_', ' ').title()
        rows.append([
            Paragraph(
                f"<b>{T.html_escape(p.get('name', '?'))}</b><br/>"
                f"<font size=9 color='#6B6B6B'>{T.html_escape(p.get('title', '?'))}</font>",
                st['body_tight'],
            ),
            Paragraph(f"{icon}&nbsp;&nbsp;{role_label}", st['body_tight']),
            Paragraph(f"{p.get('tenure_months', '?')} mo", st['body_tight']),
            Paragraph(T.html_escape(p.get('engagement_note', '') or '—'), st['muted']),
        ])

    t = Table(rows, colWidths=[1.9 * inch, 1.6 * inch, 0.7 * inch, 2.55 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), T.ACCENT_TINT),
        ('TEXTCOLOR', (0, 0), (-1, 0), T.ACCENT_DARK),
        ('LINEBELOW', (0, 0), (-1, 0), 0.75, T.ACCENT),
        ('LINEBELOW', (0, 1), (-1, -1), 0.25, T.BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


def _two_column_lists(left_label: str, left_items: list,
                      right_label: str, right_items: list) -> Table:
    """Side-by-side lists (problems | solutions)."""
    st = T.styles()

    def _col(label, items):
        out = [Paragraph(label, st['h3'])]
        if items:
            for item in items:
                out.append(Paragraph(f"•&nbsp;&nbsp;{T.html_escape(item)}", st['bullet']))
        else:
            out.append(Paragraph("<i>—</i>", st['muted']))
        return out

    t = Table(
        [[_col(left_label, left_items), _col(right_label, right_items)]],
        colWidths=[3.35 * inch, 3.35 * inch],
    )
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    return t


def _objection_card(o: dict):
    st = T.styles()
    resolved = o.get('resolved')
    tick = '✓' if resolved else '⚠'
    tick_color = '#2E7D5B' if resolved else '#C6882E'
    title_text = (
        f"<font color='{tick_color}'><b>{tick}</b></font>&nbsp;&nbsp;"
        f"<b>{T.html_escape(o.get('raised_by', 'Prospect team'))}</b>"
    )
    body = [
        Paragraph(f'"{T.html_escape(o.get("concern", ""))}"', st['quote']),
        Paragraph(
            f"<font color='#6B6B6B'>Handled:</font> {T.html_escape(o.get('how_handled', ''))}",
            st['body_tight'],
        ),
    ]
    return T.card(Paragraph(title_text, st['body']), body)


def _qa_card(q: dict):
    st = T.styles()
    source = f"  <font color='#9A9A9A'>· {T.html_escape(q.get('source', ''))}</font>" if q.get('source') else ''
    title_text = f"<b>{T.html_escape(q.get('asked_by', 'Prospect team'))}</b>{source}"
    body = [
        Paragraph(f'"{T.html_escape(q.get("question", ""))}"', st['quote']),
        Paragraph(
            f"<font color='#6B6B6B'>Answer:</font> {T.html_escape(q.get('answer', ''))}",
            st['body_tight'],
        ),
    ]
    return T.card(Paragraph(title_text, st['body']), body)


def _risk_card(r: dict):
    st = T.styles()
    title = Paragraph(f"<b>{T.html_escape(r.get('risk', ''))}</b>", st['body'])
    body = [Paragraph(
        f"<font color='#6B6B6B'>Evidence:</font> {T.html_escape(r.get('evidence', ''))}",
        st['body_tight'],
    )]
    return T.card(title, body)


def _theme_table(themes: list) -> Table:
    """Weekly themes as a 4-column strip."""
    st = T.styles()
    label_style = ParagraphStyle(
        'week_label', fontName='Helvetica-Bold', fontSize=9,
        textColor=T.ACCENT_DARK, leading=11, alignment=1,  # centered
    )
    theme_style = ParagraphStyle(
        'week_theme', fontName='Helvetica', fontSize=10,
        textColor=T.INK, leading=13, alignment=1,  # centered
    )
    cells = []
    for t_ in themes:
        cells.append([
            Paragraph(f"WEEK {t_.get('week', '?')}", label_style),
            Spacer(1, 3),
            Paragraph(T.html_escape(t_.get('theme', '')), theme_style),
        ])
    # Pad to 4 columns if fewer
    while len(cells) < 4:
        cells.append([Paragraph('', label_style)])

    col_width = 6.75 / max(len(themes), 1) * inch if themes else 1.7 * inch
    t = Table([cells], colWidths=[col_width] * len(cells))
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), T.ACCENT_TINT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LINEAFTER', (0, 0), (-2, -1), 0.5, colors.white),
    ]))
    return t
