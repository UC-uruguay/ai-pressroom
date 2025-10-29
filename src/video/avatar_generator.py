"""
Generate avatar images for each AI speaker.

Creates simple, clean avatar images with speaker name and themed colors.
"""
from pathlib import Path
from typing import Dict, Any, Optional

from PIL import Image, ImageDraw, ImageFont

from ..shared.logger import get_logger

logger = get_logger(__name__)


class AvatarGenerator:
    """Generate avatar images for debate speakers."""

    # Color schemes for each AI
    COLORS = {
        "chatgpt": {
            "background": "#10A37F",  # OpenAI teal
            "accent": "#1A7F64",
            "text": "#FFFFFF",
        },
        "gemini": {
            "background": "#4285F4",  # Google blue
            "accent": "#1967D2",
            "text": "#FFFFFF",
        },
        "claude": {
            "background": "#D97757",  # Anthropic orange
            "accent": "#CC5500",
            "text": "#FFFFFF",
        },
    }

    DEFAULT_SIZE = (1920, 1080)

    def __init__(self, output_dir: Path):
        """
        Initialize avatar generator.

        Args:
            output_dir: Directory to save generated images
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_avatar(
        self,
        speaker: str,
        character: Dict[str, Any],
        size: tuple[int, int] = DEFAULT_SIZE
    ) -> Path:
        """
        Generate personified avatar image for a speaker.

        Args:
            speaker: Speaker name (chatgpt, gemini, claude)
            character: Character configuration
            size: Image size (width, height)

        Returns:
            Path to generated image
        """
        output_path = self.output_dir / f"avatar_{speaker}.png"

        # Always regenerate to ensure latest design
        logger.info(f"Generating personified avatar for {speaker}...")

        # Get colors
        colors = self.COLORS.get(speaker, self.COLORS["chatgpt"])

        # Create image with gradient background
        img = Image.new("RGB", size, colors["background"])
        draw = ImageDraw.Draw(img)

        # Draw gradient background
        for y in range(size[1]):
            alpha = y / size[1]
            # Blend from background to accent
            draw.line(
                [(0, y), (size[0], y)],
                fill=self._blend_color(
                    colors["background"],
                    colors["accent"],
                    alpha * 0.3
                )
            )

        # Draw personified character based on speaker
        if speaker == "chatgpt":
            self._draw_chatgpt_character(draw, size, colors)
        elif speaker == "gemini":
            self._draw_gemini_character(draw, size, colors)
        elif speaker == "claude":
            self._draw_claude_character(draw, size, colors)

        # Get text to display
        ai_name = character.get("ai_name", speaker.upper())
        persona_name = character.get("persona_name", ai_name)
        company = character.get("company", "")

        # Try to load font (use default if not available)
        try:
            # Try common system fonts
            font_large = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                120
            )
            font_medium = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                60
            )
            font_small = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                40
            )
        except OSError:
            logger.warning("System font not found, using default")
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()

        # Draw AI name in center
        ai_text = ai_name
        bbox = draw.textbbox((0, 0), ai_text, font=font_large)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2 - 100

        # Draw shadow
        draw.text(
            (x + 4, y + 4),
            ai_text,
            font=font_large,
            fill="#00000040"
        )
        # Draw main text
        draw.text(
            (x, y),
            ai_text,
            font=font_large,
            fill=colors["text"]
        )

        # Draw persona name
        persona_text = f"aka {persona_name}"
        bbox = draw.textbbox((0, 0), persona_text, font=font_medium)
        text_width = bbox[2] - bbox[0]
        x = (size[0] - text_width) // 2
        y = (size[1] - text_height) // 2 + 50

        draw.text(
            (x, y),
            persona_text,
            font=font_medium,
            fill=colors["text"]
        )

        # Draw company name at bottom
        if company:
            try:
                font_small = ImageFont.truetype(
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                    40
                )
            except OSError:
                font_small = ImageFont.load_default()

            bbox = draw.textbbox((0, 0), company, font=font_small)
            text_width = bbox[2] - bbox[0]
            x = (size[0] - text_width) // 2
            y = size[1] - 100

            draw.text(
                (x, y),
                company,
                font=font_small,
                fill=colors["text"]
            )

        # Save image
        img.save(output_path, "PNG", quality=95)
        logger.info(f"Saved avatar to {output_path}")

        return output_path

    def generate_all_avatars(
        self,
        characters: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Path]:
        """
        Generate avatars for all speakers.

        Args:
            characters: Dictionary of character configurations

        Returns:
            Dictionary mapping speaker name to avatar path
        """
        avatars = {}

        for speaker, character in characters.items():
            avatar_path = self.generate_avatar(speaker, character)
            avatars[speaker] = avatar_path

        logger.info(f"Generated {len(avatars)} avatar images")
        return avatars

    def _blend_color(
        self,
        color1: str,
        color2: str,
        alpha: float
    ) -> str:
        """
        Blend two hex colors.

        Args:
            color1: First color (hex)
            color2: Second color (hex)
            alpha: Blend factor (0-1)

        Returns:
            Blended color (hex)
        """
        # Convert hex to RGB
        c1 = tuple(int(color1[i:i+2], 16) for i in (1, 3, 5))
        c2 = tuple(int(color2[i:i+2], 16) for i in (1, 3, 5))

        # Blend
        blended = tuple(
            int(c1[i] * (1 - alpha) + c2[i] * alpha)
            for i in range(3)
        )

        # Convert back to hex
        return f"#{blended[0]:02x}{blended[1]:02x}{blended[2]:02x}"

    def _draw_chatgpt_character(
        self,
        draw: ImageDraw.ImageDraw,
        size: tuple[int, int],
        colors: Dict[str, str]
    ) -> None:
        """Draw ChatGPT character (GPT Professor with glasses)."""
        cx, cy = size[0] // 2, size[1] // 2 - 200

        # Face (circle)
        face_radius = 200
        draw.ellipse(
            [cx - face_radius, cy - face_radius,
             cx + face_radius, cy + face_radius],
            fill="#FFFFFF",
            outline=colors["accent"],
            width=8
        )

        # Glasses (two circles connected)
        glass_radius = 60
        glass_y_offset = -20
        # Left glass
        draw.ellipse(
            [cx - 120 - glass_radius, cy + glass_y_offset - glass_radius,
             cx - 120 + glass_radius, cy + glass_y_offset + glass_radius],
            outline=colors["accent"],
            width=6
        )
        # Right glass
        draw.ellipse(
            [cx + 120 - glass_radius, cy + glass_y_offset - glass_radius,
             cx + 120 + glass_radius, cy + glass_y_offset + glass_radius],
            outline=colors["accent"],
            width=6
        )
        # Bridge
        draw.line(
            [cx - 60, cy + glass_y_offset, cx + 60, cy + glass_y_offset],
            fill=colors["accent"],
            width=6
        )

        # Eyes (behind glasses)
        eye_radius = 15
        # Left eye
        draw.ellipse(
            [cx - 120 - eye_radius, cy + glass_y_offset - eye_radius,
             cx - 120 + eye_radius, cy + glass_y_offset + eye_radius],
            fill="#000000"
        )
        # Right eye
        draw.ellipse(
            [cx + 120 - eye_radius, cy + glass_y_offset - eye_radius,
             cx + 120 + eye_radius, cy + glass_y_offset + eye_radius],
            fill="#000000"
        )

        # Smile (arc)
        draw.arc(
            [cx - 80, cy + 30, cx + 80, cy + 120],
            start=0,
            end=180,
            fill=colors["accent"],
            width=8
        )

    def _draw_gemini_character(
        self,
        draw: ImageDraw.ImageDraw,
        size: tuple[int, int],
        colors: Dict[str, str]
    ) -> None:
        """Draw Gemini character (energetic star-shaped character)."""
        cx, cy = size[0] // 2, size[1] // 2 - 200

        # Star-shaped body
        star_points = []
        num_points = 5
        outer_radius = 220
        inner_radius = 100

        for i in range(num_points * 2):
            angle = i * 3.14159 / num_points - 3.14159 / 2
            if i % 2 == 0:
                radius = outer_radius
            else:
                radius = inner_radius
            x = cx + int(radius * __import__('math').cos(angle))
            y = cy + int(radius * __import__('math').sin(angle))
            star_points.append((x, y))

        # Draw star
        draw.polygon(star_points, fill="#FFFFFF", outline=colors["accent"], width=8)

        # Face on the star
        # Happy eyes (^_^)
        draw.arc(
            [cx - 70, cy - 30, cx - 30, cy - 10],
            start=180,
            end=360,
            fill="#000000",
            width=6
        )
        draw.arc(
            [cx + 30, cy - 30, cx + 70, cy - 10],
            start=180,
            end=360,
            fill="#000000",
            width=6
        )

        # Big smile
        draw.arc(
            [cx - 90, cy + 10, cx + 90, cy + 100],
            start=0,
            end=180,
            fill=colors["accent"],
            width=10
        )

        # Sparkles around
        sparkle_positions = [
            (cx - 280, cy - 100),
            (cx + 280, cy - 100),
            (cx - 250, cy + 150),
            (cx + 250, cy + 150)
        ]
        for sx, sy in sparkle_positions:
            # Small star sparkle
            draw.line([sx - 15, sy, sx + 15, sy], fill="#FFFF00", width=4)
            draw.line([sx, sy - 15, sx, sy + 15], fill="#FFFF00", width=4)

    def _draw_claude_character(
        self,
        draw: ImageDraw.ImageDraw,
        size: tuple[int, int],
        colors: Dict[str, str]
    ) -> None:
        """Draw Claude character (wise, calm character)."""
        cx, cy = size[0] // 2, size[1] // 2 - 200

        # Face (rounded square for sophistication)
        face_size = 350
        draw.rounded_rectangle(
            [cx - face_size // 2, cy - face_size // 2,
             cx + face_size // 2, cy + face_size // 2],
            radius=50,
            fill="#FFFFFF",
            outline=colors["accent"],
            width=8
        )

        # Calm, intelligent eyes
        eye_y = cy - 40
        # Left eye
        draw.ellipse(
            [cx - 100 - 25, eye_y - 15, cx - 100 + 25, eye_y + 15],
            fill="#000000"
        )
        # Right eye
        draw.ellipse(
            [cx + 100 - 25, eye_y - 15, cx + 100 + 25, eye_y + 15],
            fill="#000000"
        )

        # Slight smile (subtle)
        draw.arc(
            [cx - 70, cy + 40, cx + 70, cy + 100],
            start=0,
            end=180,
            fill=colors["accent"],
            width=6
        )

        # Thought symbol (cloud above head)
        cloud_y = cy - face_size // 2 - 120
        # Three circles forming a thought cloud
        draw.ellipse(
            [cx - 60, cloud_y, cx - 10, cloud_y + 50],
            fill="#FFFFFF",
            outline=colors["accent"],
            width=4
        )
        draw.ellipse(
            [cx - 10, cloud_y - 20, cx + 50, cloud_y + 40],
            fill="#FFFFFF",
            outline=colors["accent"],
            width=4
        )
        draw.ellipse(
            [cx + 20, cloud_y, cx + 70, cloud_y + 50],
            fill="#FFFFFF",
            outline=colors["accent"],
            width=4
        )
