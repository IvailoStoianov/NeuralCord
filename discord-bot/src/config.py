"""
Configuration settings for the Discord bot and Filter AI.
This file centralizes all configurable parameters to make adjustments easier.
"""

# Version information
VERSION = "0.9.0"
VERSION_NAME = "Beta"
RELEASE_DATE = "2024-04-01"

# FilterAI settings
FILTER_AI_CONFIG = {
    # Maximum number of characters in conversation context sent to Character.AI
    "MAX_CONTEXT_LENGTH": 1000,
    
    # Maximum number of messages to include in context
    "MAX_CONTEXT_MESSAGES": 15,
    
    # Maximum length of a single message before truncation
    "MAX_MESSAGE_LENGTH": 200,
    
    # Default Ollama model to use
    "DEFAULT_MODEL": "mistral",
    
    # Response tags for the filter AI
    "RESPOND_TAG": "[RESPOND]",
    "IGNORE_TAG": "[IGNORE]",
    "SUMMARY_TAG": "[SUMMARY]"
}

# Discord bot settings
BOT_CONFIG = {
    # Default cooldown between responses in seconds
    "DEFAULT_COOLDOWN": 1,
    
    # Minimum allowed cooldown in seconds
    "MIN_COOLDOWN": 1,
    
    # Default data file location
    "DATA_FILE": "bot_data.json",
    
    # Rate limiting settings
    "RATE_LIMIT": {
        "ENABLED": True,
        "MAX_CALLS_PER_MINUTE": 30,  # Maximum API calls per minute
        "MAX_CALLS_PER_USER": 10     # Maximum API calls per user per minute
    }
}

# Logging settings
LOGGING_CONFIG = {
    # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    "LEVEL": "INFO",
    
    # Log file names
    "BOT_LOG_FILE": "bot.log",
    "FILTER_LOG_FILE": "filter_ai.log",
    
    # Log format
    "FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
} 