# Doctor-Patient Appointment Scheduling System
## Week 2: OOP Domain Architecture & Management Services Specification

---

### 1. Overview & Architectural Goals
In Week 2, the system evolves from raw database models into a pure Object-Oriented domain service layer. 
The architecture enforces strict separation of concerns through dedicated domain managers:
1. **`DepartmentManager`**: Clinic administration, room floors, and consultation duration standards.
2. **`DoctorManager`**: Doctor schedules, shifts, maximum daily capacity, workload utilization, and emergency leaves.
3. **`PatientManager`**: Patient registration, attendance histories, and statistical no-show risk categorization.
4. **`SlotManager`**: Partitioning shifts into discrete time intervals, collision detection, and earliest-free-slot lookups.
5. **`AppointmentManager`**: Core lifecycle controller handling booking, rescheduling, and state transitions.
6. **`AppointmentStateMachine`**: Enforcing valid state progression and preventing illegal status jumps.
7. **`QueueManager`**: Generating department-prefixed token IDs, managing live OPD room queues, and computing estimated wait times.

---

### 2. Appointment State Machine

The appointment lifecycle is governed by an explicit state machine preventing race conditions and invalid transitions:

```
                  ┌───────────────┐
                  │    BOOKED     │
                  └───────┬───────┘
                          │ (confirm_appointment)
                          ▼
                  ┌───────────────┐
                  │   CONFIRMED   │
                  └───────┬───────┘
                          │ (check_in_patient)
                          ▼
                  ┌───────────────┐
                  │  CHECKED_IN   │
                  └───────┬───────┘
                          │ (start_consultation)
                          ▼
                  ┌───────────────┐
                  │IN_CONSULTATION│
                  └───────┬───────┘
                          │ (complete_consultation)
                          ▼
                  ┌───────────────┐
                  │   COMPLETED   │ [Terminal State]
                  └───────────────┘

* Cancellation is permitted from BOOKED, CONFIRMED, or CHECKED_IN.
* No-Show can be marked from CONFIRMED or CHECKED_IN (if patient does not answer call).
* COMPLETED, CANCELLED, and NO_SHOW are terminal states with zero outgoing transitions.
```

---

### 3. Manager Specifications

#### A. DepartmentManager
* Encapsulates hospital department floor routing and standard consultation times (e.g. Cardiology: 20 mins, General Medicine: 15 mins).

#### B. DoctorManager
* Tracks doctor availability and real-time workload utilization rate:
$$\text{Utilization Rate (\%)} = \left(\frac{\text{Booked Appointments}}{\text{Max Daily Capacity}}\right) \times 100$$
* Supports one-click emergency leave toggle which prevents new slot bookings and triggers rescheduling.

#### C. PatientManager
* Calculates patient no-show ratio:
$$\text{No-Show Ratio} = \frac{\text{Past No-Shows}}{\text{Total Visits}}$$
* Assigns risk categories:
  * **LOW RISK:** Ratio $< 0.20$
  * **MEDIUM RISK:** $0.20 \le \text{Ratio} < 0.40$
  * **HIGH RISK:** Ratio $\ge 0.40$ (Candidate for smart overbooking in Week 5)

#### D. SlotManager
* Partitions doctor shifts into discrete intervals:
$$\text{Slot } i: [T_{\text{start}} + i \cdot \Delta t, \,\, T_{\text{start}} + (i+1) \cdot \Delta t]$$
* Overlap detection using interval intersection checks ($O(1)$ query using SQL compound indexes).

#### E. QueueManager
* Generates tokens formatted by clinic: `CARD-001`, `GEN-002`, `ORTH-003`.
* Computes estimated wait time in minutes for patient $k$ waiting in line:
$$\text{Wait Time} = k \times \text{Department Slot Duration}$$

---

### 4. Verification Evidence
* **Unit Tests:** 6 comprehensive unit tests passing with `pytest` covering all managers and state transitions.
* **Interactive Demo:** Verified with `python3 main_demo_week2.py`.
