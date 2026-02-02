"""
Unified metrics interface for all financial calculations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import setup_logger
from financial_models.cash_analysis import CashAnalyzer
from financial_models.capital_structure import CapitalStructureAnalyzer
from financial_models.dilution_scenarios import DilutionScenarioModeler
from data_ingestion.data_normalizer import DataNormalizer
from data_ingestion.gold_price_fetcher import GoldPriceFetcher

logger = setup_logger(__name__)


class MetricsCalculator:
    """Unified interface for all financial metrics"""

    def __init__(self):
        self.cash_analyzer = CashAnalyzer()
        self.capital_analyzer = CapitalStructureAnalyzer()
        self.dilution_modeler = DilutionScenarioModeler()
        self.normalizer = DataNormalizer()
        self.gold_fetcher = GoldPriceFetcher()

    def get_all_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive metrics for a company.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with all calculated metrics
        """
        # Gather all component analyses
        company_data = self.normalizer.get_normalized_company_data(ticker)
        cash_analysis = self.cash_analyzer.analyze_cash_position(ticker)
        capital_structure = self.capital_analyzer.analyze_structure(ticker)
        dilution_scenarios = self.dilution_modeler.model_scenarios(ticker)
        gold_data = self.gold_fetcher.get_current_price()

        # Combine into unified structure
        result = {
            'ticker': ticker,
            'company_name': company_data.get('name', ticker),

            # Market metrics
            'market': {
                'current_price': capital_structure.get('current_price', 0),
                'market_cap_millions': capital_structure.get('market_cap_millions', 0),
                'enterprise_value_millions': capital_structure.get('ev_millions', 0),
                'daily_change_pct': company_data.get('market', {}).get('daily_change_pct', 0),
                'fifty_two_week_high': company_data.get('market', {}).get('fifty_two_week_high', 0),
                'fifty_two_week_low': company_data.get('market', {}).get('fifty_two_week_low', 0),
                'from_52w_high_pct': self._calc_from_high(
                    capital_structure.get('current_price', 0),
                    company_data.get('market', {}).get('fifty_two_week_high', 0)
                )
            },

            # Cash metrics
            'cash': {
                'total_cash_millions': cash_analysis.get('current_cash_millions', 0),
                'net_cash_millions': cash_analysis.get('net_cash_millions', 0),
                'quarterly_burn_millions': cash_analysis.get('quarterly_burn_millions', 0),
                'runway_months': cash_analysis.get('runway_months', 0),
                'runway_risk': cash_analysis.get('runway_risk', {}),
                'cash_per_share': capital_structure.get('cash_per_share', 0),
                'burn_trend': cash_analysis.get('burn_trend', {}).get('trend', 'unknown')
            },

            # Capital structure
            'capital': {
                'shares_outstanding_millions': capital_structure.get('shares_outstanding_millions', 0),
                'float_percentage': capital_structure.get('float_percentage', 0),
                'total_debt_millions': capital_structure.get('total_debt_millions', 0),
                'debt_to_equity': capital_structure.get('debt_to_equity', 0)
            },

            # Dilution
            'dilution': {
                'expected_dilution_pct': dilution_scenarios.get('expected_dilution_percentage', 0),
                'expected_ownership_post': dilution_scenarios.get('expected_ownership_post', 0),
                'scenarios': {
                    k: {
                        'dilution_pct': v.get('dilution_percentage', 0),
                        'probability': v.get('probability', 0)
                    }
                    for k, v in dilution_scenarios.get('scenarios', {}).items()
                }
            },

            # Project metrics
            'project': {
                'name': company_data.get('project', {}).get('name', 'Unknown'),
                'stage': company_data.get('project', {}).get('stage', 'unknown'),
                'production_oz': company_data.get('project', {}).get('annual_production_oz', 0),
                'aisc': company_data.get('project', {}).get('aisc_per_oz', 0),
                'margin_per_oz': gold_data.get('price', 2100) - company_data.get('project', {}).get('aisc_per_oz', 0),
                'mine_life_years': company_data.get('project', {}).get('mine_life_years', 0),
                'capex_millions': company_data.get('project', {}).get('initial_capex_millions', 0),
                'start_year': company_data.get('project', {}).get('production_start_year', 2030),
                'years_to_production': company_data.get('calculated', {}).get('years_to_production', 0)
            },

            # Funding
            'funding': {
                'funding_gap_millions': company_data.get('calculated', {}).get('funding_gap_millions', 0),
                'capex_coverage': (
                    cash_analysis.get('current_cash_millions', 0) /
                    company_data.get('project', {}).get('initial_capex_millions', 1) * 100
                )
            },

            # Gold context
            'gold': {
                'current_price': gold_data.get('price', 2100),
                'daily_change': gold_data.get('daily_change', 0),
                'daily_change_pct': gold_data.get('daily_change_pct', 0)
            },

            # Meta
            'control_factor': company_data.get('control_factor', 0.25),
            'analysis_time': datetime.now().isoformat()
        }

        logger.info(f"Calculated all metrics for {ticker}")
        return result

    def _calc_from_high(self, current: float, high: float) -> float:
        """Calculate percentage from 52-week high"""
        if high <= 0:
            return 0
        return ((current - high) / high) * 100

    def get_summary_metrics(self, ticker: str) -> Dict[str, Any]:
        """
        Get key summary metrics for quick display.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with key metrics only
        """
        full_metrics = self.get_all_metrics(ticker)

        return {
            'ticker': ticker,
            'company_name': full_metrics['company_name'],
            'price': full_metrics['market']['current_price'],
            'market_cap_millions': full_metrics['market']['market_cap_millions'],
            'cash_millions': full_metrics['cash']['total_cash_millions'],
            'runway_months': full_metrics['cash']['runway_months'],
            'runway_risk': full_metrics['cash']['runway_risk'].get('level', 'unknown'),
            'project': full_metrics['project']['name'],
            'stage': full_metrics['project']['stage'],
            'aisc': full_metrics['project']['aisc'],
            'margin': full_metrics['project']['margin_per_oz'],
            'start_year': full_metrics['project']['start_year'],
            'expected_dilution': full_metrics['dilution']['expected_dilution_pct'],
            'funding_gap': full_metrics['funding']['funding_gap_millions'],
            'gold_price': full_metrics['gold']['current_price']
        }

    def compare_metrics(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """
        Get comparison metrics for multiple companies.

        Args:
            tickers: List of ticker symbols

        Returns:
            List of summary metrics for each company
        """
        return [self.get_summary_metrics(ticker) for ticker in tickers]

    def get_key_metrics_table(self, tickers: List[str]) -> List[Dict]:
        """
        Get metrics formatted for a comparison table.

        Args:
            tickers: List of ticker symbols

        Returns:
            List of dictionaries suitable for DataFrame
        """
        rows = []
        for ticker in tickers:
            metrics = self.get_summary_metrics(ticker)
            rows.append({
                'Ticker': ticker,
                'Company': metrics['company_name'],
                'Price': f"${metrics['price']:.2f}",
                'Mkt Cap': f"${metrics['market_cap_millions']:.0f}M",
                'Cash': f"${metrics['cash_millions']:.1f}M",
                'Runway': f"{metrics['runway_months']:.0f}mo" if metrics['runway_months'] else 'N/A',
                'Project': metrics['project'],
                'Stage': metrics['stage'].title(),
                'AISC': f"${metrics['aisc']:,.0f}",
                'Margin': f"${metrics['margin']:.0f}",
                'Start': metrics['start_year'],
                'Dilution': f"{metrics['expected_dilution']:.0f}%",
                'Gap': f"${metrics['funding_gap']:.0f}M"
            })
        return rows


# Convenience function
def get_company_metrics(ticker: str) -> Dict[str, Any]:
    """Quick access to all metrics for a ticker"""
    calculator = MetricsCalculator()
    return calculator.get_all_metrics(ticker)
