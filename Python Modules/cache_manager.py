import hashlib
import json
import time
from typing import Dict, Any, Optional, Tuple

class CacheManager:
    """
    Simple in-memory cache for LLM responses to reduce redundant API calls.
    """
    
    def __init__(self, ttl: int = 3600):
        """
        Initialize the cache manager.
        
        Args:
            ttl: Time-to-live for cache entries in seconds (default: 1 hour)
        """
        self.cache = {}  # In-memory cache
        self.ttl = ttl   # Cache TTL in seconds
    
    def _generate_key(self, model: str, messages: list, params: dict) -> str:
        """
        Generate a unique cache key for a request.
        
        Args:
            model: The LLM model name
            messages: The message list
            params: Additional parameters
            
        Returns:
            A string hash key
        """
        # Create a dictionary with all relevant request parameters
        key_dict = {
            "model": model,
            "messages": messages,
            "params": params
        }
        
        # Convert to a consistent string and hash it
        key_str = json.dumps(key_dict, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, model: str, messages: list, params: dict) -> Optional[Dict[str, Any]]:
        """
        Get a cached response if available and not expired.
        
        Args:
            model: The LLM model name
            messages: The message list
            params: Additional parameters
            
        Returns:
            Cached response or None if not found/expired
        """
        key = self._generate_key(model, messages, params)
        
        if key in self.cache:
            # Check if cache entry is still valid
            entry = self.cache[key]
            if time.time() - entry["timestamp"] < self.ttl:
                return entry["response"]
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, model: str, messages: list, params: dict, response: Dict[str, Any]) -> None:
        """
        Store a response in the cache.
        
        Args:
            model: The LLM model name
            messages: The message list
            params: Additional parameters
            response: The API response to cache
        """
        key = self._generate_key(model, messages, params)
        
        self.cache[key] = {
            "response": response,
            "timestamp": time.time()
        }
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache = {}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache stats
        """
        current_time = time.time()
        valid_entries = sum(1 for entry in self.cache.values() 
                           if current_time - entry["timestamp"] < self.ttl)
        
        return {
            "total_entries": len(self.cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self.cache) - valid_entries,
            "memory_usage_approx": self._estimate_memory_usage()
        }
    
    def _estimate_memory_usage(self) -> str:
        """
        Roughly estimate memory usage of the cache.
        
        Returns:
            String describing approximate memory usage
        """
        # Very rough estimate based on cache size
        cache_str = json.dumps(self.cache)
        size_bytes = len(cache_str)
        
        if size_bytes < 1024:
            return f"{size_bytes} bytes"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.2f} MB"