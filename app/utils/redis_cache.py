"""Redis caching utility - Two-layer caching strategy."""

import logging
import json
import hashlib
from typing import Optional, Any, Dict
import requests

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache with two-layer strategy: SQL + Results."""

    def __init__(
        self,
        rest_url: str,
        rest_token: str,
        ttl: int = 86400
    ):
        """Initialize Upstash Redis cache."""
        self.rest_url = rest_url.rstrip('/')
        self.headers = {"Authorization": f"Bearer {rest_token}"}
        self.ttl = ttl
        logger.info("RedisCache initialized with two-layer caching")

    def _generate_key(self, prefix: str, query: str) -> str:
        """Generate cache key with prefix."""
        hash_value = hashlib.md5(query.encode()).hexdigest()
        return f"{prefix}:{hash_value}"

    def get_sql(self, query: str) -> Optional[str]:
        """Get cached SQL query."""
        key = self._generate_key("sql_v2", query)
        try:
            response = requests.get(
                f"{self.rest_url}/get/{key}",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result')
                if result:
                    logger.info(f"SQL cache HIT for query: {query[:50]}...")
                    return result
            logger.info(f"SQL cache MISS for query: {query[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Redis get_sql error: {e}")
            return None

    def set_sql(self, query: str, sql: str):
        """Cache generated SQL query."""
        key = self._generate_key("sql_v2", query)
        try:
            response = requests.post(
                f"{self.rest_url}/set/{key}",
                headers=self.headers,
                data=sql,
                timeout=5
            )
            
            if response.status_code == 200:
                requests.post(
                    f"{self.rest_url}/expire/{key}/{self.ttl}",
                    headers=self.headers,
                    timeout=5
                )
                logger.info(f"Cached SQL for query: {query[:50]}...")
            else:
                logger.error(f"Failed to cache SQL: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Redis set_sql error: {e}")

    def get_result(self, query: str) -> Optional[dict]:
        """Get cached query result."""
        key = self._generate_key("result_v2", query)
        try:
            response = requests.post(
                f"{self.rest_url}/json.get/{key}",
                headers=self.headers,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                result = data.get('result')
                if result is not None:
                    logger.info(f"Result cache HIT for query: {query[:50]}...")
                    if isinstance(result, dict):
                        return result
                    else:
                        logger.error(f"Unexpected cached result type: {type(result)}")
                        return None
                    
            logger.info(f"Result cache MISS for query: {query[:50]}...")
            return None
        except Exception as e:
            logger.error(f"Redis get_result error: {e}")
            return None

    def set_result(self, query: str, result: dict):
        """Cache query result."""
        key = self._generate_key("result_v2", query)
        try:
            response = requests.post(
                f"{self.rest_url}/json.set/{key}/$/",
                headers=self.headers,
                json=result,
                timeout=5
            )
            
            if response.status_code == 200:
                requests.post(
                    f"{self.rest_url}/expire/{key}/{self.ttl}",
                    headers=self.headers,
                    timeout=5
                )
                logger.info(f"Cached result for query: {query[:50]}...")
            else:
                logger.error(f"Failed to cache result: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Redis set_result error: {e}")

    def delete(self, query: str):
        """Delete both SQL and result caches."""
        for prefix in ["sql_v2", "result_v2"]:
            key = self._generate_key(prefix, query)
            try:
                requests.post(
                    f"{self.rest_url}/del/{key}",
                    headers=self.headers,
                    timeout=5
                )
            except Exception as e:
                logger.error(f"Redis delete error: {e}")

    def clear_all(self):
        """Clear all caches."""
        logger.warning("Clearing all cache keys")
        try:
            response = requests.post(
                f"{self.rest_url}/keys/*",
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                keys = response.json().get('result', [])
                for key in keys:
                    requests.post(
                        f"{self.rest_url}/del/{key}",
                        headers=self.headers,
                        timeout=5
                    )
                logger.info(f"Cleared {len(keys)} cache keys")
        except Exception as e:
            logger.error(f"Redis clear_all error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            response = requests.get(
                f"{self.rest_url}/dbsize",
                headers=self.headers,
                timeout=5
            )
            if response.status_code == 200:
                total_keys = response.json().get('result', 0)
                return {
                    "total_keys": total_keys,
                    "estimated_sql_cache": total_keys // 2,
                    "estimated_result_cache": total_keys // 2
                }
            return {}
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {}