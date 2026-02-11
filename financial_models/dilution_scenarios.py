"""
Dilution scenario modeling: Low/Base/High with probabilities.
Supports company-specific known raises and strategic financing commitments.
"""
import yaml
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import setup_logger
from financial_models.capital_structure import CapitalStructureAnalyzer
from data_ingestion.data_normalizer import DataNormalizer

logger = setup_logger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')


def _load_companies_config() -> Dict:
    """Load companies config for known raises and strategic financing."""
    filepath = os.path.join(CONFIG_DIR, 'companies.yaml')
    try:
        with open(filepath, 'r') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.warning(f"Could not load companies config: {e}")
        return {}


class DilutionScenarioModeler:
    """Models dilution scenarios for pre-production miners"""

    # Default scenario definitions (for companies without known financing)
    DEFAULT_SCENARIOS = {
        'low': {
            'name': 'Low Dilution',
            'dilution_percentage': 10,
            'probability': 0.20,
            'description': 'Minimal raise, strong market, strategic investment',
            'conditions': [
                'Gold price remains elevated',
                'Strong institutional interest',
                'Favorable debt markets'
            ]
        },
        'base': {
            'name': 'Base Case',
            'dilution_percentage': 30,
            'probability': 0.50,
            'description': 'Standard project financing with equity component',
            'conditions': [
                'Typical financing structure',
                'Mix of debt and equity',
                'Normal market conditions'
            ]
        },
        'high': {
            'name': 'High Dilution',
            'dilution_percentage': 60,
            'probability': 0.25,
            'description': 'Significant equity raises required',
            'conditions': [
                'Challenging market conditions',
                'Cost overruns or delays',
                'Limited debt availability'
            ]
        },
        'extreme': {
            'name': 'Extreme Dilution',
            'dilution_percentage': 100,
            'probability': 0.05,
            'description': 'Major restructuring or distressed financing',
            'conditions': [
                'Project setbacks',
                'Severe market downturn',
                'Forced equity raises at discount'
            ]
        }
    }

    def __init__(self):
        self.cap_analyzer = CapitalStructureAnalyzer()
        self.normalizer = DataNormalizer()
        self.companies_config = _load_companies_config()

    def _get_known_raises(self, ticker: str) -> List[Dict]:
        """Get completed/closed known raises for a company from config."""
        company = self.companies_config.get('companies', {}).get(ticker, {})
        raises = company.get('known_raises', [])
        return [r for r in raises if r.get('status') == 'closed']

    def _get_strategic_financing(self, ticker: str) -> Dict:
        """Get strategic financing details (e.g. Orion) from config."""
        company = self.companies_config.get('companies', {}).get(ticker, {})
        return company.get('strategic_financing', {})

    def _sum_known_raises(self, ticker: str) -> Dict[str, float]:
        """Sum up capital already raised and shares already issued from known raises."""
        raises = self._get_known_raises(ticker)
        total_proceeds = sum(r.get('gross_proceeds_millions', 0) for r in raises)
        total_shares = sum(r.get('shares_issued', 0) for r in raises)
        return {
            'total_raised_millions': total_proceeds,
            'total_shares_issued': total_shares,
            'raises': raises
        }

    def _build_informed_scenarios(self, ticker: str, funding_gap_millions: float,
                                  current_shares: int, current_price: float) -> Dict:
        """Build dilution scenarios informed by known financing and strategic commitments."""
        strategic = self._get_strategic_financing(ticker)
        known = self._sum_known_raises(ticker)

        # Calculate remaining funding gap after known raises
        remaining_gap = max(0, funding_gap_millions - known['total_raised_millions'])

        # Check for construction financing commitment (e.g. Orion)
        construction_commitment = 0
        has_debt_backstop = False
        for partner_key, partner in strategic.items():
            commitment = partner.get('construction_financing_commitment_millions', 0)
            if commitment > 0:
                construction_commitment += commitment
                has_debt_backstop = True

        # Build scenarios based on actual financing landscape
        if has_debt_backstop and construction_commitment >= remaining_gap:
            # Strong financing backstop exists (e.g. Orion $300M)
            return {
                'low': {
                    'name': 'Debt-Funded Build',
                    'dilution_percentage': 5,
                    'probability': 0.25,
                    'description': f'Construction financed primarily through committed debt facility (${construction_commitment:.0f}M available)',
                    'conditions': [
                        'Strong PFS economics',
                        'Debt facility fully drawn',
                        'Minimal additional equity needed'
                    ]
                },
                'base': {
                    'name': 'Mixed Debt + Equity',
                    'dilution_percentage': 20,
                    'probability': 0.45,
                    'description': f'Debt covers ~60-70% of remaining ${remaining_gap:.0f}M gap, equity covers rest',
                    'conditions': [
                        'Typical project finance structure',
                        'Partial debt draw + equity component',
                        'Normal market conditions'
                    ]
                },
                'high': {
                    'name': 'Equity-Heavy Build',
                    'dilution_percentage': 40,
                    'probability': 0.25,
                    'description': 'Debt facility terms unfavorable, more equity needed',
                    'conditions': [
                        'Higher interest rates',
                        'PFS shows marginal economics',
                        'Equity markets more accessible than debt'
                    ]
                },
                'extreme': {
                    'name': 'Full Equity + Overruns',
                    'dilution_percentage': 70,
                    'probability': 0.05,
                    'description': 'Debt backstop not exercised, capex overruns, distressed equity',
                    'conditions': [
                        'Project setbacks or delays',
                        'Gold price decline',
                        'Orion declines to fund'
                    ]
                }
            }
        else:
            # No strong backstop — use defaults but adjusted for known raises
            return self.DEFAULT_SCENARIOS

    def model_scenarios(self, ticker: str, scenarios: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Model dilution scenarios for a company.
        Accounts for known raises already completed and strategic financing commitments.

        Args:
            ticker: Company ticker symbol
            scenarios: Optional custom scenarios (uses informed defaults if not provided)

        Returns:
            Dictionary with scenario analysis
        """
        # Get company data
        company_data = self.normalizer.get_normalized_company_data(ticker)
        capital = self.cap_analyzer.analyze_structure(ticker)

        if 'error' in company_data or capital.get('shares_outstanding', 0) == 0:
            return {'ticker': ticker, 'error': 'Unable to get company data'}

        current_shares = capital['shares_outstanding']
        current_price = capital['current_price']
        market_cap = capital['market_cap']
        funding_gap_millions = company_data['calculated']['funding_gap_millions']
        funding_gap = funding_gap_millions * 1_000_000

        # Get known raises info
        known = self._sum_known_raises(ticker)
        strategic = self._get_strategic_financing(ticker)

        # Build scenarios: use informed scenarios if we have financing data
        if scenarios is None and (known['raises'] or strategic):
            scenarios = self._build_informed_scenarios(
                ticker, funding_gap_millions, current_shares, current_price
            )
        else:
            scenarios = scenarios or self.DEFAULT_SCENARIOS

        # Model each scenario
        scenario_results = {}
        expected_shares = 0
        expected_dilution = 0

        for scenario_key, scenario_def in scenarios.items():
            dilution_pct = scenario_def['dilution_percentage'] / 100
            probability = scenario_def['probability']

            # Calculate new shares
            new_shares = current_shares * dilution_pct
            post_shares = current_shares + new_shares

            # Calculate ownership impact
            current_ownership = 100
            post_ownership = (current_shares / post_shares) * 100 if post_shares > 0 else 0

            # Implied capital raised (assuming at current price)
            capital_raised = new_shares * current_price

            scenario_results[scenario_key] = {
                'name': scenario_def['name'],
                'dilution_percentage': scenario_def['dilution_percentage'],
                'probability': probability,
                'description': scenario_def['description'],
                'conditions': scenario_def.get('conditions', []),

                # Share counts
                'current_shares': current_shares,
                'new_shares': new_shares,
                'post_shares': post_shares,
                'current_shares_millions': current_shares / 1_000_000,
                'new_shares_millions': new_shares / 1_000_000,
                'post_shares_millions': post_shares / 1_000_000,

                # Ownership impact
                'ownership_pre': current_ownership,
                'ownership_post': post_ownership,
                'ownership_loss': current_ownership - post_ownership,

                # Implied value
                'implied_capital_raised': capital_raised,
                'implied_capital_raised_millions': capital_raised / 1_000_000,

                # Post-dilution price (assuming market cap unchanged)
                'implied_post_price': market_cap / post_shares if post_shares > 0 else 0,

                # Coverage of funding gap
                'funding_gap_coverage': (
                    capital_raised / funding_gap * 100
                    if funding_gap > 0 else float('inf')
                )
            }

            # Accumulate for expected value
            expected_shares += post_shares * probability
            expected_dilution += scenario_def['dilution_percentage'] * probability

        # Calculate remaining gap after known raises
        remaining_gap_millions = max(0, funding_gap_millions - known['total_raised_millions'])

        # Build strategic financing summary
        strategic_summary = {}
        for partner_key, partner in strategic.items():
            strategic_summary[partner_key] = {
                'name': partner.get('name', partner_key),
                'invested_millions': partner.get('total_invested_millions', 0),
                'ownership_pct': partner.get('ownership_pct', 0),
                'construction_commitment_millions': partner.get('construction_financing_commitment_millions', 0),
                'binding': partner.get('construction_financing_binding', False),
                'royalty_nsr_pct': partner.get('royalty_nsr_pct', 0),
                'matching_rights': partner.get('matching_rights', False),
            }

        # Calculate probability-weighted expected values
        result = {
            'ticker': ticker,
            'company_name': company_data.get('name', ticker),
            'current_price': current_price,
            'current_shares': current_shares,
            'current_shares_millions': current_shares / 1_000_000,
            'market_cap': market_cap,
            'market_cap_millions': market_cap / 1_000_000,
            'funding_gap_millions': funding_gap / 1_000_000,

            # Known raises already completed
            'known_raises': known['raises'],
            'total_already_raised_millions': known['total_raised_millions'],
            'total_shares_from_raises': known['total_shares_issued'],
            'remaining_funding_gap_millions': remaining_gap_millions,

            # Strategic financing
            'strategic_financing': strategic_summary,

            'scenarios': scenario_results,

            # Expected values
            'expected_dilution_percentage': expected_dilution,
            'expected_post_shares': expected_shares,
            'expected_post_shares_millions': expected_shares / 1_000_000,
            'expected_ownership_post': (current_shares / expected_shares) * 100 if expected_shares > 0 else 0,

            'analysis_time': datetime.now().isoformat()
        }

        logger.info(f"Dilution scenarios for {ticker}: Expected {expected_dilution:.1f}% dilution "
                     f"(already raised ${known['total_raised_millions']:.0f}M, "
                     f"remaining gap ${remaining_gap_millions:.0f}M)")
        return result

    def calculate_npv_adjusted_for_dilution(
        self,
        ticker: str,
        base_npv: float,
        scenarios: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Adjust NPV for expected dilution.

        Args:
            ticker: Company ticker
            base_npv: Base case NPV in dollars
            scenarios: Optional custom scenarios

        Returns:
            Dictionary with dilution-adjusted NPV per share
        """
        dilution_analysis = self.model_scenarios(ticker, scenarios)

        if 'error' in dilution_analysis:
            return dilution_analysis

        current_shares = dilution_analysis['current_shares']
        results = {
            'ticker': ticker,
            'base_npv': base_npv,
            'base_npv_billions': base_npv / 1_000_000_000,
            'current_shares_millions': current_shares / 1_000_000,
            'base_npv_per_share': base_npv / current_shares if current_shares > 0 else 0,
            'scenarios': {},
            'expected_npv_per_share': 0
        }

        expected_npv_per_share = 0

        for scenario_key, scenario in dilution_analysis['scenarios'].items():
            post_shares = scenario['post_shares']
            probability = scenario['probability']

            npv_per_share = base_npv / post_shares if post_shares > 0 else 0

            results['scenarios'][scenario_key] = {
                'name': scenario['name'],
                'dilution_percentage': scenario['dilution_percentage'],
                'probability': probability,
                'post_shares_millions': scenario['post_shares_millions'],
                'npv_per_share': npv_per_share,
                'npv_per_share_vs_base': (
                    (npv_per_share / results['base_npv_per_share'] - 1) * 100
                    if results['base_npv_per_share'] > 0 else 0
                )
            }

            expected_npv_per_share += npv_per_share * probability

        results['expected_npv_per_share'] = expected_npv_per_share
        results['expected_npv_vs_base'] = (
            (expected_npv_per_share / results['base_npv_per_share'] - 1) * 100
            if results['base_npv_per_share'] > 0 else 0
        )

        return results

    def compare_dilution_scenarios(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Compare dilution scenarios across companies.

        Args:
            tickers: List of ticker symbols

        Returns:
            Comparison data
        """
        comparisons = {}
        for ticker in tickers:
            comparisons[ticker] = self.model_scenarios(ticker)

        return comparisons


# Convenience functions
def model_dilution(ticker: str) -> Dict[str, Any]:
    """Quick dilution scenario modeling"""
    modeler = DilutionScenarioModeler()
    return modeler.model_scenarios(ticker)


def get_expected_dilution(ticker: str) -> float:
    """Get expected dilution percentage for a ticker"""
    modeler = DilutionScenarioModeler()
    result = modeler.model_scenarios(ticker)
    return result.get('expected_dilution_percentage', 30)  # Default 30%
