import os
from dataclasses import dataclass

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "slap_game.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

config = Config()
