"""
Constants for the web search module.

User-configurable values belong in:
  - agent_env/web_search.env  : API keys
  - config/services_config.yaml : per-service behavior defaults
"""
from __future__ import annotations

# ============================================================================
# Service Names
# ============================================================================
SERVICE_TAVILY = "tavily_search"
SERVICE_TAVILY_ALIAS = "tavily"
SERVICE_PERPLEXITY = "perplexity"

# ============================================================================
# Tavily API Hard Limits (fixed by the Tavily API — not user-configurable)
# ============================================================================
TAVILY_MAX_RESULTS = 20
TAVILY_MAX_INCLUDE_DOMAINS = 300
TAVILY_MAX_EXCLUDE_DOMAINS = 150
TAVILY_MIN_CHUNKS_PER_SOURCE = 1
TAVILY_MAX_CHUNKS_PER_SOURCE = 3

# ============================================================================
# Search Depth Options
# ============================================================================
SEARCH_DEPTH_BASIC = "basic"
SEARCH_DEPTH_ADVANCED = "advanced"
SEARCH_DEPTH_FAST = "fast"
SEARCH_DEPTH_ULTRA_FAST = "ultra-fast"

# ============================================================================
# Topic Options
# ============================================================================
TOPIC_GENERAL = "general"
TOPIC_NEWS = "news"
TOPIC_FINANCE = "finance"

# ============================================================================
# HTTP Defaults (fallback if not set in services_config.yaml)
# ============================================================================
DEFAULT_TIMEOUT = 30
HEALTH_CHECK_TIMEOUT = 10

# ============================================================================
# Date Format
# ============================================================================
DATE_FORMAT = "%Y-%m-%d"
DATE_FORMAT_REGEX = r"^\d{4}-\d{2}-\d{2}$"

# ============================================================================
# Content Types
# ============================================================================
CONTENT_TYPE_JSON = "application/json"

# ============================================================================
# Error Messages
# ============================================================================
ERROR_NO_SERVICES = "No services available"
ERROR_SERVICE_NOT_FOUND = "Service '{service}' not found"
ERROR_INVALID_DATE_FORMAT = (
    "{param_name} must be in YYYY-MM-DD format (e.g., '2024-01-01'). "
    "Received: '{date_str}'"
)
ERROR_INVALID_DATE_VALUE = "{param_name} is not a valid date: '{date_str}'"
ERROR_EMPTY_QUERY = "Query cannot be empty"
ERROR_API_KEY_REQUIRED = (
    "{service_name} API key is required. Set {env_var} environment variable "
    "or provide api_key in config."
)

# ============================================================================
# Environment Variable Names
# ============================================================================
ENV_TAVILY_API_KEY = "TAVILY_API_KEY"
ENV_PERPLEXITY_API_KEY = "PERPLEXITY_API_KEY"

# ============================================================================
# Validation Limits (used by Pydantic schemas in types.py)
# ============================================================================
MIN_MAX_RESULTS = 1
MAX_MAX_RESULTS = 50
DEFAULT_MAX_RESULTS = 10
