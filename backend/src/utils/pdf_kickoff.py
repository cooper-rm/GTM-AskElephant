"""
Kickoff Meeting Request Draft → PDF.

Consumes kickoff_draft.structured + deal info.
Renders the draft as if it were an email preview, with meeting details
and internal CSM notes in separate sections.
"""
import io

from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, KeepTogether
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle

from . import pdf_theme as T


def generate_kickoff_pdf(deal: dict, structured: dict) -> bytes:
    """
    Render a two-page kickoff draft:
      1. Cover — branded title page
      2. For-review callout + email preview card
    Meeting logistics live in the brief — this document is intentionally minimal.
    """
    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')

    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"

    buf = io.BytesIO()
    doc = T.make_doc(buf, title=f"Kickoff Draft · {company['name']}")

    story = []

    # ── Cover page ────────────────────────────────────────────────────────
    story += T.cover_page(
        kicker="Kickoff Meeting Request · Draft",
        company_name=company['name'],
        subtitle=f"Recipient: {champion['name']}, {champion['title']}",
        meta_pairs=[
            ('ACV', acv_str),
            ('Seats', str(deal_info.get('seats', 0))),
            ('Use case', deal_info.get('use_case', '—')),
            ('Deal', deal_info.get('deal_id') or deal.get('deal_id', '—')),
        ],
        prepared_for="For CSM review  ·  Not sent automatically",
    )

    # ── Inside page: callout + email preview (only — keep it simple) ─────
    story.append(_draft_callout())
    story.append(Spacer(1, 0.25 * inch))
    story.append(_email_preview(
        to_name=champion['name'],
        subject=structured.get('subject', ''),
        body=structured.get('body', ''),
    ))

    doc.build(story)
    return buf.getvalue()


# ── Components ────────────────────────────────────────────────────────────

def _draft_callout() -> Table:
    """Small banner reminding CSM this is a draft for review."""
    text = (
        "<b>For CSM review.</b>  Copy, edit and send from your email client — "
        "this draft is not sent automatically."
    )
    p = Paragraph(text, ParagraphStyle(
        'callout', fontName='Helvetica', fontSize=9.5,
        textColor=T.MUTED, leading=12,
    ))
    t = Table([[p]], colWidths=[6.75 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FBF7E6')),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBEFORE', (0, 0), (0, -1), 3, T.WARN),
    ]))
    return t


def _email_preview(to_name: str, subject: str, body: str):
    """Render a styled email-preview block (like a Gmail card)."""
    st = T.styles()

    # Header row: To / Subject
    meta_style = ParagraphStyle(
        'meta_label', fontName='Helvetica-Bold', fontSize=8.5,
        textColor=T.MUTED, leading=11,
    )
    meta_val = ParagraphStyle(
        'meta_val', fontName='Helvetica', fontSize=10,
        textColor=T.INK, leading=13,
    )

    header = Table(
        [
            [Paragraph("TO", meta_style), Paragraph(T.html_escape(to_name), meta_val)],
            [Paragraph("SUBJECT", meta_style), Paragraph(T.html_escape(subject), meta_val)],
        ],
        colWidths=[0.85 * inch, 5.9 * inch],
    )
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    # Body — split paragraphs on blank lines
    body_flows = []
    for para in (body or '').split('\n\n'):
        stripped = para.strip()
        if stripped:
            # Preserve internal line breaks with <br/>
            html = T.html_escape(stripped).replace('\n', '<br/>')
            body_flows.append(Paragraph(html, st['email_body']))

    inner = [[header]]
    inner += [[Spacer(1, 10)]]
    # Hairline separator
    sep = Table([['']], colWidths=[6.75 * inch], rowHeights=[0.5])
    sep.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), T.BORDER)]))
    inner += [[sep], [Spacer(1, 8)]]
    for f in body_flows:
        inner.append([f])

    wrap = Table(inner, colWidths=[6.75 * inch])
    wrap.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 0.5, T.BORDER),
        ('LEFTPADDING', (0, 0), (-1, -1), 16),
        ('RIGHTPADDING', (0, 0), (-1, -1), 16),
        ('TOPPADDING', (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 14),
    ]))
    return KeepTogether(wrap)


