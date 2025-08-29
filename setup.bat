@echo off
echo === SlapFight Bot Setup ===

IF NOT EXIST venv (
    python -m venv venv
)

call venv\Scripts\activate.bat

python -m pip install --upgrade pip

IF NOT EXIST requirements.txt (
    echo Error: requirements.txt not found!
    pause
    exit /b 1
)

pip install -r requirements.txt

IF NOT EXIST assets (
    mkdir assets
    mkdir assets\bodies
    mkdir assets\backgrounds
    mkdir assets\fonts
)

IF NOT EXIST assets\bodies\m_middleweight.png (
    echo Creating placeholder body image...
    python -c "from PIL import Image, ImageDraw; img = Image.new('RGB', (100, 200), (200, 200, 200)); draw = ImageDraw.Draw(img); draw.text((10, 10), 'Male Body', fill=(0,0,0)); img.save('assets/bodies/m_middleweight.png')"
)

IF NOT EXIST assets\backgrounds\arena.png (
    echo Creating placeholder arena image...
    python -c "from PIL import Image, ImageDraw; img = Image.new('RGB', (400, 300), (100, 100, 255)); draw = ImageDraw.Draw(img); draw.text((150, 140), 'ARENA', fill=(255,255,255)); img.save('assets/backgrounds/arena.png')"
)

IF NOT EXIST .env (
    echo Creating .env file from example...
    copy .env.example .env
    echo Please edit .env with your actual bot token!
    pause
)

echo Setup complete!
echo.
echo Next steps:
echo 1. Edit .env and add your bot token
echo 2. Run: python bot.py
echo.
pause
