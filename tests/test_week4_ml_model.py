import pytest
from pathlib import Path
import pandas as pd

from src.ml import (
    load_and_split_data, train_and_evaluate_models,
    NoShowPredictor, SAVED_MODEL_PATH
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "opd_appointments_dataset.csv"

def test_data_loading_and_splitting():
    assert DATA_PATH.exists(), "Dataset CSV does not exist."
    X_train, X_test, y_train, y_test = load_and_split_data(str(DATA_PATH), test_size=0.2)

    assert len(X_train) == 2000
    assert len(X_test) == 500
    assert "lead_days" in X_train.columns
    assert "past_no_show_ratio" in X_train.columns
    assert "sms_received" in X_train.columns

def test_model_training_and_roc_auc_exceeds_threshold():
    results = train_and_evaluate_models(str(DATA_PATH))

    lr = results["logistic_regression"]
    rf = results["random_forest"]

    # Target threshold from project plan: ROC-AUC > 0.75
    assert lr["roc_auc"] > 0.75, f"Logistic Regression ROC-AUC ({lr['roc_auc']:.3f}) below 0.75 target."
    assert rf["roc_auc"] > 0.75, f"Random Forest ROC-AUC ({rf['roc_auc']:.3f}) below 0.75 target."

    # Both models should achieve accuracy > 75%
    assert lr["accuracy"] > 0.75
    assert rf["accuracy"] > 0.75

    # Check serialization
    assert Path(results["saved_path"]).exists()

def test_predictor_inference():
    predictor = NoShowPredictor(str(SAVED_MODEL_PATH))

    sample_features = {
        "age": 35,
        "gender": "Female",
        "lead_days": 3,
        "day_of_week": 1,
        "appointment_hour": 10,
        "past_visits": 5,
        "past_no_shows": 1,
        "past_no_show_ratio": 0.20,
        "sms_received": 1,
        "hypertension": 0,
        "diabetes": 0
    }

    prob = predictor.predict_probability(sample_features)
    assert 0.0 <= prob <= 1.0

def test_predictor_behavioral_sensitivity():
    predictor = NoShowPredictor(str(SAVED_MODEL_PATH))

    # High Risk Persona: Booked 14 days in advance, 60% past no-shows, no SMS
    high_risk_features = {
        "age": 28,
        "gender": "Male",
        "lead_days": 14,
        "day_of_week": 4,
        "appointment_hour": 11,
        "past_visits": 5,
        "past_no_shows": 3,
        "past_no_show_ratio": 0.60,
        "sms_received": 0,
        "hypertension": 0,
        "diabetes": 0
    }

    # Low Risk Persona: Same day booking (0 days), 0 past no-shows, SMS sent
    low_risk_features = {
        "age": 55,
        "gender": "Female",
        "lead_days": 0,
        "day_of_week": 2,
        "appointment_hour": 9,
        "past_visits": 10,
        "past_no_shows": 0,
        "past_no_show_ratio": 0.0,
        "sms_received": 1,
        "hypertension": 1,
        "diabetes": 0
    }

    high_eval = predictor.assess_smart_overbooking(high_risk_features)
    low_eval = predictor.assess_smart_overbooking(low_risk_features)

    # High risk probability must be significantly higher than low risk
    assert high_eval["predicted_no_show_prob"] > low_eval["predicted_no_show_prob"]
    assert high_eval["predicted_no_show_prob"] >= 0.50
    assert high_eval["eligible_for_overbook"] is True
    assert low_eval["eligible_for_overbook"] is False
    assert len(high_eval["key_drivers"]) > 0
