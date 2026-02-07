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

    @staticmethod
    def _extract_statement_value(statement: pd.DataFrame, row_names: list) -> Optional[float]:
        """
        Extract the first non-null numeric value from the first matching row.
        Statement columns are typically ordered latest -> oldest.
        """
        if statement.empty:
            return None

        for row_name in row_names:
            if row_name not in statement.index:
                continue

            row = statement.loc[row_name]
            if isinstance(row, pd.Series):
                values = row.tolist()
            else:
                values = [row]

            for value in values:
                if pd.notna(value):
                    try:
                        return float(value)
                    except (TypeError, ValueError):
                        continue

        return None

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
            if cached and cached.get('current_price', 0) > 0:
                return cached

        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Try to get price from info first
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or 0
            previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose') or 0

            # If price is 0, try getting from history
            if current_price == 0:
                try:
                    hist = stock.history(period="5d")
                    if not hist.empty:
                        current_price = float(hist['Close'].iloc[-1])
                        if len(hist) > 1:
                            previous_close = float(hist['Close'].iloc[-2])
                except:
                    pass

            # Get market cap, calculate if needed
            market_cap = info.get('marketCap', 0)
            shares_outstanding = info.get('sharesOutstanding', 0)

            if market_cap == 0 and shares_outstanding > 0 and current_price > 0:
                market_cap = shares_outstanding * current_price

            result = {
                'ticker': ticker,
                'name': info.get('longName') or info.get('shortName') or ticker,
                'current_price': current_price,
                'previous_close': previous_close,
                'market_cap': market_cap,
                'shares_outstanding': shares_outstanding,
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

            if self.use_cache and result['current_price'] > 0:
                self.cache.set(cache_key, result)

            logger.info(f"Fetched info for {ticker}: ${result['current_price']:.2f}")
            return result

        except Exception as e:
            logger.error(f"Error fetching info for {ticker}: {e}")
            return {'ticker': ticker, 'error': str(e), 'current_price': 0, 'market_cap': 0}

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
        # Bump cache namespace so improved extraction logic is used immediately.
        cache_key = self._cache_key(ticker, 'cash_v2')

        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        try:
            stock = yf.Ticker(ticker)
            quarterly_balance_sheet = stock.quarterly_balance_sheet
            annual_balance_sheet = stock.balance_sheet
            quarterly_cash_flow = stock.quarterly_cashflow
            annual_cash_flow = stock.cashflow
            try:
                info = stock.info
            except Exception:
                info = {}

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

            # Prefer quarterly statements for current runway; fallback to annual.
            balance_sheet = (
                quarterly_balance_sheet
                if not quarterly_balance_sheet.empty
                else annual_balance_sheet
            )

            total_cash_from_bs = self._extract_statement_value(
                balance_sheet,
                [
                    'Cash Cash Equivalents And Short Term Investments',
                    'Cash And Short Term Investments'
                ]
            )
            cash_and_eq = self._extract_statement_value(
                balance_sheet,
                ['Cash And Cash Equivalents']
            )
            short_term_inv = self._extract_statement_value(
                balance_sheet,
                ['Other Short Term Investments']
            )
            total_debt = self._extract_statement_value(
                balance_sheet,
                ['Total Debt']
            )

            if cash_and_eq is not None:
                result['cash_and_equivalents'] = cash_and_eq
            if short_term_inv is not None:
                result['short_term_investments'] = short_term_inv
            if total_debt is not None:
                result['total_debt'] = total_debt

            if total_cash_from_bs is not None and total_cash_from_bs > 0:
                result['total_cash'] = total_cash_from_bs
                # Avoid showing 0 cash components when the statement only exposes aggregate cash.
                if result['cash_and_equivalents'] == 0 and result['short_term_investments'] == 0:
                    result['cash_and_equivalents'] = total_cash_from_bs
            else:
                result['total_cash'] = result['cash_and_equivalents'] + result['short_term_investments']

            # Fallback to quote summary fields when statements are sparse/stale.
            info_total_cash = info.get('totalCash') if isinstance(info, dict) else None
            info_total_debt = info.get('totalDebt') if isinstance(info, dict) else None
            if isinstance(info_total_cash, (int, float)) and info_total_cash > result['total_cash']:
                result['total_cash'] = float(info_total_cash)
                if result['cash_and_equivalents'] == 0:
                    result['cash_and_equivalents'] = float(info_total_cash)
            if isinstance(info_total_debt, (int, float)) and result['total_debt'] == 0:
                result['total_debt'] = float(info_total_debt)

            result['net_cash'] = result['total_cash'] - result['total_debt']

            # Prefer quarterly FCF as quarterly burn; fallback to annual FCF / 4.
            quarterly_fcf = self._extract_statement_value(quarterly_cash_flow, ['Free Cash Flow'])
            annual_fcf = self._extract_statement_value(annual_cash_flow, ['Free Cash Flow'])

            if isinstance(quarterly_fcf, (int, float)) and quarterly_fcf < 0:
                result['quarterly_cash_burn'] = abs(float(quarterly_fcf))
            elif isinstance(annual_fcf, (int, float)) and annual_fcf < 0:
                result['quarterly_cash_burn'] = abs(float(annual_fcf)) / 4

            if result['total_cash'] > 0 and result['quarterly_cash_burn'] > 0:
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
