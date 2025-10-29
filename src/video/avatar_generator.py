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
        Generate avatar image for a speaker.

        Args:
            speaker: Speaker name (chatgpt, gemini, claude)
            character: Character configuration
            size: Image size (width, height)

        Returns:
            Path to generated image
        """
        output_path = self.output_dir / f"avatar_{speaker}.png"

        # Skip if already exists
        if output_path.exists():
            logger.info(f"Avatar already exists: {output_path}")
            return output_path

        logger.info(f"Generating avatar for {speaker}...")

        # Get colors
        colors = self.COLORS.get(speaker, self.COLORS["chatgpt"])

        # Create image
        img = Image.new("RGB", size, colors["background"])
        draw = ImageDraw.Draw(img)

        # Draw accent gradient (simple two-tone)
        for i in range(size[1] // 2):
            alpha = i / (size[1] // 2)
            # Simple blend
            draw.line(
                [(0, i), (size[0], i)],
                fill=colors["background"]
            )

        # Draw bottom accent bar
        accent_height = size[1] // 4
        draw.rectangle(
            [(0, size[1] - accent_height), (size[0], size[1])],
            fill=colors["accent"]
        )

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
            bbox = draw.textbbox((0, 0), company, font=font_small)
            text_width = bbox[2] - bbox[0]
            x = (size[0] - text_width) // 2
            y = size[1] - accent_height // 2 - 20

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
