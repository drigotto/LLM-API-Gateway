import os
import time
import uuid
import hmac
import hashlib
import json
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from flask import request, jsonify

class AuthManager:
    """
    Manages API key authentication and authorization.
    """
    
    def __init__(self, api_keys_file: str = "api_keys.json"):
        """
        Initialize the authentication manager.
        
        Args:
            api_keys_file: Path to JSON file storing API keys
        """
        self.api_keys_file = api_keys_file
        self.api_keys = self._load_api_keys()
        
        # Create default admin key if no keys exist
        if not self.api_keys:
            self._create_default_admin_key()
    
    def _load_api_keys(self) -> Dict[str, Dict[str, Any]]:
        """
        Load API keys from the keys file.
        
        Returns:
            Dictionary of API keys
        """
        if os.path.exists(self.api_keys_file):
            try:
                with open(self.api_keys_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading API keys: {str(e)}")
                return {}
        return {}
    
    def _save_api_keys(self) -> None:
        """Save API keys to the keys file."""
        try:
            with open(self.api_keys_file, 'w') as f:
                json.dump(self.api_keys, f, indent=2)
        except Exception as e:
            print(f"Error saving API keys: {str(e)}")
    
    def _create_default_admin_key(self) -> str:
        """
        Create a default admin API key.
        
        Returns:
            The generated API key
        """
        api_key = self.generate_api_key()
        self.api_keys[api_key] = {
            "name": "Default Admin",
            "role": "admin",
            "created_at": time.time(),
            "rate_limit": 100,  # Higher rate limit for admin
            "allowed_models": ["*"],  # All models allowed
            "active": True
        }
        self._save_api_keys()
        print(f"Generated default admin API key: {api_key}")
        return api_key
    
    def generate_api_key(self) -> str:
        """
        Generate a new API key.
        
        Returns:
            A new unique API key
        """
        # Generate a random UUID and hash it
        random_id = str(uuid.uuid4())
        timestamp = str(int(time.time()))
        
        # Create a unique key with timestamp and random component
        key_material = f"{random_id}:{timestamp}"
        hashed = hashlib.sha256(key_material.encode()).hexdigest()
        
        # Format as a readable API key with prefix
        return f"llm_wrapper_{hashed[:32]}"
    
    def create_api_key(self, name: str, role: str = "user", 
                      rate_limit: int = 60, 
                      allowed_models: List[str] = None) -> str:
        """
        Create a new API key for a user or service.
        
        Args:
            name: Name or description of the key owner
            role: Role (admin, user, etc.)
            rate_limit: Rate limit in requests per minute
            allowed_models: List of allowed models or ["*"] for all
            
        Returns:
            The generated API key
        """
        api_key = self.generate_api_key()
        self.api_keys[api_key] = {
            "name": name,
            "role": role,
            "created_at": time.time(),
            "rate_limit": rate_limit,
            "allowed_models": allowed_models or ["*"],
            "active": True
        }
        self._save_api_keys()
        return api_key
    
    def validate_key(self, api_key: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate an API key and return key information.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple of (is_valid, key_info)
        """
        key_info = self.api_keys.get(api_key, {})
        if not key_info or not key_info.get("active", False):
            return False, {"error": "Invalid or inactive API key"}
        
        return True, key_info
    
    def is_allowed_model(self, api_key: str, model: str) -> bool:
        """
        Check if a model is allowed for a given API key.
        
        Args:
            api_key: The API key to check
            model: The model to check access for
            
        Returns:
            True if the model is allowed, False otherwise
        """
        valid, key_info = self.validate_key(api_key)
        if not valid:
            return False
        
        allowed_models = key_info.get("allowed_models", [])
        return "*" in allowed_models or model in allowed_models
    
    def get_rate_limit(self, api_key: str) -> int:
        """
        Get the rate limit for a given API key.
        
        Args:
            api_key: The API key to check
            
        Returns:
            Rate limit in requests per minute
        """
        valid, key_info = self.validate_key(api_key)
        if not valid:
            return 0
        
        return key_info.get("rate_limit", 60)
    
    def deactivate_key(self, api_key: str) -> bool:
        """
        Deactivate an API key.
        
        Args:
            api_key: The API key to deactivate
            
        Returns:
            True if successful, False otherwise
        """
        if api_key in self.api_keys:
            self.api_keys[api_key]["active"] = False
            self._save_api_keys()
            return True
        return False
    
    def authenticate(self, f: Callable) -> Callable:
        """
        Flask decorator for API key authentication.
        
        Args:
            f: The function to decorate
            
        Returns:
            Decorated function
        """
        @wraps(f)
        def decorated(*args, **kwargs):
            # Get API key from header or query parameter
            api_key = request.headers.get("X-API-Key")
            if not api_key:
                api_key = request.args.get("api_key")
            
            if not api_key:
                return jsonify({"error": "API key is missing"}), 401
            
            # Validate the API key
            valid, key_info = self.validate_key(api_key)
            if not valid:
                return jsonify({"error": "Invalid or inactive API key"}), 401
            
            # Check if model is allowed (if specified in request)
            if request.method == "POST" and request.is_json:
                data = request.json
                if data and "model" in data:
                    model = data.get("model")
                    if not self.is_allowed_model(api_key, model):
                        return jsonify({
                            "error": f"Access to model '{model}' is not allowed with this API key"
                        }), 403
            
            # Add key info to request context for use in the endpoint
            request.auth_info = key_info
            request.api_key = api_key
            
            return f(*args, **kwargs)
        
        return decorated
    
    def get_all_keys_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all API keys (admin only).
        
        Returns:
            List of API key information dictionaries
        """
        # Create a safe version that doesn't include the actual keys
        keys_info = []
        for key, info in self.api_keys.items():
            masked_key = f"{key[:8]}...{key[-4:]}"
            keys_info.append({
                "key": masked_key,
                "name": info.get("name"),
                "role": info.get("role"),
                "created_at": info.get("created_at"),
                "rate_limit": info.get("rate_limit"),
                "allowed_models": info.get("allowed_models"),
                "active": info.get("active")
            })
        
        return keys_info