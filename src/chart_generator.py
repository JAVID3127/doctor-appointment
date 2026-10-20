import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from typing import Dict, Any

def generate_benchmark_charts(summary: Dict[str, Any], output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Visual aesthetics
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.edgecolor"] = "#cbd5e1"
    plt.rcParams["axes.linewidth"] = 0.8

    policies = ["Traditional Fixed\n(No Overbooking)", "Naive Static\n(+25% Overbook)", "Proposed Smart OPD\n(ML + ESI Triage)"]
    keys = ["fixed", "naive", "smart"]
    colors = ["#64748b", "#f59e0b", "#10b981"]

    # =========================================================================
    # CHART 1: 4-Panel Comparative Bar Chart
    # =========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), dpi=300)
    fig.patch.set_facecolor("#f8fafc")
    for ax in axes.flat:
        ax.set_facecolor("#ffffff")
        ax.grid(axis="y", linestyle="--", alpha=0.5, color="#e2e8f0")

    # Panel 1: Doctor Utilization (%)
    ax1 = axes[0, 0]
    utils = [summary[k]["doctor_utilization_mean"] for k in keys]
    errs = [summary[k]["doctor_utilization_std"] for k in keys]
    bars1 = ax1.bar(policies, utils, yerr=errs, capsize=5, color=colors, width=0.55, edgecolor="#0f172a", linewidth=1)
    ax1.set_title("Doctor Utilization Rate (%) [Higher is Better]", fontsize=12, fontweight="bold", pad=12, color="#0f172a")
    ax1.set_ylabel("Utilization (%)", fontsize=10, color="#475569")
    ax1.set_ylim(0, 105)
    for b in bars1:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width() / 2, h + 3, f"{h:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    # Panel 2: Doctor Idle Downtime (Minutes / Day)
    ax2 = axes[0, 1]
    idles = [summary[k]["doctor_idle_mean"] for k in keys]
    bars2 = ax2.bar(policies, idles, color=colors, width=0.55, edgecolor="#0f172a", linewidth=1)
    ax2.set_title("Doctor Idle Downtime (Mins/Day) [Lower is Better]", fontsize=12, fontweight="bold", pad=12, color="#0f172a")
    ax2.set_ylabel("Idle Minutes", fontsize=10, color="#475569")
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width() / 2, h + 8, f"{h:.0f}m", ha="center", va="bottom", fontsize=10, fontweight="bold")

    # Panel 3: Patient Average Wait Time (Minutes)
    ax3 = axes[1, 0]
    waits = [summary[k]["patient_wait_mean"] for k in keys]
    bars3 = ax3.bar(policies, waits, color=colors, width=0.55, edgecolor="#0f172a", linewidth=1)
    ax3.set_title("Patient Average Wait Time (Minutes) [Lower is Better]", fontsize=12, fontweight="bold", pad=12, color="#0f172a")
    ax3.set_ylabel("Wait Time (mins)", fontsize=10, color="#475569")
    for b in bars3:
        h = b.get_height()
        ax3.text(b.get_x() + b.get_width() / 2, h + 1, f"{h:.1f}m", ha="center", va="bottom", fontsize=10, fontweight="bold")

    # Panel 4: Emergency Response Latency (Minutes)
    ax4 = axes[1, 1]
    em_waits = [summary[k]["emergency_wait_mean"] for k in keys]
    bars4 = ax4.bar(policies, em_waits, color=colors, width=0.55, edgecolor="#0f172a", linewidth=1)
    ax4.set_title("Emergency Care Response Time (Mins) [Critical Acuity]", fontsize=12, fontweight="bold", pad=12, color="#0f172a")
    ax4.set_ylabel("Response Delay (mins)", fontsize=10, color="#475569")
    for b in bars4:
        h = b.get_height()
        ax4.text(b.get_x() + b.get_width() / 2, h + 0.6, f"{h:.1f}m", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.suptitle("Smart Hospital OPD Scheduling System - 30-Day Monte Carlo Benchmark", fontsize=16, fontweight="bold", y=0.98, color="#0f172a")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    chart1_path = output_dir / "benchmark_comparison.png"
    plt.savefig(chart1_path, dpi=300)
    plt.close()
    print(f"✅ Generated Benchmark Comparison Chart: {chart1_path}")

    # =========================================================================
    # CHART 2: Pareto Efficiency Frontier & Wait Time Distribution
    # =========================================================================
    fig2, (ax_trade, ax_cdf) = plt.subplots(1, 2, figsize=(15, 6), dpi=300)
    fig2.patch.set_facecolor("#f8fafc")
    ax_trade.set_facecolor("#ffffff")
    ax_cdf.set_facecolor("#ffffff")
    ax_trade.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
    ax_cdf.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")

    # Trade-off Frontier Plot
    p_x = [summary[k]["doctor_idle_mean"] for k in keys]
    p_y = [summary[k]["patient_wait_mean"] for k in keys]
    labels = ["Traditional Fixed\n(High Doctor Idle Time)", "Naive Overbooking\n(Severe Patient Congestion)", "Smart OPD Sweet Spot\n(Pareto-Optimal Frontier)"]

    for x, y, label, c in zip(p_x, p_y, labels, colors):
        ax_trade.scatter(x, y, s=280, color=c, edgecolor="#0f172a", linewidth=1.5, zorder=5)
        offset_y = 1.5 if "Naive" in label else -2.5
        ax_trade.annotate(label, xy=(x, y), xytext=(x - 30, y + offset_y),
                          fontsize=9.5, fontweight="bold", color="#1e293b",
                          arrowprops=dict(arrowstyle="->", color="#64748b", lw=1.2))

    # Curve connecting trade-off
    curve_x = np.linspace(min(p_x) - 10, max(p_x) + 20, 100)
    # Hyperbolic frontier curve fit: Wait * Idle ~ C
    c_val = summary["smart"]["doctor_idle_mean"] * summary["smart"]["patient_wait_mean"]
    curve_y = c_val / curve_x
    ax_trade.plot(curve_x, curve_y, "--", color="#94a3b8", label="Theoretical Operational Frontier", zorder=2)

    ax_trade.set_title("Doctor Idle Time vs. Patient Wait Time Trade-off", fontsize=12, fontweight="bold", color="#0f172a")
    ax_trade.set_xlabel("Doctor Idle Downtime (mins/day) [→ Worse]", fontsize=10, color="#475569")
    ax_trade.set_ylabel("Patient Wait Time (mins) [↑ Worse]", fontsize=10, color="#475569")
    ax_trade.legend(loc="upper right", fontsize=9)

    # Empirical CDF of Patient Wait Times
    for k, c, name in zip(keys, colors, ["Traditional Fixed", "Naive Overbooking", "Smart OPD"]):
        waits = np.sort(summary[k]["raw_waits"])
        cdf = np.arange(1, len(waits) + 1) / len(waits)
        ax_cdf.plot(waits, cdf, label=name, color=c, linewidth=2.5)

    ax_cdf.axvline(30, color="#ef4444", linestyle=":", label="30-min Tolerance Threshold")
    ax_cdf.set_title("Patient Wait Time Distribution (CDF)", fontsize=12, fontweight="bold", color="#0f172a")
    ax_cdf.set_xlabel("Wait Time (minutes)", fontsize=10, color="#475569")
    ax_cdf.set_ylabel("Cumulative Probability P(Wait ≤ t)", fontsize=10, color="#475569")
    ax_cdf.set_xlim(0, 75)
    ax_cdf.legend(loc="lower right", fontsize=9)

    plt.suptitle("Healthcare Operational Efficiency & Queue Stability Analysis", fontsize=15, fontweight="bold", y=0.98, color="#0f172a")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])

    chart2_path = output_dir / "tradeoff_curve.png"
    plt.savefig(chart2_path, dpi=300)
    plt.close()
    print(f"✅ Generated Trade-off & CDF Chart: {chart2_path}")
