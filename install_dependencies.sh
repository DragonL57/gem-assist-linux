#!/bin/bash

echo "Installing required dependencies for Gem-Assist..."

# Core data processing packages
echo "Installing pandas, numpy, and matplotlib..."
uv pip install pandas numpy matplotlib

# Web scraping tools
echo "Installing requests and beautifulsoup4..."
uv pip install requests beautifulsoup4

# Dynamic web content & browser automation
echo "Installing selenium..."
uv pip install selenium

# PDF processing
echo "Installing PyPDF2..."
uv pip install PyPDF2

# Word document processing
echo "Installing python-docx..."
uv pip install python-docx

# Google API client for advanced search
echo "Installing google-api-python-client..."
uv pip install google-api-python-client

echo "All dependencies installed successfully!"
echo "You can now run the assistant with: uv run assistant.py"
