"""Redis caching utility."""

import logging
import json
import hashlib
from typing import Optional, Any
import redis

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache for query results."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6380,
        password: Optional[str] = None,
        ttl: int = 86400
    ):
        """Initialize Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            password: Redis password
            ttl: Time-to-live in seconds
        """
        self.ttl = ttl
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            password=password,
            decode_responses=True
        )
        logger.info(f"RedisCache initialized: {host}:{port}")

    def _generate_key(self, query: str) -> str:
        """Generate cache key from query.
        
        Args:
            query: User query string
            
        Returns:
            MD5 hash of query
        """
        return f"query:{hashlib.md5(query.encode()).hexdigest()}"

    def get(self, query: str) -> Optional[dict]:
        """Get cached result for query.
        
        Args:
            query: User query string
            
        Returns:
            Cached result dict or None
        """
        key = self._generate_key(query)
        try:
            cached = self.redis_client.get(key)
            if cached:
                logger.info(f"Cache HIT for query: {query[:50]}...")
                return json.loads(cached)
            else:
                logger.info(f"Cache MISS for query: {query[:50]}...")
                return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, query: str, result: dict):
        """Cache result for query.
        
        Args:
            query: User query string
            result: Result dictionary to cache
        """
        key = self._generate_key(query)
        try:
            self.redis_client.setex(
                key,
                self.ttl,
                json.dumps(result)
            )
            logger.info(f"Cached result for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, query: str):
        """Delete cached result.
        
        Args:
            query: User query string
        """
        key = self._generate_key(query)
        try:
            self.redis_client.delete(key)
            logger.info(f"Deleted cache for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def clear_all(self):
        """Clear all cached queries."""
        try:
            for key in self.redis_client.scan_iter("query:*"):
                self.redis_client.delete(key)
            logger.info("Cleared all cached queries")
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics.
        
        Returns:
            Dict with cache stats
        """
        try:
            info = self.redis_client.info()
            total_keys = self.redis_client.dbsize()
            return {
                "total_keys": total_keys,
                "memory_used_mb": info.get('used_memory', 0) / (1024 * 1024),
                "hits": info.get('keyspace_hits', 0),
                "misses": info.get('keyspace_misses', 0)
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {}