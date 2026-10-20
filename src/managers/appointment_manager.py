from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from ..models import Appointment, TimeSlot, Patient, Doctor, AppointmentStatus
from ..state_machine import AppointmentStateMachine, AppointmentState, InvalidStateTransitionError

class AppointmentManager:
    """
    Manages the full lifecycle of outpatient appointments.
    Enforces state transitions via AppointmentStateMachine and syncs slot/patient state.
    """

    def __init__(self, session: Session):
        self.session = session

    def book_appointment(
        self,
        patient_id: int,
        doctor_id: int,
        slot_id: int,
        predicted_no_show: float = 0.0,
        allow_overbook: bool = False
    ) -> Appointment:
        slot = self.session.query(TimeSlot).filter(TimeSlot.slot_id == slot_id).first()
        if not slot:
            raise ValueError(f"TimeSlot #{slot_id} does not exist.")

        if slot.is_booked and not allow_overbook:
            raise ValueError(f"Slot #{slot_id} is already booked. Enable allow_overbook to schedule additional patients.")

        # If already booked and overbooked allowed
        if slot.is_booked and allow_overbook:
            slot.is_overbooked = True
        else:
            slot.is_booked = True

        appt = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            booking_timestamp=datetime.now(),
            status=AppointmentStatus.BOOKED,
            predicted_no_show_prob=predicted_no_show
        )
        self.session.add(appt)
        self.session.commit()
        self.session.refresh(appt)
        return appt

    def get_appointment(self, appointment_id: int) -> Optional[Appointment]:
        return self.session.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()

    def transition_status(self, appointment_id: int, target_status: AppointmentStatus) -> Appointment:
        """Validates and executes a state machine transition."""
        appt = self.get_appointment(appointment_id)
        if not appt:
            raise ValueError(f"Appointment #{appointment_id} not found.")

        current_enum = AppointmentState(appt.status.value)
        target_enum = AppointmentState(target_status.value)

        # Enforce state machine rules
        AppointmentStateMachine.validate_transition(current_enum, target_enum)

        appt.status = target_status

        # Side effects of status transitions
        if target_status == AppointmentStatus.CANCELLED:
            # Free up the slot if it was the only booking
            slot = appt.slot
            if slot and not slot.is_overbooked:
                slot.is_booked = False

        elif target_status == AppointmentStatus.NO_SHOW:
            # Log no-show in patient record
            patient = appt.patient
            if patient:
                patient.total_visits += 1
                patient.past_no_shows += 1

        elif target_status == AppointmentStatus.COMPLETED:
            # Log successful consultation
            patient = appt.patient
            if patient:
                patient.total_visits += 1

        self.session.commit()
        self.session.refresh(appt)
        return appt

    # Explicit Convenience Methods
    def confirm_appointment(self, appointment_id: int) -> Appointment:
        return self.transition_status(appointment_id, AppointmentStatus.CONFIRMED)

    def check_in_patient(self, appointment_id: int) -> Appointment:
        return self.transition_status(appointment_id, AppointmentStatus.CHECKED_IN)

    def start_consultation(self, appointment_id: int) -> Appointment:
        return self.transition_status(appointment_id, AppointmentStatus.IN_CONSULTATION)

    def complete_consultation(self, appointment_id: int) -> Appointment:
        return self.transition_status(appointment_id, AppointmentStatus.COMPLETED)

    def mark_no_show(self, appointment_id: int) -> Appointment:
        return self.transition_status(appointment_id, AppointmentStatus.NO_SHOW)

    def cancel_appointment(self, appointment_id: int) -> Appointment:
        return self.transition_status(appointment_id, AppointmentStatus.CANCELLED)

    def reschedule_appointment(self, appointment_id: int, new_slot_id: int) -> Appointment:
        """Reschedules an active appointment to a new time slot."""
        appt = self.get_appointment(appointment_id)
        if not appt:
            raise ValueError(f"Appointment #{appointment_id} not found.")

        if appt.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            raise ValueError(f"Cannot reschedule appointment in terminal state '{appt.status.value}'.")

        new_slot = self.session.query(TimeSlot).filter(TimeSlot.slot_id == new_slot_id).first()
        if not new_slot:
            raise ValueError(f"Target slot #{new_slot_id} not found.")
        if new_slot.is_booked:
            raise ValueError(f"Target slot #{new_slot_id} is already booked.")

        # Free previous slot
        old_slot = appt.slot
        if old_slot:
            old_slot.is_booked = False
            old_slot.is_overbooked = False

        # Book new slot
        new_slot.is_booked = True
        appt.slot_id = new_slot_id
        appt.doctor_id = new_slot.doctor_id

        self.session.commit()
        self.session.refresh(appt)
        return appt
