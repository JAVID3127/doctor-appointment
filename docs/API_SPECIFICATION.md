# Smart Hospital OPD System - REST API Specification

This document provides complete documentation for the REST API endpoints provided by the Week 6 Flask Web Application.

---

## 1. System Metrics & Feeds

### `GET /api/metrics`
Retrieves aggregated hospital outpatient metrics for executive monitoring.
- **Request:** None
- **Response `200 OK`:**
```json
{
  "active_doctors": 6,
  "completed_appointments": 14,
  "emergency_triages": 2,
  "smart_overbooked_appointments": 4,
  "total_appointments": 48,
  "total_doctors": 6,
  "total_patients": 42
}
```

### `GET /api/queue/token-board`
High-frequency polling feed designed for the Waiting Hall Digital Display.
- **Request:** None
- **Response `200 OK`:**
```json
{
  "timestamp": "Live",
  "board": [
    {
      "current_patient": "Aarav Mehta",
      "current_token": "GENE-001",
      "doctor_name": "Dr. Rajesh Sharma",
      "estimated_delay_mins": 30,
      "patients_waiting": 2,
      "room_number": "OPD-101",
      "specialization": "General Medicine"
    }
  ]
}
```

---

## 2. Departments & Doctor Information

### `GET /api/departments`
Lists all medical departments in the hospital.
- **Response `200 OK`:** Array of department objects containing `dept_id`, `dept_name`, `default_slot_duration_mins`, `floor_number`, and `doctor_count`.

### `GET /api/doctors`
Returns list of doctors. Optional query filter: `?dept_id=1`.
- **Response `200 OK`:** Array of doctor objects containing `doctor_id`, `name`, `specialization`, `room_number`, `max_daily_capacity`, and `is_available`.

### `GET /api/doctors/{doctor_id}/slots`
Returns available consultation time slots for a specified doctor.
- **Response `200 OK`:**
```json
[
  {
    "slot_id": 1,
    "doctor_id": 1,
    "start_time": "09:00",
    "end_time": "09:15",
    "duration_minutes": 15,
    "is_booked": false,
    "is_overbooked": false
  }
]
```

---

## 3. Outpatient Appointment Management

### `POST /api/appointments`
Registers an appointment. Automatically assesses ML no-show risk, evaluates smart overbooking thresholds ($P(\text{No-Show}) \ge 0.50$), and issues a departmental token.
- **Request Body:**
```json
{
  "name": "Suresh Raina",
  "phone": "9876543299",
  "age": 36,
  "gender": "Male",
  "doctor_id": 1,
  "slot_id": 4,
  "lead_days": 2,
  "sms_sent": true
}
```
- **Response `201 Created`:**
```json
{
  "success": true,
  "data": {
    "appointment_id": 15,
    "token": "GENE-015",
    "patient_name": "Suresh Raina",
    "doctor_name": "Dr. Rajesh Sharma",
    "specialization": "General Medicine",
    "room_number": "OPD-101",
    "slot_time": "09:45 - 10:00",
    "predicted_no_show_prob": 0.18,
    "is_smart_overbooked": false,
    "status": "CONFIRMED"
  }
}
```

### `PATCH /api/appointments/{appointment_id}/status`
Transitions an appointment across the clinical consultation lifecycle.
- **Valid Status Values:** `BOOKED`, `CONFIRMED`, `CHECKED_IN`, `IN_CONSULTATION`, `COMPLETED`, `CANCELLED`, `NO_SHOW`.
- **Request Body:** `{"status": "IN_CONSULTATION"}`
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "appointment_id": 15,
    "status": "IN_CONSULTATION"
  }
}
```
*Note: If status is set to `CANCELLED` on a slot that has an overbooked secondary patient, the secondary appointment is automatically promoted to primary status.*

---

## 4. Emergency Triage & Doctor Absence

### `POST /api/triage`
Registers walk-in acute emergency and preempts doctor's consultation room based on Emergency Severity Index (ESI 1-4).
- **Request Body:**
```json
{
  "patient_name": "Kavita Rao",
  "phone": "9812345678",
  "dept_id": 2,
  "severity": 1
}
```
- **Response `201 Created`:**
```json
{
  "success": true,
  "data": {
    "triage_id": 3,
    "patient_name": "Kavita Rao",
    "severity_level": 1,
    "assigned_doctor": "Dr. Vikram Patel",
    "room_number": "OPD-201",
    "arrival_time": "10:14:22"
  }
}
```

### `POST /api/doctors/{doctor_id}/leave`
Triggers sudden doctor absence and reassigns all remaining consultations to available peers in the same specialty.
- **Response `200 OK`:**
```json
{
  "success": true,
  "data": {
    "doctor_name": "Dr. Anita Desai",
    "status": "On Leave",
    "reassigned_count": 8,
    "reassignments": [
      {
        "patient": "Aarav Mehta",
        "new_doctor": "Dr. Rajesh Sharma",
        "new_room": "OPD-101"
      }
    ]
  }
}
```
