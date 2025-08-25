#!/bin/bash
set -e

echo "=== SlapFight Bot Setup ==="

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip

if [ ! -f "requirements.txt" ]; then
    echo "Missing requirements.txt"
    exit 1
fi

pip install -r requirements.txt

if [ ! -d "assets" ]; then
    mkdir -p assets/bodies assets/backgrounds assets/fonts
    touch assets/bodies/m_middleweight.png
    touch assets/backgrounds/arena.png
    touch assets/fonts/ComicNeue-Bold.ttf
fi

if [ ! -f ".env" ]; then
    echo "BOT_TOKEN=8217931968:AAEO7YsKB975bwCtsfnE4c0OtXz9VjkAO0Q" > .env
    echo ".env created. Please edit it with your real bot token."
    exit 1
fi

export $(grep -v '^#' .env | xargs)

echo "Starting SlapFight bot..."
python bot.py
