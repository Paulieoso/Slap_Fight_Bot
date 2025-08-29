#!/bin/bash
echo "=== SlapFight Bot Setup ==="

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

python -m pip install --upgrade pip

if [ ! -f "requirements.txt" ]; then
    echo "Error: requirements.txt not found!"
    exit 1
fi

pip install -r requirements.txt

if [ ! -d "assets" ]; then
    mkdir -p assets/bodies assets/backgrounds assets/fonts
fi

if [ ! -f "assets/bodies/m_middleweight.png" ]; then
    echo "Creating placeholder body image..."
    python3 -c "from PIL import Image, ImageDraw; img = Image.new('RGB', (100, 200), (200, 200, 200)); draw = ImageDraw.Draw(img); draw.text((10, 10), 'Male Body', fill=(0,0,0)); img.save('assets/bodies/m_middleweight.png')"
fi

if [ ! -f "assets/backgrounds/arena.png" ]; then
    echo "Creating placeholder arena image..."
    python3 -c "from PIL import Image, ImageDraw; img = Image.new('RGB', (400, 300), (100, 100, 255)); draw = ImageDraw.Draw(img); draw.text((150, 140), 'ARENA', fill=(255,255,255)); img.save('assets/backgrounds/arena.png')"
fi

if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "Please edit .env with your actual bot token!"
fi

echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your bot token"
echo "2. Run: python bot.py"
