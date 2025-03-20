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
MAX_TOKENS = None
SEED = None

# Script parameters

# Whether to clear the console before starting
CLEAR_BEFORE_START = True


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
