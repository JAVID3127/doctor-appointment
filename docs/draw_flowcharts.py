import os
os.environ['MPLCONFIGDIR'] = '/Users/irfan/.gemini/antigravity/scratch/mpl'

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent
os.makedirs(OUT_DIR, exist_ok=True)

def draw_overbooking_and_conflict_flow():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 8), dpi=220)
    plt.subplots_adjust(wspace=0.25)

    # -------------------------------------------------------------
    # PANEL 1: SMART OVERBOOKING DECISION PIPELINE
    # -------------------------------------------------------------
    ax1.set_xlim(0, 100)
    ax1.set_ylim(0, 100)
    ax1.axis('off')
    ax1.set_title('Smart Overbooking Mathematical Decision Flowchart', fontsize=11, fontweight='bold', color='#1e3a8a', pad=12)

    def draw_node(ax, x, y, w, h, text, bg='#eff6ff', border='#3b82f6', is_rhombus=False):
        if is_rhombus:
            # Decision Diamond
            diamond = patches.Polygon([
                [x + w/2, y], [x + w, y + h/2], [x + w/2, y + h], [x, y + h/2]
            ], facecolor=bg, edgecolor=border, lw=1.3)
            ax.add_patch(diamond)
        else:
            ax.add_patch(patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=0.5",
                                                facecolor=bg, edgecolor=border, lw=1.3))
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=7.2, fontweight='bold', color='#1e293b')

    # Steps in Panel 1
    draw_node(ax1, 20, 88, 60, 8, "Incoming Patient Request & Target Slot", bg='#dbeafe', border='#2563eb')
    ax1.annotate('', xy=(50, 78), xytext=(50, 88), arrowprops=dict(arrowstyle="->", color='#64748b', lw=1.2))

    draw_node(ax1, 20, 70, 60, 8, "Query ML Model: Compute P(no-show)", bg='#fef3c7', border='#d97706')
    ax1.annotate('', xy=(50, 58), xytext=(50, 70), arrowprops=dict(arrowstyle="->", color='#64748b', lw=1.2))

    draw_node(ax1, 15, 46, 70, 12, "Is Slot Booked & Max(P_primary, P_incoming) >= 50%?", bg='#fef9c3', border='#ca8a04', is_rhombus=True)

    # YES branch
    ax1.annotate('YES', xy=(50, 32), xytext=(50, 46), arrowprops=dict(arrowstyle="->", color='#16a34a', lw=1.4))
    draw_node(ax1, 15, 20, 70, 12, "Does E[Show] + (1 - P_in) <= Doctor Capacity?", bg='#fef9c3', border='#ca8a04', is_rhombus=True)

    ax1.annotate('YES', xy=(50, 8), xytext=(50, 20), arrowprops=dict(arrowstyle="->", color='#16a34a', lw=1.4))
    draw_node(ax1, 20, 0, 60, 8, "AUTHORIZE SMART OVERBOOKING\nFlag Slot: is_overbooked=True", bg='#dcfce7', border='#16a34a')

    # NO branches
    ax1.annotate('NO', xy=(5, 52), xytext=(15, 52), arrowprops=dict(arrowstyle="->", color='#dc2626', lw=1.2))
    draw_node(ax1, 0, 48, 12, 8, "Single\nSlot", bg='#fee2e2', border='#ef4444')

    ax1.annotate('NO', xy=(85, 26), xytext=(85, 26), arrowprops=dict(arrowstyle="->", color='#dc2626', lw=1.2))
    draw_node(ax1, 86, 22, 14, 8, "Deny\nOverbook", bg='#fee2e2', border='#ef4444')

    # -------------------------------------------------------------
    # PANEL 2: CONFLICT RESOLUTION & TRIAGE PIPELINE
    # -------------------------------------------------------------
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 100)
    ax2.axis('off')
    ax2.set_title('Dynamic Conflict Resolution & Triage Architecture', fontsize=11, fontweight='bold', color='#0f766e', pad=12)

    # Top: Emergency Triage Flow
    draw_node(ax2, 5, 86, 42, 10, "Emergency Walk-in Arrival\n(PriorityQueue Min-Heap)", bg='#fee2e2', border='#dc2626')
    ax2.annotate('', xy=(26, 74), xytext=(26, 86), arrowprops=dict(arrowstyle="->", color='#dc2626', lw=1.4))
    draw_node(ax2, 5, 62, 42, 12, "Preempt Active Room\nPush Waiting to Buffer Slot", bg='#fce7f3', border='#db2777')

    # Bottom: Doctor Absence Cascade
    draw_node(ax2, 53, 86, 42, 10, "Doctor Emergency Leave\n(Absence Detected)", bg='#fef3c7', border='#d97706')
    ax2.annotate('', xy=(74, 74), xytext=(74, 86), arrowprops=dict(arrowstyle="->", color='#d97706', lw=1.4))
    draw_node(ax2, 53, 62, 42, 12, "Scan Peer Specialists in Dept\nMatching Time Window", bg='#e0f2fe', border='#0284c7')
    ax2.annotate('', xy=(74, 50), xytext=(74, 62), arrowprops=dict(arrowstyle="->", color='#0284c7', lw=1.4))
    draw_node(ax2, 53, 38, 42, 12, "Reroute Appointments to\nFree Slots or Safe Buffers", bg='#dcfce7', border='#16a34a')

    # Bottom Banner
    ax2.add_patch(patches.FancyBboxPatch((5, 8), 90, 16, boxstyle="round,pad=0.3,rounding_size=0.6",
                                         facecolor='#f8fafc', edgecolor='#64748b', lw=1.2))
    ax2.text(50, 19, "Cancellation Promotion Workflow", ha='center', va='center', fontsize=8, fontweight='bold', color='#1e3a8a')
    ax2.text(50, 12.5, "Primary Cancels ➔ Promote Secondary Overbook to Primary ➔ Clear is_overbooked Flag",
             ha='center', va='center', fontsize=6.8, color='#334155')

    out_file = str(OUT_DIR / "overbooking_and_triage_flow.png")
    fig.savefig(out_file, dpi=220, bbox_inches='tight')
    plt.close(fig)
    print("Flowcharts generated successfully at:", out_file)

if __name__ == "__main__":
    draw_overbooking_and_conflict_flow()
