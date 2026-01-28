"""Redis caching utility for query results."""

import logging
import json
import hashlib
from typing import Optional, Any, Dict
import requests

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache for query results."""

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
        logger.info("RedisCache initialized")

    def _normalize_query(self, query: Optional[str]) -> str:
        """Normalize query so semantically identical prompts map to same cache key."""
        # lower + collapse whitespace + trim
        return " ".join((query or "").split()).strip().lower()

    def _generate_key(self, prefix: str, query: str) -> str:
        """Generate cache key with prefix (stable + collision-resistant)."""
        normalized = self._normalize_query(query)
        hash_value = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        logger.info(f"[CACHE-KEY] prefix={prefix} raw_len={len(query or '')} normalized_len={len(normalized)} normalized_preview={normalized[:120]!r}")
        return f"{prefix}:{hash_value}"

    def get_result(self, query: str) -> Optional[dict]:
        """Get cached query result."""
        key = self._generate_key("result_v2", query)
        try:
            response = requests.post(
                f"{self.rest_url}/json.get/{key}",
                headers=self.headers,
                timeout=5
            )

            if response.status_code != 200:
                logger.info(f"Result cache MISS key={key} query_preview={query[:50]!r} status={response.status_code}")
                return None

            data = response.json()
            result = data.get("result", None)

            # Upstash returns result=None when key doesn't exist
            if result is None:
                logger.info(f"Result cache MISS key={key} query_preview={query[:50]!r}")
                return None

            logger.info(f"Result cache HIT key={key} query_preview={query[:50]!r}")

            # Upstash may return dict or JSON string depending on command/plan
            if isinstance(result, dict):
                return result

            if isinstance(result, str):
                # Some Upstash responses can be "null" (string) too
                if result.strip().lower() == "null":
                    logger.info(f"Result cache MISS (null string) key={key} query_preview={query[:50]!r}")
                    return None
                try:
                    return json.loads(result)
                except Exception:
                    logger.error(f"Cached result was a string but not valid JSON key={key}")
                    return None

            logger.error(f"Unexpected cached result type: {type(result)} key={key}")
            return None

        except Exception as e:
            logger.error(f"Redis get_result error: {e}")
            return None


    def set_result(self, query: str, result: Dict[str, Any]):
        """Cache query result payload."""
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
                logger.info(f"Cached result key={key} query_preview={query[:50]!r}")
            else:
                logger.error(f"Failed to cache result: {response.status_code} - {response.text}")
        except Exception as e:
            logger.error(f"Redis set_result error: {e}")

    def delete(self, query: str):
        """Delete result cache for a query."""
        key = self._generate_key("result_v2", query)
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
                return {"total_keys": total_keys}
            return {}
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {}
