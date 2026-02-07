"""
Benchmarks Module
Self-storage and alternative investment comparisons
"""
from benchmarks.self_storage_model import SelfStorageModel, get_benchmark_irr, calculate_control_adjusted
from benchmarks.adjusted_return import AdjustedReturnCalculator, get_adjusted_return, compare_miners

__all__ = [
    'SelfStorageModel',
    'get_benchmark_irr',
    'calculate_control_adjusted',
    'AdjustedReturnCalculator',
    'get_adjusted_return',
    'compare_miners'
]
