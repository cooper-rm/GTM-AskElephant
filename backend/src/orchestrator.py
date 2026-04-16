"""
Pipeline Orchestrator

Wires together the full Closed-Won Activation pipeline:

1. Validate input (deal record matches schema)
2. Feature engineering
3. ML scoring (XGBoost + HNSW) → ML context package
4. Analysis agents (Q&A History + Risk Narrative) → Enriched context
5. Output agents — two-wave execution:
     Wave 1 (parallel): welcome_email, slack_announce, csm_brief, kickoff_draft, crm_updates
     Wave 2 (sequential, after Wave 1): success_plan — consumes csm_brief.structured
6. Delivery (send email, post Slack, push CRM)
7. Generate + email PDF handoff package (brief + plan + kickoff)

Returns the complete handoff package.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from .nodes.feature_engineer import engineer_features
from .nodes.xgb_scoring import predict_churn
from .nodes.nn_retrieval import query_neighbors, compute_nn_churn_rate
from .nodes.risk_calibration import calibrate_risk

from .nodes.agents import qa_history, risk_narrative
from .nodes.agents import welcome_email, slack_announce, csm_brief
from .nodes.agents import kickoff_draft, crm_updates, success_plan
from .nodes.agents import delivery
from .utils.invoice_pdf import generate_invoice_pdf
from .utils.pdf_brief import generate_brief_pdf
from .utils.pdf_plan import generate_plan_pdf
from .utils.pdf_kickoff import generate_kickoff_pdf


def run_pipeline(deal: dict, csm_email: str = 'askelephantdemo@gmail.com') -> dict:
    """
    Run the full activation pipeline on a deal record.
    Returns a dict with handoff artifacts + delivery status + manifest.
    """
    started_at = datetime.utcnow().isoformat()
    deal_id = deal['deal_id']

    # Step 1: Feature engineering
    features = engineer_features(deal)

    # Step 2: ML scoring
    xgb_result = predict_churn(features)
    neighbors = query_neighbors(features, k=5, alpha=4.0)

    # Calibrate raw XGB output into interpretable risk multiplier
    risk_cal = calibrate_risk(xgb_result['churn_risk_prob'])

    ml_context = {
        'churn_risk_prob': xgb_result['churn_risk_prob'],
        'risk_multiplier': risk_cal['risk_multiplier'],
        'risk_tier': risk_cal['risk_tier'],
        'risk_interpretation': risk_cal['interpretation'],
        'base_rate': risk_cal['base_rate'],
        'top_risk_factors': xgb_result['top_risk_factors'],
        'shap_values': xgb_result['shap_values'],
        'nearest_neighbors': neighbors,
        'nn_churn_rate': compute_nn_churn_rate(neighbors),
    }

    # Step 3: Analysis agents
    qa_result = qa_history.run(deal)
    risk_result = risk_narrative.run(deal, ml_context)

    enriched_context = {
        'deal': deal,
        'ml_context': ml_context,
        'qa_history': qa_result,
        'risk_narrative': risk_result,
    }

    # Step 4: Output agents — Wave 1 in parallel, then success_plan in Wave 2
    artifacts = _run_output_agents_two_wave(enriched_context)

    # Step 5: Delivery
    champion = next(p for p in deal['people'] if p['role'] == 'champion')
    # In test mode (default), route ALL emails to csm_email for visibility.
    # In production, set TEST_MODE=false to route customer emails to real addresses.
    test_mode = os.environ.get('TEST_MODE', 'true').lower() != 'false'
    if test_mode:
        champion_email = csm_email
    else:
        champion_email = f"{champion['name'].lower().replace(' ', '.')}@{deal['company']['name'].lower()}.com"

    # Generate invoice PDF for the welcome email attachment
    try:
        invoice_bytes = generate_invoice_pdf(deal)
        invoice_attachment = [(
            f"AskElephant_Invoice_{deal_id}.pdf",
            invoice_bytes,
            'application/pdf',
        )]
    except Exception as e:
        print(f"[invoice] PDF generation failed: {e}")
        invoice_attachment = None

    delivery_results = {
        'welcome_email': delivery.send_email(
            deal_id, champion_email, artifacts['welcome_email'],
            subject_hint='Welcome to AskElephant',
            attachments=invoice_attachment,
        ),
        'slack_announce': delivery.post_slack(
            deal_id, '#closed-won-announcements', artifacts['slack_announce']
        ),
        'csm_brief': delivery.save_csm_brief(
            deal_id, artifacts['csm_brief']
        ),
        'kickoff_draft': delivery.save_kickoff_draft(
            deal_id, artifacts['kickoff_draft']
        ),
        'crm_updates': delivery.push_crm_updates(
            deal_id, artifacts['crm_updates']
        ),
        'success_plan': delivery.save_success_plan(
            deal_id, artifacts['success_plan']
        ),
    }

    # Step 6: Generate PDF handoff package (Brief + Plan + Kickoff) and email to CSM
    pdf_results = _generate_and_deliver_package(
        deal=deal,
        deal_id=deal_id,
        ml_context=ml_context,
        artifacts=artifacts,
        csm_email=csm_email,
    )
    delivery_results['handoff_package'] = pdf_results

    return {
        'deal_id': deal_id,
        'started_at': started_at,
        'completed_at': datetime.utcnow().isoformat(),
        'ml_context': ml_context,
        'artifacts': artifacts,
        'delivery': delivery_results,
    }


def _run_output_agents_two_wave(enriched_context: dict) -> dict:
    """
    Two-wave execution:
      Wave 1 (parallel): all agents except success_plan
      Wave 2 (sequential): success_plan, which receives csm_brief.structured
                           in its enriched_context so it can reference the
                           synthesized customer context and risks when
                           drafting the plan.
    """
    wave1_agents = {
        'welcome_email': welcome_email.run,
        'slack_announce': slack_announce.run,
        'csm_brief': csm_brief.run,
        'kickoff_draft': kickoff_draft.run,
        'crm_updates': crm_updates.run,
    }

    results: dict = {}
    with ThreadPoolExecutor(max_workers=len(wave1_agents)) as pool:
        futures = {name: pool.submit(fn, enriched_context) for name, fn in wave1_agents.items()}
        for name, future in futures.items():
            try:
                results[name] = future.result(timeout=180)
            except Exception as e:
                results[name] = f'[Agent failed: {e}]'

    # Wave 2 — success_plan consumes csm_brief.structured if available
    brief_artifact = results.get('csm_brief')
    brief_structured = (
        brief_artifact.get('structured')
        if isinstance(brief_artifact, dict) else None
    )
    plan_context = {**enriched_context, 'csm_brief_structured': brief_structured}

    try:
        results['success_plan'] = success_plan.run(plan_context)
    except Exception as e:
        results['success_plan'] = f'[Agent failed: {e}]'

    return results


def _generate_and_deliver_package(
    deal: dict,
    deal_id: str,
    ml_context: dict,
    artifacts: dict,
    csm_email: str,
) -> dict:
    """
    Generate the 3 handoff PDFs from structured artifacts, persist to
    data/runs/{deal_id}/, and email them to the CSM as a single package.
    Tolerates individual PDF failures — whatever rendered successfully
    gets bundled.
    """
    run_dir = os.path.join(
        os.path.dirname(__file__), "../data/runs", deal_id,
    )
    os.makedirs(run_dir, exist_ok=True)

    company_name = deal['company']['name']
    pdfs: list = []
    pdf_status = {}

    # Brief PDF
    brief = artifacts.get('csm_brief')
    if isinstance(brief, dict) and brief.get('structured'):
        try:
            data = generate_brief_pdf(deal, ml_context, brief['structured'])
            fname = f"01_Handoff_Brief_{deal_id}.pdf"
            with open(os.path.join(run_dir, fname), 'wb') as f:
                f.write(data)
            pdfs.append((fname, data))
            pdf_status['brief'] = 'ok'
        except Exception as e:
            pdf_status['brief'] = f'failed: {e}'
            print(f"[pdf] brief PDF failed: {e}")
    else:
        pdf_status['brief'] = 'skipped: no structured brief'

    # Plan PDF
    plan = artifacts.get('success_plan')
    if isinstance(plan, dict) and plan.get('structured'):
        try:
            data = generate_plan_pdf(deal, plan['structured'])
            fname = f"02_Success_Plan_{deal_id}.pdf"
            with open(os.path.join(run_dir, fname), 'wb') as f:
                f.write(data)
            pdfs.append((fname, data))
            pdf_status['plan'] = 'ok'
        except Exception as e:
            pdf_status['plan'] = f'failed: {e}'
            print(f"[pdf] plan PDF failed: {e}")
    else:
        pdf_status['plan'] = 'skipped: no structured plan'

    # Kickoff draft PDF
    kickoff = artifacts.get('kickoff_draft')
    if isinstance(kickoff, dict) and kickoff.get('structured'):
        try:
            data = generate_kickoff_pdf(deal, kickoff['structured'])
            fname = f"03_Kickoff_Draft_{deal_id}.pdf"
            with open(os.path.join(run_dir, fname), 'wb') as f:
                f.write(data)
            pdfs.append((fname, data))
            pdf_status['kickoff'] = 'ok'
        except Exception as e:
            pdf_status['kickoff'] = f'failed: {e}'
            print(f"[pdf] kickoff PDF failed: {e}")
    else:
        pdf_status['kickoff'] = 'skipped: no structured kickoff'

    if not pdfs:
        return {
            'status': 'skipped',
            'reason': 'no PDFs generated',
            'pdf_status': pdf_status,
        }

    subject, body = _compose_handoff_email(deal, pdfs)

    send_result = delivery.send_handoff_package(
        deal_id=deal_id,
        recipient=csm_email,
        subject=subject,
        body=body,
        pdfs=pdfs,
    )
    send_result['pdf_status'] = pdf_status
    return send_result


def _compose_handoff_email(deal: dict, pdfs: list) -> tuple:
    """
    Compose a clean handoff-package email for the CSM: one-line intro,
    three attached docs with purpose descriptions, sign-off.
    """
    company = deal['company']
    deal_info = deal['deal']
    champion = next(p for p in deal['people'] if p['role'] == 'champion')

    amount = deal_info.get('amount', 0)
    acv_str = f"${amount/1000:.1f}K" if amount >= 1000 else f"${amount:,.0f}"

    subject = f"Handoff: {company['name']} — {acv_str} closed-won ({deal['deal_id']})"

    # Map filename prefix to one-line description
    doc_lines = []
    for fname, _ in pdfs:
        if fname.startswith('01_'):
            doc_lines.append(
                f"  1.  {fname}\n"
                f"       Customer context, stakeholders, objections, and risk assessment. Start here."
            )
        elif fname.startswith('02_'):
            doc_lines.append(
                f"  2.  {fname}\n"
                f"       Recommended week-by-week plan with success criteria and expected outputs."
            )
        elif fname.startswith('03_'):
            doc_lines.append(
                f"  3.  {fname}\n"
                f"       Ready-to-edit email draft proposing a kickoff call with {champion['name'].split()[0]}."
            )
        else:
            doc_lines.append(f"  •  {fname}")

    body = (
        f"{company['name']} just closed — handoff package ready for review.\n\n"
        f"Three documents attached:\n\n"
        + "\n\n".join(doc_lines)
        + "\n\n"
        f"Reply with questions or flag anything that doesn't look right.\n\n"
        f"The AskElephant Team"
    )

    return subject, body


