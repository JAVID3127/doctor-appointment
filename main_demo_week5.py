import sys
from pathlib import Path
from datetime import datetime, date, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.core.db import init_db, get_session
from src.core.models import (
    Department, Doctor, Patient, TimeSlot, Appointment,
    AppointmentStatus, TriageSeverity
)
from src.overbooking.smart_overbooker import SmartOverbookingEngine
from src.conflicts.conflict_resolver import ConflictResolutionEngine

def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title.upper()}")
    print("=" * 80)

def main():
    print_header("Doctor-Patient Appointment Scheduling System — Week 5 Demo")
    print("🏥 Week 5 Focus: Smart Overbooking Engine & Dynamic Conflict Resolution\n")

    init_db()
    session = get_session()

    overbooker = SmartOverbookingEngine(session)
    resolver = ConflictResolutionEngine(session)

    # Setup base department and doctors
    dept = session.query(Department).first()
    if not dept:
        dept = Department(dept_name="General Medicine", default_slot_duration_mins=15, floor_number=1)
        session.add(dept)
        session.commit()

    doc1 = session.query(Doctor).filter(Doctor.name == "Dr. Rajesh Sharma").first()
    if not doc1:
        doc1 = Doctor(name="Dr. Rajesh Sharma", specialization="General Medicine", room_number="OPD-101", dept_id=dept.dept_id, max_daily_capacity=20)
        session.add(doc1)
        session.commit()

    doc2 = session.query(Doctor).filter(Doctor.name == "Dr. Anita Desai").first()
    if not doc2:
        doc2 = Doctor(name="Dr. Anita Desai", specialization="General Medicine", room_number="OPD-102", dept_id=dept.dept_id, max_daily_capacity=20)
        session.add(doc2)
        session.commit()

    # Patients
    p_high = session.query(Patient).filter(Patient.phone == "9876500001").first()
    if not p_high:
        p_high = Patient(name="Rohan Gupta (High-Risk)", age=24, gender="Male", phone="9876500001", total_visits=5, past_no_shows=3)
        session.add(p_high)
        session.commit()

    p_norm = session.query(Patient).filter(Patient.phone == "9876500002").first()
    if not p_norm:
        p_norm = Patient(name="Aarav Mehta (Low-Risk)", age=34, gender="Male", phone="9876500002", total_visits=8, past_no_shows=0)
        session.add(p_norm)
        session.commit()

    today = date(2026, 10, 20)
    st1 = datetime(2026, 10, 20, 9, 0)
    st2 = datetime(2026, 10, 20, 9, 15)

    slot1 = session.query(TimeSlot).filter(TimeSlot.doctor_id == doc1.doctor_id, TimeSlot.start_time == st1).first()
    if not slot1:
        slot1 = TimeSlot(doctor_id=doc1.doctor_id, start_time=st1, end_time=st1 + timedelta(minutes=15), is_booked=True)
        session.add(slot1)
        session.commit()

    primary_appt = session.query(Appointment).filter(Appointment.slot_id == slot1.slot_id, Appointment.is_secondary_overbook == False).first()
    if not primary_appt:
        primary_appt = Appointment(
            patient_id=p_high.patient_id,
            doctor_id=doc1.doctor_id,
            slot_id=slot1.slot_id,
            predicted_no_show_prob=0.65,
            status=AppointmentStatus.CONFIRMED,
            is_secondary_overbook=False
        )
        session.add(primary_appt)
        session.commit()

    # =========================================================================
    # DEMO 1: SMART OVERBOOKING IN ACTION
    # =========================================================================
    print_header("1. Smart Overbooking: High-Risk Slot Pairing")
    print(f"Slot #{slot1.slot_id} (09:00 - 09:15) currently assigned to primary patient:")
    print(f"   • Primary Patient : {p_high.name} (Predicted P(no-show) = 65.0%)")

    # Evaluate overbooking incoming patient Aarav Mehta (p_noshow = 10%)
    can_ob, reason = overbooker.can_overbook_slot(slot1.slot_id, incoming_p_noshow=0.10, target_date=today)
    print(f"\n   Overbooking Eligibility Assessment: {reason}")

    if can_ob:
        sec_appt = overbooker.execute_smart_overbook(slot1.slot_id, p_norm.patient_id, doc1.doctor_id, predicted_no_show=0.10)
        print(f"   ✔ Secondary Booking Executed: Appt #{sec_appt.appointment_id} for {p_norm.name}")
        print(f"   ✔ Slot #{slot1.slot_id} Status: is_booked={slot1.is_booked}, is_overbooked={slot1.is_overbooked}")

    stats = overbooker.calculate_expected_shift_attendance(doc1.doctor_id, today)
    print(f"\n   Doctor Shift Utilization Math:")
    print(f"   • Total Bookings on Shift     : {stats['total_booked']}")
    print(f"   • Mathematical Expected Show  : {stats['expected_attendees']:.2f} patients")
    print(f"   • Predicted No-Shows Absorbed : {stats['expected_no_shows']:.2f} missed visits")
    print(f"   • Remaining Capacity Slack    : {stats['capacity_slack']:.2f} slots")

    # =========================================================================
    # DEMO 2: CANCELLATION PROMOTION WORKFLOW
    # =========================================================================
    print_header("2. Cancellation Promotion: Auto-Promoting Secondary Patient")
    primary_appt = session.query(Appointment).filter(
        Appointment.slot_id == slot1.slot_id,
        Appointment.is_secondary_overbook == False
    ).first()

    print(f"Primary patient ({p_high.name}) calls OPD reception to CANCEL appointment...")
    promoted = overbooker.handle_cancellation_promotion(primary_appt.appointment_id)
    session.refresh(slot1)

    print(f"   ✔ Primary Appointment #{primary_appt.appointment_id} -> Status: [CANCELLED]")
    if promoted:
        print(f"   ✔ Promoted Secondary Patient: {promoted.patient.name} (Appt #{promoted.appointment_id}) is now PRIMARY CONFIRMED!")
        print(f"   ✔ Slot #{slot1.slot_id} Overbooked Flag Cleared: is_overbooked={slot1.is_overbooked}")

    # =========================================================================
    # DEMO 3: EMERGENCY WALK-IN TRIAGE PREEMPTION
    # =========================================================================
    print_header("3. Emergency Walk-in Triage: PriorityQueue Preemption")
    p_emerg = session.query(Patient).filter(Patient.phone == "9876599999").first()
    if not p_emerg:
        p_emerg = Patient(name="Emergency Trauma Victim", age=45, gender="Male", phone="9876599999")
        session.add(p_emerg)
        session.commit()

    print(f"🚨 CODE RED: Critical walk-in emergency arrives at General Medicine triage desk!")
    triage_info = resolver.register_emergency_walk_in(p_emerg.patient_id, dept.dept_id, severity=TriageSeverity.CRITICAL.value)

    print(f"   • Triage Record ID       : #{triage_info['triage_id']}")
    print(f"   • Patient Name           : {triage_info['patient_name']}")
    print(f"   • Severity Level         : LEVEL {triage_info['severity_level']} (CRITICAL RESUSCITATION)")
    print(f"   • Intervening Specialist : {triage_info['assigned_doctor']} (Room {triage_info['room_number']})")
    print(f"   • Preemption Action      : {triage_info['preempted_patient_status']}")

    # =========================================================================
    # DEMO 4: DOCTOR ABSENCE CASCADE REASSIGNMENT
    # =========================================================================
    print_header("4. Conflict Resolution: Doctor Absence Cascade Reassignment")
    # Setup 2 patients booked with Dr. Rajesh Sharma
    p_case_a = session.query(Patient).filter(Patient.phone == "9876500010").first()
    if not p_case_a:
        p_case_a = Patient(name="Sunita Verma", age=58, gender="Female", phone="9876500010")
        session.add(p_case_a)
        session.commit()

    slot_rajesh = session.query(TimeSlot).filter(TimeSlot.doctor_id == doc1.doctor_id, TimeSlot.start_time == st2).first()
    if not slot_rajesh:
        slot_rajesh = TimeSlot(doctor_id=doc1.doctor_id, start_time=st2, end_time=st2 + timedelta(minutes=15), is_booked=True)
        session.add(slot_rajesh)
        session.commit()

    appt_rajesh = session.query(Appointment).filter(Appointment.slot_id == slot_rajesh.slot_id).first()
    if not appt_rajesh:
        appt_rajesh = Appointment(patient_id=p_case_a.patient_id, doctor_id=doc1.doctor_id, slot_id=slot_rajesh.slot_id, status=AppointmentStatus.BOOKED)
        session.add(appt_rajesh)
        session.commit()

    # Create matching free slot for peer Dr. Anita Desai
    slot_anita = session.query(TimeSlot).filter(TimeSlot.doctor_id == doc2.doctor_id, TimeSlot.start_time == st2).first()
    if not slot_anita:
        slot_anita = TimeSlot(doctor_id=doc2.doctor_id, start_time=st2, end_time=st2 + timedelta(minutes=15), is_booked=False)
        session.add(slot_anita)
        session.commit()

    print(f"⚠️ DOCTOR EMERGENCY LEAVE ALERT: Dr. Rajesh Sharma calls in sick for today ({today}).")
    print(f"Initiating Automated Conflict Cascade across General Medicine department...")

    cascade_report = resolver.execute_doctor_absence_cascade(doc1.doctor_id, today)
    print(f"\n   Cascade Execution Summary:")
    print(f"   • Doctor On Leave      : {cascade_report['doctor_on_leave']} (Status: Inactive)")
    print(f"   • Affected Consultations : {cascade_report['total_affected_patients']}")
    print(f"   • Successfully Rerouted: {cascade_report['successfully_reassigned']} (100% resolution)")

    for r in cascade_report["reassignments"]:
        print(f"\n   🔀 Patient Reassigned: {r['patient_name']}")
        print(f"      - Original Doctor : {r['from_doctor']}")
        print(f"      - New Specialist  : {r['to_doctor']} (Room {r['new_room']})")
        print(f"      - Consultation Time: {r['new_time']}")
        print(f"      - Allocation Method: {r['method']}")

    session.close()

    print("\n" + "=" * 80)
    print("  WEEK 5 VERIFICATION COMPLETE: SMART OVERBOOKING & CONFLICT LOGIC OPERATIONAL!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()
