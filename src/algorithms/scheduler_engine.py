from typing import List, Dict, Optional, Tuple
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from ..models import Doctor, Department, TimeSlot, Appointment, Patient, AppointmentStatus
from .interval_scheduling import (
    AppointmentRequest, earliest_finish_time_schedule,
    interval_partitioning_multidoctor, compact_shift_schedule
)

class IntervalSchedulingEngine:
    """
    High-level Scheduling Engine integrating Greedy Interval Scheduling
    with database doctors, departments, and consultation slots.
    """

    def __init__(self, session: Session):
        self.session = session

    def schedule_department_batch(
        self,
        dept_id: int,
        requests: List[AppointmentRequest],
        target_date: date
    ) -> Dict:
        """
        Schedules a batch of patient consultation requests across all available
        doctors in a specific department using Multi-Doctor Interval Partitioning.
        """
        dept = self.session.query(Department).filter(Department.dept_id == dept_id).first()
        if not dept:
            raise ValueError(f"Department #{dept_id} not found.")

        # Find available doctors in this department
        available_doctors = self.session.query(Doctor).filter(
            Doctor.dept_id == dept_id,
            Doctor.is_available == True
        ).all()

        if not available_doctors:
            raise ValueError(f"No available doctors found in department '{dept.dept_name}'.")

        doctor_ids = [d.doctor_id for d in available_doctors]
        doc_map = {d.doctor_id: d for d in available_doctors}

        # Run interval partitioning
        partitioned = interval_partitioning_multidoctor(requests, doctor_ids)

        persisted_slots = []
        persisted_appointments = []

        for doc_id, assigned_reqs in partitioned.items():
            for req in assigned_reqs:
                # Create and persist slot
                slot = TimeSlot(
                    doctor_id=doc_id,
                    start_time=req.start_time,
                    end_time=req.end_time,
                    is_booked=True,
                    is_overbooked=False
                )
                self.session.add(slot)
                self.session.flush()

                appt = Appointment(
                    patient_id=req.patient_id,
                    doctor_id=doc_id,
                    slot_id=slot.slot_id,
                    booking_timestamp=datetime.now(),
                    status=AppointmentStatus.BOOKED,
                    predicted_no_show_prob=0.0
                )
                self.session.add(appt)
                persisted_slots.append(slot)
                persisted_appointments.append(appt)

        self.session.commit()

        total_scheduled = sum(len(reqs) for reqs in partitioned.values())
        return {
            "department_name": dept.dept_name,
            "target_date": str(target_date),
            "doctors_utilized": len([d for d, r in partitioned.items() if len(r) > 0]),
            "total_requests": len(requests),
            "total_scheduled": total_scheduled,
            "rejection_rate_pct": round(((len(requests) - total_scheduled) / len(requests)) * 100, 1) if requests else 0.0,
            "allocations_per_doctor": {
                doc_map[d].name: len(r) for d, r in partitioned.items()
            }
        }

    def compute_doctor_utilization(
        self,
        doctor_id: int,
        target_date: date,
        start_hour: int = 9,
        end_hour: int = 13
    ) -> Dict:
        """
        Calculates active consultation time vs idle time during a shift.
        """
        doc = self.session.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doc:
            raise ValueError(f"Doctor #{doctor_id} not found.")

        shift_start = datetime(target_date.year, target_date.month, target_date.day, start_hour, 0)
        shift_end = datetime(target_date.year, target_date.month, target_date.day, end_hour, 0)
        total_shift_minutes = int((shift_end - shift_start).total_seconds() / 60)

        # Get booked slots during shift
        slots = self.session.query(TimeSlot).filter(
            TimeSlot.doctor_id == doctor_id,
            TimeSlot.start_time >= shift_start,
            TimeSlot.end_time <= shift_end,
            TimeSlot.is_booked == True
        ).order_by(TimeSlot.start_time).all()

        active_minutes = sum(s.duration_minutes for s in slots)
        idle_minutes = max(0, total_shift_minutes - active_minutes)
        utilization_pct = round((active_minutes / total_shift_minutes) * 100, 1) if total_shift_minutes > 0 else 0.0

        return {
            "doctor_id": doc.doctor_id,
            "doctor_name": doc.name,
            "specialization": doc.specialization,
            "shift_hours": f"{start_hour:02d}:00 - {end_hour:02d}:00",
            "total_shift_minutes": total_shift_minutes,
            "active_consultation_minutes": active_minutes,
            "idle_gap_minutes": idle_minutes,
            "utilization_rate_pct": utilization_pct,
            "appointments_count": len(slots)
        }
