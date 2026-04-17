"""
Q&A History Agent

Extracts Q&A exchanges from touches, then uses LLM to analyze
what the questions reveal about the customer's priorities,
knowledge gaps, and expectations.

Two-step: Python extraction → LLM analysis.
"""
import json

from ...utils.llm import ask_claude


def run(deal: dict) -> dict:
    """
    Extract Q&A history and analyze what it reveals.

    Returns:
        qa_items (list), analysis (str), key_insights (list),
        open_questions (list)
    """
    # Step 1: Python extraction
    all_qas = []
    open_questions = []

    for touch in deal.get('touches', []):
        questions = touch.get('questions_asked', [])
        for q in questions:
            if not isinstance(q, dict):
                continue

            qa_item = {
                'touch_number': touch.get('touch_number'),
                'touch_type': touch.get('type'),
                'date': touch.get('date'),
                'stage': touch.get('stage'),
                'asked_by': q.get('by'),
                'question': q.get('question'),
                'answer': q.get('answer'),
            }
            all_qas.append(qa_item)

            answer = (q.get('answer') or '').strip().lower()
            if not answer or answer in ('tbd', 'unknown', 'follow up', 'to be determined'):
                open_questions.append(q.get('question'))

    # Deduplicate on exact question match
    seen = set()
    deduplicated = []
    for qa in all_qas:
        key = (qa['question'] or '').strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduplicated.append(qa)

    # Step 2: LLM analysis — what do these questions reveal?
    if not deduplicated:
        return {
            'qa_items': [],
            'analysis': 'No Q&A exchanges recorded in the deal history.',
            'key_insights': [],
            'open_questions': open_questions,
        }

    company = deal.get('company', {}).get('name', '?')
    qa_text = '\n'.join(
        f"  - Touch #{q['touch_number']} ({q['stage']}) [{q['asked_by']}]: "
        f"\"{q['question']}\" → \"{q['answer']}\""
        for q in deduplicated[:12]
    )

    prompt = f"""Analyze these Q&A exchanges from the sales process for {company}.
Don't just summarize what was asked — read between the lines. What do the questions
REVEAL about this customer's mindset, priorities, and hidden concerns?

A question is often not about its literal answer. Someone asking "what's your uptime SLA?"
is really telling you they've been burned by downtime before. Someone asking about
references is signaling they need social proof to build internal consensus.

Q&A HISTORY:
{qa_text}

Return ONLY valid JSON:
{{
  "analysis": "2-3 sentence summary of what the Q&A pattern reveals about this customer's psychology and buying motivations",
  "key_insights": [
    "What a specific question IMPLIES about the person's mindset — not what they asked, but what it reveals (e.g. 'Champion asking about quarterly reporting suggests they need visible wins to justify the purchase internally')",
    "Another insight reading between the lines"
  ]
}}

RULES:
- Read between the lines — what does each question IMPLY about the asker's situation?
- Early pricing questions → budget pressure or need for internal ROI justification
- Integration/security questions → prior bad vendor experience or IT gatekeeping
- Timeline questions → external deadline driving urgency (or lack of it)
- "Who else uses this?" questions → needs social proof, may lack internal authority
- Questions about implementation support → anticipating adoption friction
- Max 3 key_insights, each 1-2 sentences, specific to THIS customer's context"""

    try:
        raw = ask_claude(prompt, "Output valid JSON only. No markdown.", timeout=30, model="haiku")
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        llm_result = json.loads(cleaned)
    except Exception:
        llm_result = {
            'analysis': f'{len(deduplicated)} Q&A exchanges recorded across {len(set(q["touch_number"] for q in deduplicated))} touches.',
            'key_insights': [],
        }

    return {
        'qa_items': deduplicated,
        'analysis': llm_result.get('analysis', ''),
        'key_insights': llm_result.get('key_insights', []),
        'open_questions': open_questions,
        'total_qa_pairs': len(all_qas),
        'unique_qa_pairs': len(deduplicated),
        'prospect_questions': [qa for qa in deduplicated if qa.get('asked_by') == 'prospect'],
        'rep_questions': [qa for qa in deduplicated if qa.get('asked_by') == 'rep'],
    }
