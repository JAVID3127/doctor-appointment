from typing import Dict, Any, Tuple, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session

from ..core.models import TimeSlot, Appointment, Doctor, Patient, AppointmentStatus
from ..core.config import MAX_OVERBOOK_PER_SLOT, OVERBOOK_NO_SHOW_THRESHOLD, MAX_SHIFT_OVERBOOK_RATE

class SmartOverbookingEngine:
    """
    Intelligent Overbooking Controller.
    Balances doctor capacity utilization with waiting room congestion limits
    using mathematical expectations of patient attendance.
    """

    def __init__(self, session: Session):
        self.session = session

    def calculate_expected_shift_attendance(self, doctor_id: int, target_date: date) -> Dict[str, Any]:
        """
        Computes the expected number of arriving patients for a doctor's shift:
        E[Attendees] = sum(1 - P(no-show_i)) for all active bookings.
        """
        doc = self.session.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doc:
            raise ValueError(f"Doctor #{doctor_id} not found.")

        # Query all active appointments for this doctor on target_date
        active_appts = self.session.query(Appointment).join(TimeSlot).filter(
            Appointment.doctor_id == doctor_id,
            TimeSlot.start_time >= datetime.combine(target_date, datetime.min.time()),
            TimeSlot.start_time <= datetime.combine(target_date, datetime.max.time()),
            Appointment.status.notin_([AppointmentStatus.CANCELLED])
        ).all()

        total_booked = len(active_appts)
        overbooked_count = sum(1 for a in active_appts if a.is_secondary_overbook)
        
        # Expected attendees = sum(1 - p_i)
        expected_attendees = sum((1.0 - a.predicted_no_show_prob) for a in active_appts)
        expected_no_shows = total_booked - expected_attendees

        capacity = doc.max_daily_capacity
        overbook_ceiling = int(capacity * MAX_SHIFT_OVERBOOK_RATE)

        return {
            "doctor_id": doc.doctor_id,
            "doctor_name": doc.name,
            "max_daily_capacity": capacity,
            "total_booked": total_booked,
            "overbooked_count": overbooked_count,
            "overbook_ceiling": overbook_ceiling,
            "expected_attendees": round(expected_attendees, 2),
            "expected_no_shows": round(expected_no_shows, 2),
            "capacity_slack": round(capacity - expected_attendees, 2)
        }

    def can_overbook_slot(
        self,
        slot_id: int,
        incoming_p_noshow: float,
        target_date: Optional[date] = None
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a slot is mathematically and operationally safe to overbook.
        """
        slot = self.session.query(TimeSlot).filter(TimeSlot.slot_id == slot_id).first()
        if not slot:
            return False, f"Slot #{slot_id} does not exist."

        if not slot.is_booked:
            return False, f"Slot #{slot_id} is currently empty. Primary booking should be used instead of overbooking."

        if slot.is_overbooked:
            return False, f"Slot #{slot_id} already has a secondary overbooking (Hard cap of +{MAX_OVERBOOK_PER_SLOT} reached)."

        # Fetch existing primary appointment on this slot
        primary_appt = self.session.query(Appointment).filter(
            Appointment.slot_id == slot_id,
            Appointment.status.notin_([AppointmentStatus.CANCELLED])
        ).first()

        primary_risk = primary_appt.predicted_no_show_prob if primary_appt else 0.0

        # Smart overbooking rule: At least one patient must have elevated no-show risk
        max_risk = max(primary_risk, incoming_p_noshow)
        if max_risk < OVERBOOK_NO_SHOW_THRESHOLD:
            return False, (
                f"Risk too low to overbook safely. Primary risk={primary_risk:.1%}, "
                f"Incoming risk={incoming_p_noshow:.1%}. Threshold is {OVERBOOK_NO_SHOW_THRESHOLD:.0%}."
            )

        # Check shift capacity constraint
        shift_date = target_date or slot.start_time.date()
        stats = self.calculate_expected_shift_attendance(slot.doctor_id, shift_date)

        if stats["overbooked_count"] >= stats["overbook_ceiling"]:
            return False, f"Shift overbooking ceiling of {stats['overbook_ceiling']} extra patients reached for this doctor."

        incoming_show_prob = 1.0 - incoming_p_noshow
        new_expected = stats["expected_attendees"] + incoming_show_prob
        if new_expected > stats["max_daily_capacity"] + 0.5:
            return False, f"Expected attendance ({new_expected:.1f}) exceeds doctor capacity ({stats['max_daily_capacity']})."

        return True, "AUTHORIZED: High no-show probability enables safe secondary overbooking without congestion."

    def execute_smart_overbook(
        self,
        slot_id: int,
        patient_id: int,
        doctor_id: int,
        predicted_no_show: float
    ) -> Appointment:
        """
        Executes an authorized smart overbooking on an existing slot.
        """
        can_overbook, reason = self.can_overbook_slot(slot_id, predicted_no_show)
        if not can_overbook:
            raise ValueError(f"Smart Overbooking Denied: {reason}")

        slot = self.session.query(TimeSlot).filter(TimeSlot.slot_id == slot_id).first()
        slot.is_overbooked = True

        appt = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            booking_timestamp=datetime.now(),
            status=AppointmentStatus.CONFIRMED,
            predicted_no_show_prob=predicted_no_show,
            is_secondary_overbook=True
        )
        self.session.add(appt)
        self.session.commit()
        self.session.refresh(appt)
        return appt

    def handle_cancellation_promotion(self, cancelled_appointment_id: int) -> Optional[Appointment]:
        """
        When a primary appointment is cancelled, if the slot had a secondary overbooked patient,
        promotes the secondary patient to primary status and unmarks the slot's overbooked flag.
        """
        appt = self.session.query(Appointment).filter(Appointment.appointment_id == cancelled_appointment_id).first()
        if not appt:
            return None

        slot = appt.slot
        appt.status = AppointmentStatus.CANCELLED

        promoted_appt = None
        if slot and slot.is_overbooked:
            # Find the secondary booking on this slot
            secondary_appt = self.session.query(Appointment).filter(
                Appointment.slot_id == slot.slot_id,
                Appointment.appointment_id != cancelled_appointment_id,
                Appointment.status.notin_([AppointmentStatus.CANCELLED])
            ).first()

            if secondary_appt:
                secondary_appt.is_secondary_overbook = False
                slot.is_overbooked = False
                promoted_appt = secondary_appt
        else:
            if slot:
                slot.is_booked = False

        self.session.commit()
        return promoted_appt
