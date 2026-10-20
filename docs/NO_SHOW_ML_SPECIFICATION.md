# Doctor-Patient Appointment Scheduling System
## Week 4: Machine Learning No-Show Forecasting Specification

---

### 1. Objective & Problem Overview
In public hospital OPDs, 20% to 30% of scheduled appointments result in patient "no-shows".
Rigid 1-patient-per-slot allocation leaves doctors idle whenever a patient misses their slot.
Week 4 develops an empirical machine learning model trained on historical patient behavior to compute a calibrated probability:
$$P(\text{no-show}) \in [0.0, 1.0]$$

This probability score feeds directly into Week 5's **Smart Overbooking Engine**, enabling safe secondary slot allocation for high-risk appointments without waiting room overcrowding.

---

### 2. Feature Engineering & Clinical Drivers

| Feature Name | Data Type | Description | Observed Impact on No-Show |
| :--- | :--- | :--- | :--- |
| **`past_no_show_ratio`** | Continuous ($[0.0, 1.0]$) | $\frac{\text{Past Missed Appointments}}{\text{Total Registered Visits}}$ | **Strongest Positive Driver (+38%):** Patients with prior unexcused absences are overwhelmingly likely to miss again. |
| **`lead_days`** | Integer ($\ge 0$) | Number of days between booking date and appointment date | **Strong Positive Driver (+26%):** Longer lead times increase forgetfulness and scheduling conflicts. Same-day bookings ($0$ days) show near-zero missed visits. |
| **`sms_received`** | Binary ($\{0, 1\}$) | Whether automated SMS alert reminder was sent | **Protective Factor (-16%):** SMS alerts cut no-shows by ~35%. |
| **`age`** | Integer | Patient age in years | Elderly patients and young children (accompanied by parents) show lower no-show rates than young adults. |
| **`hypertension` / `diabetes`** | Binary ($\{0, 1\}$) | Chronic medical conditions | Slight protective effect (regular medication prescription renewals). |
| **`day_of_week`** | Categorical ($0..5$) | Monday through Saturday | Fridays and Saturdays exhibit slightly elevated missed visit rates. |

---

### 3. Model Performance & Comparative Benchmark

Models evaluated on 20% held-out test set ($N = 500$ unseen appointments):

| Metric | Logistic Regression | Random Forest Classifier | Evaluation Target |
| :--- | :--- | :--- | :--- |
| **Accuracy** | 78.20% | 78.40% | $> 75.0\%$ |
| **Precision** | 65.57% | 70.00% | $> 60.0\%$ |
| **Recall (Sensitivity)** | 31.25% | 27.34% | Practical threshold |
| **F1-Score** | 0.423 | 0.393 | Balanced score |
| **ROC-AUC Score** | **0.752** | **0.750** | **$> 0.750$ (Met)** |

---

### 4. Smart Overbooking Risk Decision Logic

The model output $p = P(\text{no-show})$ is mapped to actionable clinical policies:

$$\text{Decision}(p) = 
\begin{cases}
\textbf{CONFIRMED (Strict 1-slot):} & p < 0.30 \quad (\text{Low risk of absence}) \\
\textbf{STANDARD MONITORING:} & 0.30 \le p < 0.55 \quad (\text{Send extra SMS reminder}) \\
\textbf{SAFE TO OVERBOOK:} & p \ge 0.55 \quad (\text{Authorize secondary booking})
\end{cases}$$

---

### 5. Visual Evidence
* View **[docs/roc_curve_and_features.png](roc_curve_and_features.png)** for the dual-panel ROC curves (comparing Logistic Regression vs Random Forest vs Chance) and feature importance bar chart.
