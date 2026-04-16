"""
Kickoff Draft Agent

Generates a draft kickoff meeting request for the CSM to review and send to the customer.
NOT sent directly to the customer — posted to #kickoff-drafts for CSM review.

Produces a ready-to-edit email draft with:
  - Suggested subject line
  - Full email body (customer-facing voice)
  - Proposed meeting details (duration, timeframe, attendees, agenda)
  - Internal notes for the CSM (context, champion nuances, risk-calibrated adjustments)

Returns {"blocks": [...], "text": "...", "structured": {...}}.
"""
import json
from datetime import datetime, timezone

from ...utils.llm import ask_claude


def run(enriched_context: dict) -> dict:
    deal = enriched_context['deal']
    ml = enriched_context.get('ml_context', {})
    risk = enriched_context.get('risk_narrative', {})

    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')

    structured = _generate_structured_draft(deal, ml, risk)
    blocks = _render_blocks(company, deal_info, champion, structured)
    fallback = f"Kickoff meeting draft — {company['name']} (for CSM review before sending to {champion['name']})"

    return {
        'blocks': blocks,
        'text': fallback,
        'structured': structured,
    }


def _generate_structured_draft(deal: dict, ml: dict, risk: dict) -> dict:
    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')
    has_exec = any(p['role'] == 'exec_sponsor' for p in deal['people'])
    attendees = [
        p for p in deal['people']
        if p['role'] in ('champion', 'exec_sponsor', 'technical_evaluator', 'end_user')
    ]

    attendees_str = '\n'.join(f"  - {p['name']}, {p['title']} ({p['role']})" for p in attendees)

    # Pretty product-tier label — never leak raw snake_case keys into customer-facing copy
    tier_key = deal_info.get('product_tier', '')
    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(tier_key, tier_key.replace('_', ' ').title())

    risk_tier = ml.get('risk_tier', 'average')

    # Risk-calibrated intensity
    intensity = {
        'very_low': "Standard 45-minute kickoff. Champion-led. No pre-meeting prep needed.",
        'low': "Standard 45-minute kickoff. Champion-led.",
        'average': "Standard 45-minute kickoff with explicit success criteria review.",
        'elevated': "60-minute kickoff. Include exec sponsor. Pre-kickoff check-in with champion recommended.",
        'high': "60-75 minute kickoff. Exec sponsor attendance important. Pre-kickoff touchpoint with champion required.",
        'very_high': "White-glove kickoff. Compressed agenda. Exec sponsor must attend. Pre-kickoff AND mid-week check-in.",
    }.get(risk_tier, "Standard 45-minute kickoff.")

    prompt = f"""Draft a kickoff meeting request email. This email is NOT sent automatically — the CSM reviews, edits, and sends it.
Return ONLY valid JSON matching the schema.

CUSTOMER:
- Company: {company['name']} ({company.get('segment', '?')}, {company.get('industry', '?')}, {company.get('employee_count', 0)} employees)
- Champion: {champion['name']}, {champion['title']}  ({champion.get('tenure_months', '?')} months in role)
- Product: {tier_label} ({deal_info.get('seats', 0)} seats)
- Use case: {deal_info.get('use_case', '?')}
- Exec sponsor engaged: {has_exec}

RISK PROFILE:
- Tier: {risk_tier} ({ml.get('risk_multiplier', 1.0)}x average churn risk)
- Intensity guidance: {intensity}

OUTPUT SCHEMA (valid JSON only, no markdown fences):
{{
  "subject": "Specific subject line — NOT 'Welcome' or 'Hi' (e.g. 'Kickoff call — mapping your rep productivity rollout')",
  "body": "Full email body addressed to the champion by first name. 110-160 words. Structure:\\n\\nHi <first name>,\\n\\n<Opening sentence that references their SPECIFIC pain or goal — pull from use case, not generic 'congrats on being active'.>\\n\\n<Propose kickoff: 45 min, next week or a loose window. One sentence.>\\n\\nOn the call, we'll:\\n\\n<Three concrete items starting with verbs (Walk through..., Map out..., Identify...). Each 8-12 words. Tied to their use case.>\\n\\n<One sentence closing with 'Reply with 2-3 time windows that work for you and your team'.>\\n\\nThe AskElephant Team"
}}

STRICT RULES:
- Plain text only. NO markdown. NO asterisks. NO hash marks. NO underscores. NO backticks. NO emojis.
- NO snake_case tokens in the customer-facing body (e.g. do NOT write 'unlimited_automation' — use the pretty 'Unlimited Automation' label above). Any field that came with an underscore gets written in natural prose.
- NO placeholders ('[calendar link]', '[your name]', '[date]') — if info isn't available, omit the sentence.
- Sign-off MUST be exactly: The AskElephant Team
- Body must sound like a real human wrote it — no corporate fluff, no 'We are excited to'.
- Do NOT suggest specific dates or times — just a window like 'next week'.
- If risk is elevated/high, the body should (subtly) hint that bringing the exec sponsor adds value.
- The body MUST include inline agenda (3 bullets phrased as a list starting with 'On the call, we'll:'). This replaces a separate agenda section.
- Do NOT include attendee lists, meeting logistics, or post-kickoff expectations in the body — the brief covers that."""

    try:
        raw = ask_claude(
            prompt,
            "Output only valid JSON. No markdown fences. No commentary.",
            timeout=90,
            model="sonnet",
        )
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        return json.loads(cleaned)
    except Exception as e:
        return _fallback_structured(deal, error=str(e))


def _fallback_structured(deal: dict, error: str = '') -> dict:
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')
    use_case = deal_info.get('use_case', 'your use case')
    return {
        'subject': f"Kickoff call — getting your team set up for {use_case}",
        'body': (
            f"Hi {champion['name'].split()[0]},\n\n"
            f"Let's get your team productive on {use_case} as quickly as possible. "
            f"I'd like to schedule a 45-minute kickoff call next week.\n\n"
            f"On the call, we'll:\n\n"
            f"- Walk through your current workflow and pain points\n"
            f"- Map out the first 2-3 automations to deploy\n"
            f"- Align on success metrics and a 30-day roadmap\n\n"
            f"Reply with 2-3 time windows that work for you and your team.\n\n"
            f"The AskElephant Team"
        ),
    }


def _render_blocks(company: dict, deal_info: dict, champion: dict, s: dict) -> list:
    """
    Render the kickoff draft as a minimal Slack card: header, subject, body, footer.
    Meeting logistics live in the brief — this is just the draft email.
    """
    spacer = {"type": "section", "text": {"type": "mrkdwn", "text": "\u2800"}}
    divider = {"type": "divider"}

    blocks: list = [spacer]

    # Header
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📅  Kickoff Draft  ·  {company['name']}",
            "emoji": True,
        },
    })
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": (
                f"_For CSM review  ·  Copy, edit and send from your email client_  ·  "
                f"Recipient: *{champion['name']}*, {champion['title']}"
            ),
        }],
    })
    blocks.append(divider)

    # Subject
    subject = s.get('subject', '')
    if subject:
        blocks.append(_mrkdwn_section(f"*Subject:*   {subject}"))

    # Body — single block, line breaks preserved
    body = s.get('body', '')
    if body:
        blocks.append(_mrkdwn_section(body))

    # Footer
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": (
                f"_Draft generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ·  "
                f"Stakeholder context + risks live in  #customer-success-briefings_"
            ),
        }],
    })
    blocks.append(spacer)

    return blocks


def _mrkdwn_section(text: str) -> dict:
    if len(text) > 2900:
        text = text[:2880] + "\n_…(truncated)_"
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}
