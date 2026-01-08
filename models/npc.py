"""NPC models with persistent memory."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class Interaction:
    """A single interaction with an NPC."""
    timestamp: str
    player_action: str  # What the player said/did
    npc_response: str   # How the NPC responded
    topic: str          # Topic of conversation (quest, hint, trade, etc.)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp,
            'player_action': self.player_action,
            'npc_response': self.npc_response,
            'topic': self.topic
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Interaction':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class NPC:
    """A non-player character with memory."""
    id: str  # Unique ID (e.g., "merchant_1")
    name: str
    role: str  # merchant, scholar, guard, hermit, quest_giver, companion_potential, hostile
    personality: str  # grumpy, friendly, mysterious, paranoid, etc.
    location: str  # Description of where they are

    # Memory system
    interactions: List[Interaction] = field(default_factory=list)
    knowledge: List[str] = field(default_factory=list)  # Things they know (hints, rumors)

    # State
    alive: bool = True
    hostile: bool = False
    met_before: bool = False

    # Trade (optional)
    sells_items: bool = False
    inventory_value: int = 0  # For merchants
    price_modifier: float = 1.0  # Affected by morality/relationship

    # Morality reactions
    reaction_to_morality: Dict[str, str] = field(default_factory=dict)  # {'good': 'friendly', 'evil': 'nervous'}
    base_attitude: str = "neutral"  # neutral, friendly, suspicious, hostile

    # Quest & Information
    offers_quest: bool = False
    quest_id: Optional[str] = None
    reveals_information: bool = False
    information_topics: List[str] = field(default_factory=list)  # Topics NPC can reveal

    # Combat
    can_be_negotiated: bool = True  # If hostile, can player talk them down?
    will_attack_on_provocation: bool = False  # Becomes hostile if threatened
    bribe_threshold: int = 0  # Gold needed to bribe (0 = cannot be bribed)

    # Quest markers (for quest-related NPCs)
    quest_id: Optional[str] = None  # Quest this NPC belongs to
    quest_objective_id: Optional[str] = None  # Specific objective (e.g., "rescue_hostages")

    def add_interaction(self, player_action: str, npc_response: str, topic: str = "general"):
        """Record an interaction with the player."""
        interaction = Interaction(
            timestamp=datetime.now().isoformat(),
            player_action=player_action,
            npc_response=npc_response,
            topic=topic
        )
        self.interactions.append(interaction)
        self.met_before = True

    def get_recent_interactions(self, limit: int = 5) -> List[Interaction]:
        """Get the most recent interactions."""
        return self.interactions[-limit:] if self.interactions else []

    def knows_about(self, topic: str) -> bool:
        """Check if NPC knows about a topic."""
        return any(topic.lower() in k.lower() for k in self.knowledge)

    def get_attitude(self, player_morality: int, relationship: int = 0) -> str:
        """
        Calculate NPC's attitude toward player based on morality and relationship.

        Args:
            player_morality: Player's morality score (-100 to +100)
            relationship: Personal relationship with this NPC (-100 to +100)

        Returns:
            Attitude string: 'hostile', 'suspicious', 'neutral', 'friendly', 'loyal'
        """
        # Personal relationship overrides morality
        if relationship >= 50:
            return "loyal"
        elif relationship >= 20:
            return "friendly"
        elif relationship <= -50:
            return "hostile"
        elif relationship <= -20:
            return "suspicious"

        # Check morality-based reactions
        if player_morality >= 50 and "good" in self.reaction_to_morality:
            return self.reaction_to_morality["good"]
        elif player_morality <= -50 and "evil" in self.reaction_to_morality:
            return self.reaction_to_morality["evil"]
        elif -50 < player_morality < 50 and "neutral" in self.reaction_to_morality:
            return self.reaction_to_morality["neutral"]

        # Fall back to base attitude
        return self.base_attitude

    def should_attack(self, player_morality: int, relationship: int = 0) -> bool:
        """Check if NPC should attack player."""
        if not self.alive:
            return False

        if self.hostile:
            return True

        # Check if provoked by extreme evil
        if self.will_attack_on_provocation and player_morality <= -75 and relationship < -30:
            return True

        return False

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'role': self.role,
            'personality': self.personality,
            'location': self.location,
            'interactions': [i.to_dict() for i in self.interactions],
            'knowledge': self.knowledge,
            'alive': self.alive,
            'hostile': self.hostile,
            'met_before': self.met_before,
            'sells_items': self.sells_items,
            'inventory_value': self.inventory_value,
            'price_modifier': self.price_modifier,
            'reaction_to_morality': self.reaction_to_morality,
            'base_attitude': self.base_attitude,
            'offers_quest': self.offers_quest,
            'reveals_information': self.reveals_information,
            'information_topics': self.information_topics,
            'can_be_negotiated': self.can_be_negotiated,
            'will_attack_on_provocation': self.will_attack_on_provocation,
            'bribe_threshold': self.bribe_threshold,
            'quest_id': self.quest_id,
            'quest_objective_id': self.quest_objective_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'NPC':
        """Create from dictionary."""
        interactions_data = data.get('interactions', [])
        interactions = [Interaction.from_dict(i) for i in interactions_data]

        return cls(
            id=data['id'],
            name=data['name'],
            role=data['role'],
            personality=data['personality'],
            location=data['location'],
            interactions=interactions,
            knowledge=data.get('knowledge', []),
            alive=data.get('alive', True),
            hostile=data.get('hostile', False),
            met_before=data.get('met_before', False),
            sells_items=data.get('sells_items', False),
            inventory_value=data.get('inventory_value', 0),
            price_modifier=data.get('price_modifier', 1.0),
            reaction_to_morality=data.get('reaction_to_morality', {}),
            base_attitude=data.get('base_attitude', 'neutral'),
            offers_quest=data.get('offers_quest', False),
            reveals_information=data.get('reveals_information', False),
            information_topics=data.get('information_topics', []),
            can_be_negotiated=data.get('can_be_negotiated', True),
            will_attack_on_provocation=data.get('will_attack_on_provocation', False),
            bribe_threshold=data.get('bribe_threshold', 0),
            quest_id=data.get('quest_id'),
            quest_objective_id=data.get('quest_objective_id')
        )
