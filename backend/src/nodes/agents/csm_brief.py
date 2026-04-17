"""
CSM Brief Agent — Block Kit output + structured JSON for downstream consumption.

Single LLM call produces a rich structured brief with 4 sections:
  1. Customer Context — stakeholders, business, problems, solutions, objections, Q&A, expectations
  2. Risk Assessment — hero churn badge + specific risks + neighbor patterns
  3. First 30 Days Agenda — high-level themes (NOT the detailed plan)
  4. Handoff Notes — customer-specific tips

Returns {"blocks": [...], "text": "...", "structured": {...}}.
  - blocks/text → Slack rendering
  - structured → persisted on disk and available for downstream agents (e.g. 30-day plan)
"""
import json
from datetime import datetime, timezone

from ...utils.llm import ask_claude


RISK_EMOJI = {
    'very_low': '🟢', 'low': '🟢',
    'average': '🟡',
    'elevated': '🟠',
    'high': '🔴', 'very_high': '🔴',
}

# Role-specific icons — let the eye scan on shape, not text
ROLE_EMOJI = {
    'champion': '🏆',
    'technical_evaluator': '⚙️',
    'economic_buyer': '💰',
    'exec_sponsor': '👑',
    'end_user': '👤',
}


def run(enriched_context: dict) -> dict:
    deal = enriched_context['deal']
    ml = enriched_context.get('ml_context', {})
    risk = enriched_context.get('risk_narrative', {})
    qa = enriched_context.get('qa_history', {})
    objections = enriched_context.get('objection_history', {})
    neighbors = enriched_context.get('neighbor_analysis', {})

    company = deal['company']
    deal_info = deal['deal']

    structured = _generate_structured_brief(deal, ml, risk, qa, objections, neighbors)
    blocks = _render_blocks(company, deal_info, ml, structured)
    fallback = _build_fallback(company, deal_info, ml)

    return {
        'blocks': blocks,
        'text': fallback,
        'structured': structured,
    }


# ────────────────────────────────────────────────────────────────────────────
# LLM call → structured JSON
# ────────────────────────────────────────────────────────────────────────────

def _generate_structured_brief(deal: dict, ml: dict, risk: dict, qa: dict, objections: dict, neighbors: dict) -> dict:
    company = deal['company']
    deal_info = deal['deal']

    # Pretty tier label — never leak snake_case into the brief's prose
    tier_key = deal_info.get('product_tier', '')
    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(tier_key, tier_key.replace('_', ' ').title())

    people_str = '\n'.join(
        f"  - {p['name']} ({p['role']}) — {p.get('title', '?')}, {p.get('tenure_months', '?')} mo in role"
        for p in deal['people']
    ) or '  (no people recorded)'

    # Touch history — Q&A from structured agent, no raw objection parsing
    touches_parts = []
    for t in deal.get('touches', [])[:10]:
        header = (
            f"  Touch #{t.get('touch_number')} — {t.get('type', '?')} "
            f"on {t.get('date', '?')} "
            f"(sentiment: {t.get('sentiment', 'neutral')}, inbound: {t.get('inbound', False)})"
        )
        parts = [header]

        qas = t.get('questions_asked', [])
        if qas:
            parts.append("    Q&A:")
            for q in qas[:5]:
                parts.append(
                    f"      - [{q.get('by', 'unknown')}] Q: {q.get('question', '')}\n"
                    f"        A: {q.get('answer', '')}"
                )

        touches_parts.append('\n'.join(parts))
    touches_str = '\n'.join(touches_parts) or '  (no touch history)'

    # Structured objection history (from objection_history agent)
    obj_items = objections.get('objection_history', [])[:6]
    objections_str = '\n'.join(
        f"  - Touch #{o.get('touch_number')} ({o.get('stage', '?')}) — "
        f"{o.get('raised_by', '?')} ({o.get('raised_by_role', '?')}): "
        f"\"{o.get('objection', '')}\""
        for o in obj_items
    ) or '  (no objections recorded)'
    unresolved_str = ', '.join(objections.get('unresolved_objections', [])) or 'None'

    # Risk factors — humanized (no SHAP jargon)
    top_factors = ml.get('top_risk_factors', [])
    factors_str = '\n'.join(
        f"  - {name.replace('_', ' ').title()}: {'increases' if val > 0 else 'reduces'} churn risk"
        for name, val in top_factors[:5]
    ) or '  (no factors identified)'

    # Neighbor analysis — use LLM-analyzed patterns instead of raw data
    neighbor_pattern = neighbors.get('pattern_analysis', '')
    neighbor_insights = neighbors.get('actionable_insights', [])
    neighbor_warnings = neighbors.get('warning_signals', [])
    nn_analysis_str = neighbor_pattern
    if neighbor_insights:
        nn_analysis_str += '\nActionable insights:\n' + '\n'.join(f"  - {i}" for i in neighbor_insights[:3])
    if neighbor_warnings:
        nn_analysis_str += '\nWarning signals:\n' + '\n'.join(f"  - {w}" for w in neighbor_warnings[:2])
    nn_analysis_str = nn_analysis_str or '  (no similar deal analysis available)'

    prompt = f"""Generate a comprehensive CSM handoff brief. Return ONLY valid JSON matching the schema.

DEAL:
- Company: {company['name']} ({company.get('segment', '?')}, {company.get('industry', '?')}, {company.get('employee_count', 0)} employees)
- Product: {tier_label} ({deal_info.get('seats', 0)} seats, ${deal_info.get('amount', 0):,.0f} ACV)
- Use case: {deal_info.get('use_case', '?')}
- Competitor replaced: {deal_info.get('competitor', 'None')}
- Effective discount: {deal_info.get('effective_discount_pct', 0)}%
- Sales cycle: {deal_info.get('cycle_days', '?')} days

PEOPLE (use these names + titles for attribution):
{people_str}

TOUCH HISTORY:
{touches_str}

OBJECTION ANALYSIS (from objection agent):
Objections raised:
{objections_str}
Unresolved concerns: {unresolved_str}
Objection agent analysis: {objections.get('analysis', '(none)')}

RISK CONTEXT:
- Risk tier: {ml.get('risk_tier', 'unknown')}
- Risk multiplier: {ml.get('risk_multiplier', 1.0)}x average churn rate
- Key risk factors:
{factors_str}

SIMILAR DEAL ANALYSIS (from neighbor analysis agent):
{nn_analysis_str}

PRIOR RISK NARRATIVE:
{risk.get('summary', '(none)')}

ATTRIBUTION RULES:
- Every objection, concern, and question MUST be attributed to a specific person by "Name (role)"
- When a touch Q&A is marked [prospect] or [rep], infer the likely person:
    * pricing / contract / discount → economic buyer or champion
    * integration / security / data model → technical evaluator
    * process / change management → champion
    * strategic / ROI → exec sponsor
- If genuinely unclear, say "prospect team" — never fabricate a name
- Rep-asked questions attribute to "Rep"

OUTPUT SCHEMA (valid JSON only, no markdown fences):
{{
  "customer_context": {{
    "business_summary": "2-3 sentence snapshot: who they are, what they do, CS org context.",
    "stakeholder_map": [
      {{"name": "...", "role": "champion|exec_sponsor|technical_evaluator|economic_buyer|end_user",
        "title": "...", "tenure_months": N,
        "engagement_note": "brief observation from touches (e.g. 'active in 4 of 5 touches, drove eval')"}}
    ],
    "current_problems": ["specific pain 1 they explicitly mentioned", "..."],
    "solutions_delivered": ["concrete way our product addresses pain 1", "..."],
    "objections": [
      {{"raised_by": "Name (role)", "concern": "verbatim or close paraphrase",
        "how_handled": "what the rep said/did", "resolved": true}}
    ],
    "qa_highlights": [
      {{"asked_by": "Name (role) or Rep", "question": "...", "answer": "...",
        "source": "Touch #N (type)"}}
    ],
    "expectations_to_manage": ["specific expectation customer has that CSM needs to handle"]
  }},
  "risk_assessment": {{
    "key_risks": [
      {{"risk": "specific risk (not generic)", "evidence": "concrete evidence from touches or ML"}}
    ],
    "similar_deal_patterns": "1-2 sentence observation of patterns from neighbor deals",
    "neighbor_highlights": ["Acme Corp (SMB) churned day 45: low adoption", "..."]
  }},
  "agenda_30d": {{
    "themes": [
      {{"week": 1, "theme": "short phrase"}},
      {{"week": 2, "theme": "..."}},
      {{"week": 3, "theme": "..."}},
      {{"week": 4, "theme": "..."}}
    ],
    "critical_dates": ["Kickoff call by Day 3", "Exec check-in by Day 14", "..."]
  }},
  "handoff_notes": {{
    "customer_specific_tips": [
      "concrete non-obvious thing about THIS customer (e.g. 'Champion is 3 months tenure — compensate with exec touch')"
    ]
  }}
}}

RULES:
- Use REAL names from PEOPLE list. No placeholders, no made-up names.
- Be specific — reference touch numbers, actual quotes, real ML metrics
- HARD CAPS: max 4 stakeholders, 4 objections, 4 qa_highlights, 3 key_risks, 3 neighbor_highlights, 3 items in any other list
- NEVER write snake_case in any string value (e.g. 'unlimited_automation'). Use the pretty product label given above and natural-language phrasings everywhere.
- NO generic boilerplate ("ensure successful onboarding", "drive adoption") — if you can't be specific, omit it
- If data is missing for a section, return an empty list rather than filler"""

    try:
        raw = ask_claude(
            prompt,
            "Output only valid JSON. No markdown fences. No commentary before or after.",
            timeout=180,
            model="sonnet",
        )
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        return json.loads(cleaned)
    except Exception as e:
        return _fallback_structured(deal, ml, risk, error=str(e))


def _fallback_structured(deal: dict, ml: dict, risk: dict, error: str = '') -> dict:
    """Minimal structure that still renders if the LLM fails."""
    company = deal['company']
    deal_info = deal['deal']
    return {
        'customer_context': {
            'business_summary': (
                f"{company['name']} is a {company.get('segment', '?')} "
                f"{company.get('industry', '')} company with {company.get('employee_count', '?')} employees."
            ),
            'stakeholder_map': [
                {
                    'name': p['name'], 'role': p['role'], 'title': p.get('title', ''),
                    'tenure_months': p.get('tenure_months', 0),
                    'engagement_note': '',
                }
                for p in deal['people']
            ],
            'current_problems': [deal_info.get('use_case', 'Not specified')],
            'solutions_delivered': [
                f"{deal_info.get('product_tier', 'Product')} configured for "
                f"{deal_info.get('use_case', 'their use case')}"
            ],
            'objections': [],
            'qa_highlights': [],
            'expectations_to_manage': [
                f'[Brief generation failed: {error[:120]}]' if error else ''
            ],
        },
        'risk_assessment': {
            'key_risks': [{'risk': 'See risk narrative', 'evidence': risk.get('summary', '')}],
            'similar_deal_patterns': '',
            'neighbor_highlights': [],
        },
        'agenda_30d': {
            'themes': [
                {'week': 1, 'theme': 'Onboarding & technical setup'},
                {'week': 2, 'theme': 'First-value milestone'},
                {'week': 3, 'theme': 'Team-wide adoption'},
                {'week': 4, 'theme': 'Value review & expansion talk'},
            ],
            'critical_dates': [],
        },
        'handoff_notes': {
            'customer_specific_tips': [],
        },
    }


# ────────────────────────────────────────────────────────────────────────────
# Structured JSON → Slack Block Kit
# ────────────────────────────────────────────────────────────────────────────

def _render_blocks(company: dict, deal_info: dict, ml: dict, s: dict) -> list:
    spacer = {"type": "section", "text": {"type": "mrkdwn", "text": "\u2800"}}
    divider = {"type": "divider"}

    risk_tier = ml.get('risk_tier', 'average')
    risk_emoji = RISK_EMOJI.get(risk_tier, '🟡')
    risk_multiplier = ml.get('risk_multiplier', 1.0)
    churn_prob = ml.get('churn_risk_prob', 0)

    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"

    blocks: list = [spacer]

    # ── Header ────────────────────────────────────────────────────────────
    blocks.append({
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": f"📋  CSM Handoff Brief  ·  {company['name']}",
            "emoji": True,
        },
    })
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": (
                f"_AI-generated for CSM review_  ·  "
                f"{company.get('segment', '').upper()}  ·  "
                f"{acv_str} ACV  ·  "
                f"{deal_info.get('seats', 0)} seats"
            ),
        }],
    })
    blocks.append(divider)

    # ── 1. Customer Context ────────────────────────────────────────────────
    blocks.append(_section_header("1.  Customer Context"))
    ctx = s.get('customer_context', {}) or {}

    # Business summary — single block (matches PDF rendering)
    if ctx.get('business_summary'):
        blocks.append(_mrkdwn_section(ctx['business_summary']))

    # Stakeholders — one card per person (name dominant, blockquote for note)
    sm = (ctx.get('stakeholder_map', []) or [])[:4]
    if sm:
        blocks.append(_subheader("👥  Stakeholders"))
        for p in sm:
            role = (p.get('role') or '').lower()
            icon = ROLE_EMOJI.get(role, '👤')
            role_label = role.replace('_', ' ').title()
            tenure = p.get('tenure_months', '?')
            text = (
                f"{icon}   *{p.get('name', '?')}*\n"
                f"{p.get('title', '?')}  ·  _{role_label}_  ·  _{tenure} mo in role_"
            )
            if p.get('engagement_note'):
                text += f"\n> {p['engagement_note']}"
            blocks.append(_mrkdwn_section(text))

    # Current problems — single block with label + bullets
    if ctx.get('current_problems'):
        bullets = '\n'.join(f"•   {p}" for p in ctx['current_problems'][:4])
        blocks.append(_mrkdwn_section(f"*🎯  What they're solving*\n{bullets}"))

    # Solutions
    if ctx.get('solutions_delivered'):
        bullets = '\n'.join(f"•   {x}" for x in ctx['solutions_delivered'][:4])
        blocks.append(_mrkdwn_section(f"*💡  What we're delivering*\n{bullets}"))

    # Objections — card per item, verbatim as blockquote
    objs = (ctx.get('objections', []) or [])[:4]
    if objs:
        blocks.append(_subheader("🗣️  Objections  ·  how they were handled"))
        for o in objs:
            tick = '✅' if o.get('resolved') else '⚠️'
            text = (
                f"{tick}   *{o.get('raised_by', 'Prospect team')}*\n"
                f"> {o.get('concern', '')}\n"
                f"_Handled:_  {o.get('how_handled', '')}"
            )
            blocks.append(_mrkdwn_section(text))

    # Q&A highlights — card per item
    qas = (ctx.get('qa_highlights', []) or [])[:4]
    if qas:
        blocks.append(_subheader("❓  Key Q&A from sales"))
        for q in qas:
            source = f"   ·   _{q.get('source', '')}_" if q.get('source') else ''
            text = (
                f"*{q.get('asked_by', 'Prospect team')}*{source}\n"
                f"> {q.get('question', '')}\n"
                f"_Answer:_  {q.get('answer', '')}"
            )
            blocks.append(_mrkdwn_section(text))

    # Expectations — inline list
    exp_list = [e for e in (ctx.get('expectations_to_manage') or []) if e][:3]
    if exp_list:
        bullets = '\n'.join(f"•   {e}" for e in exp_list)
        blocks.append(_mrkdwn_section(f"*🧭  Expectations to manage*\n{bullets}"))

    blocks.append(divider)

    # ── 2. Risk Assessment ─────────────────────────────────────────────────
    blocks.append(_section_header("2.  Risk Assessment"))

    blocks.append(_mrkdwn_section(
        f"{risk_emoji}   *Risk tier:*  _{risk_tier.replace('_', ' ')}_\n"
        f"*{risk_multiplier}x* average churn rate"
    ))

    ra = s.get('risk_assessment', {}) or {}
    risks = (ra.get('key_risks', []) or [])[:3]
    if risks:
        blocks.append(_subheader("🚩  Key risks identified"))
        for r in risks:
            blocks.append(_mrkdwn_section(
                f"*{r.get('risk', '')}*\n"
                f"> {r.get('evidence', '')}"
            ))

    if ra.get('similar_deal_patterns') or ra.get('neighbor_highlights'):
        parts = [f"*🔍  Similar historical deals*"]
        if ra.get('similar_deal_patterns'):
            parts.append(ra['similar_deal_patterns'])
        for n in (ra.get('neighbor_highlights') or [])[:3]:
            parts.append(f"•   {n}")
        blocks.append(_mrkdwn_section('\n'.join(parts)))

    blocks.append(divider)

    # ── 3. First 30 Days Agenda ────────────────────────────────────────────
    blocks.append(_section_header("3.  First 30 Days  ·  High-Level Agenda"))

    themes = s.get('agenda_30d', {}).get('themes', []) or []
    if themes:
        lines = '\n'.join(
            f"*Week {t.get('week', '?')}*   ·   {t.get('theme', '')}"
            for t in themes
        )
        blocks.append(_mrkdwn_section(lines))

    crit = s.get('agenda_30d', {}).get('critical_dates', []) or []
    if crit:
        bullets = '\n'.join(f"•   {d}" for d in crit[:3])
        blocks.append(_mrkdwn_section(f"*📌  Critical dates*\n{bullets}"))

    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": "_Detailed week-by-week plan posted in  #30d-customer-success-plans_",
        }],
    })
    blocks.append(divider)

    # ── 4. Handoff Notes ───────────────────────────────────────────────────
    blocks.append(_section_header("4.  Handoff Notes for CSM"))

    hn = s.get('handoff_notes', {}) or {}

    tips = hn.get('customer_specific_tips', []) or []
    if tips:
        bullets = '\n'.join(f"•   {t}" for t in tips[:4])
        blocks.append(_mrkdwn_section(f"*💡  Customer-specific tips*\n{bullets}"))

    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": f"_Brief generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        }],
    })
    blocks.append(spacer)

    return blocks


def _section_header(text: str) -> dict:
    """Big section-title header block (use for top-level sections)."""
    return {
        "type": "header",
        "text": {"type": "plain_text", "text": text, "emoji": True},
    }


def _subheader(text: str) -> dict:
    """
    Subheading inside a section — smaller than a header block.
    Rendered as a bold mrkdwn line; visually groups list cards below it.
    """
    return {"type": "section", "text": {"type": "mrkdwn", "text": f"*{text}*"}}


def _mrkdwn_section(text: str) -> dict:
    """Plain mrkdwn section block with defensive 3000-char truncation."""
    if len(text) > 2900:
        text = text[:2880] + "\n_…(truncated)_"
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}


def _build_fallback(company: dict, deal_info: dict, ml: dict) -> str:
    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"
    return (
        f"CSM Handoff Brief — {company['name']} ({acv_str}) · "
        f"Risk tier: {ml.get('risk_tier', 'average')} · "
        f"{ml.get('risk_multiplier', 1.0)}x avg churn"
    )
