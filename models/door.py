"""Door and key models."""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class DoorState(Enum):
    """Door states."""
    OPEN = "open"
    CLOSED = "closed"
    LOCKED = "locked"


class Direction(Enum):
    """Cardinal directions."""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


@dataclass
class Door:
    """A door between rooms."""
    direction: Direction
    state: DoorState
    key_id: Optional[str] = None  # ID of key required to unlock (e.g., "rusty_key")

    def is_passable(self) -> bool:
        """Check if door can be passed through."""
        return self.state in [DoorState.OPEN, DoorState.CLOSED]

    def unlock(self, key_id: str) -> bool:
        """
        Unlock door with key.

        Args:
            key_id: ID of the key being used

        Returns:
            True if unlocked successfully
        """
        if self.state != DoorState.LOCKED:
            return False

        if self.key_id and key_id == self.key_id:
            self.state = DoorState.CLOSED
            return True

        return False

    def open(self) -> bool:
        """
        Open door (if not locked).

        Returns:
            True if opened successfully
        """
        if self.state == DoorState.LOCKED:
            return False

        self.state = DoorState.OPEN
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'direction': self.direction.value,
            'state': self.state.value,
            'key_id': self.key_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Door':
        """Create from dictionary."""
        return cls(
            direction=Direction(data['direction']),
            state=DoorState(data['state']),
            key_id=data.get('key_id')
        )
