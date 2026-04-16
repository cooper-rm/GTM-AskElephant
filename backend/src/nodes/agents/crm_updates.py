"""
CRM Updates Agent

Generates structured CRM field updates to queue on the customer record.
Deterministic — no LLM needed. Maps deal data to CRM fields.
"""


def run(enriched_context: dict) -> dict:
    """
    Produce structured CRM updates from enriched context.
    Returns dict of CRM field → value.
    """
    deal = enriched_context['deal']
    risk = enriched_context['risk_narrative']
    ml = enriched_context.get('ml_context', {})

    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')
    has_exec = any(p['role'] == 'exec_sponsor' for p in deal['people'])

    return {
        'deal_id': deal['deal_id'],
        'hubspot_updates': {
            # Account-level
            'account_status': 'active',
            'account_segment': company['segment'],
            'account_industry': company['industry'],
            'account_employees': company['employee_count'],
            'account_arr': deal_info['amount'],

            # Deal-level
            'deal_stage': 'closed_won',
            'deal_seats': deal_info['seats'],
            'deal_product_tier': deal_info['product_tier'],
            'deal_use_case': deal_info['use_case'],
            'deal_competitor_replaced': deal_info['competitor'] if deal_info['competitor'] != 'None' else None,
            'deal_close_date': deal_info['close_date'],
            'deal_kickoff_date': deal_info.get('kickoff_date'),

            # Contacts
            'primary_champion': champion['name'],
            'champion_title': champion['title'],
            'exec_sponsor_engaged': has_exec,
            'num_stakeholders': len(deal['people']),

            # Risk signals from ML
            'churn_risk_score': ml.get('churn_risk_prob', 0),
            'risk_level': risk.get('risk_level', 'low'),
            'human_review_required': risk.get('risk_level') in ('high',),
        },
        'tasks_to_create': [
            {
                'task': 'Schedule kickoff meeting',
                'due_days': 3,
                'assigned_to': 'CSM',
            },
            {
                'task': f'First check-in with {champion["name"]}',
                'due_days': 14,
                'assigned_to': 'CSM',
            },
            {
                'task': 'Day-30 value review',
                'due_days': 30,
                'assigned_to': 'CSM',
            },
        ],
    }
