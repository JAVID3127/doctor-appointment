import pickle
from pathlib import Path
from typing import Dict, Any
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, roc_curve, classification_report
)

try:
    from .data_preprocessor import (
        build_preprocessor, load_and_split_data,
        ALL_FEATURES, NUMERIC_FEATURES, CATEGORICAL_FEATURES, BINARY_FEATURES
    )
except ImportError:
    from data_preprocessor import (
        build_preprocessor, load_and_split_data,
        ALL_FEATURES, NUMERIC_FEATURES, CATEGORICAL_FEATURES, BINARY_FEATURES
    )

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
SAVED_MODEL_PATH = MODEL_DIR / "no_show_pipeline.joblib"

def train_and_evaluate_models(csv_path: str) -> Dict[str, Any]:
    """
    Trains Logistic Regression and Random Forest models on OPD historical data.
    Evaluates both on unseen test set and serializes the champion model.
    """
    X_train, X_test, y_train, y_test = load_and_split_data(csv_path)

    # 1. Pipeline A: Logistic Regression (Interpretable baseline)
    log_reg_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", LogisticRegression(max_iter=1000, random_state=42))
    ])
    log_reg_pipeline.fit(X_train, y_train)

    y_pred_lr = log_reg_pipeline.predict(X_test)
    y_proba_lr = log_reg_pipeline.predict_proba(X_test)[:, 1]

    lr_metrics = {
        "model_name": "Logistic Regression",
        "accuracy": accuracy_score(y_test, y_pred_lr),
        "precision": precision_score(y_test, y_pred_lr),
        "recall": recall_score(y_test, y_pred_lr),
        "f1": f1_score(y_test, y_pred_lr),
        "roc_auc": roc_auc_score(y_test, y_proba_lr),
        "y_proba": y_proba_lr
    }

    # 2. Pipeline B: Random Forest Classifier (Non-linear ensembles)
    rf_pipeline = Pipeline([
        ("preprocessor", build_preprocessor()),
        ("classifier", RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42))
    ])
    rf_pipeline.fit(X_train, y_train)

    y_pred_rf = rf_pipeline.predict(X_test)
    y_proba_rf = rf_pipeline.predict_proba(X_test)[:, 1]

    rf_metrics = {
        "model_name": "Random Forest",
        "accuracy": accuracy_score(y_test, y_pred_rf),
        "precision": precision_score(y_test, y_pred_rf),
        "recall": recall_score(y_test, y_pred_rf),
        "f1": f1_score(y_test, y_pred_rf),
        "roc_auc": roc_auc_score(y_test, y_proba_rf),
        "y_proba": y_proba_rf
    }

    # Select best model based on ROC-AUC
    best_pipeline = rf_pipeline if rf_metrics["roc_auc"] >= lr_metrics["roc_auc"] else log_reg_pipeline
    best_name = "Random Forest" if best_pipeline == rf_pipeline else "Logistic Regression"

    # Save champion pipeline using standard pickle
    with open(SAVED_MODEL_PATH, "wb") as f:
        pickle.dump(best_pipeline, f)
    print(f"Saved champion pipeline ({best_name}) to {SAVED_MODEL_PATH}")

    return {
        "logistic_regression": lr_metrics,
        "random_forest": rf_metrics,
        "champion_model_name": best_name,
        "champion_pipeline": best_pipeline,
        "y_test": y_test,
        "saved_path": str(SAVED_MODEL_PATH)
    }

class NoShowModelTrainer:
    """
    Production-grade training orchestrator for online continuous retraining
    and serialization of the OPD no-show prediction pipeline.
    """
    def __init__(self, data_path: str = None):
        default_csv = Path(__file__).resolve().parent.parent.parent / "data" / "opd_appointments_dataset.csv"
        self.data_path = data_path or str(default_csv)

    def train_and_export(self, model_path: str = None) -> Dict[str, Any]:
        results = train_and_evaluate_models(self.data_path)
        return {
            "champion_model_name": results["champion_model_name"],
            "roc_auc": round(float(results["random_forest"]["roc_auc"]), 3),
            "accuracy": round(float(results["random_forest"]["accuracy"]), 3),
            "precision": round(float(results["random_forest"]["precision"]), 3),
            "recall": round(float(results["random_forest"]["recall"]), 3),
            "saved_path": results["saved_path"]
        }

if __name__ == "__main__":
    data_file = Path(__file__).resolve().parent.parent.parent / "data" / "opd_appointments_dataset.csv"
    train_and_evaluate_models(str(data_file))
