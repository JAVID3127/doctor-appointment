import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, AppointmentStatus
from src.state_machine import AppointmentStateMachine, AppointmentState, InvalidStateTransitionError
from src.managers import (
    DepartmentManager, DoctorManager, PatientManager,
    SlotManager, AppointmentManager, QueueManager
)

@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session for manager testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_state_machine_transitions():
    # Valid progression
    assert AppointmentStateMachine.can_transition(AppointmentState.BOOKED, AppointmentState.CONFIRMED) is True
    assert AppointmentStateMachine.can_transition(AppointmentState.CONFIRMED, AppointmentState.CHECKED_IN) is True
    assert AppointmentStateMachine.can_transition(AppointmentState.CHECKED_IN, AppointmentState.IN_CONSULTATION) is True
    assert AppointmentStateMachine.can_transition(AppointmentState.IN_CONSULTATION, AppointmentState.COMPLETED) is True

    # Invalid jump
    assert AppointmentStateMachine.can_transition(AppointmentState.BOOKED, AppointmentState.IN_CONSULTATION) is False
    with pytest.raises(InvalidStateTransitionError):
        AppointmentStateMachine.validate_transition(AppointmentState.BOOKED, AppointmentState.IN_CONSULTATION)

    # Terminal state transition attempt
    assert AppointmentStateMachine.can_transition(AppointmentState.COMPLETED, AppointmentState.BOOKED) is False
    with pytest.raises(InvalidStateTransitionError):
        AppointmentStateMachine.validate_transition(AppointmentState.COMPLETED, AppointmentState.BOOKED)

def test_department_and_doctor_managers(db_session):
    dept_mgr = DepartmentManager(db_session)
    doc_mgr = DoctorManager(db_session)

    dept = dept_mgr.register_department(name="Neurology", slot_duration_mins=20, floor_number=4)
    assert dept.dept_id is not None
    assert dept.dept_name == "Neurology"

    doc = doc_mgr.register_doctor(
        name="Dr. Homi Bhabha",
        specialization="Neurology",
        room_number="OPD-401",
        dept_id=dept.dept_id,
        max_capacity=20
    )
    assert doc.doctor_id is not None

    docs_in_dept = dept_mgr.get_doctors_in_department(dept.dept_id)
    assert len(docs_in_dept) == 1
    assert docs_in_dept[0].name == "Dr. Homi Bhabha"

    # Emergency leave toggle
    doc_mgr.set_doctor_availability(doc.doctor_id, is_available=False)
    available_neurologists = doc_mgr.get_available_doctors_by_specialty("Neurology")
    assert len(available_neurologists) == 0

def test_patient_risk_categorization(db_session):
    pat_mgr = PatientManager(db_session)

    # Patient with high no-show history
    p1 = pat_mgr.register_patient(name="Ramesh", age=45, gender="Male", phone="9111111111", total_visits=10, past_no_shows=5)
    profile1 = pat_mgr.get_risk_profile(p1.patient_id)
    assert profile1["risk_category"] == "HIGH RISK"
    assert profile1["recommended_overbook"] is True

    # Patient with perfect attendance
    p2 = pat_mgr.register_patient(name="Lata", age=30, gender="Female", phone="9222222222", total_visits=8, past_no_shows=0)
    profile2 = pat_mgr.get_risk_profile(p2.patient_id)
    assert profile2["risk_category"] == "LOW RISK"
    assert profile2["recommended_overbook"] is False

def test_slot_manager_interval_partitioning(db_session):
    dept_mgr = DepartmentManager(db_session)
    doc_mgr = DoctorManager(db_session)
    slot_mgr = SlotManager(db_session)

    dept = dept_mgr.register_department("General Medicine", slot_duration_mins=15)
    doc = doc_mgr.register_doctor("Dr. Sen", "General Medicine", "OPD-101", dept.dept_id)

    shift_date = date(2026, 10, 20)
    # Generate 9:00 AM to 10:00 AM (4 slots of 15 mins)
    slots = slot_mgr.generate_shift_intervals(
        doctor_id=doc.doctor_id,
        shift_date=shift_date,
        start_hour=9,
        end_hour=10,
        interval_mins=15
    )
    assert len(slots) == 4
    assert slots[0].start_time == datetime(2026, 10, 20, 9, 0)
    assert slots[3].end_time == datetime(2026, 10, 20, 10, 0)

    # Collision test: attempt to add overlapping slot at 09:10
    with pytest.raises(ValueError, match="Interval collision"):
        slot_mgr.create_single_slot(
            doctor_id=doc.doctor_id,
            start_time=datetime(2026, 10, 20, 9, 10),
            end_time=datetime(2026, 10, 20, 9, 25)
        )

def test_appointment_lifecycle_and_reschedule(db_session):
    dept_mgr = DepartmentManager(db_session)
    doc_mgr = DoctorManager(db_session)
    slot_mgr = SlotManager(db_session)
    pat_mgr = PatientManager(db_session)
    appt_mgr = AppointmentManager(db_session)

    dept = dept_mgr.register_department("Cardiology", slot_duration_mins=20)
    doc = doc_mgr.register_doctor("Dr. Patel", "Cardiology", "OPD-201", dept.dept_id)
    pat = pat_mgr.register_patient("Aarav", 35, "Male", "9876500000")

    shift_date = date(2026, 10, 20)
    slots = slot_mgr.generate_shift_intervals(doc.doctor_id, shift_date, start_hour=9, end_hour=11, interval_mins=20)

    # 1. Book appointment
    appt = appt_mgr.book_appointment(patient_id=pat.patient_id, doctor_id=doc.doctor_id, slot_id=slots[0].slot_id)
    assert appt.status == AppointmentStatus.BOOKED
    assert slots[0].is_booked is True

    # 2. Reschedule to slot 1
    appt_mgr.reschedule_appointment(appt.appointment_id, new_slot_id=slots[1].slot_id)
    assert appt.slot_id == slots[1].slot_id
    assert slots[0].is_booked is False
    assert slots[1].is_booked is True

    # 3. Status workflow progression
    appt_mgr.confirm_appointment(appt.appointment_id)
    assert appt.status == AppointmentStatus.CONFIRMED

    appt_mgr.check_in_patient(appt.appointment_id)
    assert appt.status == AppointmentStatus.CHECKED_IN

    appt_mgr.start_consultation(appt.appointment_id)
    assert appt.status == AppointmentStatus.IN_CONSULTATION

    appt_mgr.complete_consultation(appt.appointment_id)
    assert appt.status == AppointmentStatus.COMPLETED
    assert pat.total_visits == 1

def test_queue_manager_token_and_wait_time(db_session):
    dept_mgr = DepartmentManager(db_session)
    doc_mgr = DoctorManager(db_session)
    slot_mgr = SlotManager(db_session)
    pat_mgr = PatientManager(db_session)
    appt_mgr = AppointmentManager(db_session)
    queue_mgr = QueueManager(db_session)

    dept = dept_mgr.register_department("Cardiology", slot_duration_mins=20)
    doc = doc_mgr.register_doctor("Dr. Patel", "Cardiology", "OPD-201", dept.dept_id)
    p1 = pat_mgr.register_patient("Patient 1", 40, "Male", "9000000001")
    p2 = pat_mgr.register_patient("Patient 2", 50, "Female", "9000000002")

    shift_date = date(2026, 10, 20)
    slots = slot_mgr.generate_shift_intervals(doc.doctor_id, shift_date, start_hour=9, end_hour=10, interval_mins=20)

    a1 = appt_mgr.book_appointment(p1.patient_id, doc.doctor_id, slots[0].slot_id)
    a2 = appt_mgr.book_appointment(p2.patient_id, doc.doctor_id, slots[1].slot_id)

    # Confirm and check-in both patients
    appt_mgr.confirm_appointment(a1.appointment_id)
    appt_mgr.check_in_patient(a1.appointment_id)
    appt_mgr.start_consultation(a1.appointment_id)  # Patient 1 is in consultation

    appt_mgr.confirm_appointment(a2.appointment_id)
    appt_mgr.check_in_patient(a2.appointment_id)    # Patient 2 is waiting in lobby

    queue = queue_mgr.get_doctor_active_queue(doc.doctor_id)
    assert len(queue) == 2
    assert queue[0]["token"].startswith("CARD-")
    assert queue[0]["estimated_wait_minutes"] == 0  # In consult
    assert queue[1]["estimated_wait_minutes"] == 0  # 1st in line (starts when current consult finishes)

    # Hospital Token Board check
    board = queue_mgr.get_hospital_token_board()
    assert len(board) == 1
    assert board[0]["doctor_name"] == "Dr. Patel"
    assert board[0]["patients_waiting"] == 1
