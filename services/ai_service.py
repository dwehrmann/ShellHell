"""AI service for dynamic content generation with multiple provider support."""

import os
import json
from typing import Dict, Tuple, Optional, Any, List

from models.dungeon import Dungeon, Room
from models.game_state import RoomType
from services.ai_providers import get_provider, AIProvider
from services.prompts import INTERPRETER_PROMPT, NARRATOR_PROMPT, MAGIC_EVALUATOR_PROMPT


# System instruction for the Dungeon Master
SYSTEM_INSTRUCTION = """
Du bist der drakonische Dungeon Master (DM). Dein Vorbild sind Nethack und klassische Text-Adventures.

STRENGE REGELN FÜR DIE MECHANIK:
1. GEIZ: Sei extrem zurückhaltend mit Belohnungen. Ein "Untersuchen" eines Items gibt XP oder Informationen, aber fast NIE ein neues Item.
2. KEINE DUPLIKATE: Wenn der Spieler ein Item untersucht, das er bereits hat, gib im JSON-Feld "item" NULL zurück. Das "item"-Feld im JSON ist NUR für den PHYSISCHEN ERHALT eines neuen Objekts.
3. TRANSFORMATION: Falls ein Item ein anderes ersetzt (z.B. Zahnrad wird zu Ring), nutze "replaceItemName".
4. ATTRIBUT-CHECKS: Nutze die Attribute (STR, DEX, WIS, INT) für JEDE riskante Aktion. Je nachdem, welches Attribut für die Aktion zuständig ist.
   - Str: Stärke, Dex: Geschicklichkeit, Wis: Weisheit (Zusammenhänge, Weltordnung), Int: Verständnis und hohe Intelligenzleistungen
   - Erfolg: "Dank deiner hohen [Attribut]..."
   - Fehlschlag: "Deine mangelnde [Attribut] wird dir zum Verhängnis..."
   - Nadeln im Staub: Ein Spieler mit hoher DEX (15+) oder WIS (15+) wird NICHT gestochen.
5. THEMA: Bleibe strikt bei der Atmosphäre des aktuellen Dungeons.

JSON-Schema:
{
  "narration": "Atmosphärische Beschreibung des Ergebnisses inkl. Check-Erwähnung.",
  "success": boolean,
  "impact": {
    "hp": number,
    "gold": number,
    "xp": number,
    "item": null | {
      "name": "String",
      "type": "weapon|armor|ring|head|consumable",
      "stats": { "strength": number, "attack": number, "defense": number, "wisdom": number, "hp": number },
      "isCurse": boolean,
      "description": "Flavor text"
    },
    "replaceItemName": "String (Name des Items im Inventar, das durch das neue 'item' ersetzt oder gelöscht werden soll)"
  }
}
"""


class AIService:
    """Service for AI-generated content."""

    def __init__(self):
        """Initialize the AI service."""
        self.provider: AIProvider = get_provider()
        # Note: Provider info is logged silently. If API unavailable, fallback texts will be used.

    def is_available(self) -> bool:
        """Check if AI service is available."""
        return self.provider.is_available()

    def interpret_action(
        self,
        action_text: str,
        player: Any,
        room: Any,
        theme_context: str = "Generic fantasy dungeon"
    ) -> Dict[str, Any]:
        """
        Interpret natural language action into structured intent.

        This is the FIRST stage of action resolution:
        Player input → LLM Interpreter → Structured JSON

        Args:
            action_text: Raw player input ("I tip the chandelier on the goblin")
            player: Player object with inventory, stats, etc.
            room: Current room with enemies, objects

        Returns:
            Dict with action_type, target, method, plausibility, valid, etc.
        """
        # VERSION MARKER: v2.0 with safe_get and file logging

        # FIRST THING: Write to log to prove we're here
        try:
            with open('/tmp/shellhell_debug.log', 'a') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"interpret_action CALLED - v2.0\n")
                f.write(f"Action: {action_text}\n")
                f.write(f"Player type: {type(player).__name__}\n")
                f.write(f"Player is dict: {isinstance(player, dict)}\n")
        except Exception as log_error:
            pass  # Don't let logging break the game

        if not self.is_available():
            # Fallback: treat as invalid
            return {
                "valid": False,
                "reason_if_invalid": "AI not available",
                "plausibility": 0.0
            }

        try:
            # Build player state for prompt

            # Handle both dict and object access
            def safe_get(obj, key, default=None):
                """Safely get attribute from object or dict."""
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            # Get player attributes safely
            player_name = safe_get(player, 'name', 'Unknown')
            player_race = safe_get(player, 'race', 'Unknown')
            player_level = safe_get(player, 'level', 1)
            player_hp = safe_get(player, 'hp', 20)
            player_max_hp = safe_get(player, 'max_hp', 20)

            # Get inventory and equipment
            inventory = safe_get(player, 'inventory', [])
            inventory_names = [safe_get(item, 'name', 'Unknown') for item in inventory]

            equipment = safe_get(player, 'equipment', {})
            equipment_summary = {}
            for k, v in (equipment.items() if isinstance(equipment, dict) else {}):
                equipment_summary[k] = safe_get(v, 'name', None) if v else None

            # Get attributes
            attributes = safe_get(player, 'attributes', None)
            if attributes:
                attr_str = safe_get(attributes, 'strength', 10)
                attr_dex = safe_get(attributes, 'dexterity', 10)
                attr_wis = safe_get(attributes, 'wisdom', 10)
                attr_int = safe_get(attributes, 'intelligence', 10)
            else:
                attr_str = attr_dex = attr_wis = attr_int = 10

            player_state = f"""Name: {player_name} ({player_race})
Level: {player_level}, HP: {player_hp}/{player_max_hp}
Attributes: STR={attr_str}, DEX={attr_dex}, WIS={attr_wis}, INT={attr_int}
Inventory: {inventory_names}
Equipment: {equipment_summary}"""

            # Build room state
            room_enemies = []
            if room.monster and room.monster.hp > 0:
                room_enemies.append(room.monster.name)

            # Get items on the ground (loot)
            room_loot = []
            if hasattr(room, 'loot') and room.loot:
                room_loot = [item.name for item in room.loot]

            room_state = f"""Type: {room.type.value}
Description: {room.description or 'Unknown room'}
Enemies present: {room_enemies if room_enemies else 'None'}
Items on ground: {room_loot if room_loot else 'None'}
Objects: [Assume generic dungeon furniture unless described]"""

            # Format prompt
            prompt = INTERPRETER_PROMPT.format(
                theme_context=theme_context,
                player_state=player_state,
                room_state=room_state
            )

            # Add player action
            full_prompt = f"{prompt}\n\nPlayer Action: \"{action_text}\"\n\nYour JSON response:"

            # Call LLM with JSON mode
            response = self.provider.generate(full_prompt, temperature=0.1, json_mode=True)

            if not response:
                return {
                    "valid": False,
                    "reason_if_invalid": "LLM returned empty response",
                    "plausibility": 0.0
                }

            # Parse JSON
            intent = json.loads(response)

            # Validate schema
            required_fields = ['action_type', 'valid', 'plausibility']
            for field in required_fields:
                if field not in intent:
                    return {
                        "valid": False,
                        "reason_if_invalid": f"LLM response missing '{field}'",
                        "plausibility": 0.0
                    }

            return intent

        except json.JSONDecodeError as e:
            print(f"AI Interpreter: Invalid JSON - {e}")
            print(f"Response was: {response}")
            return {
                "valid": False,
                "reason_if_invalid": "LLM returned invalid JSON",
                "plausibility": 0.0
            }
        except Exception as e:
            # Log exception to file
            import traceback
            with open('/tmp/shellhell_debug.log', 'a') as f:
                f.write(f"\n!!! EXCEPTION in interpret_action !!!\n")
                f.write(f"Exception type: {type(e).__name__}\n")
                f.write(f"Exception message: {str(e)}\n")
                f.write(f"Traceback:\n")
                traceback.print_exc(file=f)

            return {
                "valid": False,
                "reason_if_invalid": f"{type(e).__name__}: {str(e)}",
                "plausibility": 0.0
            }

    def generate_dungeon_plot(self, theme: str) -> str:
        """
        Generate a plot background for the dungeon theme.

        Args:
            theme: The dungeon theme

        Returns:
            A short (1-2 sentences) plot description
        """
        if not self.is_available():
            return theme

        try:
            prompt = f'''Erstelle basierend auf dem Thema "{theme}" einen kurzen Plot-Hintergrund (max 2 Sätze).

WICHTIG - Passe den Plot an das THEMA an:
- Zwergenhalle → Verlassen, Fluch, verlorene Schätze
- Orkhöhle → Kriegslager, Konflikt, Gefangene
- Verlassene Stadt → Urban Decay, Verfall, Kriminalität, keine Body-Horror!
- Abwasserkanal → Verschmutzung, Mutationen, verborgene Siedlung
- Pyramide → Grabräuber, Fluch der Pharaonen, uralte Magie

VERBOTEN:
❌ Nekromanten, Hungergeister, Feuergeister (zu spezifisch)
❌ Body-Horror (pulsierende Wände, Fleisch, Organe)
❌ Immer die gleiche Formel

STIL: Konkret, bodenständig, passend zum Setting

Beispiele:
✓ Zwergenhalle: "Die Zwerge verschwanden vor 100 Jahren spurlos. Gerüchte sprechen von einem verfluchten Edelstein in der Schatzkammer."
✓ Stadt: "Nach dem Pestjahr wurden die Toten hastig in den Kellern verscharrt. Seither verlassen die Wachen nachts die Untergründe."
✓ Abwasserkanal: "Diebe nutzen die Kanäle als Versteck. Doch neuerdings kehren selbst die Diebe nicht mehr zurück."

Thema: "{theme}"'''

            result = self.provider.generate(prompt, temperature=0.7)
            return result if result else theme

        except Exception as e:
            print(f"AI Error (plot): {e}")
            return theme

    def generate_intro_sequence(self, player_name: str, player_race: str, theme: str, story_context: str, starting_room) -> str:
        """
        Generate an atmospheric intro for the starting room.

        Args:
            player_name: The player's name
            player_race: The player's race
            theme: The dungeon theme
            story_context: The plot background
            starting_room: The Room object at (0,0)

        Returns:
            Intro text (backstory + room description)
        """
        if not self.is_available():
            return f"{player_name} betritt {theme}. Der Eingang liegt hinter dir."

        try:
            # Check if room has assigned object
            obj_info = ""
            if starting_room.assigned_object:
                obj = starting_room.assigned_object
                obj_info = f"\nObjekt im Raum: {obj['name']} ({obj['mystery']})"

            prompt = f'''Du bist ein atmosphärischer Dungeon Master. Schreibe eine Intro-Sequenz für den Spielstart.

Spieler: {player_name} ({player_race})
Thema: {theme}
Hintergrund: {story_context}{obj_info}

Erstelle eine Intro-Sequenz in 2 Teilen (je 2-3 Sätze):

1. BACKSTORY (Wie kam der Charakter hierher? Was sucht er?):
   - Kurz und konkret
   - Persönliche Motivation
   - Bezug zum Plot

2. STARTROOM BESCHREIBUNG (Atmosphärisch, detailliert):
   - Lichtverhältnisse, Gerüche, Geräusche
   - Erste Eindrücke{"- Erwähne das Objekt: " + starting_room.assigned_object['name'] if starting_room.assigned_object else ""}
   - Bedrohliche oder geheimnisvolle Stimmung


Beispiel:

**Backstory:**
Die Nachricht kam in der Nacht: Deine Schwester wurde zuletzt in dieser verfallenen Mühle gesehen. Du bist gekommen, um sie zu finden – oder herauszufinden, was mit ihr geschehen ist.

**Startroom:**
Der Eingang liegt hinter dir, zugewachsen mit Dornenranken. Gedämpftes Licht fällt durch zersplitterte Fenster und wirft lange Schatten auf den staubigen Boden. Ein altes Mühlrad knarzt leise im Wind draußen, während ein metallischer Geruch schwer in der Luft hängt.

Format:
**Backstory:**
[Dein Text]

**Startroom:**
[Dein Text]'''

            result = self.provider.generate(prompt, temperature=0.8)
            return result if result else f"{player_name} betritt {theme}."

        except Exception as e:
            print(f"AI Error (intro): {e}")
            return f"{player_name} betritt {theme}."

    def generate_object_palette(self, theme: str, story_context: str, dungeon_size: int) -> List[Dict[str, Any]]:
        """
        Generate a cohesive object palette for the entire dungeon.

        Args:
            theme: The dungeon theme
            story_context: The plot background
            dungeon_size: Number of rooms in the dungeon

        Returns:
            List of object dicts with: name, object_type, suggested_location, mystery
        """
        if not self.is_available():
            return self._generate_fallback_palette(theme, dungeon_size)

        try:
            num_objects = min(dungeon_size, 12)  # Max 12 unique objects

            prompt = f'''Du erstellst eine OBJECT PALETTE für einen {dungeon_size}-Raum Dungeon.

Thema: "{theme}"
Plot: "{story_context}"

Erstelle {num_objects} UNIQUE Objekte, die thematisch zusammenpassen und die Geschichte des Dungeons erzählen. Du bist frei in der Art und Namen des Objekts, aber folge diesen Regeln:

REGELN:
1. Jedes Objekt ist EINZIGARTIG (kein Duplikat!)
2. Objekte bauen aufeinander auf und gehören zum Dungeon Theme (erzählen zusammen eine Geschichte)
3. Mix aus: Werkzeuge, Möbel, Mechanik, Behälter, Dekoration
4. KONKRET, nicht abstrakt (Mühlstein JA, Schatten NEIN)

Für jedes Objekt:
- name: Erfinde einen konkreten Namen (z.B. "Mühlstein", "Messbecher", "Glocke", "Wandteppich")
- object_type: "anchor" (Hauptobjekt), "mechanism" (beweglich), "container" (Behälter), "decoration" (Deko)
- suggested_location: "entrance", "storage", "workshop", "center", "treasure", "stairs", "random"
- mystery: Kurzer Hinweis was seltsam ist (max 1 kurzer Satz)

Beispiel für "Verlassene Mühle":
[
  {{"name": "Mühlstein", "object_type": "anchor", "suggested_location": "center", "mystery": "lief rückwärts"}},
  {{"name": "Messbecher", "object_type": "container", "suggested_location": "storage", "mystery": "Maßlinie bricht ab"}},
  {{"name": "Filtertuch", "object_type": "decoration", "suggested_location": "workshop", "mystery": "Blutflecken"}},
  {{"name": "Glocke", "object_type": "mechanism", "suggested_location": "entrance", "mystery": "Klöppel fehlt"}},
  {{"name": "Sackwagen", "object_type": "anchor", "suggested_location": "storage", "mystery": "Rad blockiert"}},
  {{"name": "Werkbank", "object_type": "anchor", "suggested_location": "workshop", "mystery": "Kratzer von Ketten"}},
  {{"name": "Sieb", "object_type": "container", "suggested_location": "workshop", "mystery": "Löcher zugenäht"}},
  {{"name": "Siegelwachs", "object_type": "decoration", "suggested_location": "random", "mystery": "Name rausgekratzt"}}
]

Antworte NUR mit dem JSON-Array, kein anderer Text!'''

            result = self.provider.generate(prompt, temperature=0.8)

            if result:
                # Parse JSON
                try:
                    # Clean up potential markdown code blocks
                    if '```' in result:
                        result = result.split('```')[1]
                        if result.startswith('json'):
                            result = result[4:]

                    palette = json.loads(result.strip())

                    # Validate structure
                    if isinstance(palette, list) and len(palette) > 0:
                        return palette

                except json.JSONDecodeError as e:
                    print(f"JSON Parse Error (palette): {e}")
                    print(f"Raw result: {result}")

        except Exception as e:
            print(f"AI Error (object palette): {e}")

        return self._generate_fallback_palette(theme, dungeon_size)

    def _generate_fallback_palette(self, theme: str, dungeon_size: int) -> List[Dict[str, Any]]:
        """Generate a simple fallback palette without AI."""
        num_objects = min(dungeon_size, 8)

        # Generic objects that work for any theme
        generic_objects = [
            {"name": "Werkbank", "object_type": "anchor", "suggested_location": "workshop", "mystery": "Werkzeug fehlt"},
            {"name": "Kiste", "object_type": "container", "suggested_location": "storage", "mystery": "Schloss gebrochen"},
            {"name": "Tisch", "object_type": "anchor", "suggested_location": "center", "mystery": "Kratzer"},
            {"name": "Kerzenhalter", "object_type": "decoration", "suggested_location": "random", "mystery": "Wachs frisch"},
            {"name": "Stuhl", "object_type": "anchor", "suggested_location": "random", "mystery": "Bein fehlt"},
            {"name": "Fass", "object_type": "container", "suggested_location": "storage", "mystery": "Leck"},
            {"name": "Regal", "object_type": "anchor", "suggested_location": "storage", "mystery": "Leer"},
            {"name": "Kette", "object_type": "mechanism", "suggested_location": "random", "mystery": "Rost"}
        ]

        return generic_objects[:num_objects]

    def generate_all_room_descriptions(
        self,
        dungeon: Dungeon,
        theme: str,
        story_context: str
    ) -> Dict[Tuple[int, int], str]:
        """
        Generate descriptions for all rooms in batch.

        Args:
            dungeon: The dungeon object
            theme: The dungeon theme
            story_context: The plot context

        Returns:
            Dictionary mapping (x, y) coordinates to room descriptions
        """
        if not self.is_available():
            return self._generate_fallback_descriptions(dungeon)

        descriptions = {}

        try:
            # Generate descriptions one-by-one for better quality
            # (Batch-JSON was too unreliable)
            for y, row in enumerate(dungeon.grid):
                for x, room in enumerate(row):
                    exits = dungeon.get_exits(x, y)
                    desc = self._generate_single_room_description(
                        room, exits, theme, story_context
                    )
                    descriptions[(x, y)] = desc

        except Exception as e:
            print(f"AI Error (batch descriptions): {e}")
            return self._generate_fallback_descriptions(dungeon)

        # Fill in any missing descriptions
        for y, row in enumerate(dungeon.grid):
            for x, room in enumerate(row):
                if (x, y) not in descriptions:
                    descriptions[(x, y)] = self._generate_fallback_description(room, dungeon.get_exits(x, y))

        return descriptions

    def _generate_single_room_description(
        self,
        room: 'Room',
        exits: list,
        theme: str,
        story_context: str,
        is_return: bool = False,
        quest_manager = None
    ) -> str:
        """Generate a single atmospheric room description."""
        try:
            import random

            # Add atmosphere modifiers for more variation
            atmosphere_modifiers = [
                "verlassen und vergessen",
                "kürzlich besucht",
                "in Verfall begriffen",
                "bedrohlich still",
                "voller unheilvoller Zeichen",
                "merkwürdig gut erhalten",
                "von Feuchtigkeit durchsetzt",
                "mit Spuren eines Kampfes",
                "gespenstisch ordentlich",
                "chaotisch durcheinander",
                "kalt und zugig",
                "erstickend stickig",
                "von schwachem Licht erhellt",
                "in tiefes Dunkel getaucht"
            ]

            focus_areas = [
                "Achte besonders auf die Architektur und Bauweise",
                "Konzentriere dich auf Geräusche und Akustik",
                "Beschreibe vor allem Gerüche und die Luftqualität",
                "Fokussiere auf Lichtquellen und Schatten",
                "Betone den Zustand und das Alter des Raums",
                "Hebe Spuren früherer Bewohner hervor",
                "Beschreibe besonders die Temperatur und Luftfeuchtigkeit"
            ]

            mood = random.choice(atmosphere_modifiers)
            focus = random.choice(focus_areas)

            exit_str = ", ".join(exits)

            # Build quest context if available
            quest_context = ""
            if quest_manager:
                active_quests = quest_manager.get_active_quests()
                if active_quests and not all(q.completed for q in active_quests):
                    quest_context = "\n\nQUEST-KONTEXT (integriere subtil in Beschreibung):"
                    for quest in active_quests:
                        if not quest.completed:
                            incomplete_objs = [obj for obj in quest.objectives if not obj.completed and not obj.hidden]
                            if incomplete_objs:
                                quest_context += f"\n- {quest.title}: {', '.join([obj.description for obj in incomplete_objs])}"

            if is_return:
                # RÜCKKEHR: Zeige nur Delta
                prompt = f'''Du bist ein präziser Dungeon Master. Der Spieler kehrt zu einem Raum zurück.

Globaler Plot: "{story_context}"
Dungeon-Thema: "{theme}"
Ausgänge: {exit_str}{quest_context}'''

                if room.monster:
                    prompt += f'''\nGegner anwesend: {room.monster.name}'''
                if room.npc:
                    prompt += f'''\nNPC anwesend: {room.npc.name} ({room.npc.role})'''

                prompt += '''

Beschreibe NUR was sich VERÄNDERT hat (1 Satz):
- Ist etwas NEU da? (Objekt, Geräusch, Geruch)
- Ist etwas WEG? (verschwunden, verschoben)
- Ist etwas ANDERS? (stärker, schwächer, repariert, kaputt)
- Wenn Gegner/NPC: erwähne ihre Präsenz knapp

Beispiele:
✓ "Der Mühlstein hat sich leicht gedreht, frischer Staub liegt daneben."
✓ "Das Tropfen ist lauter geworden."
✓ "Die Kerbe in der Wand wurde vertieft."
✓ "Ein Wandernder Händler hat hier Lager aufgeschlagen."

Keine Wiederholung der Erst-Beschreibung! Nur das Delta!'''

            else:
                # ERSTES MAL: Volle Beschreibung
                prompt = f'''Du bist ein präziser Dungeon Master. Beschreibe einen KONKRETEN Raum.

🌍 KONTEXT (Halte dich ans Thema!):
Globaler Plot: "{story_context}"
Dungeon-Thema: "{theme}"
Raum-Typ: {room.type.value}
Ausgänge: {exit_str}

🎭 ATMOSPHÄRE FÜR DIESEN RAUM (für Variation):
Dieser Raum wirkt: {mood}
{focus}{quest_context}'''

                if room.monster:
                    prompt += f'''\nGegner anwesend: {room.monster.name}'''
                if room.npc:
                    prompt += f'''\nNPC anwesend: {room.npc.name} ({room.npc.role})'''

                # Add assigned object if available
                if room.assigned_object:
                    obj = room.assigned_object
                    prompt += f'''\n\nWICHTIG - Nutze DIESES Objekt (aus der Palette):
Objekt-Name: {obj['name']}
Objekt-Typ: {obj['object_type']}
Mystery-Hinweis: {obj['mystery']}'''

                    prompt += '''

STIL-ANFORDERUNGEN (KRITISCH):
📏 Länge: 3-4 KURZE Sätze (nicht mehr!)
📝 Satzlänge: Max 20 Wörter pro Satz (keine Schachtelsätze!)
🎨 Atmosphäre: Nutze 2-3 Sinneseindrücke (nicht alle auf einmal!)
🔍 Variation: Jeder Raum muss ANDERS wirken (aber zum Thema passen!)
💡 Konkret: Beschreibe SPEZIFISCHE Details, nicht Allgemeines
🎯 Thementreue: Alle Details müssen zum Dungeon-Thema "{theme}" passen!
🚫 Klarheit: KEINE Metaphern, KEINE "als ob/als würde", KEINE Fragen an Spieler

WICHTIG - VARIATION INNERHALB DES THEMAS:
✓ Nutze die vorgegebene Atmosphäre ("{mood}") als Leitfaden
✓ Jeder Raum ist einzigartig, aber Teil desselben Dungeons
✓ Verschiedene Räume = verschiedene Funktionen/Zustände (nicht verschiedene Welten!)

SENSORISCHE DETAILS - Wähle 2-3 davon (nicht mehr!):
✓ Visuelle Details: Lichtverhältnisse, Schatten, Farben, Materialien, Zustand
✓ Akustik: Geräusche, Echos, Stille, Tropfen, Knarren, Wind
✓ Geruch: Feuchtigkeit, Verwesung, Rauch, Schimmel, Metall, alte Luft
✓ Haptik/Temperatur: Kälte, Wärme, feuchte Luft, Zugluft
✓ Bewegung: Was bewegt sich? Staub, Ratten, Vorhänge, Schatten

WICHTIG - Objekt-Beschreibung:
✓ Das zugewiesene Objekt ist FEST INSTALLIERT und kann NICHT mitgenommen werden
✓ Beschreibe es als festen Bestandteil des Raums (Möbel, Mechanik, fest verbaut)
✓ Der Spieler kann es nur UNTERSUCHEN oder DAMIT INTERAGIEREN

Beschreibe den Raum mit dem zugewiesenen Objekt:
1. Objekt platzieren (wo steht es, wie sieht es aus)
2. Mystery-Hinweis einbauen (was ist seltsam daran)
3. Was macht diesen Raum besonders?

Falls kein Objekt zugewiesen: Nutze generischen Raum-Typ.'''

                else:
                    prompt += '''

STIL-ANFORDERUNGEN (KRITISCH):
📏 Länge: 3-4 KURZE Sätze (nicht mehr!)
📝 Satzlänge: Max 20 Wörter pro Satz (keine Schachtelsätze!)
🎨 Atmosphäre: Nutze 2-3 Sinneseindrücke (nicht alle auf einmal!)
🔍 Variation: Jeder Raum muss ANDERS wirken (aber zum Thema passen!)
💡 Konkret: Beschreibe SPEZIFISCHE Details, nicht Allgemeines
🎯 Thementreue: Alle Details müssen zum Dungeon-Thema "{theme}" passen!
🚫 Klarheit: KEINE Metaphern, KEINE "als ob/als würde", KEINE Fragen an Spieler

WICHTIG - VARIATION INNERHALB DES THEMAS:
✓ Nutze die vorgegebene Atmosphäre ("{mood}") als Leitfaden
✓ Jeder Raum ist einzigartig, aber Teil desselben Dungeons
✓ Verschiedene Räume = verschiedene Funktionen/Zustände (nicht verschiedene Welten!)

SENSORISCHE DETAILS - Wähle 2-3 davon (nicht mehr!):
✓ Visuelle Details: Lichtverhältnisse, Schatten, Farben, Materialien, Zustand
✓ Akustik: Geräusche, Echos, Stille, Tropfen, Knarren, Wind
✓ Geruch: Feuchtigkeit, Verwesung, Rauch, Schimmel, Metall, alte Luft
✓ Haptik/Temperatur: Kälte, Wärme, feuchte Luft, Zugluft
✓ Bewegung: Was bewegt sich? Staub, Ratten, Vorhänge, Schatten

WICHTIG - VARIETÄT IN RAUMTYPEN:
Nutze VERSCHIEDENE Räume pro Dungeon (nicht immer das gleiche!):
- Normale Kellerwände (Ziegel, Stein, Mörtel)
- Abwasserkanal mit Röhrensystem
- Natürlicher Tunnel/Höhle
- Lagerraum
- Werkstatt
- Wohnbereich
- Wachraum
- Kapelle/Schrein
- Archiv
- Küche

VERBOTEN - Wiederholungen:
❌ Nicht in JEDEM Raum: pulsierende Wände, Fleisch, Schleim, verdrehte Gesichter
❌ Nicht IMMER das gleiche Objekt
❌ Nicht IMMER die gleiche Atmosphäre

Beschreibe konkret was man SIEHT/HÖRT/RIECHT - nicht abstrakte Emotionen'''

                prompt += '''

STRUKTUR-VORLAGE (3-4 KURZE Sätze):
1. HAUPTEINDRUCK: Was siehst du zuerst? (1 kurzer Satz, max 15 Wörter)
2. SENSORISCHE DETAILS: 1-2 konkrete Sinneseindrücke (1 Satz, max 20 Wörter)
3. BESONDERHEIT: Was macht DIESEN Raum einzigartig? (1 Satz)
4. [Optional] STIMMUNG/WARNUNG: Atmosphäre oder Hinweis (1 kurzer Satz)

GUTE Beispiele (KURZE Sätze!):
✓ "Die Decke des Gewölbes ist niedrig, die Balken vermodern. Ein beißender Geruch nach Ammoniak steigt aus den Ecken auf. In der Mitte ruht eine massive Truhe aus Eichenholz. Die Luft ist kalt und feucht."

✓ "Verrostete Haken hängen an der Wand dieser alten Küche. Staub und Asche bedecken den Boden und wirbeln bei jedem Schritt auf. Von oben tropft Wasser durch Risse im Gemäuer. Die Stille hier ist drückend."

✓ "Ein Trümmerfeld aus zerbrochenen Säulen und Steinblöcken. Der Geruch von feuchtem Holz und kaltem Stein hängt schwer in der Luft. Rostige Werkzeuge liegen verstreut unter Staub. In den Schatten glitzert etwas schwach."

VERBOTEN - Diese FEHLER vermeiden:
❌ Zu lange Sätze (über 20 Wörter)
❌ Verschachtelung (Nebensätze mit "während", "als", "wobei")
❌ Metaphern ("krumme Finger", "Raum betrauert", "erwacht")
❌ Füllwörter ("als ob", "als würde", "offensichtlich", "deutlich")
❌ Direkte Fragen an Spieler ("aber was lauert noch?")
❌ Zu poetisch/dramatisch (schreibe präzise, nicht romantisch!)

Wenn Gegner/NPC: Integriere in letzten Satz natürlich.
Thema: {theme}'''

            if room.type.value == 'STAIRS':
                prompt += '\n\nBesonderheit: Erwähne die Treppe zum nächsten Level.'

            result = self.provider.generate(prompt, temperature=0.7)
            if result:
                return result

        except Exception as e:
            print(f"AI Error (single room): {e}")

        # Fallback
        return self._generate_fallback_description(room, exits)

    def _generate_fallback_descriptions(self, dungeon: Dungeon) -> Dict[Tuple[int, int], str]:
        """Generate fallback descriptions without AI."""
        descriptions = {}
        for y, row in enumerate(dungeon.grid):
            for x, room in enumerate(row):
                exits = dungeon.get_exits(x, y)
                descriptions[(x, y)] = self._generate_fallback_description(room, exits)
        return descriptions

    def _generate_fallback_description(self, room: Room, exits: list) -> str:
        """Generate a simple fallback description."""
        exit_str = ", ".join(exits)

        # Simple concrete descriptions without AI
        anchors = ["Ein alter Mühlstein", "Eine verrostete Kette", "Ein zerbrochener Messbecher",
                   "Eine tiefe Kerbe in der Wand", "Ein aufgehängtes Filtertuch"]
        processes = ["tropft leise", "knarrt im Wind", "schwingt sanft", "rostet vor sich hin"]

        import random
        anchor = random.choice(anchors)
        process = random.choice(processes)

        desc = f"{anchor} {process}."

        # Add room type context
        if room.type == RoomType.TREASURE:
            desc += " Ein schwaches Glitzern in der Ecke."
        elif room.type == RoomType.STAIRS:
            desc += " Eine Treppe führt in die Tiefe."

        # Add monster/NPC if present
        if room.monster:
            desc += f" {room.monster.name} lauert hier."
        elif room.npc:
            desc += f" {room.npc.name} ist anwesend."

        desc += f" Ausgänge: {exit_str}."
        return desc

    def generate_room_item_for_object(self, assigned_object: Dict, theme: str) -> Optional[Dict]:
        """
        Generate a thematic item for a room with an assigned_object.
        30% chance to generate an item.

        Args:
            assigned_object: The room's assigned object
            theme: The dungeon theme

        Returns:
            Item dict with name, type, and stats, or None
        """
        import random
        if not self.is_available():
            return None

        # 30% chance to have an item
        if random.random() > 0.30:
            return None

        try:
            obj_name = assigned_object['name']
            obj_mystery = assigned_object.get('mystery', '')

            prompt = f'''Du bist ein Item Designer. Erstelle ein thematisch passendes Item für diesen Raum.

Raum-Objekt: {obj_name}
Mystery-Hinweis: {obj_mystery}
Dungeon-Thema: {theme}

Erstelle EIN Item, das thematisch zum Raum-Objekt passt:
- Es sollte VERWANDT sein (z.B. "Axtständer" → "Rostige Axt")
- Es kann beschädigt/alt/verflucht sein (interessanter!)
- Stats sollten das widerspiegeln

Beispiele:
- Axtständer → Rostige Axt: -1 Angriff wegen Alter, +1 Kälteschaden (eisige Klinge)
- Altar → Gesegnetes Amulett: +2 HP, kann einmal sterben verhindern
- Werkbank → Lederne Handschuhe: +1 DEF
- Mühlstein → Steinbrecher-Hammer: +3 Angriff, -1 Geschwindigkeit

Antworte im JSON-Format:
{{
  "name": "Item-Name",
  "type": "weapon/armor/consumable/accessory",
  "stats": {{"attack": 2, "defense": 0}} oder {{"hp": 5}},
  "special": "Beschreibung des besonderen Effekts (optional)"
}}

Nur JSON, kein anderer Text!'''

            result = self.provider.generate(prompt, temperature=0.8)

            if result:
                # Clean up JSON
                if '```' in result:
                    result = result.split('```')[1]
                    if result.startswith('json'):
                        result = result[4:]
                result = result.strip()

                import json
                item_data = json.loads(result)
                return item_data

        except Exception as e:
            print(f"AI Error (room item): {e}")
            return None

        return None

    def resolve_action(
        self,
        action: str,
        player: Any,
        room: Room,
        story_context: str
    ) -> Dict[str, Any]:
        """
        Resolve a free-form player action.

        DEPRECATED: This method is no longer used. Use the two-stage system:
        1. interpret_action() to parse action
        2. ActionResolver.resolve_free_action() for dice rolling
        3. narrate_action_result() for narration

        Args:
            action: The player's action text
            player: The player object
            room: The current room
            story_context: The plot context

        Returns:
            Dictionary with narration and impact
        """
        # This method is deprecated and should not be called
        print("WARNING: resolve_action() is deprecated, use two-stage system instead")
        return {
            'narration': 'Diese Methode ist veraltet.',
            'success': False,
            'impact': {}
        }

    def narrate_action_result(
        self,
        action: str,
        result: Dict[str, Any],
        story_context: str
    ) -> Dict[str, Any]:
        """
        Narrate the result of a free action with structured discoveries.

        The DM (AI) does NOT decide success/failure - that's already determined by dice.
        The DM only interprets and narrates the result atmospherically.

        Args:
            action: The action text
            result: The roll result with success/failure already determined
            story_context: The plot context

        Returns:
            Dict with:
                - narrative: The atmospheric text
                - discovered_gold: Amount of gold found (0 if none)
                - discovered_items: List of item names mentioned
                - discovered_objects: List of new interactable objects
        """
        if not self.is_available():
            return {
                'narrative': '',
                'discovered_gold': 0,
                'discovered_items': [],
                'discovered_objects': []
            }

        try:
            import json
            from services.prompts import NARRATOR_PROMPT

            success_str = "SUCCESS" if result['success'] else "FAILURE"
            attr = result['attribute'].upper()

            # Build monster state string
            ctx = result['context']
            if ctx.get('has_monster'):
                monster_name = ctx.get('monster_name', 'Unknown')
                monster_hp = ctx.get('monster_hp', 0)
                monster_alive = ctx.get('monster_alive', False)
                status = "ALIVE" if monster_alive else "DEAD"
                monster_state = f"{monster_name} (HP: {monster_hp}, {status})"
            else:
                monster_state = "No monster present"

            # Build mechanical effect description
            impact = result['impact']
            effects = []
            if impact['hp'] != 0:
                effects.append(f"HP: {impact['hp']:+d}")
            if impact['gold'] > 0:
                effects.append(f"Gold: +{impact['gold']}")
            if impact['xp'] > 0:
                effects.append(f"XP: +{impact['xp']}")
            if impact.get('item'):
                effects.append(f"Item found: {impact['item'].name}")

            # Include treasure findings if present in result
            if result.get('treasure_found'):
                treasure_data = result['treasure_found']
                if treasure_data.get('gold'):
                    effects.append(f"Treasure Gold: +{treasure_data['gold']}")
                if treasure_data.get('items'):
                    items_str = ", ".join([item.name for item in treasure_data['items']])
                    effects.append(f"Treasure Items: {items_str}")

            mechanical_effect = ", ".join(effects) if effects else "No mechanical effect"

            # Map attribute to description
            attr_descriptions = {
                'strength': 'STRENGTH (force, power, muscles)',
                'dexterity': 'DEXTERITY (agility, reflexes, quickness)',
                'wisdom': 'WISDOM (perception, awareness, senses)',
                'intelligence': 'INTELLIGENCE (reasoning, knowledge, cleverness)'
            }
            attr_desc = attr_descriptions.get(result['attribute'], result['attribute'].upper())

            # Check fail count for repeated failures
            fail_count = result.get('fail_count', 0)
            failure_context = ""
            if fail_count > 1:
                failure_context = f"\n\nWICHTIG: Dies ist Fehlversuch #{fail_count} der GLEICHEN Aktion! Bei Versuch #3 zerbricht/zerfällt das Objekt endgültig. Beschreibe die Verschlechterung dramatisch."

            # Get inventory and equipment info
            player_inventory_str = ", ".join(ctx.get('player_inventory', [])) if ctx.get('player_inventory') else "empty"
            player_equipped_str = ", ".join([f"{slot}: {name}" for slot, name in ctx.get('player_equipped', {}).items()]) if ctx.get('player_equipped') else "nothing equipped"
            target_location = ctx.get('target_location', 'environment')

            # Get fixed objects context
            fixed_objects_str = ", ".join(result.get('fixed_objects', [])) if result.get('fixed_objects') else "None"

            prompt = NARRATOR_PROMPT.format(
                current_theme=story_context,
                current_room=ctx['room_description'],
                monster_state=monster_state,
                player_inventory=player_inventory_str,
                player_equipped=player_equipped_str,
                target_location=target_location,
                fixed_objects=fixed_objects_str,
                action_description=action,
                attribute_used=attr_desc,
                result=f"{success_str} - Roll: {result['roll']}, Total: {result['total']}, DC: {result['difficulty']}",
                mechanical_effect=mechanical_effect
            ) + failure_context

            result_text = self.provider.generate(prompt, temperature=0.8)

            if not result_text:
                return {
                    'narrative': '',
                    'discovered_gold': 0,
                    'discovered_items': [],
                    'discovered_objects': []
                }

            # CRITICAL: Enforce JSON format
            # If AI didn't return JSON, retry with strict prompt
            result_text = result_text.strip()

            # Quick check: Does it look like JSON?
            looks_like_json = result_text.startswith('{') or result_text.startswith('```json')

            retry_count = 0
            max_retries = 2

            while not looks_like_json and retry_count < max_retries:
                retry_count += 1
                print(f"⚠️ AI returned non-JSON, retrying ({retry_count}/{max_retries})...")

                # AI ignored our JSON request! Retry with VERY strict prompt
                retry_prompt = f"""⚠️ CRITICAL ERROR: You MUST return ONLY valid JSON! ⚠️

Previous output was INVALID (plain text instead of JSON) - attempt {retry_count}/{max_retries}

Your task: Describe action outcome in German.
Action result: {result['success']}
Context: {ctx['room_description'][:100]}

YOU MUST RETURN EXACTLY THIS FORMAT:
{{
  "narrative": "Deine deutsche Beschreibung hier (2-3 Sätze)",
  "discovered_gold": 0,
  "discovered_items": [],
  "discovered_objects": []
}}

RULES:
1. Output MUST start with {{ character
2. Output MUST end with }} character
3. NO text before the JSON
4. NO text after the JSON
5. Valid JSON only!

Example of CORRECT output:
{{"narrative": "Du öffnest die Tür vorsichtig.", "discovered_gold": 0, "discovered_items": [], "discovered_objects": []}}

NOW RETURN VALID JSON:"""

                # Use lower temperature for more deterministic output
                result_text = self.provider.generate(retry_prompt, temperature=0.2)
                result_text = result_text.strip()
                looks_like_json = result_text.startswith('{') or result_text.startswith('```json')

            if retry_count > 0:
                if looks_like_json:
                    print(f"✅ Retry successful! AI returned JSON after {retry_count} attempt(s)")
                else:
                    print(f"❌ All retries failed. Falling back to regex parser...")

            # Try to parse as JSON
            try:
                # Clean up response (sometimes AI adds markdown)
                result_text = result_text.strip()
                if result_text.startswith('```json'):
                    result_text = result_text[7:]
                if result_text.startswith('```'):
                    result_text = result_text[3:]
                if result_text.endswith('```'):
                    result_text = result_text[:-3]
                result_text = result_text.strip()

                parsed = json.loads(result_text)

                # Validate structure
                return {
                    'narrative': parsed.get('narrative', ''),
                    'discovered_gold': int(parsed.get('discovered_gold', 0)),
                    'discovered_items': parsed.get('discovered_items', []),
                    'discovered_objects': parsed.get('discovered_objects', [])
                }
            except json.JSONDecodeError:
                # Fallback: Parse plain text for mentions of gold/coins/items
                discovered_gold = 0
                discovered_items = []
                discovered_objects = []

                # Parse for gold/coins mentions
                import re
                text_lower = result_text.lower()

                # Check for coin/gold/money mentions
                coin_patterns = [
                    r'(\d+)\s*(gold)?münzen?',
                    r'münzen?.*(\d+)',
                    r'(\d+)\s*gold',
                    r'gold.*(\d+)',
                    r'verkrustete[rns]?\s+münzen',
                    r'alte[rns]?\s+münzen',
                    r'goldstücke',
                    r'silbermünzen',
                    r'kupfermünzen',
                    r'münzen',
                    r'geldbeutel',
                    r'geldsack',
                    r'beutel.*gold',
                    r'schwere[rns]?\s+beutel',  # "schwerer Beutel" suggests gold
                    r'kleiner.*beutel',  # "kleiner Beutel" with context
                    r'beutel.*münz'
                ]

                has_money = False
                for pattern in coin_patterns:
                    match = re.search(pattern, text_lower)
                    if match:
                        has_money = True
                        # Try to extract amount
                        if match.groups():
                            try:
                                amount = int(match.group(1))
                                if amount > 0 and amount < 1000:  # Sanity check
                                    discovered_gold = amount
                            except (ValueError, IndexError):
                                pass
                        break

                # If money mentioned but no specific amount, estimate gold value
                if has_money:
                    if discovered_gold == 0:
                        # Estimate gold amount based on description
                        import random
                        if 'haufen' in text_lower or 'viele' in text_lower or 'stapel' in text_lower:
                            discovered_gold = random.randint(15, 30)
                        elif 'schwer' in text_lower or 'geldbeutel' in text_lower or 'geldsack' in text_lower:
                            # Heavy pouch/bag suggests good amount
                            discovered_gold = random.randint(20, 40)
                        elif 'einige' in text_lower or 'paar' in text_lower:
                            discovered_gold = random.randint(5, 15)
                        elif 'klein' in text_lower or 'wenig' in text_lower:
                            # Small amount
                            discovered_gold = random.randint(3, 10)
                        else:
                            discovered_gold = random.randint(8, 20)
                    # Don't add coins as items - they're currency!

                # Check for other common lootable items
                item_patterns = [
                    (r'(alte|zerrissene|verblichene)\s+(karte|landkarte)', 'Alte Karte'),
                    (r'(rostiger|alter|verrosteter)\s+schlüssel', 'Rostiger Schlüssel'),
                    (r'(zerbrochene|alte)\s+(flasche|phiole)', 'Zerbrochene Flasche'),
                    (r'(altes|verstaubtes)\s+(buch|tagebuch)', 'Altes Buch'),
                    (r'(gold|silber|bronze)ring', 'Ring'),
                    (r'(alte|blutige)\s+waffe', 'Alte Waffe'),
                    (r'edelstein', 'Edelstein'),
                    (r'juwel', 'Juwel'),
                    (r'(altes|zerrissenes)\s+pergament', 'Altes Pergament')
                ]

                for pattern, item_name in item_patterns:
                    if re.search(pattern, text_lower):
                        if item_name not in discovered_items:
                            discovered_items.append(item_name)

                # Return plain text with parsed discoveries
                return {
                    'narrative': result_text,
                    'discovered_gold': discovered_gold,
                    'discovered_items': discovered_items,
                    'discovered_objects': discovered_objects
                }

        except Exception as e:
            print(f"AI Error (narrate action): {e}")
            return {
                'narrative': '',
                'discovered_gold': 0,
                'discovered_items': [],
                'discovered_objects': []
            }

    def generate_treasure(
        self,
        theme: str,
        room_description: str,
        tier: str = "common"
    ) -> dict:
        """
        Generate a thematic treasure item using AI.

        Args:
            theme: The dungeon theme
            room_description: Current room description
            tier: Treasure tier (minor, common, rare, epic)

        Returns:
            Dict with item_name, item_description, item_type, stats
        """
        if not self.is_available():
            return None

        try:
            import json
            from services.prompts import TREASURE_GENERATOR_PROMPT
            from constants import TREASURE_GENERATION_RULES

            rules = TREASURE_GENERATION_RULES
            tier_rules = rules['tiers'][tier]

            prompt = TREASURE_GENERATOR_PROMPT.format(
                theme=theme,
                room_description=room_description[:200],  # Truncate for brevity
                tier=tier,
                tier_rules=f"Gold: {tier_rules['gold_range']}, Stats: {tier_rules['stat_bonus_range']}",
                stat_bonus_range=tier_rules['stat_bonus_range'],
                weapon_light=", ".join(rules['weapon_types']['light']),
                weapon_medium=", ".join(rules['weapon_types']['medium']),
                weapon_heavy=", ".join(rules['weapon_types']['heavy']),
                armor_light=", ".join(rules['armor_types']['light']),
                armor_medium=", ".join(rules['armor_types']['medium']),
                armor_heavy=", ".join(rules['armor_types']['heavy']),
                accessory_types=", ".join(rules['accessory_types'])
            )

            response = self.provider.generate(prompt, temperature=0.9, json_mode=True)
            treasure_data = json.loads(response)

            return treasure_data

        except Exception as e:
            print(f"AI Error (generate treasure): {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_crafted_item(
        self,
        action: str,
        materials_mentioned: List[str],
        room_description: str,
        theme: str
    ) -> Optional['Item']:
        """
        Generate a crafted item based on player's crafting action.

        Args:
            action: The crafting action (e.g., "arbeite eine rüstung aus den tierhäuten")
            materials_mentioned: Materials found in the action/room
            room_description: Current room description
            theme: Dungeon theme

        Returns:
            Item object or None if generation fails
        """
        if not self.is_available():
            return None

        try:
            import json
            from models.items import Item, ItemType, ItemStats

            materials_str = ", ".join(materials_mentioned) if materials_mentioned else "unbekannte Materialien"

            prompt = f'''Du generierst ein GECRAFTETES Item basierend auf einer Spieler-Aktion.

Spieler-Aktion: "{action}"
Materialien: {materials_str}
Raum: {room_description[:150]}
Thema: {theme}

Erstelle ein Item, das der Spieler aus den Materialien herstellt:
- Name muss zu Materialien + Aktion passen
- Beschreibung: 1 Satz, erwähne Materialien
- Typ: weapon, armor, ring, consumable
- CURSED Items (10% Chance): Verfluchte Items mit Nachteilen!
  * is_curse: true markiert verfluchte Items
  * Negative Stats: attack/defense können -5 bis +5 sein
  * Curse effects: curse_damage_per_turn (1-3), fire_weakness (-0.2 bis -0.5)
  * Mixed curses: z.B. -3 ATK aber +30% Lifesteal (Balance!)
- Normal Items: Stats & Effekte wie gewohnt
  * Gute Waffe: attack 3-5
  * Schwache/verrottete Waffe: attack 0-2, dafür vielleicht special_effects
  * Gute Rüstung: defense 3-5
  * Alte/beschädigte Rüstung: defense 0-2, dafür vielleicht special_effects
  * Special Effects (optional): fire_resistance, cold_resistance, poison_resistance (0.0-0.5), poison_damage (1-5), lifesteal (0.1-0.3)
  * Ring: 1-2 stat points verteilt ODER special_effects
  * Consumable: hp 5-15

OUTPUT SCHEMA (JSON only):
{{
  "item_name": "<Name des Items>",
  "item_description": "<1 Satz Beschreibung>",
  "item_type": "<weapon|armor|ring|consumable>",
  "is_curse": <false or true, 10% chance for true>,
  "stats": {{
    "attack": <-5 to +5, can be negative for cursed items>,
    "defense": <-5 to +5, can be negative for cursed items>,
    "strength": <-2 to +2>,
    "dexterity": <-2 to +2>,
    "wisdom": <-2 to +2>,
    "intelligence": <-2 to +2>,
    "hp": <-10 to +15>
  }},
  "special_effects": {{
    "fire_resistance": <0.0-0.5 optional>,
    "cold_resistance": <0.0-0.5 optional>,
    "poison_resistance": <0.0-0.5 optional>,
    "fire_weakness": <-0.5 to -0.2 optional for curses>,
    "cold_weakness": <-0.5 to -0.2 optional for curses>,
    "poison_damage": <1-5 optional>,
    "lifesteal": <0.1-0.3 optional>,
    "curse_damage_per_turn": <1-3 optional for curses>
  }}
}}

Beispiele:
Action: "arbeite eine rüstung aus den tierhäuten und metallsplittern"
Materials: Tierhäute, Metallsplitter
Output: {{"item_name": "Schuppenlederweste", "item_description": "Eine rohe Rüstung aus gehärteten Tierhäuten, verstärkt mit glänzenden Metallschuppen.", "item_type": "armor", "stats": {{"defense": 3, "dexterity": 1}}, "special_effects": {{}}}}

Action: "schmiede einen dolch aus dem eisenerz"
Materials: Eisenerz
Output: {{"item_name": "Grober Eisendolch", "item_description": "Eine simple, aber scharfe Klinge, grob aus Eisenerz geschmiedet.", "item_type": "weapon", "stats": {{"attack": 3}}, "special_effects": {{}}}}

Action: "nimm den verrotteten ledermantel"
Materials: Ledermantel (verrottet)
Output: {{"item_name": "Verrottetes Lederwams", "item_description": "Ein zerfallender Mantel aus brüchigem Leder, kaum noch Schutz bietend.", "item_type": "armor", "is_curse": false, "stats": {{"defense": 0}}, "special_effects": {{"cold_resistance": 0.2}}}}

Action: "nimm den blutbefleckten ring"
Materials: Ring (blutig, düster)
Output: {{"item_name": "Blutring der Gier", "item_description": "Ein silberner Ring mit eingetrockneten Blutflecken, er flüstert dunkle Versprechen.", "item_type": "ring", "is_curse": true, "stats": {{"strength": -2}}, "special_effects": {{"lifesteal": 0.25, "curse_damage_per_turn": 2}}}}

Action: "hebe das verrostete schwert auf"
Materials: Schwert (verrostet, alt)
Output: {{"item_name": "Verfluchte Klinge", "item_description": "Ein rostiges Schwert, dessen Griff eisig kalt ist und Unglück verspricht.", "item_type": "weapon", "is_curse": true, "stats": {{"attack": -3}}, "special_effects": {{"cold_weakness": -0.3}}}}

Antworte NUR mit JSON!'''

            response = self.provider.generate(prompt, temperature=0.8, json_mode=True)
            if not response:
                return None

            item_data = json.loads(response)

            # Create Item object
            item_id = item_data['item_name'].lower().replace(' ', '_').replace('-', '_')

            stats_data = item_data.get('stats', {})
            item_stats = ItemStats(
                attack=stats_data.get('attack', 0),
                defense=stats_data.get('defense', 0),
                strength=stats_data.get('strength', 0),
                dexterity=stats_data.get('dexterity', 0),
                wisdom=stats_data.get('wisdom', 0),
                intelligence=stats_data.get('intelligence', 0),
                hp=stats_data.get('hp', 0)
            )

            item_type_str = item_data.get('item_type', 'material')
            try:
                item_type = ItemType(item_type_str)
            except ValueError:
                item_type = ItemType.MATERIAL

            # Parse special_effects and curse status from AI response
            special_effects = item_data.get('special_effects', {})
            is_curse = item_data.get('is_curse', False)

            crafted_item = Item(
                id=f"crafted_{item_id}",
                name=item_data['item_name'],
                description=item_data['item_description'],
                type=item_type,
                stats=item_stats,
                special_effects=special_effects,
                is_curse=is_curse
            )

            return crafted_item

        except Exception as e:
            print(f"AI Error (generate crafted item): {e}")
            import traceback
            traceback.print_exc()
            return None

    def evaluate_magic(
        self,
        components: List[str],
        gesture: str,
        words: str,
        environment: str
    ) -> dict:
        """
        Evaluate an experimental magic attempt.

        Args:
            components: List of item names used as components
            gesture: Description of the gesture
            words: Words/incantation spoken
            environment: Room type/description

        Returns:
            Dict with is_valid_attempt, plausibility, effect_type, magnitude,
            is_discovery, spell_name, consequence, reasoning
        """
        if not self.is_available():
            return None

        try:
            import json
            from services.prompts import MAGIC_EVALUATOR_PROMPT

            prompt = MAGIC_EVALUATOR_PROMPT.format(
                components=", ".join(components) if components else "None",
                gesture_description=gesture,
                spoken_words=words,
                location_type=environment
            )

            response = self.provider.generate(prompt, temperature=0.7, json_mode=True)
            magic_data = json.loads(response)

            return magic_data

        except Exception as e:
            print(f"AI Error (evaluate magic): {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_npc_dialogue(
        self,
        player_message: str,
        npc,
        world_state,
        story_context: str,
        player_hp: int = None,
        player_max_hp: int = None,
        player_quirk: Optional[Dict] = None,
        player_morality: int = 0,
        relationship: int = 0,
        quest_manager = None,
        player_equipment = None
    ) -> Dict[str, Any]:
        """
        Generate NPC response based on personality, knowledge, and history.

        Args:
            player_message: What the player said
            npc: The NPC object with personality, knowledge, interactions
            world_state: WorldState with event history
            story_context: Current dungeon theme/story
            player_hp: Current player HP (for healing decisions)
            player_max_hp: Max player HP

        Returns:
            Dict with 'response' (text) and 'actions' (list of action dicts)
        """
        if not self.is_available():
            return {
                'response': f"{npc.name} nickt stumm.",
                'actions': [],
                'attitude_change': 0,
                'reveals_information': False,
                'information_revealed': None,
                'offers_quest': False,
                'will_attack': False
            }

        try:
            # Build context from NPC memory
            conversation_history = ""
            recent = npc.get_recent_interactions(limit=3)
            if recent:
                conversation_history = "\n".join([
                    f"Player: {i.player_action}\n{npc.name}: {i.npc_response}"
                    for i in recent
                ])

            # Build world event context
            world_context = world_state.get_echo_context(npc.location)

            # Player status for context
            player_status = ""
            if player_hp is not None and player_max_hp is not None:
                hp_percent = int((player_hp / player_max_hp) * 100)
                player_status = f"\nSPIELER STATUS: {player_hp}/{player_max_hp} HP ({hp_percent}%)"

            # Check for cursed items
            cursed_items = []
            if player_equipment:
                for slot, item in player_equipment.items():
                    if item and item.is_curse:
                        cursed_items.append(item.name)

            if cursed_items:
                player_status += f"\n⚠️ VERFLUCHT: Der Spieler trägt verfluchte Items: {', '.join(cursed_items)}"
                player_status += "\n(Als Priester/Einsiedler/Hexe kannst du Flüche brechen!)"

            # Player quirk for context
            quirk_context = ""
            if player_quirk:
                tags = ", ".join(player_quirk.get('narrative_tags', []))
                quirk_context = f"\nSPIELER QUIRK: {player_quirk['name']} - Du bemerkst: {tags}"
                quirk_context += "\n(Reagiere subtil darauf in deiner Antwort - Misstrauen, Mitleid, Abscheu, etc.)"

            # Calculate current attitude
            attitude = npc.get_attitude(player_morality, relationship)

            # Morality context
            morality_tier = "neutral"
            if player_morality >= 50:
                morality_tier = "good"
            elif player_morality <= -50:
                morality_tier = "evil"

            morality_context = f"\nSPIELER REPUTATION: {morality_tier} (Morality: {player_morality})"
            morality_context += f"\nDEINE AKTUELLE EINSTELLUNG: {attitude}"
            if relationship != 0:
                morality_context += f" (Beziehung: {relationship})"

            # Build quest context
            quest_context = ""
            if quest_manager:
                # Check if this NPC is quest-related
                if npc.quest_id and npc.quest_objective_id:
                    quest = quest_manager.get_quest(npc.quest_id)
                    if quest and not quest.completed:
                        quest_context = f"\n\nQUEST-ROLLE: Du bist Teil der Quest '{quest.title}'. "
                        quest_context += "Der Spieler muss mit dir interagieren, um ein Quest-Ziel zu erfüllen. "
                        quest_context += "Reagiere entsprechend deiner Rolle (Geisel: ängstlich aber dankbar, etc.)"

                # Add general quest hints for other NPCs
                else:
                    active_quests = quest_manager.get_active_quests()
                    if active_quests and not all(q.completed for q in active_quests):
                        quest_context = "\n\nAKTIVE QUESTS (du kannst Hinweise geben):"
                        for quest in active_quests:
                            if not quest.completed:
                                incomplete_objs = [obj for obj in quest.objectives if not obj.completed and not obj.hidden]
                                if incomplete_objs:
                                    quest_context += f"\n- {quest.title}: {', '.join([obj.description for obj in incomplete_objs])}"

            # Build prompt
            prompt = f"""Du bist {npc.name}, ein {npc.role} mit {npc.personality}er Persönlichkeit.

DUNGEON-KONTEXT:
{story_context}

WELTGESCHICHTE (was bisher geschah):
{world_context if world_context else 'Noch keine bedeutenden Ereignisse.'}

DEIN WISSEN:
{chr(10).join(['- ' + k for k in npc.knowledge])}

BISHERIGE GESPRÄCHE:
{conversation_history if conversation_history else 'Erstes Gespräch.'}{player_status}{quirk_context}{morality_context}{quest_context}

SPIELER SAGT: "{player_message}"

Du kannst SPRECHEN und HANDELN. Antworte mit JSON:

OUTPUT SCHEMA:
{{
  "response": "<deine gesprochene Antwort, 1-3 Sätze>",
  "actions": [
    {{"type": "<action_type>", "value": <number or string>}}
  ],
  "attitude_change": <-1, 0, or +1>,
  "reveals_information": <boolean>,
  "information_revealed": "<topic key if true, else null>",
  "offers_quest": <boolean>,
  "will_attack": <boolean>
}}

VERFÜGBARE AKTIONEN:
1. heal - Heile den Spieler (nur wenn du Priester/Heiler bist und Spieler verletzt ist)
   {{"type": "heal", "value": 20}}

2. give_item - Gib dem Spieler ein Item (wenn du Händler bist oder ein Geschenk machst)
   {{"type": "give_item", "value": "Item-Beschreibung"}}

3. call_guards - Rufe Wachen (wenn Spieler dich bedroht/bestohlen hat)
   {{"type": "call_guards", "value": 1}}

4. unlock_door - Öffne eine Tür (wenn du einen Schlüssel hast)
   {{"type": "unlock_door", "value": "direction"}}

5. reveal_secret - Enthülle ein Geheimnis (wenn Spieler richtige Frage stellt)
   {{"type": "reveal_secret", "value": "Beschreibung des Geheimnisses"}}

6. uncurse - Entferne einen Fluch von equipped Items (nur Priester/Einsiedler/Hexe)
   {{"type": "uncurse", "value": "cost:50"}}
   - NUR wenn Spieler VERFLUCHT ist (siehe STATUS)
   - Cost: 50-200 Gold (abhängig von deiner Gier/Güte)
   - Priester: günstiger (50-100), Einsiedler: medium (75-150), Hexe: teurer (100-200)
   - Wenn Spieler arm ist, kannst du auch kostenlos helfen (nur bei guter Einstellung)

REGELN:
- PRIEST/HOLY Rolle: Kann heilen, aber nur wenn Spieler verletzt (<80% HP) und nett fragt
- MERCHANT Rolle: Kann Items geben (gegen Gold, oder als Geschenk wenn sehr freundlich)
- GUARD Rolle: Ruft Verstärkung bei Bedrohung
- Sei konsistent mit deiner Persönlichkeit ({npc.personality})
- "actions" kann leer sein [] wenn du nur reden willst
- Maximal 1-2 Aktionen pro Antwort

ATTITUDE & REAKTION:
- attitude_change: Wie beeinflusst diese Interaktion deine Einstellung? (-1 = schlechter, 0 = gleich, +1 = besser)
- Wenn Spieler dich bedroht, beleidigt, oder böse handelt: attitude_change = -1
- Wenn Spieler hilfsbereit, höflich, oder gut handelt: attitude_change = +1
- Bei neutraler Konversation: attitude_change = 0

INFORMATION & QUESTS:
- reveals_information: true wenn du ein Geheimnis/Hint aus deinem WISSEN teilst
- information_revealed: Der Topic-Key aus deinem Wissen (z.B. "laboratory_location", "secret_passage")
- offers_quest: true wenn du dem Spieler eine Aufgabe gibst (nur wenn passend zur Situation)

ANGRIFF:
- will_attack: true wenn du jetzt angreifen willst (nur bei extremer Provokation oder wenn du hostile bist)
- Normalerweise false - NPCs greifen nicht leichtfertig an!

Beispiel (Priester heilt):
Player HP: 15/40 (37%), fragt nach Heilung
{{"response": "Die göttliche Flamme sei mit dir, mein Kind. Lass mich deine Wunden lindern.", "actions": [{{"type": "heal", "value": 25}}]}}

Beispiel (Händler gibt Item):
Player hat Gold und fragt höflich
{{"response": "Ah, ein weiser Kunde! Nimm diese Tinktur, sie wird dir auf deiner Reise helfen.", "actions": [{{"type": "give_item", "value": "Heiltrank (HP +15)"}}]}}

Beispiel (nur Gespräch):
{{"response": "Die Schatten flüstern von verborgenen Schätzen in den Ostkammern.", "actions": []}}

Deine Antwort (NUR JSON):"""

            response_json = self.provider.generate(prompt, json_mode=True)
            if not response_json:
                return {
                    'response': f"{npc.name} schweigt nachdenklich.",
                    'actions': [],
                    'attitude_change': 0,
                    'reveals_information': False,
                    'information_revealed': None,
                    'offers_quest': False,
                    'will_attack': False
                }

            data = json.loads(response_json)
            return {
                'response': data.get('response', f"{npc.name} nickt."),
                'actions': data.get('actions', []),
                'attitude_change': data.get('attitude_change', 0),
                'reveals_information': data.get('reveals_information', False),
                'information_revealed': data.get('information_revealed'),
                'offers_quest': data.get('offers_quest', False),
                'will_attack': data.get('will_attack', False)
            }

        except Exception as e:
            print(f"AI Error (NPC dialogue): {e}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"{npc.name} murmelt etwas Unverständliches.",
                'actions': [],
                'attitude_change': 0,
                'reveals_information': False,
                'information_revealed': None,
                'offers_quest': False,
                'will_attack': False
            }

    def describe_generic(self, prompt: str) -> str:
        """
        Generate a generic description.

        Args:
            prompt: The prompt for description

        Returns:
            Generated text
        """
        if not self.is_available():
            return ""

        try:
            result = self.provider.generate(prompt)
            return result if result else ""
        except Exception as e:
            print(f"AI Error (generic): {e}")
            return ""


# Global instance
_ai_service = None


def get_ai_service() -> AIService:
    """Get the global AI service instance."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
