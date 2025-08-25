from config import config
from telegram.ext import Application

def main():
    app = Application.builder().token(telegram-bot-token).build()
    # TODO: add handlers here (your game logic is already implemented in your original bot.py)
    print("Slap Fight Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
