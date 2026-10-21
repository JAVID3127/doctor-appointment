"""
Comprehensive Phase 4 Verification Test Suite
Tests every case requested in the Audit specification:
1. Successful booking
2. Unavailable slot
3. Conflicting appointment
4. Alternative slot suggestion
5. Duplicate booking attempt
6. Cancellation and queue update
7. Waiting hall with no appointments
8. Waiting hall with multiple appointments
9. Patient refreshes the page
10. Backend or API error
11. Doctor marks a patient as in consultation and then completed
12. Unauthorized user attempts to access protected information
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Doctor, Department, Patient, Appointment, AppointmentStatus, TimeSlot
from src.services import HospitalOPDService
from app import create_app

@pytest.fixture
def phase4_client():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    service = HospitalOPDService(session)
    service.seed_initial_data_if_empty()
    session.close()

    app = create_app(custom_engine=engine)
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

def test_1_successful_booking(phase4_client):
    """Verifies standard successful booking per flowchart step 1-12."""
    res = phase4_client.post("/api/appointments", json={
        "name": "Rohan Verma",
        "phone": "9876543210",
        "age": 29,
        "gender": "Male",
        "email": "rohan.v@example.com",
        "doctor_id": 1,
        "slot_id": 1,
        "lead_days": 2,
        "sms_sent": True
    })
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert "token" in data
    assert data["patient_name"] == "Rohan Verma"
    assert data["doctor_name"] is not None
    assert data["room_number"] == "OPD-101"

def test_2_and_3_unavailable_slot_and_conflicting_appointment(phase4_client):
    """Verifies that an already overbooked/full slot rejects conflicting bookings."""
    # Patient 1 books slot 2 (primary)
    res1 = phase4_client.post("/api/appointments", json={
        "name": "Patient One",
        "phone": "9811111111",
        "age": 30,
        "gender": "Male",
        "doctor_id": 1,
        "slot_id": 2,
        "lead_days": 1,
        "sms_sent": True
    })
    assert res1.status_code == 201

    # Patient 2 with high attendance attempts overbooking (should be denied if attendance is high)
    res2 = phase4_client.post("/api/appointments", json={
        "name": "Patient Two",
        "phone": "9822222222",
        "age": 32,
        "gender": "Female",
        "doctor_id": 1,
        "slot_id": 2,
        "lead_days": 0,
        "sms_sent": True
    })
    assert res2.status_code == 400
    assert "already booked" in res2.get_json()["error"] or "denied" in res2.get_json()["error"]

def test_4_alternative_slot_suggestion(phase4_client):
    """Verifies query of available slots to suggest alternative when chosen slot is busy."""
    slots_res = phase4_client.get("/api/doctors/1/slots")
    assert slots_res.status_code == 200
    slots = slots_res.get_json()
    open_slots = [s for s in slots if not s["is_booked"]]
    assert len(open_slots) > 0
    # First alternative slot is cleanly identifiable
    alt_slot = open_slots[0]
    assert alt_slot["slot_id"] is not None
    assert "start_time" in alt_slot

def test_5_duplicate_booking_attempt(phase4_client):
    """Verifies that the same patient cannot book the exact same slot twice."""
    res1 = phase4_client.post("/api/appointments", json={
        "name": "Duplicate Tester",
        "phone": "9833333333",
        "age": 40,
        "gender": "Male",
        "doctor_id": 2,
        "slot_id": 13,
        "lead_days": 1,
        "sms_sent": True
    })
    assert res1.status_code == 201

    res2 = phase4_client.post("/api/appointments", json={
        "name": "Duplicate Tester",
        "phone": "9833333333",
        "age": 40,
        "gender": "Male",
        "doctor_id": 2,
        "slot_id": 13,
        "lead_days": 1,
        "sms_sent": True
    })
    assert res2.status_code == 400
    assert "already hold an active booking" in res2.get_json()["error"]

def test_6_cancellation_and_queue_update(phase4_client):
    """Verifies appointment cancellation releases slot and updates patient tracker."""
    book_res = phase4_client.post("/api/appointments", json={
        "name": "Cancel Tester",
        "phone": "9844444444",
        "age": 25,
        "gender": "Female",
        "doctor_id": 3,
        "slot_id": 25,
        "lead_days": 1,
        "sms_sent": True
    })
    assert book_res.status_code == 201
    appt_id = book_res.get_json()["data"]["appointment_id"]
    token = book_res.get_json()["data"]["token"]

    # Cancel with authorized phone
    cancel_res = phase4_client.post(f"/api/appointments/{appt_id}/cancel", json={"phone": "9844444444"})
    assert cancel_res.status_code == 200
    assert cancel_res.get_json()["success"] is True

    # Check tracker
    track_res = phase4_client.get(f"/api/queue/track?query={token}")
    records = track_res.get_json()["results"]
    assert len(records) == 1
    assert records[0]["status"] == "CANCELLED"

def test_7_and_8_waiting_hall_lifecycle(phase4_client):
    """Verifies waiting hall token board with empty queue and multiple appointments."""
    # 7. Initial empty / default board
    board_res = phase4_client.get("/api/queue/token-board")
    assert board_res.status_code == 200
    board_data = board_res.get_json()
    assert "board" in board_data
    assert "summary" in board_data
    assert len(board_data["board"]) >= 5  # Hospital seeded doctors

    # 8. Book multiple appointments for Doctor 1 (Room OPD-101)
    phase4_client.post("/api/appointments", json={
        "name": "Patient Alpha",
        "phone": "9855555551",
        "age": 22,
        "gender": "Male",
        "doctor_id": 1,
        "slot_id": 3,
        "lead_days": 1,
        "sms_sent": True
    })
    phase4_client.post("/api/appointments", json={
        "name": "Patient Beta",
        "phone": "9855555552",
        "age": 35,
        "gender": "Female",
        "doctor_id": 1,
        "slot_id": 4,
        "lead_days": 1,
        "sms_sent": True
    })

    board_res2 = phase4_client.get("/api/queue/token-board")
    doc1 = next(r for r in board_res2.get_json()["board"] if r["room_number"] == "OPD-101")
    assert doc1["patients_waiting"] >= 2
    assert len(doc1["upcoming_tokens"]) >= 2
    assert doc1["doctor_name"] is not None

def test_9_patient_refreshes_page(phase4_client):
    """Verifies that all views reload cleanly without error."""
    views = ["/", "/book", "/display", "/track", "/login", "/register", "/health"]
    for v in views:
        res = phase4_client.get(v)
        assert res.status_code == 200, f"Failed on view {v}"

def test_10_backend_or_api_error_handling(phase4_client):
    """Verifies graceful JSON error responses for invalid inputs."""
    # Missing required field
    res = phase4_client.post("/api/appointments", json={"name": "Incomplete"})
    assert res.status_code == 400
    assert "error" in res.get_json()

    # Invalid phone
    res2 = phase4_client.post("/api/appointments", json={
        "name": "Bad Phone",
        "phone": "123",
        "age": 25,
        "gender": "Male",
        "doctor_id": 1,
        "slot_id": 5
    })
    assert res2.status_code == 400
    assert "mobile number" in res2.get_json()["error"]

def test_11_doctor_marks_in_consultation_and_completed(phase4_client):
    """Verifies full clinical consultation progression."""
    book_res = phase4_client.post("/api/appointments", json={
        "name": "Consultation Subject",
        "phone": "9866666666",
        "age": 45,
        "gender": "Male",
        "doctor_id": 1,
        "slot_id": 5,
        "lead_days": 0,
        "sms_sent": True
    })
    appt_id = book_res.get_json()["data"]["appointment_id"]

    # Doctor calls patient into consultation room
    c_res = phase4_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "IN_CONSULTATION"})
    assert c_res.status_code == 200
    assert c_res.get_json()["data"]["status"] == "IN_CONSULTATION"

    # Doctor marks consultation complete
    done_res = phase4_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "COMPLETED"})
    assert done_res.status_code == 200
    assert done_res.get_json()["data"]["status"] == "COMPLETED"

def test_12_unauthorized_user_access_prevention(phase4_client):
    """Verifies patient private records cannot be accessed or modified by unauthorized users."""
    # 1. Book for Patient A
    book_a = phase4_client.post("/api/appointments", json={
        "name": "Patient Alice",
        "phone": "9877777771",
        "age": 29,
        "gender": "Female",
        "doctor_id": 1,
        "slot_id": 6,
        "lead_days": 1,
        "sms_sent": True
    })
    appt_a_id = book_a.get_json()["data"]["appointment_id"]

    # 2. Unauthorized attempt to cancel Patient A's appointment with Patient B's phone
    unauth_cancel = phase4_client.post(f"/api/appointments/{appt_a_id}/cancel", json={"phone": "9999999999"})
    assert unauth_cancel.status_code == 403
    assert "Access Denied" in unauth_cancel.get_json()["error"]

    # 3. Patient portal requires authenticated session
    portal_res = phase4_client.get("/patient/dashboard")
    assert portal_res.status_code == 302  # Redirected to login
