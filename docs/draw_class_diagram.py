import os
os.environ['MPLCONFIGDIR'] = '/Users/irfan/.gemini/antigravity/brain/4510ac04-4ed0-4c22-b764-640b6aab507a/scratch/mpl'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUT_DIR = '/Users/irfan/.gemini/antigravity/scratch/irfan/Javid/week_2/docs'
os.makedirs(OUT_DIR, exist_ok=True)

def draw_class_diagram():
    fig, ax = plt.subplots(figsize=(15, 10), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title
    ax.text(50, 97, "Doctor-Patient Appointment Scheduling System — Week 2 OOP Class Diagram",
            ha='center', va='center', fontsize=14, fontweight='bold', color='#1e3a8a')
    ax.text(50, 94.5, "Service Managers, State Machine & Real-Time Queue Architecture",
            ha='center', va='center', fontsize=9, color='#64748b')

    def draw_box(x, y, w, h, title, subtitle, methods, header_bg='#1d4ed8'):
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.5",
                                            facecolor='white', edgecolor='#64748b', linewidth=1.2))
        ax.add_patch(patches.FancyBboxPatch((x, y + h - 3.2), w, 3.2, boxstyle="round,pad=0.1,rounding_size=0.4",
                                            facecolor=header_bg, edgecolor=header_bg))
        ax.text(x + w/2, y + h - 1.6, title, ha='center', va='center',
                fontsize=8.5, fontweight='bold', color='white')

        cy = y + h - 5.0
        if subtitle:
            ax.text(x + 1, cy, subtitle, ha='left', va='center', fontsize=6.5, fontstyle='italic', color='#475569')
            cy -= 2.0

        for m in methods:
            ax.text(x + 1, cy, f"+ {m}", ha='left', va='center', fontsize=6.2, color='#1e293b')
            cy -= 1.8

    # 1. State Machine (Top Center)
    draw_box(
        x=35, y=74, w=30, h=18,
        title="AppointmentStateMachine",
        subtitle="Enforces valid state lifecycle",
        methods=[
            "ALLOWED_TRANSITIONS: Dict",
            "can_transition(curr, next): bool",
            "validate_transition(curr, next)"
        ],
        header_bg="#7c3aed"
    )

    # 2. AppointmentManager (Center)
    draw_box(
        x=35, y=36, w=30, h=33,
        title="AppointmentManager",
        subtitle="Core lifecycle controller",
        methods=[
            "book_appointment(pat_id, doc_id, slot_id)",
            "confirm_appointment(appt_id)",
            "check_in_patient(appt_id)",
            "start_consultation(appt_id)",
            "complete_consultation(appt_id)",
            "mark_no_show(appt_id)",
            "cancel_appointment(appt_id)",
            "reschedule_appointment(appt_id, new_slot)",
            "transition_status(appt_id, target_status)"
        ],
        header_bg="#b91c1c"
    )

    # Connect StateMachine to AppointmentManager
    ax.annotate('', xy=(50, 69), xytext=(50, 74), arrowprops=dict(arrowstyle="->", color='#7c3aed', lw=1.5))
    ax.text(51.5, 71.5, "validates", fontsize=7, color='#7c3aed')

    # 3. DepartmentManager (Top Left)
    draw_box(
        x=4, y=68, w=27, h=23,
        title="DepartmentManager",
        subtitle="Clinics & floors",
        methods=[
            "register_department(name, mins, floor)",
            "get_department_by_id(id)",
            "get_department_by_name(name)",
            "get_all_departments(): List",
            "get_doctors_in_department(id)"
        ],
        header_bg="#0f766e"
    )

    # 4. DoctorManager (Middle Left)
    draw_box(
        x=4, y=34, w=27, h=29,
        title="DoctorManager",
        subtitle="Physicians & shift quotas",
        methods=[
            "register_doctor(name, spec, room, dept)",
            "get_doctor_by_id(id)",
            "get_available_doctors_by_specialty()",
            "set_doctor_availability(id, is_avail)",
            "get_doctor_workload(id, date): Dict"
        ],
        header_bg="#1d4ed8"
    )

    # Connect DepartmentManager to DoctorManager
    ax.annotate('', xy=(17.5, 63), xytext=(17.5, 68), arrowprops=dict(arrowstyle="->", color='#0f766e', lw=1.2))

    # 5. SlotManager (Bottom Left)
    draw_box(
        x=4, y=4, w=27, h=26,
        title="SlotManager",
        subtitle="Interval partitioner & collision",
        methods=[
            "generate_shift_intervals(doc, date, ...)",
            "check_collision(doc, start, end): bool",
            "create_single_slot(doc, start, end)",
            "get_free_slots(doc, date): List",
            "get_earliest_free_slot(doc, date)"
        ],
        header_bg="#4338ca"
    )

    # Connect DoctorManager to SlotManager
    ax.annotate('', xy=(17.5, 30), xytext=(17.5, 34), arrowprops=dict(arrowstyle="->", color='#1d4ed8', lw=1.2))

    # Connect SlotManager to AppointmentManager
    ax.annotate('', xy=(35, 45), xytext=(31, 25), arrowprops=dict(arrowstyle="->", color='#4338ca', lw=1.2))

    # 6. PatientManager (Top Right)
    draw_box(
        x=69, y=62, w=27, h=28,
        title="PatientManager",
        subtitle="Attendance & no-show risk",
        methods=[
            "register_patient(name, age, phone)",
            "get_patient_by_id(id)",
            "get_patient_by_phone(phone)",
            "record_attendance(id, attended: bool)",
            "get_risk_profile(id): Dict"
        ],
        header_bg="#0284c7"
    )

    # Connect PatientManager to AppointmentManager
    ax.annotate('', xy=(65, 55), xytext=(69, 70), arrowprops=dict(arrowstyle="->", color='#0284c7', lw=1.2))

    # 7. QueueManager (Bottom Right)
    draw_box(
        x=69, y=20, w=27, h=30,
        title="QueueManager",
        subtitle="Tokens & wait times",
        methods=[
            "generate_token(appointment): str",
            "get_doctor_active_queue(doc_id): List",
            "get_hospital_token_board(): List",
            "compute_estimated_wait_time(pos, mins)"
        ],
        header_bg="#d97706"
    )

    # Connect AppointmentManager to QueueManager
    ax.annotate('', xy=(69, 38), xytext=(65, 42), arrowprops=dict(arrowstyle="->", color='#d97706', lw=1.2))

    # Bottom status bar
    ax.add_patch(patches.Rectangle((4, 2), 92, 4.2, facecolor='#166534', edgecolor='none'))
    ax.text(50, 4.1, '✔  WEEK 2 COMPLETE: Object-Oriented Services, Strict State Transitions & Real-Time OPD Queue Tracking',
            ha='center', va='center', fontsize=7.5, fontweight='bold', color='white')

    out_file = os.path.join(OUT_DIR, "class_diagram.png")
    fig.savefig(out_file, dpi=220, bbox_inches='tight')
    plt.close(fig)
    print("Class diagram generated successfully at:", out_file)

if __name__ == "__main__":
    draw_class_diagram()
