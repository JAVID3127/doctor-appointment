import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Department, Doctor, Patient, TimeSlot, Appointment
from src.algorithms import (
    AppointmentRequest,
    earliest_finish_time_schedule,
    interval_partitioning_multidoctor,
    compact_shift_schedule,
    IntervalSchedulingEngine
)

@pytest.fixture
def db_session():
    """Provides an isolated in-memory SQLite database session for scheduling tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_earliest_finish_time_single_doctor():
    base = datetime(2026, 10, 20, 9, 0)
    # Request A: 09:00 - 09:30
    req_a = AppointmentRequest("REQ-1", 1, "P1", "General", base, base + timedelta(minutes=30))
    # Request B: 09:15 - 09:45 (conflicts with A and C)
    req_b = AppointmentRequest("REQ-2", 2, "P2", "General", base + timedelta(minutes=15), base + timedelta(minutes=45))
    # Request C: 09:30 - 10:00 (compatible with A)
    req_c = AppointmentRequest("REQ-3", 3, "P3", "General", base + timedelta(minutes=30), base + timedelta(minutes=60))

    accepted = earliest_finish_time_schedule([req_a, req_b, req_c])

    # EFT must select A and C (cardinality 2), rejecting B
    assert len(accepted) == 2
    assert accepted[0].request_id == "REQ-1"
    assert accepted[1].request_id == "REQ-3"

def test_eft_nested_intervals_edge_case():
    base = datetime(2026, 10, 20, 9, 0)
    # One long appointment spanning 2 hours
    long_req = AppointmentRequest("LONG", 100, "Slow Patient", "General", base, base + timedelta(hours=2))

    # Four 30-min appointments fitting in the same 2 hours
    short_reqs = [
        AppointmentRequest(f"SHORT-{i}", i, f"P{i}", "General", base + timedelta(minutes=i*30), base + timedelta(minutes=(i+1)*30))
        for i in range(4)
    ]

    all_requests = [long_req] + short_reqs
    accepted = earliest_finish_time_schedule(all_requests)

    # EFT should accept all 4 short appointments and reject the long one!
    assert len(accepted) == 4
    for appt in accepted:
        assert appt.request_id != "LONG"

def test_multi_doctor_interval_partitioning():
    base = datetime(2026, 10, 20, 9, 0)
    doctor_ids = [101, 102]

    # 4 overlapping requests at 9:00, 9:15, 9:30, 9:45 each 30 mins
    requests = [
        AppointmentRequest(f"REQ-{i}", i, f"P{i}", "Cardiology",
                           base + timedelta(minutes=i*15),
                           base + timedelta(minutes=i*15 + 30))
        for i in range(4)
    ]

    schedule = interval_partitioning_multidoctor(requests, doctor_ids)

    # Total scheduled should be 4
    total_scheduled = sum(len(reqs) for reqs in schedule.values())
    assert total_scheduled == 4

    # Verify that NO doctor has overlapping appointments
    for doc_id, assigned_reqs in schedule.items():
        for i in range(len(assigned_reqs)):
            for j in range(i + 1, len(assigned_reqs)):
                assert not assigned_reqs[i].overlaps_with(assigned_reqs[j]), f"Overlap found for doctor #{doc_id}"

def test_compact_shift_schedule():
    shift_start = datetime(2026, 10, 20, 9, 0)
    shift_end = datetime(2026, 10, 20, 11, 0)

    requests = [
        AppointmentRequest("REQ-1", 1, "P1", "General", shift_start, shift_start + timedelta(minutes=20)),
        AppointmentRequest("REQ-2", 2, "P2", "General", shift_start, shift_start + timedelta(minutes=20)),
        AppointmentRequest("REQ-3", 3, "P3", "General", shift_start, shift_start + timedelta(minutes=20)),
    ]

    # Compact schedule with 5 min buffer
    packed = compact_shift_schedule(shift_start, shift_end, requests, buffer_mins=5)
    assert len(packed) == 3

    # Check timings:
    # Appt 1: 09:00 - 09:20
    # Appt 2: 09:25 - 09:45
    # Appt 3: 09:50 - 10:10
    assert packed[0][0] == shift_start
    assert packed[0][1] == shift_start + timedelta(minutes=20)
    assert packed[1][0] == shift_start + timedelta(minutes=25)
    assert packed[2][0] == shift_start + timedelta(minutes=50)

def test_engine_batch_scheduling_and_utilization(db_session):
    engine = IntervalSchedulingEngine(db_session)

    dept = Department(dept_name="Orthopedics", default_slot_duration_mins=15, floor_number=1)
    db_session.add(dept)
    db_session.flush()

    doc1 = Doctor(name="Dr. Reddy", specialization="Orthopedics", room_number="OPD-105", dept_id=dept.dept_id)
    doc2 = Doctor(name="Dr. Iyer", specialization="Orthopedics", room_number="OPD-106", dept_id=dept.dept_id)
    db_session.add_all([doc1, doc2])
    db_session.flush()

    patient = Patient(name="Patient Test", age=30, gender="Male", phone="9999900001")
    db_session.add(patient)
    db_session.commit()

    base = datetime(2026, 10, 20, 9, 0)
    requests = [
        AppointmentRequest(f"REQ-{i}", patient.patient_id, f"Patient {i}", "Orthopedics",
                           base + timedelta(minutes=i*20),
                           base + timedelta(minutes=i*20 + 20))
        for i in range(6)
    ]

    target_date = date(2026, 10, 20)
    res = engine.schedule_department_batch(dept.dept_id, requests, target_date)

    assert res["total_requests"] == 6
    assert res["total_scheduled"] == 6
    assert res["doctors_utilized"] >= 1

    # Check utilization calculation
    util = engine.compute_doctor_utilization(doc1.doctor_id, target_date, start_hour=9, end_hour=13)
    assert util["total_shift_minutes"] == 240
    assert util["active_consultation_minutes"] > 0
    assert util["utilization_rate_pct"] > 0.0

def test_stress_50_patient_requests_zero_overlap():
    base = datetime(2026, 10, 20, 9, 0)
    doctor_ids = [1, 2, 3, 4]

    # Generate 50 requests across 5 hours
    requests = []
    for i in range(50):
        start_min = (i % 20) * 15
        dur = 15 if i % 2 == 0 else 20
        st = base + timedelta(minutes=start_min)
        et = st + timedelta(minutes=dur)
        requests.append(AppointmentRequest(f"STRESS-{i}", i, f"Patient {i}", "Medicine", st, et))

    schedule = interval_partitioning_multidoctor(requests, doctor_ids)

    # Ensure ZERO overlaps in every doctor's allocated schedule
    for doc_id, assigned_reqs in schedule.items():
        for i in range(len(assigned_reqs)):
            for j in range(i + 1, len(assigned_reqs)):
                assert not assigned_reqs[i].overlaps_with(assigned_reqs[j]), (
                    f"Collision in doctor #{doc_id} schedule between "
                    f"'{assigned_reqs[i].request_id}' and '{assigned_reqs[j].request_id}'"
                )

def test_adjacent_intervals_compatibility():
    """Adjacent intervals (end_time of A == start_time of B) must not conflict."""
    base = datetime(2026, 10, 20, 9, 0)
    req_a = AppointmentRequest("ADJ-1", 1, "P1", "General", base, base + timedelta(minutes=15))
    req_b = AppointmentRequest("ADJ-2", 2, "P2", "General", base + timedelta(minutes=15), base + timedelta(minutes=30))
    req_c = AppointmentRequest("ADJ-3", 3, "P3", "General", base + timedelta(minutes=30), base + timedelta(minutes=45))

    # Overlaps method check
    assert not req_a.overlaps_with(req_b)
    assert not req_b.overlaps_with(req_c)

    # EFT should accept all 3 contiguous appointments
    accepted = earliest_finish_time_schedule([req_a, req_b, req_c])
    assert len(accepted) == 3
    assert [r.request_id for r in accepted] == ["ADJ-1", "ADJ-2", "ADJ-3"]

def test_identical_overlapping_intervals():
    """Two requests with identical time intervals conflict; EFT selects exactly one."""
    base = datetime(2026, 10, 20, 10, 0)
    req_1 = AppointmentRequest("IDEN-1", 10, "P10", "Cardiology", base, base + timedelta(minutes=30), priority=1)
    req_2 = AppointmentRequest("IDEN-2", 11, "P11", "Cardiology", base, base + timedelta(minutes=30), priority=2)

    assert req_1.overlaps_with(req_2)

    accepted = earliest_finish_time_schedule([req_1, req_2])
    assert len(accepted) == 1
    # Higher priority (priority=2) is selected first
    assert accepted[0].request_id == "IDEN-2"

def test_non_overlapping_sparse_intervals():
    """Sparse non-overlapping intervals across the shift should all be accepted."""
    base = datetime(2026, 10, 20, 9, 0)
    reqs = [
        AppointmentRequest(f"SPARSE-{i}", i, f"P{i}", "Pediatrics",
                           base + timedelta(hours=i),
                           base + timedelta(hours=i, minutes=20))
        for i in range(5)
    ]

    accepted = earliest_finish_time_schedule(reqs)
    assert len(accepted) == 5
