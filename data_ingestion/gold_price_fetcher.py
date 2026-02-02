"""
Gold spot price fetcher using Yahoo Finance GC=F ticker
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from utils.logger import setup_logger
from data_ingestion.cache_manager import get_cache

logger = setup_logger(__name__)

# Gold futures ticker on Yahoo Finance
GOLD_TICKER = "GC=F"


class GoldPriceFetcher:
    """Fetches gold spot/futures prices from Yahoo Finance"""

    def __init__(self, use_cache: bool = True):
        self.use_cache = use_cache
        self.cache = get_cache() if use_cache else None
        self.ticker = GOLD_TICKER

    def get_current_price(self) -> Dict[str, Any]:
        """
        Get current gold spot price.

        Returns:
            Dictionary with gold price data
        """
        cache_key = f"gold_price_{datetime.now().strftime('%Y%m%d_%H')}"

        if self.use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached

        try:
            gold = yf.Ticker(self.ticker)
            info = gold.info
            history = gold.history(period="5d")

            current_price = info.get('regularMarketPrice', 0)
            if current_price == 0 and not history.empty:
                current_price = float(history['Close'].iloc[-1])

            previous_close = info.get('previousClose', 0)
            if previous_close == 0 and len(history) > 1:
                previous_close = float(history['Close'].iloc[-2])

            result = {
                'price': current_price,
                'previous_close': previous_close,
                'daily_change': current_price - previous_close if previous_close else 0,
                'daily_change_pct': ((current_price - previous_close) / previous_close * 100) if previous_close else 0,
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh', 0),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow', 0),
                'fetch_time': datetime.now().isoformat(),
                'source': 'Yahoo Finance (GC=F)'
            }

            if self.use_cache:
                self.cache.set(cache_key, result)

            logger.info(f"Fetched gold price: ${current_price:.2f}/oz")
            return result

        except Exception as e:
            logger.error(f"Error fetching gold price: {e}")
            # Return reasonable fallback
            return {
                'price': 2100,  # Reasonable fallback
                'error': str(e),
                'fetch_time': datetime.now().isoformat(),
                'source': 'fallback'
            }

    def get_price_history(self, period: str = "1y") -> pd.DataFrame:
        """
        Get historical gold prices.

        Args:
            period: Time period (1mo, 3mo, 6mo, 1y, 2y, 5y, max)

        Returns:
            DataFrame with gold price history
        """
        try:
            gold = yf.Ticker(self.ticker)
            history = gold.history(period=period)

            if history.empty:
                logger.warning("No gold price history returned")
                return pd.DataFrame()

            logger.info(f"Fetched {len(history)} days of gold price history")
            return history

        except Exception as e:
            logger.error(f"Error fetching gold history: {e}")
            return pd.DataFrame()

    def get_price_stats(self, period: str = "1y") -> Dict[str, float]:
        """
        Get gold price statistics over a period.

        Args:
            period: Time period for statistics

        Returns:
            Dictionary with price statistics
        """
        history = self.get_price_history(period)

        if history.empty:
            return {}

        close_prices = history['Close']

        return {
            'current': float(close_prices.iloc[-1]),
            'mean': float(close_prices.mean()),
            'median': float(close_prices.median()),
            'std': float(close_prices.std()),
            'min': float(close_prices.min()),
            'max': float(close_prices.max()),
            'range': float(close_prices.max() - close_prices.min()),
            'volatility': float(close_prices.std() / close_prices.mean() * 100),  # As percentage
            'period': period
        }

    def get_moving_averages(self) -> Dict[str, float]:
        """
        Get common moving averages for gold.

        Returns:
            Dictionary with MA values
        """
        history = self.get_price_history("1y")

        if history.empty or len(history) < 200:
            return {}

        close = history['Close']

        return {
            'ma_20': float(close.tail(20).mean()),
            'ma_50': float(close.tail(50).mean()),
            'ma_100': float(close.tail(100).mean()),
            'ma_200': float(close.tail(200).mean()),
            'current': float(close.iloc[-1]),
            'above_ma_50': bool(close.iloc[-1] > close.tail(50).mean()),
            'above_ma_200': bool(close.iloc[-1] > close.tail(200).mean())
        }


# Convenience function
def get_gold_price() -> float:
    """Quick fetch of current gold price"""
    fetcher = GoldPriceFetcher()
    data = fetcher.get_current_price()
    return data.get('price', 2100)


def get_gold_data() -> Dict[str, Any]:
    """Get comprehensive gold price data"""
    fetcher = GoldPriceFetcher()
    return {
        'current': fetcher.get_current_price(),
        'stats': fetcher.get_price_stats(),
        'moving_averages': fetcher.get_moving_averages()
    }
