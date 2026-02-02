"""
Probability-weighted expected value calculations
"""
import yaml
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import setup_logger
from scenario_engine.npv_calculator import NPVCalculator

logger = setup_logger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')


class ProbabilityWeightedAnalysis:
    """Calculate probability-weighted expected NPV and returns"""

    def __init__(self):
        self.calculator = NPVCalculator()
        self.assumptions = self._load_assumptions()

    def _load_assumptions(self) -> Dict:
        """Load gold price scenarios from config"""
        filepath = os.path.join(CONFIG_DIR, 'assumptions.yaml')
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading assumptions: {e}")
            return {}

    def calculate_expected_npv(
        self,
        annual_production_oz: float,
        aisc_per_oz: float,
        discount_rate: float,
        initial_capex: float,
        start_year: int,
        mine_life_years: int,
        scenarios: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Calculate probability-weighted expected NPV across gold price scenarios.

        Args:
            annual_production_oz: Annual production
            aisc_per_oz: All-in sustaining cost
            discount_rate: Discount rate
            initial_capex: Capital expenditure
            start_year: Production start
            mine_life_years: Mine life
            scenarios: Optional custom scenarios (uses config default if not provided)

        Returns:
            Dictionary with expected NPV and scenario details
        """
        if scenarios is None:
            scenarios = self.assumptions.get('gold_price_scenarios', {})

        if not scenarios:
            # Fallback default scenarios
            scenarios = {
                'bear': {'price': 1800, 'probability': 0.20},
                'base': {'price': 2100, 'probability': 0.50},
                'bull': {'price': 2500, 'probability': 0.25},
                'super_bull': {'price': 3000, 'probability': 0.05}
            }

        # Normalize probabilities
        total_prob = sum(s['probability'] for s in scenarios.values())
        if abs(total_prob - 1.0) > 0.01:
            logger.warning(f"Scenario probabilities sum to {total_prob}, normalizing")
            for s in scenarios.values():
                s['probability'] /= total_prob

        # Calculate NPV for each scenario
        scenario_results = {}
        expected_npv = 0
        expected_irr = 0

        for name, scenario in scenarios.items():
            gold_price = scenario['price']
            probability = scenario['probability']

            metrics = self.calculator.calculate_project_metrics(
                gold_price=gold_price,
                annual_production_oz=annual_production_oz,
                aisc_per_oz=aisc_per_oz,
                discount_rate=discount_rate,
                initial_capex=initial_capex,
                start_year=start_year,
                mine_life_years=mine_life_years
            )

            npv = metrics['npv']
            irr = metrics['irr']

            scenario_results[name] = {
                'gold_price': gold_price,
                'probability': probability,
                'npv': npv,
                'npv_millions': npv / 1_000_000,
                'npv_billions': npv / 1_000_000_000,
                'irr': irr,
                'irr_percentage': irr * 100,
                'margin_per_oz': gold_price - aisc_per_oz,
                'weighted_npv': npv * probability,
                'label': scenario.get('label', name.title())
            }

            expected_npv += npv * probability
            expected_irr += irr * probability

        # Calculate variance and standard deviation
        npv_variance = sum(
            s['probability'] * (s['npv'] - expected_npv) ** 2
            for s in scenario_results.values()
        )
        npv_std_dev = npv_variance ** 0.5

        result = {
            'expected_npv': expected_npv,
            'expected_npv_millions': expected_npv / 1_000_000,
            'expected_npv_billions': expected_npv / 1_000_000_000,
            'expected_irr': expected_irr,
            'expected_irr_percentage': expected_irr * 100,

            'npv_std_dev': npv_std_dev,
            'npv_std_dev_millions': npv_std_dev / 1_000_000,
            'coefficient_of_variation': npv_std_dev / expected_npv if expected_npv != 0 else float('inf'),

            'scenarios': scenario_results,

            # Min/Max
            'max_npv': max(s['npv'] for s in scenario_results.values()),
            'min_npv': min(s['npv'] for s in scenario_results.values()),
            'max_npv_millions': max(s['npv_millions'] for s in scenario_results.values()),
            'min_npv_millions': min(s['npv_millions'] for s in scenario_results.values()),

            # Upside/Downside
            'upside_vs_expected': (
                max(s['npv'] for s in scenario_results.values()) / expected_npv - 1
            ) * 100 if expected_npv > 0 else 0,
            'downside_vs_expected': (
                min(s['npv'] for s in scenario_results.values()) / expected_npv - 1
            ) * 100 if expected_npv > 0 else 0,

            # Inputs
            'discount_rate': discount_rate,
            'aisc': aisc_per_oz,
            'production_oz': annual_production_oz,
            'capex_millions': initial_capex / 1_000_000,

            'calculation_time': datetime.now().isoformat()
        }

        logger.info(f"Expected NPV: ${expected_npv/1e9:.2f}B (std dev: ${npv_std_dev/1e9:.2f}B)")
        return result

    def calculate_risk_adjusted_value(
        self,
        expected_npv: float,
        npv_std_dev: float,
        risk_aversion: float = 0.5
    ) -> float:
        """
        Calculate risk-adjusted value using mean-variance framework.

        Args:
            expected_npv: Expected NPV
            npv_std_dev: Standard deviation of NPV
            risk_aversion: Risk aversion parameter (higher = more penalty for risk)

        Returns:
            Risk-adjusted value
        """
        return expected_npv - (risk_aversion * npv_std_dev)

    def compare_expected_values(
        self,
        projects: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compare probability-weighted values across multiple projects.

        Args:
            projects: List of project parameter dictionaries

        Returns:
            Comparison results
        """
        results = []

        for project in projects:
            expected = self.calculate_expected_npv(
                annual_production_oz=project['annual_production_oz'],
                aisc_per_oz=project['aisc_per_oz'],
                discount_rate=project['discount_rate'],
                initial_capex=project['initial_capex'],
                start_year=project['start_year'],
                mine_life_years=project['mine_life_years']
            )

            risk_adjusted = self.calculate_risk_adjusted_value(
                expected['expected_npv'],
                expected['npv_std_dev']
            )

            results.append({
                'name': project.get('name', 'Unknown'),
                'expected_npv_millions': expected['expected_npv_millions'],
                'npv_std_dev_millions': expected['npv_std_dev_millions'],
                'expected_irr_pct': expected['expected_irr_percentage'],
                'risk_adjusted_millions': risk_adjusted / 1_000_000,
                'cv': expected['coefficient_of_variation']
            })

        # Rank by risk-adjusted value
        results.sort(key=lambda x: x['risk_adjusted_millions'], reverse=True)

        return {
            'projects': results,
            'best_risk_adjusted': results[0]['name'] if results else None,
            'comparison_time': datetime.now().isoformat()
        }


# Convenience function
def calculate_expected_npv(
    production_oz: float,
    aisc: float,
    discount_rate: float,
    capex_millions: float,
    start_year: int,
    mine_life: int
) -> Dict[str, Any]:
    """Quick expected NPV calculation"""
    analyzer = ProbabilityWeightedAnalysis()
    return analyzer.calculate_expected_npv(
        annual_production_oz=production_oz,
        aisc_per_oz=aisc,
        discount_rate=discount_rate,
        initial_capex=capex_millions * 1_000_000,
        start_year=start_year,
        mine_life_years=mine_life
    )
