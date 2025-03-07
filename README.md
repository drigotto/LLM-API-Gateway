# LLM Wrapper API

A comprehensive wrapper API for multiple Large Language Models (LLMs) with advanced features for production use.

## Features

- **Multi-Provider Support**: Seamlessly interact with models from Anthropic, OpenAI, and more
- **Intelligent Caching**: Reduce costs by caching identical requests
- **Cost Tracking**: Monitor and analyze API usage and costs
- **Rate Limiting**: Protect your API from abuse and control costs
- **Authentication**: Secure API access with granular permissions
- **Message Processing**: Enhance and validate messages before sending
- **Configurable**: Easily configure via environment variables
- **Python Client**: Simple client library for interacting with the API

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/llm-wrapper.git
cd llm-wrapper
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```
# API Keys (required)
ANTHROPIC_API_KEY=your_anthropic_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=100

# Caching
CACHE_TTL=3600
USE_CACHE=true

# Server
PORT=5000
HOST=0.0.0.0
DEBUG=true

# Logging
LOG_LEVEL=INFO
COST_LOG_FILE=api_costs.log
```

### Running the API

Start the server:
```bash
python app.py
```

The API will start on `http://localhost:5000` (or the port you specified).

### Using the Client

```python
from client import LLMWrapperClient

# Create client
client = LLMWrapperClient("http://localhost:5000", "your_api_key")

# Get a completion
messages = [
    {"role": "user", "content": "What are the benefits of using a wrapper API for LLMs?"}
]

response = client.get_completion(
    messages=messages,
    model="claude-3-5-sonnet",
    max_tokens=500,
    temperature=0.7
)

# Print the response
print(response["choices"][0]["content"])
```

## API Endpoints

### Authentication

All endpoints require an API key to be provided in the `X-API-Key` header.

### Core Endpoints

- `GET /models` - List available models
- `POST /completions` - Get a completion from an LLM

### Management Endpoints

- `GET /usage` - Get usage statistics
- `GET /cache/stats` - Get cache statistics
- `POST /cache/clear` - Clear the cache (admin only)
- `GET /rate-limits` - Check rate limit status
- `POST /rate-limits/client` - Set client rate limit (admin only)
- `POST /rate-limits/model` - Set model rate limit (admin only)

### Authentication Endpoints

- `GET /auth/keys` - List API keys (admin only)
- `POST /auth/keys` - Create a new API key (admin only)
- `POST /auth/keys/deactivate` - Deactivate an API key (admin only)

## Components

The LLM Wrapper API consists of several key components:

1. **Main Application (app.py)**: The Flask application that handles HTTP requests
2. **Message Processor (message_processor.py)**: Processes and enhances messages
3. **Cache Manager (cache_manager.py)**: Manages response caching
4. **Cost Tracker (cost_tracker.py)**: Tracks API usage and costs
5. **Rate Limiter (rate_limiter.py)**: Controls request rates
6. **Auth Manager (auth_manager.py)**: Manages API keys and authentication
7. **Client (client.py)**: Python client for interacting with the API

## Customization

You can customize the API by:

1. Adding support for more LLM providers
2. Enhancing the message processing pipeline
3. Implementing more advanced caching strategies
4. Creating custom cost optimization rules
5. Developing additional client libraries

## Production Considerations

For production deployment:

1. Use a production-grade WSGI server like Gunicorn
2. Set up proper logging and monitoring
3. Use a more robust caching solution (Redis, etc.)
4. Implement database storage for API keys and usage data
5. Set up proper security measures (HTTPS, etc.)
6. Consider containerization with Docker

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- OpenAI and Anthropic for their powerful LLM APIs
- The Flask team for the web framework