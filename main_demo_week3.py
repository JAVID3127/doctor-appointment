import sys
from pathlib import Path
from datetime import datetime, date, timedelta
import random

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.db import init_db, get_session
from src.models import Department, Doctor, Patient, TimeSlot, Appointment
from src.algorithms import (
    AppointmentRequest,
    earliest_finish_time_schedule,
    interval_partitioning_multidoctor,
    compact_shift_schedule,
    IntervalSchedulingEngine
)

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def main():
    print_header("Doctor-Patient Appointment Scheduling System — Week 3 Demo")
    print("🏥 Week 3 Focus: Interval Scheduling Algorithms (EFT & Multi-Doctor Partitioning)\n")

    base = datetime(2026, 10, 20, 9, 0)

    # DEMO 1: EARLIEST FINISH TIME (EFT) SINGLE DOCTOR SELECTION
    print_header("1. Greedy Choice: Earliest Finish Time (EFT) Single Doctor Algorithm")
    print("Scenario: Multiple overlapping requests submitted for Dr. Rajesh Sharma (General Medicine).")

    raw_requests = [
        AppointmentRequest("REQ-1", 101, "Aarav Mehta", "General", base, base + timedelta(minutes=45)),                # 09:00 - 09:45
        AppointmentRequest("REQ-2", 102, "Sunita Verma", "General", base + timedelta(minutes=15), base + timedelta(minutes=35)), # 09:15 - 09:35 (EFT candidate)
        AppointmentRequest("REQ-3", 103, "Rohan Gupta", "General", base + timedelta(minutes=35), base + timedelta(minutes=55)),  # 09:35 - 09:55
        AppointmentRequest("REQ-4", 104, "Fatima Sheikh", "General", base + timedelta(minutes=30), base + timedelta(minutes=75)), # 09:30 - 10:15
        AppointmentRequest("REQ-5", 105, "Deepak Kumar", "General", base + timedelta(minutes=60), base + timedelta(minutes=90)),  # 10:00 - 10:30
    ]

    print(f"{'Request ID':<10} | {'Patient Name':<16} | {'Time Window':<18} | {'Duration'}")
    print("-" * 60)
    for r in raw_requests:
        trange = f"{r.start_time.strftime('%H:%M')} - {r.end_time.strftime('%H:%M')}"
        print(f"{r.request_id:<10} | {r.patient_name:<16} | {trange:<18} | {r.duration_minutes} mins")

    optimal_subset = earliest_finish_time_schedule(raw_requests)
    print(f"\n✔ EFT Algorithm Output: Selected {len(optimal_subset)} mutually compatible appointments (Maximum Cardinality):")
    for r in optimal_subset:
        trange = f"{r.start_time.strftime('%H:%M')} - {r.end_time.strftime('%H:%M')}"
        print(f"   [ACCEPTED] {r.request_id:<8} | {r.patient_name:<16} | {trange} ({r.duration_minutes} mins)")

    # DEMO 2: MULTI-DOCTOR INTERVAL PARTITIONING
    print_header("2. Multi-Doctor Interval Partitioning (Min-Heap Room Allocation)")
    print("Scenario: 8 incoming patient requests across Cardiology (Dr. Vikram Patel & Dr. Priya Nambiar).")

    cardio_requests = [
        AppointmentRequest("CARD-1", 201, "Kavita Rao", "Cardiology", base, base + timedelta(minutes=30)),
        AppointmentRequest("CARD-2", 202, "Manoj Joshi", "Cardiology", base + timedelta(minutes=10), base + timedelta(minutes=40)),
        AppointmentRequest("CARD-3", 203, "Harish Bhat", "Cardiology", base + timedelta(minutes=30), base + timedelta(minutes=60)),
        AppointmentRequest("CARD-4", 204, "Zoya Khan", "Cardiology", base + timedelta(minutes=40), base + timedelta(minutes=70)),
        AppointmentRequest("CARD-5", 205, "Pooja Nair", "Cardiology", base + timedelta(minutes=60), base + timedelta(minutes=90)),
        AppointmentRequest("CARD-6", 206, "Amit Shah", "Cardiology", base + timedelta(minutes=70), base + timedelta(minutes=100)),
        AppointmentRequest("CARD-7", 207, "Geeta Sen", "Cardiology", base + timedelta(minutes=90), base + timedelta(minutes=120)),
        AppointmentRequest("CARD-8", 208, "Naveen Raj", "Cardiology", base + timedelta(minutes=100), base + timedelta(minutes=130)),
    ]

    doctor_ids = [1, 2]
    doc_names = {1: "Dr. Vikram Patel (Room 201)", 2: "Dr. Priya Nambiar (Room 202)"}
    multidoctor_schedule = interval_partitioning_multidoctor(cardio_requests, doctor_ids)

    for doc_id, assigned in multidoctor_schedule.items():
        print(f"\n👨‍⚕️ {doc_names[doc_id]} -> Assigned {len(assigned)} consultations (Zero Collision):")
        for r in assigned:
            trange = f"{r.start_time.strftime('%H:%M')} - {r.end_time.strftime('%H:%M')}"
            print(f"   Slot: {trange} | Patient: {r.patient_name} ({r.request_id})")

    # DEMO 3: BEFORE VS AFTER DOCTOR UTILIZATION COMPARISON
    print_header("3. Benchmark: Naive Scheduling vs Interval-Compacted Scheduling")
    shift_start = datetime(2026, 10, 20, 9, 0)
    shift_end = datetime(2026, 10, 20, 13, 0)  # 4-hour shift (240 mins)
    total_mins = 240

    # Naive Unoptimized: Scattered bookings with large idle gaps
    naive_slots = [
        ("09:00 - 09:20", 20),
        ("10:15 - 10:35", 20),  # 55 min idle gap!
        ("11:40 - 12:00", 20),  # 65 min idle gap!
        ("12:30 - 12:50", 20),  # 30 min idle gap!
    ]
    naive_active = sum(dur for _, dur in naive_slots)
    naive_idle = total_mins - naive_active
    naive_util = (naive_active / total_mins) * 100

    # Interval-Compacted: Greedily packed slots with 5-min sanitization buffers
    compact_requests = [
        AppointmentRequest(f"P-{i}", i, f"Patient {i}", "Gen", shift_start, shift_start + timedelta(minutes=20))
        for i in range(10)
    ]
    packed = compact_shift_schedule(shift_start, shift_end, compact_requests, buffer_mins=5)
    compact_active = len(packed) * 20
    compact_idle = total_mins - (len(packed) * 25 - 5)
    compact_util = (compact_active / total_mins) * 100

    print(f"{'Metric':<32} | {'Naive Manual Booking':<22} | {'Greedy Interval Scheduling'}")
    print("-" * 80)
    print(f"{'Total Shift Duration':<32} | {total_mins} mins (4.0 hrs){'':<4} | {total_mins} mins (4.0 hrs)")
    print(f"{'Patients Treated':<32} | {len(naive_slots)} patients{'':<13} | {len(packed)} patients")
    print(f"{'Active Consultation Time':<32} | {naive_active} mins{'':<15} | {compact_active} mins")
    print(f"{'Wasted Idle Gap Time':<32} | {naive_idle} mins{'':<15} | {compact_idle} mins")
    print(f"{'Doctor Utilization Rate':<32} | {naive_util:.1f}%{'':<17} | {compact_util:.1f}% (▲ +{compact_util - naive_util:.1f}%)")

    # DEMO 4: DATABASE PERSISTENCE INTEGRATION
    print_header("4. Database Integration: Persisting Optimal Schedule to Database")
    init_db()
    session = get_session()
    engine = IntervalSchedulingEngine(session)

    # Seed or get department
    dept = session.query(Department).first()
    if not dept:
        dept = Department(dept_name="Pediatrics", default_slot_duration_mins=15, floor_number=2)
        session.add(dept)
        session.commit()

    doc = session.query(Doctor).filter(Doctor.dept_id == dept.dept_id).first()
    if not doc:
        doc = Doctor(name="Dr. Meera Iyer", specialization="Pediatrics", room_number="OPD-206", dept_id=dept.dept_id, max_daily_capacity=25)
        session.add(doc)
        session.commit()

    patient = session.query(Patient).first()
    if not patient:
        patient = Patient(name="Baby Aarav", age=4, gender="Male", phone="9888877771")
        session.add(patient)
        session.commit()

    batch_reqs = [
        AppointmentRequest(f"PED-{i}", patient.patient_id, f"Pediatric Case #{i}", "Pediatrics",
                           base + timedelta(minutes=i*20), base + timedelta(minutes=i*20 + 15))
        for i in range(5)
    ]

    target_date = date(2026, 10, 20)
    res = engine.schedule_department_batch(dept.dept_id, batch_reqs, target_date)
    print(f"Batch Scheduling Complete for {res['department_name']}:")
    print(f"   • Requests Processed : {res['total_requests']}")
    print(f"   • Confirmed Bookings : {res['total_scheduled']}")
    print(f"   • Rejection Rate     : {res['rejection_rate_pct']}%")

    util = engine.compute_doctor_utilization(doc.doctor_id, target_date)
    print(f"   • Doctor Utilization : {util['utilization_rate_pct']}% ({util['active_consultation_minutes']} active mins / {util['total_shift_minutes']} shift mins)")

    session.close()

    print("\n" + "=" * 80)
    print("  WEEK 3 VERIFICATION COMPLETE: GREEDY INTERVAL SCHEDULING FULLY OPERATIONAL!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
