import sys
from pathlib import Path
from datetime import datetime, date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.db import init_db, get_session
from src.state_machine import AppointmentStateMachine, AppointmentState, InvalidStateTransitionError
from src.managers import (
    DepartmentManager, DoctorManager, PatientManager,
    SlotManager, AppointmentManager, QueueManager
)
from src.models import AppointmentStatus

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def main():
    print_header("Doctor-Patient Appointment Scheduling System — Week 2 Demo")
    print("🏥 Week 2 Focus: Pure OOP Domain Services, State Machine & Queue Management\n")

    init_db()
    session = get_session()

    dept_mgr = DepartmentManager(session)
    doc_mgr = DoctorManager(session)
    pat_mgr = PatientManager(session)
    slot_mgr = SlotManager(session)
    appt_mgr = AppointmentManager(session)
    queue_mgr = QueueManager(session)

    # 1. Register Departments via DepartmentManager
    print("🏢 1. DepartmentManager: Registering Clinical Departments...")
    cardio = dept_mgr.register_department("Cardiology", slot_duration_mins=20, floor_number=2)
    gen_med = dept_mgr.register_department("General Medicine", slot_duration_mins=15, floor_number=1)
    ortho = dept_mgr.register_department("Orthopedics", slot_duration_mins=15, floor_number=1)
    print(f"   Registered {len(dept_mgr.get_all_departments())} departments successfully.")

    # 2. Register Doctors via DoctorManager
    print("\n👨‍⚕️ 2. DoctorManager: Registering OPD Specialists...")
    doc1 = doc_mgr.register_doctor("Dr. Vikram Patel", "Cardiology", "OPD-201", cardio.dept_id, max_capacity=20)
    doc2 = doc_mgr.register_doctor("Dr. Rajesh Sharma", "General Medicine", "OPD-101", gen_med.dept_id, max_capacity=30)
    print(f"   Doctor Registered: {doc1.name} (Room {doc1.room_number}) | Quota: {doc1.max_daily_capacity} patients")
    print(f"   Doctor Registered: {doc2.name} (Room {doc2.room_number}) | Quota: {doc2.max_daily_capacity} patients")

    # 3. Register Patients & Calculate Risk Profiles via PatientManager
    print_header("PatientManager: Risk Categorization & Attendance History")
    pat_data = [
        ("Aarav Mehta", 34, "Male", "9876540001", 10, 1),
        ("Rohan Gupta", 24, "Male", "9876540002", 5, 3),   # High no-show risk (60%)
        ("Sunita Verma", 58, "Female", "9876540003", 12, 0),
        ("Fatima Sheikh", 42, "Female", "9876540004", 8, 2),
    ]
    registered_patients = []
    print(f"{'Patient Name':<18} | {'Total Visits':<12} | {'No-Shows':<10} | {'No-Show Ratio':<15} | {'Risk Category'}")
    print("-" * 75)
    for name, age, gender, phone, visits, noshows in pat_data:
        p = pat_mgr.register_patient(name, age, gender, phone, visits, noshows)
        registered_patients.append(p)
        prof = pat_mgr.get_risk_profile(p.patient_id)
        print(f"{prof['name']:<18} | {prof['total_visits']:<12} | {prof['past_no_shows']:<10} | {prof['no_show_ratio']:<15.1%} | {prof['risk_category']}")

    # 4. Generate Shift Intervals via SlotManager
    print_header("SlotManager: Discrete Interval Partitioning (09:00 - 10:20)")
    today = date.today()
    slots_doc1 = slot_mgr.generate_shift_intervals(doc1.doctor_id, today, start_hour=9, end_hour=11, interval_mins=20)
    print(f"Generated {len(slots_doc1)} non-overlapping 20-min consultation intervals for {doc1.name}:")
    for s in slots_doc1[:4]:
        print(f"   Slot #{s.slot_id}: {s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')} ({s.duration_minutes} mins)")

    # 5. Book Appointments and Run State Machine Lifecycle
    print_header("AppointmentManager & StateMachine: Lifecycle Transitions")
    appt1 = appt_mgr.book_appointment(registered_patients[0].patient_id, doc1.doctor_id, slots_doc1[0].slot_id)
    appt2 = appt_mgr.book_appointment(registered_patients[1].patient_id, doc1.doctor_id, slots_doc1[1].slot_id, predicted_no_show=0.60)
    appt3 = appt_mgr.book_appointment(registered_patients[2].patient_id, doc1.doctor_id, slots_doc1[2].slot_id)

    print(f"Appt #{appt1.appointment_id} for {registered_patients[0].name} initialized in state: [{appt1.status.value}]")

    # Legal transitions: BOOKED -> CONFIRMED -> CHECKED_IN -> IN_CONSULTATION -> COMPLETED
    appt_mgr.confirm_appointment(appt1.appointment_id)
    print(f" -> Transitioned to: [{appt1.status.value}]")

    appt_mgr.check_in_patient(appt1.appointment_id)
    print(f" -> Transitioned to: [{appt1.status.value}] (Patient arrived at OPD)")

    appt_mgr.start_consultation(appt1.appointment_id)
    print(f" -> Transitioned to: [{appt1.status.value}] (Doctor examining patient)")

    # Intercept illegal state transition attempt
    print("\n   Testing State Machine Enforcement: Attempting illegal jump [IN_CONSULTATION -> BOOKED]...")
    try:
        AppointmentStateMachine.validate_transition(AppointmentState.IN_CONSULTATION, AppointmentState.BOOKED)
    except InvalidStateTransitionError as e:
        print(f"   🛡️ BLOCKED ILLEGAL TRANSITION: {e}")

    appt_mgr.complete_consultation(appt1.appointment_id)
    print(f" -> Final State: [{appt1.status.value}] (Consultation finished)")

    # Check-in patient 2 and patient 3
    appt_mgr.confirm_appointment(appt2.appointment_id)
    appt_mgr.check_in_patient(appt2.appointment_id)
    appt_mgr.start_consultation(appt2.appointment_id)

    appt_mgr.confirm_appointment(appt3.appointment_id)
    appt_mgr.check_in_patient(appt3.appointment_id)

    # 6. Live Hospital Queue & Token Board via QueueManager
    print_header("QueueManager: Real-Time OPD Token Board & Wait Times")
    board = queue_mgr.get_hospital_token_board()
    print(f"{'Doctor Name':<20} | {'Room':<8} | {'Current Token in Room':<24} | {'Waiting':<8} | {'Estimated Delay'}")
    print("-" * 80)
    for b in board:
        print(f"{b['doctor_name']:<20} | {b['room_number']:<8} | {b['current_token']:<24} | {b['patients_waiting']:<8} | {b['estimated_delay_mins']} mins")

    print("\nDoctor's Detailed Queue View:")
    doc1_queue = queue_mgr.get_doctor_active_queue(doc1.doctor_id)
    for q in doc1_queue:
        print(f"   Token: {q['token']} | Patient: {q['patient_name']:<14} | Room: {q['room_number']} | Wait: {q['estimated_wait_minutes']} mins | {q['status_label']}")

    # 7. Rescheduling Demonstration
    print_header("AppointmentManager: Rescheduling Demonstration")
    free_slot = slot_mgr.get_earliest_free_slot(doc1.doctor_id, today)
    print(f"Moving Patient 3 (Appt #{appt3.appointment_id}) to new slot #{free_slot.slot_id} ({free_slot.start_time.strftime('%H:%M')})...")
    appt_mgr.reschedule_appointment(appt3.appointment_id, free_slot.slot_id)
    print(f"Rescheduled Successfully! New Slot ID: #{appt3.slot_id} | Status: [{appt3.status.value}]")

    session.close()
    print("\n" + "=" * 80)
    print("  WEEK 2 VERIFICATION COMPLETE: ALL OOP MANAGERS & STATE MACHINES OPERATIONAL!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
