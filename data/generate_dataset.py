import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
CSV_OUT = DATA_DIR / "opd_appointments_dataset.csv"

def generate_opd_dataset(n_samples: int = 2500, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic hospital OPD patient appointment dataset
    modeling real-world clinical no-show dynamics.
    """
    np.random.seed(random_seed)

    # 1. Demographics
    ages = np.random.randint(1, 85, size=n_samples)
    genders = np.random.choice(["Male", "Female"], size=n_samples, p=[0.48, 0.52])

    # 2. Scheduling & Temporal Factors
    # Exponential distribution for lead days (majority book 0-7 days in advance, some up to 30)
    raw_lead = np.random.exponential(scale=5.0, size=n_samples)
    lead_days = np.clip(np.round(raw_lead).astype(int), 0, 30)

    # Days of week (0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat)
    day_of_week = np.random.choice([0, 1, 2, 3, 4, 5], size=n_samples, p=[0.22, 0.20, 0.18, 0.18, 0.15, 0.07])
    appointment_hour = np.random.choice(range(9, 17), size=n_samples)  # 9 AM to 4 PM

    # 3. Medical & Behavioral History
    past_visits = np.random.poisson(lam=4.0, size=n_samples)
    past_no_shows = np.zeros(n_samples, dtype=int)
    for i in range(n_samples):
        if past_visits[i] > 0:
            past_no_shows[i] = np.random.binomial(n=past_visits[i], p=0.18)

    past_no_show_ratio = np.divide(past_no_shows, past_visits, out=np.zeros_like(past_no_shows, dtype=float), where=past_visits > 0)

    # SMS reminder (more likely sent if lead time > 2 days)
    sms_prob = np.where(lead_days > 2, 0.75, 0.25)
    sms_received = (np.random.random(n_samples) < sms_prob).astype(int)

    # Health conditions (correlated with age)
    hypertension_prob = np.clip((ages - 25) / 70, 0.05, 0.65)
    hypertension = (np.random.random(n_samples) < hypertension_prob).astype(int)

    diabetes_prob = np.clip((ages - 30) / 80, 0.02, 0.35)
    diabetes = (np.random.random(n_samples) < diabetes_prob).astype(int)

    # 4. Latent No-Show Probability Modeling (Ground Truth Log-Odds)
    log_odds = -1.8 \
        + 0.14 * lead_days \
        + 4.0 * past_no_show_ratio \
        - 1.4 * sms_received \
        - 0.02 * (ages - 40) \
        - 0.5 * hypertension \
        + 0.35 * (day_of_week >= 4)

    # Extra penalty for same-day walk-in: lead_days == 0 almost never misses
    log_odds[lead_days == 0] -= 3.0

    probabilities = 1.0 / (1.0 + np.exp(-log_odds))
    no_show = (np.random.random(n_samples) < probabilities).astype(int)

    df = pd.DataFrame({
        "patient_id": np.arange(1001, 1001 + n_samples),
        "age": ages,
        "gender": genders,
        "lead_days": lead_days,
        "day_of_week": day_of_week,
        "appointment_hour": appointment_hour,
        "past_visits": past_visits,
        "past_no_shows": past_no_shows,
        "past_no_show_ratio": np.round(past_no_show_ratio, 3),
        "sms_received": sms_received,
        "hypertension": hypertension,
        "diabetes": diabetes,
        "no_show": no_show
    })

    df.to_csv(CSV_OUT, index=False)
    print(f"Generated {n_samples} records. Saved to {CSV_OUT}")
    print(f"Overall No-Show Rate: {df['no_show'].mean():.1%}")
    return df

if __name__ == "__main__":
    generate_opd_dataset()
