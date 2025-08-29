import os
import logging
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "slap_game.db")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_CLUBS: int = 2
    MAX_FLINCHES: int = 2
    MAX_HP: int = 20
    CLUB_DAMAGE: int = 4
    FLINCH_DAMAGE: int = 1
    TOTAL_ROUNDS: int = 5
    AI_WAIT_TIME: int = 2
    GAME_TIMEOUT: int = 300
    
    def validate(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
            
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

config = Config()
