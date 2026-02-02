"""
Capital structure analysis: shares, debt, dilution tracking
"""
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import setup_logger
from data_ingestion.yfinance_fetcher import YFinanceFetcher

logger = setup_logger(__name__)


class CapitalStructureAnalyzer:
    """Analyzes capital structure and dilution"""

    def __init__(self):
        self.fetcher = YFinanceFetcher()

    def analyze_structure(self, ticker: str) -> Dict[str, Any]:
        """
        Analyze capital structure for a company.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with capital structure analysis
        """
        stock_info = self.fetcher.get_stock_info(ticker)
        cash_data = self.fetcher.get_cash_position(ticker)

        shares_outstanding = stock_info.get('shares_outstanding', 0)
        market_cap = stock_info.get('market_cap', 0)
        current_price = stock_info.get('current_price', 0)

        result = {
            'ticker': ticker,

            # Share structure
            'shares_outstanding': shares_outstanding,
            'shares_outstanding_millions': shares_outstanding / 1_000_000,
            'float_shares': stock_info.get('float_shares', 0),
            'float_percentage': (
                stock_info.get('float_shares', 0) / shares_outstanding * 100
                if shares_outstanding > 0 else 0
            ),

            # Market valuation
            'current_price': current_price,
            'market_cap': market_cap,
            'market_cap_millions': market_cap / 1_000_000,

            # Debt structure
            'total_debt': cash_data.get('total_debt', 0),
            'total_debt_millions': cash_data.get('total_debt', 0) / 1_000_000,
            'net_debt': -cash_data.get('net_cash', 0),  # Negative net cash = net debt
            'net_debt_millions': -cash_data.get('net_cash', 0) / 1_000_000,

            # Enterprise value
            'enterprise_value': market_cap + cash_data.get('total_debt', 0) - cash_data.get('total_cash', 0),
            'ev_millions': (market_cap + cash_data.get('total_debt', 0) - cash_data.get('total_cash', 0)) / 1_000_000,

            # Leverage ratios
            'debt_to_equity': (
                cash_data.get('total_debt', 0) / market_cap
                if market_cap > 0 else 0
            ),
            'cash_to_market_cap': (
                cash_data.get('total_cash', 0) / market_cap
                if market_cap > 0 else 0
            ),

            # Per share metrics
            'book_value_per_share': 0,  # Would need additional balance sheet data
            'cash_per_share': (
                cash_data.get('total_cash', 0) / shares_outstanding
                if shares_outstanding > 0 else 0
            ),

            'analysis_time': datetime.now().isoformat()
        }

        logger.info(f"Capital structure for {ticker}: {result['shares_outstanding_millions']:.1f}M shares, ${result['market_cap_millions']:.1f}M market cap")
        return result

    def calculate_dilution_impact(
        self,
        ticker: str,
        raise_amount: float,
        issue_price_discount: float = 0.10
    ) -> Dict[str, Any]:
        """
        Calculate impact of potential equity raise.

        Args:
            ticker: Company ticker
            raise_amount: Amount to raise in dollars
            issue_price_discount: Discount to current price for new shares

        Returns:
            Dictionary with dilution analysis
        """
        structure = self.analyze_structure(ticker)

        current_shares = structure['shares_outstanding']
        current_price = structure['current_price']

        if current_shares <= 0 or current_price <= 0:
            return {'error': 'Invalid share or price data'}

        # Issue price (typically at discount)
        issue_price = current_price * (1 - issue_price_discount)

        # New shares issued
        new_shares = raise_amount / issue_price if issue_price > 0 else 0

        # Post-raise totals
        post_raise_shares = current_shares + new_shares
        dilution_percentage = new_shares / current_shares * 100 if current_shares > 0 else 0

        # Ownership dilution
        original_ownership = 100
        post_raise_ownership = (current_shares / post_raise_shares) * 100 if post_raise_shares > 0 else 0

        # Post-raise metrics
        post_raise_cash = structure.get('cash_to_market_cap', 0) * structure['market_cap'] + raise_amount
        post_raise_market_cap = post_raise_shares * current_price  # Assuming price holds

        return {
            'ticker': ticker,
            'raise_amount': raise_amount,
            'raise_amount_millions': raise_amount / 1_000_000,

            # Pre-raise
            'pre_shares_outstanding': current_shares,
            'pre_shares_millions': current_shares / 1_000_000,
            'pre_market_cap': structure['market_cap'],

            # Issue terms
            'issue_price': issue_price,
            'issue_price_discount': issue_price_discount,
            'new_shares_issued': new_shares,
            'new_shares_millions': new_shares / 1_000_000,

            # Post-raise
            'post_shares_outstanding': post_raise_shares,
            'post_shares_millions': post_raise_shares / 1_000_000,
            'post_market_cap': post_raise_market_cap,

            # Dilution metrics
            'dilution_percentage': dilution_percentage,
            'ownership_pre_raise': original_ownership,
            'ownership_post_raise': post_raise_ownership,
            'ownership_reduction': original_ownership - post_raise_ownership,

            # Value per share impact (assuming no value creation)
            'implied_price_post_raise': (
                (structure['market_cap'] + raise_amount) / post_raise_shares
                if post_raise_shares > 0 else 0
            )
        }

    def compare_structures(self, tickers: List[str]) -> pd.DataFrame:
        """
        Compare capital structures across companies.

        Args:
            tickers: List of ticker symbols

        Returns:
            Comparison DataFrame
        """
        rows = []
        for ticker in tickers:
            structure = self.analyze_structure(ticker)
            rows.append({
                'Ticker': ticker,
                'Price': f"${structure['current_price']:.2f}",
                'Market Cap ($M)': round(structure['market_cap_millions'], 1),
                'Shares (M)': round(structure['shares_outstanding_millions'], 1),
                'Float (%)': round(structure['float_percentage'], 1),
                'Debt ($M)': round(structure['total_debt_millions'], 1),
                'EV ($M)': round(structure['ev_millions'], 1),
                'Cash/Share': f"${structure['cash_per_share']:.2f}"
            })

        return pd.DataFrame(rows)


# Convenience functions
def analyze_capital(ticker: str) -> Dict[str, Any]:
    """Quick capital structure analysis"""
    analyzer = CapitalStructureAnalyzer()
    return analyzer.analyze_structure(ticker)


def calculate_raise_dilution(ticker: str, raise_amount_millions: float) -> Dict[str, Any]:
    """Calculate dilution from potential raise"""
    analyzer = CapitalStructureAnalyzer()
    return analyzer.calculate_dilution_impact(ticker, raise_amount_millions * 1_000_000)
