"""Game state management."""

from enum import Enum


class GameState(Enum):
    """Main game states."""
    START = "START"
    THEME_SELECTION = "THEME_SELECTION"  # Choose dungeon theme
    CHARACTER_CREATION = "CHARACTER_CREATION"
    EXPLORING = "EXPLORING"
    CONVERSATION = "CONVERSATION"  # Talking to NPC - all input goes to NPC
    ENCOUNTER = "ENCOUNTER"  # Pre-combat: Spieler kann reagieren (anschleichen, reden, angreifen)
    COMBAT = "COMBAT"
    GAMEOVER = "GAMEOVER"
    VICTORY = "VICTORY"


class CreationStep(Enum):
    """Character creation steps."""
    ROLLING = "ROLLING"
    RACE = "RACE"
    QUIRK = "QUIRK"
    NAME = "NAME"


class RoomType(Enum):
    """Room types in the dungeon."""
    EMPTY = "EMPTY"
    MONSTER = "MONSTER"
    TREASURE = "TREASURE"
    STAIRS_DOWN = "STAIRS_DOWN"  # Treppe nach unten (tiefer ins Dungeon)
    STAIRS_UP = "STAIRS_UP"      # Treppe nach oben (zurück/raus)
