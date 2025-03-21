"""
All project configuration will be saved here

Needs restart if anything is changed here.
"""

import datetime
import platform
import requests

# Which model to use
# can be gemini/gemini-2.0-flash or gemini/gemini-2.0-flash-lite
# Also supports ollama if you are using `assistant.py` by setting `ollama/qwen2.5`
# or if you want to use gemini-2.0-flash from openrouter for example you can put `openrouter/google/gemini-2.0-flash-exp:free`
# Not every model supports tool calling so some might throw errors
# Here you can find all the supported provider: https://docs.litellm.ai/docs/providers/

MODEL = "gemini/gemini-2.0-flash"

# The assistants name
NAME = "Gemini"

# Model Parameters (None means default)

TEMPERATURE = 0.25
TOP_P = None
MAX_TOKENS = 8192  # Set to maximum supported by the model
SEED = None

# Script parameters

# Whether to clear the console before starting
CLEAR_TERMINAL = True
CLEAR_BEFORE_START = CLEAR_TERMINAL  # For backward compatibility

# Whether to take one message at a time
TAKE_ONLY_ONE_MESSAGE = True

# Verbose terminal, shows system prompts of messages
DEBUG_MODE = True  # Make sure this is set to True to see model reasoning

# Timeout in seconds for duckduckgo and webpages
# (the smaller the better but might not always be correct results)
DUCKDUCKGO_TIMEOUT = 5

# Maximum results for each of the following
MAX_DUCKDUCKGO_SEARCH_RESULTS = 4
MAX_REDDIT_SEARCH_RESULTS = 10
MAX_REDDIT_POST_COMMENTS = -1  # -1 means all comments

# Whether to print OS error messages.
PRINT_OS_ERROR = False

# These are for visuals there is nothing important in here
THEME_LOCALS = {
    "PRIMARY": "#584ea8",
    "SECONDARY": "#4a4464",
    "ACCENT": "#7c6f9f",
    "BACKGROUND": "#f5f5f5",
    "TEXT": "#333333",
}

# Helper function to get current system time in nice format
def get_current_time():
    """Returns the current time in a readable format."""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")

# Gemini safety settings
SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]


def get_location_info():
    try:
        response = requests.get("http://www.geoplugin.net/json.gp")
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        city = data.get("geoplugin_city", "Unknown")
        country = data.get("geoplugin_countryName", "Unknown")
        continent = data.get("geoplugin_continentName", "Unknown")
        timezone = data.get("geoplugin_timezone", "Unknown")
        currency_code = data.get("geoplugin_currencyCode", "Unknown")
        currency_symbol = data.get("geoplugin_currencySymbol", "Unknown")

        location_info = f"Location: City: {city}, Country: {country}, Continent: {continent}, Timezone: {timezone}, Currency: {currency_symbol} ({currency_code})"
        return location_info
    except requests.exceptions.RequestException as e:
        location_info = f"Location: Could not retrieve location information. Error: {e}"
        print(e)
        return location_info
    except (ValueError, KeyError) as e:
        location_info = f"Location: Error parsing location data. Error: {e}"
        print(e)
        return location_info

def get_system_prompt():
    """Returns a well-structured system prompt for the assistant."""
    return f"""
    # Role and Identity
    You are {NAME}, an advanced terminal-based personal assistant designed to help with various tasks.
    Current date: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
    Running on: {platform.system()} {platform.release()}
    {get_location_info()}
    
    # Core Principles
    1. BE HELPFUL: Provide concise, practical solutions to user requests.
    2. BE PRECISE: When dealing with code, files, or system operations, accuracy is critical.
    3. BE RESOURCEFUL: Use the best available tools for each task.
    4. BE EFFICIENT: Prefer direct solutions over lengthy explanations unless details are requested.
    
    # Capabilities and Approach
    - You have access to various tools for file operations, web interactions, system management, and more.
    - ALWAYS use tools rather than simulating or describing their function.
    - When faced with an ambiguous request:
      1. Make reasonable assumptions based on context
      2. Execute the most likely interpretation
      3. Briefly explain your approach if it's not straightforward
    - For system operations, prefer the `run_shell_command` tool over theoretical explanations.
    
    # Response Format
    - Keep responses concise and focused on solutions
    - Use markdown for formatting when beneficial
    - For code or file content, use appropriate code blocks with syntax highlighting
    - Structure multi-step solutions with clear numbering or bullets

    # Tool Usage Guidelines
    - For missing functionality, combine existing tools creatively
    - When downloading files, provide clear progress updates
    - For web searches, summarize findings rather than just providing links
    - Use note-taking capabilities to maintain context across interactions
    
    # Limitations Awareness
    - Some web interaction tools may face rate limits
    - File downloads may have issues with dynamic endpoints
    - Tool execution may fail due to permissions or system constraints
    
    Remember: You are a practical assistant focused on getting things done efficiently.
    """

# DUCKDUCKGO SEARCH

# The max amount of results duckduckgo search tool can return
MAX_DUCKDUCKGO_SEARCH_RESULTS: int = 4

# Timeout
DUCKDUCKGO_TIMEOUT: int = 20


# REDDIT

# The max amount of results reddit search tool can return, keep it low so it doesn't consume too much tokens as it feeds it raw
MAX_REDDIT_SEARCH_RESULTS: int = 5

# Maximum amount of reddit comments to load when looking into specific reddit posts, -1 for no limit
MAX_REDDIT_POST_COMMENTS: int = -1

# Multi-agent framework settings
DEBUG = True  # Enable to see agent reasoning steps
USE_MULTI_AGENT = False  # Enable multi-agent framework to test the fixed implementation
MULTI_AGENT_THRESHOLD = "low"  # Options: "low", "medium", "high" - controls how aggressively to use multi-agent mode
AGENT_TIMEOUT = 45  # Maximum seconds for an agent to process a task (increased to handle rate limiting)
RETRY_BACKOFF_BASE = 2.0  # Base for exponential backoff
MAX_RETRIES = 3  # Maximum number of retries per agent call
RETRY_INITIAL_WAIT = 4  # Initial wait time in seconds before first retry

# Multi-agent system configuration message
MULTI_AGENT_MESSAGE = """
# Multi-agent system is ENABLED
# 
# Current implementation features:
# - Improved error handling for Vertex AI function call mismatches
# - Direct LLM calls without tools for planning and synthesis
# - Exponential backoff for rate limit handling
# - Simplified communication between agents
# - More resilience against API errors
# 
# To disable, set USE_MULTI_AGENT = False in config.py
"""

# Print the multi-agent message if enabled
if USE_MULTI_AGENT:
    print("\033[93m" + MULTI_AGENT_MESSAGE + "\033[0m")
