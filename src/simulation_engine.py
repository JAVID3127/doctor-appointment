import random
import math
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SimulatedPatient:
    patient_id: int
    name: str
    age: int
    gender: str
    total_past_visits: int
    past_no_shows: int
    lead_days: int
    sms_reminder: bool
    is_emergency: bool = False
    esi_severity: int = 4  # 1 (critical) to 4 (routine)
    slot_id: int = 0
    assigned_doctor_id: int = 0
    scheduled_start: float = 0.0  # minutes from 09:00
    actual_arrival: float = 0.0
    consultation_duration: float = 15.0
    will_show: bool = True
    is_secondary_overbook: bool = False
    predicted_no_show_prob: float = 0.0

@dataclass
class SimulationDayResult:
    day_index: int
    policy_name: str
    total_booked: int
    total_attended: int
    total_no_shows: int
    total_emergencies: int
    doctor_consultation_minutes: float
    doctor_idle_minutes: float
    doctor_overtime_minutes: float
    patient_wait_times: List[float] = field(default_factory=list)
    emergency_wait_times: List[float] = field(default_factory=list)

    @property
    def doctor_utilization_pct(self) -> float:
        total_time = self.doctor_consultation_minutes + self.doctor_idle_minutes
        if total_time == 0:
            return 0.0
        return round((self.doctor_consultation_minutes / total_time) * 100.0, 2)

    @property
    def avg_patient_wait_minutes(self) -> float:
        if not self.patient_wait_times:
            return 0.0
        return round(float(np.mean(self.patient_wait_times)), 2)

    @property
    def max_patient_wait_minutes(self) -> float:
        if not self.patient_wait_times:
            return 0.0
        return round(float(np.max(self.patient_wait_times)), 2)

    @property
    def avg_emergency_wait_minutes(self) -> float:
        if not self.emergency_wait_times:
            return 0.0
        return round(float(np.mean(self.emergency_wait_times)), 2)

class MonteCarloOPDSimulator:
    """
    Monte Carlo OPD Simulation Engine that replicates patient arrivals,
    service times, cancellations, and clinical workflows across multiple policies.
    """

    def __init__(
        self,
        num_doctors: int = 4,
        clinic_hours: float = 7.0,  # 09:00 to 16:00 (420 minutes)
        slot_duration_mins: float = 15.0,
        random_seed: int = 42
    ):
        self.num_doctors = num_doctors
        self.clinic_hours = clinic_hours
        self.clinic_duration_mins = clinic_hours * 60.0  # 420 mins
        self.slot_duration_mins = slot_duration_mins
        self.slots_per_doctor = int(self.clinic_duration_mins // slot_duration_mins)  # 28 slots
        self.random_seed = random_seed
        self.rng = np.random.default_rng(random_seed)

    def generate_day_patients(self, day_seed: int) -> List[SimulatedPatient]:
        """Generates realistic synthetic patient cohort for a single OPD operational day."""
        local_rng = np.random.default_rng(day_seed)
        patients = []
        patient_counter = 1

        total_base_slots = self.num_doctors * self.slots_per_doctor  # 4 * 28 = 112 appointments

        first_names = ["Aarav", "Sunita", "Rohan", "Priya", "Vikram", "Meera", "Anand", "Deepa", "Rahul", "Kavita", "Sanjay", "Neha"]
        last_names = ["Sharma", "Verma", "Patel", "Reddy", "Iyer", "Nair", "Gupta", "Singh", "Joshi", "Chopra"]

        for doc_id in range(1, self.num_doctors + 1):
            for slot_idx in range(self.slots_per_doctor):
                sched_start = slot_idx * self.slot_duration_mins
                age = int(local_rng.integers(18, 75))
                gender = "Female" if local_rng.random() < 0.52 else "Male"
                past_visits = int(local_rng.geometric(p=0.25)) - 1
                past_noshows = int(local_rng.binomial(past_visits, 0.20)) if past_visits > 0 else 0
                ratio = past_noshows / past_visits if past_visits > 0 else 0.0

                lead_days = int(local_rng.choice([0, 1, 2, 3, 5, 7, 10, 14], p=[0.15, 0.25, 0.20, 0.15, 0.10, 0.08, 0.05, 0.02]))
                sms = bool(local_rng.random() < 0.80)

                # ML logistic probability model
                log_odds = -1.8 + (0.14 * lead_days) + (4.0 * ratio) - (1.4 if sms else 0.0) - (0.02 * (age - 40))
                if lead_days == 0:
                    log_odds -= 3.0
                p_noshow = 1.0 / (1.0 + math.exp(-log_odds))
                p_noshow = float(round(p_noshow, 3))

                # Realized attendance
                will_show = bool(local_rng.random() >= p_noshow)

                # Consultation duration: log-normal distribution around 14.5 mins, std 4 mins
                # ln(14.5) ~ 2.67
                duration = float(np.clip(local_rng.lognormal(mean=2.65, sigma=0.28), 6.0, 35.0))

                # Arrival variation: patients arrive around scheduled start (-10 to +15 mins)
                arrival_jitter = float(local_rng.normal(loc=-2.0, scale=6.0))
                actual_arrival = max(0.0, sched_start + arrival_jitter)

                p = SimulatedPatient(
                    patient_id=patient_counter,
                    name=f"{local_rng.choice(first_names)} {local_rng.choice(last_names)}",
                    age=age,
                    gender=gender,
                    total_past_visits=past_visits,
                    past_no_shows=past_noshows,
                    lead_days=lead_days,
                    sms_reminder=sms,
                    slot_id=slot_idx,
                    assigned_doctor_id=doc_id,
                    scheduled_start=sched_start,
                    actual_arrival=actual_arrival,
                    consultation_duration=duration,
                    will_show=will_show,
                    is_secondary_overbook=False,
                    predicted_no_show_prob=p_noshow
                )
                patients.append(p)
                patient_counter += 1

        # Generate walk-in emergencies (Poisson distribution ~ 4 to 8 per day)
        num_emergencies = int(local_rng.poisson(lam=5.0))
        for _ in range(num_emergencies):
            arr_time = float(local_rng.uniform(15.0, self.clinic_duration_mins - 30.0))
            severity = int(local_rng.choice([1, 2, 3], p=[0.25, 0.45, 0.30]))
            dur = float(local_rng.uniform(12.0, 30.0)) if severity == 1 else float(local_rng.uniform(10.0, 20.0))
            assigned_doc = int(local_rng.integers(1, self.num_doctors + 1))

            p = SimulatedPatient(
                patient_id=patient_counter,
                name=f"Emergency Patient #{patient_counter}",
                age=int(local_rng.integers(20, 80)),
                gender="Other",
                total_past_visits=0,
                past_no_shows=0,
                lead_days=0,
                sms_reminder=False,
                is_emergency=True,
                esi_severity=severity,
                slot_id=-1,
                assigned_doctor_id=assigned_doc,
                scheduled_start=arr_time,
                actual_arrival=arr_time,
                consultation_duration=dur,
                will_show=True,
                is_secondary_overbook=False,
                predicted_no_show_prob=0.0
            )
            patients.append(p)
            patient_counter += 1

        return patients

    # =========================================================================
    # Policy A: Baseline 1 (Fixed Schedule, No Overbooking, FIFO Walk-in)
    # =========================================================================
    def run_policy_baseline_fixed(self, day_seed: int) -> SimulationDayResult:
        patients = self.generate_day_patients(day_seed)
        
        # Doctor state: current time available for each doctor
        doctor_time = {d: 0.0 for d in range(1, self.num_doctors + 1)}
        doctor_consult = {d: 0.0 for d in range(1, self.num_doctors + 1)}
        doctor_idle = {d: 0.0 for d in range(1, self.num_doctors + 1)}
        patient_waits = []
        emergency_waits = []

        total_booked = 0
        total_attended = 0
        total_noshows = 0
        total_emergencies = 0

        # Sort all patients by scheduled/arrival time
        scheduled_patients = sorted(
            [p for p in patients if not p.is_emergency],
            key=lambda x: (x.assigned_doctor_id, x.scheduled_start)
        )
        emergency_patients = sorted(
            [p for p in patients if p.is_emergency],
            key=lambda x: x.actual_arrival
        )

        for p in scheduled_patients:
            total_booked += 1
            doc = p.assigned_doctor_id
            sched = p.scheduled_start

            # If doctor is free before scheduled slot, doctor is idle waiting
            if doctor_time[doc] < sched:
                doctor_idle[doc] += (sched - doctor_time[doc])
                doctor_time[doc] = sched

            if not p.will_show:
                total_noshows += 1
                # In traditional fixed booking, doctor waits out the 15-minute slot!
                doctor_idle[doc] += self.slot_duration_mins
                doctor_time[doc] += self.slot_duration_mins
                continue

            total_attended += 1
            # Patient arrives at actual_arrival
            arrival = p.actual_arrival
            start_service = max(arrival, doctor_time[doc], sched)
            wait = start_service - arrival
            patient_waits.append(max(0.0, wait))

            doctor_consult[doc] += p.consultation_duration
            doctor_time[doc] = start_service + p.consultation_duration

        # In baseline, emergencies wait in FIFO order until a doctor completes regular appointments
        for ep in emergency_patients:
            total_emergencies += 1
            doc = ep.assigned_doctor_id
            arrival = ep.actual_arrival
            # Wait until doctor is next free
            start_service = max(arrival, doctor_time[doc])
            wait = start_service - arrival
            emergency_waits.append(max(0.0, wait))
            doctor_consult[doc] += ep.consultation_duration
            doctor_time[doc] = start_service + ep.consultation_duration

        total_overtime = sum(max(0.0, doctor_time[d] - self.clinic_duration_mins) for d in range(1, self.num_doctors + 1))

        return SimulationDayResult(
            day_index=day_seed,
            policy_name="Traditional Fixed (No Overbooking)",
            total_booked=total_booked,
            total_attended=total_attended,
            total_no_shows=total_noshows,
            total_emergencies=total_emergencies,
            doctor_consultation_minutes=sum(doctor_consult.values()),
            doctor_idle_minutes=sum(doctor_idle.values()),
            doctor_overtime_minutes=total_overtime,
            patient_wait_times=patient_waits,
            emergency_wait_times=emergency_waits
        )

    # =========================================================================
    # Policy B: Baseline 2 (Naive Static Overbooking: +25% Flat)
    # =========================================================================
    def run_policy_baseline_naive_overbooking(self, day_seed: int) -> SimulationDayResult:
        patients = self.generate_day_patients(day_seed)
        local_rng = np.random.default_rng(day_seed + 1000)

        # Naively add a second patient to every 4th slot (+25% overbooking) without checking no-show risk
        overbooked_patients = []
        p_id = 5000
        for doc_id in range(1, self.num_doctors + 1):
            for slot_idx in range(0, self.slots_per_doctor, 4):
                sched_start = slot_idx * self.slot_duration_mins
                will_show = bool(local_rng.random() >= 0.25)  # generic 25% no-show
                duration = float(np.clip(local_rng.lognormal(mean=2.65, sigma=0.28), 6.0, 35.0))
                arr = max(0.0, sched_start + float(local_rng.normal(-1.0, 5.0)))

                overbooked_patients.append(SimulatedPatient(
                    patient_id=p_id,
                    name=f"Naive Overbooked #{p_id}",
                    age=40,
                    gender="Male",
                    total_past_visits=2,
                    past_no_shows=0,
                    lead_days=3,
                    sms_reminder=True,
                    slot_id=slot_idx,
                    assigned_doctor_id=doc_id,
                    scheduled_start=sched_start,
                    actual_arrival=arr,
                    consultation_duration=duration,
                    will_show=will_show,
                    is_secondary_overbook=True
                ))
                p_id += 1

        all_scheduled = sorted(
            [p for p in patients if not p.is_emergency] + overbooked_patients,
            key=lambda x: (x.assigned_doctor_id, x.scheduled_start, not x.is_secondary_overbook)
        )
        emergencies = sorted([p for p in patients if p.is_emergency], key=lambda x: x.actual_arrival)

        doctor_time = {d: 0.0 for d in range(1, self.num_doctors + 1)}
        doctor_consult = {d: 0.0 for d in range(1, self.num_doctors + 1)}
        doctor_idle = {d: 0.0 for d in range(1, self.num_doctors + 1)}
        patient_waits = []
        emergency_waits = []

        total_booked = len(all_scheduled)
        total_attended = sum(1 for p in all_scheduled if p.will_show)
        total_noshows = total_booked - total_attended

        for p in all_scheduled:
            doc = p.assigned_doctor_id
            sched = p.scheduled_start

            if doctor_time[doc] < sched:
                doctor_idle[doc] += (sched - doctor_time[doc])
                doctor_time[doc] = sched

            if not p.will_show:
                continue

            arrival = p.actual_arrival
            start_service = max(arrival, doctor_time[doc])
            wait = start_service - arrival
            patient_waits.append(max(0.0, wait))

            doctor_consult[doc] += p.consultation_duration
            doctor_time[doc] = start_service + p.consultation_duration

        for ep in emergencies:
            doc = ep.assigned_doctor_id
            arrival = ep.actual_arrival
            start_service = max(arrival, doctor_time[doc])
            wait = start_service - arrival
            emergency_waits.append(max(0.0, wait))
            doctor_consult[doc] += ep.consultation_duration
            doctor_time[doc] = start_service + ep.consultation_duration

        total_overtime = sum(max(0.0, doctor_time[d] - self.clinic_duration_mins) for d in range(1, self.num_doctors + 1))

        return SimulationDayResult(
            day_index=day_seed,
            policy_name="Naive Static Overbooking (+25%)",
            total_booked=total_booked,
            total_attended=total_attended,
            total_no_shows=total_noshows,
            total_emergencies=len(emergencies),
            doctor_consultation_minutes=sum(doctor_consult.values()),
            doctor_idle_minutes=sum(doctor_idle.values()),
            doctor_overtime_minutes=total_overtime,
            patient_wait_times=patient_waits,
            emergency_wait_times=emergency_waits
        )

    # =========================================================================
    # Policy C: Proposed System (Smart OPD: ML Overbooking + ESI Preemption)
    # =========================================================================
    def run_policy_proposed_smart_opd(self, day_seed: int) -> SimulationDayResult:
        patients = self.generate_day_patients(day_seed)
        local_rng = np.random.default_rng(day_seed + 2000)

        # Smart Overbooking: Only add secondary patient IF primary slot has predicted no-show risk >= 0.50
        smart_overbooked = []
        p_id = 9000
        for p in patients:
            if not p.is_emergency and p.predicted_no_show_prob >= 0.50:
                # Add secondary patient with low no-show probability (e.g. lead_days=0 walk-in or confirmed)
                sec_duration = float(np.clip(local_rng.lognormal(mean=2.65, sigma=0.28), 6.0, 35.0))
                sec_arr = max(0.0, p.scheduled_start + float(local_rng.normal(-1.0, 4.0)))
                sec_p = SimulatedPatient(
                    patient_id=p_id,
                    name=f"Smart Overbooked #{p_id}",
                    age=35,
                    gender="Female",
                    total_past_visits=4,
                    past_no_shows=0,
                    lead_days=0,
                    sms_reminder=True,
                    slot_id=p.slot_id,
                    assigned_doctor_id=p.assigned_doctor_id,
                    scheduled_start=p.scheduled_start,
                    actual_arrival=sec_arr,
                    consultation_duration=sec_duration,
                    will_show=True,  # reliable show
                    is_secondary_overbook=True,
                    predicted_no_show_prob=0.08
                )
                smart_overbooked.append(sec_p)
                p_id += 1

        # Check for random doctor leave (3% chance)
        doctor_on_leave = None
        if local_rng.random() < 0.03:
            doctor_on_leave = int(local_rng.integers(1, self.num_doctors + 1))

        # Reassign patients of absent doctor across remaining doctors (Cascade)
        active_docs = [d for d in range(1, self.num_doctors + 1) if d != doctor_on_leave]
        all_scheduled = [p for p in patients if not p.is_emergency] + smart_overbooked
        for p in all_scheduled:
            if p.assigned_doctor_id == doctor_on_leave and active_docs:
                p.assigned_doctor_id = active_docs[p.slot_id % len(active_docs)]

        doctor_time = {d: 0.0 for d in active_docs}
        doctor_consult = {d: 0.0 for d in active_docs}
        doctor_idle = {d: 0.0 for d in active_docs}
        patient_waits = []
        emergency_waits = []

        total_booked = len(all_scheduled)
        total_attended = sum(1 for p in all_scheduled if p.will_show)
        total_noshows = total_booked - total_attended

        # Group regular appointments by doctor
        by_doc = {d: [] for d in active_docs}
        for p in all_scheduled:
            if p.assigned_doctor_id in by_doc:
                by_doc[p.assigned_doctor_id].append(p)

        emergencies = sorted([p for p in patients if p.is_emergency], key=lambda x: x.actual_arrival)

        # Process consultation timeline per doctor with ESI Emergency Preemption
        for doc in active_docs:
            doc_appts = sorted(by_doc[doc], key=lambda x: (x.scheduled_start, not x.is_secondary_overbook))
            doc_emergencies = [ep for ep in emergencies if ep.assigned_doctor_id == doc or (ep.assigned_doctor_id == doctor_on_leave and doc == active_docs[0])]

            timeline_appts = []
            for appt in doc_appts:
                timeline_appts.append(("APPT", appt.scheduled_start, appt))
            for em in doc_emergencies:
                timeline_appts.append(("EMERGENCY", em.actual_arrival, em))

            # Sort by arrival/start time, but Emergencies (ESI 1 & 2) preempt current queue!
            timeline_appts.sort(key=lambda item: item[1])

            for item_type, timestamp, entity in timeline_appts:
                if item_type == "EMERGENCY":
                    # ESI Preemption: gets immediate priority!
                    arrival = entity.actual_arrival
                    start_service = max(arrival, doctor_time[doc])
                    wait = start_service - arrival
                    emergency_waits.append(max(0.0, wait))
                    doctor_consult[doc] += entity.consultation_duration
                    doctor_time[doc] = start_service + entity.consultation_duration
                else:
                    # Regular appointment
                    if not entity.will_show:
                        continue
                    sched = entity.scheduled_start
                    if doctor_time[doc] < sched:
                        doctor_idle[doc] += (sched - doctor_time[doc])
                        doctor_time[doc] = sched

                    arrival = entity.actual_arrival
                    start_service = max(arrival, doctor_time[doc])
                    wait = start_service - arrival
                    patient_waits.append(max(0.0, wait))
                    doctor_consult[doc] += entity.consultation_duration
                    doctor_time[doc] = start_service + entity.consultation_duration

        total_overtime = sum(max(0.0, doctor_time[d] - self.clinic_duration_mins) for d in active_docs)

        return SimulationDayResult(
            day_index=day_seed,
            policy_name="Proposed Smart OPD (ML Overbooking + ESI)",
            total_booked=total_booked,
            total_attended=total_attended,
            total_no_shows=total_noshows,
            total_emergencies=len(emergencies),
            doctor_consultation_minutes=sum(doctor_consult.values()),
            doctor_idle_minutes=sum(doctor_idle.values()),
            doctor_overtime_minutes=total_overtime,
            patient_wait_times=patient_waits,
            emergency_wait_times=emergency_waits
        )
