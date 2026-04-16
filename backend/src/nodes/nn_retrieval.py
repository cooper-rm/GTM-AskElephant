"""
Nearest Neighbor Retrieval Node

Embeds deal features into dense vectors, indexes them with HNSW,
and retrieves k nearest historical deals with their outcomes.

Build phase: build_index() — run once on training data
Query phase: query_neighbors() — run per webhook call

HNSW parameters based on:
Cooper & Busch (2026), "Capacity-Limited Failure in Approximate
Nearest Neighbor Search on Image Embedding Spaces", J. Imaging 12(2), 55.
https://doi.org/10.3390/jimaging12020055

Key finding: ef_search = α × k (α ≥ 1) preserves neighborhood geometry.
At α = 4, accuracy ≈ exact KNN across all metrics.
"""
import json
import os
import pickle

import numpy as np
import hnswlib
from sklearn.preprocessing import StandardScaler


# --- Paths ---
MODELS_DIR = os.path.join(os.path.dirname(__file__), "../../data/models/hnsw")
INDEX_PATH = os.path.join(MODELS_DIR, "index.bin")
METADATA_PATH = os.path.join(MODELS_DIR, "metadata.json")
COLUMNS_PATH = os.path.join(MODELS_DIR, "columns.json")
SCALER_PATH = os.path.join(MODELS_DIR, "scaler.pkl")


# --- Feature columns (fixed order for vector construction) ---
# Excludes: deal_id, one-hot encoded categoricals that are already in the dict
FEATURE_COLUMNS = [
    # Deal features
    'amount', 'seats', 'price_per_seat', 'discount_vs_list',
    'is_inbound', 'product_tier_encoded', 'has_competitor',
    'competitor_gong', 'competitor_fathom', 'competitor_fireflies',
    'competitor_clari', 'competitor_chorus',
    # People features
    'num_stakeholders', 'has_exec_sponsor', 'has_technical_evaluator',
    'champion_tenure_months', 'unique_roles_count', 'is_single_threaded',
    # Touch features
    'total_touches', 'sdr_attempts', 'active_touches',
    'total_call_minutes', 'avg_call_duration', 'n_calls', 'n_emails',
    'calls_to_emails_ratio', 'sales_cycle_days',
    'avg_days_between_touches', 'longest_gap_days',
    'touch_frequency_trend', 'n_reschedules',
    # Response features
    'response_rate', 'avg_response_time_hours',
    'fastest_response_hours', 'sdr_attempts_before_connect',
    # Engagement features
    'avg_sentiment_score', 'sentiment_trend',
    'total_questions_asked', 'prospect_questions_count',
    'total_objections', 'unique_objection_themes',
    # Company features
    'employee_count', 'annual_revenue', 'revenue_per_employee',
    # Industry one-hot
    'industry_saas_tech', 'industry_marketing_agency', 'industry_fintech',
    'industry_proptech', 'industry_healthcare_it', 'industry_edtech',
    'industry_ecommerce', 'industry_managed_it_cybersecurity',
    'industry_professional_services', 'industry_vertical_saas',
]


def features_to_vector(features: dict) -> np.ndarray:
    """Convert a feature dict to a numpy vector in fixed column order."""
    return np.array([features.get(col, 0) for col in FEATURE_COLUMNS], dtype=np.float32)


# --- Build phase ---

def build_index(
    features_list: list[dict],
    metadata_list: list[dict],
    m: int = 32,
    ef_construction: int = 200,
) -> None:
    """
    Build HNSW index from training data and save to disk.

    Args:
        features_list: list of feature dicts (from feature_engineer)
        metadata_list: list of dicts with deal_id, outcome, etc.
        m: HNSW connectivity parameter
        ef_construction: construction-time exploration factor
    """
    # Convert to vectors
    vectors = np.array([features_to_vector(f) for f in features_list])
    n, dim = vectors.shape

    # Fit scaler and normalize
    scaler = StandardScaler()
    vectors_scaled = scaler.fit_transform(vectors)

    # Build index
    index = hnswlib.Index(space='l2', dim=dim)
    index.init_index(max_elements=n * 2, M=m, ef_construction=ef_construction)
    index.add_items(vectors_scaled, list(range(n)))

    # Save everything
    os.makedirs(MODELS_DIR, exist_ok=True)
    index.save_index(INDEX_PATH)

    with open(METADATA_PATH, 'w') as f:
        json.dump(metadata_list, f, indent=2)

    with open(COLUMNS_PATH, 'w') as f:
        json.dump(FEATURE_COLUMNS, f, indent=2)

    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)

    print(f"HNSW index built: {n} vectors, {dim} dimensions")
    print(f"Saved to {MODELS_DIR}/")


# --- Query phase ---

_loaded_index = None
_loaded_metadata = None
_loaded_scaler = None


def load_index():
    """Load HNSW index, metadata, and scaler into memory."""
    global _loaded_index, _loaded_metadata, _loaded_scaler

    with open(COLUMNS_PATH) as f:
        columns = json.load(f)
    assert columns == FEATURE_COLUMNS, "Column mismatch between saved index and current code"

    with open(SCALER_PATH, 'rb') as f:
        _loaded_scaler = pickle.load(f)

    with open(METADATA_PATH) as f:
        _loaded_metadata = json.load(f)

    dim = len(FEATURE_COLUMNS)
    _loaded_index = hnswlib.Index(space='l2', dim=dim)
    _loaded_index.load_index(INDEX_PATH, max_elements=len(_loaded_metadata) * 2)

    print(f"HNSW index loaded: {len(_loaded_metadata)} vectors, {dim} dimensions")


def query_neighbors(
    features: dict,
    k: int = 5,
    alpha: float = 4.0,
) -> list[dict]:
    """
    Query HNSW index for k nearest neighbors.

    Sets ef_search = alpha * k to preserve neighborhood geometry.
    Returns list of neighbor dicts with outcome data.
    """
    if _loaded_index is None:
        load_index()

    # Convert and scale
    vector = features_to_vector(features).reshape(1, -1)
    vector_scaled = _loaded_scaler.transform(vector)

    # Set search effort: ef_search = α × k
    ef_search = max(int(alpha * k), k + 1)
    _loaded_index.set_ef(ef_search)

    # Query
    indices, distances = _loaded_index.knn_query(vector_scaled, k=k)

    # Map to metadata
    neighbors = []
    for idx, dist in zip(indices[0], distances[0]):
        meta = _loaded_metadata[idx].copy()
        meta['distance'] = round(float(dist), 4)
        neighbors.append(meta)

    return neighbors


def compute_nn_churn_rate(neighbors: list[dict]) -> float:
    """Calculate churn rate among retrieved nearest neighbors."""
    if not neighbors:
        return 0.0
    churned = sum(1 for n in neighbors if n.get('outcome') == 'churned')
    return round(churned / len(neighbors), 3)
