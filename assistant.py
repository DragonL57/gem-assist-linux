"""
GEM-Assist - A terminal-based assistant that can run tools.
This file is now a wrapper around the modularized implementation.
"""
from assistant import Assistant
from assistant.session import ChatSession
from assistant.session import SessionManager
from main import main

# Backward compatibility exports
__all__ = ["Assistant", "ChatSession", "main"]

if __name__ == "__main__":
    main()