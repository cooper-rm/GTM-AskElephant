"""
30-Day Success Plan Agent — Block Kit output + structured JSON.

Consumes the CSM brief's structured output (stakeholder map, risks, tips)
so the plan references specific people and known concerns rather than
generic onboarding activities.

Single LLM call produces structured JSON; Python renders Block Kit for Slack.

Returns {"blocks": [...], "text": "...", "structured": {...}}.
"""
import json
from datetime import datetime, timezone

from ...utils.llm import ask_claude


def run(enriched_context: dict) -> dict:
    deal = enriched_context['deal']
    ml = enriched_context.get('ml_context', {})
    brief_structured = enriched_context.get('csm_brief_structured')

    company = deal['company']
    deal_info = deal['deal']

    structured = _generate_structured_plan(deal, ml, brief_structured)
    blocks = _render_blocks(company, deal_info, structured)
    fallback = _build_fallback(company, deal_info, ml, structured)

    return {
        'blocks': blocks,
        'text': fallback,
        'structured': structured,
    }


# ──────────────────────────────────────────────────────────────────────────
# LLM call → structured JSON
# ──────────────────────────────────────────────────────────────────────────

def _generate_structured_plan(deal: dict, ml: dict, brief: dict | None) -> dict:
    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')
    has_exec = any(p['role'] == 'exec_sponsor' for p in deal['people'])
    risk_tier = ml.get('risk_tier', 'average')
    risk_multiplier = ml.get('risk_multiplier', 1.0)

    # Pretty tier label — never leak snake_case into plan prose
    tier_key = deal_info.get('product_tier', '')
    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(tier_key, tier_key.replace('_', ' ').title())

    # Risk-calibrated cadence guidance
    timeline_guidance = {
        'very_low': "Standard cadence. Week 4 value review.",
        'low': "Standard cadence. Week 4 value review.",
        'average': "Standard cadence with mid-week pulse checks.",
        'elevated': "Accelerate Week 1-2 milestones. Exec alignment by Day 10.",
        'high': "Compress Week 1. Exec alignment by Day 7. Twice-weekly check-ins.",
        'very_high': "White-glove onboarding. Daily touchpoints Week 1. Exec alignment Day 3.",
    }.get(risk_tier, "Standard cadence.")

    # ── Brief context (only included if available) ────────────────────────
    brief_section = ""
    if brief:
        ctx = brief.get('customer_context', {}) or {}
        ra = brief.get('risk_assessment', {}) or {}
        hn = brief.get('handoff_notes', {}) or {}

        brief_lines = ["\nCSM BRIEF CONTEXT (use this to ground your plan in specifics):"]

        if ctx.get('stakeholder_map'):
            brief_lines.append("\nStakeholders:")
            for p in ctx['stakeholder_map'][:4]:
                engagement = f" — {p.get('engagement_note', '')}" if p.get('engagement_note') else ''
                brief_lines.append(
                    f"  - {p.get('name')} ({p.get('role')}, {p.get('tenure_months', '?')} mo){engagement}"
                )

        if ctx.get('current_problems'):
            brief_lines.append("\nCustomer's current problems:")
            brief_lines += [f"  - {x}" for x in ctx['current_problems'][:4]]

        if ctx.get('objections'):
            brief_lines.append("\nObjections raised in sales:")
            for o in ctx['objections'][:3]:
                brief_lines.append(
                    f"  - [{o.get('raised_by', 'prospect')}] {o.get('concern', '')}"
                )

        if ctx.get('expectations_to_manage'):
            brief_lines.append("\nExpectations CSM needs to manage:")
            brief_lines += [f"  - {e}" for e in ctx['expectations_to_manage'][:3]]

        if ra.get('key_risks'):
            brief_lines.append("\nKey risks identified:")
            for r in ra['key_risks'][:3]:
                brief_lines.append(f"  - {r.get('risk', '')}: {r.get('evidence', '')}")

        if hn.get('customer_specific_tips'):
            brief_lines.append("\nCustomer-specific tips from the brief:")
            brief_lines += [f"  - {t}" for t in hn['customer_specific_tips'][:3]]

        brief_section = '\n'.join(brief_lines)

    prompt = f"""Generate a 30-day success plan as structured JSON. Return ONLY valid JSON.

DEAL:
- Customer: {company['name']} ({company.get('segment', '?')}, {company.get('industry', '?')}, {company.get('employee_count', 0)} employees)
- Champion: {champion['name']}, {champion['title']} ({champion.get('tenure_months', '?')} mo)
- Exec sponsor engaged: {has_exec}
- Product: {tier_label} ({deal_info.get('seats', 0)} seats)
- Use case: {deal_info.get('use_case', '?')}
- Competitor replaced: {deal_info.get('competitor', 'None')}
- Risk tier: {risk_tier} ({risk_multiplier}x average churn)
- Timeline guidance: {timeline_guidance}
{brief_section}

OUTPUT SCHEMA (valid JSON only, no markdown fences):
{{
  "success_criteria": "ONE sentence: what 'working' looks like by Day 30 for THIS customer specifically.",
  "week_1": {{
    "focus": "short phrase (e.g. 'Foundation' or 'Technical setup')",
    "gate": "measurable milestone that must be true to proceed to Week 2",
    "activities": ["specific action 1", "specific action 2", "specific action 3"],
    "customer_stakeholders": ["Name (role) actively involved from the customer this week", "..."],
    "expected_outputs": ["concrete deliverable that exists by end of week (e.g. 'Salesforce integration live')", "..."],
    "owner": "CSM | AE | Implementation Lead"
  }},
  "week_2": {{ "focus": "...", "gate": "...", "activities": [...], "customer_stakeholders": [...], "expected_outputs": [...], "owner": "..." }},
  "week_3": {{ "focus": "...", "gate": "...", "activities": [...], "customer_stakeholders": [...], "expected_outputs": [...], "owner": "..." }},
  "week_4": {{ "focus": "...", "gate": "...", "activities": [...], "customer_stakeholders": [...], "expected_outputs": [...], "owner": "..." }}
}}

RULES:
- Reference the customer's specific USE CASE in Week 2 activities
- If exec sponsor is missing, Week 1 or 2 must include exec engagement action by NAME (use brief context)
- Activities must be concrete (e.g. "Schedule onboarding call with Alex Chen (IT) by Day 3" NOT "engage stakeholders")
- Activities: 2-4 per week, max 14 words each
- customer_stakeholders: 1-3 specific people (Name + role) from the brief's stakeholder map, NOT generic roles
- expected_outputs: 1-3 concrete things that exist by end of week (live integrations, reports, metrics, trained users) — not activities repeated
- Use real names from the brief when referring to people"""

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
    except Exception:
        return _fallback_structured(deal_info)


def _fallback_structured(deal_info: dict) -> dict:
    def _w(focus, gate, activities, outputs):
        return {
            'focus': focus,
            'gate': gate,
            'activities': activities,
            'customer_stakeholders': [],
            'expected_outputs': outputs,
            'owner': 'CSM',
        }
    return {
        'success_criteria': (
            f"Customer actively using {deal_info.get('use_case', 'the product')} "
            f"with measurable adoption by Day 30."
        ),
        'week_1': _w(
            'Foundation',
            'Technical setup complete, champion trained',
            ['Welcome call with champion', 'Integration setup', 'Product walkthrough'],
            ['Product access provisioned', 'Champion trained on core features'],
        ),
        'week_2': _w(
            'First Value',
            'First workflow producing output',
            ['Expand to pilot team', 'Track first-week metrics', 'Address early friction'],
            ['First production workflow live', 'Baseline metrics captured'],
        ),
        'week_3': _w(
            'Expansion',
            'Adoption target hit',
            ['Roll out to full team', 'Weekly adoption report', 'Gather user feedback'],
            ['Full team has active accounts', 'Adoption report delivered'],
        ),
        'week_4': _w(
            'Value Review',
            'ROI demonstrated against original pain',
            ['Prep exec business review', 'Present value metrics', 'Discuss expansion'],
            ['QBR slides prepared', 'Expansion opportunities identified'],
        ),
    }


# ──────────────────────────────────────────────────────────────────────────
# Structured JSON → Slack Block Kit
# ──────────────────────────────────────────────────────────────────────────

def _render_blocks(company: dict, deal_info: dict, plan: dict) -> list:
    spacer = {"type": "section", "text": {"type": "mrkdwn", "text": "\u2800"}}
    divider = {"type": "divider"}

    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"

    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(deal_info.get('product_tier', ''), deal_info.get('product_tier', ''))

    blocks: list = [spacer]

    # ── Header ────────────────────────────────────────────────────────────
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📋  Recommended 30-Day Success Plan  ·  {company['name']}",
            "emoji": True,
        },
    })
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": (
                f"_AI-generated recommendation for CSM review_  ·  "
                f"{acv_str} ACV  ·  "
                f"{deal_info.get('seats', 0)} seats  ·  "
                f"{tier_label}"
            ),
        }],
    })
    blocks.append(divider)

    # ── Success criteria (the headline) ───────────────────────────────────
    # Risk info lives on the CSM brief. Plan cadence is already calibrated
    # internally — no need to restate risk here.
    blocks.append(_section_header("🎯  Success Criteria"))
    blocks.append(_mrkdwn_section(f"> {plan.get('success_criteria', 'TBD')}"))
    blocks.append(divider)

    # ── Weeks 1-4 ─────────────────────────────────────────────────────────
    week_labels = [
        ('week_1', '1', 'Days 1-7'),
        ('week_2', '2', 'Days 8-14'),
        ('week_3', '3', 'Days 15-21'),
        ('week_4', '4', 'Days 22-30'),
    ]

    for i, (key, num, date_range) in enumerate(week_labels):
        week = plan.get(key, {}) or {}
        focus = week.get('focus', '')
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📅  Week {num}  ·  {focus}",
                "emoji": True,
            },
        })
        blocks.append({
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_{date_range}_"}],
        })

        gate = week.get('gate', '')
        owner = week.get('owner', 'CSM')
        blocks.append(_mrkdwn_section(
            f"*🎯  Gate:*   {gate}\n"
            f"*👤  Owner:*   {owner}"
        ))

        activities = (week.get('activities') or [])[:4]
        if activities:
            bullets = '\n'.join(f"•   {a}" for a in activities)
            blocks.append(_mrkdwn_section(f"*🗒  Activities*\n{bullets}"))

        stakeholders = (week.get('customer_stakeholders') or [])[:3]
        outputs = (week.get('expected_outputs') or [])[:3]
        if stakeholders or outputs:
            parts = []
            if stakeholders:
                parts.append("*👥  Customer stakeholders*\n" + '\n'.join(f"•   {s}" for s in stakeholders))
            if outputs:
                parts.append("*📦  Expected outputs*\n" + '\n'.join(f"•   {o}" for o in outputs))
            blocks.append(_mrkdwn_section('\n\n'.join(parts)))

        # Divider between weeks, but not after the last
        if i < len(week_labels) - 1:
            blocks.append(divider)

    # ── Footer ────────────────────────────────────────────────────────────
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": (
                f"_Plan generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ·  "
                f"Grounded in CSM brief context  ·  "
                f"Risks + handoff context in  #customer-success-briefings_"
            ),
        }],
    })
    blocks.append(spacer)

    return blocks


def _section_header(text: str) -> dict:
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": text, "emoji": True},
    }


def _mrkdwn_section(text: str) -> dict:
    if len(text) > 2900:
        text = text[:2880] + "\n_…(truncated)_"
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _build_fallback(company: dict, deal_info: dict, ml: dict, plan: dict) -> str:
    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"
    return (
        f"30-Day Success Plan — {company['name']} ({acv_str}) · "
        f"Risk {ml.get('risk_tier', 'average')}"
    )
