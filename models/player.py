"""Player and character models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from models.items import Item, ItemType
from models.grimoire import Grimoire


@dataclass
class Attributes:
    """Character attributes."""
    strength: int = 10
    dexterity: int = 10
    wisdom: int = 10
    intelligence: int = 10
    vitality: int = 10

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'strength': self.strength,
            'dexterity': self.dexterity,
            'wisdom': self.wisdom,
            'intelligence': self.intelligence,
            'vitality': self.vitality
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Attributes':
        """Create from dictionary."""
        # Handle old saves without vitality
        if 'vitality' not in data:
            data['vitality'] = 10
        return cls(**data)


@dataclass
class Buff:
    """Temporary buff effect."""
    name: str
    type: str  # 'attack' or 'defense'
    value: int
    duration: int


@dataclass
class Player:
    """The player character."""
    name: str = ""
    race: str = ""
    theme: str = ""
    attributes: Attributes = field(default_factory=Attributes)

    # Combat stats
    hp: int = 50
    max_hp: int = 50
    attack: int = 10
    defense: int = 5

    # Progress
    gold: int = 0
    xp: int = 0
    level: int = 1

    # Position
    x: int = 0
    y: int = 0
    z: int = 0  # Level/Ebene (0 = oberste Ebene)

    # Skills and buffs
    unlocked_skills: List[str] = field(default_factory=list)
    cooldowns: Dict[str, int] = field(default_factory=dict)
    buffs: List[Buff] = field(default_factory=list)

    # Inventory
    inventory: List[Item] = field(default_factory=list)
    equipment: Dict[str, Optional[Item]] = field(default_factory=lambda: {
        'weapon': None,
        'armor': None,
        'ring': None,
        'head': None
    })

    # Magic system
    grimoire: Grimoire = field(default_factory=Grimoire)

    # Character traits
    quirk: Optional[Dict[str, any]] = None  # Stat bonus, narrative malus
    gift: Optional[Dict[str, any]] = None  # Secret bonus, stat malus

    # Morality & Reputation
    morality: int = 0  # Range: -100 (evil) to +100 (good)
    npc_relationships: Dict[str, int] = field(default_factory=dict)  # npc_id -> attitude (-100 to +100)

    # Quest System
    quest_manager: Optional['QuestManager'] = None  # Will be initialized in __post_init__ or from_dict

    def get_effective_attack(self) -> int:
        """Calculate attack including equipment bonuses."""
        bonus = sum(
            item.stats.attack
            for item in self.equipment.values()
            if item is not None
        )
        return self.attack + bonus

    def get_effective_defense(self) -> int:
        """Calculate defense including equipment bonuses."""
        bonus = sum(
            item.stats.defense
            for item in self.equipment.values()
            if item is not None
        )
        return self.defense + bonus

    def equip_item(self, item: Item) -> bool:
        """Equip an item from inventory."""
        if item not in self.inventory:
            return False

        slot = item.type.value
        if slot not in self.equipment:
            return False

        # Check if current item in slot is cursed (can't be unequipped!)
        if self.equipment[slot] and self.equipment[slot].is_curse:
            return False  # Can't replace cursed item

        # Unequip current item in that slot
        if self.equipment[slot]:
            self.equipment[slot].equipped = False

        # Equip new item
        self.equipment[slot] = item
        item.equipped = True
        return True

    def uncurse_item(self, item: Item) -> bool:
        """Remove curse from an item (requires special NPC/action)."""
        if not item.is_curse:
            return False

        item.is_curse = False
        # Optionally: also remove curse-specific effects
        if item.special_effects:
            curse_effects = ['curse_damage_per_turn', 'fire_weakness', 'cold_weakness']
            for effect in curse_effects:
                if effect in item.special_effects:
                    del item.special_effects[effect]

        return True

    def apply_curse_damage(self) -> int:
        """Apply damage from cursed items. Returns total damage taken."""
        total_damage = 0

        for slot, item in self.equipment.items():
            if item and item.is_curse and item.special_effects:
                curse_dmg = item.special_effects.get('curse_damage_per_turn', 0)
                if curse_dmg > 0:
                    total_damage += curse_dmg

        if total_damage > 0:
            self.hp = max(0, self.hp - total_damage)

        return total_damage

    def to_dict(self) -> dict:
        """Convert player to dictionary for serialization."""
        return {
            'name': self.name,
            'race': self.race,
            'theme': self.theme,
            'attributes': self.attributes.to_dict(),
            'hp': self.hp,
            'max_hp': self.max_hp,
            'attack': self.attack,
            'defense': self.defense,
            'gold': self.gold,
            'xp': self.xp,
            'level': self.level,
            'x': self.x,
            'y': self.y,
            'z': self.z,
            'unlocked_skills': self.unlocked_skills,
            'cooldowns': self.cooldowns,
            'buffs': [{'name': b.name, 'type': b.type, 'value': b.value, 'duration': b.duration} for b in self.buffs],
            'inventory': [item.to_dict() for item in self.inventory],
            'equipment': {k: v.to_dict() if v else None for k, v in self.equipment.items()},
            'grimoire': self.grimoire.to_dict(),
            'quirk': self.quirk,
            'gift': self.gift,
            'morality': self.morality,
            'npc_relationships': self.npc_relationships,
            'quest_manager': self.quest_manager.to_dict() if self.quest_manager else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Player':
        """Create player from dictionary."""
        player = cls(
            name=data.get('name', ''),
            race=data.get('race', ''),
            theme=data.get('theme', ''),
            attributes=Attributes.from_dict(data.get('attributes', {})),
            hp=data.get('hp', 50),
            max_hp=data.get('max_hp', 50),
            attack=data.get('attack', 10),
            defense=data.get('defense', 5),
            gold=data.get('gold', 0),
            xp=data.get('xp', 0),
            level=data.get('level', 1),
            x=data.get('x', 0),
            y=data.get('y', 0),
            z=data.get('z', 0),
            unlocked_skills=data.get('unlocked_skills', []),
            cooldowns=data.get('cooldowns', {}),
        )

        # Restore buffs
        player.buffs = [Buff(**b) for b in data.get('buffs', [])]

        # Restore inventory
        player.inventory = [Item.from_dict(item_data) for item_data in data.get('inventory', [])]

        # Restore equipment
        equipment_data = data.get('equipment', {})
        player.equipment = {
            k: Item.from_dict(v) if v else None
            for k, v in equipment_data.items()
        }

        # Restore grimoire
        grimoire_data = data.get('grimoire', {})
        player.grimoire = Grimoire.from_dict(grimoire_data) if grimoire_data else Grimoire()

        # Restore character traits and morality
        player.quirk = data.get('quirk')
        player.gift = data.get('gift')
        player.morality = data.get('morality', 0)
        player.npc_relationships = data.get('npc_relationships', {})

        # Restore quest manager
        quest_manager_data = data.get('quest_manager')
        if quest_manager_data:
            from models.quest import QuestManager
            player.quest_manager = QuestManager.from_dict(quest_manager_data)
        else:
            from models.quest import QuestManager
            player.quest_manager = QuestManager()

        return player

    def adjust_morality(self, amount: int, reason: str = "") -> None:
        """
        Adjust player's morality score.

        Args:
            amount: Change in morality (-100 to +100)
            reason: Why the morality changed (for logging)
        """
        old_morality = self.morality
        self.morality = max(-100, min(100, self.morality + amount))

        # Log significant changes
        if abs(amount) >= 10:
            if self.morality >= 50 and old_morality < 50:
                # Crossed into "good" territory
                pass  # Game will log this
            elif self.morality <= -50 and old_morality > -50:
                # Crossed into "evil" territory
                pass  # Game will log this

    def get_relationship(self, npc_id: str) -> int:
        """Get relationship level with an NPC (-100 to +100)."""
        return self.npc_relationships.get(npc_id, 0)

    def adjust_relationship(self, npc_id: str, amount: int) -> None:
        """Adjust relationship with an NPC."""
        current = self.get_relationship(npc_id)
        self.npc_relationships[npc_id] = max(-100, min(100, current + amount))

    def get_reputation_tier(self) -> str:
        """Get reputation tier for display."""
        if self.morality >= 75:
            return "Heiliger"
        elif self.morality >= 50:
            return "Heldenhaft"
        elif self.morality >= 25:
            return "Gut"
        elif self.morality >= -25:
            return "Neutral"
        elif self.morality >= -50:
            return "Böse"
        elif self.morality >= -75:
            return "Verdorben"
        else:
            return "Dämonisch"
