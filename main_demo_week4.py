import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.ml import (
    load_and_split_data, train_and_evaluate_models,
    NoShowPredictor, SAVED_MODEL_PATH
)

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def main():
    print_header("Doctor-Patient Appointment Scheduling System — Week 4 Demo")
    print("🏥 Week 4 Focus: AI No-Show Forecasting Model (Tabular ML & Overbooking Risk Scoring)\n")

    data_path = Path(__file__).resolve().parent / "data" / "opd_appointments_dataset.csv"
    if not data_path.exists():
        print("Generating dataset first...")
        from data.generate_dataset import generate_opd_dataset
        generate_opd_dataset()

    df = pd.read_csv(data_path)
    print(f"📊 1. Historical Dataset Overview:")
    print(f"   • Total Patient Appointments : {len(df):,}")
    print(f"   • Overall No-Show Rate       : {df['no_show'].mean():.1%}")
    print(f"   • Features Analyzed          : Age, Gender, Lead Days, Past No-Shows, SMS, Comorbidities\n")

    # Train and Evaluate Models
    print_header("2. Training & Comparative Evaluation: Logistic Regression vs Random Forest")
    results = train_and_evaluate_models(str(data_path))
    lr = results["logistic_regression"]
    rf = results["random_forest"]

    print(f"{'Metric':<25} | {'Logistic Regression':<22} | {'Random Forest (Champion)'}")
    print("-" * 75)
    print(f"{'Accuracy':<25} | {lr['accuracy']:<22.2%} | {rf['accuracy']:.2%}")
    print(f"{'Precision':<25} | {lr['precision']:<22.2%} | {rf['precision']:.2%}")
    print(f"{'Recall (Sensitivity)':<25} | {lr['recall']:<22.2%} | {rf['recall']:.2%}")
    print(f"{'F1-Score':<25} | {lr['f1']:<22.3f} | {rf['f1']:.3f}")
    print(f"{'ROC-AUC Score':<25} | {lr['roc_auc']:<22.3f} | {rf['roc_auc']:.3f}")

    print(f"\n🏆 Champion Model Selected: {results['champion_model_name']} (Saved to {results['saved_path']})")

    # Inference on Patient Personas
    print_header("3. Real-Time Inference: Patient Personas & Smart Overbooking Assessment")
    predictor = NoShowPredictor(str(SAVED_MODEL_PATH))

    personas = [
        {
            "name": "Persona 1: Low-Risk Walk-In Patient",
            "features": {
                "age": 62, "gender": "Female", "lead_days": 0, "day_of_week": 1,
                "appointment_hour": 9, "past_visits": 12, "past_no_shows": 0,
                "past_no_show_ratio": 0.0, "sms_received": 1, "hypertension": 1, "diabetes": 0
            }
        },
        {
            "name": "Persona 2: Moderate-Risk Patient",
            "features": {
                "age": 35, "gender": "Male", "lead_days": 4, "day_of_week": 2,
                "appointment_hour": 11, "past_visits": 4, "past_no_shows": 1,
                "past_no_show_ratio": 0.25, "sms_received": 1, "hypertension": 0, "diabetes": 0
            }
        },
        {
            "name": "Persona 3: High-Risk Advance Booking (Overbooking Candidate)",
            "features": {
                "age": 23, "gender": "Male", "lead_days": 14, "day_of_week": 5,
                "appointment_hour": 14, "past_visits": 5, "past_no_shows": 3,
                "past_no_show_ratio": 0.60, "sms_received": 0, "hypertension": 0, "diabetes": 0
            }
        }
    ]

    for p in personas:
        eval_res = predictor.assess_smart_overbooking(p["features"])
        print(f"\n👤 {p['name']}:")
        print(f"   • Predicted No-Show Prob  : {eval_res['predicted_no_show_prob']:.1%} (Attendance: {eval_res['attendance_probability']:.1%})")
        print(f"   • Risk Classification     : {eval_res['risk_level']}")
        print(f"   • Smart Overbook Eligible : {'YES (Secondary slot authorized)' if eval_res['eligible_for_overbook'] else 'NO (Strict single booking)'}")
        print(f"   • Recommendation          : {eval_res['action_recommendation']}")
        print(f"   • Key Decision Factors    : {', '.join(eval_res['key_drivers'])}")

    print("\n" + "=" * 80)
    print("  WEEK 4 VERIFICATION COMPLETE: AI NO-SHOW FORECASTING ENGINE OPERATIONAL!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
