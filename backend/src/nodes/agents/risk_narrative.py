"""
Risk Narrative Agent

Turns XGBoost churn score + nearest neighbor outcomes into
plain-English risk assessment for the CS team.

Uses LLM to translate ML outputs into human language.
"""
import json

from ...utils.llm import ask_claude


def run(deal: dict, ml_context: dict) -> dict:
    """
    Generate plain-English risk narrative.

    Input:
        deal: full deal record
        ml_context: {
            'churn_risk_prob': float,
            'top_risk_factors': list of (feature, shap_value),
            'nearest_neighbors': list of neighbor dicts with outcomes,
        }

    Output:
        {summary, similar_deal_patterns, watch_for, recommended_actions, risk_level, ...}
    """
    churn_prob = ml_context.get('churn_risk_prob', 0)
    top_factors = ml_context.get('top_risk_factors', [])
    neighbors = ml_context.get('nearest_neighbors', [])

    nn_churned = [n for n in neighbors if n.get('outcome') == 'churned']
    nn_churn_rate = len(nn_churned) / max(len(neighbors), 1)

    if churn_prob >= 0.5:
        risk_level = 'high'
    elif churn_prob >= 0.25:
        risk_level = 'medium'
    else:
        risk_level = 'low'

    top_factors_str = '\n'.join([
        f"  - {name}: {val:+.3f} ({'increases' if val > 0 else 'reduces'} risk)"
        for name, val in top_factors[:5]
    ])

    similar_str = '\n'.join([
        f"  - {n.get('company_name')} ({n.get('segment')}, ${n.get('amount'):,.0f}): "
        f"{n.get('outcome')}" +
        (f" at day {n.get('days_to_churn')}" if n.get('days_to_churn') else '') +
        (f" — reason: {n.get('churn_reason')}" if n.get('churn_reason') else '')
        for n in neighbors[:5]
    ])

    prompt = f"""You are generating a concise risk narrative for a CSM handoff package.

DEAL:
- Company: {deal['company']['name']} ({deal['company']['segment']}, {deal['company']['industry']})
- ACV: ${deal['deal']['amount']:,.0f}, {deal['deal']['seats']} seats
- Use case: {deal['deal']['use_case']}

ML OUTPUT:
- Churn risk probability: {churn_prob:.1%} ({risk_level} risk)
- Top features driving this prediction:
{top_factors_str}

SIMILAR HISTORICAL DEALS (nearest neighbors):
{similar_str}
- {len(nn_churned)}/{len(neighbors)} similar deals churned

Write a short risk narrative (3-5 sentences) that:
1. Plainly states the risk level and why
2. References specific patterns from similar deals that churned (if any)
3. Identifies 2-3 specific things the CSM should watch for
4. Uses language a CSM would understand — no ML jargon

Also provide 2-3 concrete recommended actions for the first 14 days.

Output ONLY valid JSON:
{{
  "summary": "3-5 sentence plain-English risk assessment",
  "similar_deal_patterns": ["pattern 1", "pattern 2"],
  "watch_for": ["signal 1", "signal 2", "signal 3"],
  "recommended_actions": ["action 1", "action 2", "action 3"],
  "risk_level": "{risk_level}"
}}"""

    try:
        raw = ask_claude(prompt, "Output valid JSON only. No markdown.", timeout=60, model="sonnet")
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = cleaned.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        narrative = json.loads(cleaned)
    except Exception:
        narrative = {
            'summary': f'Churn risk is {risk_level} ({churn_prob:.1%}). Based on top factors and similar deals.',
            'similar_deal_patterns': [],
            'watch_for': [],
            'recommended_actions': [],
            'risk_level': risk_level,
        }

    narrative['churn_risk_prob'] = churn_prob
    narrative['nn_churn_rate'] = round(nn_churn_rate, 3)
    narrative['top_risk_factors'] = [list(f) for f in top_factors[:5]]

    return narrative
