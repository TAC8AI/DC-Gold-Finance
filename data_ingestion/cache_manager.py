"""
Local caching with TTL for API responses
"""
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional
import pandas as pd

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Default cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')

# Default TTL in minutes
DEFAULT_TTL_MINUTES = 15


class CacheManager:
    """Manages local file-based caching with TTL"""

    def __init__(self, cache_dir: str = CACHE_DIR, ttl_minutes: int = DEFAULT_TTL_MINUTES):
        self.cache_dir = cache_dir
        self.ttl = timedelta(minutes=ttl_minutes)
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            logger.info(f"Created cache directory: {self.cache_dir}")

    def _get_cache_key(self, key: str) -> str:
        """Generate a safe filename from cache key"""
        return hashlib.md5(key.encode()).hexdigest()

    def _get_cache_path(self, key: str) -> str:
        """Get full path to cache file"""
        return os.path.join(self.cache_dir, f"{self._get_cache_key(key)}.json")

    def _is_expired(self, cache_time: datetime) -> bool:
        """Check if cached data has expired"""
        return datetime.now() - cache_time > self.ttl

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieve cached data if it exists and hasn't expired.

        Args:
            key: Cache key identifier

        Returns:
            Cached data or None if not found/expired
        """
        cache_path = self._get_cache_path(key)

        if not os.path.exists(cache_path):
            logger.debug(f"Cache miss: {key}")
            return None

        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)

            cache_time = datetime.fromisoformat(cached['timestamp'])

            if self._is_expired(cache_time):
                logger.debug(f"Cache expired: {key}")
                return None

            logger.debug(f"Cache hit: {key}")
            return cached['data']

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Cache read error for {key}: {e}")
            return None

    def set(self, key: str, data: Any) -> bool:
        """
        Store data in cache.

        Args:
            key: Cache key identifier
            data: Data to cache (must be JSON serializable)

        Returns:
            True if successful
        """
        cache_path = self._get_cache_path(key)

        try:
            # Handle pandas DataFrames
            if isinstance(data, pd.DataFrame):
                serializable_data = {
                    '_type': 'dataframe',
                    'data': data.to_dict(orient='split')
                }
            elif isinstance(data, pd.Series):
                serializable_data = {
                    '_type': 'series',
                    'data': data.to_dict()
                }
            else:
                serializable_data = data

            cache_entry = {
                'timestamp': datetime.now().isoformat(),
                'data': serializable_data
            }

            with open(cache_path, 'w') as f:
                json.dump(cache_entry, f, default=str)

            logger.debug(f"Cache set: {key}")
            return True

        except (TypeError, ValueError) as e:
            logger.warning(f"Cache write error for {key}: {e}")
            return False

    def invalidate(self, key: str) -> bool:
        """Remove specific cache entry"""
        cache_path = self._get_cache_path(key)
        if os.path.exists(cache_path):
            os.remove(cache_path)
            logger.debug(f"Cache invalidated: {key}")
            return True
        return False

    def clear_all(self) -> int:
        """Clear all cached data. Returns count of removed files."""
        count = 0
        for filename in os.listdir(self.cache_dir):
            if filename.endswith('.json'):
                os.remove(os.path.join(self.cache_dir, filename))
                count += 1
        logger.info(f"Cleared {count} cache entries")
        return count

    def get_stats(self) -> dict:
        """Get cache statistics"""
        files = [f for f in os.listdir(self.cache_dir) if f.endswith('.json')]
        total_size = sum(
            os.path.getsize(os.path.join(self.cache_dir, f))
            for f in files
        )
        return {
            'entries': len(files),
            'size_bytes': total_size,
            'size_mb': round(total_size / (1024 * 1024), 2),
            'ttl_minutes': self.ttl.total_seconds() / 60
        }


# Global cache instance
_cache = None

def get_cache() -> CacheManager:
    """Get or create global cache instance"""
    global _cache
    if _cache is None:
        _cache = CacheManager()
    return _cache
