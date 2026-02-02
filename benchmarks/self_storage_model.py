"""
Self-storage benchmark model for control comparison
"""
import yaml
import os
from typing import Dict, Any, Optional
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')


class SelfStorageModel:
    """
    Models self-storage development as a control investment benchmark.

    Used to compare mining investments against a high-control,
    stable alternative investment.
    """

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load benchmark configuration"""
        filepath = os.path.join(CONFIG_DIR, 'benchmarks.yaml')
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading benchmarks config: {e}")
            return {}

    def get_benchmark_returns(self) -> Dict[str, Any]:
        """
        Get self-storage benchmark return metrics.

        Returns:
            Dictionary with benchmark returns and characteristics
        """
        ss_config = self.config.get('self_storage', {})
        returns = ss_config.get('returns', {})
        timeline = ss_config.get('timeline', {})

        return {
            'name': ss_config.get('name', 'Self-Storage Development'),
            'description': ss_config.get('description', ''),

            # Returns
            'irr': returns.get('irr', 0.18),
            'irr_percentage': returns.get('irr', 0.18) * 100,
            'cash_on_cash_year1': returns.get('cash_on_cash_year1', 0.08),
            'stabilized_yield': returns.get('stabilized_yield', 0.12),

            # Timeline
            'development_months': timeline.get('development_months', 18),
            'lease_up_months': timeline.get('lease_up_months', 12),
            'total_to_stabilization': timeline.get('total_to_stabilization', 30),
            'hold_period_years': timeline.get('hold_period_years', 5),

            # Risk characteristics
            'risk_profile': ss_config.get('risk_profile', {}),

            # Advantages/Disadvantages for display
            'advantages': ss_config.get('advantages', []),
            'disadvantages': ss_config.get('disadvantages', [])
        }

    def get_control_factor(self, ticker: Optional[str] = None) -> float:
        """
        Get control factor for a company or default.

        Control factor represents the "penalty" for lack of control
        vs a fully controlled investment like self-storage.

        Args:
            ticker: Optional company ticker for company-specific factor

        Returns:
            Control factor (0.10-0.50)
        """
        control_config = self.config.get('control_factors', {})
        base = control_config.get('base', 0.25)

        # Could implement company-specific adjustments here
        # For now, return base factor
        return base

    def calculate_control_adjustment(
        self,
        mining_return: float,
        control_factor: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate control-adjusted return for a mining investment.

        Formula: Adjusted Return = Mining Return - (Control Factor * Benchmark IRR)

        Args:
            mining_return: Expected return from mining investment (as decimal)
            control_factor: Optional override for control factor

        Returns:
            Dictionary with adjusted return calculation
        """
        benchmark = self.get_benchmark_returns()
        factor = control_factor if control_factor is not None else self.get_control_factor()

        control_penalty = factor * benchmark['irr']
        adjusted_return = mining_return - control_penalty

        return {
            'mining_return': mining_return,
            'mining_return_pct': mining_return * 100,
            'benchmark_irr': benchmark['irr'],
            'benchmark_irr_pct': benchmark['irr_percentage'],
            'control_factor': factor,
            'control_penalty': control_penalty,
            'control_penalty_pct': control_penalty * 100,
            'adjusted_return': adjusted_return,
            'adjusted_return_pct': adjusted_return * 100,

            # Interpretation
            'beats_benchmark': adjusted_return > 0,
            'excess_vs_benchmark': adjusted_return,
            'excess_vs_benchmark_pct': adjusted_return * 100
        }

    def get_hurdle_rates(self) -> Dict[str, float]:
        """
        Get hurdle rates for investment decisions.

        Returns:
            Dictionary with hurdle rates
        """
        hurdles = self.config.get('hurdle_rates', {})
        return {
            'minimum_adjusted_return': hurdles.get('minimum_adjusted_return', 0.15),
            'minimum_raw_return': hurdles.get('minimum_raw_return', 0.25),
            'maximum_acceptable_risk_score': hurdles.get('maximum_acceptable_risk_score', 2.0)
        }

    def get_alternative_benchmarks(self) -> Dict[str, Dict]:
        """
        Get alternative benchmark comparisons.

        Returns:
            Dictionary of benchmark name -> characteristics
        """
        return self.config.get('alternative_benchmarks', {})

    def compare_to_alternatives(self, mining_return: float) -> Dict[str, Any]:
        """
        Compare mining return to all alternative benchmarks.

        Args:
            mining_return: Expected mining return

        Returns:
            Comparison against all benchmarks
        """
        alternatives = self.get_alternative_benchmarks()
        comparisons = {}

        for name, benchmark in alternatives.items():
            expected = benchmark.get('expected_return', 0)
            comparisons[name] = {
                'name': benchmark.get('name', name),
                'expected_return': expected,
                'expected_return_pct': expected * 100,
                'mining_excess': mining_return - expected,
                'mining_excess_pct': (mining_return - expected) * 100,
                'beats_benchmark': mining_return > expected,
                'volatility': benchmark.get('volatility', 0),
                'leverage_to_gold': benchmark.get('leverage_to_gold', 1.0)
            }

        return {
            'mining_return': mining_return,
            'mining_return_pct': mining_return * 100,
            'comparisons': comparisons,
            'beats_all': all(c['beats_benchmark'] for c in comparisons.values()),
            'best_alternative': max(comparisons.items(), key=lambda x: x[1]['expected_return'])[0]
        }


# Convenience functions
def get_benchmark_irr() -> float:
    """Get self-storage benchmark IRR"""
    model = SelfStorageModel()
    return model.get_benchmark_returns()['irr']


def calculate_control_adjusted(mining_return: float, control_factor: float = 0.25) -> float:
    """Calculate control-adjusted return"""
    model = SelfStorageModel()
    result = model.calculate_control_adjustment(mining_return, control_factor)
    return result['adjusted_return']
