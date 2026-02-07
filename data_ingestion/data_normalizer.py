"""
Normalize data across multiple companies into a standard format
"""
import yaml
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd

from utils.logger import setup_logger
from data_ingestion.yfinance_fetcher import YFinanceFetcher
from data_ingestion.gold_price_fetcher import GoldPriceFetcher

logger = setup_logger(__name__)

# Path to config files
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')


class DataNormalizer:
    """Normalizes and combines data from multiple sources into standard format"""

    def __init__(self):
        self.yf_fetcher = YFinanceFetcher()
        self.gold_fetcher = GoldPriceFetcher()
        self.companies_config = self._load_config('companies.yaml')
        self.assumptions_config = self._load_config('assumptions.yaml')

    def _load_config(self, filename: str) -> Dict:
        """Load YAML configuration file"""
        filepath = os.path.join(CONFIG_DIR, filename)
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return {}

    def get_company_tickers(self) -> List[str]:
        """Get list of company tickers from config"""
        return list(self.companies_config.get('companies', {}).keys())

    def get_normalized_company_data(self, ticker: str) -> Dict[str, Any]:
        """
        Get normalized data for a single company.

        Combines:
        - Static config data (projects, assumptions)
        - Live market data (price, market cap)
        - Cash position data

        Args:
            ticker: Company ticker symbol

        Returns:
            Normalized company data dictionary
        """
        company_config = self.companies_config.get('companies', {}).get(ticker, {})

        if not company_config:
            logger.warning(f"No config found for {ticker}")
            return {'ticker': ticker, 'error': 'No configuration found'}

        # Fetch live data
        stock_info = self.yf_fetcher.get_stock_info(ticker)
        cash_data = self.yf_fetcher.get_cash_position(ticker)

        # Get primary project
        projects = company_config.get('projects', {})
        primary_project = list(projects.values())[0] if projects else {}

        # Build normalized structure
        normalized = {
            'ticker': ticker,
            'name': company_config.get('name', stock_info.get('name', ticker)),
            'exchange': company_config.get('exchange', stock_info.get('exchange', '')),
            'description': company_config.get('description', ''),

            # Market data
            'market': {
                'current_price': stock_info.get('current_price', 0),
                'previous_close': stock_info.get('previous_close', 0),
                'daily_change_pct': stock_info.get('daily_change_pct', 0),
                'market_cap': stock_info.get('market_cap', 0),
                'market_cap_millions': stock_info.get('market_cap', 0) / 1_000_000,
                'shares_outstanding': stock_info.get('shares_outstanding', 0),
                'fifty_two_week_high': stock_info.get('fifty_two_week_high', 0),
                'fifty_two_week_low': stock_info.get('fifty_two_week_low', 0),
                'volume': stock_info.get('volume', 0),
                'beta': stock_info.get('beta', 1.0)
            },

            # Cash position
            'cash': {
                'cash_and_equivalents': cash_data.get('cash_and_equivalents', 0),
                'total_cash': cash_data.get('total_cash', 0),
                'total_cash_millions': cash_data.get('total_cash', 0) / 1_000_000,
                'total_debt': cash_data.get('total_debt', 0),
                'net_cash': cash_data.get('net_cash', 0),
                'quarterly_burn': cash_data.get('quarterly_cash_burn', 0),
                'runway_months': cash_data.get('runway_months', 0)
            },

            # Primary project data
            'project': {
                'name': primary_project.get('name', 'Unknown'),
                'type': primary_project.get('type', 'unknown'),
                'annual_production_oz': primary_project.get('annual_production_oz', 0),
                'aisc_per_oz': primary_project.get('aisc_per_oz', 0),
                'mine_life_years': primary_project.get('mine_life_years', 0),
                'initial_capex_millions': primary_project.get('initial_capex_millions', 0),
                'production_start_year': primary_project.get('production_start_year', 2030),
                'stage': primary_project.get('stage', 'exploration'),
                'jurisdiction': primary_project.get('jurisdiction', 'Unknown'),
                'grade_g_per_t': primary_project.get('grade_g_per_t', 0),
                'recovery_rate': primary_project.get('recovery_rate', 0)
            },

            # Control factor for benchmarking
            'control_factor': company_config.get('control_factor', 0.25),
            'notes': company_config.get('notes', ''),

            # Calculated metrics
            'calculated': {
                'enterprise_value': (
                    stock_info.get('market_cap', 0) +
                    cash_data.get('total_debt', 0) -
                    cash_data.get('total_cash', 0)
                ),
                'years_to_production': max(0, primary_project.get('production_start_year', 2030) - datetime.now().year),
                'capex_vs_cash': (
                    primary_project.get('initial_capex_millions', 0) * 1_000_000 /
                    max(cash_data.get('total_cash', 1), 1)
                ),
                'funding_gap_millions': max(0,
                    primary_project.get('initial_capex_millions', 0) -
                    cash_data.get('total_cash', 0) / 1_000_000
                )
            },

            'fetch_time': datetime.now().isoformat()
        }

        logger.info(f"Normalized data for {ticker}")
        return normalized

    def get_all_companies_normalized(self) -> Dict[str, Dict]:
        """
        Get normalized data for all configured companies.

        Returns:
            Dictionary of ticker -> normalized data
        """
        tickers = self.get_company_tickers()
        results = {}

        for ticker in tickers:
            results[ticker] = self.get_normalized_company_data(ticker)

        logger.info(f"Normalized data for {len(results)} companies")
        return results

    def get_comparison_dataframe(self) -> pd.DataFrame:
        """
        Get a DataFrame suitable for company comparison.

        Returns:
            DataFrame with key metrics for each company
        """
        all_data = self.get_all_companies_normalized()
        gold_price = self.gold_fetcher.get_current_price().get('price', 2100)

        rows = []
        for ticker, data in all_data.items():
            if 'error' in data:
                continue

            row = {
                'Ticker': ticker,
                'Company': data['name'],
                'Price': data['market']['current_price'],
                'Market Cap ($M)': round(data['market']['market_cap_millions'], 1),
                'Cash ($M)': round(data['cash']['total_cash_millions'], 1),
                'Runway (Months)': round(data['cash']['runway_months'], 0) if data['cash']['runway_months'] else 'N/A',
                'Project': data['project']['name'],
                'Stage': data['project']['stage'].title(),
                'Production (oz/yr)': f"{data['project']['annual_production_oz']:,}",
                'AISC ($/oz)': data['project']['aisc_per_oz'],
                'Margin ($/oz)': round(gold_price - data['project']['aisc_per_oz'], 0),
                'Start Year': data['project']['production_start_year'],
                'Capex ($M)': data['project']['initial_capex_millions'],
                'Funding Gap ($M)': round(data['calculated']['funding_gap_millions'], 1)
            }
            rows.append(row)

        return pd.DataFrame(rows)

    def get_gold_context(self) -> Dict[str, Any]:
        """
        Get gold price context for analysis.

        Returns:
            Dictionary with gold price data and context
        """
        current = self.gold_fetcher.get_current_price()
        stats = self.gold_fetcher.get_price_stats()

        return {
            'current_price': current.get('price', 2100),
            'daily_change': current.get('daily_change', 0),
            'daily_change_pct': current.get('daily_change_pct', 0),
            'year_high': current.get('fifty_two_week_high', 0),
            'year_low': current.get('fifty_two_week_low', 0),
            'year_mean': stats.get('mean', 0),
            'year_volatility': stats.get('volatility', 0),
            'scenarios': self.assumptions_config.get('gold_price_scenarios', {})
        }


# Convenience functions
def get_all_company_data() -> Dict[str, Dict]:
    """Quick fetch of all normalized company data"""
    normalizer = DataNormalizer()
    return normalizer.get_all_companies_normalized()


def get_comparison_table() -> pd.DataFrame:
    """Get comparison DataFrame"""
    normalizer = DataNormalizer()
    return normalizer.get_comparison_dataframe()
