# config.py
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
    
    # Webhook settings
    USE_WEBHOOK: bool = os.getenv("USE_WEBHOOK", "false").lower() == "true"
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_PATH: str = os.getenv("WEBHOOK_PATH", "/webhook")
    WEBHOOK_HOST: str = os.getenv("WEBHOOK_HOST", "0.0.0.0")
    WEBHOOK_PORT: int = int(os.getenv("WEBHOOK_PORT", "8443"))
    
    def validate(self):
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        if self.USE_WEBHOOK and not self.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required when using webhook mode")
            
        logging.basicConfig(
            level=getattr(logging, self.LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

config = Config()
