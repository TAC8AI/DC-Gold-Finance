"""
Control-adjusted return calculations for mining investments
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import setup_logger
from benchmarks.self_storage_model import SelfStorageModel
from scenario_engine.probability_weighting import ProbabilityWeightedAnalysis
from data_ingestion.data_normalizer import DataNormalizer

logger = setup_logger(__name__)


class AdjustedReturnCalculator:
    """
    Calculates control-adjusted returns for mining investments.

    Compares mining expected returns against a control benchmark
    (self-storage development) to determine if the extra risk
    of mining is adequately compensated.
    """

    def __init__(self):
        self.benchmark = SelfStorageModel()
        self.npv_analyzer = ProbabilityWeightedAnalysis()
        self.normalizer = DataNormalizer()

    def calculate_mining_expected_return(
        self,
        ticker: str,
        discount_rate: float = 0.08
    ) -> Dict[str, Any]:
        """
        Calculate expected return for a mining investment.

        Uses NPV analysis and current market cap to derive implied return.

        Args:
            ticker: Company ticker symbol
            discount_rate: Discount rate for NPV calculation

        Returns:
            Dictionary with expected return metrics
        """
        # Get company data
        company_data = self.normalizer.get_normalized_company_data(ticker)

        if 'error' in company_data:
            return {'ticker': ticker, 'error': company_data['error']}

        project = company_data.get('project', {})
        market = company_data.get('market', {})

        # Calculate expected NPV
        expected_analysis = self.npv_analyzer.calculate_expected_npv(
            annual_production_oz=project.get('annual_production_oz', 0),
            aisc_per_oz=project.get('aisc_per_oz', 0),
            discount_rate=discount_rate,
            initial_capex=project.get('initial_capex_millions', 0) * 1_000_000,
            start_year=project.get('production_start_year', 2030),
            mine_life_years=project.get('mine_life_years', 15)
        )

        expected_npv = expected_analysis['expected_npv']
        market_cap = market.get('market_cap', 0)

        # Calculate implied return
        if market_cap > 0:
            # Upside = (Expected NPV / Current Market Cap) - 1
            implied_upside = (expected_npv / market_cap) - 1

            # Annualize based on years to production
            years_to_production = company_data.get('calculated', {}).get('years_to_production', 4)

            if years_to_production > 0 and implied_upside > -1:
                annualized_return = (1 + implied_upside) ** (1 / years_to_production) - 1
            else:
                annualized_return = implied_upside  # Fallback
        else:
            implied_upside = 0
            annualized_return = 0

        return {
            'ticker': ticker,
            'company_name': company_data.get('name', ticker),

            # Expected NPV
            'expected_npv': expected_npv,
            'expected_npv_millions': expected_npv / 1_000_000,
            'expected_npv_billions': expected_npv / 1_000_000_000,

            # Market valuation
            'market_cap': market_cap,
            'market_cap_millions': market_cap / 1_000_000,

            # Implied returns
            'implied_upside': implied_upside,
            'implied_upside_pct': implied_upside * 100,
            'annualized_return': annualized_return,
            'annualized_return_pct': annualized_return * 100,

            # Timeline
            'years_to_production': company_data.get('calculated', {}).get('years_to_production', 0),

            # Project details
            'project': project.get('name', 'Unknown'),
            'stage': project.get('stage', 'unknown'),

            'calculation_time': datetime.now().isoformat()
        }

    def calculate_adjusted_return(
        self,
        ticker: str,
        discount_rate: float = 0.08,
        control_factor: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate control-adjusted return for a mining investment.

        Args:
            ticker: Company ticker symbol
            discount_rate: Discount rate for NPV
            control_factor: Optional override (uses company default if not provided)

        Returns:
            Dictionary with adjusted return analysis
        """
        # Get mining expected return
        mining_return = self.calculate_mining_expected_return(ticker, discount_rate)

        if 'error' in mining_return:
            return mining_return

        # Get control factor
        company_data = self.normalizer.get_normalized_company_data(ticker)
        factor = control_factor if control_factor is not None else company_data.get('control_factor', 0.25)

        # Calculate control-adjusted return
        adjustment = self.benchmark.calculate_control_adjustment(
            mining_return=mining_return['annualized_return'],
            control_factor=factor
        )

        # Get hurdle rates
        hurdles = self.benchmark.get_hurdle_rates()

        # Make investment decision
        meets_hurdle = (
            adjustment['adjusted_return'] >= hurdles['minimum_adjusted_return'] and
            mining_return['annualized_return'] >= hurdles['minimum_raw_return']
        )

        result = {
            'ticker': ticker,
            'company_name': mining_return['company_name'],

            # Mining return
            'mining_return': mining_return['annualized_return'],
            'mining_return_pct': mining_return['annualized_return_pct'],
            'implied_upside_pct': mining_return['implied_upside_pct'],

            # NPV context
            'expected_npv_billions': mining_return['expected_npv_billions'],
            'market_cap_millions': mining_return['market_cap_millions'],

            # Control adjustment
            'control_factor': factor,
            'benchmark_irr': adjustment['benchmark_irr'],
            'benchmark_irr_pct': adjustment['benchmark_irr_pct'],
            'control_penalty_pct': adjustment['control_penalty_pct'],
            'adjusted_return': adjustment['adjusted_return'],
            'adjusted_return_pct': adjustment['adjusted_return_pct'],

            # Decision metrics
            'beats_benchmark': adjustment['beats_benchmark'],
            'meets_hurdle': meets_hurdle,
            'minimum_adjusted_hurdle': hurdles['minimum_adjusted_return'],
            'minimum_raw_hurdle': hurdles['minimum_raw_return'],

            # Excess returns
            'excess_vs_benchmark_pct': adjustment['excess_vs_benchmark_pct'],

            # Project context
            'project': mining_return['project'],
            'stage': mining_return['stage'],
            'years_to_production': mining_return['years_to_production'],

            'calculation_time': datetime.now().isoformat()
        }

        logger.info(f"Adjusted return for {ticker}: {result['adjusted_return_pct']:.1f}% (meets hurdle: {meets_hurdle})")
        return result

    def compare_adjusted_returns(
        self,
        tickers: List[str],
        discount_rate: float = 0.08
    ) -> Dict[str, Any]:
        """
        Compare control-adjusted returns across multiple companies.

        Args:
            tickers: List of ticker symbols
            discount_rate: Discount rate for calculations

        Returns:
            Comparison data
        """
        results = {}
        for ticker in tickers:
            results[ticker] = self.calculate_adjusted_return(ticker, discount_rate)

        # Rank by adjusted return
        valid_results = [(t, r) for t, r in results.items() if 'error' not in r]
        ranked = sorted(
            valid_results,
            key=lambda x: x[1]['adjusted_return'],
            reverse=True
        )

        # Summary stats
        meets_hurdle = [t for t, r in valid_results if r['meets_hurdle']]
        beats_benchmark = [t for t, r in valid_results if r['beats_benchmark']]

        return {
            'results': results,
            'ranking': [
                {
                    'rank': i + 1,
                    'ticker': t,
                    'adjusted_return_pct': r['adjusted_return_pct'],
                    'mining_return_pct': r['mining_return_pct'],
                    'meets_hurdle': r['meets_hurdle']
                }
                for i, (t, r) in enumerate(ranked)
            ],
            'best_adjusted': ranked[0][0] if ranked else None,
            'meets_hurdle': meets_hurdle,
            'beats_benchmark': beats_benchmark,
            'comparison_time': datetime.now().isoformat()
        }

    def generate_summary_table(
        self,
        tickers: List[str],
        discount_rate: float = 0.08
    ) -> List[Dict]:
        """
        Generate a summary table for dashboard display.

        Args:
            tickers: List of ticker symbols
            discount_rate: Discount rate

        Returns:
            List of row dictionaries for DataFrame
        """
        comparison = self.compare_adjusted_returns(tickers, discount_rate)

        rows = []
        for entry in comparison['ranking']:
            ticker = entry['ticker']
            result = comparison['results'][ticker]

            rows.append({
                'Rank': entry['rank'],
                'Ticker': ticker,
                'Company': result['company_name'],
                'Mining Return': f"{result['mining_return_pct']:.1f}%",
                'Control Penalty': f"-{result['control_penalty_pct']:.1f}%",
                'Adjusted Return': f"{result['adjusted_return_pct']:.1f}%",
                'Meets Hurdle': 'Yes' if result['meets_hurdle'] else 'No',
                'NPV ($B)': f"${result['expected_npv_billions']:.2f}",
                'Mkt Cap ($M)': f"${result['market_cap_millions']:.0f}"
            })

        return rows


# Convenience functions
def get_adjusted_return(ticker: str, discount_rate: float = 0.08) -> float:
    """Get control-adjusted return for a ticker"""
    calculator = AdjustedReturnCalculator()
    result = calculator.calculate_adjusted_return(ticker, discount_rate)
    return result.get('adjusted_return', 0)


def compare_miners(tickers: List[str]) -> Dict[str, Any]:
    """Compare adjusted returns across miners"""
    calculator = AdjustedReturnCalculator()
    return calculator.compare_adjusted_returns(tickers)
