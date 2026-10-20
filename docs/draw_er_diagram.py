import os
os.environ['MPLCONFIGDIR'] = '/Users/irfan/.gemini/antigravity/brain/4510ac04-4ed0-4c22-b764-640b6aab507a/scratch/mpl'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUT_DIR = '/Users/irfan/.gemini/antigravity/scratch/doctor_appointment_system/week_1/docs'
os.makedirs(OUT_DIR, exist_ok=True)

def draw_er_diagram():
    fig, ax = plt.subplots(figsize=(14, 9), dpi=220)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Title
    ax.text(50, 96, "Doctor-Patient Appointment Scheduling System — Entity Relationship (ER) Diagram",
            ha='center', va='center', fontsize=14, fontweight='bold', color='#1e3a8a')
    ax.text(50, 93, "Week 1 Database Architecture Specification",
            ha='center', va='center', fontsize=9, color='#64748b')

    # Helper function to draw an entity table
    def draw_entity(x, y, w, h, table_name, pk, fks, attrs, header_color='#1d4ed8'):
        # Outer box
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.5",
                                            facecolor='white', edgecolor='#64748b', linewidth=1.2))
        # Header
        ax.add_patch(patches.FancyBboxPatch((x, y + h - 3.2), w, 3.2, boxstyle="round,pad=0.1,rounding_size=0.4",
                                            facecolor=header_color, edgecolor=header_color))
        ax.text(x + w/2, y + h - 1.6, table_name.upper(), ha='center', va='center',
                fontsize=8, fontweight='bold', color='white')

        # Attributes
        cy = y + h - 4.8
        ax.text(x + 1, cy, f"[PK] {pk}", ha='left', va='center', fontsize=6.8, fontweight='bold', color='#b45309')
        cy -= 2.0
        for fk in fks:
            ax.text(x + 1, cy, f"[FK] {fk}", ha='left', va='center', fontsize=6.5, fontweight='bold', color='#0369a1')
            cy -= 1.8
        for attr in attrs:
            ax.text(x + 1, cy, f"• {attr}", ha='left', va='center', fontsize=6.2, color='#1e293b')
            cy -= 1.6

    # 1. Departments (Top Left)
    draw_entity(
        x=5, y=70, w=25, h=18,
        table_name="departments",
        pk="dept_id: INT",
        fks=[],
        attrs=["dept_name: VARCHAR", "default_slot_mins: INT", "floor_number: INT"],
        header_color="#0f766e"
    )

    # 2. Doctors (Middle Left)
    draw_entity(
        x=5, y=36, w=25, h=26,
        table_name="doctors",
        pk="doctor_id: INT",
        fks=["dept_id: INT"],
        attrs=["name: VARCHAR", "specialization: VARCHAR", "room_number: VARCHAR", "max_capacity: INT", "is_available: BOOL"],
        header_color="#1d4ed8"
    )

    # 3. Time Slots (Bottom Left)
    draw_entity(
        x=5, y=6, w=25, h=22,
        table_name="time_slots",
        pk="slot_id: INT",
        fks=["doctor_id: INT"],
        attrs=["start_time: DATETIME", "end_time: DATETIME", "is_booked: BOOL", "is_overbooked: BOOL"],
        header_color="#4338ca"
    )

    # 4. Appointments (Center)
    draw_entity(
        x=38, y=32, w=27, h=30,
        table_name="appointments",
        pk="appointment_id: INT",
        fks=["patient_id: INT", "doctor_id: INT", "slot_id: INT"],
        attrs=["booking_time: DATETIME", "status: ENUM", "predicted_no_show: FLOAT"],
        header_color="#b91c1c"
    )

    # 5. Patients (Top Right)
    draw_entity(
        x=72, y=56, w=24, h=32,
        table_name="patients",
        pk="patient_id: INT",
        fks=[],
        attrs=["name: VARCHAR", "age: INT", "gender: VARCHAR", "phone: VARCHAR (UQ)", "total_visits: INT", "past_no_shows: INT"],
        header_color="#0369a1"
    )

    # 6. Emergency Triage (Middle Right)
    draw_entity(
        x=38, y=5, w=27, h=20,
        table_name="emergency_triage",
        pk="triage_id: INT",
        fks=["patient_id: INT", "doctor_id: INT", "preempted_slot: INT"],
        attrs=["severity_level: INT", "arrival_time: DATETIME"],
        header_color="#dc2626"
    )

    # 7. Historical Records (Bottom Right)
    draw_entity(
        x=72, y=14, w=24, h=24,
        table_name="historical_records",
        pk="record_id: INT",
        fks=["patient_id: INT"],
        attrs=["lead_days: INT", "day_of_week: INT", "sms_sent: BOOL", "no_show_flag: BOOL"],
        header_color="#6b21a8"
    )

    # Connector Lines
    # Departments -> Doctors
    ax.plot([17.5, 17.5], [70, 62], color='#0f766e', lw=1.5, linestyle='-')
    ax.text(19, 66, "1 : N", fontsize=7.5, fontweight='bold', color='#0f766e')

    # Doctors -> TimeSlots
    ax.plot([17.5, 17.5], [36, 28], color='#1d4ed8', lw=1.5, linestyle='-')
    ax.text(19, 32, "1 : N", fontsize=7.5, fontweight='bold', color='#1d4ed8')

    # Doctors -> Appointments
    ax.plot([30, 38], [48, 48], color='#1d4ed8', lw=1.5, linestyle='-')
    ax.text(33, 50, "1 : N", fontsize=7.5, fontweight='bold', color='#1d4ed8')

    # Patients -> Appointments
    ax.plot([72, 65], [70, 52], color='#0369a1', lw=1.5, linestyle='-')
    ax.text(67, 63, "1 : N", fontsize=7.5, fontweight='bold', color='#0369a1')

    # TimeSlots -> Appointments
    ax.plot([30, 42], [20, 32], color='#4338ca', lw=1.5, linestyle='-')
    ax.text(34, 25, "1 : 1..2", fontsize=7.5, fontweight='bold', color='#4338ca')

    # Patients -> Historical Records
    ax.plot([84, 84], [56, 38], color='#6b21a8', lw=1.5, linestyle='-')
    ax.text(85.5, 47, "1 : N", fontsize=7.5, fontweight='bold', color='#6b21a8')

    out_file = os.path.join(OUT_DIR, "database_schema.png")
    fig.savefig(out_file, dpi=220, bbox_inches='tight')
    plt.close(fig)
    print("ER diagram generated successfully at:", out_file)

if __name__ == "__main__":
    draw_er_diagram()
