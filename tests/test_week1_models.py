import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import (
    Base, Department, Doctor, Patient, TimeSlot,
    Appointment, EmergencyTriage, HistoricalRecord,
    AppointmentStatus, TriageSeverity
)
from src.crud import (
    create_department, create_doctor, get_doctors_by_specialization,
    create_patient, record_patient_attendance,
    create_time_slot, check_slot_collision,
    book_appointment, update_appointment_status,
    register_emergency_triage, create_historical_record
)

@pytest.fixture
def db_session():
    """Provides an isolated, in-memory SQLite database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_department(db_session):
    dept = create_department(db_session, name="Cardiology", slot_duration=20, floor=2)
    assert dept.dept_id is not None
    assert dept.dept_name == "Cardiology"
    assert dept.default_slot_duration_mins == 20
    assert dept.floor_number == 2

def test_create_doctor_and_specialization_filter(db_session):
    dept = create_department(db_session, name="Orthopedics", slot_duration=15, floor=1)
    doc1 = create_doctor(db_session, name="Dr. Rao", specialization="Orthopedics", room_number="OPD-101", dept_id=dept.dept_id)
    doc2 = create_doctor(db_session, name="Dr. Mehta", specialization="Pediatrics", room_number="OPD-201", dept_id=dept.dept_id)

    ortho_docs = get_doctors_by_specialization(db_session, "Orthopedics")
    assert len(ortho_docs) == 1
    assert ortho_docs[0].name == "Dr. Rao"

def test_patient_model_and_no_show_ratio(db_session):
    pat = create_patient(db_session, name="Sunita", age=45, gender="Female", phone="9999988888", total_visits=10, past_no_shows=3)
    assert pat.patient_id is not None
    assert pat.no_show_ratio == 0.3

    # Attendance recording
    record_patient_attendance(db_session, pat.patient_id, attended=False)
    assert pat.total_visits == 11
    assert pat.past_no_shows == 4

def test_time_slot_creation_and_overlap_prevention(db_session):
    dept = create_department(db_session, name="General Medicine")
    doc = create_doctor(db_session, name="Dr. Sharma", specialization="General Medicine", room_number="OPD-101", dept_id=dept.dept_id)

    now = datetime(2026, 10, 20, 9, 0)
    slot1 = create_time_slot(db_session, doctor_id=doc.doctor_id, start_time=now, end_time=now + timedelta(minutes=15))
    assert slot1.slot_id is not None
    assert slot1.duration_minutes == 15

    # Attempt overlapping slot (should raise ValueError)
    overlapping_start = now + timedelta(minutes=5)
    overlapping_end = now + timedelta(minutes=20)
    
    assert check_slot_collision(db_session, doc.doctor_id, overlapping_start, overlapping_end) is True
    
    with pytest.raises(ValueError, match="collision detected"):
        create_time_slot(db_session, doctor_id=doc.doctor_id, start_time=overlapping_start, end_time=overlapping_end)

def test_invalid_slot_time_range(db_session):
    dept = create_department(db_session, name="General Medicine")
    doc = create_doctor(db_session, name="Dr. Sharma", specialization="General Medicine", room_number="OPD-101", dept_id=dept.dept_id)

    now = datetime(2026, 10, 20, 9, 0)
    with pytest.raises(ValueError, match="strictly after"):
        create_time_slot(db_session, doctor_id=doc.doctor_id, start_time=now, end_time=now - timedelta(minutes=10))

def test_appointment_booking_and_status_progression(db_session):
    dept = create_department(db_session, name="General Medicine")
    doc = create_doctor(db_session, name="Dr. Sharma", specialization="General Medicine", room_number="OPD-101", dept_id=dept.dept_id)
    pat = create_patient(db_session, name="Aarav", age=30, gender="Male", phone="9988776655")

    now = datetime(2026, 10, 20, 9, 0)
    slot = create_time_slot(db_session, doctor_id=doc.doctor_id, start_time=now, end_time=now + timedelta(minutes=15))

    appt = book_appointment(db_session, patient_id=pat.patient_id, doctor_id=doc.doctor_id, slot_id=slot.slot_id, predicted_no_show=0.15)
    assert appt.status == AppointmentStatus.BOOKED
    assert slot.is_booked is True

    # Advance status through consultation lifecycle
    update_appointment_status(db_session, appt.appointment_id, AppointmentStatus.CHECKED_IN)
    assert appt.status == AppointmentStatus.CHECKED_IN

    update_appointment_status(db_session, appt.appointment_id, AppointmentStatus.IN_CONSULTATION)
    assert appt.status == AppointmentStatus.IN_CONSULTATION

    update_appointment_status(db_session, appt.appointment_id, AppointmentStatus.COMPLETED)
    assert appt.status == AppointmentStatus.COMPLETED

def test_smart_overbooking_flow(db_session):
    dept = create_department(db_session, name="General Medicine")
    doc = create_doctor(db_session, name="Dr. Sharma", specialization="General Medicine", room_number="OPD-101", dept_id=dept.dept_id)
    pat1 = create_patient(db_session, name="P1", age=25, gender="Male", phone="9911111111")
    pat2 = create_patient(db_session, name="P2", age=35, gender="Female", phone="9922222222")

    now = datetime(2026, 10, 20, 9, 0)
    slot = create_time_slot(db_session, doctor_id=doc.doctor_id, start_time=now, end_time=now + timedelta(minutes=15))

    # First booking
    book_appointment(db_session, patient_id=pat1.patient_id, doctor_id=doc.doctor_id, slot_id=slot.slot_id, predicted_no_show=0.70)
    assert slot.is_booked is True
    assert slot.is_overbooked is False

    # Second booking without force_overbook should fail
    with pytest.raises(ValueError, match="already booked"):
        book_appointment(db_session, patient_id=pat2.patient_id, doctor_id=doc.doctor_id, slot_id=slot.slot_id)

    # Overbooking with force_overbook=True
    appt2 = book_appointment(db_session, patient_id=pat2.patient_id, doctor_id=doc.doctor_id, slot_id=slot.slot_id, force_overbook=True)
    assert appt2 is not None
    assert slot.is_overbooked is True

def test_emergency_triage_and_historical_records(db_session):
    dept = create_department(db_session, name="Cardiology")
    doc = create_doctor(db_session, name="Dr. Patel", specialization="Cardiology", room_number="OPD-201", dept_id=dept.dept_id)
    pat = create_patient(db_session, name="Emergency Case", age=60, gender="Male", phone="9933333333")

    triage = register_emergency_triage(db_session, patient_id=pat.patient_id, doctor_id=doc.doctor_id, severity=TriageSeverity.CRITICAL.value)
    assert triage.triage_id is not None
    assert triage.severity_level == 1

    rec = create_historical_record(db_session, patient_id=pat.patient_id, lead_days=3, day_of_week=1, sms_sent=True, no_show_flag=False)
    assert rec.record_id is not None
    assert rec.no_show_flag is False
