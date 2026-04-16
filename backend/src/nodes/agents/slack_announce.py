"""
Slack Announcement Agent

Generates a clean, celebratory internal announcement that a deal closed.
Uses Slack's Block Kit for real typography:
  - `header` block = large bold title
  - `section` with `fields` = 2-column key/value grid
  - `divider` = native horizontal rule
  - `context` block = small muted footer caption

Returns a dict {"blocks": [...], "text": fallback_for_notifications}.
"""


def run(enriched_context: dict) -> dict:
    deal = enriched_context['deal']
    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')

    # Product tier → pretty label
    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(deal_info.get('product_tier', ''), deal_info.get('product_tier', 'Unknown'))

    competitor = deal_info.get('competitor', 'None')
    use_case = deal_info.get('use_case', '')

    # ACV nicely formatted
    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"

    # Compact deal facts — single mrkdwn section (tighter than a grid)
    deal_facts = '\n'.join([
        f"💰  *ACV:*  {acv_str}",
        f"👥  *Seats:*  {deal_info.get('seats', 0)}",
        f"📦  *Plan:*  {tier_label}",
        f"🎯  *Use Case:*  {use_case}",
    ])

    # Company / champion block text
    detail_lines = [
        f"🏢  *Company:*  {company['name']}  ·  {company.get('industry', '')}  ·  {company.get('employee_count', 0)} employees",
        f"⭐  *Champion:*  {champion['name']}, {champion['title']}",
    ]
    if competitor and competitor != 'None':
        detail_lines.append(f"🏆  *Replaced:*  {competitor}")
    detail_text = '\n'.join(detail_lines)

    # Notification fallback (mobile push, screen readers)
    fallback = (
        f"🎉 New Win! {company['name']} just closed — "
        f"{acv_str} ACV, {deal_info.get('seats', 0)} seats ({tier_label})"
    )

    # Empty section used as vertical spacer (braille-blank = non-whitespace
    # char Slack can't collapse, so the block renders with real height).
    spacer = {"type": "section", "text": {"type": "mrkdwn", "text": "\u2800"}}

    blocks = [
        spacer,
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🎉  New Win!  {company['name']} just closed",
                "emoji": True,
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": deal_facts},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": detail_text},
        },
        {"type": "divider"},
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "Nice work team!  🔥"},
            ],
        },
        spacer,
    ]

    return {"blocks": blocks, "text": fallback}
