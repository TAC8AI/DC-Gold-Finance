"""
Data Ingestion Module
Handles fetching and normalizing data from external sources
"""
from data_ingestion.yfinance_fetcher import YFinanceFetcher, fetch_company_data
from data_ingestion.gold_price_fetcher import GoldPriceFetcher, get_gold_price, get_gold_data
from data_ingestion.data_normalizer import DataNormalizer, get_all_company_data, get_comparison_table
from data_ingestion.cache_manager import CacheManager, get_cache

__all__ = [
    'YFinanceFetcher',
    'fetch_company_data',
    'GoldPriceFetcher',
    'get_gold_price',
    'get_gold_data',
    'DataNormalizer',
    'get_all_company_data',
    'get_comparison_table',
    'CacheManager',
    'get_cache'
]
