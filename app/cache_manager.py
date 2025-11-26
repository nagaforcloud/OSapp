# app/cache_manager.py
"""
Advanced caching system for the Onestream RAG application.
Provides multi-level caching with Redis, memory, and file-based caching.
"""

import json
import time
import hashlib
import pickle
import asyncio
from typing import Any, Optional, Dict, Union, List
from functools import wraps, lru_cache
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from app.config import REDIS_HOST, REDIS_PORT, REDIS_DB, CACHE_TTL
except ImportError:
    REDIS_HOST = "localhost"
    REDIS_PORT = 6379
    REDIS_DB = 0
    CACHE_TTL = 3600

from app.enhanced_logger import get_current_context, info, debug, warning


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    data: Any
    timestamp: float
    ttl: int
    hit_count: int = 0
    metadata: Dict[str, Any] = None

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        return time.time() > (self.timestamp + self.ttl)

    def increment_hit(self):
        """Increment hit counter."""
        self.hit_count += 1


class CacheManager:
    """Advanced cache manager with multiple backends."""

    def __init__(self, redis_url: str = None, memory_size: int = 1000):
        """
        Initialize cache manager.

        Args:
            redis_url: Redis connection URL
            memory_size: Maximum number of items in memory cache
        """
        self.redis_url = redis_url or f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        self.memory_size = memory_size
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.cache_stats = {
            'memory_hits': 0,
            'redis_hits': 0,
            'misses': 0,
            'total_requests': 0
        }
        self.lock = threading.RLock()

        # Initialize Redis if available
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
                self.redis_client.ping()
                info("Redis cache initialized", component="cache_manager")
            except Exception as e:
                warning(f"Redis cache unavailable: {e}", component="cache_manager")
                self.redis_client = None

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        self.cache_stats['total_requests'] += 1
        context = get_current_context()

        # Try memory cache first
        with self.lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if not entry.is_expired():
                    entry.increment_hit()
                    self.cache_stats['memory_hits'] += 1
                    debug("Memory cache hit", cache_key=key, component="cache_manager", **context)
                    return entry.data
                else:
                    # Remove expired entry
                    del self.memory_cache[key]

        # Try Redis cache
        if self.redis_client:
            try:
                cached_data = self.redis_client.get(key)
                if cached_data:
                    entry = pickle.loads(cached_data)
                    if not entry.is_expired():
                        # Cache in memory for faster access
                        with self.lock:
                            if len(self.memory_cache) < self.memory_size:
                                self.memory_cache[key] = entry
                        entry.increment_hit()
                        self.cache_stats['redis_hits'] += 1
                        debug("Redis cache hit", cache_key=key, component="cache_manager", **context)
                        return entry.data
                    else:
                        # Remove expired entry from Redis
                        self.redis_client.delete(key)
            except Exception as e:
                warning(f"Redis cache error: {e}", cache_key=key, component="cache_manager", **context)

        self.cache_stats['misses'] += 1
        debug("Cache miss", cache_key=key, component="cache_manager", **context)
        return None

    def set(self, key: str, value: Any, ttl: int = CACHE_TTL, metadata: Dict[str, Any] = None):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            metadata: Additional metadata
        """
        context = get_current_context()
        entry = CacheEntry(
            data=value,
            timestamp=time.time(),
            ttl=ttl,
            metadata=metadata or {}
        )

        # Set in memory cache
        with self.lock:
            # LRU eviction if memory cache is full
            if len(self.memory_cache) >= self.memory_size:
                # Remove oldest entry
                oldest_key = min(self.memory_cache.keys(),
                                key=lambda k: self.memory_cache[k].timestamp)
                del self.memory_cache[oldest_key]

            self.memory_cache[key] = entry

        # Set in Redis cache
        if self.redis_client:
            try:
                serialized_data = pickle.dumps(entry)
                self.redis_client.setex(key, ttl, serialized_data)
                debug("Cache set", cache_key=key, ttl=ttl, component="cache_manager", **context)
            except Exception as e:
                warning(f"Redis cache set error: {e}", cache_key=key, component="cache_manager", **context)

    def delete(self, key: str):
        """Delete entry from cache."""
        with self.lock:
            if key in self.memory_cache:
                del self.memory_cache[key]

        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                warning(f"Redis cache delete error: {e}", cache_key=key, component="cache_manager")

    def clear(self):
        """Clear all cache entries."""
        with self.lock:
            self.memory_cache.clear()

        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                warning(f"Redis cache clear error: {e}", component="cache_manager")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = self.cache_stats['memory_hits'] + self.cache_stats['redis_hits']
        hit_rate = (total_hits / self.cache_stats['total_requests'] * 100) if self.cache_stats['total_requests'] > 0 else 0

        return {
            **self.cache_stats,
            'hit_rate_percent': round(hit_rate, 2),
            'memory_cache_size': len(self.memory_cache),
            'redis_available': self.redis_client is not None
        }


# Global cache manager instance
cache_manager = CacheManager()


def cache_result(prefix: str = "cache", ttl: int = CACHE_TTL,
                cache_args: bool = True, cache_kwargs: bool = True):
    """
    Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
        cache_args: Whether to include function arguments in cache key
        cache_kwargs: Whether to include keyword arguments in cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_args_list = args if cache_args else ()
            cache_kwargs_dict = kwargs if cache_kwargs else {}
            cache_key = cache_manager._generate_key(prefix, func.__name__, *cache_args_list, **cache_kwargs_dict)

            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                metadata = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                cache_manager.set(cache_key, result, ttl, metadata)
                return result
            except Exception as e:
                # Don't cache on error
                raise

        # Add cache management methods to function
        wrapper.cache_clear = lambda: cache_manager.clear()
        wrapper.cache_delete = lambda *args, **kwargs: cache_manager.delete(
            cache_manager._generate_key(prefix, func.__name__,
                                      args if cache_args else (),
                                      kwargs if cache_kwargs else {})
        )
        wrapper.cache_stats = lambda: cache_manager.get_stats()

        return wrapper
    return decorator


def async_cache_result(prefix: str = "async_cache", ttl: int = CACHE_TTL):
    """
    Decorator for caching async function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = cache_manager._generate_key(prefix, func.__name__, *args, **kwargs)

            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute async function and cache result
            try:
                result = await func(*args, **kwargs)
                metadata = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'async': True,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                cache_manager.set(cache_key, result, ttl, metadata)
                return result
            except Exception as e:
                raise

        return wrapper
    return decorator


# Memory-only LRU cache for small, frequently accessed data
@lru_cache(maxsize=128)
def fast_cache(key: str) -> Any:
    """Fast in-memory cache for small data."""
    # This will be replaced by actual data
    return None


class CacheWarmer:
    """Cache warming utility for pre-loading frequently accessed data."""

    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    async def warm_embeddings_cache(self, texts: List[str], embedding_function):
        """Warm up embeddings cache."""
        info(f"Warming embeddings cache for {len(texts)} texts")

        with ThreadPoolExecutor(max_workers=4) as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, self._cache_embedding, text, embedding_function)
                for text in texts[:50]  # Limit to prevent overwhelming
            ]
            await asyncio.gather(*tasks)

    def _cache_embedding(self, text: str, embedding_function):
        """Cache single embedding."""
        cache_key = cache_manager._generate_key("embedding", text)
        if cache_manager.get(cache_key) is None:
            embedding = embedding_function(text)
            cache_manager.set(cache_key, embedding, ttl=7200)  # 2 hours

    def warm_document_cache(self, document_ids: List[str], document_loader):
        """Warm up document cache."""
        info(f"Warming document cache for {len(document_ids)} documents")

        for doc_id in document_ids[:20]:  # Limit to prevent overwhelming
            cache_key = cache_manager._generate_key("document", doc_id)
            if cache_manager.get(cache_key) is None:
                try:
                    document = document_loader(doc_id)
                    cache_manager.set(cache_key, document, ttl=3600)
                except Exception as e:
                    warning(f"Failed to warm cache for document {doc_id}: {e}")


# Global cache warmer
cache_warmer = CacheWarmer(cache_manager)