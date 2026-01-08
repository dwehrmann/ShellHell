"""Quest system for tracking player objectives."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class QuestObjective:
    """A single quest objective."""
    id: str  # "rescue_hostages", "defeat_boss", "find_artifact"
    description: str  # "Rette die Geiseln des Orkhäuptlings"
    type: str  # "kill", "rescue", "collect", "reach", "interact"
    target: str  # "Orkhäuptling", "Geisel", "Rubin"
    count_required: int = 1
    count_current: int = 0
    completed: bool = False
    hidden: bool = False  # If true, don't show until discovered

    def progress(self, increment: int = 1) -> bool:
        """
        Increment progress and check if completed.

        Returns:
            True if objective was just completed
        """
        if self.completed:
            return False

        old_count = self.count_current
        self.count_current = min(self.count_required, self.count_current + increment)

        if self.count_current >= self.count_required and not self.completed:
            self.completed = True
            return True

        return False

    def get_progress_string(self) -> str:
        """Get progress as string like '2/3' or '✓'."""
        if self.completed:
            return "✓"
        return f"{self.count_current}/{self.count_required}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'description': self.description,
            'type': self.type,
            'target': self.target,
            'count_required': self.count_required,
            'count_current': self.count_current,
            'completed': self.completed,
            'hidden': self.hidden
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'QuestObjective':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Quest:
    """A quest with multiple objectives."""
    id: str  # "orc_cave_main"
    title: str  # "Der Orkhäuptling"
    description: str  # "Die Orks terrorisieren die Gegend..."
    objectives: List[QuestObjective]
    theme_id: str  # "orc_cave"
    active: bool = True
    completed: bool = False

    # Rewards
    xp_reward: int = 100
    gold_reward: int = 50
    special_reward: Optional[str] = None  # Item ID or special effect

    def update_objective(self, objective_id: str, increment: int = 1) -> Optional[QuestObjective]:
        """
        Update objective progress.

        Returns:
            The objective if it was just completed, None otherwise
        """
        for obj in self.objectives:
            if obj.id == objective_id:
                just_completed = obj.progress(increment)

                # Check if all objectives are now complete
                if all(o.completed for o in self.objectives):
                    self.completed = True

                return obj if just_completed else None

        return None

    def get_active_objectives(self) -> List[QuestObjective]:
        """Get list of non-completed, non-hidden objectives."""
        return [obj for obj in self.objectives if not obj.completed and not obj.hidden]

    def get_completion_percentage(self) -> float:
        """Get quest completion as percentage."""
        if not self.objectives:
            return 100.0

        completed_count = sum(1 for obj in self.objectives if obj.completed)
        return (completed_count / len(self.objectives)) * 100.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'objectives': [obj.to_dict() for obj in self.objectives],
            'theme_id': self.theme_id,
            'active': self.active,
            'completed': self.completed,
            'xp_reward': self.xp_reward,
            'gold_reward': self.gold_reward,
            'special_reward': self.special_reward
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Quest':
        """Create from dictionary."""
        objectives = [QuestObjective.from_dict(obj) for obj in data.get('objectives', [])]
        return cls(
            id=data['id'],
            title=data['title'],
            description=data['description'],
            objectives=objectives,
            theme_id=data['theme_id'],
            active=data.get('active', True),
            completed=data.get('completed', False),
            xp_reward=data.get('xp_reward', 100),
            gold_reward=data.get('gold_reward', 50),
            special_reward=data.get('special_reward')
        )


@dataclass
class QuestManager:
    """Manages active quests for the player."""
    quests: Dict[str, Quest] = field(default_factory=dict)

    def add_quest(self, quest: Quest) -> None:
        """Add a quest to active quests."""
        self.quests[quest.id] = quest

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """Get quest by ID."""
        return self.quests.get(quest_id)

    def get_active_quests(self) -> List[Quest]:
        """Get all active (not completed) quests."""
        return [q for q in self.quests.values() if q.active and not q.completed]

    def update_objective(self, quest_id: str, objective_id: str, increment: int = 1) -> Optional[tuple]:
        """
        Update quest objective.

        Returns:
            Tuple of (quest, objective) if objective was just completed, None otherwise
        """
        quest = self.get_quest(quest_id)
        if not quest:
            return None

        obj = quest.update_objective(objective_id, increment)
        return (quest, obj) if obj else None

    def find_quest_by_target(self, target_name: str, objective_type: str = None) -> Optional[tuple]:
        """
        Find quest that has an objective with matching target.

        Returns:
            Tuple of (quest, objective) if found, None otherwise
        """
        target_lower = target_name.lower()

        for quest in self.get_active_quests():
            for obj in quest.objectives:
                if obj.completed:
                    continue

                if objective_type and obj.type != objective_type:
                    continue

                if target_lower in obj.target.lower():
                    return (quest, obj)

        return None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'quests': {qid: q.to_dict() for qid, q in self.quests.items()}
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'QuestManager':
        """Create from dictionary."""
        quests = {qid: Quest.from_dict(qdata) for qid, qdata in data.get('quests', {}).items()}
        return cls(quests=quests)
