"""
Risk Calibration Node

Converts raw XGBoost churn probability into a calibrated risk multiplier
relative to the base churn rate, using the EMPIRICAL bucket lookup from
training data (Yeh & Lien 2009 sorting smoothing method).

Why bucketed lookup instead of raw probability:
    - XGBoost over-predicts in high-probability buckets (common in imbalanced data)
    - Raw 0.75 score might correspond to only ~31% actual churn rate
    - Bucket lookup maps raw score → empirical rate observed in training

Output is a risk MULTIPLIER (e.g., "2.3x average") — never a raw probability.
Agents consume the multiplier + tier, not the model's unreliable raw score.
"""
import json
import os


MODELS_DIR = os.path.join(os.path.dirname(__file__), "../../data/models/xgb")
CALIBRATION_PATH = os.path.join(MODELS_DIR, "calibration_buckets.json")


# --- Save during training ---

def save_calibration(buckets: list[dict], base_rate: float) -> None:
    """
    Persist bucket table and base rate during training.

    Args:
        buckets: list of dicts from SSM bucketed calibration with keys:
            {'bucket_low': 0.0, 'bucket_high': 0.1, 'avg_predicted': 0.04,
             'actual_rate': 0.038, 'n': 40}
        base_rate: overall churn rate in training data
    """
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(CALIBRATION_PATH, 'w') as f:
        json.dump({
            'base_rate': float(base_rate),
            'buckets': buckets,
        }, f, indent=2)


# --- Load + lookup at inference ---

_loaded_calibration = None


def load_calibration() -> dict:
    """Load calibration table into memory."""
    global _loaded_calibration
    if not os.path.exists(CALIBRATION_PATH):
        # Fallback — no calibration available, use raw score
        _loaded_calibration = {'base_rate': 0.145, 'buckets': []}
        return _loaded_calibration
    with open(CALIBRATION_PATH) as f:
        _loaded_calibration = json.load(f)
    return _loaded_calibration


def lookup_empirical_rate(churn_risk_prob: float, calibration: dict) -> float:
    """
    Look up the empirical actual churn rate for a given raw score.

    Rules:
      1. If the score's bucket is populated (n > 0) → use its actual_rate
      2. If the score's bucket is empty (n == 0) → walk BACKWARDS to previous
         populated bucket and use that rate
      3. If no populated buckets exist at all → fall back to raw score
    """
    buckets = calibration.get('buckets', [])
    if not buckets:
        return churn_risk_prob

    # Sort by bucket_low to guarantee order
    buckets = sorted(buckets, key=lambda b: b.get('bucket_low', 0))

    # Find which bucket the score falls into
    target_idx = None
    for i, bucket in enumerate(buckets):
        lo = bucket.get('bucket_low', 0)
        hi = bucket.get('bucket_high', 1)
        if lo <= churn_risk_prob <= hi:
            target_idx = i
            break

    # Score above all buckets (shouldn't happen but defensive)
    if target_idx is None:
        target_idx = len(buckets) - 1

    # Walk backwards from the target bucket until we find a populated one
    for i in range(target_idx, -1, -1):
        if buckets[i].get('n', 0) > 0:
            return buckets[i].get('actual_rate', churn_risk_prob)

    # No populated bucket at or below the target — look upward as last resort
    for i in range(target_idx + 1, len(buckets)):
        if buckets[i].get('n', 0) > 0:
            return buckets[i].get('actual_rate', churn_risk_prob)

    # No populated buckets anywhere — fall back to raw score
    return churn_risk_prob


# --- Main calibration function ---

def calibrate_risk(churn_risk_prob: float, base_rate: float = None) -> dict:
    """
    Convert raw churn probability into calibrated risk multiplier + tier.

    Uses empirical bucket lookup from training data (SSM calibration).
    Returns a multiplier, NOT a raw probability — this is what agents consume.

    Returns:
        {
            'churn_risk_prob': 0.75,              # raw model output (for audit only)
            'empirical_rate': 0.31,               # bucket-lookup actual rate
            'base_rate': 0.145,                   # observed base rate in training
            'risk_multiplier': 2.14,              # 2.14x more likely than average
            'risk_tier': 'elevated',              # categorical bucket
            'interpretation': '2.1x average ...', # human-readable
        }
    """
    if _loaded_calibration is None:
        load_calibration()

    calibration = _loaded_calibration or {'base_rate': 0.145, 'buckets': []}
    if base_rate is None:
        base_rate = calibration.get('base_rate', 0.145)

    # Avoid division by zero
    if base_rate <= 0:
        base_rate = 0.0001

    # Look up empirical rate from bucket table
    empirical_rate = lookup_empirical_rate(churn_risk_prob, calibration)

    # Multiplier relative to base rate
    multiplier = empirical_rate / base_rate

    # Tier thresholds
    if multiplier < 0.5:
        tier = 'very_low'
    elif multiplier < 0.9:
        tier = 'low'
    elif multiplier < 1.25:
        tier = 'average'
    elif multiplier < 2.0:
        tier = 'elevated'
    elif multiplier < 3.5:
        tier = 'high'
    else:
        tier = 'very_high'

    # Human-readable interpretation
    if multiplier >= 1.0:
        interpretation = (
            f"{multiplier:.1f}x average churn risk "
            f"({empirical_rate:.0%} expected vs {base_rate:.0%} base rate)"
        )
    else:
        interpretation = (
            f"{multiplier:.1f}x average churn risk — safer than baseline "
            f"({empirical_rate:.0%} expected vs {base_rate:.0%} base rate)"
        )

    return {
        'churn_risk_prob': round(churn_risk_prob, 3),
        'empirical_rate': round(empirical_rate, 3),
        'base_rate': round(base_rate, 3),
        'risk_multiplier': round(multiplier, 2),
        'risk_tier': tier,
        'interpretation': interpretation,
    }
