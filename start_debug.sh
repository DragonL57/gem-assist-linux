#!/bin/bash

# Set debug mode in config.py
sed -i 's/DEBUG_MODE = False/DEBUG_MODE = True/g' config.py

echo "Starting Gem-assist in debug mode..."
uv run assistant.py

# Restore normal mode when done (optional)
# sed -i 's/DEBUG_MODE = True/DEBUG_MODE = False/g' config.py
