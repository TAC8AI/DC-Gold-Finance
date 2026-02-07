"""
Cash position analysis: runway, burn rate, trends
"""
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import setup_logger
from data_ingestion.yfinance_fetcher import YFinanceFetcher

logger = setup_logger(__name__)


class CashAnalyzer:
    """Analyzes cash position, burn rate, and runway"""

    def __init__(self):
        self.fetcher = YFinanceFetcher()

    def analyze_cash_position(self, ticker: str) -> Dict[str, Any]:
        """
        Comprehensive cash analysis for a company.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with detailed cash analysis
        """
        cash_data = self.fetcher.get_cash_position(ticker)
        stock_info = self.fetcher.get_stock_info(ticker)
        bs, _, cf = self.fetcher.get_financials(ticker)

        # Extract historical cash positions for trend
        historical_cash = self._extract_historical_cash(bs)
        burn_trend = self._calculate_burn_trend(historical_cash)

        result = {
            'ticker': ticker,

            # Current position
            'current_cash': cash_data.get('total_cash', 0),
            'current_cash_millions': cash_data.get('total_cash', 0) / 1_000_000,
            'cash_and_equivalents': cash_data.get('cash_and_equivalents', 0),
            'short_term_investments': cash_data.get('short_term_investments', 0),

            # Debt
            'total_debt': cash_data.get('total_debt', 0),
            'net_cash': cash_data.get('net_cash', 0),
            'net_cash_millions': cash_data.get('net_cash', 0) / 1_000_000,

            # Burn analysis
            'quarterly_burn': cash_data.get('quarterly_cash_burn', 0),
            'quarterly_burn_millions': cash_data.get('quarterly_cash_burn', 0) / 1_000_000,
            'annual_burn': cash_data.get('quarterly_cash_burn', 0) * 4,
            'annual_burn_millions': cash_data.get('quarterly_cash_burn', 0) * 4 / 1_000_000,

            # Runway
            'runway_months': cash_data.get('runway_months', 0),
            'runway_quarters': cash_data.get('runway_months', 0) / 3 if cash_data.get('runway_months') else 0,

            # Trend analysis
            'burn_trend': burn_trend,
            'historical_cash': historical_cash,

            # Relative metrics
            'cash_to_market_cap': (
                cash_data.get('total_cash', 0) / stock_info.get('market_cap', 1)
                if stock_info.get('market_cap', 0) > 0 else 0
            ),

            # Risk assessment
            'runway_risk': self._assess_runway_risk(cash_data.get('runway_months', 0)),

            'analysis_time': datetime.now().isoformat()
        }

        logger.info(f"Cash analysis for {ticker}: ${result['current_cash_millions']:.1f}M, {result['runway_months']:.0f} months runway")
        return result

    def _extract_historical_cash(self, balance_sheet: pd.DataFrame) -> List[Dict]:
        """Extract historical cash positions from balance sheet"""
        historical = []

        if balance_sheet.empty:
            return historical

        try:
            for col in balance_sheet.columns[:4]:  # Last 4 periods
                cash = 0
                if 'Cash And Cash Equivalents' in balance_sheet.index:
                    cash = float(balance_sheet.loc['Cash And Cash Equivalents', col] or 0)

                historical.append({
                    'date': col.strftime('%Y-%m-%d') if hasattr(col, 'strftime') else str(col),
                    'cash': cash,
                    'cash_millions': cash / 1_000_000
                })
        except Exception as e:
            logger.warning(f"Error extracting historical cash: {e}")

        return historical

    def _calculate_burn_trend(self, historical_cash: List[Dict]) -> Dict[str, Any]:
        """Calculate burn rate trend from historical data"""
        if len(historical_cash) < 2:
            return {'trend': 'unknown', 'direction': 0}

        # Calculate changes between periods
        changes = []
        for i in range(len(historical_cash) - 1):
            change = historical_cash[i]['cash'] - historical_cash[i + 1]['cash']
            changes.append(change)

        avg_change = sum(changes) / len(changes) if changes else 0

        if avg_change > 0:
            trend = 'decreasing'  # Cash is going down
            direction = -1
        elif avg_change < 0:
            trend = 'increasing'  # Cash is going up (raises, etc.)
            direction = 1
        else:
            trend = 'stable'
            direction = 0

        return {
            'trend': trend,
            'direction': direction,
            'avg_quarterly_change': avg_change,
            'avg_quarterly_change_millions': avg_change / 1_000_000,
            'periods_analyzed': len(changes)
        }

    def _assess_runway_risk(self, runway_months: float) -> Dict[str, Any]:
        """Assess risk level based on runway"""
        if runway_months <= 0 or runway_months is None:
            return {'level': 'unknown', 'score': 0, 'description': 'Unable to calculate runway'}

        if runway_months < 6:
            return {
                'level': 'critical',
                'score': 1,
                'description': 'Immediate funding needed',
                'color': '#dc2626'
            }
        elif runway_months < 12:
            return {
                'level': 'high',
                'score': 2,
                'description': 'Funding needed within year',
                'color': '#f97316'
            }
        elif runway_months < 18:
            return {
                'level': 'moderate',
                'score': 3,
                'description': 'Manageable but monitor closely',
                'color': '#eab308'
            }
        elif runway_months < 24:
            return {
                'level': 'low',
                'score': 4,
                'description': 'Comfortable runway',
                'color': '#22c55e'
            }
        else:
            return {
                'level': 'minimal',
                'score': 5,
                'description': 'Well funded',
                'color': '#16a34a'
            }

    def compare_cash_positions(self, tickers: List[str]) -> pd.DataFrame:
        """
        Compare cash positions across multiple companies.

        Args:
            tickers: List of ticker symbols

        Returns:
            DataFrame with comparison
        """
        rows = []
        for ticker in tickers:
            analysis = self.analyze_cash_position(ticker)
            rows.append({
                'Ticker': ticker,
                'Cash ($M)': round(analysis['current_cash_millions'], 1),
                'Net Cash ($M)': round(analysis['net_cash_millions'], 1),
                'Quarterly Burn ($M)': round(analysis['quarterly_burn_millions'], 1),
                'Runway (Months)': round(analysis['runway_months'], 0) if analysis['runway_months'] else 'N/A',
                'Risk Level': analysis['runway_risk']['level'].title(),
                'Trend': analysis['burn_trend']['trend'].title()
            })

        return pd.DataFrame(rows)


# Convenience function
def analyze_company_cash(ticker: str) -> Dict[str, Any]:
    """Quick cash analysis for a ticker"""
    analyzer = CashAnalyzer()
    return analyzer.analyze_cash_position(ticker)
