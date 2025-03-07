import time
import threading
from typing import Dict, Any, List, Tuple
from collections import defaultdict

class RateLimiter:
    """
    Implements token bucket rate limiting for API calls.
    """
    
    def __init__(self, tokens_per_minute: int = 60, max_tokens: int = 60):
        """
        Initialize the rate limiter.
        
        Args:
            tokens_per_minute: Tokens replenished per minute
            max_tokens: Maximum number of tokens in the bucket
        """
        self.tokens_per_minute = tokens_per_minute
        self.tokens_per_second = tokens_per_minute / 60.0
        self.max_tokens = max_tokens
        
        # Default bucket for general rate limiting
        self.bucket = {
            "tokens": max_tokens,
            "last_refill": time.time()
        }
        
        # Per-client rate limiting
        self.client_buckets = defaultdict(
            lambda: {"tokens": max_tokens, "last_refill": time.time()}
        )
        
        # Per-model rate limiting (different models may have different quotas)
        self.model_buckets = defaultdict(
            lambda: {"tokens": max_tokens, "last_refill": time.time()}
        )
        
        # Start a background thread to refill tokens
        self.running = True
        self.refill_thread = threading.Thread(target=self._refill_tokens_periodically)
        self.refill_thread.daemon = True
        self.refill_thread.start()
    
    def _refill_tokens(self, bucket: Dict[str, float]) -> None:
        """
        Refill tokens based on time elapsed.
        
        Args:
            bucket: Token bucket to refill
        """
        now = time.time()
        time_passed = now - bucket["last_refill"]
        tokens_to_add = time_passed * self.tokens_per_second
        
        # Update bucket
        bucket["tokens"] = min(bucket["tokens"] + tokens_to_add, self.max_tokens)
        bucket["last_refill"] = now
    
    def _refill_tokens_periodically(self) -> None:
        """
        Background thread that refills all token buckets periodically.
        """
        while self.running:
            # Refill global bucket
            self._refill_tokens(self.bucket)
            
            # Refill client buckets
            for bucket in self.client_buckets.values():
                self._refill_tokens(bucket)
            
            # Refill model buckets
            for bucket in self.model_buckets.values():
                self._refill_tokens(bucket)
            
            # Sleep for a short time
            time.sleep(1)
    
    def check_rate_limit(self, 
                         client_id: str = "default", 
                         model: str = None, 
                         tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if a request is within rate limits.
        
        Args:
            client_id: Client identifier for client-specific rate limiting
            model: Model name for model-specific rate limiting
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            Tuple of (allowed, limit_info)
        """
        # Refill tokens first
        self._refill_tokens(self.bucket)
        self._refill_tokens(self.client_buckets[client_id])
        if model:
            self._refill_tokens(self.model_buckets[model])
        
        # Check global bucket
        if self.bucket["tokens"] < tokens:
            return False, {
                "allowed": False,
                "level": "global",
                "tokens_available": self.bucket["tokens"],
                "tokens_requested": tokens,
                "retry_after": (tokens - self.bucket["tokens"]) / self.tokens_per_second
            }
        
        # Check client-specific bucket
        if self.client_buckets[client_id]["tokens"] < tokens:
            return False, {
                "allowed": False,
                "level": "client",
                "client_id": client_id,
                "tokens_available": self.client_buckets[client_id]["tokens"],
                "tokens_requested": tokens,
                "retry_after": (tokens - self.client_buckets[client_id]["tokens"]) / self.tokens_per_second
            }
        
        # Check model-specific bucket if provided
        if model and self.model_buckets[model]["tokens"] < tokens:
            return False, {
                "allowed": False,
                "level": "model",
                "model": model,
                "tokens_available": self.model_buckets[model]["tokens"],
                "tokens_requested": tokens,
                "retry_after": (tokens - self.model_buckets[model]["tokens"]) / self.tokens_per_second
            }
        
        # All checks passed, consume tokens
        self.bucket["tokens"] -= tokens
        self.client_buckets[client_id]["tokens"] -= tokens
        if model:
            self.model_buckets[model]["tokens"] -= tokens
        
        return True, {
            "allowed": True,
            "tokens_consumed": tokens,
            "tokens_remaining": {
                "global": self.bucket["tokens"],
                "client": self.client_buckets[client_id]["tokens"],
                "model": self.model_buckets[model]["tokens"] if model else None
            }
        }
    
    def set_client_limit(self, client_id: str, tokens_per_minute: int) -> None:
        """
        Set a custom rate limit for a specific client.
        
        Args:
            client_id: Client identifier
            tokens_per_minute: Custom tokens per minute for this client
        """
        # Create custom bucket with specified rate
        self.client_buckets[client_id] = {
            "tokens": tokens_per_minute,
            "last_refill": time.time(),
            "tokens_per_second": tokens_per_minute / 60.0
        }
    
    def set_model_limit(self, model: str, tokens_per_minute: int) -> None:
        """
        Set a custom rate limit for a specific model.
        
        Args:
            model: Model name
            tokens_per_minute: Custom tokens per minute for this model
        """
        # Create custom bucket with specified rate
        self.model_buckets[model] = {
            "tokens": tokens_per_minute,
            "last_refill": time.time(),
            "tokens_per_second": tokens_per_minute / 60.0
        }
    
    def stop(self) -> None:
        """Stop the background thread."""
        self.running = False
        if self.refill_thread.is_alive():
            self.refill_thread.join(timeout=1)