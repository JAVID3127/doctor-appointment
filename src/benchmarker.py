import json
import csv
from pathlib import Path
from typing import Dict, List, Any
import numpy as np

from .simulation_engine import MonteCarloOPDSimulator, SimulationDayResult

class OPDBenchmarker:
    """
    Runs paired multi-day Monte Carlo simulations across:
      1. Traditional Fixed Scheduling (No Overbooking)
      2. Naive Static Overbooking (+25%)
      3. Proposed Smart OPD (ML-Aware Overbooking + ESI Triage)
    Computes comparative statistics, variance bounds, and efficiency gains.
    """

    def __init__(self, num_days: int = 30, num_doctors: int = 4, random_seed: int = 42):
        self.num_days = num_days
        self.num_doctors = num_doctors
        self.random_seed = random_seed
        self.simulator = MonteCarloOPDSimulator(num_doctors=num_doctors, random_seed=random_seed)

    def run_benchmark(self) -> Dict[str, Any]:
        results = {
            "fixed": [],
            "naive": [],
            "smart": []
        }

        print(f"🔬 Executing Monte Carlo simulation across {self.num_days} operational days...")

        for day in range(1, self.num_days + 1):
            seed = self.random_seed + day
            res_fixed = self.simulator.run_policy_baseline_fixed(seed)
            res_naive = self.simulator.run_policy_baseline_naive_overbooking(seed)
            res_smart = self.simulator.run_policy_proposed_smart_opd(seed)

            results["fixed"].append(res_fixed)
            results["naive"].append(res_naive)
            results["smart"].append(res_smart)

        summary = self._aggregate_statistics(results)
        return summary

    def _aggregate_statistics(self, results: Dict[str, List[SimulationDayResult]]) -> Dict[str, Any]:
        output = {}

        for key, day_runs in results.items():
            utilizations = [r.doctor_utilization_pct for r in day_runs]
            idles = [r.doctor_idle_minutes for r in day_runs]
            overtimes = [r.doctor_overtime_minutes for r in day_runs]
            attended = [r.total_attended for r in day_runs]
            
            # Combine all patient wait times across the 30 days
            all_waits = [w for r in day_runs for w in r.patient_wait_times]
            all_em_waits = [w for r in day_runs for w in r.emergency_wait_times]

            output[key] = {
                "policy_name": day_runs[0].policy_name,
                "doctor_utilization_mean": round(float(np.mean(utilizations)), 2),
                "doctor_utilization_std": round(float(np.std(utilizations)), 2),
                "doctor_idle_mean": round(float(np.mean(idles)), 2),
                "doctor_idle_std": round(float(np.std(idles)), 2),
                "doctor_overtime_mean": round(float(np.mean(overtimes)), 2),
                "doctor_overtime_std": round(float(np.std(overtimes)), 2),
                "patient_wait_mean": round(float(np.mean(all_waits)), 2),
                "patient_wait_median": round(float(np.median(all_waits)), 2),
                "patient_wait_p90": round(float(np.percentile(all_waits, 90)), 2),
                "emergency_wait_mean": round(float(np.mean(all_em_waits)), 2),
                "emergency_wait_p90": round(float(np.percentile(all_em_waits, 90)), 2),
                "daily_attended_mean": round(float(np.mean(attended)), 2),
                "total_patients_attended": sum(attended),
                "raw_waits": all_waits[:1000]  # Store sample for plotting
            }

        # Calculate percentage comparisons vs Baseline 1 (Fixed)
        fixed = output["fixed"]
        smart = output["smart"]
        naive = output["naive"]

        util_gain_vs_fixed = round(((smart["doctor_utilization_mean"] - fixed["doctor_utilization_mean"]) / fixed["doctor_utilization_mean"]) * 100.0, 1)
        idle_reduction = round(((fixed["doctor_idle_mean"] - smart["doctor_idle_mean"]) / fixed["doctor_idle_mean"]) * 100.0, 1)
        em_wait_reduction = round(((fixed["emergency_wait_mean"] - smart["emergency_wait_mean"]) / fixed["emergency_wait_mean"]) * 100.0, 1)
        wait_penalty_vs_naive = round(((naive["patient_wait_mean"] - smart["patient_wait_mean"]) / naive["patient_wait_mean"]) * 100.0, 1)

        output["comparative_gains"] = {
            "doctor_utilization_increase_vs_fixed_pct": util_gain_vs_fixed,
            "doctor_idle_reduction_pct": idle_reduction,
            "emergency_latency_reduction_pct": em_wait_reduction,
            "patient_wait_savings_vs_naive_pct": wait_penalty_vs_naive,
            "additional_patients_treated_per_day": round(smart["daily_attended_mean"] - fixed["daily_attended_mean"], 1)
        }

        return output

    def export_results(self, summary: Dict[str, Any], output_dir: Path):
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. JSON Export
        json_path = output_dir / "simulation_results.json"
        with open(json_path, "w") as f:
            json.dump(summary, f, indent=2)

        # 2. CSV Summary Export
        csv_path = output_dir / "benchmark_summary.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Policy Name",
                "Doctor Utilization (%)",
                "Doctor Idle (mins/day)",
                "Avg Patient Wait (mins)",
                "90th Percentile Wait (mins)",
                "Clinic Overtime (mins/day)",
                "Emergency Wait (mins)",
                "Total Attended (30 Days)"
            ])
            for key in ["fixed", "naive", "smart"]:
                p = summary[key]
                writer.writerow([
                    p["policy_name"],
                    f"{p['doctor_utilization_mean']} ± {p['doctor_utilization_std']}",
                    f"{p['doctor_idle_mean']} ± {p['doctor_idle_std']}",
                    p["patient_wait_mean"],
                    p["patient_wait_p90"],
                    f"{p['doctor_overtime_mean']} ± {p['doctor_overtime_std']}",
                    p["emergency_wait_mean"],
                    p["total_patients_attended"]
                ])

        print(f"✅ Benchmark results exported to {json_path} and {csv_path}")
