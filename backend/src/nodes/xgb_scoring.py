"""
XGBoost Churn Scoring Node

Trains and scores deals for churn risk using XGBoost classifier
with SHAP explainability.

Requires: shap>=0.46 (compatible with XGBoost 2.x)

Build phase: train_model() — run once on training data
Query phase: predict_churn() — run per webhook call
"""
import os
import pickle

import numpy as np
import xgboost as xgb
import shap

from .nn_retrieval import FEATURE_COLUMNS, features_to_vector


# --- Paths ---
MODELS_DIR = os.path.join(os.path.dirname(__file__), "../../data/models/xgb")
MODEL_PATH = os.path.join(MODELS_DIR, "model.pkl")
EXPLAINER_PATH = os.path.join(MODELS_DIR, "shap_explainer.pkl")


# --- Build phase ---

def train_model(
    features_list: list[dict],
    labels: list[int],
    params: dict = None,
) -> dict:
    """
    Train XGBoost churn classifier with SHAP explainer. Save to disk.

    Args:
        features_list: list of feature dicts (from feature_engineer)
        labels: list of 0/1 (0=retained/expanded, 1=churned)
        params: optional XGBoost params override

    Returns:
        dict with training metrics
    """
    X = np.array([features_to_vector(f) for f in features_list])
    y = np.array(labels)

    if params is None:
        params = {
            'objective': 'binary:logistic',
            'eval_metric': 'auc',
            'max_depth': 4,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'min_child_weight': 3,
            'scale_pos_weight': (y == 0).sum() / max((y == 1).sum(), 1),
            'random_state': 42,
        }

    model = xgb.XGBClassifier(**params)
    model.fit(X, y, verbose=False)

    # Build SHAP explainer (requires shap >= 0.46)
    explainer = shap.TreeExplainer(model)

    # Save
    os.makedirs(MODELS_DIR, exist_ok=True)
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    with open(EXPLAINER_PATH, 'wb') as f:
        pickle.dump(explainer, f)

    # Metrics
    y_pred = model.predict_proba(X)[:, 1]
    from sklearn.metrics import roc_auc_score, accuracy_score
    metrics = {
        'n_samples': len(y),
        'n_churned': int(y.sum()),
        'churn_rate': round(y.mean(), 3),
        'auc': round(roc_auc_score(y, y_pred), 3) if len(set(y)) > 1 else 0,
        'accuracy': round(accuracy_score(y, (y_pred > 0.5).astype(int)), 3),
    }

    print(f"XGBoost model trained: {metrics}")
    print(f"Saved to {MODELS_DIR}/")
    return metrics


# --- Query phase ---

_loaded_model = None
_loaded_explainer = None


def load_model():
    """Load XGBoost model and SHAP explainer into memory."""
    global _loaded_model, _loaded_explainer

    with open(MODEL_PATH, 'rb') as f:
        _loaded_model = pickle.load(f)
    with open(EXPLAINER_PATH, 'rb') as f:
        _loaded_explainer = pickle.load(f)

    print("XGBoost model + SHAP explainer loaded")


def predict_churn(features: dict) -> dict:
    """
    Score a deal for churn risk with SHAP explainability.

    Returns:
        churn_risk_prob: float 0-1
        top_risk_factors: list of (feature_name, shap_value) tuples sorted by |value|
        shap_values: dict of feature_name -> shap_value for this deal
    """
    if _loaded_model is None:
        load_model()

    vector = features_to_vector(features).reshape(1, -1)

    churn_prob = float(_loaded_model.predict_proba(vector)[0, 1])

    # Per-deal SHAP values
    shap_values = _loaded_explainer.shap_values(vector)[0]

    shap_dict = {col: round(float(val), 4) for col, val in zip(FEATURE_COLUMNS, shap_values)}
    sorted_factors = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)
    top_factors = sorted_factors[:7]

    return {
        'churn_risk_prob': round(churn_prob, 3),
        'top_risk_factors': top_factors,
        'shap_values': shap_dict,
    }
