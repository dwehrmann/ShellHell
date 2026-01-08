# ShellHell - Implementierungsplan

Basierend auf `/home/dwehrmann/dev/DungeonCLI/overview.md`

## Status Quo (Was bereits existiert)

### ✅ Implementiert
- Multi-Provider Support (Gemini, DeepSeek, OpenAI)
- Character Creation (4d6 drop lowest, Rassen, Namen)
- Dungeon Generation (6x6 Grid, on-the-fly Raumbeschreibungen)
- Basic Combat System (Turn-based, ATK vs DEF)
- Inventory & Equipment System
- Freie Aktionen mit Würfelsystem (keyword-basiert)
- Level-Up System (XP, Stats)

### ⚠️ Teilweise implementiert
- AI-Integration: **Nur Narrator**, kein Interpreter
- Action Resolution: **Keyword-basiert**, nicht plausibility-basiert
- Würfelsystem: **DC-basiert**, nicht plausibility-basiert

### ❌ Fehlt noch
- Zwei-Stufen LLM System (Interpreter → Validator → Narrator)
- Experimentelles Magic System (discovery-based)
- Consequence Chain System
- Morality Drift / Reputation
- Grimoire Persistence & Legacy
- Permadeath mit Graveyard
- Save/Load mit Checksums
- Theme System
- Premium Content System

---

## Architektur-Änderungen

### Problem: Provider vs. Design-Spezifikation
**Design (overview.md):** Nutzt Anthropic Claude Haiku
**Aktuell:** Multi-Provider (Gemini, DeepSeek, OpenAI)

**Lösung:** Provider-System **behalten**, aber Claude Haiku als Standard empfehlen

### Problem: Einstufiges LLM (nur Narrator)
**Design:** Interpreter → Validator → Narrator (3 Stufen)
**Aktuell:** Nur Narrator

**Lösung:** `AIService` erweitern um:
- `interpret_action()` - Gibt structured JSON zurück
- `validate_action()` - Engine entscheidet (bereits in `actions.py` als Skeleton)
- `narrate_result()` - Bereits vorhanden

### Problem: Keyword-basierte Actions
**Design:** Plausibility Score (0.0-1.0) vom LLM
**Aktuell:** Keyword-Matching (force→STR, sneak→DEX)

**Lösung:** `ActionResolver` umbauen:
1. LLM interpretiert Action → gibt Plausibility
2. Engine validiert (Physik, Inventory, etc.)
3. Roll gegen Plausibility
4. LLM erzählt Ergebnis

---

## Implementierungsplan

### **Phase 1: Zwei-Stufen LLM System** (Prio: HOCH)

#### 1A: Interpreter Mode
**Ziel:** LLM parst freie Eingaben zu strukturiertem JSON

**Neue Dateien:**
- `services/prompts.py` - System Prompts für Interpreter/Narrator/Magic
- Erweiterung von `services/ai_service.py`:
  ```python
  def interpret_action(self, action_text, player_state, room_state) -> dict:
      """
      Returns:
      {
          "action_type": "physical_attack|use_item|move|interact_object|social|environment_action|attempt_magic",
          "target": "goblin",
          "method": "swing sword at head",
          "plausibility": 0.85,
          "requirements": ["sword equipped"],
          "valid": true,
          "components_used": []
      }
      """
  ```

**Änderungen:**
- `game/actions.py`:
  - Remove keyword-matching
  - Call `ai.interpret_action()` statt lokales Pattern-Matching
  - Use returned `plausibility` für Roll

**Test:** `"I swing my sword at the goblin"` → `{"action_type": "physical_attack", "plausibility": 0.9}`

---

#### 1B: Validator erweitern
**Ziel:** Engine hat finales Wort über Physik/Inventory

**Änderungen in `game/actions.py`:**
```python
class ActionValidator:
    FORBIDDEN_METHODS = ['teleport', 'fly', 'phase_through']

    def validate(self, intent, player, room):
        # Check target exists
        if intent['target']:
            valid_targets = [m.name for m in room.monsters] + ["room object"]
            if intent['target'] not in valid_targets:
                return {"allowed": False, "reason": "TARGET_NOT_PRESENT"}

        # Check physics violations
        for forbidden in self.FORBIDDEN_METHODS:
            if forbidden in intent['method'].lower():
                if not self.has_ability(player, forbidden):
                    return {"allowed": False, "reason": "PHYSICS_VIOLATION"}

        # Check plausibility threshold
        if intent['plausibility'] < 0.1:
            return {"allowed": False, "reason": "IMPLAUSIBLE"}

        return {"allowed": True}
```

---

### **Phase 2: Experimentelles Magic System** (Prio: HOCH)

#### 2A: Magic Discovery
**Ziel:** Spieler experimentieren mit Components + Gestures + Words

**Neue Dateien:**
- `models/magic.py`:
  ```python
  @dataclass
  class Spell:
      id: str
      name: str
      components: List[str]
      gesture: str
      words: str
      effect_type: str  # fire, ice, heal, shield, etc.
      magnitude: str    # minor, moderate, major
      reliability: float  # 0.0-1.0, increases with use
      discovery_time: int

  @dataclass
  class Grimoire:
      discovered_spells: List[Spell]
      spell_usage_count: Dict[str, int]  # spell_id → count
  ```

- Erweiterung `services/ai_service.py`:
  ```python
  def evaluate_magic(self, components, gesture, words, environment) -> dict:
      """
      Returns:
      {
          "is_valid_attempt": true,
          "plausibility": 0.75,
          "effect_type": "fire",
          "magnitude": "moderate",
          "is_discovery": true,
          "spell_name": "Flame Burst",
          "consequence": "none"
      }
      """
  ```

**Integration:**
- `game/actions.py`: Wenn `action_type == "attempt_magic"`:
  - Call `ai.evaluate_magic()`
  - Roll gegen Plausibility
  - Bei Erfolg: Save to Grimoire (persistent!)

---

#### 2B: Grimoire Persistence
**Ziel:** Entdeckte Spells überleben den Tod

**Neue Datei:**
- `services/grimoire_manager.py`:
  ```python
  class GrimoireManager:
      def __init__(self):
          self.grimoire_path = Path.home() / ".shellhell" / "grimoire.json"

      def load_grimoire(self) -> Grimoire:
          # Load with checksum verification

      def save_grimoire(self, grimoire: Grimoire):
          # Save with SHA256 checksum

      def add_spell(self, spell: Spell):
          grimoire = self.load_grimoire()
          grimoire.discovered_spells.append(spell)
          self.save_grimoire(grimoire)
  ```

**Integration:**
- `main.py`: Beim Start Grimoire laden
- `game/actions.py`: Nach Magic Discovery → `grimoire_manager.add_spell()`

---

### **Phase 3: Consequence & Morality** (Prio: MITTEL)

#### 3A: Consequence Chain System
**Ziel:** Actions haben langfristige Folgen

**Neue Datei:**
- `models/consequences.py`:
  ```python
  @dataclass
  class Consequence:
      trigger_action: str  # "burned_tavern", "befriended_npc"
      turn_created: int
      consequence_type: str  # "reputation", "world_state", "npc_reaction"
      severity: int  # 1-5
      resolved: bool = False

  class ConsequenceTracker:
      def __init__(self):
          self.active_consequences: List[Consequence] = []

      def add_consequence(self, action: str, severity: int):
          # Track major player actions

      def check_triggers(self, current_state) -> List[str]:
          # Return list of triggered consequences
  ```

**Integration:**
- Nach jedem LLM Narrator Call: Extract consequences from narration
- Store in `game.consequence_tracker`
- Bei Room Entry: Check for triggered consequences

---

#### 3B: Morality Drift / Reputation
**Ziel:** NPC reactions basierend auf Player-Verhalten

**Neue Datei:**
- `models/reputation.py`:
  ```python
  class Reputation:
      traits: Dict[str, int]  # "pragmatist": 5, "pacifist": -2, "pyromaniac": 8

      def update(self, action_type: str, severity: int):
          # Increment relevant trait scores

      def get_dominant_trait(self) -> str:
          # Return highest trait

      def affects_dialogue(self, npc_type: str) -> str:
          # "guards_attack", "merchants_refuse", "thieves_recruit"
  ```

**Integration:**
- Nach jedem erfolgreichen Action: Update Reputation
- Bei NPC Encounter: Check Reputation → modify behavior

---

### **Phase 4: State Management** (Prio: HOCH)

#### 4A: Save/Load mit Checksums
**Ziel:** Anti-Cheat mit SHA256

**Neue Datei:**
- `services/state_manager.py` (bereits im Design als `core/state.py`)
  ```python
  class StateManager:
      def save(self, data, filename):
          # Write JSON + SHA256 checksum

      def load(self, filename):
          # Verify checksum, reject if tampered

      def save_current_run(self, player, dungeon, game_state):
          # Save to ~/.shellhell/current_run.json

      def load_current_run(self):
          # Load active game
  ```

**Integration:**
- `main.py`: Beim Quit → `state_manager.save_current_run()`
- `main.py`: Beim Start → Option "Continue" → `state_manager.load_current_run()`

---

#### 4B: Permadeath & Graveyard
**Ziel:** Tod ist permanent, aber Legacy bleibt

**Erweiterung `services/state_manager.py`:**
```python
def save_to_graveyard(self, character):
    # Save death record to ~/.shellhell/graveyard/char_XXX.json
    # Include: name, level, depth, cause_of_death, equipment, grimoire_size

def get_graveyard_entries(self) -> List[dict]:
    # Load all past characters for display
```

**Integration:**
- `main.py`: Bei HP <= 0 → GameState.GAMEOVER → `save_to_graveyard()`
- Neue Option im Hauptmenü: "View Graveyard"
- Legacy: Nächster Charakter kann altes Grimoire finden (bereits geladen beim Start)

---

### **Phase 5: Theme System** (Prio: MITTEL)

#### 5A: Content Structure
**Neue Dateien:**
- `content/base/themes.json` - 3-4 Free Themes
- `content/base/enemies.json` - Theme-spezifische Gegner
- `content/base/items.json` - Theme-spezifische Items

**Format (siehe overview.md Zeile 625-696)**

**Änderungen:**
- `main.py`: Beim Start → Theme aus JSON laden (statt hardcoded)
- `models/dungeon.py`: Theme-aware Enemy Spawning
- `services/ai_service.py`: Inject theme in all prompts

---

#### 5B: Theme Selection
**UI-Änderung:**
```
$ ./run.sh

SHELLHELL v0.7.1
================

[N]ew Game
[C]ontinue
[G]raveyard
[Q]uit

> n

Select Theme:
  1. Abandoned Laboratory
  2. Forgotten Crypt
  3. Sunken Ruins
  [Premium: 4-9 locked]

> 1
```

---

### **Phase 6: Premium Content** (Prio: NIEDRIG)

#### 6A: License System
**Neue Datei:**
- `core/license_manager.py` (siehe overview.md Zeile 580-616)

**Integration:**
- Check `content/premium/.premium_key` Existenz
- Show upsell 1x pro Session
- Lock Themes 4-9 wenn kein Key

---

## Priorisierung & Zeitplan

### Sprint 1: Core LLM Integration ✅ COMPLETED
- [x] Phase 1A: Interpreter Mode
- [x] Phase 1B: Validator erweitern
- [x] Test: Freie Aktionen mit Plausibility

**Ziel:** `"I tip the chandelier onto the goblin"` funktioniert mit plausibility 0.75 ✓

**Ergebnis:**
- `services/prompts.py` erstellt (INTERPRETER_PROMPT, NARRATOR_PROMPT, MAGIC_EVALUATOR_PROMPT)
- `ai_service.py`: `interpret_action()` implementiert
- `ActionValidator` mit Physik-Checks, Target-Validierung, Plausibility-Threshold
- `ActionResolver` nutzt LLM statt Keywords
- Plausibility (0.0-1.0) → DC (5-20) Mapping
- Test Suite bestätigt Funktionalität
- **Siehe**: `SPRINT1_SUMMARY.md` für Details

---

### Sprint 2: Magic System
- [ ] Phase 2A: Magic Discovery
- [ ] Phase 2B: Grimoire Persistence
- [ ] Test: Spell-Entdeckung + Reload

**Ziel:** Spell discovery funktioniert, Grimoire bleibt nach Neustart

---

### Sprint 3: State & Permadeath
- [ ] Phase 4A: Save/Load mit Checksums
- [ ] Phase 4B: Graveyard
- [ ] Test: Death → Graveyard Entry → New char mit altem Grimoire

---

### Sprint 4: Consequences & Morality
- [ ] Phase 3A: Consequence Chains
- [ ] Phase 3B: Reputation System
- [ ] Test: Burn tavern → Guards hostile later

---

### Sprint 5: Themes & Polish
- [ ] Phase 5A: Content Structure
- [ ] Phase 5B: Theme Selection
- [ ] Phase 6A: Premium System (optional)

---

## Migration Strategy

### Was bleibt
- ✅ Existierende Models (Player, Room, Monster, Item)
- ✅ Character Creation Flow
- ✅ Combat System (kann später erweitert werden)
- ✅ Terminal UI (blessed-basiert)

### Was sich ändert
- ⚠️ `game/actions.py`: Von Keyword-Matching zu LLM Interpretation
- ⚠️ `services/ai_service.py`: Zwei neue Methoden (interpret, evaluate_magic)
- ⚠️ `main.py`: State Management, Graveyard UI

### Neu hinzu
- `services/prompts.py`
- `services/state_manager.py`
- `services/grimoire_manager.py`
- `models/magic.py`
- `models/consequences.py`
- `models/reputation.py`
- `content/base/*.json`
- `core/license_manager.py`

---

## Nächste Schritte

1. **Jetzt:** Sprint 1 starten - Interpreter Mode implementieren
2. **Provider-Frage klären:** Claude Haiku als Standard, aber Multi-Provider behalten?
3. **Testing:** Jeder Sprint endet mit Manual Test

**Start:** Phase 1A - Interpreter Prompt + `interpret_action()` Methode erstellen
