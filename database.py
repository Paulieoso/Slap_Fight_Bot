# database.py
import sqlite3
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from models import Player, Game, GameState
from config import config

logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    pass

class Database:
    def __init__(self, db_url: str = config.DATABASE_URL):
        self.db_url = db_url
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with error handling"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_url)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            if conn:
                conn.close()
    
    def init_db(self):
        """Initialize database tables"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                
                # Players table
                c.execute('''CREATE TABLE IF NOT EXISTS players
                            (user_id INTEGER PRIMARY KEY, 
                             username TEXT NOT NULL,
                             gender TEXT,
                             skin_tone TEXT,
                             body_style TEXT,
                             selfie_image BLOB,
                             wins INTEGER DEFAULT 0,
                             losses INTEGER DEFAULT 0,
                             created_at REAL NOT NULL)''')
                
                # Games table
                c.execute('''CREATE TABLE IF NOT EXISTS games
                            (game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                             player1_id INTEGER NOT NULL,
                             player2_id INTEGER,
                             player1_hp INTEGER DEFAULT 20,
                             player2_hp INTEGER DEFAULT 20,
                             player1_clubs INTEGER DEFAULT 0,
                             player2_clubs INTEGER DEFAULT 0,
                             player1_flinches INTEGER DEFAULT 0,
                             player2_flinches INTEGER DEFAULT 0,
                             current_turn INTEGER,
                             round_number INTEGER DEFAULT 1,
                             state TEXT NOT NULL,
                             player1_slap INTEGER,
                             player2_slap INTEGER,
                             created_at REAL NOT NULL,
                             updated_at REAL NOT NULL,
                             FOREIGN KEY (player1_id) REFERENCES players (user_id),
                             FOREIGN KEY (player2_id) REFERENCES players (user_id))''')
                
                # Game actions table
                c.execute('''CREATE TABLE IF NOT EXISTS game_actions
                            (action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                             game_id INTEGER NOT NULL,
                             round_number INTEGER NOT NULL,
                             player_id INTEGER NOT NULL,
                             action_type TEXT NOT NULL,
                             slap_count INTEGER,
                             guess_count INTEGER,
                             damage INTEGER,
                             timestamp REAL NOT NULL,
                             FOREIGN KEY (game_id) REFERENCES games (game_id),
                             FOREIGN KEY (player_id) REFERENCES players (user_id))''')
                
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")
    
    def get_player(self, user_id: int) -> Optional[Player]:
        """Get player by user ID"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
                row = c.fetchone()
                return Player.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting player {user_id}: {e}")
            return None
    
    def create_player(self, player: Player) -> bool:
        """Create a new player"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO players 
                            (user_id, username, gender, skin_tone, body_style, selfie_image, wins, losses, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (player.user_id, player.username, player.gender.value if player.gender else None,
                          player.skin_tone.value if player.skin_tone else None,
                          player.body_style.value if player.body_style else None,
                          player.selfie_image, player.wins, player.losses, player.created_at))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error creating player {player.user_id}: {e}")
            return False
    
    def update_player(self, player: Player) -> bool:
        """Update player data"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('''UPDATE players 
                            SET username=?, gender=?, skin_tone=?, body_style=?, selfie_image=?, wins=?, losses=?
                            WHERE user_id=?''',
                         (player.username, player.gender.value if player.gender else None,
                          player.skin_tone.value if player.skin_tone else None,
                          player.body_style.value if player.body_style else None,
                          player.selfie_image, player.wins, player.losses, player.user_id))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating player {player.user_id}: {e}")
            return False
    
    def create_game(self, player1_id: int, player2_id: Optional[int] = None) -> Optional[int]:
        """Create a new game and return game ID"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                timestamp = time.time()
                c.execute('''INSERT INTO games 
                            (player1_id, player2_id, player1_hp, player2_hp, current_turn, 
                             round_number, state, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (player1_id, player2_id, config.MAX_HP, config.MAX_HP, player1_id,
                          1, GameState.PLAYER1_CHOOSE_SLAP.value, timestamp, timestamp))
                game_id = c.lastrowid
                conn.commit()
                return game_id
        except sqlite3.Error as e:
            logger.error(f"Error creating game: {e}")
            return None
    
    def get_game(self, game_id: int) -> Optional[Game]:
        """Get game by ID"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM games WHERE game_id = ?", (game_id,))
                row = c.fetchone()
                return Game.from_dict(dict(row)) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting game {game_id}: {e}")
            return None
    
    def update_game(self, game: Game) -> bool:
        """Update game data"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('''UPDATE games 
                            SET player1_id=?, player2_id=?, player1_hp=?, player2_hp=?,
                                player1_clubs=?, player2_clubs=?, player1_flinches=?, player2_flinches=?,
                                current_turn=?, round_number=?, state=?, player1_slap=?, player2_slap=?,
                                updated_at=?
                            WHERE game_id=?''',
                         (game.player1_id, game.player2_id, game.player1_hp, game.player2_hp,
                          game.player1_clubs, game.player2_clubs, game.player1_flinches, game.player2_flinches,
                          game.current_turn, game.round_number, game.state.value, 
                          game.player1_slap, game.player2_slap, time.time(), game.game_id))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error updating game {game.game_id}: {e}")
            return False
    
    def get_player_games(self, user_id: int, active_only: bool = True) -> List[Game]:
        """Get all games for a player"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                if active_only:
                    c.execute('''SELECT * FROM games 
                                WHERE (player1_id = ? OR player2_id = ?) 
                                AND state NOT IN (?, ?)
                                ORDER BY updated_at DESC''',
                             (user_id, user_id, GameState.GAME_END.value, GameState.TIMED_OUT.value))
                else:
                    c.execute('''SELECT * FROM games 
                                WHERE player1_id = ? OR player2_id = ? 
                                ORDER BY updated_at DESC''',
                             (user_id, user_id))
                
                rows = c.fetchall()
                return [Game.from_dict(dict(row)) for row in rows]
        except sqlite3.Error as e:
            logger.error(f"Error getting games for player {user_id}: {e}")
            return []
    
    def get_global_rankings(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get global rankings by wins"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('''SELECT user_id, username, wins, losses, 
                            (wins * 1.0 / CASE WHEN (wins + losses) = 0 THEN 1 ELSE (wins + losses) END) as win_rate
                            FROM players 
                            ORDER BY wins DESC, win_rate DESC
                            LIMIT ?''', (limit,))
                
                return [dict(row) for row in c.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting rankings: {e}")
            return []
    
    def add_game_action(self, game_id: int, round_number: int, player_id: int, 
                       action_type: str, slap_count: Optional[int] = None, 
                       guess_count: Optional[int] = None, damage: Optional[int] = None) -> bool:
        """Record a game action for analytics"""
        try:
            with self.get_connection() as conn:
                c = conn.cursor()
                c.execute('''INSERT INTO game_actions 
                            (game_id, round_number, player_id, action_type, slap_count, guess_count, damage, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (game_id, round_number, player_id, action_type, slap_count, guess_count, damage, time.time()))
                conn.commit()
                return True
        except sqlite3.Error as e:
            logger.error(f"Error adding game action: {e}")
            return False

# Global database instance
db = Database()
