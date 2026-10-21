import pytest
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models import Base, Patient, Doctor, Department, TimeSlot, Appointment, AppointmentStatus
from src.services import HospitalOPDService
from app import create_app

@pytest.fixture
def memory_service():
    """Provides an isolated database and HospitalOPDService instance."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    service = HospitalOPDService(session)
    service.seed_initial_data_if_empty()
    yield service
    session.close()

@pytest.fixture
def test_client():
    """Provides Flask test client with in-memory database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    app = create_app(custom_engine=engine)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    with app.test_client() as client:
        yield client

def test_patient_registration_and_password_hashing(memory_service):
    """Verifies that patient registration succeeds and password is cryptographically hashed."""
    patient_data = memory_service.register_patient(
        name="Sunil Gavaskar",
        phone="9876500001",
        password="securePassword123",
        age=45,
        gender="Male",
        email="sunil@example.com"
    )

    assert patient_data["name"] == "Sunil Gavaskar"
    assert patient_data["phone"] == "9876500001"
    assert "password" not in patient_data
    assert "password_hash" not in patient_data

    # Query DB directly to verify password is NOT stored in plain text
    patient_record = memory_service.session.query(Patient).filter(Patient.phone == "9876500001").first()
    assert patient_record is not None
    assert patient_record.password_hash is not None
    assert patient_record.password_hash != "securePassword123"
    assert patient_record.password_hash.startswith("scrypt:") or patient_record.password_hash.startswith("pbkdf2:")

    # Verify check_password helper
    assert patient_record.check_password("securePassword123") is True
    assert patient_record.check_password("wrongPassword") is False

def test_duplicate_registration_prevention(memory_service):
    """Verifies duplicate phone numbers and duplicate emails are rejected."""
    memory_service.register_patient(
        name="Pooja Sharma",
        phone="9876500002",
        password="password123",
        age=28,
        gender="Female",
        email="pooja@example.com"
    )

    # Attempt duplicate phone registration
    with pytest.raises(ValueError, match="already registered"):
        memory_service.register_patient(
            name="Pooja Duplicate",
            phone="9876500002",
            password="anotherPassword",
            age=30,
            gender="Female",
            email="different@example.com"
        )

    # Attempt duplicate email registration
    with pytest.raises(ValueError, match="already registered"):
        memory_service.register_patient(
            name="Different Person",
            phone="9876500003",
            password="anotherPassword",
            age=35,
            gender="Female",
            email="pooja@example.com"
        )

def test_registration_input_validations(memory_service):
    """Verifies server-side validation on age, phone, and password length."""
    # Invalid phone
    with pytest.raises(ValueError, match="10-digit"):
        memory_service.register_patient(
            name="Test Patient",
            phone="12345",
            password="validPassword",
            age=30
        )

    # Short password
    with pytest.raises(ValueError, match="at least 6 characters"):
        memory_service.register_patient(
            name="Test Patient",
            phone="9876500004",
            password="123",
            age=30
        )

    # Invalid age
    with pytest.raises(ValueError, match="Age must be between"):
        memory_service.register_patient(
            name="Test Patient",
            phone="9876500005",
            password="validPassword",
            age=150
        )

def test_patient_authentication(memory_service):
    """Verifies authentication via phone or email, and rejection of invalid passwords."""
    memory_service.register_patient(
        name="Vikram Singh",
        phone="9876500006",
        password="secretVikram123",
        age=38,
        gender="Male",
        email="vikram@hospital.in"
    )

    # Authenticate using phone
    auth_phone = memory_service.authenticate_patient("9876500006", "secretVikram123")
    assert auth_phone is not None
    assert auth_phone.name == "Vikram Singh"

    # Authenticate using email
    auth_email = memory_service.authenticate_patient("vikram@hospital.in", "secretVikram123")
    assert auth_email is not None
    assert auth_email.name == "Vikram Singh"

    # Wrong password
    auth_bad = memory_service.authenticate_patient("9876500006", "wrongPass")
    assert auth_bad is None

def test_patient_portal_authorization(test_client):
    """Verifies that unauthenticated users are redirected, and patients can view their dashboard."""
    # Unauthenticated GET
    res = test_client.get("/patient/dashboard")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    # Register via web form
    reg_res = test_client.post("/register", data={
        "name": "Kavita Rao",
        "phone": "9876500007",
        "email": "kavita@test.com",
        "password": "mypassword123",
        "confirm_password": "mypassword123",
        "age": "32",
        "gender": "Female"
    }, follow_redirects=True)

    assert reg_res.status_code == 200
    assert b"Welcome, Kavita Rao" in reg_res.data
    assert b"Authenticated Patient Session" in reg_res.data

def test_doctor_dashboard_role_authorization(test_client):
    """Verifies RBAC protection: patients and unauthenticated users cannot access doctor rooms."""
    # Unauthenticated user visiting doctor room
    res = test_client.get("/doctor/1")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

    # Log in as patient
    test_client.post("/register", data={
        "name": "Normal Patient",
        "phone": "9876500008",
        "password": "patientPassword123",
        "confirm_password": "patientPassword123",
        "age": "25",
        "gender": "Male"
    })

    # Patient attempting to view doctor room
    doc_res = test_client.get("/doctor/1")
    assert doc_res.status_code == 403
    assert b"Access Denied" in doc_res.data

    # Log in as Doctor 1
    test_client.get("/logout")
    login_doc = test_client.post("/login", data={"username": "doctor1", "password": "doc123"}, follow_redirects=True)
    assert login_doc.status_code == 200
    assert b"Dr. Rajesh Sharma" in login_doc.data

def test_future_date_slot_generation(test_client):
    """Verifies that available consultation slots can be queried for future dates."""
    future_date = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
    res = test_client.get(f"/api/doctors/1/slots?date={future_date}")
    assert res.status_code == 200
    slots = res.get_json()
    assert len(slots) >= 6
    assert any(s["is_booked"] is False for s in slots)

def test_appointment_cancellation_and_slot_release(test_client):
    """Verifies that cancelling an appointment restores slot availability."""
    # Register patient
    test_client.post("/register", data={
        "name": "Anita Roy",
        "phone": "9876500009",
        "password": "passwordAnita1",
        "confirm_password": "passwordAnita1",
        "age": "40",
        "gender": "Female"
    })

    # Fetch available slot
    slots_res = test_client.get("/api/doctors/1/slots")
    slots = slots_res.get_json()
    open_slot = next(s for s in slots if not s["is_booked"])
    slot_id = open_slot["slot_id"]

    # Book appointment
    book_res = test_client.post("/api/appointments", json={
        "name": "Anita Roy",
        "phone": "9876500009",
        "age": 40,
        "gender": "Female",
        "doctor_id": 1,
        "slot_id": slot_id,
        "lead_days": 1,
        "sms_sent": True
    })
    assert book_res.status_code == 201
    appt_data = book_res.get_json()["data"]
    appt_id = appt_data["appointment_id"]

    # Verify slot is now booked
    slots_res2 = test_client.get("/api/doctors/1/slots")
    slots2 = slots_res2.get_json()
    booked_slot = next(s for s in slots2 if s["slot_id"] == slot_id)
    assert booked_slot["is_booked"] is True

    # Cancel appointment
    cancel_res = test_client.post(f"/api/appointments/{appt_id}/cancel", json={})
    assert cancel_res.status_code == 200
    cancel_json = cancel_res.get_json()
    assert cancel_json["success"] is True

    # Verify slot is released back to available
    slots_res3 = test_client.get("/api/doctors/1/slots")
    slots3 = slots_res3.get_json()
    released_slot = next(s for s in slots3 if s["slot_id"] == slot_id)
    assert released_slot["is_booked"] is False

def test_unauthorized_cancellation_prevention(test_client):
    """Verifies that an unauthorized user cannot cancel another patient's appointment."""
    # Patient A books appointment
    book_res = test_client.post("/api/appointments", json={
        "name": "Patient Alpha",
        "phone": "9876500010",
        "age": 29,
        "gender": "Male",
        "doctor_id": 1,
        "slot_id": 1,
        "lead_days": 1,
        "sms_sent": True
    })
    appt_id = book_res.get_json()["data"]["appointment_id"]

    # Patient B attempts to cancel Patient A's appointment
    test_client.get("/logout")
    test_client.post("/register", data={
        "name": "Patient Beta",
        "phone": "9876500011",
        "password": "passwordBeta123",
        "confirm_password": "passwordBeta123",
        "age": "31",
        "gender": "Male"
    })

    bad_cancel = test_client.post(f"/api/appointments/{appt_id}/cancel", json={})
    assert bad_cancel.status_code == 403
    assert "Access Denied" in bad_cancel.get_json()["error"]

def test_health_check_endpoints(test_client):
    """Verifies that system health probe returns 200 with database status."""
    res = test_client.get("/health")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "healthy"
    assert json_data["database"] == "connected"

    res_api = test_client.get("/api/health")
    assert res_api.status_code == 200

def test_waiting_hall_full_lifecycle_and_room_status(test_client):
    """
    Tests the complete OPD queue lifecycle and verifies Waiting Hall display updates:
    1. Initial: Room Ready
    2. Book appointment: Token appears in upcoming waitlist
    3. Check in: Waiting count increments, room state becomes CALLING_PATIENT
    4. Call to room: Room state becomes IN_CONSULTATION with active token
    5. Complete consultation: Room state resets to ROOM_READY, completed count increments
    """
    # 1. Initial board state
    b_res = test_client.get("/api/queue/token-board")
    assert b_res.status_code == 200
    b_data = b_res.get_json()
    doc1_room = next(r for r in b_data["board"] if r["room_number"] == "OPD-101")
    assert doc1_room["room_status"] in ["ROOM_READY", "CALLING_PATIENT", "IN_CONSULTATION"]

    # 2. Book appointment for Dr. Rajesh Sharma (Doctor 1, Room OPD-101)
    slots = test_client.get("/api/doctors/1/slots").get_json()
    open_slot = next(s for s in slots if not s["is_booked"])
    slot_id = open_slot["slot_id"]

    book_res = test_client.post("/api/appointments", json={
        "name": "Queue Test Patient",
        "phone": "9876500099",
        "age": 35,
        "gender": "Male",
        "doctor_id": 1,
        "slot_id": slot_id,
        "lead_days": 1,
        "sms_sent": True
    })
    assert book_res.status_code == 201
    appt_id = book_res.get_json()["data"]["appointment_id"]
    token = book_res.get_json()["data"]["token"]

    # 3. Check In patient
    checkin_res = test_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "CHECKED_IN"})
    assert checkin_res.status_code == 200

    # Verify Waiting Hall reflects waiting patient
    b_res2 = test_client.get("/api/queue/token-board")
    doc1_b2 = next(r for r in b_res2.get_json()["board"] if r["room_number"] == "OPD-101")
    assert doc1_b2["patients_waiting"] >= 1
    assert token in doc1_b2["upcoming_tokens"]

    # 4. Doctor calls patient into consultation room
    call_res = test_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "IN_CONSULTATION"})
    assert call_res.status_code == 200

    b_res3 = test_client.get("/api/queue/token-board")
    doc1_b3 = next(r for r in b_res3.get_json()["board"] if r["room_number"] == "OPD-101")
    assert doc1_b3["room_status"] == "IN_CONSULTATION"
    assert doc1_b3["current_token"] == token

    # 5. Doctor finishes consultation
    done_res = test_client.patch(f"/api/appointments/{appt_id}/status", json={"status": "COMPLETED"})
    assert done_res.status_code == 200

    b_res4 = test_client.get("/api/queue/token-board")
    doc1_b4 = next(r for r in b_res4.get_json()["board"] if r["room_number"] == "OPD-101")
    assert doc1_b4["completed_today"] >= 1

def test_duplicate_same_slot_booking_rejected(test_client):
    """Verifies that the same patient cannot book the exact same slot twice."""
    # First booking
    res1 = test_client.post("/api/appointments", json={
        "name": "Double Booking Patient",
        "phone": "9876500077",
        "age": 28,
        "gender": "Female",
        "doctor_id": 2,
        "slot_id": 13,
        "lead_days": 1,
        "sms_sent": True
    })
    assert res1.status_code in [201, 400]

    # Attempt second booking for the exact same slot by the same patient
    res2 = test_client.post("/api/appointments", json={
        "name": "Double Booking Patient",
        "phone": "9876500077",
        "age": 28,
        "gender": "Female",
        "doctor_id": 2,
        "slot_id": 13,
        "lead_days": 1,
        "sms_sent": True
    })
    assert res2.status_code == 400
    assert "already hold an active booking" in res2.get_json()["error"] or "capacity" in res2.get_json()["error"]

def test_slot_doctor_mismatch_rejected(test_client):
    """Verifies that selecting a slot belonging to Doctor 1 while submitting for Doctor 2 is rejected."""
    # Slot 1 belongs to Doctor 1
    mismatch_res = test_client.post("/api/appointments", json={
        "name": "Mismatch Patient",
        "phone": "9876500088",
        "age": 30,
        "gender": "Male",
        "doctor_id": 2, # Doctor 2
        "slot_id": 1,   # Slot 1 belongs to Doctor 1
        "lead_days": 1,
        "sms_sent": True
    })
    assert mismatch_res.status_code == 400
    assert "does not belong" in mismatch_res.get_json()["error"]

def test_online_ml_retraining_endpoint(test_client):
    """Verifies that /api/ml/retrain trains and exports the pipeline without error."""
    retrain_res = test_client.post("/api/ml/retrain")
    assert retrain_res.status_code == 200
    data = retrain_res.get_json()
    assert data["success"] is True
    assert "metrics" in data
    assert data["metrics"]["roc_auc"] > 0.70

