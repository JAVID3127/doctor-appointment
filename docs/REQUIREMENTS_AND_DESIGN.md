# Doctor-Patient Appointment Scheduling System
## Week 1: Requirements Analysis, System Design & Database Specification

---

### 1. Project Background & Problem Context
In busy public hospital Outpatient Departments (OPDs), manual queue and token systems lead to two primary bottlenecks:
* **Overcrowded Waiting Halls:** Long queues resulting from unscheduled walk-ins and overlapping appointments.
* **Wasted Doctor Time (No-Shows):** 20% to 30% of scheduled patients do not arrive, leaving doctors idle while walk-in patients wait outside.

The goal of Week 1 is to establish the complete architectural foundation, entity models, database schema, and data access layer to enable:
1. **Interval Scheduling:** Efficient packing of consultation intervals across doctor shifts.
2. **AI No-Show Forecasting:** Historical tracking to support smart overbooking.
3. **OOP Domain Models:** Clean encapsulation of hospital entities with state tracking and conflict resolution.

---

### 2. User Roles & Use Cases

#### System Users
1. **OPD Receptionist / Administrator:**
   * Registers departments, doctors, and rooms.
   * Manages on-site patient registrations and walk-in triage.
   * Views the live queue and token board.
2. **Consulting Doctor:**
   * Configures availability and shift schedules.
   * Views daily consultation timeline and marks appointment progress (`CHECKED_IN`, `IN_CONSULTATION`, `COMPLETED`, `NO_SHOW`).
   * Requests emergency leave or rescheduling.
3. **Patient / Attendant:**
   * Searches available doctors by medical specialization.
   * Requests consultation time slots.
   * Tracks assigned token number and estimated wait time.

#### Major Operations
* **UC-01 (Register Entities):** Add departments, doctors, and patient profiles with contact information.
* **UC-02 (Slot Generation):** Partition doctor working hours into non-overlapping consultation intervals.
* **UC-03 (Appointment Booking):** Allocate primary slots or smart-overbooked secondary slots based on no-show risk.
* **UC-04 (Emergency Walk-in Triage):** Insert urgent cases into doctor queues using PriorityQueue preemption.
* **UC-05 (Attendance & Retraining Logging):** Record whether a patient attended or missed the appointment to keep historical records updated.

---

### 3. Database Architecture & ER Specification

The system uses a relational SQLite/MySQL database with 7 core tables:

```
+-------------------+           +-----------------------+
|    departments    | 1       N |        doctors        |
|-------------------|-----------|-----------------------|
| dept_id (PK)      |           | doctor_id (PK)        |
| dept_name (UQ)    |           | dept_id (FK)          |
| default_slot_mins |           | name, specialization  |
| floor_number      |           | room_number, capacity |
+-------------------+           +-----------------------+
                                        | 1
                                        |
                                        | N
+-------------------+           +-----------------------+
|     patients      |           |      time_slots       |
|-------------------|           |-----------------------|
| patient_id (PK)   |           | slot_id (PK)          |
| name, age, gender |           | doctor_id (FK)        |
| phone (UQ)        |           | start_time, end_time  |
| visits, no_shows  |           | is_booked, overbooked |
+-------------------+           +-----------------------+
        | 1                             | 1
        |                               |
        +---------------+---------------+
                        |
                        | N
                +-----------------------+
                |     appointments      |
                |-----------------------|
                | appointment_id (PK)   |
                | patient_id (FK)       |
                | doctor_id (FK)        |
                | slot_id (FK)          |
                | booking_timestamp     |
                | status (ENUM)         |
                | predicted_no_show_prob|
                +-----------------------+
```

#### Detailed Table Specifications

| Table Name | Primary Key | Foreign Keys | Key Attributes & Constraints |
| :--- | :--- | :--- | :--- |
| `departments` | `dept_id` | - | `dept_name` (UNIQUE), `default_slot_duration_mins`, `floor_number` |
| `doctors` | `doctor_id` | `dept_id` | `name`, `specialization`, `room_number`, `max_daily_capacity`, `is_available` |
| `patients` | `patient_id` | - | `name`, `age`, `gender`, `phone` (UNIQUE), `total_visits`, `past_no_shows` |
| `time_slots` | `slot_id` | `doctor_id` | `start_time`, `end_time` (`CHECK(end_time > start_time)`), `is_booked`, `is_overbooked` |
| `appointments` | `appointment_id` | `patient_id`, `doctor_id`, `slot_id` | `booking_timestamp`, `status` (`BOOKED..COMPLETED`), `predicted_no_show_prob` |
| `emergency_triage` | `triage_id` | `patient_id`, `doctor_id`, `preempted_slot_id` | `severity_level` (1=Critical..4=Non-urgent), `arrival_time` |
| `historical_records` | `record_id` | `patient_id` | `lead_days`, `day_of_week`, `sms_sent`, `no_show_flag` |

---

### 4. OOP Design & State Machine

#### Appointment Lifecycle State Machine
```
[BOOKED] ──► [CONFIRMED] ──► [CHECKED_IN] ──► [IN_CONSULTATION] ──► [COMPLETED]
    │                                                    │
    └─────────────────────► [CANCELLED]                  └──► [NO_SHOW]
```

#### Conflict Prevention Rules
1. **No Overlapping Slots for Same Doctor:** Checked via `check_slot_collision` before creating any interval.
2. **Strict Time Boundaries:** Slot start time must be strictly before end time.
3. **Controlled Overbooking:** Overbooking is restricted to a maximum of 1 extra patient per slot and requires explicit flag authorization.

---

### 5. Verification & Testing Evidence
* **Unit Test Suite:** 8 test cases written with `pytest` covering entity creation, slot collision prevention, state transitions, and overbooking flow.
* **Test Status:** 8/8 passed, 0 warnings.
* **Database Seed Script:** Populated with 5 departments, 7 doctors, 10 patients, 12 time slots, 4 active appointments, 1 emergency triage case, and 50 historical training records.
