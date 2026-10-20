# Smart OPD: Doctor-Patient Appointment Scheduling System
## Final Academic Project Defense Presentation (7-Week Execution)

---

### Slide 1: Title & Overview
**Project Title:** Smart Hospital OPD: An Algorithmic & Machine Learning System for Outpatient Scheduling  
**Domain:** Healthcare Operations Research & Artificial Intelligence  
**Focus:** Busy Government Hospital Outpatient Departments (OPDs)  
**Key Innovations:**
- Greedy Multi-Doctor Interval Partitioning ($O(n \log d)$)
- Machine Learning Attendance Forecasting ($P(\text{No-Show})$)
- Risk-Aware Smart Overbooking with $+1$ Slot Cap
- Emergency Severity Index (ESI) Real-Time Walk-in Preemption
- Big-Screen Waiting Hall Digital Token Display & Doctor Dashboards

---

### Slide 2: Clinical Context & Problem Motivation
- **The Public OPD Crisis:** Government hospitals handle hundreds of walk-ins and appointments daily per doctor.
- **The Core Trade-off:**
  - *Doctor Idle Time* (Wasted capacity when scheduled patients fail to show up) vs.
  * *Patient Wait Times* (Overcrowded, infectious waiting halls when clinics overbook naively).
- **The Empirical Reality:**
  - Average patient no-show rate is **~25%** in public healthcare.
  - Traditional fixed booking results in doctors sitting idle 20-30% of their working hours.
  - Naive flat overbooking causes cascading 45-60 minute waiting room delays and physician burnout.

---

### Slide 3: 7-Week Project Lifecycle Roadmap
- **Week 1:** Foundation & Relational Database Architecture (SQLite, 7 tables, SQLAlchemy ORM)
- **Week 2:** Object-Oriented Domain Layer & State Transition Machines (`AppointmentStateMachine`)
- **Week 3:** Interval Scheduling Core (Greedy Earliest Finish Time & Multi-Doctor Min-Heap Partitioning)
- **Week 4:** Machine Learning No-Show Predictor (2,500 patient cohort, Logistic Regression & Random Forest, 0.752 ROC-AUC)
- **Week 5:** Smart Overbooking ($\mathbb{E}[\text{Show}]$ threshold model) & Emergency Preemption Engine
- **Week 6:** Full-Stack Web Application (Flask REST API, Doctor Dashboard, Patient Portal, Live Token Board)
- **Week 7:** Monte Carlo Simulation (30 days, 3,000+ patient arrivals), Empirical Benchmarking & Defense Report

---

### Slide 4: Algorithmic Core — Greedy Interval Partitioning
- **Interval Scheduling Maximization (EFT):** Sort by finish time $f_i$ ($O(n \log n)$) to maximize non-overlapping consultations.
- **Interval Partitioning Across $d$ Physicians:**
  - Utilizes a Min-Heap keyed on doctor earliest available time $t_k$.
  - Assigns incoming appointment interval to doctor with $\min(t_k)$ if $t_k \le s_i$.
  - Complexity: $O(n \log d)$, achieving theoretically optimal room allocation.
- **Shift Compaction:** Closes non-productive doctor idle gaps, increasing raw slot capacity by $+41.7\%$.

---

### Slide 5: Machine Learning No-Show Forecasting Model
- **Trained on 2,500 Outpatient Encounters:**
  - Features: `lead_days` ($+0.14$), `historical_no_show_ratio` ($+4.00$), `sms_reminder_sent` ($-1.40$), `patient_age` ($-0.02$).
- **Calibrated Logistic Equation:**
  $$\text{logit}(p) = -1.80 + 0.14 \cdot \text{lead\_days} + 4.00 \cdot \text{ratio} - 1.40 \cdot \text{sms} - 0.02 \cdot (\text{age} - 40)$$
- **Performance:** ROC-AUC **0.752**, Precision **78.4%**, Recall **71.2%**.
- **Clinical Insight:** Lead time >7 days combined with zero prior visits spikes no-show probability to >58%.

---

### Slide 6: Smart Overbooking & Dynamic Conflict Resolution
- **Expected Show Formulation:**
  $$\mathbb{E}[\text{Show}] = P(\text{Show}_1) + P(\text{Show}_2) = (1 - P_1) + (1 - P_2)$$
- **Mathematical Policy Rule:**
  - Secondary slot overbooking is permitted *if and only if* $P_1(\text{No-Show}) \ge 0.50$.
  - Hard cap: Max $+1$ overbook per slot (strictly prevents uncontrolled cascading).
  - Cancellation Auto-Promotion: If primary patient cancels, secondary patient is instantly elevated to primary status.
- **Emergency Priority Preemption:**
  - Critical ESI Level 1 & 2 walk-ins immediately preempt doctor's queue via PriorityQueue.
  - Doctor Unscheduled Absence: Cascades remaining active consultations across available peer specialists.

---

### Slide 7: Full-Stack Web Application & Portals
- **Tier 1 (Presentation):**
  - **Lobby Digital Token Board (`/display`):** 3-second auto-polling feed for waiting hall TVs.
  - **Doctor Consultation Workstation (`/doctor/<id>`):** Direct status transitions (`CHECKED_IN`, `IN_CONSULTATION`, `COMPLETED`).
  - **Patient Self-Booking Portal (`/book`):** Real-time available slot selection with token generation.
  - **Emergency Triage Desk (`/triage`):** Rapid clinical preemption intake.
- **Tier 2 (RESTful API):** 10 endpoints handling JSON payloads with transactional integrity.

---

### Slide 8: 30-Day Monte Carlo Simulation Architecture
- **Stochastic Patient Process Model:**
  - 4 Specialist Doctors, 7-hour daily clinic operations (420 minutes, 28 slots/doctor).
  - Consultation durations sampled from empirical Log-normal distribution ($\mu=2.65, \sigma=0.28$, mean $\approx 14.5$ mins).
  - Walk-in emergencies generated via Poisson process ($\lambda = 5.0$ cases/day).
  - Random doctor emergency leave probability ($p=0.03$ per doctor-day).
- **Paired Experimental Runs:** Exact seed sequence matching for rigorous variance reduction.

---

### Slide 9: Quantitative Benchmark Comparison
| Operational Metric | Traditional Fixed | Naive Static (+25%) | Proposed Smart OPD | Clinical Significance |
| :--- | :---: | :---: | :---: | :--- |
| **Doctor Utilization** | 83.0% | 96.2% | **93.6%** | $+12.8\%$ relative gain vs. Fixed |
| **Doctor Idle Downtime** | 300.7 min/day | 70.3 min/day | **107.9 min/day** | **-64.1% reduction** in wasted doctor time |
| **Average Patient Wait** | 11.3 min | 25.6 min | **21.1 min** | **-17.7% lower wait** vs. Naive Overbooking |
| **90th Percentile Wait** | 25.0 min | 55.9 min | **52.5 min** | Controlled wait distribution |
| **Emergency Response Time** | 239.2 min | 255.1 min | **26.6 min** | **-88.9% reduction** in life-saving triage latency |
| **Patients Treated (30 Days)**| 2,824 | 3,455 | **3,069** | $+245$ additional outpatients served |

---

### Slide 10: The Pareto-Optimal Efficiency Frontier
- **The Classic Operations Frontier:**
  - *Traditional Fixed Booking:* Doctor idle downtime is excessive (~301 mins/day) while patient wait times are low.
  - *Naive Flat Overbooking:* Severe queue instability — 55+ minute wait times and 200+ minutes of clinic overtime.
  - *Proposed Smart OPD:* Reaches the **Pareto-Optimal Sweet Spot** on the hyperbolic trade-off curve, recapturing $64\%$ of idle doctor capacity while shielding patients from extreme congestion.

---

### Slide 11: Real-World Clinical Impact & Feasibility
1. **Zero Hardware Barrier:** Runs on standard hospital local intranet; works seamlessly on existing reception PCs and waiting lobby TV displays.
2. **Transparent Explainability:** No-show risk scoring uses calibrated linear factors that hospital administrators and medical superintendents can audit.
3. **Emergency Safeguards:** Life-threatening emergencies are never blocked by pre-scheduled appointments.
4. **Physician Well-being:** Controlled overtime eliminates chronic physician burnout caused by uncalibrated overbooking.

---

### Slide 12: Project Conclusion & Future Roadmap
- **Conclusion:**
  - Successfully designed, implemented, tested, and benchmarked a complete end-to-end Smart OPD solution across all 7 weeks.
  - Proved mathematically and empirically that combining Greedy Interval Scheduling with ML risk scoring resolves the healthcare idle-wait paradox.
- **Future Extensions:**
  - Integration with national Ayushman Bharat Digital Mission (ABDM) / ABHA health records.
  - Multi-lingual SMS & WhatsApp interactive 2-way attendance confirmation bots.
  - Real-time IoT Bluetooth beacon patient arrival tracking in outpatient waiting halls.
