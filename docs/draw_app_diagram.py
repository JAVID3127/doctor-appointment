import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

def draw_web_app_architecture():
    fig, ax = plt.subplots(figsize=(14, 10), dpi=300)
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    # Titles
    plt.suptitle("Smart Hospital OPD Scheduling System - Web & System Architecture", fontsize=18, fontweight="bold", y=0.96, color="#0f172a")
    plt.title("Tiered Client-Server Architecture: Responsive Web UI, RESTful Endpoints, Domain Algorithms, & SQLite Persistence", fontsize=11, color="#475569", pad=15)

    def draw_box(x, y, w, h, title, subtitle, bg_color, border_color, text_color="#0f172a"):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.08",
                                     linewidth=2, edgecolor=border_color, facecolor=bg_color, zorder=2)
        ax.add_patch(rect)
        ax.text(x + w / 2, y + h - 0.22, title, ha="center", va="center", fontsize=11, fontweight="bold", color=text_color, zorder=3)
        ax.text(x + w / 2, y + h / 2 - 0.1, subtitle, ha="center", va="center", fontsize=8.5, color=text_color, zorder=3, multialignment="center")

    def draw_layer_bg(x, y, w, h, label, bg_color, border_color):
        rect = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.04,rounding_size=0.12",
                                     linewidth=1.5, linestyle="--", edgecolor=border_color, facecolor=bg_color, zorder=1)
        ax.add_patch(rect)
        ax.text(x + 0.3, y + h - 0.25, label, ha="left", va="center", fontsize=11, fontweight="bold", color=border_color, zorder=3)

    # 1. Presentation Tier (Top)
    draw_layer_bg(0.5, 7.0, 13.0, 2.3, "TIER 1: PRESENTATION & CLIENT DASHBOARDS", "#e0f2fe", "#0284c7")
    draw_box(0.8, 7.3, 3.8, 1.6, "Waiting Hall Display", "Fullscreen High-Contrast Token Board\nLive Clock & 3s Real-time Polling\nRoom & Token Caller", "#ffffff", "#0284c7")
    draw_box(5.1, 7.3, 3.8, 1.6, "Doctor Workstation", "OPD Consultation Room Dashboard\nStatus Transitions (Check-in, Finish)\nEmergency Leave Cascade Button", "#ffffff", "#0284c7")
    draw_box(9.4, 7.3, 3.8, 1.6, "Patient Portal & Triage", "Patient Self-Service Booking\nDynamic Slot Dropdown\nEmergency Walk-in Priority Override", "#ffffff", "#0284c7")

    # 2. Application & REST API Tier (Middle-Top)
    draw_layer_bg(0.5, 4.4, 13.0, 2.2, "TIER 2: FLASK REST API ROUTING & CONTROLLERS", "#f0fdf4", "#16a34a")
    draw_box(0.8, 4.7, 3.8, 1.5, "Token & Board API", "GET /api/queue/token-board\nGET /api/metrics\nLive Room Status & Queue Feeds", "#ffffff", "#16a34a")
    draw_box(5.1, 4.7, 3.8, 1.5, "Appointment Controller", "POST /api/appointments\nPATCH /api/appointments/<id>/status\nToken Generation & Promotion", "#ffffff", "#16a34a")
    draw_box(9.4, 4.7, 3.8, 1.5, "Doctor & Triage Controller", "GET /api/doctors/<id>/slots\nPOST /api/doctors/<id>/leave\nPOST /api/triage", "#ffffff", "#16a34a")

    # 3. Domain Service & Algorithmic Core (Middle-Bottom)
    draw_layer_bg(0.5, 2.1, 13.0, 2.0, "TIER 3: DOMAIN SERVICE & ALGORITHMIC ENGINES", "#fef3c7", "#d97706")
    draw_box(0.8, 2.3, 3.8, 1.4, "Interval Scheduler", "Greedy Interval Partitioning\nMulti-Doctor Min-Heap O(n log d)\nDynamic Gap Compaction", "#ffffff", "#d97706")
    draw_box(5.1, 2.3, 3.8, 1.4, "ML No-Show Predictor", "Trained Feature Logistic Model\nAttendance Probability P(Show)\nLead-Time & History Calibration", "#ffffff", "#d97706")
    draw_box(9.4, 2.3, 3.8, 1.4, "Smart Overbooking & Triage", "Dynamic E[Show] Overbook +1\nWalk-in Preemption & Priority Queue\nDoctor Leave Cascade Reassignment", "#ffffff", "#d97706")

    # 4. Data Persistence Tier (Bottom)
    draw_layer_bg(0.5, 0.2, 13.0, 1.6, "TIER 4: DATABASE & STORAGE LAYER (SQLAlchemy ORM & SQLite)", "#f5f3ff", "#7c3aed")
    draw_box(0.8, 0.35, 12.4, 0.95, "Relational Schema: opd_hospital.db", "Departments | Doctors | Patients | TimeSlots | Appointments | EmergencyTriage | HistoricalRecords", "#ffffff", "#7c3aed")

    # Flow arrows
    def draw_arrow(x1, y1, x2, y2, color="#64748b"):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="<|-|>", color=color, lw=2.0, mutation_scale=15))

    draw_arrow(2.7, 7.3, 2.7, 6.2, "#0284c7")
    draw_arrow(7.0, 7.3, 7.0, 6.2, "#0284c7")
    draw_arrow(11.3, 7.3, 11.3, 6.2, "#0284c7")

    draw_arrow(2.7, 4.7, 2.7, 3.7, "#16a34a")
    draw_arrow(7.0, 4.7, 7.0, 3.7, "#16a34a")
    draw_arrow(11.3, 4.7, 11.3, 3.7, "#16a34a")

    draw_arrow(7.0, 2.3, 7.0, 1.35, "#d97706")

    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9.8)
    ax.axis("off")

    output_path = Path(__file__).resolve().parent / "web_app_architecture.png"
    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close()
    print(f"✅ Generated Web Architecture diagram: {output_path}")

if __name__ == "__main__":
    draw_web_app_architecture()
