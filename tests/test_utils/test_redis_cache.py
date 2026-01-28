"""Tests for the Redis cache utility."""

import json
import hashlib
import pytest
from unittest.mock import Mock, MagicMock, patch

from app.utils.redis_cache import RedisCache


class TestRedisCacheInitialization:
    """Test cases for RedisCache initialization."""

    def test_redis_cache_initialization(self):
        """Test RedisCache initializes correctly."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token",
            ttl=3600
        )

        assert cache.rest_url == "https://test-redis.upstash.io"
        assert cache.ttl == 3600
        assert cache.headers["Authorization"] == "Bearer test-token"

    def test_redis_cache_strips_trailing_slash(self):
        """Test that trailing slash is stripped from URL."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io/",
            rest_token="test-token"
        )

        assert cache.rest_url == "https://test-redis.upstash.io"

    def test_redis_cache_default_ttl(self):
        """Test default TTL is 86400 seconds."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        assert cache.ttl == 86400


class TestRedisCacheKeyGeneration:
    """Test cases for cache key generation."""

    def test_generate_key_deterministic(self):
        """Test that same query generates same key."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        key1 = cache._generate_key("result_v2", "Show top customers")
        key2 = cache._generate_key("result_v2", "Show top customers")

        assert key1 == key2

    def test_generate_key_uses_sha256(self):
        """Test that key uses SHA256 hash."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        key = cache._generate_key("result_v2", "Show top customers")

        expected_hash = hashlib.sha256("show top customers".encode("utf-8")).hexdigest()
        assert key == f"result_v2:{expected_hash}"

    def test_generate_key_different_queries(self):
        """Test that different queries generate different keys."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        key1 = cache._generate_key("result_v2", "Show top customers")
        key2 = cache._generate_key("result_v2", "List all products")

        assert key1 != key2

    def test_generate_key_different_prefixes(self):
        """Test that different prefixes generate different keys."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        key1 = cache._generate_key("sql_v2", "Show top customers")
        key2 = cache._generate_key("result_v2", "Show top customers")

        assert key1 != key2


class TestRedisCacheNormalization:
    """Test cases for query normalization."""

    def test_normalize_query_lowercase(self):
        """Test that queries are lowercased."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        result = cache._normalize_query("SHOW TOP CUSTOMERS")

        assert result == "show top customers"

    def test_normalize_query_collapses_whitespace(self):
        """Test that extra whitespace is collapsed."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        result = cache._normalize_query("show   top   customers")

        assert result == "show top customers"

    def test_normalize_query_strips_whitespace(self):
        """Test that leading/trailing whitespace is stripped."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        result = cache._normalize_query("  show top customers  ")

        assert result == "show top customers"

    def test_normalize_query_handles_none(self):
        """Test that None query returns empty string."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        result = cache._normalize_query(None)

        assert result == ""

    def test_normalize_query_handles_empty_string(self):
        """Test that empty string returns empty string."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        result = cache._normalize_query("")

        assert result == ""

    def test_normalize_query_equivalent_queries(self):
        """Test that semantically identical queries normalize to same value."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        q1 = cache._normalize_query("Show top customers")
        q2 = cache._normalize_query("  show  top  customers  ")
        q3 = cache._normalize_query("SHOW TOP CUSTOMERS")

        assert q1 == q2 == q3


class TestRedisCacheGetResult:
    """Test cases for get_result method."""

    def test_get_result_cache_hit_dict(self, mock_upstash_response):
        """Test cache hit when Upstash returns dict."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        cached_data = {"query": "test", "sql": "SELECT 1", "s3_url": "http://example.com"}

        with patch('requests.post', return_value=mock_upstash_response(cached_data)):
            result = cache.get_result("test query")

        assert result is not None
        assert result["query"] == "test"

    def test_get_result_cache_hit_json_string(self, mock_upstash_response):
        """Test cache hit when Upstash returns JSON string."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        cached_data = json.dumps({"query": "test", "sql": "SELECT 1"})

        with patch('requests.post', return_value=mock_upstash_response(cached_data)):
            result = cache.get_result("test query")

        assert result is not None
        assert result["query"] == "test"

    def test_get_result_cache_miss_none(self, mock_upstash_response):
        """Test cache miss when result is None."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', return_value=mock_upstash_response(None)):
            result = cache.get_result("nonexistent query")

        assert result is None

    def test_get_result_cache_miss_null_string(self, mock_upstash_response):
        """Test cache miss when result is 'null' string."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', return_value=mock_upstash_response("null")):
            result = cache.get_result("test query")

        assert result is None

    def test_get_result_cache_miss_status_not_200(self):
        """Test cache miss when HTTP status is not 200."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('requests.post', return_value=mock_response):
            result = cache.get_result("test query")

        assert result is None

    def test_get_result_handles_request_error(self):
        """Test that request errors return None."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', side_effect=Exception("Connection timeout")):
            result = cache.get_result("test query")

        assert result is None

    def test_get_result_handles_invalid_json_string(self, mock_upstash_response):
        """Test that invalid JSON string returns None."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', return_value=mock_upstash_response("not valid json {")):
            result = cache.get_result("test query")

        assert result is None

    def test_get_result_handles_unexpected_type(self, mock_upstash_response):
        """Test that unexpected result types return None."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', return_value=mock_upstash_response(12345)):
            result = cache.get_result("test query")

        assert result is None


class TestRedisCacheSetResult:
    """Test cases for set_result method."""

    def test_set_result_success(self):
        """Test successful result caching."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token",
            ttl=3600
        )

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch('requests.post', return_value=mock_response) as mock_post:
            cache.set_result("test query", {"sql": "SELECT 1"})

        # Should make two requests: json.set and expire
        assert mock_post.call_count == 2

        # Verify expire call
        expire_call = mock_post.call_args_list[1]
        assert "/expire/" in expire_call[0][0]
        assert "/3600" in expire_call[0][0]

    def test_set_result_failure(self):
        """Test result caching when set fails."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"

        with patch('requests.post', return_value=mock_response) as mock_post:
            # Should not raise
            cache.set_result("test query", {"sql": "SELECT 1"})

        # Should only make one request (json.set, no expire on failure)
        assert mock_post.call_count == 1

    def test_set_result_handles_exception(self):
        """Test that set_result handles exceptions gracefully."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', side_effect=Exception("Network error")):
            # Should not raise
            cache.set_result("test query", {"sql": "SELECT 1"})


class TestRedisCacheDelete:
    """Test cases for delete method."""

    def test_delete_success(self):
        """Test successful cache deletion."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post') as mock_post:
            cache.delete("test query")

        assert mock_post.call_count == 1
        call_url = mock_post.call_args[0][0]
        assert "/del/" in call_url

    def test_delete_handles_exception(self):
        """Test that delete handles exceptions gracefully."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', side_effect=Exception("Network error")):
            # Should not raise
            cache.delete("test query")


class TestRedisCacheClearAll:
    """Test cases for clear_all method."""

    def test_clear_all_success(self):
        """Test successful cache clearing."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        keys_response = MagicMock()
        keys_response.status_code = 200
        keys_response.json.return_value = {"result": ["key1", "key2", "key3"]}

        del_response = MagicMock()
        del_response.status_code = 200

        with patch('requests.post', side_effect=[keys_response, del_response, del_response, del_response]):
            cache.clear_all()

    def test_clear_all_no_keys(self):
        """Test clear_all when no keys exist."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        keys_response = MagicMock()
        keys_response.status_code = 200
        keys_response.json.return_value = {"result": []}

        with patch('requests.post', return_value=keys_response):
            # Should not raise
            cache.clear_all()

    def test_clear_all_handles_exception(self):
        """Test that clear_all handles exceptions gracefully."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.post', side_effect=Exception("Network error")):
            # Should not raise
            cache.clear_all()


class TestRedisCacheStats:
    """Test cases for get_stats method."""

    def test_get_stats_success(self):
        """Test successful stats retrieval."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 42}

        with patch('requests.get', return_value=mock_response):
            stats = cache.get_stats()

        assert stats["total_keys"] == 42

    def test_get_stats_failure(self):
        """Test stats retrieval when request fails."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('requests.get', return_value=mock_response):
            stats = cache.get_stats()

        assert stats == {}

    def test_get_stats_handles_exception(self):
        """Test that get_stats handles exceptions gracefully."""
        cache = RedisCache(
            rest_url="https://test-redis.upstash.io",
            rest_token="test-token"
        )

        with patch('requests.get', side_effect=Exception("Network error")):
            stats = cache.get_stats()

        assert stats == {}
