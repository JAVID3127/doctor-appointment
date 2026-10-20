import os
os.environ['MPLCONFIGDIR'] = '/Users/irfan/.gemini/antigravity/scratch/mpl'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

OUT_DIR = '/Users/irfan/.gemini/antigravity/scratch/irfan/Javid/week_3/docs'
os.makedirs(OUT_DIR, exist_ok=True)

def draw_schedule_comparison():
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), dpi=220)
    plt.subplots_adjust(hspace=0.4)

    # -------------------------------------------------------------
    # PANEL 1: NAIVE MANUAL SCHEDULING VS GREEDY INTERVAL PACKING
    # -------------------------------------------------------------
    ax1.set_xlim(0, 240)
    ax1.set_ylim(-0.5, 2.5)
    ax1.set_yticks([0.5, 1.5])
    ax1.set_yticklabels(['Greedy Interval\nScheduling (75% Util)', 'Naive Manual\nBooking (33% Util)'], fontsize=9, fontweight='bold')
    ax1.set_xlabel('Shift Timeline (09:00 AM to 01:00 PM - 240 Minutes)', fontsize=9, fontweight='semibold')
    ax1.set_title('Doctor Shift Timeline: Naive Scattered Slots vs. Greedy Interval Compaction', fontsize=11, fontweight='bold', pad=10, color='#1e3a8a')
    ax1.grid(axis='x', linestyle=':', alpha=0.6)

    # Shift background (gray)
    ax1.add_patch(patches.Rectangle((0, 1.1), 240, 0.8, facecolor='#f1f5f9', edgecolor='#94a3b8', linewidth=1))
    ax1.add_patch(patches.Rectangle((0, 0.1), 240, 0.8, facecolor='#f1f5f9', edgecolor='#94a3b8', linewidth=1))

    # Naive slots
    naive_slots = [
        (0, 20, "Patient 1"),
        (75, 95, "Patient 2"),
        (160, 180, "Patient 3"),
        (210, 230, "Patient 4")
    ]
    for start, end, label in naive_slots:
        ax1.add_patch(patches.Rectangle((start, 1.15), end - start, 0.7, facecolor='#3b82f6', edgecolor='#1d4ed8', lw=1.2))
        ax1.text((start + end)/2, 1.5, label, ha='center', va='center', color='white', fontsize=7.5, fontweight='bold')

    # Idle gap annotations in naive
    ax1.text(47, 1.5, 'IDLE GAP (55m)', ha='center', va='center', color='#b91c1c', fontsize=7.5, fontweight='bold')
    ax1.text(127, 1.5, 'IDLE GAP (65m)', ha='center', va='center', color='#b91c1c', fontsize=7.5, fontweight='bold')
    ax1.text(195, 1.5, 'IDLE (30m)', ha='center', va='center', color='#b91c1c', fontsize=7.5, fontweight='bold')

    # Greedy packed slots
    for i in range(9):
        st = i * 25
        et = st + 20
        ax1.add_patch(patches.Rectangle((st, 0.15), 20, 0.7, facecolor='#16a34a', edgecolor='#15803d', lw=1.2))
        ax1.text((st + et)/2, 0.5, f"P-{i+1}", ha='center', va='center', color='white', fontsize=7.5, fontweight='bold')
        # Buffer
        if i < 8:
            ax1.add_patch(patches.Rectangle((et, 0.15), 5, 0.7, facecolor='#fef08a', edgecolor='#ca8a04', lw=0.5))

    ax1.text(230, 0.5, 'Buffer', ha='center', va='center', color='#854d0e', fontsize=6.5)

    # -------------------------------------------------------------
    # PANEL 2: MULTI-DOCTOR INTERVAL PARTITIONING (CARDIOLOGY)
    # -------------------------------------------------------------
    ax2.set_xlim(0, 150)
    ax2.set_ylim(-0.5, 2.5)
    ax2.set_yticks([0.5, 1.5])
    ax2.set_yticklabels(['Dr. Priya Nambiar\n(Room 202)', 'Dr. Vikram Patel\n(Room 201)'], fontsize=9, fontweight='bold')
    ax2.set_xlabel('Minutes from 09:00 AM', fontsize=9, fontweight='semibold')
    ax2.set_title('Multi-Doctor Interval Partitioning: Zero Collisions Across Parallel Rooms', fontsize=11, fontweight='bold', pad=10, color='#0f766e')
    ax2.grid(axis='x', linestyle=':', alpha=0.6)

    # Doctor 1 slots (0-30, 30-60, 60-90, 90-120)
    doc1_slots = [(0, 30, "CARD-1"), (30, 60, "CARD-3"), (60, 90, "CARD-5"), (90, 120, "CARD-7")]
    for st, et, lbl in doc1_slots:
        ax2.add_patch(patches.Rectangle((st, 1.15), et - st, 0.7, facecolor='#0284c7', edgecolor='#0369a1', lw=1.2))
        ax2.text((st + et)/2, 1.5, lbl, ha='center', va='center', color='white', fontsize=8, fontweight='bold')

    # Doctor 2 slots (10-40, 40-70, 70-100, 100-130)
    doc2_slots = [(10, 40, "CARD-2"), (40, 70, "CARD-4"), (70, 100, "CARD-6"), (100, 130, "CARD-8")]
    for st, et, lbl in doc2_slots:
        ax2.add_patch(patches.Rectangle((st, 0.15), et - st, 0.7, facecolor='#0d9488', edgecolor='#0f766e', lw=1.2))
        ax2.text((st + et)/2, 0.5, lbl, ha='center', va='center', color='white', fontsize=8, fontweight='bold')

    out_file = os.path.join(OUT_DIR, "schedule_visualization.png")
    fig.savefig(out_file, dpi=220, bbox_inches='tight')
    plt.close(fig)
    print("Schedule comparison visualization generated successfully at:", out_file)

if __name__ == "__main__":
    draw_schedule_comparison()
