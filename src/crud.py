from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .models import (
    Department, Doctor, Patient, TimeSlot, Appointment,
    EmergencyTriage, HistoricalRecord, AppointmentStatus, TriageSeverity
)

# =============================================================================
# DEPARTMENT OPERATIONS
# =============================================================================

def create_department(session: Session, name: str, slot_duration: int = 15, floor: int = 1) -> Department:
    existing = session.query(Department).filter(Department.dept_name.ilike(name)).first()
    if existing:
        return existing
    dept = Department(dept_name=name, default_slot_duration_mins=slot_duration, floor_number=floor)
    session.add(dept)
    session.commit()
    session.refresh(dept)
    return dept

def get_all_departments(session: Session) -> List[Department]:
    return session.query(Department).order_by(Department.dept_name).all()

def get_department_by_id(session: Session, dept_id: int) -> Optional[Department]:
    return session.query(Department).filter(Department.dept_id == dept_id).first()

# =============================================================================
# DOCTOR OPERATIONS
# =============================================================================

def create_doctor(
    session: Session,
    name: str,
    specialization: str,
    room_number: str,
    dept_id: int,
    max_capacity: int = 30,
    is_available: bool = True
) -> Doctor:
    doc = Doctor(
        name=name,
        specialization=specialization,
        room_number=room_number,
        dept_id=dept_id,
        max_daily_capacity=max_capacity,
        is_available=is_available
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc

def get_doctor_by_id(session: Session, doctor_id: int) -> Optional[Doctor]:
    return session.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()

def get_doctors_by_specialization(session: Session, specialization: str) -> List[Doctor]:
    return session.query(Doctor).filter(
        Doctor.specialization.ilike(f"%{specialization}%"),
        Doctor.is_available == True
    ).all()

def get_all_doctors(session: Session) -> List[Doctor]:
    return session.query(Doctor).order_by(Doctor.specialization, Doctor.name).all()

def update_doctor_availability(session: Session, doctor_id: int, is_available: bool) -> Optional[Doctor]:
    doc = get_doctor_by_id(session, doctor_id)
    if doc:
        doc.is_available = is_available
        session.commit()
        session.refresh(doc)
    return doc

# =============================================================================
# PATIENT OPERATIONS
# =============================================================================

def create_patient(
    session: Session,
    name: str,
    age: int,
    gender: str,
    phone: str,
    total_visits: int = 0,
    past_no_shows: int = 0,
    email: Optional[str] = None
) -> Patient:
    existing = session.query(Patient).filter(Patient.phone == phone).first()
    if existing:
        if email and not existing.email:
            existing.email = email
            session.commit()
        return existing
    patient = Patient(
        name=name,
        age=age,
        gender=gender,
        phone=phone,
        email=email,
        total_visits=total_visits,
        past_no_shows=past_no_shows
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    return patient

def get_patient_by_id(session: Session, patient_id: int) -> Optional[Patient]:
    return session.query(Patient).filter(Patient.patient_id == patient_id).first()

def get_patient_by_phone(session: Session, phone: str) -> Optional[Patient]:
    return session.query(Patient).filter(Patient.phone == phone).first()

def get_all_patients(session: Session) -> List[Patient]:
    return session.query(Patient).order_by(Patient.name).all()

def record_patient_attendance(session: Session, patient_id: int, attended: bool) -> Optional[Patient]:
    patient = get_patient_by_id(session, patient_id)
    if patient:
        patient.total_visits += 1
        if not attended:
            patient.past_no_shows += 1
        session.commit()
        session.refresh(patient)
    return patient

# =============================================================================
# TIME SLOT OPERATIONS & OVERLAP PREVENTION
# =============================================================================

def check_slot_collision(session: Session, doctor_id: int, start_time: datetime, end_time: datetime) -> bool:
    """Returns True if this doctor already has an overlapping slot in this time range."""
    overlap = session.query(TimeSlot).filter(
        TimeSlot.doctor_id == doctor_id,
        or_(
            and_(TimeSlot.start_time <= start_time, TimeSlot.end_time > start_time),
            and_(TimeSlot.start_time < end_time, TimeSlot.end_time >= end_time),
            and_(TimeSlot.start_time >= start_time, TimeSlot.end_time <= end_time)
        )
    ).first()
    return overlap is not None

def create_time_slot(
    session: Session,
    doctor_id: int,
    start_time: datetime,
    end_time: datetime,
    allow_collision: bool = False
) -> TimeSlot:
    if end_time <= start_time:
        raise ValueError("Slot end_time must be strictly after start_time.")
    
    if not allow_collision and check_slot_collision(session, doctor_id, start_time, end_time):
        raise ValueError(f"Time slot collision detected for doctor {doctor_id} between {start_time} and {end_time}")

    slot = TimeSlot(
        doctor_id=doctor_id,
        start_time=start_time,
        end_time=end_time,
        is_booked=False,
        is_overbooked=False
    )
    session.add(slot)
    session.commit()
    session.refresh(slot)
    return slot

def get_available_slots_for_doctor(session: Session, doctor_id: int, date: Optional[datetime.date] = None) -> List[TimeSlot]:
    query = session.query(TimeSlot).filter(
        TimeSlot.doctor_id == doctor_id,
        TimeSlot.is_booked == False
    )
    if date:
        query = query.filter(
            TimeSlot.start_time >= datetime.combine(date, datetime.min.time()),
            TimeSlot.start_time <= datetime.combine(date, datetime.max.time())
        )
    return query.order_by(TimeSlot.start_time).all()

# =============================================================================
# APPOINTMENT OPERATIONS & WORKFLOW
# =============================================================================

def book_appointment(
    session: Session,
    patient_id: int,
    doctor_id: int,
    slot_id: int,
    predicted_no_show: float = 0.0,
    force_overbook: bool = False
) -> Appointment:
    slot = session.query(TimeSlot).filter(TimeSlot.slot_id == slot_id).first()
    if not slot:
        raise ValueError(f"TimeSlot with id {slot_id} does not exist.")

    if slot.is_booked and not force_overbook:
        raise ValueError(f"Slot {slot_id} is already booked. Overbooking must be explicitly enabled.")

    if slot.is_booked and force_overbook:
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
    session.add(appt)
    session.commit()
    session.refresh(appt)
    return appt

def update_appointment_status(
    session: Session,
    appointment_id: int,
    new_status: AppointmentStatus
) -> Optional[Appointment]:
    appt = session.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appt:
        return None
    appt.status = new_status
    session.commit()
    session.refresh(appt)
    return appt

def get_appointments_for_doctor(session: Session, doctor_id: int) -> List[Appointment]:
    return session.query(Appointment).filter(Appointment.doctor_id == doctor_id).order_by(Appointment.appointment_id).all()

# =============================================================================
# EMERGENCY TRIAGE OPERATIONS
# =============================================================================

def register_emergency_triage(
    session: Session,
    patient_id: int,
    doctor_id: int,
    severity: int = TriageSeverity.URGENT.value,
    preempted_slot_id: Optional[int] = None
) -> EmergencyTriage:
    triage = EmergencyTriage(
        patient_id=patient_id,
        doctor_id=doctor_id,
        severity_level=severity,
        arrival_time=datetime.now(),
        preempted_slot_id=preempted_slot_id
    )
    session.add(triage)
    session.commit()
    session.refresh(triage)
    return triage

# =============================================================================
# HISTORICAL RECORDS
# =============================================================================

def create_historical_record(
    session: Session,
    patient_id: int,
    lead_days: int,
    day_of_week: int,
    sms_sent: bool,
    no_show_flag: bool
) -> HistoricalRecord:
    rec = HistoricalRecord(
        patient_id=patient_id,
        lead_days=lead_days,
        day_of_week=day_of_week,
        sms_sent=sms_sent,
        no_show_flag=no_show_flag
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec

def get_all_historical_records(session: Session) -> List[HistoricalRecord]:
    return session.query(HistoricalRecord).all()
