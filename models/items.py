"""Item and equipment models."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ItemType(Enum):
    """Types of items."""
    WEAPON = "weapon"
    ARMOR = "armor"
    RING = "ring"
    HEAD = "head"
    CONSUMABLE = "consumable"
    KEY = "key"
    MATERIAL = "material"  # Spell components, crafting materials


@dataclass
class ItemStats:
    """Stats bonuses from an item."""
    strength: int = 0
    dexterity: int = 0
    wisdom: int = 0
    intelligence: int = 0
    attack: int = 0
    defense: int = 0
    hp: int = 0


@dataclass
class Item:
    """Represents an item that can be found or equipped."""
    id: str
    name: str
    description: str
    type: ItemType
    stats: ItemStats
    is_curse: bool = False
    equipped: bool = False
    key_id: Optional[str] = None  # For keys: ID to match with locked doors
    special_effects: dict = field(default_factory=dict)  # Special effects like lifesteal, poison, etc.

    @classmethod
    def from_dict(cls, data: dict) -> 'Item':
        """Create an Item from a dictionary."""
        stats_data = data.get('stats', {})
        stats = ItemStats(**stats_data)
        return cls(
            id=data.get('id', ''),
            name=data.get('name', ''),
            description=data.get('description', ''),
            type=ItemType(data.get('type', 'consumable')),
            stats=stats,
            is_curse=data.get('isCurse', False),
            equipped=data.get('equipped', False),
            key_id=data.get('key_id'),
            special_effects=data.get('special_effects', {})
        )

    def to_dict(self) -> dict:
        """Convert item to dictionary for serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type.value,
            'stats': {
                'strength': self.stats.strength,
                'dexterity': self.stats.dexterity,
                'wisdom': self.stats.wisdom,
                'intelligence': self.stats.intelligence,
                'attack': self.stats.attack,
                'defense': self.stats.defense,
                'hp': self.stats.hp,
            },
            'isCurse': self.is_curse,
            'equipped': self.equipped,
            'key_id': self.key_id,
            'special_effects': self.special_effects
        }

    def get_special_effect(self, effect_type: str) -> Optional[any]:
        """Get a special effect value by type."""
        return self.special_effects.get(effect_type)

    def has_lifesteal(self) -> bool:
        """Check if item has lifesteal effect (from description or special_effects)."""
        # Check special_effects field
        if 'lifesteal' in self.special_effects:
            return True
        # Check description for keywords
        desc_lower = self.description.lower()
        keywords = ['heilt den träger', 'life steal', 'lifesteal', 'saugt', 'lebenskraft']
        return any(keyword in desc_lower for keyword in keywords)
