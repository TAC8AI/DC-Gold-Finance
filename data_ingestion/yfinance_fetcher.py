"""
Yahoo Finance data fetcher for stock prices, financials, and market data
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from utils.logger import setup_logger
from data_ingestion.cache_manager import get_cache

logger = setup_logger(__name__)


class YFinanceFetcher:
    """Fetches financial data from Yahoo Finance with caching"""

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.cache = get_cache() if use_cache else None

    def _cache_key(self, ticker: str, data_type: str) -> str:
        """Generate cache key for ticker data"""
        return f"yf_{ticker}_{data_type}_{datetime.now().strftime('%Y%m%d')}"

    def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get basic stock info including price, market cap, etc.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with stock information
        """
        cache_key = self._cache_key(ticker, 'info')

        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            result = {
                'ticker': ticker,
                'name': info.get('longName', info.get('shortName', ticker)),
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'previous_close': info.get('previousClose', 0),
                'market_cap': info.get('marketCap', 0),
                'shares_outstanding': info.get('sharesOutstanding', 0),
                'float_shares': info.get('floatShares', 0),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'volume': info.get('volume', 0),
                'avg_volume': info.get('averageVolume', 0),
                'beta': info.get('beta', 1.0),
                'exchange': info.get('exchange', 'Unknown'),
                'currency': info.get('currency', 'USD'),
                'fetch_time': datetime.now().isoformat()
            }

            # Calculate daily change
            if result['previous_close'] > 0:
                result['daily_change_pct'] = (
                    (result['current_price'] - result['previous_close'])
                    / result['previous_close'] * 100
                )
            else:
                result['daily_change_pct'] = 0

            if self.use_cache:
                self.cache.set(cache_key, result)

            logger.info(f"Fetched info for {ticker}: ${result['current_price']:.2f}")
            return result

        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}

    def get_price_history(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """
        Get historical price data.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, ytd, max)

        Returns:
            DataFrame with OHLCV data
        """
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period=period)

            if history.empty:
                logger.warning(f"No price history for {ticker}")
                return pd.DataFrame()

            logger.info(f"Fetched {len(history)} days of price history for {ticker}")
            return history

        except Exception as e:
            logger.error(f"Error fetching price history for {ticker}: {e}")
            return pd.DataFrame()

    def get_financials(self, ticker: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Get financial statements.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Tuple of (balance_sheet, income_statement, cash_flow)
        """
        try:
            stock = yf.Ticker(ticker)

            balance_sheet = stock.balance_sheet
            income_stmt = stock.income_stmt
            cash_flow = stock.cashflow

            logger.info(f"Fetched financials for {ticker}")
            return balance_sheet, income_stmt, cash_flow

        except Exception as e:
            logger.error(f"Error fetching financials for {ticker}: {e}")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    def get_cash_position(self, ticker: str) -> Dict[str, Any]:
        """
        Get current cash position and related metrics.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with cash metrics
        """
        cache_key = self._cache_key(ticker, 'cash')

        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        try:
            stock = yf.Ticker(ticker)
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow

            result = {
                'ticker': ticker,
                'cash_and_equivalents': 0,
                'short_term_investments': 0,
                'total_cash': 0,
                'total_debt': 0,
                'net_cash': 0,
                'quarterly_cash_burn': 0,
                'runway_months': 0,
                'fetch_time': datetime.now().isoformat()
            }

            # Extract cash from balance sheet
            if not balance_sheet.empty:
                if 'Cash And Cash Equivalents' in balance_sheet.index:
                    result['cash_and_equivalents'] = float(balance_sheet.loc['Cash And Cash Equivalents'].iloc[0] or 0)
                if 'Other Short Term Investments' in balance_sheet.index:
                    result['short_term_investments'] = float(balance_sheet.loc['Other Short Term Investments'].iloc[0] or 0)
                if 'Total Debt' in balance_sheet.index:
                    result['total_debt'] = float(balance_sheet.loc['Total Debt'].iloc[0] or 0)

            result['total_cash'] = result['cash_and_equivalents'] + result['short_term_investments']
            result['net_cash'] = result['total_cash'] - result['total_debt']

            # Estimate quarterly burn from cash flow
            if not cash_flow.empty and 'Free Cash Flow' in cash_flow.index:
                fcf = cash_flow.loc['Free Cash Flow'].iloc[0]
                if fcf and fcf < 0:
                    # Annual burn / 4 = quarterly
                    result['quarterly_cash_burn'] = abs(float(fcf)) / 4
                    if result['quarterly_cash_burn'] > 0:
                        result['runway_months'] = (result['total_cash'] / result['quarterly_cash_burn']) * 3

            if self.use_cache:
                self.cache.set(cache_key, result)

            logger.info(f"Fetched cash position for {ticker}: ${result['total_cash']/1e6:.1f}M")
            return result

        except Exception as e:
            logger.error(f"Error fetching cash position for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e)}

    def get_multiple_tickers(self, tickers: list) -> Dict[str, Dict]:
        """
        Fetch data for multiple tickers efficiently.

        Args:
            tickers: List of ticker symbols

        Returns:
            Dictionary of ticker -> data
        """
        results = {}
        for ticker in tickers:
            results[ticker] = {
                'info': self.get_stock_info(ticker),
                'cash': self.get_cash_position(ticker)
            }
        return results


# Convenience function
def fetch_company_data(ticker: str) -> Dict[str, Any]:
    """Quick fetch of all company data"""
    fetcher = YFinanceFetcher()
    return {
        'info': fetcher.get_stock_info(ticker),
        'cash': fetcher.get_cash_position(ticker),
        'history': fetcher.get_price_history(ticker)
    }
