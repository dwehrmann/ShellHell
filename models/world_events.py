"""World event tracking system - the Echo System."""

from dataclasses import dataclass, field
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class WorldEvent:
    """A significant event that affects the world state."""
    timestamp: str
    event_type: str  # combat, magic, exploration, conversation, etc.
    description: str  # What happened
    location: str    # Where it happened
    impact_level: str  # minor, moderate, major, catastrophic

    # Details
    actor: str = "Player"  # Who did it
    target: str = ""       # Who/what was affected
    consequences: List[str] = field(default_factory=list)  # What changed

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'description': self.description,
            'location': self.location,
            'impact_level': self.impact_level,
            'actor': self.actor,
            'target': self.target,
            'consequences': self.consequences
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorldEvent':
        """Create from dictionary."""
        return cls(
            timestamp=data['timestamp'],
            event_type=data['event_type'],
            description=data['description'],
            location=data['location'],
            impact_level=data['impact_level'],
            actor=data.get('actor', 'Player'),
            target=data.get('target', ''),
            consequences=data.get('consequences', [])
        )


class WorldState:
    """Tracks the state of the world and significant events."""

    def __init__(self):
        """Initialize world state."""
        self.events: List[WorldEvent] = []
        self.global_flags: Dict[str, bool] = {}  # e.g., {"mines_flooded": True}
        self.environmental_changes: List[str] = []  # Persistent changes to world

    def add_event(
        self,
        event_type: str,
        description: str,
        location: str,
        impact_level: str = "minor",
        target: str = "",
        consequences: List[str] = None
    ) -> WorldEvent:
        """Record a significant event."""
        event = WorldEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            description=description,
            location=location,
            impact_level=impact_level,
            target=target,
            consequences=consequences or []
        )

        self.events.append(event)

        # Add environmental changes for major/catastrophic events
        if impact_level in ['major', 'catastrophic']:
            for consequence in event.consequences:
                if consequence not in self.environmental_changes:
                    self.environmental_changes.append(consequence)

        return event

    def get_events_at_location(self, location: str) -> List[WorldEvent]:
        """Get all events that happened at a location."""
        return [e for e in self.events if location.lower() in e.location.lower()]

    def get_events_by_type(self, event_type: str) -> List[WorldEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_major_events(self) -> List[WorldEvent]:
        """Get major and catastrophic events only."""
        return [e for e in self.events if e.impact_level in ['major', 'catastrophic']]

    def get_recent_events(self, limit: int = 10) -> List[WorldEvent]:
        """Get most recent events."""
        return self.events[-limit:] if self.events else []

    def set_flag(self, flag_name: str, value: bool = True):
        """Set a global flag (e.g., boss defeated, area unlocked)."""
        self.global_flags[flag_name] = value

    def has_flag(self, flag_name: str) -> bool:
        """Check if a flag is set."""
        return self.global_flags.get(flag_name, False)

    def get_echo_context(self, current_location: str = None) -> str:
        """
        Generate context string for LLM about world history.
        This is used to influence future descriptions.
        """
        if not self.events:
            return "The dungeon is pristine, untouched by previous adventurers."

        context_parts = []

        # Recent major events
        major_events = self.get_major_events()
        if major_events:
            context_parts.append("SIGNIFICANT EVENTS:")
            for event in major_events[-5:]:  # Last 5 major events
                context_parts.append(f"- {event.description}")

        # Environmental changes
        if self.environmental_changes:
            context_parts.append("\nENVIRONMENTAL CHANGES:")
            for change in self.environmental_changes[-5:]:
                context_parts.append(f"- {change}")

        # Location-specific history
        if current_location:
            local_events = self.get_events_at_location(current_location)
            if local_events:
                context_parts.append(f"\nEVENTS AT THIS LOCATION ({current_location}):")
                for event in local_events[-3:]:
                    context_parts.append(f"- {event.description}")

        return "\n".join(context_parts) if context_parts else "No significant history yet."

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'events': [e.to_dict() for e in self.events],
            'global_flags': self.global_flags,
            'environmental_changes': self.environmental_changes
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'WorldState':
        """Create from dictionary."""
        world = cls()
        world.events = [WorldEvent.from_dict(e) for e in data.get('events', [])]
        world.global_flags = data.get('global_flags', {})
        world.environmental_changes = data.get('environmental_changes', [])
        return world
