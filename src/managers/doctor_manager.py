from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from datetime import date, datetime
from ..models import Doctor, Appointment, TimeSlot, AppointmentStatus

class DoctorManager:
    """Manages doctor profiles, shifts, workload utilization, and emergency leaves."""

    def __init__(self, session: Session):
        self.session = session

    def register_doctor(
        self,
        name: str,
        specialization: str,
        room_number: str,
        dept_id: int,
        max_capacity: int = 30
    ) -> Doctor:
        doc = Doctor(
            name=name,
            specialization=specialization,
            room_number=room_number,
            dept_id=dept_id,
            max_daily_capacity=max_capacity,
            is_available=True
        )
        self.session.add(doc)
        self.session.commit()
        self.session.refresh(doc)
        return doc

    def get_doctor_by_id(self, doctor_id: int) -> Optional[Doctor]:
        return self.session.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()

    def get_all_doctors(self) -> List[Doctor]:
        return self.session.query(Doctor).order_by(Doctor.specialization, Doctor.name).all()

    def get_available_doctors_by_specialty(self, specialization: str) -> List[Doctor]:
        return self.session.query(Doctor).filter(
            Doctor.specialization.ilike(f"%{specialization}%"),
            Doctor.is_available == True
        ).all()

    def set_doctor_availability(self, doctor_id: int, is_available: bool) -> Optional[Doctor]:
        """Toggles doctor availability (e.g. marking on emergency leave)."""
        doc = self.get_doctor_by_id(doctor_id)
        if doc:
            doc.is_available = is_available
            self.session.commit()
            self.session.refresh(doc)
        return doc

    def get_doctor_workload(self, doctor_id: int, target_date: Optional[date] = None) -> Dict:
        """Returns doctor capacity, booked count, and remaining quota."""
        doc = self.get_doctor_by_id(doctor_id)
        if not doc:
            raise ValueError(f"Doctor ID #{doctor_id} not found.")

        query = self.session.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.notin_([AppointmentStatus.CANCELLED])
        )
        if target_date:
            query = query.join(TimeSlot).filter(
                TimeSlot.start_time >= datetime.combine(target_date, datetime.min.time()),
                TimeSlot.start_time <= datetime.combine(target_date, datetime.max.time())
            )

        booked_count = query.count()
        remaining_capacity = max(0, doc.max_daily_capacity - booked_count)
        utilization_rate = round((booked_count / doc.max_daily_capacity) * 100, 1) if doc.max_daily_capacity > 0 else 0.0

        return {
            "doctor_id": doc.doctor_id,
            "doctor_name": doc.name,
            "specialization": doc.specialization,
            "room_number": doc.room_number,
            "max_daily_capacity": doc.max_daily_capacity,
            "booked_appointments": booked_count,
            "remaining_capacity": remaining_capacity,
            "utilization_rate_pct": utilization_rate,
            "is_available": doc.is_available
        }
