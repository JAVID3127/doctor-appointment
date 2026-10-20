import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import random

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import init_db, get_session
from src.crud import (
    create_department, create_doctor, create_patient,
    create_time_slot, book_appointment, register_emergency_triage,
    create_historical_record, update_appointment_status
)
from src.models import AppointmentStatus, TriageSeverity

def seed_database():
    print("🏥 Initializing database schema...")
    init_db()
    session = get_session()

    print("🏢 Seeding Departments...")
    departments = [
        create_department(session, name="General Medicine", slot_duration=10, floor=1),
        create_department(session, name="Cardiology", slot_duration=20, floor=2),
        create_department(session, name="Orthopedics", slot_duration=15, floor=1),
        create_department(session, name="Pediatrics", slot_duration=15, floor=2),
        create_department(session, name="Dermatology", slot_duration=12, floor=3),
    ]

    print("👨‍⚕️ Seeding Doctors...")
    doctors = [
        create_doctor(session, name="Dr. Rajesh Sharma", specialization="General Medicine", room_number="OPD-101", dept_id=departments[0].dept_id, max_capacity=35),
        create_doctor(session, name="Dr. Anita Desai", specialization="General Medicine", room_number="OPD-102", dept_id=departments[0].dept_id, max_capacity=35),
        create_doctor(session, name="Dr. Vikram Patel", specialization="Cardiology", room_number="OPD-201", dept_id=departments[1].dept_id, max_capacity=20),
        create_doctor(session, name="Dr. Priya Nambiar", specialization="Cardiology", room_number="OPD-202", dept_id=departments[1].dept_id, max_capacity=20),
        create_doctor(session, name="Dr. Suresh Reddy", specialization="Orthopedics", room_number="OPD-105", dept_id=departments[2].dept_id, max_capacity=25),
        create_doctor(session, name="Dr. Meera Iyer", specialization="Pediatrics", room_number="OPD-206", dept_id=departments[3].dept_id, max_capacity=30),
        create_doctor(session, name="Dr. Kabir Sen", specialization="Dermatology", room_number="OPD-302", dept_id=departments[4].dept_id, max_capacity=25),
    ]

    print("🧑‍🦽 Seeding Patients...")
    patients_data = [
        ("Aarav Mehta", 34, "Male", "9876543210", 8, 1),
        ("Sunita Verma", 58, "Female", "9876543211", 12, 0),
        ("Rohan Gupta", 24, "Male", "9876543212", 4, 2),
        ("Fatima Sheikh", 42, "Female", "9876543213", 15, 3),
        ("Kavita Rao", 67, "Female", "9876543214", 20, 1),
        ("Deepak Kumar", 19, "Male", "9876543215", 2, 1),
        ("Pooja Nair", 31, "Female", "9876543216", 6, 0),
        ("Manoj Joshi", 50, "Male", "9876543217", 9, 4),
        ("Zoya Khan", 8, "Female", "9876543218", 5, 0),
        ("Harish Bhat", 72, "Male", "9876543219", 18, 2),
    ]

    patients = [
        create_patient(session, name=p[0], age=p[1], gender=p[2], phone=p[3], total_visits=p[4], past_no_shows=p[5])
        for p in patients_data
    ]

    print("⏰ Seeding Time Slots for today and tomorrow...")
    today = date.today()
    created_slots = []
    
    # Generate 4 slots for Dr. Rajesh Sharma and Dr. Vikram Patel for demonstration
    for doc in doctors[:2]:
        base_time = datetime(today.year, today.month, today.day, 9, 0)
        for i in range(6):
            st = base_time + timedelta(minutes=i * 15)
            et = st + timedelta(minutes=15)
            slot = create_time_slot(session, doctor_id=doc.doctor_id, start_time=st, end_time=et)
            created_slots.append(slot)

    print("📅 Booking Sample Appointments...")
    # Book first 3 slots
    a1 = book_appointment(session, patient_id=patients[0].patient_id, doctor_id=doctors[0].doctor_id, slot_id=created_slots[0].slot_id, predicted_no_show=0.12)
    update_appointment_status(session, a1.appointment_id, AppointmentStatus.COMPLETED)

    a2 = book_appointment(session, patient_id=patients[1].patient_id, doctor_id=doctors[0].doctor_id, slot_id=created_slots[1].slot_id, predicted_no_show=0.08)
    update_appointment_status(session, a2.appointment_id, AppointmentStatus.IN_CONSULTATION)

    a3 = book_appointment(session, patient_id=patients[2].patient_id, doctor_id=doctors[0].doctor_id, slot_id=created_slots[2].slot_id, predicted_no_show=0.65)
    update_appointment_status(session, a3.appointment_id, AppointmentStatus.CHECKED_IN)

    # Smart overbooking test on high-risk slot (slot 2 has p_noshow=0.65)
    a4_overbook = book_appointment(
        session,
        patient_id=patients[3].patient_id,
        doctor_id=doctors[0].doctor_id,
        slot_id=created_slots[2].slot_id,
        predicted_no_show=0.20,
        force_overbook=True
    )

    print("🚨 Seeding Emergency Walk-in Triage Record...")
    register_emergency_triage(
        session,
        patient_id=patients[4].patient_id,
        doctor_id=doctors[0].doctor_id,
        severity=TriageSeverity.CRITICAL.value,
        preempted_slot_id=created_slots[3].slot_id
    )

    print("📊 Seeding Historical Appointment Logs (for Week 4 ML Training)...")
    for pat in patients:
        for _ in range(5):
            lead = random.choice([0, 1, 3, 7, 14])
            dow = random.randint(0, 5)
            sms = random.choice([True, False])
            # Higher chance of no show if high past no shows and no SMS
            prob_miss = 0.6 if (pat.past_no_shows > 1 and not sms) else 0.15
            missed = random.random() < prob_miss
            create_historical_record(session, pat.patient_id, lead_days=lead, day_of_week=dow, sms_sent=sms, no_show_flag=missed)

    session.close()
    print("✅ Seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
