#!/bin/bash
# Dungeon Crawler Launcher

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
    echo "Installing dependencies..."
    venv/bin/pip install -r requirements.txt
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "WARNING: .env file not found!"
    echo "Copy .env.example to .env and add your Google Gemini API_KEY"
    echo "The game will run with fallback texts if no API key is provided."
    echo ""
fi

# Run the game
venv/bin/python main.py
