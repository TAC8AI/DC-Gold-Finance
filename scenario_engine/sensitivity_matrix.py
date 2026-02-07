"""
Sensitivity analysis: Gold price x Discount rate matrix
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from utils.logger import setup_logger
from scenario_engine.npv_calculator import NPVCalculator

logger = setup_logger(__name__)


class SensitivityMatrix:
    """Generates sensitivity analysis for NPV across multiple variables"""

    def __init__(self):
        self.calculator = NPVCalculator()

    def generate_gold_discount_matrix(
        self,
        annual_production_oz: float,
        aisc_per_oz: float,
        initial_capex: float,
        start_year: int,
        mine_life_years: int,
        gold_prices: Optional[List[float]] = None,
        discount_rates: Optional[List[float]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate NPV sensitivity matrix for gold price vs discount rate.

        Args:
            annual_production_oz: Annual production
            aisc_per_oz: All-in sustaining cost
            initial_capex: Capital expenditure
            start_year: Production start year
            mine_life_years: Mine life
            gold_prices: List of gold prices to test
            discount_rates: List of discount rates to test

        Returns:
            Tuple of (DataFrame with matrix, metadata dict)
        """
        # Default ranges if not specified
        if gold_prices is None:
            gold_prices = [1600, 1800, 2000, 2200, 2400, 2600, 2800, 3000]

        if discount_rates is None:
            discount_rates = [0.05, 0.08, 0.10, 0.12]

        # Build matrix
        matrix_data = []

        for rate in discount_rates:
            row = {}
            for gold in gold_prices:
                npv, _ = self.calculator.calculate_project_npv(
                    gold_price=gold,
                    annual_production_oz=annual_production_oz,
                    aisc_per_oz=aisc_per_oz,
                    discount_rate=rate,
                    initial_capex=initial_capex,
                    start_year=start_year,
                    mine_life_years=mine_life_years
                )
                row[f"${gold:,.0f}"] = npv / 1_000_000  # In millions

            matrix_data.append(row)

        # Create DataFrame with discount rate labels as index
        df = pd.DataFrame(
            matrix_data,
            index=[f"{r*100:.0f}%" for r in discount_rates]
        )

        # Calculate metadata
        max_npv = df.max().max()
        min_npv = df.min().min()

        # Find breakeven points for each discount rate
        breakevens = {}
        for rate in discount_rates:
            breakeven = self.calculator.find_breakeven_gold_price(
                annual_production_oz=annual_production_oz,
                aisc_per_oz=aisc_per_oz,
                discount_rate=rate,
                initial_capex=initial_capex,
                start_year=start_year,
                mine_life_years=mine_life_years
            )
            breakevens[f"{rate*100:.0f}%"] = breakeven

        metadata = {
            'gold_prices': gold_prices,
            'discount_rates': discount_rates,
            'max_npv_millions': max_npv,
            'min_npv_millions': min_npv,
            'breakeven_by_discount': breakevens,
            'aisc': aisc_per_oz,
            'production_oz': annual_production_oz,
            'capex_millions': initial_capex / 1_000_000,
            'generation_time': datetime.now().isoformat()
        }

        logger.info(f"Generated {len(discount_rates)}x{len(gold_prices)} sensitivity matrix")
        return df, metadata

    def generate_aisc_gold_matrix(
        self,
        annual_production_oz: float,
        discount_rate: float,
        initial_capex: float,
        start_year: int,
        mine_life_years: int,
        gold_prices: Optional[List[float]] = None,
        aisc_values: Optional[List[float]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate NPV sensitivity matrix for gold price vs AISC.

        Args:
            annual_production_oz: Annual production
            discount_rate: Discount rate
            initial_capex: Capital expenditure
            start_year: Production start year
            mine_life_years: Mine life
            gold_prices: List of gold prices to test
            aisc_values: List of AISC values to test

        Returns:
            Tuple of (DataFrame with matrix, metadata dict)
        """
        if gold_prices is None:
            gold_prices = [1800, 2000, 2200, 2400, 2600, 2800]

        if aisc_values is None:
            aisc_values = [800, 1000, 1200, 1400, 1600]

        matrix_data = []

        for aisc in aisc_values:
            row = {}
            for gold in gold_prices:
                npv, _ = self.calculator.calculate_project_npv(
                    gold_price=gold,
                    annual_production_oz=annual_production_oz,
                    aisc_per_oz=aisc,
                    discount_rate=discount_rate,
                    initial_capex=initial_capex,
                    start_year=start_year,
                    mine_life_years=mine_life_years
                )
                row[f"${gold:,.0f}"] = npv / 1_000_000

            matrix_data.append(row)

        df = pd.DataFrame(
            matrix_data,
            index=[f"${aisc:,.0f}" for aisc in aisc_values]
        )

        metadata = {
            'gold_prices': gold_prices,
            'aisc_values': aisc_values,
            'discount_rate': discount_rate,
            'max_npv_millions': df.max().max(),
            'min_npv_millions': df.min().min(),
            'generation_time': datetime.now().isoformat()
        }

        return df, metadata

    def generate_production_capex_matrix(
        self,
        gold_price: float,
        aisc_per_oz: float,
        discount_rate: float,
        start_year: int,
        mine_life_years: int,
        production_values: Optional[List[float]] = None,
        capex_values: Optional[List[float]] = None
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Generate NPV sensitivity for production vs capex.

        Returns:
            Tuple of (DataFrame, metadata)
        """
        if production_values is None:
            production_values = [100000, 150000, 200000, 250000, 300000]

        if capex_values is None:
            capex_values = [200e6, 300e6, 400e6, 500e6, 600e6]

        matrix_data = []

        for capex in capex_values:
            row = {}
            for prod in production_values:
                npv, _ = self.calculator.calculate_project_npv(
                    gold_price=gold_price,
                    annual_production_oz=prod,
                    aisc_per_oz=aisc_per_oz,
                    discount_rate=discount_rate,
                    initial_capex=capex,
                    start_year=start_year,
                    mine_life_years=mine_life_years
                )
                row[f"{prod/1000:.0f}K oz"] = npv / 1_000_000

            matrix_data.append(row)

        df = pd.DataFrame(
            matrix_data,
            index=[f"${c/1e6:.0f}M" for c in capex_values]
        )

        metadata = {
            'production_values': production_values,
            'capex_values': capex_values,
            'gold_price': gold_price,
            'aisc': aisc_per_oz,
            'discount_rate': discount_rate,
            'generation_time': datetime.now().isoformat()
        }

        return df, metadata

    def find_value_drivers(
        self,
        base_params: Dict[str, Any],
        variation_pct: float = 0.10
    ) -> Dict[str, Dict[str, float]]:
        """
        Identify which variables have the biggest impact on NPV.

        Args:
            base_params: Base case parameters
            variation_pct: Percentage to vary each parameter

        Returns:
            Dictionary showing NPV sensitivity to each variable
        """
        # Calculate base NPV
        base_npv, _ = self.calculator.calculate_project_npv(**base_params)

        sensitivities = {}
        variables = ['gold_price', 'annual_production_oz', 'aisc_per_oz',
                    'discount_rate', 'initial_capex', 'mine_life_years']

        for var in variables:
            if var not in base_params:
                continue

            base_value = base_params[var]

            # Calculate NPV at +/- variation
            params_up = base_params.copy()
            params_down = base_params.copy()

            if var == 'aisc_per_oz' or var == 'discount_rate' or var == 'initial_capex':
                # For costs, higher is worse
                params_up[var] = base_value * (1 + variation_pct)
                params_down[var] = base_value * (1 - variation_pct)
            else:
                params_up[var] = base_value * (1 + variation_pct)
                params_down[var] = base_value * (1 - variation_pct)

            npv_up, _ = self.calculator.calculate_project_npv(**params_up)
            npv_down, _ = self.calculator.calculate_project_npv(**params_down)

            sensitivities[var] = {
                'base_value': base_value,
                'base_npv': base_npv / 1e6,
                'npv_up': npv_up / 1e6,
                'npv_down': npv_down / 1e6,
                'npv_range': (npv_up - npv_down) / 1e6,
                'npv_change_pct_up': (npv_up - base_npv) / base_npv * 100,
                'npv_change_pct_down': (npv_down - base_npv) / base_npv * 100,
                'sensitivity': abs(npv_up - npv_down) / (2 * base_npv) * 100  # % NPV change per 10% variable change
            }

        # Sort by sensitivity
        sensitivities = dict(sorted(
            sensitivities.items(),
            key=lambda x: x[1]['sensitivity'],
            reverse=True
        ))

        return sensitivities


# Convenience function
def generate_sensitivity_matrix(
    production_oz: float,
    aisc: float,
    capex_millions: float,
    start_year: int,
    mine_life: int,
    gold_prices: Optional[List[float]] = None,
    discount_rates: Optional[List[float]] = None
) -> Tuple[pd.DataFrame, Dict]:
    """Quick sensitivity matrix generation"""
    matrix = SensitivityMatrix()
    return matrix.generate_gold_discount_matrix(
        annual_production_oz=production_oz,
        aisc_per_oz=aisc,
        initial_capex=capex_millions * 1_000_000,
        start_year=start_year,
        mine_life_years=mine_life,
        gold_prices=gold_prices,
        discount_rates=discount_rates
    )
