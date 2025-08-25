@echo off
echo === SlapFight Bot Setup ===

IF NOT EXIST venv (
    python -m venv venv
)

call venv\Scripts\activate

python -m pip install --upgrade pip

IF NOT EXIST requirements.txt (
    echo Missing requirements.txt
    exit /b
)

pip install -r requirements.txt

IF NOT EXIST assets (
    mkdir assets\bodies
    mkdir assets\backgrounds
    mkdir assets\fonts
    type nul > assets\bodies\m_middleweight.png
    type nul > assets\backgrounds\arena.png
    type nul > assets\fonts\ComicNeue-Bold.ttf
)

IF NOT EXIST .env (
    echo BOT_TOKEN=PUT_YOUR_TELEGRAM_BOT_TOKEN_HERE > .env
    echo .env created. Please edit it with your real bot token.
    exit /b
)

for /f "tokens=*" %%a in (.env) do set %%a

echo Starting SlapFight bot...
python bot.py
