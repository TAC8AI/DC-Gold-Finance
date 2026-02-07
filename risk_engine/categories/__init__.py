"""
Risk category scorers - individual modules for each risk category.

The main risk_scorer.py handles all categories, but these can be
extended for more complex category-specific logic.
"""

# Categories are handled in the main risk_scorer.py
# This package can be extended for more complex category scoring

RISK_CATEGORIES = [
    'funding',
    'execution',
    'commodity',
    'control',
    'timing'
]

CATEGORY_WEIGHTS = {
    'funding': 0.25,
    'execution': 0.25,
    'commodity': 0.20,
    'control': 0.15,
    'timing': 0.15
}
