from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from ..models import Patient

class PatientManager:
    """Manages patient registrations, attendance logs, and no-show risk profiles."""

    def __init__(self, session: Session):
        self.session = session

    def register_patient(
        self,
        name: str,
        age: int,
        gender: str,
        phone: str,
        total_visits: int = 0,
        past_no_shows: int = 0
    ) -> Patient:
        existing = self.session.query(Patient).filter(Patient.phone == phone).first()
        if existing:
            return existing
        patient = Patient(
            name=name,
            age=age,
            gender=gender,
            phone=phone,
            total_visits=total_visits,
            past_no_shows=past_no_shows
        )
        self.session.add(patient)
        self.session.commit()
        self.session.refresh(patient)
        return patient

    def get_patient_by_id(self, patient_id: int) -> Optional[Patient]:
        return self.session.query(Patient).filter(Patient.patient_id == patient_id).first()

    def get_patient_by_phone(self, phone: str) -> Optional[Patient]:
        return self.session.query(Patient).filter(Patient.phone == phone).first()

    def get_all_patients(self) -> List[Patient]:
        return self.session.query(Patient).order_by(Patient.name).all()

    def record_attendance(self, patient_id: int, attended: bool) -> Patient:
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            raise ValueError(f"Patient ID #{patient_id} not found.")

        patient.total_visits += 1
        if not attended:
            patient.past_no_shows += 1

        self.session.commit()
        self.session.refresh(patient)
        return patient

    def get_risk_profile(self, patient_id: int) -> Dict:
        """Returns statistical no-show risk assessment based on past attendance."""
        patient = self.get_patient_by_id(patient_id)
        if not patient:
            raise ValueError(f"Patient ID #{patient_id} not found.")

        ratio = patient.no_show_ratio
        if patient.total_visits == 0:
            category = "UNKNOWN / NEW PATIENT"
            recommended_overbook = False
        elif ratio >= 0.40:
            category = "HIGH RISK"
            recommended_overbook = True
        elif ratio >= 0.20:
            category = "MEDIUM RISK"
            recommended_overbook = False
        else:
            category = "LOW RISK"
            recommended_overbook = False

        return {
            "patient_id": patient.patient_id,
            "name": patient.name,
            "total_visits": patient.total_visits,
            "past_no_shows": patient.past_no_shows,
            "no_show_ratio": ratio,
            "risk_category": category,
            "recommended_overbook": recommended_overbook
        }
