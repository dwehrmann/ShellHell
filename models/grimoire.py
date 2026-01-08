"""Grimoire model for discovered spells."""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class Spell:
    """A discovered spell."""
    name: str
    effect_type: str  # fire, ice, heal, shield, lightning, etc.
    magnitude: str  # minor, moderate, major
    components: List[str]
    gesture: str
    words: str
    plausibility: float  # Original plausibility when discovered
    discovery_context: str  # Where/when it was discovered
    uses: int = 0  # How many times successfully cast

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'effect_type': self.effect_type,
            'magnitude': self.magnitude,
            'components': self.components,
            'gesture': self.gesture,
            'words': self.words,
            'plausibility': self.plausibility,
            'discovery_context': self.discovery_context,
            'uses': self.uses
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Spell':
        """Create from dictionary."""
        return cls(
            name=data['name'],
            effect_type=data['effect_type'],
            magnitude=data['magnitude'],
            components=data['components'],
            gesture=data['gesture'],
            words=data['words'],
            plausibility=data.get('plausibility', 0.5),
            discovery_context=data.get('discovery_context', ''),
            uses=data.get('uses', 0)
        )


@dataclass
class Grimoire:
    """Player's grimoire of discovered spells."""
    spells: List[Spell] = field(default_factory=list)
    total_discoveries: int = 0  # Across all deaths
    current_run_discoveries: int = 0

    def add_spell(self, spell: Spell) -> bool:
        """
        Add a spell to the grimoire if it doesn't exist.

        Returns:
            True if spell was new, False if already known
        """
        # Check if spell already exists (by name or similar components/words)
        for existing in self.spells:
            if existing.name == spell.name:
                return False
            # Similar spell check (same components + words)
            if (set(existing.components) == set(spell.components) and
                existing.words.lower() == spell.words.lower()):
                return False

        self.spells.append(spell)
        self.total_discoveries += 1
        self.current_run_discoveries += 1
        return True

    def find_spell(self, components: List[str], words: str) -> Spell:
        """Find a spell by components and words."""
        words_lower = words.lower()
        for spell in self.spells:
            if (set(spell.components) == set(components) and
                spell.words.lower() == words_lower):
                return spell
        return None

    def reset_current_run(self):
        """Reset current run discoveries (called on death)."""
        self.current_run_discoveries = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'spells': [spell.to_dict() for spell in self.spells],
            'total_discoveries': self.total_discoveries,
            'current_run_discoveries': self.current_run_discoveries
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Grimoire':
        """Create from dictionary."""
        spells = [Spell.from_dict(s) for s in data.get('spells', [])]
        return cls(
            spells=spells,
            total_discoveries=data.get('total_discoveries', 0),
            current_run_discoveries=data.get('current_run_discoveries', 0)
        )
