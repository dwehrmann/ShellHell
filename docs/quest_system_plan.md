# Quest System - Implementierungsplan

## Problem
- Story-Context ist zu vage ("Die Orks halten Gefangene")
- Keine konkreten Ziele oder Quest-Marker
- Boss-Raum spawnt random Monster, nicht theme-spezifische Bosse
- NPCs sind nicht mit der Story verknüpft

## Lösung: Quest-System

### Phase 1: Quest-Modell

```python
# models/quest.py
@dataclass
class QuestObjective:
    """Ein Quest-Ziel."""
    id: str  # "rescue_hostages", "defeat_boss", "find_artifact"
    description: str  # "Rette die Geiseln des Orkhäuptlings"
    type: str  # "kill", "rescue", "collect", "reach"
    target: str  # "Orkhäuptling", "Geisel", "Rubin"
    count_required: int = 1
    count_current: int = 0
    completed: bool = False

@dataclass
class Quest:
    """Eine Quest mit mehreren Zielen."""
    id: str  # "orc_cave_main"
    title: str  # "Der Orkhäuptling"
    description: str  # "Die Orks terrorisieren die Gegend..."
    objectives: List[QuestObjective]
    theme_id: str  # "orc_cave"
    active: bool = True
    completed: bool = False
```

### Phase 2: Theme-spezifische Quests

```python
# constants.py - Quest Templates
THEME_QUESTS = {
    "orc_cave": {
        "id": "orc_cave_main",
        "title": "Der Orkhäuptling",
        "description": "Die Orks haben Dorfbewohner entführt. Rette sie und besiege den Häuptling!",
        "objectives": [
            {
                "id": "rescue_hostages",
                "description": "Rette 3 Geiseln",
                "type": "rescue",
                "target": "Geisel",
                "count_required": 3
            },
            {
                "id": "defeat_boss",
                "description": "Besiege den Orkhäuptling",
                "type": "kill",
                "target": "Orkhäuptling",
                "count_required": 1
            }
        ]
    },

    "dwarf_halls": {
        "id": "dwarf_halls_main",
        "title": "Der Verfluchte Edelstein",
        "description": "Finde den verfluchten Edelstein und zerstöre ihn!",
        "objectives": [
            {
                "id": "find_gem",
                "description": "Finde den Seelenedelstein",
                "type": "collect",
                "target": "Seelenedelstein",
                "count_required": 1
            },
            {
                "id": "destroy_gem",
                "description": "Zerstöre den Seelenedelstein",
                "type": "interact",
                "target": "Seelenedelstein",
                "count_required": 1
            }
        ]
    }

    # ... für jedes Theme
}
```

### Phase 3: Boss-Spawning

```python
# game/dungeon_generation.py oder models/dungeon.py

def spawn_theme_boss(room: Room, theme_config: ThemeConfig, quest: Quest):
    """Spawne theme-spezifischen Boss im Stairs-Raum."""
    if theme_config.boss_monster:
        boss_template = theme_config.boss_monster
        room.monster = Monster.from_template(boss_template)

        # Markiere als Quest-Boss
        room.is_boss_room = True
        room.boss_quest_id = quest.id
```

### Phase 4: Quest-NPC Spawning

```python
# Bei Dungeon-Generation:
def spawn_quest_npcs(dungeon: Dungeon, quest: Quest, theme_config: ThemeConfig):
    """Spawne Quest-relevante NPCs."""
    for objective in quest.objectives:
        if objective.type == "rescue":
            # Spawne Geiseln in random Räumen
            for i in range(objective.count_required):
                room = dungeon.get_random_empty_room()
                hostage = NPC(
                    id=f"hostage_{i}",
                    name=f"Geisel #{i+1}",
                    role="hostage",
                    personality="frightened",
                    location=room.description,
                    # Quest-Marker
                    quest_relevant=True,
                    quest_id=quest.id,
                    quest_objective_id=objective.id
                )
                room.npc = hostage
```

### Phase 5: Quest-Tracking

```python
# In Game oder Player:
def update_quest_objective(quest_id: str, objective_id: str, increment: int = 1):
    """Aktualisiere Quest-Fortschritt."""
    quest = self.player.active_quests.get(quest_id)
    if not quest:
        return

    for obj in quest.objectives:
        if obj.id == objective_id:
            obj.count_current = min(obj.count_required, obj.count_current + increment)

            if obj.count_current >= obj.count_required:
                obj.completed = True
                self.add_log('system', f"✓ Quest Ziel erreicht: {obj.description}")

    # Check if all objectives complete
    if all(obj.completed for obj in quest.objectives):
        quest.completed = True
        self.add_log('system', f"🏆 QUEST ABGESCHLOSSEN: {quest.title}!")
        # Belohnungen...
```

### Phase 6: NPC Integration

```python
# In NPC dialogue:
def generate_npc_dialogue(...):
    """NPCs erwähnen aktive Quests."""

    # Füge Quest-Kontext hinzu
    quest_context = ""
    if player.active_quests:
        quest_context = "\n\nAKTIVE QUESTS:\n"
        for quest in player.active_quests.values():
            quest_context += f"- {quest.title}: {quest.description}\n"
            for obj in quest.objectives:
                status = "✓" if obj.completed else f"{obj.count_current}/{obj.count_required}"
                quest_context += f"  [{status}] {obj.description}\n"

    # NPCs können Hinweise zu Quest-Zielen geben
    # "Ich habe Schreie aus dem Osten gehört..." (Hinweis auf Geisel)
```

### Phase 7: Boss-Room Beschreibung

```python
# In ai_service.py - room description:
def _generate_single_room_description(...):
    """Boss-Räume bekommen spezielle Beschreibungen."""

    if room.is_boss_room and room.monster:
        prompt += f"\n\nWICHTIG: Dies ist der BOSS-RAUM! Beschreibe ihn episch."
        prompt += f"\nBoss: {room.monster.name} (HP: {room.monster.hp})"
        prompt += f"\nThema: {theme_config.name}"
```

## Implementierungs-Reihenfolge

1. **models/quest.py** - Quest und QuestObjective Klassen
2. **constants.py** - THEME_QUESTS Template für jedes Theme
3. **main.py** - Quest beim Dungeon-Start laden
4. **models/dungeon.py** - spawn_theme_boss(), spawn_quest_npcs()
5. **game/actions.py** - Quest-Updates bei NPC-Interaktion, Monster-Tod
6. **services/ai_service.py** - Quest-Kontext in NPCs und Beschreibungen
7. **main.py** - Quest-Status im Status-Command anzeigen

## Beispiel-Flow (Orc Cave)

1. **Dungeon Start**: Quest "Der Orkhäuptling" wird geladen
2. **Generation**:
   - Orkhäuptling spawnt im Stairs-Raum
   - 3 Geiseln spawnen in random Räumen
3. **Spieler findet Geisel**:
   - Spricht mit Geisel → "Bitte rette mich!"
   - Interaktion → update_quest_objective("rescue_hostages", +1)
   - Log: "✓ Quest Ziel: Rette 3 Geiseln (1/3)"
4. **Spieler findet Boss-Raum**:
   - Description: "Ein massiver Thronsaal. Auf einem Knochenthron sitzt der Orkhäuptling..."
   - Kampf mit Orkhäuptling (boss_monster Template)
5. **Nach Sieg**:
   - update_quest_objective("defeat_boss", +1)
   - Quest completed!
   - Belohnung: +500 XP, spezielles Item

## Nächste Schritte

Soll ich das implementieren? Das ist ca. 2-3 Stunden Arbeit für ein vollständiges Quest-System.
