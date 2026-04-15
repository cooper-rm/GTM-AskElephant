# GTM Engineer Homework — Game Plan

## Phase 1: Prep Work (no clock)

### 1. Define ICP
- Research AskElephant — positioning, competitors, customer problems
- Define who they sell to — segment, size, function, persona
- This informs everything: what the deal records look like, what risks matter, what the handoff should emphasize

### 2. Generate Synthetic Data
- Define deal record schema (20-30 features)
- Build realistic distributions and correlations
- 500-1000 records
- Include churn/success outcome labels based on known patterns

### 3. Architecture Map

```
CLOSED-WON ACTIVATION PIPELINE
==============================

┌─────────────────────────────────────────────────────────────────────┐
│                        DEAL RECORD (INPUT)                         │
│  amount, sales_cycle_days, discount_pct, num_stakeholders,         │
│  industry, champion_tenure, exec_sponsor, competitor_mentioned,    │
│  product_tier, use_case, notes, contacts, risks ...                │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FEATURE ENGINEERING                             │
│                                                                     │
│  Raw deal fields → model-ready features                             │
│  - Ratio features (discount_to_deal_size, cycle_per_stakeholder)   │
│  - Binary flags (has_exec_sponsor, is_single_threaded)             │
│  - Categorical encoding (industry, product_tier)                   │
│  - Text extraction from notes (risk keywords, sentiment)           │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        ML MODELS (trained in notebooks)            │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────────┐  ┌──────────────┐  │
│  │ Churn Risk       │  │ Deal Segmentation    │  │ Urgency      │  │
│  │ XGBoost          │  │ K-Means Clustering   │  │ (derived)    │  │
│  │                  │  │                      │  │              │  │
│  │ Output:          │  │ Output:              │  │ Output:      │  │
│  │ - risk_prob      │  │ - cluster_id         │  │ - level      │  │
│  │ - top_factors    │  │ - cluster_profile    │  │ - priority   │  │
│  │   (SHAP/builtin) │  │ - similar_deal_stats │  │   _actions   │  │
│  └────────┬─────────┘  └──────────┬───────────┘  └──────┬───────┘  │
│           │                       │                     │          │
│           │              ┌────────┘                     │          │
│           │              │  urgency = f(risk, cluster)──┘          │
└─────────┼───────────────────┼───────────────────────┼──────────────┘
          │                   │                       │
          └───────────────────┼───────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ML CONTEXT PACKAGE                               │
│                                                                     │
│  {                                                                  │
│    "churn_risk_prob": 0.82,                                         │
│    "top_risk_factors": ["no_exec_sponsor", "heavy_discount"],      │
│    "cluster_id": 3,                                                 │
│    "cluster_profile": "fast-close SMB, single-threaded",           │
│    "similar_deal_churn_rate": 0.35,                                 │
│    "urgency_level": "immediate",                                    │
│    "priority_actions": ["exec_alignment", "quick_win_needed"]      │
│  }                                                                  │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   AGENT ORCHESTRATOR                                │
│                                                                     │
│  Receives: deal record + ML context package                         │
│  Routes to each agent in parallel                                   │
│                                                                     │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐    │
│  │ Welcome   │ │ Slack     │ │ CSM Brief │ │ Kickoff Meeting   │    │
│  │ Email     │ │ Announce  │ │ Agent     │ │ Request Agent     │    │
│  │ Agent     │ │ Agent     │ │           │ │                   │    │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └────────┬──────────┘    │
│        │              │             │               │               │
│  ┌─────┴──────────────┴─────────────┴───────────────┘               │
│  │                                                                  │
│  │  ┌───────────┐ ┌─────────────────────┐                           │
│  │  │ CRM       │ │ 30-Day Success      │                           │
│  │  │ Update    │ │ Plan Agent          │                           │
│  │  │ Agent     │ │                     │                           │
│  │  └─────┬─────┘ └──────────┬──────────┘                           │
│  │        │                  │                                      │
└──┼────────┼──────────────────┼──────────────────────────────────────┘
   │        │                  │
   ▼        ▼                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HANDOFF PACKAGE (OUTPUT)                         │
│                                                                     │
│  ├── welcome_email.md          (customer-facing, in voice)         │
│  ├── slack_announcement.md     (internal team notification)        │
│  ├── csm_brief.md              (risk flags, context, what to watch)│
│  ├── kickoff_meeting.md        (agenda, invite draft, priorities)  │
│  ├── crm_updates.json          (stage/field changes to queue)      │
│  └── success_plan_30day.md     (milestones, risks, owner actions)  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                 TRANSPARENCY DASHBOARD                              │
│                                                                     │
│  - ML scores + feature importance visualizations                   │
│  - Agent reasoning: why each artifact says what it says            │
│  - Deal-to-output traceability                                     │
└─────────────────────────────────────────────────────────────────────┘
```

- Define every handoff point between layers
- This is the blueprint before writing code

### 4. Feature Engineering
- Transform raw deal fields into model-ready features
- Document which features map to which predictions
- Do this in notebooks — explore, iterate, visualize

### 5. Train Models (notebooks)
- EDA notebook: explore distributions, correlations, sanity check synthetic data
- Model 1: **Churn Risk Classifier** (XGBoost)
  - Binary/probability output
  - Feature importance extraction (SHAP or built-in)
  - This is the centerpiece — drives CSM brief risk flags, success plan priorities
- Model 2: **Deal Segmentation** (K-means clustering)
  - Groups similar deals into natural segments
  - Enables "deals like yours churn at X%" reasoning
  - Informs success plan based on what worked for similar deals
- Onboarding urgency: **not a separate model** — derived logic from risk score + cluster
  - High risk + no exec sponsor → front-load exec alignment
  - High complexity cluster + short sales cycle → flag potential misalignment
- Export trained models (joblib/pickle) for the pipeline to call

### 6. Define Agent System
- One agent per handoff artifact:
  - Welcome email agent
  - Internal Slack announcement agent
  - CSM brief agent (consumes ML risk outputs)
  - Kickoff meeting request agent
  - CRM update agent
  - 30-day success plan agent (see framework below)
- Each agent receives: deal record + ML outputs (scores, risk factors, cluster)
- Each agent produces: one ready-to-send artifact

#### 30-Day Success Plan Framework
The deal record carries MEDDIC-style fields from sales. The success plan agent
translates those into a TTFV (Time to First Value) driven onboarding plan.
No information loss at handoff — the same data that sold the deal drives onboarding.

**MEDDIC → 30-Day Plan Translation:**
```
MEDDIC field          →  30-day plan element
─────────────────────    ──────────────────────
Identified Pain       →  Success criteria (what "working" means for this customer)
Metrics               →  KPIs to track in first 30 days
Champion              →  Primary onboarding contact + engagement plan
Economic Buyer        →  Who to loop in for value review at day 30
Decision Criteria     →  What to prove first (buying criteria = success criteria)
Paper Process         →  Any compliance/security reqs that affect onboarding
```

**30-Day Structure:**
- **Week 1 (Days 1-7):** Technical setup, integrations live, champion trained
  - Gate: core integration active, champion can use the product
- **Week 2 (Days 8-14):** First workflows running, initial team rollout
  - Gate: first automated workflow producing output
- **Week 3 (Days 15-21):** Expand to full team, track adoption metrics
  - Gate: adoption target hit (X% of intended users active)
- **Week 4 (Days 22-30):** First value review, prep exec business review
  - Gate: measurable ROI against Identified Pain / Metrics from MEDDIC

**How ML informs the plan:**
- High churn risk → compress timeline, add more check-ins, front-load exec alignment
- Cluster profile "fast-close single-thread" → plan emphasizes multi-threading early
- Cluster profile "enterprise committee buy" → plan accounts for slower rollout, more stakeholders

### 7. Failure Handling & Human Failsafes

The system must fail cleanly, not silently or wrongly confident.
"When it breaks or hits ambiguity, it fails in a way that a human can pick up cleanly."

#### Layer 1: Input Validation (before anything runs)
- **Missing critical fields:** Deal record missing amount, champion, or use case?
  → HALT. Return: "Cannot generate handoff. Missing: [fields]. Human action required."
  → Don't guess. Don't fill in defaults. Stop and say why.
- **Malformed data:** Negative deal amounts, future close dates, impossible combos?
  → HALT with specific error. "Deal amount is negative — likely data entry error."

#### Layer 2: ML Confidence Gates (after models run)
- **Low confidence churn prediction:** Model outputs 0.45-0.55 (coin flip territory)?
  → Flag in ML context: "LOW CONFIDENCE — risk score is ambiguous"
  → CSM brief agent writes: "Model cannot confidently assess risk. Recommend manual review."
  → Don't present a weak prediction as if it's certain.
- **Cluster outlier:** Deal doesn't fit any cluster well (high distance to all centroids)?
  → Flag: "This deal doesn't match known patterns. No similar deal history available."
  → Success plan falls back to generic best practices + human review flag
- **Feature drift detected on this specific deal:** Input features outside training distribution?
  → Flag: "Warning — this deal has attributes outside model training range: [features]"

#### Layer 3: Agent Output Guardrails (after LLM generates)
- **Tone check on customer-facing content:** Welcome email sounds off?
  → Flag for human review before sending. "REVIEW RECOMMENDED: customer-facing content"
  → Never auto-send customer-facing artifacts without a confidence check
- **Conflicting signals:** ML says high risk but deal notes say "smooth process"?
  → Surface the contradiction explicitly in CSM brief: "Model flags high risk based on
    [factors], but deal notes indicate [contradicting signal]. Human judgment needed."
- **Missing context for personalization:** No champion name, no use case detail?
  → Agent writes generic version + flags: "Personalization limited — missing [fields]"

#### Layer 4: Human Escalation Triggers
These scenarios always route to a human, no matter what:

| Trigger | Why | Escalation |
|---------|-----|------------|
| Deal amount > 2x average | High-value = high-stakes handoff | "Flag: large deal — CSM lead should review all artifacts before send" |
| Multiple risk factors firing simultaneously | Compound risk is hard to automate well | "Flag: 3+ risk factors detected — recommend human-led kickoff planning" |
| Champion just changed roles/left (if detectable) | Single biggest churn predictor | "URGENT: Champion may no longer be in role. Pause automated outreach." |
| Model confidence < threshold on any prediction | System doesn't know what it doesn't know | "Low confidence — all artifacts marked DRAFT, human approval required" |

#### What this looks like in the output:
Every handoff package includes a **confidence manifest**:
```json
{
  "overall_confidence": "high",
  "human_review_required": false,
  "flags": [],
  "blocked_artifacts": [],
  "escalation_triggers": []
}
```

When something trips:
```json
{
  "overall_confidence": "low",
  "human_review_required": true,
  "flags": [
    "Churn risk model confidence: 0.51 (ambiguous)",
    "Deal does not match any known cluster profile"
  ],
  "blocked_artifacts": ["welcome_email", "slack_announcement"],
  "escalation_triggers": ["compound_risk", "low_model_confidence"]
}
```

#### Production Failure Philosophy
If this system is deployed and not working, the problem is almost never the
agents or the LLM — it's the data layer. Specifically:
- **Not enough data:** Models trained on too few deals can't generalize. The fix
  isn't better prompts, it's more training examples with real outcomes.
- **Wrong data being collected:** CRM fields are empty, inconsistent, or
  gamed by reps. The model learned garbage patterns. The fix is upstream —
  fix data collection at the source, not patch around it in the pipeline.
- **The implication:** When the system underperforms, the diagnostic is always
  "what changed in the data?" not "what's wrong with the AI?" This is a data
  quality problem dressed as an AI problem. The monitoring/drift layer exists
  specifically to surface this before it becomes a customer-facing failure.

#### Demo moment:
Fire a deliberately messy deal record from Postman — missing fields, edge case values.
Watch the system NOT hallucinate through it. Show the confidence manifest.
This is the "judgment" they're scoring for (25% of eval).

### 8. Transparency Dashboard
- Shows ML reasoning: risk scores, feature importance, why these decisions
- Shows agent outputs alongside the data that drove them
- Explainability layer, not the product

---

## Phase 2: Build Work (12-hour clock)

### Written Deliverables
- Part 1 — Outside-in brief (4 questions, 1 page)
- Part 2 — Motion pick writeup (half page)
- Part 4 — First 90 days (3 AI employees, 5 questions each)
- Part 5 — One question for founders

### System Deliverables
- Wire the pipeline end-to-end: deal record in → handoff package out
- Design doc — architecture, judgment calls, what breaks, v2 roadmap
- Record Loom — 5-7 min walkthrough

---

## ICP Notes (raw thinking for Part 1)

### Woody Interview Note
In interview, Woody mentioned seats — they want to get MORE seats per account.
This means: target companies with expansion potential. Not 5-person shops that
max out at 5 seats. Target companies where you land with one team (sales) and
expand to CS, RevOps, marketing, etc. The ideal customer has multiple revenue-facing
teams that could each become users. Land-and-expand is the growth model.

- Sweet spot: technical enough to believe in AI automation, not technical enough to build it
- The litmus test: would it take them 18+ months to implement the same system internally?
- Likely persona: VP of Sales / CRO at 200-800 person SaaS company
- They have RevOps to manage tools, but nobody to architect AI systems
- They've already tried duct-taping it (Zapier + Notion + manual processes) — it half-works
- Trigger: bleeding revenue on gaps in handoffs, stale CRM, reps doing admin instead of selling
- AskElephant's pitch: "we already built the thing you'd spend 18 months failing to build"

### Deal Context Enrichment Idea
For the agent system: when a deal comes in, enrich the deal context with publicly
available company information. For public companies (SEC filings, 10-K, earnings calls)
and funded privates (Crunchbase, PitchBook), pull revenue, employee count, funding
stage, growth signals. This context makes the handoff artifacts smarter — the CSM brief
can reference the customer's actual business size and trajectory, the success plan can
be calibrated to their scale, and the risk model gets better features (e.g., a $50K deal
at a company doing $22B in revenue is a very different risk profile than a $50K deal at
a 20-person startup). Worth building into the deal record schema as optional enrichment fields.

### Woody Quote — "Never Ask the Same Question Twice"
From podcast: Woody says you should never ask the same question to the customer twice.
Implication for our Closed-Won Activation agent: the handoff package should include a
**complete Q&A history** — every question asked during the sales cycle and the customer's
answers. This prevents the CS team from re-asking things the customer already answered
during sales, which is one of the fastest ways to erode trust post-close.

Add to the CSM brief agent output:
- List of questions previously asked (from call transcripts/notes)
- Customer's answers to each
- Open questions that were never resolved during sales
- This is a concrete, high-value artifact that most handoffs miss entirely

### Customer Base Thought (revisit later)
These ~24 testimonial customers are the ones who LOVE AskElephant enough to leave
a review. If they have ~300 customers total, that's ~8% testimonial rate. So who are
the other 92%? What types of companies are NOT showing up in testimonials?

Possible inferences:
- The enterprise logos (Stryker, Indeed, Applause) might be silent majority — big
  companies that use it but won't publicly endorse a seed-stage vendor
- Companies that churned or are lukewarm — what did they look like? What segment?
- If the testimonial base skews SMB/agency but the growth target is mid-market
  (Woody wants more seats), there might be a gap between who loves them today
  and who they need to win tomorrow

Worth revisiting: does the current product actually serve mid-market expansion
well, or is it still optimized for the 10-50 person teams that are most vocal?

---

## Feedback Loop — System Improvement Over Time

The system shouldn't be static. If we're predicting churn risk at handoff, we should
be learning from actual outcomes to get better.

### How it works:
```
  HANDOFF                    30/60/90 DAYS LATER
  ────────                   ────────────────────
  Deal closes → ML scores    Actual outcome lands
  risk + generates handoff   (churned? expanded? flat?)
        │                              │
        │                              │
        ▼                              ▼
  ┌──────────────────────────────────────────┐
  │           OUTCOME TRACKING TABLE         │
  │                                          │
  │  deal_id | predicted_risk | cluster |    │
  │  actual_outcome | days_to_churn |        │
  │  handoff_artifacts_used                  │
  └─────────────────────┬────────────────────┘
                        │
                        ▼
  ┌──────────────────────────────────────────┐
  │           MODEL RETRAINING               │
  │                                          │
  │  - Retrain churn classifier on real      │
  │    outcomes (not just synthetic data)     │
  │  - Re-cluster with actual deal outcomes  │
  │  - Track: did our risk flags predict     │
  │    the right things?                     │
  │  - Track: did the handoff artifacts we   │
  │    generated actually get used?          │
  └─────────────────────┬────────────────────┘
                        │
                        ▼
  ┌──────────────────────────────────────────┐
  │           AGENT IMPROVEMENT              │
  │                                          │
  │  - Which success plan actions correlated │
  │    with retention? Weight those higher.  │
  │  - Which CSM brief flags were ignored?   │
  │    Rewrite for clarity.                  │
  │  - Which cluster profiles need different │
  │    handoff approaches?                   │
  │  - Feed prompt tuning: "for deals like   │
  │    X, emphasize Y because Z worked"      │
  └──────────────────────────────────────────┘
```

### What this means for the demo:
- We won't have real outcome data — but we design the schema for it
- The design doc explains: "synthetic data trains v1, real outcomes train v2"
- Show the outcome tracking table structure even if it's empty
- This is a huge differentiator — most candidates will build a one-shot system

## Webhook Architecture — Live Demo Setup

```
┌──────────────┐         ┌──────────────────────────────────────────┐
│   POSTMAN    │         │              API SERVER                  │
│   or any     │  POST   │           (FastAPI / Flask)              │
│   HTTP       │────────▶│                                          │
│   client     │         │  /activate    → run full handoff pipeline│
│              │         │  /outcome     → log actual outcome data  │
│              │         │  /drift-check → return drift metrics     │
│              │         │  /retrain     → trigger model retrain    │
└──────────────┘         └──────────────────┬───────────────────────┘
                                            │
                                            ▼
                                   (existing pipeline)
                                   Deal → Features → ML → Agents → Output
```

### Demo Flow:
1. **Live handoff demo:** Hit /activate with one deal record from Postman
   → system runs full pipeline → handoff artifacts generated in real time

2. **Batch + drift demo:** Fire 50-100 deals through /activate with outcome
   data via /outcome → dashboard shows prediction vs. actual tracking
   → drift metrics update → system flags when retraining is needed

3. **Retraining signal:** Dashboard shows:
   - Model accuracy: 85% → 71% (degrading)
   - Feature drift: 3 features crossed PSI threshold
   - Recommendation: "retrain triggered" or "retraining recommended"
   - NOT actually retraining live — showing the system knows it's wrong

### Why this matters for the eval:
- "If we can't watch it run, it doesn't count" — they literally watch it run via Postman
- No scripted demo — they can modify the deal record and hit send themselves
- The drift demo shows the system is built for production, not just a one-shot

## Open Questions
- Stack: Python + FastAPI + sklearn/xgboost + Claude API + Streamlit?
- Agent framework: raw Python orchestration vs. something like LangGraph?
- Output format: files? structured JSON? simulated Slack/email templates?
- Hosting: local? deployed somewhere they can hit the webhook themselves?
