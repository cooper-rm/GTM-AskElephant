"""
Simple invoice PDF generator for welcome email attachment.

Usage:
    from ..utils.invoice_pdf import generate_invoice_pdf
    pdf_bytes = generate_invoice_pdf(deal)
"""
import io
from datetime import datetime, timezone

from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)


TIER_PRETTY = {
    'unlimited_automation': 'Unlimited Automation — Annual',
    'automations_plus_consulting': 'Automations + AI Consulting — Annual',
}

# AskElephant brand — bright SaaS blue (matches pdf_theme)
ACCENT = colors.HexColor('#2C5CE8')
ACCENT_DARK = colors.HexColor('#1E3FA6')
MUTED = colors.HexColor('#5E6578')
INK = colors.HexColor('#111111')


def generate_invoice_pdf(deal: dict) -> bytes:
    """
    Render a simple invoice for a closed-won deal.
    Returns the PDF file contents as bytes.
    """
    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')

    amount = deal_info.get('amount', 0)
    seats = deal_info.get('seats', 0)
    tier = deal_info.get('product_tier', '')
    tier_label = TIER_PRETTY.get(tier, tier.replace('_', ' ').title())
    deal_id = deal_info.get('deal_id') or deal.get('deal_id', 'N/A')

    today = datetime.now(timezone.utc).strftime('%B %d, %Y')

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        title=f"Invoice {deal_id} — AskElephant",
        author="AskElephant",
    )

    styles = getSampleStyleSheet()
    h_brand = ParagraphStyle(
        'Brand', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=22, textColor=ACCENT,
        spaceAfter=0, leading=26,
    )
    h_invoice = ParagraphStyle(
        'InvoiceLabel', parent=styles['Heading1'],
        fontName='Helvetica-Bold', fontSize=16, textColor=colors.black,
        alignment=TA_RIGHT, spaceAfter=0, leading=20,
    )
    meta = ParagraphStyle(
        'Meta', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=MUTED,
        alignment=TA_RIGHT, leading=12,
    )
    h_section = ParagraphStyle(
        'Section', parent=styles['Normal'],
        fontName='Helvetica-Bold', fontSize=9, textColor=MUTED,
        leading=12, spaceAfter=4,
    )
    body = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontName='Helvetica', fontSize=10.5, textColor=colors.black,
        leading=14,
    )
    footer = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontName='Helvetica', fontSize=9, textColor=MUTED,
        alignment=TA_LEFT, leading=12,
    )

    story = []

    # ── Top strip: brand on left, "INVOICE" + meta on right ───────────────
    top_table = Table(
        [[
            Paragraph('ASKELEPHANT', h_brand),
            [
                Paragraph('INVOICE', h_invoice),
                Spacer(1, 4),
                Paragraph(f"<b>Invoice #:</b> {deal_id}", meta),
                Paragraph(f"<b>Date:</b> {today}", meta),
                Paragraph(f"<b>Status:</b> <font color='#2C5CE8'><b>PAID</b></font>", meta),
            ],
        ]],
        colWidths=[3.5 * inch, 3.5 * inch],
    )
    top_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(top_table)
    story.append(Spacer(1, 0.25 * inch))

    # Accent rule
    rule = Table([['']], colWidths=[7 * inch], rowHeights=[2])
    rule.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), ACCENT)]))
    story.append(rule)
    story.append(Spacer(1, 0.25 * inch))

    # ── Bill-to ───────────────────────────────────────────────────────────
    story.append(Paragraph('BILL TO', h_section))
    story.append(Paragraph(f"<b>{company['name']}</b>", body))
    story.append(Paragraph(f"{champion['name']}, {champion['title']}", body))
    if company.get('industry'):
        story.append(Paragraph(
            f"<font color='#666666'>{company['industry']}  ·  "
            f"{company.get('employee_count', '?')} employees</font>",
            body,
        ))
    story.append(Spacer(1, 0.3 * inch))

    # ── Line items ────────────────────────────────────────────────────────
    line_items_data = [
        ['Description', 'Qty', 'Unit', 'Amount'],
        [
            Paragraph(f"<b>{tier_label}</b><br/>"
                      f"<font size=8 color='#666666'>{seats} seats · 12-month term</font>", body),
            '1',
            f"${amount:,.2f}",
            f"${amount:,.2f}",
        ],
    ]
    line_table = Table(
        line_items_data,
        colWidths=[3.7 * inch, 0.6 * inch, 1.1 * inch, 1.3 * inch],
    )
    line_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F4F4F2')),
        ('TEXTCOLOR', (0, 0), (-1, 0), MUTED),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),

        # Body row
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),

        # Borders
        ('LINEBELOW', (0, 0), (-1, 0), 0.5, colors.HexColor('#DDDDDD')),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
    ]))
    story.append(line_table)
    story.append(Spacer(1, 0.1 * inch))

    # ── Totals block (right-aligned) ──────────────────────────────────────
    totals_data = [
        ['Subtotal', f"${amount:,.2f}"],
        ['Tax', '—'],
        ['Total', f"${amount:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[5.4 * inch, 1.3 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -2), 10),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('TEXTCOLOR', (0, 0), (0, -2), MUTED),
        ('TEXTCOLOR', (0, -1), (-1, -1), ACCENT),
        ('LINEABOVE', (0, -1), (-1, -1), 1, ACCENT),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 0.6 * inch))

    # ── Footer ────────────────────────────────────────────────────────────
    story.append(Paragraph('Thank you for your business.', body))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph(
        'AskElephant · hello@askelephant.com · Questions? Reply to your welcome email.',
        footer,
    ))

    doc.build(story)
    return buf.getvalue()
