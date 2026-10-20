import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

from src.benchmarker import OPDBenchmarker
from src.chart_generator import generate_benchmark_charts

def main():
    print("=" * 75)
    print("🏥 SMART OPD SCHEDULING SYSTEM - WEEK 7 FINAL MONTE CARLO BENCHMARK")
    print("=" * 75)
    print("Simulating 30 operational days across 4 specialized OPD consultation units...")
    print("Testing 3 Policies: Fixed Traditional vs Naive Overbooking vs Proposed Smart OPD\n")

    benchmarker = OPDBenchmarker(num_days=30, num_doctors=4, random_seed=42)
    summary = benchmarker.run_benchmark()

    # Export metrics
    data_dir = ROOT_DIR / "data"
    docs_dir = ROOT_DIR / "docs"
    benchmarker.export_results(summary, data_dir)

    # Generate charts
    print("\n📊 Generating publication-quality comparative benchmark charts...")
    generate_benchmark_charts(summary, docs_dir)

    # Display console comparison table
    fixed = summary["fixed"]
    naive = summary["naive"]
    smart = summary["smart"]
    gains = summary["comparative_gains"]

    print("\n" + "=" * 78)
    print(f"{'OPERATIONAL METRIC':<32} | {'FIXED TRADITIONAL':<13} | {'NAIVE +25%':<12} | {'SMART OPD':<12}")
    print("=" * 78)
    print(f"{'Doctor Utilization (%)':<32} | {fixed['doctor_utilization_mean']:>11.1f}% | {naive['doctor_utilization_mean']:>10.1f}% | {smart['doctor_utilization_mean']:>10.1f}%")
    print(f"{'Doctor Idle Downtime (mins/day)':<32} | {fixed['doctor_idle_mean']:>11.1f}m | {naive['doctor_idle_mean']:>10.1f}m | {smart['doctor_idle_mean']:>10.1f}m")
    print(f"{'Average Patient Wait Time (mins)':<32} | {fixed['patient_wait_mean']:>11.1f}m | {naive['patient_wait_mean']:>10.1f}m | {smart['patient_wait_mean']:>10.1f}m")
    print(f"{'90th Percentile Wait Time (mins)':<32} | {fixed['patient_wait_p90']:>11.1f}m | {naive['patient_wait_p90']:>10.1f}m | {smart['patient_wait_p90']:>10.1f}m")
    print(f"{'Clinic Overtime (mins/day)':<32} | {fixed['doctor_overtime_mean']:>11.1f}m | {naive['doctor_overtime_mean']:>10.1f}m | {smart['doctor_overtime_mean']:>10.1f}m")
    print(f"{'Emergency Response Latency (mins)':<32} | {fixed['emergency_wait_mean']:>11.1f}m | {naive['emergency_wait_mean']:>10.1f}m | {smart['emergency_wait_mean']:>10.1f}m")
    print(f"{'Total Patients Treated (30 Days)':<32} | {fixed['total_patients_attended']:>12} | {naive['total_patients_attended']:>12} | {smart['total_patients_attended']:>12}")
    print("=" * 78)

    print("\n🎯 KEY EMPIRICAL FINDINGS & EFFICIENCY GAINS:")
    print(f"  • Doctor Utilization:    +{gains['doctor_utilization_increase_vs_fixed_pct']}% relative increase vs Fixed Traditional.")
    print(f"  • Idle Downtime Eliminated: -{gains['doctor_idle_reduction_pct']}% reduction in wasted doctor consultation slots.")
    print(f"  • Patient Wait Protection:  -{gains['patient_wait_savings_vs_naive_pct']}% less waiting time compared to Naive Overbooking.")
    print(f"  • Emergency Life Safety:    -{gains['emergency_latency_reduction_pct']}% reduction in critical triage delay via ESI preemption.")
    print(f"  • Additional Throughput:    +{gains['additional_patients_treated_per_day']} additional outpatients served per doctor-day.")
    print("=" * 78)
    print(f"📁 Benchmark Data:  {data_dir / 'benchmark_summary.csv'}")
    print(f"📈 Comparison Plot: {docs_dir / 'benchmark_comparison.png'}")
    print(f"📉 Trade-off Plot:  {docs_dir / 'tradeoff_curve.png'}")
    print("=" * 78)

if __name__ == "__main__":
    main()
