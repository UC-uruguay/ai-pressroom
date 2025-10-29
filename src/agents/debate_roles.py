"""
Role assignment system for debate.

Assigns 3 AIs to roles: 1 orchestrator + 2 debaters.
"""
import hashlib
import random
from dataclasses import dataclass
from datetime import datetime
from typing import List, Literal

RoleType = Literal["orchestrator", "debater_a", "debater_b"]
SpeakerName = Literal["chatgpt", "gemini", "claude"]


@dataclass
class RoleAssignment:
    """Assignment of speaker to role."""
    speaker: SpeakerName
    role: RoleType
    role_description: str


class RoleManager:
    """Manage role assignments for debates."""

    SPEAKERS: List[SpeakerName] = ["chatgpt", "gemini", "claude"]

    @staticmethod
    def assign_roles(date: datetime) -> dict[SpeakerName, RoleType]:
        """
        Assign roles based on date (deterministic but pseudo-random).

        Args:
            date: Date for episode

        Returns:
            Dictionary mapping speaker to role
        """
        # Use date as seed for reproducible randomness
        date_str = date.strftime("%Y-%m-%d")
        seed = int(hashlib.md5(date_str.encode()).hexdigest(), 16) % (10 ** 8)
        rng = random.Random(seed)

        # Shuffle speakers
        speakers = RoleManager.SPEAKERS.copy()
        rng.shuffle(speakers)

        # Assign roles
        return {
            speakers[0]: "orchestrator",
            speakers[1]: "debater_a",
            speakers[2]: "debater_b"
        }

    @staticmethod
    def get_role_description(role: RoleType) -> str:
        """
        Get description of role.

        Args:
            role: Role type

        Returns:
            Role description in Japanese
        """
        descriptions = {
            "orchestrator": (
                "オーケストレーター（司会兼挑発者）として、討論を仕切ります。"
                "あなたの役割は中立的な司会ではなく、**対立を促進**し、"
                "**本質を突く質問**をし、**矛盾を指摘**することです。"
            ),
            "debater_a": (
                "討論者Aとして、トピックについて最初の立場を表明します。"
                "あなたは自分の意見を**論理的に主張**し、"
                "相手の反論に対して**批判的に応答**します。"
            ),
            "debater_b": (
                "討論者Bとして、討論者Aとは**異なる視点**を提示します。"
                "あなたは相手の主張の**問題点を指摘**し、"
                "**対立的な立場**から議論を展開します。"
            )
        }
        return descriptions[role]

    @staticmethod
    def get_role_assignments(
        date: datetime
    ) -> List[RoleAssignment]:
        """
        Get detailed role assignments.

        Args:
            date: Date for episode

        Returns:
            List of RoleAssignment objects
        """
        role_map = RoleManager.assign_roles(date)

        assignments = []
        for speaker, role in role_map.items():
            assignments.append(RoleAssignment(
                speaker=speaker,
                role=role,
                role_description=RoleManager.get_role_description(role)
            ))

        return assignments
