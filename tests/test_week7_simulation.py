import pytest
import numpy as np
from src.simulation_engine import MonteCarloOPDSimulator, SimulationDayResult
from src.benchmarker import OPDBenchmarker

def test_simulator_patient_generation():
    sim = MonteCarloOPDSimulator(num_doctors=4, clinic_hours=7.0, random_seed=42)
    patients = sim.generate_day_patients(day_seed=101)
    
    # 4 doctors * 28 slots = 112 base appointments + ~4-8 emergencies
    assert len(patients) >= 112
    scheduled = [p for p in patients if not p.is_emergency]
    emergencies = [p for p in patients if p.is_emergency]

    assert len(scheduled) == 112
    assert len(emergencies) > 0

    for p in scheduled:
        assert 18 <= p.age <= 85
        assert 0.0 <= p.predicted_no_show_prob <= 1.0
        assert 5.0 <= p.consultation_duration <= 40.0

def test_policy_fixed_execution():
    sim = MonteCarloOPDSimulator(num_doctors=4, clinic_hours=7.0, random_seed=42)
    res = sim.run_policy_baseline_fixed(day_seed=101)

    assert isinstance(res, SimulationDayResult)
    assert res.total_booked == 112
    assert res.total_attended > 0
    assert res.total_no_shows > 0
    assert 50.0 <= res.doctor_utilization_pct <= 95.0
    assert res.doctor_idle_minutes > 0.0

def test_policy_smart_opd_improvements():
    sim = MonteCarloOPDSimulator(num_doctors=4, clinic_hours=7.0, random_seed=42)
    res_fixed = sim.run_policy_baseline_fixed(day_seed=101)
    res_smart = sim.run_policy_proposed_smart_opd(day_seed=101)

    # Smart OPD should achieve higher or equal doctor utilization
    assert res_smart.doctor_utilization_pct >= res_fixed.doctor_utilization_pct
    # Smart OPD should drastically reduce doctor idle downtime
    assert res_smart.doctor_idle_minutes < res_fixed.doctor_idle_minutes
    # Smart OPD should preempt emergencies and reduce emergency wait time
    assert res_smart.avg_emergency_wait_minutes <= res_fixed.avg_emergency_wait_minutes

def test_simulation_reproducibility():
    sim1 = MonteCarloOPDSimulator(num_doctors=2, clinic_hours=4.0, random_seed=99)
    sim2 = MonteCarloOPDSimulator(num_doctors=2, clinic_hours=4.0, random_seed=99)

    res1 = sim1.run_policy_proposed_smart_opd(day_seed=555)
    res2 = sim2.run_policy_proposed_smart_opd(day_seed=555)

    assert res1.total_attended == res2.total_attended
    assert res1.doctor_utilization_pct == res2.doctor_utilization_pct
    assert res1.doctor_idle_minutes == res2.doctor_idle_minutes

def test_benchmarker_aggregation():
    benchmarker = OPDBenchmarker(num_days=3, num_doctors=2, random_seed=42)
    summary = benchmarker.run_benchmark()

    assert "fixed" in summary
    assert "naive" in summary
    assert "smart" in summary
    assert "comparative_gains" in summary

    gains = summary["comparative_gains"]
    assert gains["doctor_utilization_increase_vs_fixed_pct"] > 0
    assert gains["doctor_idle_reduction_pct"] > 0
