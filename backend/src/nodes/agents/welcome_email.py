"""
Welcome Email Agent

Generates a customer-facing welcome email in AskElephant's voice.
Personalized to use case, references champion, sets expectations.
"""
from ...utils.llm import ask_claude


def run(enriched_context: dict) -> str:
    """
    Generate welcome email from enriched context.
    Returns email content as a string.
    """
    deal = enriched_context['deal']
    risk = enriched_context['risk_narrative']
    qa = enriched_context.get('qa_history', {})
    objections = enriched_context.get('objection_history', {})

    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')

    # Pretty tier label — never leak snake_case into customer-facing copy
    tier_key = deal_info.get('product_tier', '')
    tier_label = {
        'unlimited_automation': 'Unlimited Automation',
        'automations_plus_consulting': 'Automations + AI Consulting',
    }.get(tier_key, tier_key.replace('_', ' ').title())

    # Personalization signals from deal cycle analysis
    qa_insights = qa.get('key_insights', [])[:2]
    obj_insights = objections.get('risk_signals', [])[:2]
    personalization_context = ""
    if qa_insights or obj_insights:
        signals = []
        if qa_insights:
            signals.append("Q&A insights: " + "; ".join(qa_insights))
        if obj_insights:
            signals.append("Objection insights: " + "; ".join(obj_insights))
        personalization_context = f"""
PERSONALIZATION (use ONE of these to make the email feel specific to this customer):
{chr(10).join(signals)}
Pick the most relevant detail and weave it naturally into the welcoming sentence
or one of the three steps. Do NOT list it — incorporate it as if you already know
their situation. Example: instead of "help your team" say "help your reps get
those 10 hours back" if they mentioned manual work taking 10 hours.
"""

    prompt = f"""Write a welcome email from AskElephant to a new customer.
Follow the EXACT structure of the example below — every welcome email should feel this way.

DEAL CONTEXT:
- Customer: {company['name']} ({company['industry']}, {company['employee_count']} employees)
- Champion: {champion['name']}, {champion['title']}
- Product: {tier_label} ({deal_info['seats']} seats)
- Primary use case: {deal_info['use_case']}
- Risk level: {risk.get('risk_level', 'low')}
{personalization_context}

TONE: warm, direct, confident. AskElephant's voice — action-oriented, never fluffy, never corporate.

EXAMPLE of the exact structure to follow (this is gold-standard — replicate its rhythm):

Subject: Welcome to AskElephant, David

David,

Welcome to AskElephant. You're now set up with unlimited automation across 4 seats to help your reps move faster and close more deals.

Here's what happens next:

First, we'll send you login credentials for your team within the next hour. Forward those to your reps so they can get started right away.

Second, your CSM will be in touch shortly to book a kickoff call. We'll walk through your rep productivity goals and configure the system to match how your team works.

Third, expect to see your first automated workflows live within 48 hours of kickoff. We move fast so your team can too.

If you need anything before then, just reply to this email.

The AskElephant Team

---

STRUCTURAL RULES (match the example):
1. Subject: "Welcome to AskElephant, <first-name>"
2. First-name-only greeting on its own line
3. ONE welcoming sentence confirming what they bought + why it helps — tailor to their use case
4. "Here's what happens next:" on its own line
5. EXACTLY three steps starting with "First,", "Second,", "Third," — each 1-2 sentences, concrete and action-oriented. The three steps should cover: (a) immediate access/credentials, (b) CSM kickoff call, (c) first-value expectation tied to their use case
6. One short closing line inviting reply ("If you need anything before then, just reply to this email.")
7. Sign off EXACTLY as: The AskElephant Team

STRICT CONTENT RULES:
- Plain text only. NO markdown, NO asterisks, NO hash marks, NO underscores, NO backticks, NO emojis.
- NO placeholder tokens like "[calendar link]" or "[CSM name]". Omit rather than leave a placeholder.
- NO dates or specific calendar times — the CSM books the kickoff.
- NO "we are excited to" or "thank you for choosing us" — skip corporate openers.
- NO sign-off name other than "The AskElephant Team". Do not invent a signer.
- Total body (including subject) under 160 words."""

    return ask_claude(
        prompt,
        "You write concise, action-oriented customer emails. No fluff.",
        timeout=60,
        model="sonnet",
    )
