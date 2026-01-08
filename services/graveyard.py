"""Graveyard system - tracks all dead characters persistently."""

import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


class GraveyardEntry:
    """A fallen character's record."""

    def __init__(
        self,
        name: str,
        race: str,
        level: int,
        max_hp: int,
        attack: int,
        defense: int,
        gold: int,
        xp: int,
        death_cause: str,
        death_location: str,
        theme: str,
        spells_discovered: int,
        timestamp: str = None
    ):
        self.name = name
        self.race = race
        self.level = level
        self.max_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.gold = gold
        self.xp = xp
        self.death_cause = death_cause
        self.death_location = death_location
        self.theme = theme
        self.spells_discovered = spells_discovered
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'race': self.race,
            'level': self.level,
            'max_hp': self.max_hp,
            'attack': self.attack,
            'defense': self.defense,
            'gold': self.gold,
            'xp': self.xp,
            'death_cause': self.death_cause,
            'death_location': self.death_location,
            'theme': self.theme,
            'spells_discovered': self.spells_discovered,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GraveyardEntry':
        """Create from dictionary."""
        return cls(**data)


class Graveyard:
    """Manages the persistent graveyard of fallen characters."""

    def __init__(self, graveyard_file: Path = None):
        """Initialize graveyard."""
        if graveyard_file is None:
            # Use ~/.local/share/shellhell/graveyard.json
            home = Path.home()
            graveyard_dir = home / '.local' / 'share' / 'shellhell'
            graveyard_dir.mkdir(parents=True, exist_ok=True)
            graveyard_file = graveyard_dir / 'graveyard.json'

        self.graveyard_file = Path(graveyard_file)
        self.entries: List[GraveyardEntry] = []

        # Load existing entries
        self._load()

    def _load(self) -> None:
        """Load graveyard from file."""
        if not self.graveyard_file.exists():
            return

        try:
            with open(self.graveyard_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.entries = [
                GraveyardEntry.from_dict(entry)
                for entry in data.get('entries', [])
            ]

        except Exception as e:
            print(f"Graveyard Load Error: {e}")

    def _save(self) -> None:
        """Save graveyard to file."""
        try:
            data = {
                'version': '1.0',
                'entries': [entry.to_dict() for entry in self.entries]
            }

            with open(self.graveyard_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"Graveyard Save Error: {e}")

    def add_entry(self, entry: GraveyardEntry) -> None:
        """Add a fallen character to the graveyard."""
        self.entries.append(entry)
        self._save()

    def get_stats(self) -> Dict[str, Any]:
        """Get graveyard statistics."""
        if not self.entries:
            return {
                'total_deaths': 0,
                'max_level': 0,
                'total_gold_lost': 0,
                'most_common_cause': 'N/A'
            }

        death_causes = {}
        for entry in self.entries:
            death_causes[entry.death_cause] = death_causes.get(entry.death_cause, 0) + 1

        most_common_cause = max(death_causes.items(), key=lambda x: x[1])[0] if death_causes else 'N/A'

        return {
            'total_deaths': len(self.entries),
            'max_level': max(entry.level for entry in self.entries),
            'total_gold_lost': sum(entry.gold for entry in self.entries),
            'most_common_cause': most_common_cause
        }

    def get_recent_entries(self, limit: int = 10) -> List[GraveyardEntry]:
        """Get the most recent fallen characters."""
        return sorted(
            self.entries,
            key=lambda e: e.timestamp,
            reverse=True
        )[:limit]
