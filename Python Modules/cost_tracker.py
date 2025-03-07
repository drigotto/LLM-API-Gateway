import time
import json
from typing import Dict, Any, List
from datetime import datetime

class CostTracker:
    """
    Tracks API usage and estimates costs for different LLM providers.
    """
    
    def __init__(self, log_file: str = "api_costs.log"):
        """
        Initialize the cost tracker.
        
        Args:
            log_file: Path to file for logging cost data
        """
        self.log_file = log_file
        
        # Pricing per 1M input tokens (approximate, may need updating)
        self.input_pricing = {
            "claude-3-5-sonnet": 3.00,
            "claude-3-opus": 15.00,
            "claude-3-7-sonnet": 15.00,
            "gpt-3.5-turbo": 1.00,
            "gpt-4": 10.00,
            "gpt-4-turbo": 10.00
        }
        
        # Pricing per 1M output tokens (approximate, may need updating)
        self.output_pricing = {
            "claude-3-5-sonnet": 15.00,
            "claude-3-opus": 75.00,
            "claude-3-7-sonnet": 75.00,
            "gpt-3.5-turbo": 2.00,
            "gpt-4": 30.00,
            "gpt-4-turbo": 30.00
        }
        
        # Usage tracking
        self.usage = {
            "total_requests": 0,
            "cached_requests": 0,
            "api_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "model_usage": {},
            "estimated_cost": 0.0
        }
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        This is a very rough approximation (4 characters ≈ 1 token).
        
        Args:
            text: Text to estimate tokens for
            
        Returns:
            Estimated token count
        """
        return len(text) // 4
    
    def estimate_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate tokens for a list of messages.
        
        Args:
            messages: List of message dictionaries
            
        Returns:
            Estimated token count
        """
        total_tokens = 0
        for msg in messages:
            content = msg.get("content", "")
            total_tokens += self.estimate_tokens(content) + 4  # +4 for message overhead
        
        return total_tokens
    
    def track_request(self, model: str, messages: List[Dict[str, str]], response: Dict[str, Any], cached: bool = False) -> Dict[str, Any]:
        """
        Track a request and its costs.
        
        Args:
            model: The LLM model used
            messages: The input messages
            response: The API response
            cached: Whether the response was served from cache
            
        Returns:
            Dictionary with cost information
        """
        self.usage["total_requests"] += 1
        
        if cached:
            self.usage["cached_requests"] += 1
            return {"cached": True, "cost": 0.0}
        
        self.usage["api_requests"] += 1
        
        # Initialize model usage if not present
        if model not in self.usage["model_usage"]:
            self.usage["model_usage"][model] = {
                "requests": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
        
        # Track model-specific usage
        self.usage["model_usage"][model]["requests"] += 1
        
        # Estimate input tokens from messages
        input_tokens = self.estimate_message_tokens(messages)
        self.usage["total_input_tokens"] += input_tokens
        self.usage["model_usage"][model]["input_tokens"] += input_tokens
        
        # Estimate output tokens from response
        output_tokens = 0
        if "choices" in response and response["choices"]:
            content = response["choices"][0].get("message", {}).get("content", "")
            if not content and "content" in response["choices"][0]:
                content = response["choices"][0]["content"]
            
            output_tokens = self.estimate_tokens(content)
        
        self.usage["total_output_tokens"] += output_tokens
        self.usage["model_usage"][model]["output_tokens"] += output_tokens
        
        # Calculate cost
        input_cost = (input_tokens / 1000000) * self.input_pricing.get(model, 5.0)
        output_cost = (output_tokens / 1000000) * self.output_pricing.get(model, 15.0)
        total_cost = input_cost + output_cost
        
        self.usage["estimated_cost"] += total_cost
        self.usage["model_usage"][model]["cost"] += total_cost
        
        # Log the request
        self._log_request(model, input_tokens, output_tokens, total_cost)
        
        return {
            "cached": False,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost
        }
    
    def _log_request(self, model: str, input_tokens: int, output_tokens: int, cost: float) -> None:
        """
        Log a request to the cost log file.
        
        Args:
            model: LLM model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Estimated cost in USD
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        }
        
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            print(f"Error logging cost: {str(e)}")
    
    def get_usage_report(self) -> Dict[str, Any]:
        """
        Get a detailed usage and cost report.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "summary": {
                "total_requests": self.usage["total_requests"],
                "api_requests": self.usage["api_requests"],
                "cached_requests": self.usage["cached_requests"],
                "cache_hit_ratio": self.usage["cached_requests"] / max(1, self.usage["total_requests"]),
                "total_tokens": self.usage["total_input_tokens"] + self.usage["total_output_tokens"],
                "total_cost_usd": self.usage["estimated_cost"]
            },
            "models": self.usage["model_usage"],
            "pricing": {
                "input_pricing": self.input_pricing,
                "output_pricing": self.output_pricing
            }
        }
    
    def reset_usage(self) -> None:
        """Reset all usage statistics."""
        self.usage = {
            "total_requests": 0,
            "cached_requests": 0,
            "api_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "model_usage": {},
            "estimated_cost": 0.0
        }