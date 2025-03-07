@app.route("/auth/keys/deactivate", methods=["POST"])
@auth_manager.authenticate
def deactivate_api_key():
    """Endpoint to deactivate an API key (admin only)"""
    # Only admin can deactivate keys
    if request.auth_info.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
        
    data = request.json
    if not data or "api_key" not in data:
        return jsonify({"error": "API key is required"}), 400
        
    api_key = data.get("api_key")
    success = auth_manager.deactivate_key(api_key)
    
    if success:
        return jsonify({"message": "API key deactivated successfully"})
    else:
        return jsonify({"error": "API key not found"}), 404import os
import json
import requests
import time
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from message_processor import MessageProcessor
from cache_manager import CacheManager
from cost_tracker import CostTracker
from rate_limiter import RateLimiter
from auth_manager import AuthManager

# Load environment variables
load_dotenv()

# Get configuration from environment variables
PORT = int(os.getenv("PORT", 5000))
HOST = os.getenv("HOST", "0.0.0.0")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", 60))
RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", 100))
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))
USE_CACHE_DEFAULT = os.getenv("USE_CACHE", "true").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
COST_LOG_FILE = os.getenv("COST_LOG_FILE", "api_costs.log")
API_KEYS_FILE = os.getenv("API_KEYS_FILE", "api_keys.json")

# Initialize Flask app
app = Flask(__name__)

# Initialize message processor
message_processor = MessageProcessor(
    system_message="You are a helpful, accurate, and friendly AI assistant."
)

# Initialize cache manager
cache_manager = CacheManager(ttl=CACHE_TTL)

# Initialize cost tracker
cost_tracker = CostTracker(log_file=COST_LOG_FILE)

# Initialize rate limiter
rate_limiter = RateLimiter(tokens_per_minute=RATE_LIMIT_PER_MINUTE, max_tokens=RATE_LIMIT_BURST)

# Initialize authentication manager
auth_manager = AuthManager(api_keys_file=API_KEYS_FILE)

# Get API keys from environment variables
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Define which models are available through each provider
AVAILABLE_MODELS = {
    "anthropic": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-7-sonnet"],
    "openai": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
}

@app.route("/")
def home():
    return "LLM Wrapper API is running!"

@app.route("/models", methods=["GET"])
@auth_manager.authenticate
def list_models():
    """Endpoint to list all available models"""
    return jsonify(AVAILABLE_MODELS)

@app.route("/cache/stats", methods=["GET"])
@auth_manager.authenticate
def cache_stats():
    """Endpoint to get cache statistics"""
    return jsonify(cache_manager.get_stats())

@app.route("/cache/clear", methods=["POST"])
@auth_manager.authenticate
def clear_cache():
    """Endpoint to clear the cache"""
    # Only admin can clear cache
    if request.auth_info.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
        
    cache_manager.clear()
    return jsonify({"message": "Cache cleared successfully"})

@app.route("/usage", methods=["GET"])
@auth_manager.authenticate
def get_usage():
    """Endpoint to get usage and cost statistics"""
    return jsonify(cost_tracker.get_usage_report())

@app.route("/usage/reset", methods=["POST"])
@auth_manager.authenticate
def reset_usage():
    """Endpoint to reset usage statistics"""
    # Only admin can reset usage
    if request.auth_info.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
        
    cost_tracker.reset_usage()
    return jsonify({"message": "Usage statistics reset successfully"})

@app.route("/auth/keys", methods=["GET"])
@auth_manager.authenticate
def list_api_keys():
    """Endpoint to list all API keys (admin only)"""
    # Only admin can list keys
    if request.auth_info.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
        
    return jsonify(auth_manager.get_all_keys_info())

@app.route("/auth/keys", methods=["POST"])
@auth_manager.authenticate
def create_api_key():
    """Endpoint to create a new API key (admin only)"""
    # Only admin can create keys
    if request.auth_info.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
        
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    name = data.get("name")
    if not name:
        return jsonify({"error": "Name is required"}), 400
        
    role = data.get("role", "user")
    rate_limit = data.get("rate_limit", 60)
    allowed_models = data.get("allowed_models", ["*"])
    
    api_key = auth_manager.create_api_key(
        name=name,
        role=role,
        rate_limit=rate_limit,
        allowed_models=allowed_models
    )
    
    return jsonify({
        "message": "API key created successfully",
        "api_key": api_key
    })

@app.route("/rate-limits", methods=["GET"])
@auth_manager.authenticate
def get_rate_limits():
    """Endpoint to check current rate limit status"""
    client_id = request.args.get("client_id", request.api_key)
    model = request.args.get("model")
    
    _, limit_info = rate_limiter.check_rate_limit(
        client_id=client_id, 
        model=model,
        tokens=0  # Just checking, not consuming
    )
    
    return jsonify(limit_info)

@app.route("/rate-limits/client", methods=["POST"])
@auth_manager.authenticate
def set_client_rate_limit():
    """Endpoint to set custom rate limit for a client"""
    # Only admin can set rate limits
    if request.auth_info.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
        
    data = request.json
    if not data or "client_id" not in data or "tokens_per_minute" not in data:
        return jsonify({"error": "Missing required parameters"}), 400
    
    rate_limiter.set_client_limit(
        data["client_id"], 
        data["tokens_per_minute"]
    )
    
    return jsonify({"message": f"Rate limit updated for client {data['client_id']}"})

@app.route("/rate-limits/model", methods=["POST"])
@auth_manager.authenticate
def set_model_rate_limit():
    """Endpoint to set custom rate limit for a model"""
    # Only admin can set rate limits
    if request.auth_info.get("role") != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
        
    data = request.json
    if not data or "model" not in data or "tokens_per_minute" not in data:
        return jsonify({"error": "Missing required parameters"}), 400
    
    rate_limiter.set_model_limit(
        data["model"], 
        data["tokens_per_minute"]
    )
    
    return jsonify({"message": f"Rate limit updated for model {data['model']}"})


@app.route("/completions", methods=["POST"])
@auth_manager.authenticate
def get_completion():
    """Main endpoint for getting completions from LLMs"""
    # Get request data
    data = request.json
    
    # Get API key for rate limiting and tracking
    client_id = request.api_key
    
    # Validate request
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    # Check rate limit
    model = data.get("model", "claude-3-5-sonnet")
    
    # Check if the model is allowed for this API key
    if not auth_manager.is_allowed_model(request.api_key, model):
        return jsonify({
            "error": f"Access to model '{model}' is not allowed with this API key"
        }), 403
    
    # Check rate limit based on API key's rate limit
    rate_limit = auth_manager.get_rate_limit(request.api_key)
    rate_limiter.set_client_limit(client_id, rate_limit)
    
    allowed, limit_info = rate_limiter.check_rate_limit(
        client_id=client_id,
        model=model
    )
    
    if not allowed:
        return jsonify({
            "error": "Rate limit exceeded",
            "limit_info": limit_info,
            "retry_after": limit_info.get("retry_after", 60)
        }), 429
        
    # Extract parameters
    model = data.get("model", "claude-3-5-sonnet")  # Default model
    messages = data.get("messages", [])
    max_tokens = data.get("max_tokens", 1000)
    temperature = data.get("temperature", 0.7)
    
    # Check if caching is enabled for this request
    use_cache = data.get("use_cache", USE_CACHE_DEFAULT)
    
    # Process messages
    try:
        processed_messages = message_processor.process_messages(messages)
        
        # Add enhancements if provided
        enhancements = data.get("enhancements", {})
        if enhancements:
            processed_messages = message_processor.enhance_system_message(
                processed_messages, enhancements
            )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
        
    # Check cache if enabled
    if use_cache:
        cache_params = {
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        cached_response = cache_manager.get(model, processed_messages, cache_params)
        if cached_response:
            # Add cache metadata
            cached_response["wrapper_metadata"] = {
                "cached": True,
                "original_timestamp": cached_response.get("wrapper_metadata", {}).get("processed_time"),
                "cache_retrieved_time": time.time()
            }
            
            # Track cached request
            cost_info = cost_tracker.track_request(model, processed_messages, cached_response, cached=True)
            cached_response["wrapper_metadata"]["cost_info"] = cost_info
            
            return jsonify(cached_response)
    
    # Determine which provider to use based on the model
    if model in AVAILABLE_MODELS["anthropic"]:
        response = call_anthropic_api(model, processed_messages, max_tokens, temperature)
    elif model in AVAILABLE_MODELS["openai"]:
        response = call_openai_api(model, processed_messages, max_tokens, temperature)
    else:
        return jsonify({"error": f"Model {model} not supported"}), 400
        
    # Add custom metadata to response
    response["wrapper_metadata"] = {
        "processed_time": time.time(),
        "wrapper_version": "1.0.0",
        "cached": False,
        "request_id": request.headers.get("X-Request-ID", "unknown")
    }
    
    # Process response content if available
    if "content" in response.get("choices", [{}])[0]:
        content = response["choices"][0]["content"]
        processed_content, citations = message_processor.extract_citations(content)
        response["choices"][0]["content"] = processed_content
        response["citations"] = citations
    
    # Track API request and costs
    cost_info = cost_tracker.track_request(model, processed_messages, response, cached=False)
    response["wrapper_metadata"]["cost_info"] = cost_info
    
    # Store in cache if caching is enabled
    if use_cache:
        cache_params = {
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        cache_manager.set(model, processed_messages, cache_params, response)
    
    # Return the response
    return jsonify(response)

def call_anthropic_api(model, messages, max_tokens, temperature):
    """Call the Anthropic API with the given parameters"""
    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }
    
    # Convert messages to Anthropic format if needed
    anthropic_messages = messages
    
    data = {
        "model": model,
        "messages": anthropic_messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=data
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

def call_openai_api(model, messages, max_tokens, temperature):
    """Call the OpenAI API with the given parameters"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    data = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"API request failed: {str(e)}"}

if __name__ == "__main__":
    # Configure logging
    import logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start the Flask app
    print(f"Starting LLM Wrapper API on {HOST}:{PORT}")
    print(f"Rate limit: {RATE_LIMIT_PER_MINUTE} requests per minute")
    print(f"Cache TTL: {CACHE_TTL} seconds")
    app.run(debug=DEBUG, host=HOST, port=PORT)