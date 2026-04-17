"""
Neighbor Analysis Agent

Takes the 5 nearest neighbors from HNSW retrieval and uses LLM to
analyze patterns — not just "3 churned" but WHY, what the outcomes
reveal about this type of deal, and what's specifically actionable
for the CSM handling this new deal.

Two-step: structured neighbor data → LLM pattern analysis.
"""
import json

from ...utils.llm import ask_claude


def run(deal: dict, ml_context: dict) -> dict:
    """
    Analyze nearest neighbor outcomes for actionable patterns.

    Returns:
        neighbors (list), pattern_analysis (str),
        actionable_insights (list), warning_signals (list)
    """
    neighbors = ml_context.get('nearest_neighbors', [])
    nn_churn_rate = ml_context.get('nn_churn_rate', 0)
    risk_tier = ml_context.get('risk_tier', 'average')

    if not neighbors:
        return {
            'neighbors': [],
            'pattern_analysis': 'No similar historical deals found.',
            'actionable_insights': [],
            'warning_signals': [],
            'churn_rate': 0,
        }

    company = deal.get('company', {}).get('name', '?')
    deal_info = deal.get('deal', {})

    # Format neighbor details for LLM
    neighbor_text = []
    for i, n in enumerate(neighbors):
        outcome = n.get('outcome', '?')
        churn_info = ''
        if outcome == 'churned':
            churn_info = (
                f", churned at day {n.get('days_to_churn', '?')}"
                f", reason: {n.get('churn_reason', 'unknown')}"
            )
        elif outcome == 'expanded':
            churn_info = ", expanded after initial contract"

        neighbor_text.append(
            f"  {i+1}. {n.get('company_name', '?')} ({n.get('segment', '?')}, "
            f"${n.get('amount', 0):,.0f}) — {outcome}{churn_info} "
            f"[similarity: {1/(1+n.get('distance', 1)):.0%}]"
        )
    neighbors_str = '\n'.join(neighbor_text)

    churned = [n for n in neighbors if n.get('outcome') == 'churned']
    retained = [n for n in neighbors if n.get('outcome') in ('retained', 'expanded')]

    prompt = f"""Analyze these 5 historical deals that are most similar to a new deal for {company}.
Read between the lines — what do these outcomes REVEAL about deals like this one?

NEW DEAL (for context):
- {company}, {deal.get('company', {}).get('segment', '?')}, ${deal_info.get('amount', 0):,.0f}
- Use case: {deal_info.get('use_case', '?')}
- Risk tier: {risk_tier}
- Competitor replaced: {deal_info.get('competitor', 'None')}

5 NEAREST NEIGHBORS (most similar historical deals):
{neighbors_str}

Churn rate among neighbors: {nn_churn_rate:.0%} ({len(churned)} churned, {len(retained)} retained/expanded)

Return ONLY valid JSON:
{{
  "pattern_analysis": "3-4 sentence analysis of what these neighbor outcomes reveal about deals like this one. Don't just count churned vs retained — analyze WHY. What do the churned deals have in common? What did the retained deals do differently? What does the similarity score tell you about how predictive these neighbors are?",
  "actionable_insights": [
    "Specific thing the CSM should DO based on what worked for the retained neighbors or what killed the churned ones (e.g. 'Both retained neighbors had exec reviews by day 14 — schedule one immediately')",
    "Another actionable insight grounded in the neighbor data"
  ],
  "warning_signals": [
    "Specific pattern from churned neighbors that this deal shows early signs of (e.g. 'Two churned neighbors had the same segment + no exec sponsor pattern — this deal matches')",
    "Another warning if warranted"
  ],
  "neighbor_highlights": [
    {{"company": "name", "outcome": "churned/retained/expanded", "key_detail": "the ONE most important thing about this neighbor's story that's relevant to the new deal"}},
    {{"company": "name", "outcome": "...", "key_detail": "..."}}
  ]
}}

RULES:
- Every insight must reference a SPECIFIC neighbor by name
- Don't just restate the data — interpret it. What does the pattern MEAN for this deal?
- If churn reasons cluster (e.g. all "low adoption"), that's a strong signal worth flagging
- If a retained neighbor has a very similar profile, its success pattern is a playbook to follow
- Max 3 actionable_insights, 2 warning_signals, 5 neighbor_highlights"""

    try:
        raw = ask_claude(prompt, "Output valid JSON only. No markdown.", timeout=45, model="haiku")
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        llm_result = json.loads(cleaned)
    except Exception:
        llm_result = {
            'pattern_analysis': (
                f"{len(churned)}/{len(neighbors)} similar deals churned. "
                f"Neighbor churn rate: {nn_churn_rate:.0%}."
            ),
            'actionable_insights': [],
            'warning_signals': [],
            'neighbor_highlights': [],
        }

    return {
        'neighbors': neighbors,
        'churn_rate': nn_churn_rate,
        'pattern_analysis': llm_result.get('pattern_analysis', ''),
        'actionable_insights': llm_result.get('actionable_insights', []),
        'warning_signals': llm_result.get('warning_signals', []),
        'neighbor_highlights': llm_result.get('neighbor_highlights', []),
    }
