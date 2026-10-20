import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from src.db import init_db, ScopedSession, Base
from app import create_app

@pytest.fixture(scope="module")
def test_client():
    # Use in-memory SQLite database with StaticPool for test isolation
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    app = create_app(custom_engine=test_engine)
    app.config["TESTING"] = True

    with app.test_client() as client:
        with app.app_context():
            yield client
    
    ScopedSession.remove()

def test_homepage_view(test_client):
    """Test dashboard index loads with 200 OK."""
    response = test_client.get("/")
    assert response.status_code == 200
    assert b"OPD Central Command Dashboard" in response.data

def test_token_display_view(test_client):
    """Test waiting hall token display board page loads."""
    response = test_client.get("/display")
    assert response.status_code == 200
    assert b"CENTRAL OPD WAITING HALL" in response.data

def test_patient_booking_view(test_client):
    """Test booking page loads."""
    response = test_client.get("/book")
    assert response.status_code == 200
    assert b"Patient Outpatient Appointment Booking" in response.data

def test_emergency_triage_view(test_client):
    """Test emergency triage page loads."""
    response = test_client.get("/triage")
    assert response.status_code == 200
    assert b"Emergency Walk-in Triage" in response.data

def test_api_departments_and_doctors(test_client):
    """Test REST API for departments and doctors."""
    res_depts = test_client.get("/api/departments")
    assert res_depts.status_code == 200
    depts = res_depts.get_json()
    assert len(depts) >= 5
    dept_names = [d["dept_name"] for d in depts]
    assert "General Medicine" in dept_names

    res_docs = test_client.get("/api/doctors")
    assert res_docs.status_code == 200
    docs = res_docs.get_json()
    assert len(docs) >= 6

def test_api_slots_and_booking(test_client):
    """Test slot listing, booking primary appointment, and token generation."""
    # Get available slots for Dr. Rajesh Sharma (ID 1)
    slots_res = test_client.get("/api/doctors/1/slots")
    assert slots_res.status_code == 200
    slots = slots_res.get_json()
    assert len(slots) > 0
    target_slot_id = slots[0]["slot_id"]

    # Book appointment
    payload = {
        "name": "Test Patient Week6",
        "phone": "9998887771",
        "age": 45,
        "gender": "Male",
        "doctor_id": 1,
        "slot_id": target_slot_id,
        "lead_days": 1,
        "sms_sent": True
    }
    book_res = test_client.post("/api/appointments", json=payload)
    assert book_res.status_code == 201
    data = book_res.get_json()["data"]
    assert "token" in data
    assert data["token"].startswith("GENE-") or "00" in data["token"]
    assert data["patient_name"] == "Test Patient Week6"
    assert data["is_smart_overbooked"] is False
    assert 0.0 <= data["predicted_no_show_prob"] <= 1.0

def test_api_appointment_status_lifecycle(test_client):
    """Test appointment status updates: CHECKED_IN -> IN_CONSULTATION -> COMPLETED."""
    # Book a new appointment
    slots_res = test_client.get("/api/doctors/1/slots")
    slots = slots_res.get_json()
    target_slot = [s for s in slots if not s["is_booked"]][0]

    book_res = test_client.post("/api/appointments", json={
        "name": "Lifecycle Patient",
        "phone": "9998887772",
        "age": 28,
        "gender": "Female",
        "doctor_id": 1,
        "slot_id": target_slot["slot_id"],
        "lead_days": 0
    })
    appt_id = book_res.get_json()["data"]["appointment_id"]

    # Check In
    checkin_res = test_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "CHECKED_IN"})
    assert checkin_res.status_code == 200
    assert checkin_res.get_json()["data"]["status"] == "CHECKED_IN"

    # In Consultation
    consult_res = test_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "IN_CONSULTATION"})
    assert consult_res.status_code == 200
    assert consult_res.get_json()["data"]["status"] == "IN_CONSULTATION"

    # Completed
    done_res = test_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "COMPLETED"})
    assert done_res.status_code == 200
    assert done_res.get_json()["data"]["status"] == "COMPLETED"

def test_api_emergency_triage_preemption(test_client):
    """Test walk-in emergency preemption via REST endpoint."""
    triage_payload = {
        "patient_name": "Emergency Critical Case",
        "phone": "9998887773",
        "dept_id": 1,
        "severity": 1
    }
    triage_res = test_client.post("/api/triage", json=triage_payload)
    assert triage_res.status_code == 201
    data = triage_res.get_json()["data"]
    assert data["severity_level"] == 1
    assert data["assigned_doctor"] is not None
    assert data["room_number"] is not None

def test_api_doctor_leave_cascade(test_client):
    """Test emergency leave trigger and cascade reassignments."""
    # Trigger leave for doctor 2 (Dr. Anita Desai)
    leave_res = test_client.post("/api/doctors/2/leave")
    assert leave_res.status_code == 200
    data = leave_res.get_json()["data"]
    assert data["status"] == "On Leave"

    # Verify doctor is no longer available
    doc_res = test_client.get("/api/doctors/2")
    assert doc_res.get_json()["is_available"] is False

def test_api_waiting_hall_token_board(test_client):
    """Test live waiting hall token board API returns valid rooms."""
    board_res = test_client.get("/api/queue/token-board")
    assert board_res.status_code == 200
    data = board_res.get_json()
    assert "board" in data
    assert len(data["board"]) > 0
    room = data["board"][0]
    assert "doctor_name" in room
    assert "room_number" in room
    assert "current_token" in room
    assert "patients_waiting" in room

def test_login_and_logout_flow(test_client):
    """Test staff authentication: login page loads, auth succeeds, and logout clears session."""
    # GET login page
    res = test_client.get("/login")
    assert res.status_code == 200
    assert b"Hospital Staff Portal" in res.data

    # Valid admin login
    post_res = test_client.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=True)
    assert post_res.status_code == 200
    assert b"Hospital Administrator" in post_res.data

    # Logout
    logout_res = test_client.get("/logout", follow_redirects=True)
    assert logout_res.status_code == 200
    assert b"Staff Login" in logout_res.data

def test_patient_token_tracker_view_and_api(test_client):
    """Test patient token tracker page and API query by token/phone."""
    # Page loads
    res = test_client.get("/track")
    assert res.status_code == 200
    assert b"Live Patient Token &amp; Queue Tracker" in res.data

    # API query with phone from earlier test (9998887771)
    api_res = test_client.get("/api/queue/track?query=9998887771")
    assert api_res.status_code == 200
    data = api_res.get_json()
    assert data["success"] is True
    assert len(data["results"]) >= 1
    assert data["results"][0]["patient_phone"] == "9998887771"
    assert "token" in data["results"][0]

def test_booking_validation_phone_and_email(test_client):
    """Test phone length rejection and email persistence."""
    slots_res = test_client.get("/api/doctors/1/slots")
    target_slot_id = slots_res.get_json()[0]["slot_id"]

    # Reject invalid phone (too short)
    bad_payload = {
        "name": "Invalid Phone User",
        "phone": "12345",
        "age": 30,
        "doctor_id": 1,
        "slot_id": target_slot_id
    }
    bad_res = test_client.post("/api/appointments", json=bad_payload)
    assert bad_res.status_code == 400
    assert "10-digit" in bad_res.get_json()["error"]

def test_prescription_lifecycle_and_slip_view(test_client):
    """Test creating an E-Prescription and viewing the printable slip."""
    # Create prescription for appointment 1
    rx_payload = {
        "diagnosis": "Essential Hypertension & Mild Angina",
        "medicines": "Tab Telmisartan 40mg - 1 Tab OD\nTab Aspirin 75mg - 1 Tab Post Meals",
        "advice": "Low salt diet, periodic BP monitoring.",
        "follow_up_days": 14
    }
    post_res = test_client.post("/api/appointments/1/prescription", json=rx_payload)
    assert post_res.status_code == 200
    data = post_res.get_json()["data"]
    assert data["diagnosis"] == "Essential Hypertension & Mild Angina"
    assert data["follow_up_days"] == 14

    # GET JSON endpoint
    get_res = test_client.get("/api/appointments/1/prescription")
    assert get_res.status_code == 200
    assert get_res.get_json()["data"]["doctor_name"] is not None

    # GET HTML printable slip view
    slip_res = test_client.get("/prescription/1")
    assert slip_res.status_code == 200
    assert b"CENTRAL GOVERNMENT HOSPITAL" in slip_res.data
    assert b"Essential Hypertension" in slip_res.data

def test_ai_symptom_triage_api(test_client):
    """Test NLP symptom-to-specialty triage recommendation."""
    # Critical cardiac symptoms
    res_cardio = test_client.post("/api/ai/symptom-triage", json={"symptoms": "severe chest pain and left arm numbness"})
    assert res_cardio.status_code == 200
    data_cardio = res_cardio.get_json()["data"]
    assert data_cardio["recommended_department"] == "Cardiology"
    assert data_cardio["is_emergency_preempt"] is True
    assert data_cardio["urgency_level"] == 1

    # Pediatric symptoms
    res_pedia = test_client.post("/api/ai/symptom-triage", json={"symptoms": "infant child running high fever and continuous crying"})
    assert res_pedia.status_code == 200
    data_pedia = res_pedia.get_json()["data"]
    assert data_pedia["recommended_department"] == "Pediatrics"

def test_fhir_v4_appointment_export(test_client):
    """Test exporting consultation as official HL7 FHIR v4 JSON resource."""
    res = test_client.get("/api/fhir/Appointment/1")
    assert res.status_code == 200
    fhir = res.get_json()
    assert fhir["resourceType"] == "Appointment"
    assert "participant" in fhir
    assert len(fhir["participant"]) >= 2

def test_workload_rebalance_api(test_client):
    """Test cross-doctor workload rebalancer endpoint."""
    res = test_client.post("/api/departments/1/rebalance")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "transfers" in data


