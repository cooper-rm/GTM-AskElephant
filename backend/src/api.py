"""
FastAPI Webhook Server

Endpoints:
    POST /activate           Run the pipeline (async with 10s fast-fail window)
    GET  /health             Health check
    GET  /runs/{id}/status   Check pipeline status (completed / processing / failed)
    GET  /runs/{id}          Retrieve full artifacts from a past run
    GET  /runs               List all past runs
"""
import json
import os
import logging
import traceback
import threading

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

# In-flight pipeline tracking: deal_id → {"status": "processing" | "completed" | "failed", ...}
_in_flight: dict = {}
_lock = threading.Lock()

FAST_FAIL_TIMEOUT = 10  # seconds to wait for quick errors before returning "processing"


@app.get("/health")
def health():
    return {"status": "ok", "service": "activation-pipeline"}


@app.post("/activate")
async def activate(deal: dict):
    """
    Run the closed-won activation pipeline on a deal record.

    Behavior:
      - Validates input immediately (400 on bad input)
      - Checks idempotency (returns cached result if already ran)
      - Starts pipeline in background thread
      - Waits up to 10s for fast errors (bad API key, agent crashes)
      - If done in 10s → returns result (success or failure)
      - If still running → returns {"status": "processing"}, pipeline continues
      - Poll GET /runs/{deal_id}/status for the final result
    """
    if 'deal_id' not in deal:
        raise HTTPException(status_code=400, detail="Missing deal_id")
    if 'company' not in deal or 'deal' not in deal:
        raise HTTPException(status_code=400, detail="Missing required fields: company, deal")

    deal_id = deal['deal_id']
    company_name = deal.get('company', {}).get('name', '?')

    # Idempotency: if this deal already completed, return cached result
    run_dir = os.path.join(RUNS_DIR, deal_id)
    completed_marker = os.path.join(run_dir, '_completed.json')
    if os.path.exists(completed_marker):
        with open(completed_marker) as f:
            cached = json.load(f)
        logger.info(f"[{deal_id}] Idempotent hit — returning cached result")
        return JSONResponse({**cached, "cached": True})

    # Check if already in-flight
    with _lock:
        if deal_id in _in_flight and _in_flight[deal_id]['status'] == 'processing':
            return JSONResponse({
                "deal_id": deal_id,
                "status": "processing",
                "message": "Pipeline already running for this deal",
            })

    # Start pipeline in background thread
    done_event = threading.Event()
    result_holder = {}

    def _run():
        try:
            logger.info(f"[{deal_id}] Pipeline starting for {company_name}")
            with _lock:
                _in_flight[deal_id] = {"status": "processing"}

            result = run_pipeline(deal)
            summary = _build_summary(result)

            # Save completion marker for idempotency
            os.makedirs(run_dir, exist_ok=True)
            with open(completed_marker, 'w') as f:
                json.dump(summary, f, indent=2)

            result_holder['data'] = summary
            with _lock:
                _in_flight[deal_id] = summary

            logger.info(f"[{deal_id}] Pipeline complete")

        except Exception as e:
            logger.error(f"[{deal_id}] Pipeline failed: {e}")
            logger.error(traceback.format_exc())
            error_result = {
                "deal_id": deal_id,
                "status": "failed",
                "error": str(e),
            }
            # Save failure marker so status endpoint can report it
            os.makedirs(run_dir, exist_ok=True)
            with open(os.path.join(run_dir, '_failed.json'), 'w') as f:
                json.dump(error_result, f, indent=2)

            result_holder['data'] = error_result
            with _lock:
                _in_flight[deal_id] = error_result

        finally:
            done_event.set()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    # Wait up to 10s for fast errors (auth failures, agent crashes)
    done_event.wait(timeout=FAST_FAIL_TIMEOUT)

    if done_event.is_set():
        # Pipeline finished (success or failure) within the timeout
        data = result_holder.get('data', {})
        if data.get('status') == 'failed':
            return JSONResponse(data, status_code=500)
        return JSONResponse(data)
    else:
        # Still running — return processing, pipeline continues in background
        return JSONResponse({
            "deal_id": deal_id,
            "status": "processing",
            "message": (
                f"Pipeline is running for {company_name}. "
                f"Check Slack channels for real-time artifact delivery, "
                f"or poll GET /runs/{deal_id}/status for the final result."
            ),
        }, status_code=202)


@app.get("/runs/{deal_id}/status")
def get_status(deal_id: str):
    """
    Check the status of a pipeline run.
    Returns: processing | completed | failed
    """
    # Check in-flight first (most recent state)
    with _lock:
        if deal_id in _in_flight:
            return JSONResponse(_in_flight[deal_id])

    # Check disk for completed/failed markers
    run_dir = os.path.join(RUNS_DIR, deal_id)
    completed_marker = os.path.join(run_dir, '_completed.json')
    failed_marker = os.path.join(run_dir, '_failed.json')

    if os.path.exists(completed_marker):
        with open(completed_marker) as f:
            return JSONResponse(json.load(f))

    if os.path.exists(failed_marker):
        with open(failed_marker) as f:
            return JSONResponse(json.load(f), status_code=500)

    raise HTTPException(status_code=404, detail=f"No run found for {deal_id}")


def _build_summary(result: dict) -> dict:
    """
    Extract a clean, JSON-safe summary from the full pipeline result.
    """
    delivery = {}
    for name, info in result.get('delivery', {}).items():
        if isinstance(info, dict):
            delivery[name] = {
                'status': info.get('status', 'unknown'),
                'destination': info.get('destination', '?'),
            }
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
