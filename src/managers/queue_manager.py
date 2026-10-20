from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from datetime import datetime, date
from ..models import Appointment, Doctor, Department, TimeSlot, AppointmentStatus

class QueueManager:
    """
    Manages live OPD hospital waiting queues, generates patient token numbers,
    and calculates real-time estimated wait times.
    """

    def __init__(self, session: Session):
        self.session = session

    def generate_token(self, appointment: Appointment) -> str:
        """Generates a human-readable hospital token (e.g. 'CARD-004')."""
        dept_prefix = "OPD"
        if appointment.doctor and appointment.doctor.department:
            dept_name = appointment.doctor.department.dept_name.upper()
            dept_prefix = dept_name[:4]
        return f"{dept_prefix}-{appointment.appointment_id:03d}"

    def get_doctor_active_queue(self, doctor_id: int) -> List[Dict]:
        """
        Returns the ordered list of patients waiting to see the doctor
        with token numbers and estimated wait times.
        """
        doc = self.session.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doc:
            raise ValueError(f"Doctor ID #{doctor_id} not found.")

        slot_duration = doc.department.default_slot_duration_mins if doc.department else 15

        # Query checked-in or in-consultation appointments
        appointments = self.session.query(Appointment).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_([AppointmentStatus.IN_CONSULTATION, AppointmentStatus.CHECKED_IN])
        ).join(TimeSlot).order_by(TimeSlot.start_time).all()

        queue_list = []
        waiting_index = 0

        for appt in appointments:
            token = self.generate_token(appt)
            if appt.status == AppointmentStatus.IN_CONSULTATION:
                wait_minutes = 0
                status_label = "IN CONSULTATION (CURRENT)"
            else:
                # Patient is checked in and waiting outside room
                wait_minutes = waiting_index * slot_duration
                status_label = f"WAITING (Position #{waiting_index + 1})"
                waiting_index += 1

            queue_list.append({
                "appointment_id": appt.appointment_id,
                "token": token,
                "patient_id": appt.patient_id,
                "patient_name": appt.patient.name if appt.patient else "Unknown",
                "room_number": doc.room_number,
                "status": appt.status.value,
                "status_label": status_label,
                "estimated_wait_minutes": wait_minutes,
                "slot_time": appt.slot.start_time.strftime("%H:%M") if appt.slot else "?"
            })

        return queue_list

    def get_hospital_token_board(self) -> List[Dict]:
        """Provides an aggregated overview of all doctor rooms for the waiting hall monitor."""
        doctors = self.session.query(Doctor).filter(Doctor.is_available == True).all()
        board = []

        for doc in doctors:
            current_in_room = self.session.query(Appointment).filter(
                Appointment.doctor_id == doc.doctor_id,
                Appointment.status == AppointmentStatus.IN_CONSULTATION
            ).first()

            waiting_count = self.session.query(Appointment).filter(
                Appointment.doctor_id == doc.doctor_id,
                Appointment.status == AppointmentStatus.CHECKED_IN
            ).count()

            current_token = self.generate_token(current_in_room) if current_in_room else "NONE (ROOM READY)"

            board.append({
                "doctor_name": doc.name,
                "specialization": doc.specialization,
                "room_number": doc.room_number,
                "current_token": current_token,
                "patients_waiting": waiting_count,
                "estimated_delay_mins": waiting_count * (doc.department.default_slot_duration_mins if doc.department else 15)
            })

        return board
