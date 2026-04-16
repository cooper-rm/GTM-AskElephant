"""
FastAPI Webhook Server

Endpoints:
    POST /activate    Run the full pipeline on a deal record
    GET  /health      Health check
    GET  /runs/{id}   Retrieve artifacts from a past run
    GET  /runs        List all past runs
"""
import json
import os
import logging
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .orchestrator import run_pipeline


logger = logging.getLogger("activation")
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="AskElephant Closed-Won Activation",
    description="Autonomous handoff pipeline — webhook → ML → agents → delivery",
    version="0.1.0",
)

RUNS_DIR = os.path.join(os.path.dirname(__file__), "../data/runs")


@app.get("/health")
def health():
    return {"status": "ok", "service": "activation-pipeline"}


@app.post("/activate")
async def activate(deal: dict):
    """
    Run the closed-won activation pipeline on a deal record.

    Returns a clean summary of what was delivered — not the full pipeline
    output (which is saved to disk and retrievable via /runs/{deal_id}).
    """
    if 'deal_id' not in deal:
        raise HTTPException(status_code=400, detail="Missing deal_id")
    if 'company' not in deal or 'deal' not in deal:
        raise HTTPException(status_code=400, detail="Missing required fields: company, deal")

    deal_id = deal['deal_id']
    company_name = deal.get('company', {}).get('name', '?')

    # Idempotency: if this deal already ran, return the cached result
    run_dir = os.path.join(RUNS_DIR, deal_id)
    completed_marker = os.path.join(run_dir, '_completed.json')
    if os.path.exists(completed_marker):
        with open(completed_marker) as f:
            cached = json.load(f)
        logger.info(f"[{deal_id}] Idempotent hit — returning cached result")
        return JSONResponse({**cached, "cached": True})

    try:
        logger.info(f"[{deal_id}] Pipeline starting for {company_name}")
        result = run_pipeline(deal)
        logger.info(f"[{deal_id}] Pipeline complete")

        # Build a clean summary (no Block Kit blobs or LLM raw text)
        summary = _build_summary(result)

        # Save the completion marker for idempotency
        os.makedirs(run_dir, exist_ok=True)
        with open(completed_marker, 'w') as f:
            json.dump(summary, f, indent=2)

        return summary

    except Exception as e:
        logger.error(f"[{deal_id}] Pipeline failed: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Pipeline failed",
                "deal_id": deal_id,
                "message": str(e),
            },
        )


def _build_summary(result: dict) -> dict:
    """
    Extract a clean, JSON-safe summary from the full pipeline result.
    The full output (Block Kit, structured JSON, PDFs) lives on disk
    and is retrievable via /runs/{deal_id}.
    """
    delivery = {}
    for name, info in result.get('delivery', {}).items():
        if isinstance(info, dict):
            delivery[name] = {
                'status': info.get('status', 'unknown'),
                'destination': info.get('destination', '?'),
            }
            # Include PDF status for the handoff package
            if 'pdf_status' in info:
                delivery[name]['pdf_status'] = info['pdf_status']
        else:
            delivery[name] = {'status': str(info)[:100]}

    return {
        'deal_id': result.get('deal_id'),
        'status': 'completed',
        'started_at': result.get('started_at'),
        'completed_at': result.get('completed_at'),
        'risk': {
            'churn_prob': result.get('ml_context', {}).get('churn_risk_prob'),
            'risk_tier': result.get('ml_context', {}).get('risk_tier'),
            'risk_multiplier': result.get('ml_context', {}).get('risk_multiplier'),
        },
        'delivery': delivery,
        'artifacts_dir': f"data/runs/{result.get('deal_id')}/",
    }


@app.get("/runs/{deal_id}")
def get_run(deal_id: str):
    """Retrieve all artifacts from a past pipeline run."""
    run_dir = os.path.join(RUNS_DIR, deal_id)
    if not os.path.isdir(run_dir):
        raise HTTPException(status_code=404, detail=f"No run found for {deal_id}")

    artifacts = {}
    for fname in sorted(os.listdir(run_dir)):
        if fname.endswith('.json'):
            with open(os.path.join(run_dir, fname)) as f:
                name = fname.replace('.json', '')
                artifacts[name] = json.load(f)

    return JSONResponse(artifacts)


@app.get("/runs")
def list_runs():
    """List all past pipeline runs."""
    if not os.path.isdir(RUNS_DIR):
        return {"runs": []}
    runs = sorted([
        d for d in os.listdir(RUNS_DIR)
        if os.path.isdir(os.path.join(RUNS_DIR, d))
    ])
    return {"runs": runs}
