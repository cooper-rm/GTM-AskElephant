# Motion C — Closed-Won Activation Agent

**AskElephant GTM Engineer Pre-Work**

> Given a deal that just hit closed-won, own the handoff end-to-end: customer welcome, internal announcement, CSM brief with full deal context and risks, kickoff meeting request, CRM updates queued, first 30-day success plan for the account. One pass. No human stitching the pieces together.

---

## What this builds

An autonomous pipeline that takes a closed-won deal via webhook and produces a complete CSM handoff package:

| Artifact | Destination | What it does |
|----------|-------------|--------------|
| Welcome email | Gmail → customer | Personalized welcome with invoice PDF attached |
| Slack announcement | `#closed-won-announcements` | Celebratory internal deal-win post (Block Kit) |
| CSM handoff brief | `#customer-success-briefings` | Full deal context, stakeholders, objections, risk assessment, Q&A history |
| Kickoff meeting draft | `#kickoff-drafts` | Ready-to-edit email proposing a kickoff call |
| CRM updates | HubSpot (log-only) | Structured field updates for the deal record |
| 30-day success plan | `#30d-customer-success-plans` | Week-by-week plan with activities, stakeholders, expected outputs |
| PDF handoff package | Gmail → CSM | 3 branded PDFs (brief + plan + kickoff) bundled in one email |

---

## How it works

```
Webhook POST → Feature Engineering → XGBoost + SHAP → HNSW Retrieval → Risk Calibration
                                                                              ↓
                                                          ┌── Wave 1 (parallel) ──────────────────┐
                                                          │ welcome_email   │ slack_announce       │
                                                          │ csm_brief       │ kickoff_draft        │
                                                          │ crm_updates     │                      │
                                                          └─────────────────┴──────────────────────┘
                                                                              ↓
                                                          ┌── Wave 2 (sequential) ────────────────┐
                                                          │ success_plan (consumes csm_brief)      │
                                                          └───────────────────────────────────────┘
                                                                              ↓
                                                          PDF generation → Email handoff package
```

**ML stack:** XGBoost churn classifier with SHAP explanations, HNSW approximate nearest-neighbor retrieval for similar-deal context, Sorting Smoothing Method (Yeh & Lien 2009) for probability calibration into interpretable risk multipliers.

**Agent architecture:** 6 output agents (5 parallel + 1 sequential). The success plan agent consumes the CSM brief's structured output so it can reference specific stakeholders, known objections, and customer-specific tips rather than generating generic plans.

---

## Setup

### 1. Clone + install

```bash
cd backend
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
```

> **Python 3.10 required** — the ML models (XGBoost, SHAP, HNSW scaler) are serialized with 3.10. Other versions will fail on load.

### 2. Environment variables

Copy `backend/.env.example` to `backend/.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...         # #closed-won-announcements
SLACK_BRIEF_WEBHOOK_URL=https://hooks.slack.com/services/...   # #customer-success-briefings
SLACK_PLAN_WEBHOOK_URL=https://hooks.slack.com/services/...    # #30d-customer-success-plans
SLACK_KICKOFF_WEBHOOK_URL=https://hooks.slack.com/services/... # #kickoff-drafts

GMAIL_USER=askelephantdemo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

TEST_MODE=true   # routes customer emails to GMAIL_USER instead of real addresses
```

### 3. Verify

```bash
python -m src.main   # runs DEAL-0001 end-to-end
```

---

## Usage

### CLI (single deal)

```bash
# Default deal (DEAL-0001)
python -m src.main

# Specific deal
python -m src.main data/synthetic/DEAL-0042.json

# Verbose mode (shows each pipeline step)
python -m src.main --verbose
```

### Webhook server

```bash
python -m src.main --serve
# or directly:
uvicorn src.api:app --host 0.0.0.0 --port 8000
```

### API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/activate` | Run pipeline on a deal (JSON body) |
| `GET` | `/runs` | List all past runs |
| `GET` | `/runs/{deal_id}` | Retrieve artifacts from a past run |

### Example: POST a deal

```bash
curl -X POST http://localhost:8000/activate \
  -H 'Content-Type: application/json' \
  -d @data/demo_deals/DEAL-0991.json
```

Response:
```json
{
  "deal_id": "DEAL-0991",
  "status": "completed",
  "risk": {
    "churn_prob": 0.036,
    "risk_tier": "very_low",
    "risk_multiplier": 0.36
  },
  "delivery": {
    "welcome_email":    {"status": "sent", "destination": "email → ..."},
    "slack_announce":   {"status": "sent", "destination": "slack → #closed-won-announcements"},
    "csm_brief":        {"status": "sent", "destination": "slack → #customer-success-briefings"},
    "kickoff_draft":    {"status": "sent", "destination": "slack → #kickoff-drafts"},
    "crm_updates":      {"status": "logged", "destination": "hubspot → deal record"},
    "success_plan":     {"status": "sent", "destination": "slack → #30d-customer-success-plans"},
    "handoff_package":  {"status": "sent", "destination": "email → ... (handoff package)"}
  }
}
```

**Idempotent:** hitting `/activate` again with the same `deal_id` returns the cached result without re-delivering.

---

## Demo deals

10 pre-generated deals in `backend/data/demo_deals/` for Postman / demo use:

| Deal | Company | Segment | ACV | Use case |
|------|---------|---------|-----|----------|
| DEAL-0991 | PrismMetrics | SMB | $3.0K | Rep productivity |
| DEAL-0992 | PulseIO | SMB | $2.8K | Onboarding automation |
| DEAL-0993 | SageRelay | Mid-market | $13.1K | Forecasting accuracy |
| DEAL-0994 | OakIO | SMB | $5.6K | CRM automation |
| DEAL-0995 | SwiftRelay | SMB | $6.5K | Rep productivity |
| DEAL-0996 | NextAnalytics | Mid-market | $16.2K | Pipeline visibility |
| DEAL-0997 | VortexDynamics | Mid-market | $16.1K | CRM automation |
| DEAL-0998 | ObsidianPartners | Mid-market | $15.3K | CRM automation |
| DEAL-0999 | PineApps | Mid-market | $10.3K | Call recording + coaching |
| DEAL-1000 | CobaltMedia | Mid-market | $16.4K | Pipeline visibility |

---

## Key technical decisions

- **XGBoost 1.7.6** pinned for SHAP TreeExplainer compatibility (2.x JSON format breaks SHAP 0.42-0.49)
- **HNSW** with ef_search = α×k for controlled recall-latency tradeoff
- **SSM calibration** converts raw XGB probabilities into interpretable multipliers ("2.3× average churn risk") via bucketed empirical rate lookup
- **Two-wave orchestration** — brief runs first so the 30-day plan can consume its structured output (stakeholders, risks, tips) instead of regenerating context from scratch
- **Retry + idempotency** — 3× exponential backoff on transient Slack/Gmail failures; webhook short-circuits on duplicate deal_id

---

## Reliability

- **Idempotency** — `/activate` checks for `_completed.json` before re-running
- **Retry** — Gmail SMTP and Slack webhooks retry 3× with exponential backoff (1s, 3s, 9s)
- **Graceful failure** — individual agent failures don't crash the pipeline; partial results are delivered

---

## Project structure

```
├── backend/
│   ├── src/
│   │   ├── api.py              # FastAPI webhook server
│   │   ├── main.py             # CLI entry point
│   │   ├── orchestrator.py     # Pipeline wiring (7 steps, 2-wave execution)
│   │   ├── nodes/
│   │   │   ├── feature_engineer.py
│   │   │   ├── xgb_scoring.py
│   │   │   ├── nn_retrieval.py
│   │   │   ├── risk_calibration.py
│   │   │   └── agents/         # 6 output agents + delivery layer
│   │   └── utils/
│   │       ├── llm.py          # Claude API wrapper
│   │       ├── pdf_theme.py    # Shared PDF brand theme
│   │       ├── pdf_brief.py    # CSM brief PDF generator
│   │       ├── pdf_plan.py     # Success plan PDF generator
│   │       ├── pdf_kickoff.py  # Kickoff draft PDF generator
│   │       └── invoice_pdf.py  # Invoice PDF generator
│   ├── data/
│   │   ├── synthetic/          # 1,000 training deals
│   │   ├── demo_deals/         # 10 deals for Postman / demo
│   │   ├── models/             # Trained XGB + SHAP + HNSW + calibration
│   │   └── runs/               # Pipeline output per deal (gitignored)
│   └── .env.example            # Secrets template
├── notebooks/                  # ML training notebooks (4)
├── deliverables/               # Homework brief PDF + generator
├── Procfile                    # Heroku deploy
├── requirements.txt            # Python deps (pinned)
└── runtime.txt                 # Python 3.10.19
```

---

## Deploy (Heroku)

Auto-deploys from GitHub. Set env vars via `heroku config:set`:

```bash
heroku config:set ANTHROPIC_API_KEY=sk-ant-...
heroku config:set SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
heroku config:set SLACK_BRIEF_WEBHOOK_URL=https://hooks.slack.com/services/...
heroku config:set SLACK_PLAN_WEBHOOK_URL=https://hooks.slack.com/services/...
heroku config:set SLACK_KICKOFF_WEBHOOK_URL=https://hooks.slack.com/services/...
heroku config:set GMAIL_USER=askelephantdemo@gmail.com
heroku config:set GMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
heroku config:set TEST_MODE=true
```

POST a deal to `https://your-app.herokuapp.com/activate` via Postman to see it run.
