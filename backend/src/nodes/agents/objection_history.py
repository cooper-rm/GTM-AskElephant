"""
Objection History Agent

Extracts objections from touches with attribution, then uses LLM
to analyze what they signal about risk — which are truly resolved
vs just parked, and what the CSM should watch for.

Two-step: Python extraction → LLM analysis.
"""
import json

from ...utils.llm import ask_claude


def run(deal: dict) -> dict:
    """
    Extract objection history and analyze what it reveals.

    Returns:
        objection_items (list), analysis (str), risk_signals (list),
        unresolved_concerns (list)
    """
    # Step 1: Python extraction
    all_objections = []
    seen_texts = set()

    for touch in deal.get('touches', []):
        objs = touch.get('objections', [])
        person = touch.get('person_name', 'Unknown')
        role = touch.get('person_role', 'unknown')

        for obj in objs:
            text = obj if isinstance(obj, str) else str(obj.get('objection', obj.get('text', str(obj))))
            text = text.strip()
            if not text:
                continue

            item = {
                'touch_number': touch.get('touch_number'),
                'touch_type': touch.get('type'),
                'date': touch.get('date'),
                'stage': touch.get('stage'),
                'raised_by': person,
                'raised_by_role': role,
                'objection': text,
            }
            all_objections.append(item)

    # Deduplicate on objection text
    deduplicated = []
    for obj in all_objections:
        key = obj['objection'].strip().lower()
        if key not in seen_texts:
            seen_texts.add(key)
            deduplicated.append(obj)

    # Step 2: LLM analysis — what do these objections signal?
    if not deduplicated:
        return {
            'objection_items': [],
            'analysis': 'No objections recorded in the deal history.',
            'risk_signals': [],
            'unresolved_concerns': [],
        }

    company = deal.get('company', {}).get('name', '?')
    obj_text = '\n'.join(
        f"  - Touch #{o['touch_number']} ({o['stage']}) — "
        f"{o['raised_by']} ({o['raised_by_role']}): \"{o['objection']}\""
        for o in deduplicated[:8]
    )

    prompt = f"""Analyze these objections raised during the sales process for {company}.
Don't just classify them as resolved/unresolved — read between the lines.
What does each objection REVEAL about the person's real concern?

An objection is rarely about what it literally says. "We don't want another tool" isn't
about tools — it's about change fatigue, or a champion who lacks authority to mandate
adoption. "Can you match Gong's price?" isn't about price — it might be a negotiation
tactic, or a signal they need budget ammunition for their CFO.

OBJECTIONS:
{obj_text}

Return ONLY valid JSON:
{{
  "analysis": "2-3 sentence summary of what the objection pattern reveals about this customer's psychology and deal dynamics",
  "risk_signals": [
    "What a specific objection IMPLIES about the person/deal beyond its surface meaning (e.g. 'Pricing objection from economic buyer late in cycle suggests expansion will face the same budget scrutiny — CSM should build ROI case early')",
    "Another signal reading between the lines"
  ],
  "unresolved_concerns": [
    "Objection that was acknowledged but not truly addressed — the underlying concern likely persists into post-sale"
  ]
}}

RULES:
- Read between the lines — what does each objection IMPLY about the person raising it?
- Pricing objections from a champion vs economic buyer mean different things
- "We need to involve IT" isn't about IT — it's about the champion not having sole authority
- Late-stage objections are higher signal because they survived the entire sales process
- An objection that was "handled" by offering a discount was bought off, not resolved
- Max 3 risk_signals, max 2 unresolved_concerns, each 1-2 sentences"""

    try:
        raw = ask_claude(prompt, "Output valid JSON only. No markdown.", timeout=30, model="haiku")
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        llm_result = json.loads(cleaned)
    except Exception:
        llm_result = {
            'analysis': f'{len(deduplicated)} unique objections recorded.',
            'risk_signals': [],
            'unresolved_concerns': [],
        }

    return {
        'objection_items': deduplicated,
        'analysis': llm_result.get('analysis', ''),
        'risk_signals': llm_result.get('risk_signals', []),
        'unresolved_concerns': llm_result.get('unresolved_concerns', []),
        'total_objections': len(all_objections),
        'unique_objections': len(deduplicated),
    }
