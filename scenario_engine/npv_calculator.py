"""
Core DCF/NPV calculation engine
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from utils.logger import setup_logger

logger = setup_logger(__name__)


class NPVCalculator:
    """Discounted Cash Flow and NPV calculations for mining projects"""

    def __init__(self, tax_rate: float = 0.25):
        self.tax_rate = tax_rate
        self.current_year = datetime.now().year

    def calculate_project_npv(
        self,
        gold_price: float,
        annual_production_oz: float,
        aisc_per_oz: float,
        discount_rate: float,
        initial_capex: float,
        start_year: int,
        mine_life_years: int,
        tax_rate: Optional[float] = None
    ) -> Tuple[float, pd.DataFrame]:
        """
        Calculate NPV for a mining project.

        Args:
            gold_price: Gold price assumption ($/oz)
            annual_production_oz: Annual gold production
            aisc_per_oz: All-in sustaining cost per ounce
            discount_rate: Discount rate (e.g., 0.08 for 8%)
            initial_capex: Initial capital expenditure in dollars
            start_year: Year production begins
            mine_life_years: Years of mine operation
            tax_rate: Optional override for tax rate

        Returns:
            Tuple of (NPV, DataFrame with yearly cash flows)
        """
        tax = tax_rate if tax_rate is not None else self.tax_rate

        # Build yearly cash flows
        years = list(range(start_year, start_year + mine_life_years))
        cash_flows = []

        for year in years:
            # Revenue
            revenue = annual_production_oz * gold_price

            # Operating costs
            operating_cost = annual_production_oz * aisc_per_oz

            # Gross profit
            gross_profit = revenue - operating_cost

            # Tax (only on positive profit)
            tax_expense = max(0, gross_profit * tax)

            # Free cash flow
            fcf = gross_profit - tax_expense

            cash_flows.append({
                'year': year,
                'revenue': revenue,
                'operating_cost': operating_cost,
                'gross_profit': gross_profit,
                'tax_expense': tax_expense,
                'free_cash_flow': fcf
            })

        # Create DataFrame
        df = pd.DataFrame(cash_flows)

        # Calculate discount factors and present values
        df['years_from_now'] = df['year'] - self.current_year
        df['discount_factor'] = (1 + discount_rate) ** -df['years_from_now']
        df['present_value'] = df['free_cash_flow'] * df['discount_factor']

        # Calculate NPV
        pv_operations = df['present_value'].sum()

        # Discount capex (assume spent at start of production)
        years_to_capex = start_year - self.current_year - 1  # Year before production
        capex_discount_factor = (1 + discount_rate) ** -max(0, years_to_capex)
        pv_capex = initial_capex * capex_discount_factor

        npv = pv_operations - pv_capex

        # Add capex row to DataFrame for visualization
        capex_row = pd.DataFrame([{
            'year': start_year - 1,
            'revenue': 0,
            'operating_cost': 0,
            'gross_profit': 0,
            'tax_expense': 0,
            'free_cash_flow': -initial_capex,
            'years_from_now': start_year - 1 - self.current_year,
            'discount_factor': capex_discount_factor,
            'present_value': -pv_capex
        }])

        df = pd.concat([capex_row, df], ignore_index=True)
        df = df.sort_values('year').reset_index(drop=True)

        logger.info(f"Calculated NPV: ${npv/1e9:.2f}B at ${gold_price}/oz gold, {discount_rate*100:.0f}% discount")

        return npv, df

    def calculate_irr(
        self,
        initial_capex: float,
        annual_fcf: float,
        mine_life_years: int
    ) -> float:
        """
        Calculate Internal Rate of Return.

        Args:
            initial_capex: Initial investment
            annual_fcf: Annual free cash flow (simplified as constant)
            mine_life_years: Project duration

        Returns:
            IRR as decimal
        """
        # Build cash flow series: negative capex followed by positive FCFs
        cash_flows = [-initial_capex] + [annual_fcf] * mine_life_years

        try:
            irr = np.irr(cash_flows)
            return irr if not np.isnan(irr) else 0
        except:
            # Fallback calculation using approximation
            total_return = (annual_fcf * mine_life_years) / initial_capex
            if total_return > 0:
                return (total_return ** (1 / mine_life_years)) - 1
            return 0

    def calculate_payback_period(
        self,
        initial_capex: float,
        annual_fcf: float
    ) -> float:
        """
        Calculate simple payback period in years.

        Args:
            initial_capex: Initial investment
            annual_fcf: Annual free cash flow

        Returns:
            Payback period in years
        """
        if annual_fcf <= 0:
            return float('inf')
        return initial_capex / annual_fcf

    def find_breakeven_gold_price(
        self,
        annual_production_oz: float,
        aisc_per_oz: float,
        discount_rate: float,
        initial_capex: float,
        start_year: int,
        mine_life_years: int,
        search_min: float = 1000,
        search_max: float = 2500,
        tolerance: float = 1
    ) -> float:
        """
        Find the gold price where NPV = 0.

        Uses binary search to find breakeven price.

        Args:
            annual_production_oz: Annual production
            aisc_per_oz: Cost per ounce
            discount_rate: Discount rate
            initial_capex: Capex
            start_year: Production start
            mine_life_years: Mine life
            search_min: Minimum search price
            search_max: Maximum search price
            tolerance: Acceptable tolerance in $/oz

        Returns:
            Breakeven gold price
        """
        while search_max - search_min > tolerance:
            mid = (search_min + search_max) / 2
            npv, _ = self.calculate_project_npv(
                gold_price=mid,
                annual_production_oz=annual_production_oz,
                aisc_per_oz=aisc_per_oz,
                discount_rate=discount_rate,
                initial_capex=initial_capex,
                start_year=start_year,
                mine_life_years=mine_life_years
            )

            if npv > 0:
                search_max = mid
            else:
                search_min = mid

        breakeven = (search_min + search_max) / 2
        logger.info(f"Breakeven gold price: ${breakeven:.0f}/oz")
        return breakeven

    def calculate_project_metrics(
        self,
        gold_price: float,
        annual_production_oz: float,
        aisc_per_oz: float,
        discount_rate: float,
        initial_capex: float,
        start_year: int,
        mine_life_years: int
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive project metrics.

        Returns:
            Dictionary with NPV, IRR, payback, breakeven, etc.
        """
        npv, cf_df = self.calculate_project_npv(
            gold_price=gold_price,
            annual_production_oz=annual_production_oz,
            aisc_per_oz=aisc_per_oz,
            discount_rate=discount_rate,
            initial_capex=initial_capex,
            start_year=start_year,
            mine_life_years=mine_life_years
        )

        # Calculate annual FCF for simplified metrics
        annual_revenue = annual_production_oz * gold_price
        annual_cost = annual_production_oz * aisc_per_oz
        annual_fcf = (annual_revenue - annual_cost) * (1 - self.tax_rate)

        irr = self.calculate_irr(initial_capex, annual_fcf, mine_life_years)
        payback = self.calculate_payback_period(initial_capex, annual_fcf)
        breakeven = self.find_breakeven_gold_price(
            annual_production_oz, aisc_per_oz, discount_rate,
            initial_capex, start_year, mine_life_years
        )

        return {
            'npv': npv,
            'npv_billions': npv / 1_000_000_000,
            'npv_millions': npv / 1_000_000,
            'irr': irr,
            'irr_percentage': irr * 100,
            'payback_years': payback,
            'breakeven_gold_price': breakeven,

            # Input assumptions
            'gold_price': gold_price,
            'discount_rate': discount_rate,
            'discount_rate_percentage': discount_rate * 100,
            'annual_production_oz': annual_production_oz,
            'aisc_per_oz': aisc_per_oz,
            'margin_per_oz': gold_price - aisc_per_oz,
            'initial_capex': initial_capex,
            'initial_capex_millions': initial_capex / 1_000_000,
            'start_year': start_year,
            'mine_life_years': mine_life_years,

            # Derived metrics
            'annual_revenue': annual_revenue,
            'annual_revenue_millions': annual_revenue / 1_000_000,
            'annual_fcf': annual_fcf,
            'annual_fcf_millions': annual_fcf / 1_000_000,
            'total_production_oz': annual_production_oz * mine_life_years,
            'npv_per_oz': npv / (annual_production_oz * mine_life_years) if annual_production_oz > 0 else 0,

            # Cash flow data for charts
            'cash_flow_df': cf_df,

            'calculation_time': datetime.now().isoformat()
        }


# Convenience function
def calculate_npv(
    gold_price: float,
    production_oz: float,
    aisc: float,
    discount_rate: float,
    capex_millions: float,
    start_year: int,
    mine_life: int
) -> Dict[str, Any]:
    """Quick NPV calculation"""
    calculator = NPVCalculator()
    return calculator.calculate_project_metrics(
        gold_price=gold_price,
        annual_production_oz=production_oz,
        aisc_per_oz=aisc,
        discount_rate=discount_rate,
        initial_capex=capex_millions * 1_000_000,
        start_year=start_year,
        mine_life_years=mine_life
    )
