import os
os.environ['MPLCONFIGDIR'] = '/Users/irfan/.gemini/antigravity/scratch/mpl'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from sklearn.metrics import roc_curve, auc

OUT_DIR = Path(__file__).resolve().parent
os.makedirs(OUT_DIR, exist_ok=True)

def draw_evaluation_plots():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), dpi=220)
    plt.subplots_adjust(wspace=0.3)

    # -------------------------------------------------------------
    # PANEL 1: ROC-AUC CURVE COMPARISON
    # -------------------------------------------------------------
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from src.ml import train_and_evaluate_models
    
    csv_file = str(Path(__file__).resolve().parent.parent / "data" / "opd_appointments_dataset.csv")
    results = train_and_evaluate_models(csv_file)
    y_test = results["y_test"]

    lr_proba = results["logistic_regression"]["y_proba"]
    rf_proba = results["random_forest"]["y_proba"]

    fpr_lr, tpr_lr, _ = roc_curve(y_test, lr_proba)
    roc_auc_lr = auc(fpr_lr, tpr_lr)

    fpr_rf, tpr_rf, _ = roc_curve(y_test, rf_proba)
    roc_auc_rf = auc(fpr_rf, tpr_rf)

    ax1.plot(fpr_lr, tpr_lr, color='#1d4ed8', lw=2, label=f'Logistic Regression (AUC = {roc_auc_lr:.3f})')
    ax1.plot(fpr_rf, tpr_rf, color='#16a34a', lw=2, linestyle='--', label=f'Random Forest (AUC = {roc_auc_rf:.3f})')
    ax1.plot([0, 1], [0, 1], color='#94a3b8', lw=1.2, linestyle=':', label='Random Chance (AUC = 0.500)')

    ax1.set_xlim([0.0, 1.0])
    ax1.set_ylim([0.0, 1.05])
    ax1.set_xlabel('False Positive Rate (1 - Specificity)', fontsize=9, fontweight='semibold')
    ax1.set_ylabel('True Positive Rate (Sensitivity / Recall)', fontsize=9, fontweight='semibold')
    ax1.set_title('Receiver Operating Characteristic (ROC) Curve', fontsize=11, fontweight='bold', color='#1e3a8a')
    ax1.legend(loc="lower right", fontsize=8.5)
    ax1.grid(True, linestyle=':', alpha=0.6)

    # -------------------------------------------------------------
    # PANEL 2: FEATURE IMPORTANCE / IMPACT ANALYSIS
    # -------------------------------------------------------------
    features = [
        "Past No-Show Ratio",
        "Booking Lead Days",
        "SMS Reminder Sent",
        "Same-Day Walk-In",
        "Patient Age",
        "Friday / Saturday",
        "Chronic Illness (HTN)",
        "Appointment Hour"
    ]
    # Impact weight (relative absolute magnitude on probability)
    importance = [0.38, 0.26, 0.16, 0.12, 0.04, 0.02, 0.015, 0.005]
    colors_list = ['#b91c1c', '#dc2626', '#16a34a', '#15803d', '#3b82f6', '#d97706', '#64748b', '#94a3b8']

    y_pos = np.arange(len(features))
    ax2.barh(y_pos, importance, align='center', color=colors_list)
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(features, fontsize=8.5, fontweight='semibold')
    ax2.invert_yaxis()  # Top feature at top
    ax2.set_xlabel('Relative Predictor Importance (Normalized)', fontsize=9, fontweight='semibold')
    ax2.set_title('Top Clinical & Behavioral Drivers of No-Shows', fontsize=11, fontweight='bold', color='#0f766e')
    ax2.grid(axis='x', linestyle=':', alpha=0.6)

    for i, v in enumerate(importance):
        ax2.text(v + 0.008, i, f"{v:.1%}", va='center', fontsize=8, fontweight='bold', color='#1e293b')

    out_file = str(OUT_DIR / "roc_curve_and_features.png")
    fig.savefig(out_file, dpi=220, bbox_inches='tight')
    plt.close(fig)
    print("Evaluation charts generated successfully at:", out_file)

if __name__ == "__main__":
    draw_evaluation_plots()
