"""
Feature Engineer Node

Takes a raw deal record (matching deal_schema.json) and computes
all derived features for downstream ML models.

Input: raw deal JSON
Output: flat feature dictionary ready for XGBoost + embedding
"""
from datetime import datetime


# --- Sentiment mapping ---
SENTIMENT_MAP = {
    'positive': 1.0,
    'neutral': 0.5,
    'cautious': 0.25,
    'negative': 0.0,
    'no_contact': None,
    'unknown': None,
}

# --- Competitor encoding ---
KNOWN_COMPETITORS = ['Gong', 'Fathom', 'Fireflies', 'Clari', 'Chorus']

# --- Industry encoding ---
KNOWN_INDUSTRIES = [
    'SaaS/Tech', 'Marketing Agency', 'Fintech', 'PropTech',
    'Healthcare IT', 'EdTech', 'eCommerce', 'Managed IT/Cybersecurity',
    'Professional Services', 'Vertical SaaS',
]


def engineer_features(deal: dict) -> dict:
    """
    Transform raw deal record into model-ready features.
    Only computes — never modifies the original deal.
    """
    features = {'deal_id': deal['deal_id']}

    features.update(compute_deal_features(deal['deal']))
    features.update(compute_people_features(deal['people']))
    features.update(compute_touch_features(deal['touches'], deal['deal']['close_date']))
    features.update(compute_response_features(deal['touches']))
    features.update(compute_engagement_features(deal['touches']))
    features.update(compute_company_features(deal['company']))

    return features


# --- Deal-derived features ---

def compute_deal_features(deal: dict) -> dict:
    """Compute deal-level derived features."""
    list_price = 89.0
    price = deal.get('price_per_seat_monthly', list_price)

    features = {
        'amount': deal['amount'],
        'seats': deal['seats'],
        'price_per_seat': price,
        'discount_vs_list': round((list_price - price) / list_price, 3),
        'is_inbound': 1 if deal.get('lead_source') == 'inbound' else 0,
        'product_tier_encoded': 1 if deal.get('product_tier') == 'automations_plus_consulting' else 0,
    }

    # Competitor one-hot encoding
    competitor = deal.get('competitor', 'None')
    features['has_competitor'] = 1 if competitor != 'None' else 0
    for comp in KNOWN_COMPETITORS:
        features[f'competitor_{comp.lower()}'] = 1 if competitor == comp else 0

    return features


# --- People-derived features ---

def compute_people_features(people: list[dict]) -> dict:
    """Compute stakeholder-level features."""
    roles = [p['role'] for p in people]
    champion = next((p for p in people if p['role'] == 'champion'), None)

    return {
        'num_stakeholders': len(people),
        'has_exec_sponsor': 1 if 'exec_sponsor' in roles else 0,
        'has_technical_evaluator': 1 if 'technical_evaluator' in roles else 0,
        'champion_tenure_months': champion['tenure_months'] if champion else 0,
        'unique_roles_count': len(set(roles)),
        'is_single_threaded': 1 if len(people) <= 1 else 0,
    }


# --- Touch-derived features ---

def compute_touch_features(touches: list[dict], close_date_str: str) -> dict:
    """Aggregate touch-level observations into deal-level features."""
    if not touches:
        return _empty_touch_features()

    close_date = datetime.strptime(close_date_str, '%Y-%m-%d')

    prospect_touches = [t for t in touches if t['stage'] == 'prospecting']
    active_touches = [t for t in touches if t['stage'] != 'prospecting']
    call_touches = [t for t in touches if t['duration_minutes'] > 0]
    email_touches = [t for t in touches if t['type'] in
                     ('cold_email', 'follow_up_email', 'linkedin_message')]

    # Sales cycle from first touch to close
    dates = sorted([datetime.strptime(t['date'], '%Y-%m-%d') for t in touches])
    sales_cycle_days = (close_date - dates[0]).days if dates else 0

    # Gaps between consecutive touches
    gaps = []
    for i in range(1, len(dates)):
        gap = (dates[i] - dates[i-1]).days
        gaps.append(gap)

    # Touch frequency trend: first half avg gap vs second half
    touch_frequency_trend = 0.0
    if len(gaps) >= 4:
        mid = len(gaps) // 2
        first_half_avg = sum(gaps[:mid]) / mid
        second_half_avg = sum(gaps[mid:]) / (len(gaps) - mid)
        if first_half_avg > 0:
            # Positive = accelerating (gaps shrinking)
            touch_frequency_trend = round(
                (first_half_avg - second_half_avg) / first_half_avg, 3)

    n_reschedules = sum(1 for t in touches if t.get('rescheduled'))
    call_durations = [t['duration_minutes'] for t in call_touches]

    return {
        'total_touches': len(touches),
        'sdr_attempts': len(prospect_touches),
        'active_touches': len(active_touches),
        'total_call_minutes': sum(call_durations),
        'avg_call_duration': round(
            sum(call_durations) / len(call_durations), 1) if call_durations else 0,
        'n_calls': len(call_touches),
        'n_emails': len(email_touches),
        'calls_to_emails_ratio': round(
            len(call_touches) / max(len(email_touches), 1), 2),
        'sales_cycle_days': sales_cycle_days,
        'avg_days_between_touches': round(
            sum(gaps) / len(gaps), 1) if gaps else 0,
        'longest_gap_days': max(gaps) if gaps else 0,
        'touch_frequency_trend': touch_frequency_trend,
        'n_reschedules': n_reschedules,
    }


def _empty_touch_features() -> dict:
    """Return zeroed touch features when no touches exist."""
    return {
        'total_touches': 0, 'sdr_attempts': 0, 'active_touches': 0,
        'total_call_minutes': 0, 'avg_call_duration': 0, 'n_calls': 0,
        'n_emails': 0, 'calls_to_emails_ratio': 0, 'sales_cycle_days': 0,
        'avg_days_between_touches': 0, 'longest_gap_days': 0,
        'touch_frequency_trend': 0, 'n_reschedules': 0,
    }


# --- Response features ---

def compute_response_features(touches: list[dict]) -> dict:
    """Compute response rate, avg response time, etc."""
    if not touches:
        return {'response_rate': 0, 'avg_response_time_hours': 0,
                'fastest_response_hours': 0, 'sdr_attempts_before_connect': 0}

    responded = [t for t in touches if t.get('got_response')]
    response_times = [t['response_time_hours'] for t in touches
                      if t.get('response_time_hours') is not None]

    # SDR attempts before first connection
    prospect_touches = [t for t in touches if t['stage'] == 'prospecting']
    sdr_before_connect = 0
    for t in prospect_touches:
        if not t.get('got_response'):
            sdr_before_connect += 1
        else:
            break

    return {
        'response_rate': round(len(responded) / max(len(touches), 1), 3),
        'avg_response_time_hours': round(
            sum(response_times) / len(response_times), 1) if response_times else 0,
        'fastest_response_hours': round(
            min(response_times), 1) if response_times else 0,
        'sdr_attempts_before_connect': sdr_before_connect,
    }


# --- Engagement features (from AI-processed content) ---

def compute_engagement_features(touches: list[dict]) -> dict:
    """Aggregate sentiment, questions, objections across touches."""
    sentiments = []
    total_questions = 0
    prospect_questions = 0
    total_objections = 0
    objection_texts = set()

    for t in touches:
        s = SENTIMENT_MAP.get(t.get('sentiment'), None)
        if s is not None:
            sentiments.append(s)

        questions = t.get('questions_asked', [])
        total_questions += len(questions)
        prospect_questions += sum(
            1 for q in questions if q.get('by') == 'prospect')

        objs = t.get('objections', [])
        total_objections += len(objs)
        for o in objs:
            # Handle both string and dict objections from LLM
            if isinstance(o, str):
                objection_texts.add(o)
            elif isinstance(o, dict):
                objection_texts.add(str(o.get('objection', o.get('text', str(o)))))

    # Sentiment trend: second half avg minus first half avg
    sentiment_trend = 0.0
    if len(sentiments) >= 4:
        mid = len(sentiments) // 2
        first_avg = sum(sentiments[:mid]) / mid
        second_avg = sum(sentiments[mid:]) / (len(sentiments) - mid)
        sentiment_trend = round(second_avg - first_avg, 3)

    return {
        'avg_sentiment_score': round(
            sum(sentiments) / len(sentiments), 3) if sentiments else 0.5,
        'sentiment_trend': sentiment_trend,
        'total_questions_asked': total_questions,
        'prospect_questions_count': prospect_questions,
        'total_objections': total_objections,
        'unique_objection_themes': len(objection_texts),
    }


# --- Company features ---

def compute_company_features(company: dict) -> dict:
    """Compute company-level features."""
    employees = company.get('employee_count', 1)
    revenue = company.get('annual_revenue', 0)

    features = {
        'employee_count': employees,
        'annual_revenue': revenue,
        'revenue_per_employee': round(revenue / max(employees, 1)),
    }

    # Industry one-hot encoding
    industry = company.get('industry', '')
    for ind in KNOWN_INDUSTRIES:
        key = f"industry_{ind.lower().replace('/', '_').replace(' ', '_')}"
        features[key] = 1 if industry == ind else 0

    return features
