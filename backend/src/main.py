"""
Closed-Won Activation Pipeline — Main Entry Point

Usage:
    python -m src.main                       # Run on default demo deal (summary mode)
    python -m src.main --verbose             # Show step-by-step output
    python -m src.main <deal.json>           # Run on a specific deal
    python -m src.main <deal.json> --verbose # Verbose on specific deal
    python -m src.main --serve               # Start FastAPI webhook server
"""
import json
import sys
import os


def _print_section(title):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def run_cli(deal_path: str = None, verbose: bool = False):
    """Run the pipeline from the CLI on a deal JSON file."""
    if deal_path is None:
        default = os.path.join(
            os.path.dirname(__file__),
            "../data/synthetic/DEAL-0001.json",
        )
        if os.path.exists(default):
            deal_path = default
        else:
            print("No deal file provided and no default found.")
            print("Usage: python -m src.main <deal.json>")
            sys.exit(1)

    with open(deal_path) as f:
        deal = json.load(f)

    print(f"\n=== Running pipeline on {deal['deal_id']} ({deal['company']['name']}) ===\n")

    if verbose:
        _run_verbose(deal)
    else:
        _run_summary(deal)


def _run_summary(deal):
    """Default run — calls orchestrator.run_pipeline and shows summary."""
    from .orchestrator import run_pipeline

    result = run_pipeline(deal)

    print(f"\n=== Pipeline complete ===")
    print(f"Deal: {result['deal_id']}")

    ml = result['ml_context']
    print(f"Risk: {ml['risk_multiplier']}x average churn rate ({ml['risk_tier'].replace('_', ' ')})")
    print(f"Interpretation: {ml['risk_interpretation']}")

    print(f"\nArtifacts delivered:")
    for name, delivery in result['delivery'].items():
        status = delivery.get('status', 'unknown')
        dest = delivery.get('destination', '?')
        print(f"  - {name:16s} | {status:8s} | {dest}")


def _run_verbose(deal):
    """Verbose run — shows output of each pipeline step."""
    from .nodes.feature_engineer import engineer_features
    from .nodes.xgb_scoring import predict_churn
    from .nodes.nn_retrieval import query_neighbors, compute_nn_churn_rate
    from .nodes.risk_calibration import calibrate_risk
    from .nodes.agents import qa_history, risk_narrative

    # --- Step 1: Feature Engineering ---
    _print_section("STEP 1 — Feature Engineering")
    features = engineer_features(deal)
    print(f"Generated {len(features) - 1} features")  # -1 for deal_id
    print(f"Sample features:")
    for key in ['amount', 'seats', 'discount_vs_list', 'has_exec_sponsor',
                'num_stakeholders', 'total_touches', 'response_rate', 'avg_sentiment_score']:
        if key in features:
            print(f"  {key:25s} = {features[key]}")

    # --- Step 2a: XGBoost Scoring ---
    _print_section("STEP 2a — XGBoost Churn Scoring")
    xgb = predict_churn(features)
    print(f"Raw churn probability: {xgb['churn_risk_prob']:.3f}")
    print(f"\nTop risk factors (SHAP values):")
    for name, val in xgb['top_risk_factors'][:7]:
        direction = '↑ risk' if val > 0 else '↓ risk'
        print(f"  {direction}  {name:35s} {val:+.4f}")

    # --- Step 2b: Risk Calibration ---
    _print_section("STEP 2b — Risk Calibration (SSM bucket lookup)")
    risk_cal = calibrate_risk(xgb['churn_risk_prob'])
    print(f"Raw prob:         {risk_cal['churn_risk_prob']:.3f}")
    print(f"Empirical rate:   {risk_cal['empirical_rate']:.3f}  (from bucket lookup)")
    print(f"Base rate:        {risk_cal['base_rate']:.3f}")
    print(f"Risk multiplier:  {risk_cal['risk_multiplier']}x")
    print(f"Risk tier:        {risk_cal['risk_tier']}")
    print(f"Interpretation:   {risk_cal['interpretation']}")

    # --- Step 2c: HNSW Retrieval ---
    _print_section("STEP 2c — HNSW Nearest Neighbor Retrieval")
    neighbors = query_neighbors(features, k=5, alpha=4.0)
    print(f"Retrieved {len(neighbors)} nearest neighbors:")
    for n in neighbors:
        print(f"  {n['deal_id']} | {n['company_name']:18s} | "
              f"{n['segment']:12s} | ${n['amount']:>8,.0f} | "
              f"{n['outcome']:10s} | dist: {n['distance']:.2f}")
    print(f"\nNN churn rate: {compute_nn_churn_rate(neighbors):.1%}")

    # --- Build ML context ---
    ml_context = {
        'churn_risk_prob': xgb['churn_risk_prob'],
        'risk_multiplier': risk_cal['risk_multiplier'],
        'risk_tier': risk_cal['risk_tier'],
        'risk_interpretation': risk_cal['interpretation'],
        'base_rate': risk_cal['base_rate'],
        'empirical_rate': risk_cal['empirical_rate'],
        'top_risk_factors': xgb['top_risk_factors'],
        'shap_values': xgb['shap_values'],
        'nearest_neighbors': neighbors,
        'nn_churn_rate': compute_nn_churn_rate(neighbors),
    }

    # --- Step 3a: Q&A History Agent ---
    _print_section("STEP 3a — Q&A History Agent (LLM)")
    qa = qa_history.run(deal)
    print(f"Total Q&A pairs:     {qa['total_qa_pairs']}")
    print(f"Unique Q&A pairs:    {qa['unique_qa_pairs']}")
    print(f"Prospect questions:  {len(qa['prospect_questions'])}")
    print(f"Rep questions:       {len(qa['rep_questions'])}")
    print(f"Open questions:      {len(qa['open_questions'])}")
    if qa.get('analysis'):
        print(f"\nAnalysis: {qa['analysis']}")
    if qa.get('key_insights'):
        print(f"\nKey insights:")
        for item in qa['key_insights']:
            print(f"  - {item}")

    # --- Step 3b: Objection History Agent ---
    from .nodes.agents import objection_history
    _print_section("STEP 3b — Objection History Agent (LLM)")
    obj = objection_history.run(deal)
    print(f"Total objections:    {obj['total_objections']}")
    print(f"Unique objections:   {obj['unique_objections']}")
    if obj.get('analysis'):
        print(f"\nAnalysis: {obj['analysis']}")
    if obj.get('risk_signals'):
        print(f"\nRisk signals:")
        for item in obj['risk_signals']:
            print(f"  - {item}")

    # --- Step 3c: Neighbor Analysis Agent ---
    from .nodes.agents import neighbor_analysis
    _print_section("STEP 3c — Neighbor Analysis Agent (LLM)")
    nn = neighbor_analysis.run(deal, ml_context)
    if nn.get('pattern_analysis'):
        print(f"Pattern: {nn['pattern_analysis']}")
    if nn.get('actionable_insights'):
        print(f"\nActionable insights:")
        for item in nn['actionable_insights']:
            print(f"  - {item}")

    # --- Step 3d: Risk Narrative Agent ---
    _print_section("STEP 3d — Risk Narrative Agent (LLM)")
    print("Calling LLM...")
    rn = risk_narrative.run(deal, ml_context)
    print(f"\nSummary: {rn.get('summary', '')}")
    print(f"\nRisk level: {rn.get('risk_level')}")
    if rn.get('watch_for'):
        print(f"\nWatch for:")
        for item in rn['watch_for']:
            print(f"  - {item}")
    if rn.get('recommended_actions'):
        print(f"\nRecommended actions:")
        for item in rn['recommended_actions']:
            print(f"  - {item}")

    # --- Step 4 & 5: Output agents + delivery via orchestrator ---
    _print_section("STEP 4 — Output Agents + Delivery (via orchestrator)")
    from .orchestrator import run_pipeline
    run_pipeline(deal)


def run_server():
    """Start the FastAPI webhook server."""
    import uvicorn
    uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False)


def main():
    args = sys.argv[1:]
    verbose = '--verbose' in args or '-v' in args
    args = [a for a in args if a not in ('--verbose', '-v')]

    if args and args[0] == '--serve':
        run_server()
    elif args:
        run_cli(args[0], verbose=verbose)
    else:
        run_cli(verbose=verbose)


if __name__ == "__main__":
    main()
