# Doctor-Patient Appointment Scheduling System
## Week 5: Smart Overbooking Engine & Dynamic Conflict Resolution Specification

---

### 1. The Overbooking Optimization Problem
In hospital OPDs, if every slot is strictly booked 1-to-1, patient no-shows directly cause doctor under-utilization.
However, naive overbooking (e.g. booking 2 patients for every slot) causes clinic overcrowding, severe patient wait delays, and doctor burnout.

**The Solution:**
Our **Smart Overbooking Engine** pairs empirical machine learning no-show predictions $P(\text{no-show})$ with mathematical expectation constraints to authorize secondary bookings only when statistically safe.

---

### 2. Mathematical Formulation

Let a doctor shift have capacity $C$ consultation slots.
Suppose $N$ appointments have been scheduled ($N \ge C$), where appointment $i$ has predicted no-show probability $p_i$.
The independent show probability for patient $i$ is:
$$q_i = 1 - p_i$$

#### Expected Shift Attendance:
$$\mathbb{E}[\text{Attendees}] = \sum_{i=1}^{N} q_i$$

#### Expected No-Shows Absorbed:
$$\mathbb{E}[\text{No-Shows}] = \sum_{i=1}^{N} p_i = N - \mathbb{E}[\text{Attendees}]$$

#### Smart Overbooking Constraints:
A secondary patient with show probability $q_{\text{new}}$ is permitted on slot $S$ **if and only if** all of the following conditions hold:
1. **Single Secondary Cap:** The slot does not already have an overbooked patient (maximum $+1$ overbook per slot).
2. **Elevated Risk Prerequisite:**
   $$\max(p_{\text{primary}}, p_{\text{incoming}}) \ge 0.50$$
3. **Shift Attendance Capacity Invariant:**
   $$\mathbb{E}[\text{Attendees}] + q_{\text{new}} \le C + 0.5$$
4. **Shift Overbooking Ceiling:**
   $$\text{Total Overbooked Slots in Shift} \le \lfloor 0.20 \times C \rfloor$$

---

### 3. Dynamic Conflict Resolution

#### A. Emergency Walk-in Triage Preemption (PriorityQueue)
* Uses a Min-Heap keyed on $(\text{severity\_level}, \text{arrival\_timestamp})$ where:
  * **Level 1 (Critical):** Immediate resuscitation (Cardiac arrest, severe trauma).
  * **Level 2 (Urgent):** High risk, acute chest/abdominal pain.
* **Preemption Mechanism:**
  The critical patient preempts the active doctor's room. The existing scheduled patient on that slot is shifted to the next immediate buffer slot without losing their priority.

#### B. Doctor Emergency Leave Cascade Reassignment
When a doctor calls in sick or takes emergency leave:
1. The system marks the doctor as `is_available = False`.
2. Identifies all booked consultations for the doctor for that day.
3. Automatically queries available peer specialists within the same clinical department.
4. Matches affected patients to compatible free slots in peer doctors' schedules.
5. If no free slot is available, allocates a cascade overbooking buffer slot with the peer specialist.

#### C. Cancellation Promotion
* When a primary appointment is cancelled on an overbooked slot:
  * The secondary overbooked patient is automatically promoted to **Primary Confirmed** status (`is_secondary_overbook = False`).
  * The slot's overbooked flag is cleared (`is_overbooked = False`).

---

### 4. Visual Evidence
* View **[docs/overbooking_and_triage_flow.png](overbooking_and_triage_flow.png)** for the decision flowchart covering smart overbooking evaluation, emergency triage preemption, and absence cascade rerouting.
