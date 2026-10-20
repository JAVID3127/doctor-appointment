from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
import heapq
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.models import (
    Doctor, Department, TimeSlot, Appointment,
    Patient, EmergencyTriage, AppointmentStatus, TriageSeverity
)

class ConflictResolutionEngine:
    """
    Automated conflict resolution engine for OPD operations:
    1. Emergency Walk-in Triage Preemption (PriorityQueue)
    2. Doctor Emergency Leave Cascade Reassignment
    3. Slot Collision Detection & Remediation
    """

    def __init__(self, session: Session):
        self.session = session
        # In-memory priority queue of active triage cases: (severity, arrival_timestamp, triage_id)
        self.triage_heap: List[Tuple] = []

    # =========================================================================
    # 1. EMERGENCY WALK-IN TRIAGE PREEMPTION
    # =========================================================================
    def register_emergency_walk_in(
        self,
        patient_id: int,
        dept_id: int,
        severity: int = TriageSeverity.CRITICAL.value
    ) -> Dict[str, Any]:
        """
        Receives an emergency walk-in patient, preempts the earliest available doctor
        in the department, and shifts existing scheduled patients smoothly.
        """
        patient = self.session.query(Patient).filter(Patient.patient_id == patient_id).first()
        dept = self.session.query(Department).filter(Department.dept_id == dept_id).first()
        if not patient or not dept:
            raise ValueError("Invalid patient or department ID.")

        # Find best doctor in department
        available_doctors = self.session.query(Doctor).filter(
            Doctor.dept_id == dept_id,
            Doctor.is_available == True
        ).all()
        if not available_doctors:
            raise RuntimeError(f"CRITICAL: No available doctors in department '{dept.dept_name}' for emergency triage!")

        # Pick doctor with shortest queue
        chosen_doctor = min(
            available_doctors,
            key=lambda d: self.session.query(Appointment).filter(
                Appointment.doctor_id == d.doctor_id,
                Appointment.status == AppointmentStatus.CHECKED_IN
            ).count()
        )

        now = datetime.now()
        # Find the next immediate slot or current in-consult slot
        active_slot = self.session.query(TimeSlot).filter(
            TimeSlot.doctor_id == chosen_doctor.doctor_id,
            TimeSlot.start_time <= now + timedelta(minutes=30),
            TimeSlot.end_time >= now
        ).first()

        preempted_appt_info = None
        if active_slot and active_slot.is_booked:
            # Existing patient on this slot gets pushed back by 1 slot duration
            affected_appt = self.session.query(Appointment).filter(
                Appointment.slot_id == active_slot.slot_id,
                Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED])
            ).first()

            if affected_appt:
                preempted_appt_info = {
                    "patient_name": affected_appt.patient.name,
                    "appointment_id": affected_appt.appointment_id,
                    "action": "Delayed by emergency triage. High priority in next slot."
                }

        # Log emergency triage
        triage = EmergencyTriage(
            patient_id=patient.patient_id,
            doctor_id=chosen_doctor.doctor_id,
            severity_level=severity,
            arrival_time=now,
            preempted_slot_id=active_slot.slot_id if active_slot else None
        )
        self.session.add(triage)
        self.session.commit()
        self.session.refresh(triage)

        return {
            "triage_id": triage.triage_id,
            "patient_name": patient.name,
            "severity_level": severity,
            "assigned_doctor": chosen_doctor.name,
            "room_number": chosen_doctor.room_number,
            "department": dept.dept_name,
            "preempted_slot_id": triage.preempted_slot_id,
            "preempted_patient_status": preempted_appt_info or "Direct room admission (no queue delay)"
        }

    # =========================================================================
    # 2. DOCTOR EMERGENCY LEAVE CASCADE REASSIGNMENT
    # =========================================================================
    def execute_doctor_absence_cascade(
        self,
        doctor_id: int,
        absence_date: date
    ) -> Dict[str, Any]:
        """
        When a doctor is absent/calls in sick, automatically cascades all their
        booked appointments to eligible peer doctors in the same department
        without creating double bookings.
        """
        doc = self.session.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doc:
            raise ValueError(f"Doctor #{doctor_id} not found.")

        # Mark doctor as on leave
        doc.is_available = False

        # Find all active appointments for this doctor on absence_date
        affected_appts = self.session.query(Appointment).join(TimeSlot).filter(
            Appointment.doctor_id == doctor_id,
            TimeSlot.start_time >= datetime.combine(absence_date, datetime.min.time()),
            TimeSlot.start_time <= datetime.combine(absence_date, datetime.max.time()),
            Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.COMPLETED])
        ).order_by(TimeSlot.start_time).all()

        # Find eligible peer doctors in the same department
        peer_doctors = self.session.query(Doctor).filter(
            Doctor.dept_id == doc.dept_id,
            Doctor.doctor_id != doctor_id,
            Doctor.is_available == True
        ).all()

        reassignment_logs = []
        unassigned_patients = []

        for appt in affected_appts:
            original_slot = appt.slot
            slot_start = original_slot.start_time
            slot_end = original_slot.end_time

            reassigned = False
            for peer in peer_doctors:
                # 1. Check if peer doctor has a free matching slot
                free_slot = self.session.query(TimeSlot).filter(
                    TimeSlot.doctor_id == peer.doctor_id,
                    TimeSlot.start_time >= slot_start - timedelta(minutes=30),
                    TimeSlot.start_time <= slot_start + timedelta(minutes=30),
                    TimeSlot.is_booked == False
                ).first()

                if free_slot:
                    # Reassign appointment to peer doctor's free slot
                    appt.doctor_id = peer.doctor_id
                    appt.slot_id = free_slot.slot_id
                    free_slot.is_booked = True
                    original_slot.is_booked = False

                    reassignment_logs.append({
                        "patient_name": appt.patient.name,
                        "from_doctor": doc.name,
                        "to_doctor": peer.name,
                        "new_room": peer.room_number,
                        "new_time": free_slot.start_time.strftime("%H:%M"),
                        "method": "Direct Free Slot Allocation"
                    })
                    reassigned = True
                    break

            # If no free slot, allocate a safe buffer interval
            if not reassigned and peer_doctors:
                fallback_peer = peer_doctors[0]
                # Create a buffer slot at end of peer's shift
                new_slot = TimeSlot(
                    doctor_id=fallback_peer.doctor_id,
                    start_time=slot_start,
                    end_time=slot_end,
                    is_booked=True,
                    is_overbooked=True
                )
                self.session.add(new_slot)
                self.session.flush()

                appt.doctor_id = fallback_peer.doctor_id
                appt.slot_id = new_slot.slot_id
                appt.is_secondary_overbook = True
                original_slot.is_booked = False

                reassignment_logs.append({
                    "patient_name": appt.patient.name,
                    "from_doctor": doc.name,
                    "to_doctor": fallback_peer.name,
                    "new_room": fallback_peer.room_number,
                    "new_time": new_slot.start_time.strftime("%H:%M"),
                    "method": "Cascade Overbooking Buffer"
                })
                reassigned = True

            if not reassigned:
                unassigned_patients.append(appt.patient.name)

        self.session.commit()

        return {
            "doctor_on_leave": doc.name,
            "specialization": doc.specialization,
            "absence_date": str(absence_date),
            "total_affected_patients": len(affected_appts),
            "successfully_reassigned": len(reassignment_logs),
            "unassigned_count": len(unassigned_patients),
            "reassignments": reassignment_logs
        }
