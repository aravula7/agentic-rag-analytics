"""Redis caching utility - Upstash compatible."""

import logging
import json
import hashlib
from typing import Optional, Any
import requests

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache using Upstash REST API."""

    def __init__(
        self,
        rest_url: str,
        rest_token: str,
        ttl: int = 86400
    ):
        """Initialize Upstash Redis cache.
        
        Args:
            rest_url: Upstash REST URL
            rest_token: Upstash REST token
            ttl: Time-to-live in seconds
        """
        self.rest_url = rest_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {rest_token}"}
        self.ttl = ttl
        logger.info(f"RedisCache initialized with Upstash")

    def _generate_key(self, query: str) -> str:
        """Generate cache key from query."""
        return f"query:{hashlib.md5(query.encode()).hexdigest()}"

    def get(self, query: str) -> Optional[dict]:
        """Get cached result for query."""
        key = self._generate_key(query)
        try:
            response = requests.get(
                f"{self.rest_url}/get/{key}",
                headers=self.headers
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('result'):
                    logger.info(f"Cache HIT for query: {query[:50]}...")
                    return json.loads(data['result'])
            logger.info(f"Cache MISS for query: {query[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None

    def set(self, query: str, result: dict):
        """Cache result for query."""
        key = self._generate_key(query)
        try:
            requests.post(
                f"{self.rest_url}/setex/{key}/{self.ttl}",
                headers=self.headers,
                json=json.dumps(result)
            )
            logger.info(f"Cached result for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    def delete(self, query: str):
        """Delete cached result."""
        key = self._generate_key(query)
        try:
            requests.post(
                f"{self.rest_url}/del/{key}",
                headers=self.headers
            )
            logger.info(f"Deleted cache for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def clear_all(self):
        """Clear all cached queries."""
        logger.warning("clear_all not implemented for Upstash REST API")

    def get_stats(self) -> dict:
        """Get cache statistics."""
        try:
            response = requests.get(
                f"{self.rest_url}/dbsize",
                headers=self.headers
            )
            if response.status_code == 200:
                return {"total_keys": response.json().get('result', 0)}
            return {}
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {}