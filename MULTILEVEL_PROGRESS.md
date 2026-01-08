# Multi-Level Dungeon Implementation - Progress

## Status: ✅ COMPLETED (100%)

## Ziel
Mehrere Ebenen im Dungeon mit Treppen nach oben/unten. Treppen mit Ja/Nein-Prompt beim Betreten.

## ✅ Fertig

### 1. RoomType erweitert (models/game_state.py)
- ✅ `RoomType.STAIRS_DOWN` - Treppe nach unten
- ✅ `RoomType.STAIRS_UP` - Treppe nach oben
- ❌ Entfernt: `RoomType.STAIRS` (veraltet)

### 2. Player.z Koordinate (models/player.py)
- ✅ `player.z: int = 0` hinzugefügt (Ebene 0 = oben)
- ✅ `to_dict()` serialisiert z
- ✅ `from_dict()` deserialisiert z (default=0 für alte Saves)

### 3. Dungeon Multi-Level Struktur (models/dungeon.py)
- ✅ `__init__(size, num_levels=3, theme_config)` - num_levels Parameter
- ✅ `self.levels: List[List[List[Room]]]` statt `self.grid`
- ✅ `generate()` erzeugt alle Ebenen
- ✅ `_place_stairs()` platziert Treppen zwischen Ebenen
  - Treppen immer am Ende (size-1, size-1)
  - STAIRS_DOWN in Ebene N → STAIRS_UP in Ebene N+1
- ✅ `generate_doors(z)` nimmt jetzt Level-Parameter

## ✅ Phase 4: Dungeon-Methoden (COMPLETED)

### 4. Dungeon-Methoden anpassen
Status: ✅ Alle Methoden aktualisiert

**Abgeschlossen:**
- ✅ `get_room(x, y)` → `get_room(x, y, z)` mit z-Parameter
- ✅ `get_exits(x, y)` → `get_exits(x, y, z)`
- ✅ `spawn_monsters()` - iteriert alle Ebenen, Boss auf letzter Ebene STAIRS_DOWN
- ✅ `spawn_npcs()` - iteriert alle Ebenen
- ✅ `spawn_quest_npcs()` - iteriert alle Ebenen
- ✅ `spawn_hazards()` - iteriert alle Ebenen
- ✅ `to_dict()` - serialisiert levels mit num_levels
- ✅ `from_dict()` - deserialisiert levels + Migration für alte Saves

## ✅ Phase 5: Navigation (COMPLETED)

### 5. Navigation zwischen Ebenen (game/exploration.py + main.py)
- ✅ move_player() verwendet z-Koordinate für alle get_room() Calls
- ✅ Bei STAIRS_DOWN/UP: Ja/Nein-Prompt wird angezeigt
- ✅ "Hinabsteigen? Tippe 'j' für Ja, 'n' für Nein."
- ✅ Bei "j": z += 1 (down) oder z -= 1 (up), Raumbeschreibung wird angezeigt
- ✅ Bei "n": Spieler bleibt auf aktueller Ebene
- ✅ Alle get_room() Aufrufe mit z erweitert

## ✅ Phase 6: UI & Andere Dateien (COMPLETED)

### 6. UI: Ebenen-Anzeige
- ✅ Separator zeigt: "─── (x,y) Ebene 1/3 ───"
- ✅ Bei Treppen-Bewegung: "Du steigst hinab zur Ebene 2"

### 7. Andere Dateien anpassen
**Alle get_room() Aufrufe aktualisiert:**
- ✅ game/actions.py - 3 Aufrufe (Zeilen 1355, 1397, 1746)
- ✅ game/combat.py - 1 Aufruf (Zeile 52)
- ✅ main.py - 3 Aufrufe (Zeilen 469, 550, 602, 946)
- ✅ game/exploration.py - 3 Aufrufe (Zeilen 42, 70, 97)
- ✅ debug_action.py - 1 Aufruf (Zeile 40)

### 8. Save/Load System
- ✅ to_dict() serialisiert levels + num_levels
- ✅ from_dict() deserialisiert levels
- ✅ Alte Saves werden automatisch migriert (grid → levels[0])

### 9. Quest-System Boss-Spawning
- ✅ Boss spawnt auf STAIRS_DOWN in tiefster Ebene (num_levels-1)
- ✅ Quest-NPCs spawnen verteilt über alle Ebenen

## Code-Änderungen im Detail

### Dungeon.__init__()
```python
# ALT:
self.grid: List[List[Room]] = []

# NEU:
self.num_levels = num_levels
self.levels: List[List[List[Room]]] = []  # levels[z][y][x]
```

### Dungeon.get_room()
```python
# ALT:
def get_room(self, x: int, y: int) -> Optional[Room]:
    if 0 <= x < self.size and 0 <= y < self.size:
        return self.grid[y][x]
    return None

# NEU (noch zu implementieren):
def get_room(self, x: int, y: int, z: int = 0) -> Optional[Room]:
    if 0 <= z < self.num_levels and 0 <= x < self.size and 0 <= y < self.size:
        return self.levels[z][y][x]
    return None
```

### exploration.move_player()
```python
# NEU hinzufügen (nach Bewegung):
room = game.dungeon.get_room(game.player.x, game.player.y, game.player.z)

if room.type == RoomType.STAIRS_DOWN:
    # Prompt anzeigen
    game.add_log('system', 'Eine Treppe führt hinab in die Tiefe.')
    game.add_log('system', 'Hinabsteigen? (j/n)')
    game.state = GameState.STAIRS_PROMPT  # Neuer State?
    # Oder: Direkt in handle_command prüfen

elif room.type == RoomType.STAIRS_UP:
    game.add_log('system', 'Eine Treppe führt nach oben.')
    game.add_log('system', 'Hinaufsteigen? (j/n)')
```

## ✅ Abgeschlossene Schritte

1. ✅ get_room(x, y, z) anpassen
2. ✅ get_exits(x, y, z) anpassen
3. ✅ spawn_*() Methoden für alle Ebenen
4. ✅ to_dict/from_dict für levels
5. ✅ exploration.py Navigation mit Treppen-Prompt
6. ✅ Alle get_room() Aufrufe im Code aktualisieren
7. ✅ UI: Ebenen-Anzeige
8. ⏳ Testing (noch zu testen im Spiel)

## Implementierungszeit
- Phase 1-3 (Grundstruktur): ~45 min
- Phase 4 (Dungeon-Methoden): ~20 min
- Phase 5 (Navigation): ~25 min
- Phase 6 (UI & Aufrufe): ~20 min
**Total: ~110 min** (ursprünglich geschätzt: 70 min)

## Letzte Aktualisierung
2026-01-07 - ✅ **VOLLSTÄNDIG IMPLEMENTIERT** - Alle Phasen abgeschlossen, bereit zum Testen
