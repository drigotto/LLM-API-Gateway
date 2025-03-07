import requests
import json
from typing import List, Dict, Any, Optional

class LLMWrapperClient:
    """
    Client for interacting with the LLM Wrapper API.
    """
    
    def __init__(self, base_url: str, api_key: str):
        """
        Initialize the client.
        
        Args:
            base_url: Base URL of the LLM Wrapper API
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-API-Key": api_key
        })
    
    def list_models(self) -> Dict[str, List[str]]:
        """
        Get a list of available models.
        
        Returns:
            Dictionary of model providers and their models
        """
        response = self.session.get(f"{self.base_url}/models")
        response.raise_for_status()
        return response.json()
    
    def get_completion(self, 
                       messages: List[Dict[str, str]], 
                       model: str = "claude-3-5-sonnet", 
                       max_tokens: int = 1000,
                       temperature: float = 0.7,
                       use_cache: bool = True,
                       enhancements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a completion from the LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: LLM model to use
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            use_cache: Whether to use caching
            enhancements: Optional enhancements for the system message
            
        Returns:
            Response from the LLM
        """
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "use_cache": use_cache
        }
        
        if enhancements:
            data["enhancements"] = enhancements
        
        response = self.session.post(
            f"{self.base_url}/completions",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def get_usage(self) -> Dict[str, Any]:
        """
        Get usage and cost statistics.
        
        Returns:
            Usage statistics
        """
        response = self.session.get(f"{self.base_url}/usage")
        response.raise_for_status()
        return response.json()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        response = self.session.get(f"{self.base_url}/cache/stats")
        response.raise_for_status()
        return response.json()
    
    def clear_cache(self) -> Dict[str, str]:
        """
        Clear the cache.
        
        Returns:
            Response message
        """
        response = self.session.post(f"{self.base_url}/cache/clear")
        response.raise_for_status()
        return response.json()
    
    def get_rate_limits(self) -> Dict[str, Any]:
        """
        Get current rate limit status.
        
        Returns:
            Rate limit information
        """
        response = self.session.get(f"{self.base_url}/rate-limits")
        response.raise_for_status()
        return response.json()
    
    def create_api_key(self, 
                      name: str, 
                      role: str = "user",
                      rate_limit: int = 60,
                      allowed_models: List[str] = None) -> Dict[str, str]:
        """
        Create a new API key (admin only).
        
        Args:
            name: Name or description of the key owner
            role: Role (admin, user, etc.)
            rate_limit: Rate limit in requests per minute
            allowed_models: List of allowed models or ["*"] for all
            
        Returns:
            Response with new API key
        """
        data = {
            "name": name,
            "role": role,
            "rate_limit": rate_limit,
            "allowed_models": allowed_models or ["*"]
        }
        
        response = self.session.post(
            f"{self.base_url}/auth/keys",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """
        List all API keys (admin only).
        
        Returns:
            List of API key information
        """
        response = self.session.get(f"{self.base_url}/auth/keys")
        response.raise_for_status()
        return response.json()
    
    def deactivate_api_key(self, api_key: str) -> Dict[str, str]:
        """
        Deactivate an API key (admin only).
        
        Args:
            api_key: The API key to deactivate
            
        Returns:
            Response message
        """
        data = {"api_key": api_key}
        response = self.session.post(
            f"{self.base_url}/auth/keys/deactivate",
            json=data
        )
        response.raise_for_status()
        return response.json()


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Get API key from environment
    API_KEY = os.getenv("LLM_WRAPPER_API_KEY")
    BASE_URL = os.getenv("LLM_WRAPPER_URL", "http://localhost:5000")
    
    if not API_KEY:
        print("Please set the LLM_WRAPPER_API_KEY environment variable")
        exit(1)
    
    # Create client
    client = LLMWrapperClient(BASE_URL, API_KEY)
    
    # Example: Get available models
    try:
        models = client.list_models()
        print("Available models:")
        for provider, model_list in models.items():
            print(f"  {provider}: {', '.join(model_list)}")
    except Exception as e:
        print(f"Error listing models: {str(e)}")
    
    # Example: Get a completion
    try:
        messages = [
            {"role": "user", "content": "What are the benefits of using a wrapper API for LLMs?"}
        ]
        
        response = client.get_completion(
            messages=messages,
            model="claude-3-5-sonnet",
            max_tokens=500,
            temperature=0.7
        )
        
        if "choices" in response and response["choices"]:
            content = response["choices"][0].get("content", "")
            if not content and "message" in response["choices"][0]:
                content = response["choices"][0]["message"].get("content", "")
            
            print("\nResponse:")
            print(content)
            
            # Print cost information
            cost_info = response.get("wrapper_metadata", {}).get("cost_info", {})
            cached = cost_info.get("cached", False)
            
            print("\nRequest information:")
            print(f"Cached: {cached}")
            
            if not cached:
                print(f"Input tokens: {cost_info.get('input_tokens', 0)}")
                print(f"Output tokens: {cost_info.get('output_tokens', 0)}")
                print(f"Cost: ${cost_info.get('total_cost', 0):.6f}")
        else:
            print("No response content")
    except Exception as e:
        print(f"Error getting completion: {str(e)}")
    
    # Example: Get usage statistics
    try:
        usage = client.get_usage()
        print("\nUsage statistics:")
        print(f"Total requests: {usage['summary']['total_requests']}")
        print(f"Cache hit ratio: {usage['summary']['cache_hit_ratio']:.2f}")
        print(f"Total cost: ${usage['summary']['total_cost_usd']:.4f}")
    except Exception as e:
        print(f"Error getting usage: {str(e)}")