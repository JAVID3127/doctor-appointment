import sys
from pathlib import Path
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.db import get_session, init_db
from src.crud import (
    get_all_departments, get_all_doctors, get_all_patients,
    get_appointments_for_doctor, get_all_historical_records
)
from src.models import TimeSlot, Appointment, EmergencyTriage

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def main():
    print_header("Doctor-Patient Appointment Scheduling System — Week 1 Demo")
    print("🏥 Week 1 Deliverables: Foundation, OOP Entity Modeling & SQLite Database Schema\n")

    session = get_session()

    # 1. Departments
    departments = get_all_departments(session)
    print(f"🏢 Registered Hospital Departments ({len(departments)}):")
    print(f"{'ID':<4} | {'Department Name':<22} | {'Default Slot':<12} | {'Floor'}")
    print("-" * 55)
    for d in departments:
        print(f"{d.dept_id:<4} | {d.dept_name:<22} | {d.default_slot_duration_mins} mins{'':<5} | Floor {d.floor_number}")

    # 2. Doctors
    doctors = get_all_doctors(session)
    print_header(f"Registered OPD Doctors ({len(doctors)})")
    print(f"{'ID':<4} | {'Doctor Name':<22} | {'Specialization':<18} | {'Room':<8} | {'Daily Cap':<10} | {'Status'}")
    print("-" * 78)
    for doc in doctors:
        status = "Active" if doc.is_available else "On Leave"
        print(f"{doc.doctor_id:<4} | {doc.name:<22} | {doc.specialization:<18} | {doc.room_number:<8} | {doc.max_daily_capacity:<10} | {status}")

    # 3. Patients
    patients = get_all_patients(session)
    print_header(f"Sample Patients & Attendance History ({len(patients)})")
    print(f"{'ID':<4} | {'Patient Name':<18} | {'Age':<4} | {'Gender':<7} | {'Phone':<12} | {'Visits':<7} | {'No-Shows':<9} | {'No-Show Risk'}")
    print("-" * 80)
    for p in patients[:6]:
        risk = "HIGH" if p.no_show_ratio >= 0.4 else ("MEDIUM" if p.no_show_ratio >= 0.2 else "LOW")
        print(f"{p.patient_id:<4} | {p.name:<18} | {p.age:<4} | {p.gender:<7} | {p.phone:<12} | {p.total_visits:<7} | {p.past_no_shows:<9} | {p.no_show_ratio:.1%} ({risk})")

    # 4. Time Slots
    slots = session.query(TimeSlot).all()
    print_header(f"Doctor Time Slots ({len(slots)})")
    print(f"{'Slot ID':<8} | {'Doctor ID':<10} | {'Time Range':<18} | {'Duration':<10} | {'Booked?':<8} | {'Overbooked?'}")
    print("-" * 72)
    for s in slots:
        trange = f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}"
        print(f"{s.slot_id:<8} | {s.doctor_id:<10} | {trange:<18} | {s.duration_minutes} mins{'':<3} | {str(s.is_booked):<8} | {s.is_overbooked}")

    # 5. Booked Appointments
    appointments = session.query(Appointment).all()
    print_header(f"Booked Appointments & Status Lifecycles ({len(appointments)})")
    print(f"{'Appt ID':<8} | {'Patient':<16} | {'Doctor':<20} | {'Status':<16} | {'P(No-Show)':<10}")
    print("-" * 75)
    for a in appointments:
        print(f"{a.appointment_id:<8} | {a.patient.name:<16} | {a.doctor.name:<20} | {a.status.value:<16} | {a.predicted_no_show_prob:.2%}")

    # 6. Emergency Triage
    triages = session.query(EmergencyTriage).all()
    print_header(f"Emergency Walk-in Triage Queue ({len(triages)})")
    for t in triages:
        print(f"🚨 Triage ID #{t.triage_id} | Patient: {t.patient.name} | Assigned Doctor: {t.doctor.name} | Severity: LEVEL {t.severity_level} (Preempted Slot #{t.preempted_slot_id})")

    # 7. Historical Records for ML
    hist = get_all_historical_records(session)
    print_header(f"Historical Records for AI Training ({len(hist)} logged)")
    if hist:
        print(f"Sample Log: Patient #{hist[0].patient_id} booked with {hist[0].lead_days} days lead time, SMS sent: {hist[0].sms_sent}, Missed: {hist[0].no_show_flag}")
    else:
        print("ℹ️  Historical table empty (will be populated during OPD consultations or AI training).")

    session.close()

    print("\n" + "=" * 80)
    print("  WEEK 1 VERIFICATION COMPLETE: ALL 7 TABLES & OOP MODULES FUNCTIONING!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
