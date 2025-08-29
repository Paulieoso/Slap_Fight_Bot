# image_generator.py
import logging
import io
from typing import Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageOps

from models import Player, Game
from config import config

logger = logging.getLogger(__name__)

class ImageGeneratorError(Exception):
    pass

class ImageGenerator:
    # Color mappings
    SKIN_TONE_COLORS = {
        "light": (255, 220, 177),
        "medium": (210, 170, 130),
        "dark": (140, 100, 70)
    }
    
    BODY_SIZES = {
        "lightweight": (0.8, 0.8),
        "middleweight": (1.0, 1.0),
        "super_heavyweight": (1.3, 1.2)
    }
    
    @staticmethod
    def generate_character_image(player: Player) -> Optional[io.BytesIO]:
        """Generate a South Park style character image"""
        try:
            # Load base body image based on gender
            gender_prefix = "m" if player.gender.value == "male" else "f"
            body_style = player.body_style.value if player.body_style else "middleweight"
            
            body_path = f"assets/bodies/{gender_prefix}_{body_style}.png"
            body_img = Image.open(body_path).convert("RGBA")
            
            # Apply skin tone
            if player.skin_tone:
                skin_color = ImageGenerator.SKIN_TONE_COLORS[player.skin_tone.value]
                body_img = ImageGenerator.recolor_image(body_img, (255, 255, 255), skin_color)
            
            # Resize based on body style
            size_factor = ImageGenerator.BODY_SIZES[body_style]
            new_size = (int(body_img.width * size_factor[0]), int(body_img.height * size_factor[1]))
            body_img = body_img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Add selfie if available
            if player.selfie_image:
                try:
                    selfie_img = Image.open(io.BytesIO(player.selfie_image)).convert("RGBA")
                    selfie_img = selfie_img.resize((80, 80), Image.Resampling.LANCZOS)
                    
                    # Position selfie on face (coordinates need adjustment based on body style)
                    face_x, face_y = 50, 30
                    if body_style == "lightweight":
                        face_x, face_y = 45, 25
                    elif body_style == "super_heavyweight":
                        face_x, face_y = 55, 35
                    
                    body_img.paste(selfie_img, (face_x, face_y), selfie_img)
                except Exception as e:
                    logger.warning(f"Failed to add selfie to character: {e}")
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            body_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            return img_byte_arr
        
        except Exception as e:
            logger.error(f"Error generating character image: {e}")
            raise ImageGeneratorError(f"Failed to generate character image: {e}")
    
    @staticmethod
    def generate_game_image(game: Game, player1: Player, player2: Player) -> Optional[io.BytesIO]:
        """Generate a game scene with both characters and HP bars"""
        try:
            # Load background
            bg_img = Image.open("assets/backgrounds/arena.png").convert("RGBA")
            
            # Generate character images
            player1_img = Image.open(ImageGenerator.generate_character_image(player1))
            player2_img = Image.open(ImageGenerator.generate_character_image(player2))
            
            # Mirror player2 image
            player2_img = ImageOps.mirror(player2_img)
            
            # Position characters
            player1_x, player1_y = 100, 200
            player2_x, player2_y = 400, 200
            
            # Adjust positions based on body size
            if player1.body_style and player1.body_style.value == "super_heavyweight":
                player1_y -= 20
            if player2.body_style and player2.body_style.value == "super_heavyweight":
                player2_y -= 20
            
            # Paste characters onto background
            bg_img.paste(player1_img, (player1_x, player1_y), player1_img)
            bg_img.paste(player2_img, (player2_x, player2_y), player2_img)
            
            # Draw HP bars
            draw = ImageDraw.Draw(bg_img)
            
            # Player1 HP bar
            hp_width = 200
            hp_height = 20
            hp_x1, hp_y1 = 50, 150
            hp_x2, hp_y2 = hp_x1 + hp_width, hp_y1 + hp_height
            
            # Background
            draw.rectangle([hp_x1, hp_y1, hp_x2, hp_y2], fill=(100, 100, 100))
            
            # Foreground (current HP)
            hp_percent = max(0, game.player1_hp) / config.MAX_HP
            current_width = int(hp_width * hp_percent)
            draw.rectangle([hp_x1, hp_y1, hp_x1 + current_width, hp_y2], fill="green")
            
            # Border
            draw.rectangle([hp_x1, hp_y1, hp_x2, hp_y2], outline=(0, 0, 0), width=2)
            
            # Player2 HP bar (right-aligned)
            hp2_x1, hp2_y1 = bg_img.width - 50 - hp_width, 150
            hp2_x2, hp2_y2 = hp2_x1 + hp_width, hp2_y1 + hp_height
            
            # Background
            draw.rectangle([hp2_x1, hp2_y1, hp2_x2, hp2_y2], fill=(100, 100, 100))
            
            # Foreground (current HP)
            hp_percent = max(0, game.player2_hp) / config.MAX_HP
            current_width = int(hp_width * hp_percent)
            draw.rectangle([hp2_x2 - current_width, hp2_y1, hp2_x2, hp2_y2], fill="green")
            
            # Border
            draw.rectangle([hp2_x1, hp2_y1, hp2_x2, hp2_y2], outline=(0, 0, 0), width=2)
            
            # Add round number
            try:
                font = ImageFont.truetype("assets/fonts/ComicNeue-Bold.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            draw.text((bg_img.width // 2 - 30, 50), f"Round {game.round_number}", 
                     fill=(0, 0, 0), font=font)
            
            # Add player names
            p1_name = player1.username[:15] + "..." if len(player1.username) > 15 else player1.username
            p2_name = player2.username[:15] + "..." if len(player2.username) > 15 else player2.username
            
            draw.text((hp_x1, hp_y1 - 25), p1_name, fill=(0, 0, 0), font=font)
            name_width = draw.textlength(p2_name, font=font)
            draw.text((hp2_x2 - name_width, hp2_y1 - 25), p2_name, fill=(0, 0, 0), font=font)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            bg_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            
            return img_byte_arr
        
        except Exception as e:
            logger.error(f"Error generating game image: {e}")
            raise ImageGeneratorError(f"Failed to generate game image: {e}")
    
    @staticmethod
    def recolor_image(image: Image.Image, target_color: Tuple[int, int, int], 
                     replacement_color: Tuple[int, int, int]) -> Image.Image:
        """Recolor specific parts of an image"""
        data = image.getdata()
        new_data = []
        
        for item in data:
            # Check if pixel matches target color (with some tolerance)
            if all(abs(item[i] - target_color[i]) < 30 for i in range(3)):
                new_data.append(replacement_color + (item[3],))  # Keep alpha
            else:
                new_data.append(item)
        
        image.putdata(new_data)
        return image
