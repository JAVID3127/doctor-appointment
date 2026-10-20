from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models import TimeSlot, Doctor

class SlotManager:
    """
    Manages doctor consultation intervals, discrete shift partitioning,
    and interval overlap prevention.
    """

    def __init__(self, session: Session):
        self.session = session

    def check_collision(
        self,
        doctor_id: int,
        start_time: datetime,
        end_time: datetime,
        exclude_slot_id: Optional[int] = None
    ) -> bool:
        """Returns True if doctor already has an overlapping slot in this time range."""
        query = self.session.query(TimeSlot).filter(
            TimeSlot.doctor_id == doctor_id,
            or_(
                and_(TimeSlot.start_time <= start_time, TimeSlot.end_time > start_time),
                and_(TimeSlot.start_time < end_time, TimeSlot.end_time >= end_time),
                and_(TimeSlot.start_time >= start_time, TimeSlot.end_time <= end_time)
            )
        )
        if exclude_slot_id:
            query = query.filter(TimeSlot.slot_id != exclude_slot_id)
        return query.first() is not None

    def create_single_slot(
        self,
        doctor_id: int,
        start_time: datetime,
        end_time: datetime,
        enforce_no_collision: bool = True
    ) -> TimeSlot:
        """Creates a single validated time slot."""
        if end_time <= start_time:
            raise ValueError("Slot end_time must be strictly after start_time.")

        if enforce_no_collision and self.check_collision(doctor_id, start_time, end_time):
            raise ValueError(f"Interval collision detected for doctor #{doctor_id} between {start_time} and {end_time}")

        slot = TimeSlot(
            doctor_id=doctor_id,
            start_time=start_time,
            end_time=end_time,
            is_booked=False,
            is_overbooked=False
        )
        self.session.add(slot)
        self.session.commit()
        self.session.refresh(slot)
        return slot

    def generate_shift_intervals(
        self,
        doctor_id: int,
        shift_date: date,
        start_hour: int = 9,
        end_hour: int = 13,
        interval_mins: int = 15,
        buffer_mins: int = 0
    ) -> List[TimeSlot]:
        """
        Partitions doctor working hours into discrete, non-overlapping intervals.
        Supports optional buffer time between consultations (e.g. 5 min sanitization/rest).
        """
        doc = self.session.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        if not doc:
            raise ValueError(f"Doctor ID #{doctor_id} not found.")

        current_time = datetime(shift_date.year, shift_date.month, shift_date.day, start_hour, 0)
        shift_end = datetime(shift_date.year, shift_date.month, shift_date.day, end_hour, 0)

        created_slots = []
        step = timedelta(minutes=interval_mins + buffer_mins)
        duration = timedelta(minutes=interval_mins)

        while current_time + duration <= shift_end:
            slot_end = current_time + duration
            # Check collision before adding
            if not self.check_collision(doctor_id, current_time, slot_end):
                slot = TimeSlot(
                    doctor_id=doctor_id,
                    start_time=current_time,
                    end_time=slot_end,
                    is_booked=False,
                    is_overbooked=False
                )
                self.session.add(slot)
                created_slots.append(slot)
            current_time += step

        self.session.commit()
        for s in created_slots:
            self.session.refresh(s)
        return created_slots

    def get_free_slots(self, doctor_id: int, target_date: Optional[date] = None) -> List[TimeSlot]:
        query = self.session.query(TimeSlot).filter(
            TimeSlot.doctor_id == doctor_id,
            TimeSlot.is_booked == False
        )
        if target_date:
            query = query.filter(
                TimeSlot.start_time >= datetime.combine(target_date, datetime.min.time()),
                TimeSlot.start_time <= datetime.combine(target_date, datetime.max.time())
            )
        return query.order_by(TimeSlot.start_time).all()

    def get_earliest_free_slot(self, doctor_id: int, target_date: Optional[date] = None) -> Optional[TimeSlot]:
        free_slots = self.get_free_slots(doctor_id, target_date)
        return free_slots[0] if free_slots else None

    def mark_slot_booking(self, slot_id: int, is_booked: bool, is_overbooked: bool = False):
        slot = self.session.query(TimeSlot).filter(TimeSlot.slot_id == slot_id).first()
        if slot:
            slot.is_booked = is_booked
            slot.is_overbooked = is_overbooked
            self.session.commit()
            self.session.refresh(slot)
        return slot
