"""
Q&A History Agent

Aggregates questions and answers across all touches in a deal.
Identifies open/unresolved questions.

Woody's principle: "Never ask the customer the same question twice."
This agent ensures CS has the full Q&A history at handoff.

Pure Python — no LLM call needed.
"""


def run(deal: dict) -> dict:
    """
    Extract and structure Q&A history from all touches.

    Returns:
        total_qa_pairs, unique_qa_pairs, qa_history (list),
        open_questions, prospect_questions, rep_questions
    """
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
                'asked_by': q.get('by'),
                'question': q.get('question'),
                'answer': q.get('answer'),
            }
            all_qas.append(qa_item)

            # Detect unresolved — empty or placeholder answer
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

    return {
        'total_qa_pairs': len(all_qas),
        'unique_qa_pairs': len(deduplicated),
        'qa_history': deduplicated,
        'open_questions': open_questions,
        'prospect_questions': [qa for qa in deduplicated if qa.get('asked_by') == 'prospect'],
        'rep_questions': [qa for qa in deduplicated if qa.get('asked_by') == 'rep'],
    }
