"""
Scenario Engine Module
NPV calculations, sensitivity analysis, and probability weighting
"""
from scenario_engine.npv_calculator import NPVCalculator, calculate_npv
from scenario_engine.sensitivity_matrix import SensitivityMatrix, generate_sensitivity_matrix
from scenario_engine.probability_weighting import ProbabilityWeightedAnalysis, calculate_expected_npv

__all__ = [
    'NPVCalculator',
    'calculate_npv',
    'SensitivityMatrix',
    'generate_sensitivity_matrix',
    'ProbabilityWeightedAnalysis',
    'calculate_expected_npv'
]
