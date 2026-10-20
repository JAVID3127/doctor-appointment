import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.core.models import (
    Base, Department, Doctor, Patient, TimeSlot,
    Appointment, EmergencyTriage, AppointmentStatus, TriageSeverity
)
from src.overbooking.smart_overbooker import SmartOverbookingEngine
from src.conflicts.conflict_resolver import ConflictResolutionEngine

@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session for Week 5 testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def setup_hospital_entities(session):
    """Helper to populate sample departments and doctors."""
    dept = Department(dept_name="General Medicine", default_slot_duration_mins=15, floor_number=1)
    session.add(dept)
    session.flush()

    doc1 = Doctor(name="Dr. Rajesh Sharma", specialization="General Medicine", room_number="OPD-101", dept_id=dept.dept_id, max_daily_capacity=20)
    doc2 = Doctor(name="Dr. Anita Desai", specialization="General Medicine", room_number="OPD-102", dept_id=dept.dept_id, max_daily_capacity=20)
    session.add_all([doc1, doc2])

    p1 = Patient(name="Patient One", age=30, gender="Male", phone="9000000001", total_visits=5, past_no_shows=3)
    p2 = Patient(name="Patient Two", age=40, gender="Female", phone="9000000002", total_visits=10, past_no_shows=0)
    p3 = Patient(name="Patient Three", age=50, gender="Male", phone="9000000003", total_visits=4, past_no_shows=1)
    session.add_all([p1, p2, p3])
    session.commit()
    return dept, doc1, doc2, p1, p2, p3

def test_expected_attendance_calculation(db_session):
    dept, doc1, doc2, p1, p2, p3 = setup_hospital_entities(db_session)
    overbooker = SmartOverbookingEngine(db_session)

    today = date(2026, 10, 20)
    st1 = datetime(2026, 10, 20, 9, 0)
    st2 = datetime(2026, 10, 20, 9, 15)

    s1 = TimeSlot(doctor_id=doc1.doctor_id, start_time=st1, end_time=st1 + timedelta(minutes=15), is_booked=True)
    s2 = TimeSlot(doctor_id=doc1.doctor_id, start_time=st2, end_time=st2 + timedelta(minutes=15), is_booked=True)
    db_session.add_all([s1, s2])
    db_session.flush()

    # Appt 1: p_noshow = 0.60 (show prob = 0.40)
    # Appt 2: p_noshow = 0.10 (show prob = 0.90)
    a1 = Appointment(patient_id=p1.patient_id, doctor_id=doc1.doctor_id, slot_id=s1.slot_id, predicted_no_show_prob=0.60, status=AppointmentStatus.BOOKED)
    a2 = Appointment(patient_id=p2.patient_id, doctor_id=doc1.doctor_id, slot_id=s2.slot_id, predicted_no_show_prob=0.10, status=AppointmentStatus.BOOKED)
    db_session.add_all([a1, a2])
    db_session.commit()

    stats = overbooker.calculate_expected_shift_attendance(doc1.doctor_id, today)
    assert stats["total_booked"] == 2
    # Expected attendees = 0.40 + 0.90 = 1.30
    assert stats["expected_attendees"] == 1.30
    assert stats["expected_no_shows"] == 0.70

def test_smart_overbooking_authorization_and_execution(db_session):
    dept, doc1, doc2, p1, p2, p3 = setup_hospital_entities(db_session)
    overbooker = SmartOverbookingEngine(db_session)

    today = date(2026, 10, 20)
    st = datetime(2026, 10, 20, 9, 0)
    slot = TimeSlot(doctor_id=doc1.doctor_id, start_time=st, end_time=st + timedelta(minutes=15), is_booked=True)
    db_session.add(slot)
    db_session.flush()

    # Primary patient has high no-show risk (65%)
    primary_appt = Appointment(patient_id=p1.patient_id, doctor_id=doc1.doctor_id, slot_id=slot.slot_id, predicted_no_show_prob=0.65)
    db_session.add(primary_appt)
    db_session.commit()

    # Evaluate overbooking for incoming patient with 20% risk
    can_overbook, reason = overbooker.can_overbook_slot(slot.slot_id, incoming_p_noshow=0.20, target_date=today)
    assert can_overbook is True
    assert "AUTHORIZED" in reason

    # Execute overbooking
    sec_appt = overbooker.execute_smart_overbook(slot.slot_id, patient_id=p2.patient_id, doctor_id=doc1.doctor_id, predicted_no_show=0.20)
    assert sec_appt.is_secondary_overbook is True
    assert slot.is_overbooked is True

    # Double overbooking attempt (exceeding +1 cap) should fail
    can_third, reason_third = overbooker.can_overbook_slot(slot.slot_id, incoming_p_noshow=0.80)
    assert can_third is False
    assert "Hard cap" in reason_third

def test_overbooking_denial_on_low_risk_patients(db_session):
    dept, doc1, doc2, p1, p2, p3 = setup_hospital_entities(db_session)
    overbooker = SmartOverbookingEngine(db_session)

    today = date(2026, 10, 20)
    st = datetime(2026, 10, 20, 9, 0)
    slot = TimeSlot(doctor_id=doc1.doctor_id, start_time=st, end_time=st + timedelta(minutes=15), is_booked=True)
    db_session.add(slot)
    db_session.flush()

    # Both primary and incoming patients have low no-show risk (5% and 10%)
    primary_appt = Appointment(patient_id=p2.patient_id, doctor_id=doc1.doctor_id, slot_id=slot.slot_id, predicted_no_show_prob=0.05)
    db_session.add(primary_appt)
    db_session.commit()

    can_overbook, reason = overbooker.can_overbook_slot(slot.slot_id, incoming_p_noshow=0.10, target_date=today)
    assert can_overbook is False
    assert "Risk too low" in reason

def test_cancellation_promotion_workflow(db_session):
    dept, doc1, doc2, p1, p2, p3 = setup_hospital_entities(db_session)
    overbooker = SmartOverbookingEngine(db_session)

    st = datetime(2026, 10, 20, 9, 0)
    slot = TimeSlot(doctor_id=doc1.doctor_id, start_time=st, end_time=st + timedelta(minutes=15), is_booked=True, is_overbooked=True)
    db_session.add(slot)
    db_session.flush()

    primary_appt = Appointment(patient_id=p1.patient_id, doctor_id=doc1.doctor_id, slot_id=slot.slot_id, is_secondary_overbook=False)
    secondary_appt = Appointment(patient_id=p2.patient_id, doctor_id=doc1.doctor_id, slot_id=slot.slot_id, is_secondary_overbook=True)
    db_session.add_all([primary_appt, secondary_appt])
    db_session.commit()

    # Primary cancels
    promoted = overbooker.handle_cancellation_promotion(primary_appt.appointment_id)
    assert promoted is not None
    assert promoted.appointment_id == secondary_appt.appointment_id
    assert promoted.is_secondary_overbook is False
    assert slot.is_overbooked is False
    assert primary_appt.status == AppointmentStatus.CANCELLED

def test_emergency_walk_in_triage_preemption(db_session):
    dept, doc1, doc2, p1, p2, p3 = setup_hospital_entities(db_session)
    resolver = ConflictResolutionEngine(db_session)

    # Emergency patient arrives with severity 1 (Critical)
    triage_res = resolver.register_emergency_walk_in(p1.patient_id, dept.dept_id, severity=TriageSeverity.CRITICAL.value)
    assert triage_res["triage_id"] is not None
    assert triage_res["severity_level"] == 1
    assert triage_res["assigned_doctor"] in ["Dr. Rajesh Sharma", "Dr. Anita Desai"]

def test_doctor_absence_cascade_reassignment(db_session):
    dept, doc1, doc2, p1, p2, p3 = setup_hospital_entities(db_session)
    resolver = ConflictResolutionEngine(db_session)

    absence_date = date(2026, 10, 20)
    st1 = datetime(2026, 10, 20, 9, 0)
    st2 = datetime(2026, 10, 20, 9, 15)

    # Create 2 slots for Dr. Rajesh Sharma and 2 free slots for Dr. Anita Desai
    s_rajesh_1 = TimeSlot(doctor_id=doc1.doctor_id, start_time=st1, end_time=st1 + timedelta(minutes=15), is_booked=True)
    s_rajesh_2 = TimeSlot(doctor_id=doc1.doctor_id, start_time=st2, end_time=st2 + timedelta(minutes=15), is_booked=True)
    s_anita_1 = TimeSlot(doctor_id=doc2.doctor_id, start_time=st1, end_time=st1 + timedelta(minutes=15), is_booked=False)
    s_anita_2 = TimeSlot(doctor_id=doc2.doctor_id, start_time=st2, end_time=st2 + timedelta(minutes=15), is_booked=False)
    db_session.add_all([s_rajesh_1, s_rajesh_2, s_anita_1, s_anita_2])
    db_session.flush()

    a1 = Appointment(patient_id=p1.patient_id, doctor_id=doc1.doctor_id, slot_id=s_rajesh_1.slot_id, status=AppointmentStatus.BOOKED)
    a2 = Appointment(patient_id=p2.patient_id, doctor_id=doc1.doctor_id, slot_id=s_rajesh_2.slot_id, status=AppointmentStatus.BOOKED)
    db_session.add_all([a1, a2])
    db_session.commit()

    # Dr. Rajesh calls in sick! Run cascade
    cascade_res = resolver.execute_doctor_absence_cascade(doc1.doctor_id, absence_date)
    assert cascade_res["doctor_on_leave"] == "Dr. Rajesh Sharma"
    assert cascade_res["total_affected_patients"] == 2
    assert cascade_res["successfully_reassigned"] == 2
    assert doc1.is_available is False

    # Verify both appointments reassigned to Dr. Anita Desai
    db_session.refresh(a1)
    db_session.refresh(a2)
    assert a1.doctor_id == doc2.doctor_id
    assert a2.doctor_id == doc2.doctor_id
    assert s_rajesh_1.is_booked is False
    assert s_anita_1.is_booked is True
