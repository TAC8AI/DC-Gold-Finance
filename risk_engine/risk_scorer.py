"""
Main risk scoring engine for junior gold miners
"""
import yaml
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

from utils.logger import setup_logger
from data_ingestion.data_normalizer import DataNormalizer

logger = setup_logger(__name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')


class RiskScorer:
    """
    Calculates composite risk scores for junior gold miners.

    Scores on 1-5 scale where:
    - 1 = Highest risk
    - 5 = Lowest risk
    """

    def __init__(self):
        self.normalizer = DataNormalizer()
        self.risk_config = self._load_risk_config()

    def _load_risk_config(self) -> Dict:
        """Load risk weights configuration"""
        filepath = os.path.join(CONFIG_DIR, 'risk_weights.yaml')
        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading risk config: {e}")
            return {}

    def score_funding_risk(self, company_data: Dict) -> Dict[str, Any]:
        """
        Score funding risk based on cash runway.

        Args:
            company_data: Normalized company data

        Returns:
            Dictionary with score and details
        """
        runway_months = company_data.get('cash', {}).get('runway_months', 0)
        thresholds = self.risk_config.get('categories', {}).get('funding', {}).get('thresholds', {}).get('runway_months', {})

        if runway_months <= 0:
            score = 1
            level = 'unknown'
            description = 'Unable to calculate runway'
        elif runway_months < thresholds.get('critical', 6):
            score = 1
            level = 'critical'
            description = 'Immediate funding required'
        elif runway_months < thresholds.get('high', 12):
            score = 2
            level = 'high'
            description = 'Funding needed within year'
        elif runway_months < thresholds.get('moderate', 18):
            score = 3
            level = 'moderate'
            description = 'Manageable but monitor'
        elif runway_months < thresholds.get('low', 24):
            score = 4
            level = 'low'
            description = 'Comfortable runway'
        else:
            score = 5
            level = 'minimal'
            description = 'Well funded'

        return {
            'score': score,
            'level': level,
            'description': description,
            'runway_months': runway_months,
            'weight': self.risk_config.get('categories', {}).get('funding', {}).get('weight', 0.25)
        }

    def score_execution_risk(self, company_data: Dict) -> Dict[str, Any]:
        """
        Score execution risk based on project stage.

        Args:
            company_data: Normalized company data

        Returns:
            Dictionary with score and details
        """
        stage = company_data.get('project', {}).get('stage', 'exploration').lower()
        stage_scores = self.risk_config.get('categories', {}).get('execution', {}).get('stage_scores', {})

        score = stage_scores.get(stage, 2)

        stage_descriptions = {
            1: 'Early exploration, high uncertainty',
            2: 'PEA stage, significant technical risk',
            3: 'PFS/FS or permitting, moderate risk',
            4: 'Construction underway, lower risk',
            5: 'Operating mine, proven execution'
        }

        return {
            'score': score,
            'level': ['critical', 'high', 'moderate', 'low', 'minimal'][score - 1],
            'description': stage_descriptions.get(score, 'Unknown stage'),
            'stage': stage,
            'weight': self.risk_config.get('categories', {}).get('execution', {}).get('weight', 0.25)
        }

    def score_commodity_risk(self, company_data: Dict) -> Dict[str, Any]:
        """
        Score commodity price risk based on AISC.

        Args:
            company_data: Normalized company data

        Returns:
            Dictionary with score and details
        """
        aisc = company_data.get('project', {}).get('aisc_per_oz', 1200)
        thresholds = self.risk_config.get('categories', {}).get('commodity', {}).get('thresholds', {}).get('aisc', {})

        if aisc > thresholds.get('critical', 1600):
            score = 1
            level = 'critical'
            description = 'Marginal at current prices'
        elif aisc > thresholds.get('high', 1400):
            score = 2
            level = 'high'
            description = 'Limited margin'
        elif aisc > thresholds.get('moderate', 1200):
            score = 3
            level = 'moderate'
            description = 'Reasonable margin'
        elif aisc > thresholds.get('low', 1000):
            score = 4
            level = 'low'
            description = 'Strong margin'
        else:
            score = 5
            level = 'minimal'
            description = 'Excellent margin'

        return {
            'score': score,
            'level': level,
            'description': description,
            'aisc': aisc,
            'weight': self.risk_config.get('categories', {}).get('commodity', {}).get('weight', 0.20)
        }

    def score_control_risk(self, company_data: Dict) -> Dict[str, Any]:
        """
        Score management/control risk.

        Uses manual overrides from config or defaults.

        Args:
            company_data: Normalized company data

        Returns:
            Dictionary with score and details
        """
        ticker = company_data.get('ticker', '')
        overrides = self.risk_config.get('company_overrides', {})

        # Check for company-specific override
        score = overrides.get(ticker, {}).get('control', 3)

        control_descriptions = {
            1: 'Unproven team, governance concerns',
            2: 'Mixed track record',
            3: 'Competent, standard alignment',
            4: 'Strong team, good track record',
            5: 'Proven operators, exceptional'
        }

        return {
            'score': score,
            'level': ['critical', 'high', 'moderate', 'low', 'minimal'][score - 1],
            'description': control_descriptions.get(score, 'Unknown'),
            'weight': self.risk_config.get('categories', {}).get('control', {}).get('weight', 0.15)
        }

    def score_timing_risk(self, company_data: Dict) -> Dict[str, Any]:
        """
        Score timing risk based on years to production.

        Args:
            company_data: Normalized company data

        Returns:
            Dictionary with score and details
        """
        years_to_production = company_data.get('calculated', {}).get('years_to_production', 5)
        thresholds = self.risk_config.get('categories', {}).get('timing', {}).get('thresholds', {}).get('years_to_production', {})

        if years_to_production >= thresholds.get('critical', 5):
            score = 1
            level = 'critical'
            description = 'Long timeline, high uncertainty'
        elif years_to_production >= thresholds.get('high', 4):
            score = 2
            level = 'high'
            description = 'Extended timeline'
        elif years_to_production >= thresholds.get('moderate', 3):
            score = 3
            level = 'moderate'
            description = 'Moderate timeline'
        elif years_to_production >= thresholds.get('low', 2):
            score = 4
            level = 'low'
            description = 'Near-term production'
        else:
            score = 5
            level = 'minimal'
            description = 'Producing or imminent'

        return {
            'score': score,
            'level': level,
            'description': description,
            'years_to_production': years_to_production,
            'weight': self.risk_config.get('categories', {}).get('timing', {}).get('weight', 0.15)
        }

    def calculate_composite_score(self, ticker: str) -> Dict[str, Any]:
        """
        Calculate weighted composite risk score for a company.

        Args:
            ticker: Company ticker symbol

        Returns:
            Dictionary with composite score and category breakdowns
        """
        company_data = self.normalizer.get_normalized_company_data(ticker)

        if 'error' in company_data:
            return {'ticker': ticker, 'error': company_data['error']}

        # Score each category
        funding = self.score_funding_risk(company_data)
        execution = self.score_execution_risk(company_data)
        commodity = self.score_commodity_risk(company_data)
        control = self.score_control_risk(company_data)
        timing = self.score_timing_risk(company_data)

        categories = {
            'funding': funding,
            'execution': execution,
            'commodity': commodity,
            'control': control,
            'timing': timing
        }

        # Calculate weighted composite
        composite_score = sum(
            cat['score'] * cat['weight']
            for cat in categories.values()
        )

        # Interpret overall score
        interpretation = self._interpret_score(composite_score)

        result = {
            'ticker': ticker,
            'company_name': company_data.get('name', ticker),

            'composite_score': round(composite_score, 2),
            'interpretation': interpretation,

            'categories': categories,

            # Individual scores for quick access
            'funding_score': funding['score'],
            'execution_score': execution['score'],
            'commodity_score': commodity['score'],
            'control_score': control['score'],
            'timing_score': timing['score'],

            # Lowest scoring category (biggest risk)
            'weakest_category': min(categories.items(), key=lambda x: x[1]['score'])[0],
            'weakest_score': min(cat['score'] for cat in categories.values()),

            'analysis_time': datetime.now().isoformat()
        }

        logger.info(f"Risk score for {ticker}: {composite_score:.2f} ({interpretation['level']})")
        return result

    def _interpret_score(self, score: float) -> Dict[str, str]:
        """Interpret composite score into overall risk assessment"""
        interpretations = self.risk_config.get('overall_score_interpretation', {})

        if score < 1.5:
            return {
                'level': 'Very High Risk',
                'description': 'Speculative investment with significant concerns',
                'color': '#dc2626'
            }
        elif score < 2.5:
            return {
                'level': 'High Risk',
                'description': 'Significant concerns require monitoring',
                'color': '#f97316'
            }
        elif score < 3.5:
            return {
                'level': 'Moderate Risk',
                'description': 'Manageable risk profile',
                'color': '#eab308'
            }
        elif score < 4.5:
            return {
                'level': 'Low Risk',
                'description': 'Favorable risk characteristics',
                'color': '#22c55e'
            }
        else:
            return {
                'level': 'Minimal Risk',
                'description': 'Strong position across all categories',
                'color': '#16a34a'
            }

    def compare_risk_scores(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Compare risk scores across multiple companies.

        Args:
            tickers: List of ticker symbols

        Returns:
            Comparison data
        """
        scores = {}
        for ticker in tickers:
            scores[ticker] = self.calculate_composite_score(ticker)

        # Rank by composite score (higher is better/lower risk)
        ranked = sorted(
            [(t, s['composite_score']) for t, s in scores.items() if 'error' not in s],
            key=lambda x: x[1],
            reverse=True
        )

        return {
            'scores': scores,
            'ranking': [{'rank': i+1, 'ticker': t, 'score': s} for i, (t, s) in enumerate(ranked)],
            'lowest_risk': ranked[0][0] if ranked else None,
            'highest_risk': ranked[-1][0] if ranked else None,
            'comparison_time': datetime.now().isoformat()
        }


# Convenience function
def score_company_risk(ticker: str) -> Dict[str, Any]:
    """Quick risk scoring for a ticker"""
    scorer = RiskScorer()
    return scorer.calculate_composite_score(ticker)
