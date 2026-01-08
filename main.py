"""Main game loop for Dungeon Crawler."""

import sys
import os
import threading
import time
from pathlib import Path
from blessed import Terminal
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from models.game_state import GameState, CreationStep, RoomType
from models.player import Player
from models.dungeon import Dungeon
from constants import DUNGEON_SIZE
from services.save_manager import SaveManager
from services.graveyard import Graveyard, GraveyardEntry
from models.grimoire import Grimoire


class Game:
    """Main game controller."""

    def __init__(self):
        """Initialize the game."""
        self.term = Terminal()
        self.state = GameState.START
        self.creation_step = CreationStep.ROLLING
        self.player = Player()
        self.dungeon = Dungeon(DUNGEON_SIZE)
        self.logs = []
        self.running = True
        self.loading = False
        self.loading_message = ""
        self.spinner_thread = None  # Thread for animated spinner
        self.last_command = ""  # Track last command for display

        # Story context
        self.theme = ""
        self.theme_config = None  # ThemeConfig object for loot/monsters/npcs
        self.story_context = ""
        self.object_palette = []  # Object palette for room descriptions

        # Temporary state for character creation
        self.temp_attributes = None

        # Save system
        self.save_manager = SaveManager()

        # Graveyard system
        self.graveyard = Graveyard()
        self.preserved_grimoire: Grimoire = None  # Grimoire from previous run

        # World state / Echo System
        from models.world_events import WorldState
        self.world_state = WorldState()

        # Track repeated failed actions
        self.last_failed_action = ""
        self.fail_count = 0

        # Stairs navigation
        self.pending_stairs_action = None  # 'up' or 'down' when player is on stairs

        # Save/Load
        self.pending_save = False  # True when waiting for save slot selection
        self.pending_menu_return = False  # True when waiting for save confirmation before menu return

        # Conversation tracking
        self.conversation_npc = None  # Current NPC in conversation mode

        # Autocomplete with prompt_toolkit
        from ui.autocomplete import GameCompleter
        self.prompt_session = PromptSession(
            history=InMemoryHistory(),
            auto_suggest=AutoSuggestFromHistory(),
            completer=GameCompleter(self),
            complete_while_typing=True
        )

    def add_log(self, log_type: str, text: str, detail_level: str = 'normal') -> None:
        """
        Add a log entry.

        Args:
            log_type: Type of log (system, narrative, error, action)
            text: Log message
            detail_level: 'normal' (important info) or 'verbose' (technical details like dice rolls)
        """
        self.logs.append({
            'type': log_type,
            'text': text,
            'timestamp': None,
            'detail_level': detail_level
        })

    def _spinner_worker(self) -> None:
        """Background worker that updates the spinner animation."""
        spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        frame_idx = 0

        # Save cursor position and render initial screen
        print(self.term.hide_cursor, end='', flush=True)

        while self.loading:
            # Only update the spinner line, not the whole screen
            spinner = spinner_frames[frame_idx % len(spinner_frames)]
            # Move to bottom of screen and update spinner line
            with self.term.location(0, self.term.height - 3):
                print(self.term.clear_eol + self.term.cyan(f"{spinner} {self.loading_message}"), end='', flush=True)

            frame_idx += 1
            time.sleep(0.1)  # Update 10 times per second

        # Clear spinner line when done
        with self.term.location(0, self.term.height - 3):
            print(self.term.clear_eol, end='', flush=True)
        print(self.term.normal_cursor, end='', flush=True)

    def start_loading(self, message: str) -> None:
        """Start loading indicator with animated spinner."""
        self.loading = True
        self.loading_message = message
        # Render once to show the screen with logs
        self.render()
        # Start background thread to animate spinner
        self.spinner_thread = threading.Thread(target=self._spinner_worker, daemon=True)
        self.spinner_thread.start()

    def stop_loading(self) -> None:
        """Stop loading indicator."""
        self.loading = False
        self.loading_message = ""
        # Wait for spinner thread to finish
        if self.spinner_thread and self.spinner_thread.is_alive():
            self.spinner_thread.join(timeout=0.5)
        self.spinner_thread = None
        # Don't call render() here - let the normal flow handle it

    def start(self) -> None:
        """Start the game - show main menu."""
        print(self.term.clear())
        print(self.term.home())

        # ASCII Banner
        self.add_log('system', '  _________.__             .__   .__     ___ ___          .__   .__    ')
        self.add_log('system', ' /   _____/|  |__    ____  |  |  |  |   /   |   \\   ____  |  |  |  |   ')
        self.add_log('system', ' \\_____  \\ |  |  \\ _/ __ \\ |  |  |  |  /    ~    \\_/ __ \\ |  |  |  |   ')
        self.add_log('system', ' /        \\|   Y  \\\\  ___/ |  |__|  |__\\    Y    /\\  ___/ |  |__|  |__ ')
        self.add_log('system', '/_______  /|___|  / \\___  >|____/|____/ \\___|_  /  \\___  >|____/|____/ ')
        self.add_log('system', '        \\/      \\/      \\/                    \\/       \\/              ')
        self.add_log('system', '')
        self.add_log('system', '[DEBUG] Two-Stage LLM System aktiv | v0.7.2-sprint1')

        # Show graveyard stats if any
        stats = self.graveyard.get_stats()
        if stats['total_deaths'] > 0:
            self.add_log('system', '')
            self.add_log('system', f"⚰️ Friedhof: {stats['total_deaths']} Gefallene | Höchstes Level: {stats['max_level']}")

        self.add_log('system', '')
        self.add_log('system', 'Tippe "(n)eues Spiel", "(l)aden", oder "(f)riedhof".')

        self.main_loop()

    def return_to_menu(self) -> None:
        """Return to main menu from active game."""
        # Reset state
        self.state = GameState.START
        self.pending_save = False
        self.pending_menu_return = False
        self.pending_stairs_action = None

        # Clear logs
        self.logs = []

        # Show main menu
        self.add_log('system', '')
        self.add_log('system', '═══════════════════════════════════════')
        self.add_log('system', '       Zurück zum Hauptmenü')
        self.add_log('system', '═══════════════════════════════════════')
        self.add_log('system', '')

        # Show graveyard stats if any
        stats = self.graveyard.get_stats()
        if stats['total_deaths'] > 0:
            self.add_log('system', f"⚰️ Friedhof: {stats['total_deaths']} Gefallene | Höchstes Level: {stats['max_level']}")
            self.add_log('system', '')

        self.add_log('system', 'Tippe "(n)eues Spiel", "(l)aden", oder "(f)riedhof".')

    def initialize_new_game(self) -> None:
        """Initialize a new game - generate dungeon, theme, story, etc."""
        import random
        from services.ai_service import get_ai_service

        self.add_log('system', '')

        # Use pre-selected theme (from theme selection screen)
        if hasattr(self, 'selected_theme_config') and self.selected_theme_config:
            theme_config = self.selected_theme_config
        else:
            # Fallback to random (for backwards compatibility with old saves)
            from models.theme import get_random_theme
            theme_config = get_random_theme()

        self.theme = theme_config.name
        self.theme_config = theme_config
        self.player.theme = self.theme

        # Initialize dungeon with theme
        self.start_loading("⚙️ Generiere Dungeon-Layout...")
        try:
            self.dungeon = Dungeon(DUNGEON_SIZE, theme_config=theme_config)
            self.dungeon.generate()
        finally:
            self.stop_loading()

        # Get AI service
        ai = get_ai_service()

        # Generate plot and spawn monsters (fast!)
        if ai.is_available():
            self.start_loading("✨ Generiere Story-Hintergrund...")
            try:
                self.story_context = ai.generate_dungeon_plot(self.theme)
                self.add_log('system', f"✓ Thema: {self.theme}")
                self.add_log('system', f"   {self.story_context[:80]}...")
            finally:
                self.stop_loading()
        else:
            self.story_context = self.theme
            self.add_log('system', f"⚠ AI nicht verfügbar - nutze Fallback-Texte")

        # Generate object palette for the dungeon
        if ai.is_available():
            self.start_loading("🎨 Erstelle Object Palette...")
            try:
                self.object_palette = ai.generate_object_palette(
                    self.theme,
                    self.story_context,
                    DUNGEON_SIZE * DUNGEON_SIZE
                )
                self.add_log('system', f"✓ {len(self.object_palette)} Objekte generiert")
            finally:
                self.stop_loading()
        else:
            self.object_palette = ai._generate_fallback_palette(self.theme, DUNGEON_SIZE * DUNGEON_SIZE)

        # Distribute objects to rooms
        self.start_loading("🗺️ Verteile Objekte im Dungeon...")
        try:
            self._distribute_objects_to_rooms()
        finally:
            self.stop_loading()

        # Load theme-specific quest
        from constants import THEME_QUESTS
        from models.quest import Quest, QuestObjective, QuestManager

        theme_id = theme_config.id
        if theme_id in THEME_QUESTS:
            quest_template = THEME_QUESTS[theme_id]
            objectives = [QuestObjective.from_dict(obj) for obj in quest_template['objectives']]
            quest = Quest(
                id=quest_template['id'],
                title=quest_template['title'],
                description=quest_template['description'],
                objectives=objectives,
                theme_id=quest_template['theme_id'],
                xp_reward=quest_template['xp_reward'],
                gold_reward=quest_template['gold_reward'],
                special_reward=quest_template.get('special_reward')
            )

            # Initialize quest manager if needed
            if not self.player.quest_manager:
                self.player.quest_manager = QuestManager()

            # Add quest
            self.player.quest_manager.add_quest(quest)
            self.add_log('system', f"📜 Quest geladen: {quest.title}")
        else:
            self.add_log('system', f"⚠️ Keine Quest für Theme {theme_id} gefunden")
            if not self.player.quest_manager:
                self.player.quest_manager = QuestManager()

        # Spawn monsters
        self.dungeon.spawn_monsters()

        # Spawn NPCs
        self.dungeon.spawn_npcs()

        # Spawn quest-related NPCs (hostages, etc.)
        if self.player.quest_manager and self.player.quest_manager.get_active_quests():
            active_quest = self.player.quest_manager.get_active_quests()[0]
            self.dungeon.spawn_quest_npcs(active_quest)
            self.add_log('system', f"✓ Quest-NPCs gespawnt")

        # Spawn hazards
        self.dungeon.spawn_hazards()

        # Note: Room descriptions werden on-the-fly generiert beim Betreten!
        self.add_log('system', '✓ Dungeon generiert!')
        self.add_log('system', '')

    def main_loop(self) -> None:
        """Main game loop."""
        with self.term.cbreak(), self.term.hidden_cursor():
            while self.running:
                self.render()

                # Get input
                command = self.get_input()

                if command is None:
                    continue

                # Handle commands based on game state
                self.handle_command(command)

    def render(self) -> None:
        """Render the game screen."""
        # Clear screen
        print(self.term.home() + self.term.clear())

        # Sticky Header (always visible at top)
        # Shows: Game name + Location (if in dungeon) + HP (if playing)
        if self.state in [GameState.EXPLORING, GameState.ENCOUNTER, GameState.COMBAT, GameState.CONVERSATION]:
            # In dungeon: show full header with location
            left_part = "SHELLHELL v0.7.2"
            middle_part = f"📍 Ebene {self.player.z + 1} [{self.player.x},{self.player.y}]"
            right_part = f"HP: {self.player.hp}/{self.player.max_hp}"

            # Calculate spacing
            total_content = len(left_part) + len(middle_part) + len(right_part)
            available_space = self.term.width - 4  # -4 for borders
            left_spacing = (available_space - total_content) // 2
            right_spacing = available_space - total_content - left_spacing

            header_line = f"│ {left_part}{' ' * left_spacing}{middle_part}{' ' * right_spacing}{right_part} │"

            print(self.term.green("┌" + "─" * (self.term.width - 2) + "┐"))
            print(self.term.green(header_line))
            print(self.term.green("└" + "─" * (self.term.width - 2) + "┘"))
        else:
            # Menu/creation: simple banner
            print(self.term.bold + self.term.green("=" * self.term.width))
            print(self.term.center("SHELLHELL v0.7.2-sprint1"))
            print(self.term.green("=" * self.term.width) + self.term.normal)

        print()

        # Display logs (last 20)
        log_area_height = self.term.height - 10
        visible_logs = self.logs[-log_area_height:]

        # Determine which logs are "new" (last 5 entries)
        new_threshold = 5
        total_visible = len(visible_logs)

        # Disable dimming in menus, character creation, and conversations
        is_menu = self.state in [GameState.START, GameState.THEME_SELECTION, GameState.CHARACTER_CREATION, GameState.CONVERSATION]

        for idx, log in enumerate(visible_logs):
            # Determine if this log is "new" (one of the last N entries)
            is_new = (idx >= total_visible - new_threshold)

            # Get detail level (default to 'normal' for backwards compatibility)
            detail_level = log.get('detail_level', 'normal')

            # Get base color
            color = self.term.white
            if log['type'] == 'system':
                color = self.term.cyan
            elif log['type'] == 'narrative':
                color = self.term.green
            elif log['type'] == 'error':
                color = self.term.red
            elif log['type'] == 'action':
                color = self.term.yellow

            # Apply dimming based on detail level and age
            if is_menu:
                # In menu: no dimming, always full brightness
                print(color(log['text']))
            elif detail_level == 'verbose':
                # Technical details: always heavily dimmed (gray)
                print(self.term.bright_black + log['text'] + self.term.normal)
            elif is_new:
                # New important logs: full brightness
                print(color(log['text']))
            else:
                # Old important logs: slightly dimmed
                print(self.term.dim + color(log['text']) + self.term.normal)

        print()
        print(self.term.green("=" * self.term.width))

        # Status bar (HP is in sticky header, show other stats here)
        if self.state != GameState.START and self.state != GameState.CHARACTER_CREATION:
            status = f"ATK: {self.player.get_effective_attack()} | "
            status += f"DEF: {self.player.get_effective_defense()} | "
            status += f"Gold: {self.player.gold} | XP: {self.player.xp} | Lvl: {self.player.level}"
            print(self.term.bold + status + self.term.normal)
            print(self.term.green("=" * self.term.width))

        # Show last command
        if self.last_command:
            print(self.term.yellow(f"Last: > {self.last_command}"))
            print()

        # Reserve space for loading indicator (rendered by background thread)
        if self.loading and self.loading_message:
            print()  # Empty line where spinner will appear
            print()

    def get_input(self) -> str:
        """Get user input with autocomplete and hints."""
        if self.loading:
            return None

        # Build dynamic prompt
        if hasattr(self.player, 'name') and self.player.name:
            prompt_text = f"$[{self.player.name}]> "
        else:
            prompt_text = "$> "

        try:
            # Use prompt_toolkit for autocomplete and history
            command = self.prompt_session.prompt(prompt_text)
            return command.strip()
        except (KeyboardInterrupt, EOFError):
            # Handle Ctrl+C or Ctrl+D gracefully
            return None

    def handle_command(self, command: str) -> None:
        """Handle a command based on current game state."""
        cmd = command.lower()
        self.last_command = command  # Save for display

        if cmd in ['quit', 'exit', 'q']:
            self.running = False
            return

        # Return to main menu (except when already in START state)
        if cmd in ['menu', 'hauptmenü', 'hauptmenu', 'main']:
            if self.state != GameState.START:
                # Ask if player wants to save first
                if hasattr(self, 'player') and self.player.name:
                    self.add_log('system', '💾 Möchtest du vorher speichern? (j/n)')
                    self.pending_menu_return = True
                    return
                else:
                    # No active game, just return to menu
                    self.return_to_menu()
                    return
            else:
                self.add_log('system', 'Du bist bereits im Hauptmenü.')
                return

        # Handle pending menu return (save confirmation)
        if hasattr(self, 'pending_menu_return') and self.pending_menu_return:
            if cmd in ['j', 'ja', 'y', 'yes']:
                # Save and return to menu
                self.save_game(1)  # Quick save to slot 1
                self.return_to_menu()
                return
            elif cmd in ['n', 'nein', 'no']:
                # Don't save, just return to menu
                self.add_log('system', 'Nicht gespeichert.')
                self.return_to_menu()
                return
            else:
                self.add_log('error', 'Bitte antworte mit "j" (ja) oder "n" (nein).')
                return

        if self.state == GameState.START:
            self.handle_start_command(cmd)
        elif self.state == GameState.THEME_SELECTION:
            self.handle_theme_selection_command(cmd)
        elif self.state == GameState.CHARACTER_CREATION:
            self.handle_creation_command(cmd, command)
        elif self.state == GameState.EXPLORING:
            self.handle_exploring_command(cmd, command)
        elif self.state == GameState.CONVERSATION:
            self.handle_conversation_command(cmd, command)
        elif self.state == GameState.ENCOUNTER:
            self.handle_encounter_command(cmd, command)
        elif self.state == GameState.COMBAT:
            self.handle_combat_command(cmd, command)
        elif self.state == GameState.GAMEOVER:
            self.handle_gameover_command(cmd)

    def handle_start_command(self, cmd: str) -> None:
        """Handle commands in START state."""
        if cmd in ['n', 'neu', 'neues', 's', 'start']:
            # Go to theme selection
            self.state = GameState.THEME_SELECTION
            self.show_theme_selection()
        elif cmd in ['l', 'laden', 'load']:
            # Show available saves
            saves = self.save_manager.list_saves()
            if not saves:
                self.add_log('error', 'Keine Speicherstände gefunden!')
                return

            self.add_log('system', '💾 Verfügbare Speicherstände:')
            for slot, info in saves.items():
                if 'error' in info:
                    self.add_log('error', f"  Slot {slot}: Fehler - {info['error']}")
                elif 'player_name' not in info:
                    self.add_log('system', f"  Slot {slot}: Leer")
                else:
                    name = info['player_name']
                    level = info['level']
                    theme = info.get('theme', 'Unbekannt')
                    hp = info['hp']
                    max_hp = info['max_hp']
                    self.add_log('system', f"  Slot {slot}: {name}, lvl {level}, {theme} ({hp}/{max_hp} HP)")

            self.add_log('system', 'Tippe Slot-Nummer (1-3) zum Laden.')
        elif cmd in ['1', '2', '3']:
            # Try to load slot
            slot = int(cmd)
            self.load_game(slot)
        elif cmd in ['f', 'friedhof', 'graveyard']:
            self.show_graveyard()

    def show_theme_selection(self) -> None:
        """Show available themes for selection."""
        from models.theme import THEME_CONFIGS

        self.add_log('system', '')
        self.add_log('system', '🎭 Wähle dein Abenteuer:')
        self.add_log('system', '')

        # Show all themes with numbers
        theme_list = list(THEME_CONFIGS.values())
        for i, theme in enumerate(theme_list, 1):
            self.add_log('system', f"  ({i}) {theme.name}")
            self.add_log('system', f"      {theme.description}")

        self.add_log('system', '')
        self.add_log('system', f"  (r) Zufällig wählen")
        self.add_log('system', '')
        self.add_log('system', 'Tippe die Nummer oder (r) für Random.')

    def handle_theme_selection_command(self, cmd: str) -> None:
        """Handle theme selection."""
        from models.theme import THEME_CONFIGS, get_random_theme
        from game.character_creation import roll_attributes

        theme_list = list(THEME_CONFIGS.values())

        # Random selection
        if cmd in ['r', 'random', 'zufall', 'zufällig']:
            selected_theme = get_random_theme()
            self.selected_theme_config = selected_theme
            self.add_log('system', f"🎲 Zufällig gewählt: {selected_theme.name}")
        # Number selection
        elif cmd.isdigit():
            choice = int(cmd)
            if 1 <= choice <= len(theme_list):
                selected_theme = theme_list[choice - 1]
                self.selected_theme_config = selected_theme
                self.add_log('system', f"✓ Gewählt: {selected_theme.name}")
            else:
                self.add_log('error', f'Ungültige Auswahl. Bitte 1-{len(theme_list)} oder (r).')
                return
        else:
            self.add_log('error', f'Ungültige Auswahl. Bitte 1-{len(theme_list)} oder (r).')
            return

        # Move to character creation
        self.add_log('system', '')
        self.temp_attributes = roll_attributes()
        self.state = GameState.CHARACTER_CREATION
        self.creation_step = CreationStep.ROLLING

        attrs = self.temp_attributes
        self.add_log('system', f"Attribute gewürfelt:")
        self.add_log('system', f"  STR: {attrs.strength}  DEX: {attrs.dexterity}  WIS: {attrs.wisdom}  INT: {attrs.intelligence}  VIT: {attrs.vitality}")
        self.add_log('system', '(b)estätigen oder beliebiges Zeichen für neuen Wurf.')

    def _secretly_roll_gift(self) -> None:
        """
        Secretly roll for a gift (30% chance).
        Apply stat malus without telling the player.
        The gift bonus will be discovered during gameplay.
        """
        import random
        from constants_traits import GIFTS

        # 30% chance to get a gift
        if random.random() < 0.30:
            gift = random.choice(GIFTS)
            self.player.gift = gift

            # Apply stat malus SECRETLY (player doesn't know yet!)
            for stat, malus in gift['stat_malus'].items():
                current = getattr(self.player.attributes, stat)
                setattr(self.player.attributes, stat, current + malus)

            # Don't tell the player! They'll discover it during gameplay

    def handle_creation_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in CHARACTER_CREATION state."""
        from game.character_creation import roll_attributes, get_race_by_key

        if self.creation_step == CreationStep.ROLLING:
            if cmd in ['b', 'bestätigen']:
                self.player.attributes = self.temp_attributes
                self.creation_step = CreationStep.RACE
                self.add_log('system', 'Rasse wählen: (m)ensch, (o)rk, (e)lf, (h)albelf, (g)nom')
            else:
                self.temp_attributes = roll_attributes()
                attrs = self.temp_attributes
                self.add_log('system', f"Neu gewürfelt: STR: {attrs.strength}  DEX: {attrs.dexterity}  WIS: {attrs.wisdom}  INT: {attrs.intelligence}  VIT: {attrs.vitality}")

        elif self.creation_step == CreationStep.RACE:
            race = get_race_by_key(cmd)
            if race:
                self.player.race = race['name']
                self.creation_step = CreationStep.QUIRK

                # Show quirk options
                from constants_traits import QUIRKS
                self.add_log('system', '')
                self.add_log('system', '═══ QUIRKS / TICKS (Optional) ═══')
                self.add_log('system', 'Wähle einen Quirk für Stat-Bonus (aber narrative Nachteile):')
                self.add_log('system', '')

                for i, quirk in enumerate(QUIRKS, 1):
                    bonus_str = ", ".join([f"+{v} {k.upper()[:3]}" for k, v in quirk['stat_bonus'].items()])
                    self.add_log('system', f"  ({i}) {quirk['name']} - {quirk['description']}")

                self.add_log('system', f"  (0) Kein Quirk")
                self.add_log('system', '')
            else:
                self.add_log('error', 'Ungültige Rasse.')

        elif self.creation_step == CreationStep.QUIRK:
            from constants_traits import QUIRKS, GIFTS
            import random

            if cmd == '0':
                # No quirk - proceed to name
                self._secretly_roll_gift()
                self.creation_step = CreationStep.NAME
                self.add_log('system', f"Name für deinen {self.player.race}?")
            else:
                try:
                    choice = int(cmd) - 1
                    if 0 <= choice < len(QUIRKS):
                        quirk = QUIRKS[choice]
                        self.player.quirk = quirk

                        # Apply stat bonus
                        for stat, bonus in quirk['stat_bonus'].items():
                            current = getattr(self.player.attributes, stat)
                            setattr(self.player.attributes, stat, current + bonus)

                        self.add_log('system', f"✓ Quirk gewählt: {quirk['name']}")

                        # Secretly roll for gift
                        self._secretly_roll_gift()

                        self.creation_step = CreationStep.NAME
                        self.add_log('system', f"Name für deinen {self.player.race}?")
                    else:
                        self.add_log('error', 'Ungültige Wahl.')
                except ValueError:
                    self.add_log('error', 'Ungültige Eingabe.')

        elif self.creation_step == CreationStep.NAME:
            self.player.name = full_command

            # Calculate max HP based on VIT
            # Formula: 50 + (VIT - 10) * 3
            vit_modifier = (self.player.attributes.vitality - 10) * 3
            self.player.max_hp = 50 + vit_modifier
            self.player.hp = self.player.max_hp  # Start at full HP

            # Initialize dungeon NOW (after character is complete)
            self.initialize_new_game()

            self.state = GameState.EXPLORING

            # Generate intro sequence
            from services.ai_service import get_ai_service
            ai = get_ai_service()
            starting_room = self.dungeon.get_room(0, 0, 0)

            # Visual separator with room coordinates and level
            separator = f"─────────── (0,0) Ebene 1/{self.dungeon.num_levels} ───────────"
            self.add_log('system', separator)

            if ai.is_available():
                self.start_loading("✨ Generiere Intro-Sequenz...")
                try:
                    intro = ai.generate_intro_sequence(
                        self.player.name,
                        self.player.race,
                        self.theme,
                        self.story_context,
                        starting_room
                    )
                    self.add_log('narrative', intro)

                    # Mark starting room as visited and cache description
                    starting_room.visited = True
                finally:
                    self.stop_loading()
            else:
                self.add_log('narrative', f"{self.player.name} betritt {self.theme}...")

            self.add_log('system', '')
            self.add_log('system', 'Bewegung: (n)orden, (s)üden, (o)sten, (w)esten')
            self.add_log('system', 'Weitere Befehle: hilfe, inventar, status')

            # Show starting room exits
            from models.door import Direction, DoorState
            exits = self.dungeon.get_exits(0, 0)
            exit_parts = []
            for exit_name in exits:
                # Determine door direction
                door_dir = None
                if exit_name == 'Norden':
                    door_dir = Direction.NORTH
                elif exit_name == 'Süden':
                    door_dir = Direction.SOUTH
                elif exit_name == 'Osten':
                    door_dir = Direction.EAST
                elif exit_name == 'Westen':
                    door_dir = Direction.WEST

                # Check door state
                if door_dir and door_dir in starting_room.doors:
                    door = starting_room.doors[door_dir]
                    if door.state == DoorState.LOCKED:
                        exit_parts.append(f"{exit_name} 🔒")
                    else:
                        exit_parts.append(exit_name)
                else:
                    exit_parts.append(exit_name)

            if exit_parts:
                self.add_log('system', f"🧭 Ausgänge: {', '.join(exit_parts)}")

    def handle_exploring_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in EXPLORING state."""
        from game.exploration import move_player
        from game.actions import execute_free_action

        # Handle save slot selection
        if self.pending_save:
            if cmd.isdigit() and int(cmd) in [1, 2, 3]:
                slot = int(cmd)
                self.pending_save = False
                self.save_game(slot)
                return
            else:
                self.add_log('error', 'Bitte wähle einen Slot (1-3).')
                return

        # Handle stairs prompt
        if self.pending_stairs_action:
            if cmd in ['j', 'ja', 'y', 'yes']:
                # Accept stairs movement
                if self.pending_stairs_action == 'down':
                    self.player.z += 1
                    self.add_log('system', f"🪜 Du steigst die Treppe hinab zur Ebene {self.player.z + 1}.")
                elif self.pending_stairs_action == 'up':
                    self.player.z -= 1
                    if self.player.z == 0:
                        self.add_log('system', "🪜 Du steigst die Treppe hinauf zur Oberfläche.")
                    else:
                        self.add_log('system', f"🪜 Du steigst die Treppe hinauf zur Ebene {self.player.z + 1}.")

                # Clear the pending action
                self.pending_stairs_action = None

                # Show new room description
                room = self.dungeon.get_room(self.player.x, self.player.y, self.player.z)
                separator = f"─────────── ({self.player.x},{self.player.y}) Ebene {self.player.z + 1} ───────────"
                self.add_log('system', separator)

                if room.description:
                    self.add_log('narrative', room.description)
                else:
                    self.add_log('narrative', "Ein neuer Bereich des Dungeons öffnet sich vor dir.")

                return
            elif cmd in ['n', 'nein', 'no']:
                # Decline stairs movement
                self.add_log('system', "Du entscheidest dich, hier zu bleiben.")
                self.pending_stairs_action = None
                return
            else:
                # Invalid response - remind them
                self.add_log('error', 'Bitte antworte mit "j" (ja) oder "n" (nein).')
                return

        # Movement commands - map long forms to short forms
        movement_map = {
            'n': 'n', 'norden': 'n', 'north': 'n',
            's': 's', 'süden': 's', 'süd': 's', 'south': 's',
            'o': 'o', 'osten': 'o', 'ost': 'o', 'east': 'o',
            'w': 'w', 'westen': 'w', 'west': 'w'
        }

        if cmd in movement_map:
            move_player(self, movement_map[cmd])
        elif cmd in ['a', 'angriff', 'attack']:
            # Allow attacking unaware monsters from EXPLORING state
            room = self.dungeon.get_room(self.player.x, self.player.y, self.player.z)
            if room and room.monster and room.monster.hp > 0:
                # Transition to COMBAT and attack
                self.state = GameState.COMBAT
                from game.combat import attack
                attack(self)
            else:
                self.add_log('error', 'Kein Gegner hier zum Angreifen.')
        elif cmd in ['hilfe', 'help', 'h']:
            self.add_log('system', 'Befehle: n/s/o/w (Bewegung), inventar (i), status, zauber (z), rast, hilfe (h)')
            self.add_log('system', 'Speichern: save oder save [1-3]')
            self.add_log('system', 'Hauptmenü: menu | Beenden: quit')
            self.add_log('system', 'Oder versuche freie Aktionen: "untersuche wand", "hebe stein auf", etc.')
            self.add_log('system', 'Magie: "benutze [item], sage \'worte\', geste [bewegung]"')
            self.add_log('system', 'Bei Monstern: (a)ngriff')
        elif cmd in ['inventar', 'i', 'inv']:
            self.show_inventory()
        elif cmd in ['status', 'stats']:
            self.show_status()
        elif cmd in ['zauber', 'grimoire', 'z', 'spells']:
            self.show_grimoire()
        elif cmd in ['rast', 'rasten', 'rest', 'ausruhen', 'ruhen', 'sleep']:
            from game.exploration import rest_player
            rest_player(self)
        elif cmd in ['speichern', 'save', 'sp'] or cmd.startswith('speichern ') or cmd.startswith('save '):
            # Parse slot number if provided (e.g., "save 2")
            slot = 1  # default
            parts = full_command.split()
            if len(parts) > 1 and parts[1].isdigit():
                slot = int(parts[1])
                if slot not in [1, 2, 3]:
                    self.add_log('error', 'Slot muss zwischen 1-3 sein.')
                    return
            else:
                # Ask user which slot
                self.add_log('system', '💾 In welchen Slot speichern? (1-3)')
                saves = self.save_manager.list_saves()
                for slot_num in [1, 2, 3]:
                    info = saves.get(slot_num, {})
                    if 'error' in info or 'player_name' not in info:
                        self.add_log('system', f"  Slot {slot_num}: Leer")
                    else:
                        name = info['player_name']
                        level = info['level']
                        theme = info.get('theme', 'Unbekannt')
                        self.add_log('system', f"  Slot {slot_num}: {name}, lvl {level}, {theme}")

                # Set pending state to wait for slot selection
                self.pending_save = True
                return

            self.save_game(slot)
        elif cmd.startswith('e '):
            # Equip item
            item_name = cmd[2:].strip()
            item = None
            for inv_item in self.player.inventory:
                if item_name.lower() in inv_item.name.lower():
                    item = inv_item
                    break

            if item:
                if self.player.equip_item(item):
                    self.add_log('system', f"{item.name} angelegt.")
                else:
                    self.add_log('error', f"Kann {item.name} nicht anlegen.")
            else:
                self.add_log('error', f"Item nicht gefunden: {item_name}")
        else:
            # Check for simple loot pickup before running through LLM
            room = self.dungeon.get_room(self.player.x, self.player.y, self.player.z)
            cmd_lower = full_command.lower()
            pickup_keywords = ['hebe', 'nimm', 'nehme', 'aufheben', 'aufnehmen', 'pick', 'take']
            simple_pickup = any(keyword in cmd_lower for keyword in pickup_keywords)

            if simple_pickup and room.loot:
                # Direct pickup without LLM processing
                # Try to find matching item or just pick up everything
                target_words = cmd_lower.split()
                picked_up = False

                for item in room.loot[:]:
                    # Check if item name is mentioned or if it's a generic "hebe es auf"
                    item_mentioned = any(word in item.name.lower() for word in target_words)
                    generic_pickup = any(word in cmd_lower for word in ['es', 'das', 'alles', 'all', 'it'])

                    if item_mentioned or (generic_pickup and len(room.loot) == 1):
                        self.player.inventory.append(item)
                        room.loot.remove(item)
                        self.add_log('system', f"✓ +1 Item: {item.name}")
                        self.add_log('narrative', f"{item.description}")
                        picked_up = True
                        break  # Only pick up one item at a time

                if picked_up:
                    return  # Skip free action processing

            # Check for NPC conversation keywords - enter CONVERSATION mode
            room = self.dungeon.get_room(self.player.x, self.player.y, self.player.z)
            if room.npc and room.npc.alive:
                talk_keywords = ['sprich', 'spreche', 'rede', 'frag', 'frage', 'talk', 'speak', 'ask', 'sag']
                is_talking = any(keyword in full_command.lower() for keyword in talk_keywords)

                if is_talking:
                    # Enter conversation mode
                    self.conversation_npc = room.npc
                    self.state = GameState.CONVERSATION
                    self.add_log('system', f"💬 Du beginnst ein Gespräch mit {room.npc.name}.")
                    self.add_log('system', '(Tippe "tschüss" um das Gespräch zu beenden)')

                    # Process the initial message directly
                    self.handle_conversation_command(cmd, full_command)
                    return

            # Free action (for complex interactions)
            execute_free_action(self, full_command)

    def handle_conversation_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in CONVERSATION state (talking to NPC)."""
        # Exit keywords
        exit_keywords = ['tschüss', 'tschuess', 'bye', 'exit', 'ende', 'verlassen', 'geh', 'leave']

        if cmd in exit_keywords:
            self.add_log('system', f"💬 Du beendest das Gespräch mit {self.conversation_npc.name}.")
            self.conversation_npc = None
            self.state = GameState.EXPLORING
            return

        # All other input goes directly to NPC dialogue
        if not self.conversation_npc:
            # Safety check - shouldn't happen
            self.add_log('error', 'Kein Gesprächspartner gefunden.')
            self.state = GameState.EXPLORING
            return

        # Get current room
        room = self.dungeon.get_room(self.player.x, self.player.y, self.player.z)

        # Send to NPC dialogue system
        from services.ai_service import get_ai_service
        ai = get_ai_service()

        if ai.is_available():
            self.start_loading(f"💬 {self.conversation_npc.name} antwortet...")
            try:
                npc_result = ai.generate_npc_dialogue(
                    player_message=full_command,
                    npc=self.conversation_npc,
                    world_state=self.world_state,
                    story_context=self.story_context,
                    player_hp=self.player.hp,
                    player_max_hp=self.player.max_hp,
                    player_quirk=self.player.quirk,
                    player_morality=self.player.morality,
                    relationship=self.player.get_relationship(self.conversation_npc.id),
                    quest_manager=self.player.quest_manager,
                    player_equipment=self.player.equipment
                )

                response_text = npc_result['response']
                attitude_change = npc_result.get('attitude_change', 0)

                # Record interaction
                self.conversation_npc.add_interaction(
                    player_action=full_command,
                    npc_response=response_text,
                    topic="general"
                )

                # Display response
                npc_icon = {
                    'merchant': '🛒',
                    'scholar': '📚',
                    'hermit': '🧙',
                    'guard': '⚔️',
                    'priest': '✨'
                }.get(self.conversation_npc.role, '👤')

                self.add_log('narrative', f"{npc_icon} {self.conversation_npc.name}: \"{response_text}\"")

                # Process attitude change
                if attitude_change != 0:
                    self.player.adjust_relationship(self.conversation_npc.id, attitude_change * 5)
                    if attitude_change > 0:
                        self.add_log('system', f"💚 {self.conversation_npc.name} mag dich etwas mehr.")
                        karma_gain = attitude_change * 5
                        self.player.adjust_morality(karma_gain, f"Gute Tat: {self.conversation_npc.name}")
                        self.add_log('system', f"⚖️ Karma: +{karma_gain}", detail_level='verbose')
                    elif attitude_change < 0:
                        self.add_log('system', f"💔 {self.conversation_npc.name} ist enttäuscht von dir.")
                        karma_loss = attitude_change * 3
                        self.player.adjust_morality(karma_loss, f"Schlechte Tat: {self.conversation_npc.name}")
                        self.add_log('system', f"⚖️ Karma: {karma_loss}", detail_level='verbose')

                # Small XP for conversation
                self.player.xp += 2
                self.add_log('system', '+2 XP (Gespräch)')

                self.add_log('system', '(Tippe "tschüss" um das Gespräch zu beenden)')

            finally:
                self.stop_loading()
        else:
            self.add_log('error', 'AI nicht verfügbar für Gespräche.')
            self.state = GameState.EXPLORING
            self.conversation_npc = None

    def handle_combat_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in COMBAT state."""
        from game.combat import attack, flee_combat

        if cmd in ['a', 'angriff', 'attack']:
            attack(self)
        elif cmd in ['f', 'flee', 'fliehen', 'flucht']:
            flee_combat(self)
        elif cmd in ['hilfe', 'help', 'h']:
            self.add_log('system', 'Kampf-Befehle: (a)ngriff, (f)liehen')
            self.add_log('system', 'Sonstiges: menu (Hauptmenü), quit (Beenden)')
        else:
            self.add_log('error', f'Unbekannter Kampf-Befehl: {full_command}')

    def handle_encounter_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in ENCOUNTER state (pre-combat)."""
        from game.actions import DiceRoller

        room = self.dungeon.get_room(self.player.x, self.player.y, self.player.z)

        if not room or not room.monster:
            self.add_log('error', 'Kein Gegner hier.')
            self.state = GameState.EXPLORING
            return

        monster = room.monster

        if cmd in ['a', 'angriff', 'attack']:
            # Start combat immediately
            self.state = GameState.COMBAT
            self.add_log('system', "Du greifst an!")
            self.add_log('system', "Befehle: (a)ngriff, (f)liehen")

        elif cmd in ['s', 'schleichen', 'sneak', 'stealth']:
            # DEX check to sneak past or get surprise round
            dex_mod = (self.player.attributes.dexterity - 10) // 2

            # DC based on monster's perception (using defense as proxy)
            sneak_dc = 12 + (monster.defense // 3)

            sneak_roll = DiceRoller.roll(20)
            sneak_total = sneak_roll + dex_mod

            self.add_log('system', f"🎲 Schleichen (DEX): [{sneak_roll}] + {dex_mod} = {sneak_total} vs DC {sneak_dc}", detail_level='verbose')

            if sneak_total >= sneak_dc:
                # Success! Monster doesn't notice
                self.add_log('system', f"✓ Du schleichst lautlos vorbei. {monster.name} bemerkt dich nicht!")

                # Mark monster as unaware (for potential backstab bonus later)
                monster.unaware = True

                self.state = GameState.EXPLORING
            else:
                # Failed! Monster noticed - combat starts
                self.add_log('error', f"✗ Schleichen gescheitert! {monster.name} hat dich bemerkt!")
                self.state = GameState.COMBAT
                self.add_log('system', "Befehle: (a)ngriff, (f)liehen")

        elif cmd in ['r', 'reden', 'talk', 'speak', 'sprechen']:
            # Check if monster is humanoid
            humanoid_types = ['ork', 'goblin', 'mensch', 'elf', 'zwerg', 'gnom', 'räuber', 'bandit', 'wache']
            is_humanoid = any(h_type in monster.name.lower() for h_type in humanoid_types)

            if not is_humanoid:
                self.add_log('error', f"{monster.name} scheint nicht zu verstehen, was du sagst...")
                self.add_log('system', "Du kannst nur mit humanoiden Kreaturen sprechen.")
                return

            # CHA/WIS check to persuade/intimidate
            cha_mod = (self.player.attributes.charisma - 10) // 2 if hasattr(self.player.attributes, 'charisma') else 0
            wis_mod = (self.player.attributes.wisdom - 10) // 2

            # Use higher of CHA or WIS
            social_mod = max(cha_mod, wis_mod)

            # DC based on monster's hostility (HP as proxy - stronger = more aggressive)
            talk_dc = 10 + (monster.max_hp // 10)

            talk_roll = DiceRoller.roll(20)
            talk_total = talk_roll + social_mod

            self.add_log('system', f"🎲 Diplomatie (CHA/WIS): [{talk_roll}] + {social_mod} = {talk_total} vs DC {talk_dc}", detail_level='verbose')

            if talk_total >= talk_dc + 5:
                # Critical success! Monster becomes friendly/leaves loot
                self.add_log('system', f"✓ Kritischer Erfolg! {monster.name} ist beeindruckt von deinen Worten!")
                self.add_log('narrative', f"{monster.name} lässt eine Münze fallen und zieht sich zurück.")

                # Monster leaves gold
                gold_reward = 5 + (monster.max_hp // 3)
                self.player.gold += gold_reward
                self.add_log('system', f"+{gold_reward} Gold")

                # Remove monster
                room.monster = None
                self.state = GameState.EXPLORING

            elif talk_total >= talk_dc:
                # Success! Monster lets you pass
                self.add_log('system', f"✓ {monster.name} scheint überzeugt...")
                self.add_log('narrative', f"{monster.name} tritt beiseite und lässt dich passieren.")

                # Remove monster (or could mark as passive)
                room.monster = None
                self.state = GameState.EXPLORING

            else:
                # Failed! Combat starts (but no surprise round)
                self.add_log('error', f"✗ {monster.name} ist nicht überzeugt und greift an!")
                self.state = GameState.COMBAT
                self.add_log('system', "Befehle: (a)ngriff, (f)liehen")

        elif cmd in ['f', 'fliehen', 'flee']:
            # Flee before combat - easier than fleeing during combat
            dex_mod = (self.player.attributes.dexterity - 10) // 2
            flee_dc = 8 + (monster.defense // 3)  # Easier than combat flee

            flee_roll = DiceRoller.roll(20)
            flee_total = flee_roll + dex_mod

            self.add_log('system', f"🎲 Flucht (DEX): [{flee_roll}] + {dex_mod} = {flee_total} vs DC {flee_dc}", detail_level='verbose')

            if flee_total >= flee_dc:
                # Success! Flee to previous room or random adjacent
                self.add_log('system', f"✓ Du entkommst {monster.name} rechtzeitig!")

                # Find adjacent rooms
                adjacent_positions = []

                # North
                if self.player.y > 0:
                    adjacent_positions.append((self.player.x, self.player.y - 1))
                # South
                if self.player.y < self.dungeon.size - 1:
                    adjacent_positions.append((self.player.x, self.player.y + 1))
                # East
                if self.player.x < self.dungeon.size - 1:
                    adjacent_positions.append((self.player.x + 1, self.player.y))
                # West
                if self.player.x > 0:
                    adjacent_positions.append((self.player.x - 1, self.player.y))

                if adjacent_positions:
                    import random
                    new_x, new_y = random.choice(adjacent_positions)

                    # Move player
                    self.player.x = new_x
                    self.player.y = new_y

                    self.state = GameState.EXPLORING

                    # Show brief message about new location
                    self.add_log('system', f"Du ziehst dich zurück nach ({new_x}, {new_y})")
                else:
                    self.add_log('error', 'Nirgendwo zu fliehen! Du musst kämpfen.')
                    self.state = GameState.COMBAT
                    self.add_log('system', "Befehle: (a)ngriff, (f)liehen")
            else:
                # Failed! Combat starts
                self.add_log('error', f"✗ {monster.name} versperrt dir den Weg!")
                self.state = GameState.COMBAT
                self.add_log('system', "Befehle: (a)ngriff, (f)liehen")

        elif cmd in ['hilfe', 'help', 'h']:
            # Check if humanoid for context-sensitive help
            humanoid_types = ['ork', 'goblin', 'mensch', 'elf', 'zwerg', 'gnom', 'räuber', 'bandit', 'wache']
            is_humanoid = any(h_type in monster.name.lower() for h_type in humanoid_types)

            if is_humanoid:
                self.add_log('system', 'Encounter-Befehle: (a)ngriff, (s)chleichen, (r)eden, (f)liehen')
            else:
                self.add_log('system', 'Encounter-Befehle: (a)ngriff, (s)chleichen, (f)liehen')
            self.add_log('system', 'Sonstiges: menu (Hauptmenü), quit (Beenden)')
        else:
            self.add_log('error', f'Unbekannter Encounter-Befehl: {full_command}')

    def handle_gameover_command(self, cmd: str) -> None:
        """Handle commands in GAMEOVER state."""
        if cmd in ['n', 'neu', 'new']:
            # Start new game with preserved grimoire
            import random
            from game.character_creation import roll_attributes
            from models.theme import get_random_theme

            # Reset game state
            self.logs = []
            self.player = Player()

            # Restore grimoire from previous run
            if self.preserved_grimoire:
                self.player.grimoire = self.preserved_grimoire
                self.add_log('system', f"📖 Grimoire wiederhergestellt: {len(self.player.grimoire.spells)} Zauber bekannt")

            # Pick theme and create dungeon
            theme_config = get_random_theme()
            self.theme = theme_config.name
            self.theme_config = theme_config
            self.player.theme = self.theme
            self.dungeon = Dungeon(DUNGEON_SIZE, theme_config=theme_config)
            self.dungeon.generate()

            # Generate plot
            from services.ai_service import get_ai_service
            ai = get_ai_service()
            if ai.is_available():
                self.story_context = ai.generate_dungeon_plot(self.theme)
            else:
                self.story_context = self.theme

            # Generate object palette
            if ai.is_available():
                self.object_palette = ai.generate_object_palette(
                    self.theme,
                    self.story_context,
                    DUNGEON_SIZE * DUNGEON_SIZE
                )
            else:
                self.object_palette = ai._generate_fallback_palette(self.theme, DUNGEON_SIZE * DUNGEON_SIZE)

            # Distribute objects to rooms
            self._distribute_objects_to_rooms()

            # Spawn monsters
            self.dungeon.spawn_monsters()

            # Spawn NPCs
            self.dungeon.spawn_npcs()

            # Spawn hazards
            self.dungeon.spawn_hazards()

            # Start character creation
            self.temp_attributes = roll_attributes()
            self.state = GameState.CHARACTER_CREATION
            self.creation_step = CreationStep.ROLLING

            attrs = self.temp_attributes
            self.add_log('system', f"Neue Reise beginnt... Thema: {self.theme}")
            self.add_log('system', f"Attribute gewürfelt:")
            self.add_log('system', f"  STR: {attrs.strength}  DEX: {attrs.dexterity}  WIS: {attrs.wisdom}  INT: {attrs.intelligence}  VIT: {attrs.vitality}")
            self.add_log('system', '(b)estätigen oder beliebiges Zeichen für neuen Wurf.')

        elif cmd in ['f', 'friedhof', 'graveyard']:
            self.show_graveyard()

        elif cmd in ['q', 'quit']:
            self.running = False

        else:
            self.add_log('error', 'Game Over. Tippe (n)eu, (f)riedhof, oder (q)uit.')

    def show_inventory(self) -> None:
        """Show player inventory."""
        if not self.player.inventory:
            self.add_log('system', 'Inventar ist leer.')
        else:
            self.add_log('system', 'Inventar:')

            # Type icons for clarity
            from models.items import ItemType
            type_icons = {
                ItemType.WEAPON: "⚔️",
                ItemType.ARMOR: "🛡️",
                ItemType.RING: "💍",
                ItemType.HEAD: "👑",
                ItemType.CONSUMABLE: "🍎",
                ItemType.KEY: "🔑",
                ItemType.MATERIAL: "🧪"
            }

            type_labels = {
                ItemType.WEAPON: "Waffe",
                ItemType.ARMOR: "Rüstung",
                ItemType.RING: "Ring",
                ItemType.HEAD: "Helm",
                ItemType.CONSUMABLE: "Verbrauchbar",
                ItemType.KEY: "Schlüssel",
                ItemType.MATERIAL: "Material"
            }

            for item in self.player.inventory:
                equipped = " [ANGELEGT]" if item.equipped else ""
                curse_marker = " 💀 [VERFLUCHT]" if item.is_curse else ""
                icon = type_icons.get(item.type, "📦")
                type_label = type_labels.get(item.type, "Item")

                # Build stats string (handle both positive and negative stats)
                stats_parts = []
                if item.stats.attack != 0:
                    sign = "+" if item.stats.attack > 0 else ""
                    stats_parts.append(f"{sign}{item.stats.attack} ATK")
                if item.stats.defense != 0:
                    sign = "+" if item.stats.defense > 0 else ""
                    stats_parts.append(f"{sign}{item.stats.defense} DEF")
                if item.stats.hp != 0:
                    sign = "+" if item.stats.hp > 0 else ""
                    stats_parts.append(f"{sign}{item.stats.hp} HP")
                if item.stats.strength != 0:
                    sign = "+" if item.stats.strength > 0 else ""
                    stats_parts.append(f"{sign}{item.stats.strength} STR")
                if item.stats.dexterity != 0:
                    sign = "+" if item.stats.dexterity > 0 else ""
                    stats_parts.append(f"{sign}{item.stats.dexterity} DEX")
                if item.stats.wisdom != 0:
                    sign = "+" if item.stats.wisdom > 0 else ""
                    stats_parts.append(f"{sign}{item.stats.wisdom} WIS")
                if item.stats.intelligence != 0:
                    sign = "+" if item.stats.intelligence > 0 else ""
                    stats_parts.append(f"{sign}{item.stats.intelligence} INT")

                # Build special effects string
                if item.special_effects:
                    for effect_name, effect_value in item.special_effects.items():
                        if effect_name.endswith('_resistance'):
                            # Resistances: show as percentage
                            res_type = effect_name.replace('_resistance', '').capitalize()
                            percentage = int(effect_value * 100)
                            stats_parts.append(f"{percentage}% {res_type}res")
                        elif effect_name.endswith('_weakness'):
                            # Weaknesses (negative resistances)
                            weakness_type = effect_name.replace('_weakness', '').capitalize()
                            percentage = int(abs(effect_value) * 100)
                            stats_parts.append(f"-{percentage}% {weakness_type}res")
                        elif effect_name == 'poison_damage':
                            stats_parts.append(f"+{effect_value} Giftschaden")
                        elif effect_name == 'lifesteal':
                            percentage = int(effect_value * 100)
                            stats_parts.append(f"{percentage}% Lifesteal")
                        elif effect_name == 'curse_damage_per_turn':
                            stats_parts.append(f"-{effect_value} HP/Runde")

                stats_str = f" [{', '.join(stats_parts)}]" if stats_parts else ""
                self.add_log('system', f"  {icon} {item.name} ({type_label}){stats_str}{curse_marker}{equipped}")

    def show_status(self) -> None:
        """Show player status."""
        p = self.player
        self.add_log('system', f"{p.name} ({p.race}) - Level {p.level}")
        self.add_log('system', f"HP: {p.hp}/{p.max_hp}  Gold: {p.gold}  XP: {p.xp}")
        self.add_log('system', f"STR: {p.attributes.strength}  DEX: {p.attributes.dexterity}  WIS: {p.attributes.wisdom}  INT: {p.attributes.intelligence}  VIT: {p.attributes.vitality}")

        # Show karma/reputation
        reputation_tier = p.get_reputation_tier()
        karma_color = "⚖️"  # Neutral
        if p.morality >= 50:
            karma_color = "✨"  # Good
        elif p.morality <= -50:
            karma_color = "💀"  # Evil
        self.add_log('system', f"{karma_color} Karma: {p.morality} ({reputation_tier})")

        # Show quest status if available
        if p.quest_manager:
            active_quests = p.quest_manager.get_active_quests()
            if active_quests:
                self.add_log('system', '')
                self.add_log('system', '📜 Aktive Quests:')
                for quest in active_quests:
                    # Quest title with completion percentage
                    completed_objs = sum(1 for obj in quest.objectives if obj.completed)
                    total_objs = len(quest.objectives)
                    percentage = int((completed_objs / total_objs) * 100) if total_objs > 0 else 0

                    if quest.completed:
                        self.add_log('system', f"  ✓ {quest.title} [ABGESCHLOSSEN]")
                    else:
                        self.add_log('system', f"  • {quest.title} [{percentage}%]")

                    # Show non-hidden objectives
                    for obj in quest.objectives:
                        if not obj.hidden:
                            status_icon = '✓' if obj.completed else '○'
                            progress = f"{obj.count_current}/{obj.count_required}" if obj.count_required > 1 else ""
                            self.add_log('system', f"    {status_icon} {obj.description} {progress}")

    def show_grimoire(self) -> None:
        """Show discovered spells."""
        if not self.player.grimoire.spells:
            self.add_log('system', '📖 Grimoire ist leer. Entdecke Zauber durch Experimente!')
            self.add_log('system', 'Beispiel: "benutze rubin-staub, sage \'ignis\', geste aufwärts"')
        else:
            self.add_log('system', f'📖 Grimoire ({len(self.player.grimoire.spells)} Zauber entdeckt):')
            for spell in self.player.grimoire.spells:
                effect_icons = {
                    'fire': '🔥',
                    'ice': '❄️',
                    'heal': '💚',
                    'shield': '🛡️',
                    'lightning': '⚡',
                    'dark': '🌑',
                    'light': '✨'
                }
                icon = effect_icons.get(spell.effect_type, '🔮')
                magnitude_text = {'minor': 'Klein', 'moderate': 'Mittel', 'major': 'Groß'}.get(spell.magnitude, spell.magnitude)

                self.add_log('system', f"  {icon} {spell.name} ({magnitude_text})")
                self.add_log('system', f"     Komponenten: {', '.join(spell.components)}")
                self.add_log('system', f"     Worte: '{spell.words}' | Geste: {spell.gesture}")
                self.add_log('system', f"     Benutzt: {spell.uses}x | Plausibilität: {spell.plausibility:.1%}")

    def _distribute_objects_to_rooms(self) -> None:
        """Strategically distribute objects from palette to dungeon rooms."""
        import random

        if not self.object_palette:
            return

        # Create mapping of suggested_location to room types (now with z-coordinate)
        location_mapping = {
            'entrance': [(0, 0, 0)],  # Starting room
            'stairs': [],  # Stairs rooms (collected below)
            'center': [],  # Center rooms on each level
            'storage': [],  # Treasure rooms
            'workshop': [],  # Empty rooms
            'random': []  # Any room
        }

        # Collect rooms by type (iterate all levels)
        for z in range(self.dungeon.num_levels):
            # Add center room for this level
            center_x, center_y = self.dungeon.size // 2, self.dungeon.size // 2
            location_mapping['center'].append((center_x, center_y, z))

            # Add stairs rooms for this level
            stairs_x, stairs_y = self.dungeon.size - 1, self.dungeon.size - 1
            location_mapping['stairs'].append((stairs_x, stairs_y, z))

            for y in range(self.dungeon.size):
                for x in range(self.dungeon.size):
                    room = self.dungeon.get_room(x, y, z)

                    if room.type == RoomType.TREASURE:
                        location_mapping['storage'].append((x, y, z))
                    elif room.type == RoomType.EMPTY and not (x == 0 and y == 0 and z == 0):
                        location_mapping['workshop'].append((x, y, z))

                    # All rooms except starting room can be random
                    if not (x == 0 and y == 0 and z == 0):
                        location_mapping['random'].append((x, y, z))

        # Track assigned positions to avoid duplicates
        assigned_positions = set()

        # Distribute objects
        for obj in self.object_palette:
            suggested_loc = obj.get('suggested_location', 'random')

            # Get candidate positions
            candidates = location_mapping.get(suggested_loc, [])

            # Filter out already assigned
            candidates = [pos for pos in candidates if pos not in assigned_positions]

            if not candidates:
                # Fallback to random unassigned
                candidates = [pos for pos in location_mapping['random'] if pos not in assigned_positions]

            if candidates:
                # Pick random position from candidates
                x, y, z = random.choice(candidates)
                room = self.dungeon.get_room(x, y, z)

                # Assign object to room
                room.assigned_object = obj
                assigned_positions.add((x, y, z))

                # Generate a thematic item for this room (30% chance)
                from services.ai_service import get_ai_service
                ai = get_ai_service()
                item_data = ai.generate_room_item_for_object(obj, self.theme)

                if item_data:
                    # Create actual Item object
                    from models.items import Item, ItemType, ItemStats
                    import uuid

                    # Map type string to ItemType enum
                    type_mapping = {
                        'weapon': ItemType.WEAPON,
                        'armor': ItemType.ARMOR,
                        'consumable': ItemType.CONSUMABLE,
                        'accessory': ItemType.RING
                    }

                    # Normalize stat keys (AI might return 'intellect' instead of 'intelligence', 'speed' instead of 'dexterity')
                    # Only allow valid ItemStats fields
                    valid_stats = {'strength', 'dexterity', 'wisdom', 'intelligence', 'attack', 'defense', 'hp'}
                    raw_stats = item_data.get('stats', {})
                    normalized_stats = {}
                    for key, value in raw_stats.items():
                        # Map aliases to canonical names
                        if key == 'intellect':
                            key = 'intelligence'
                        elif key == 'speed':
                            key = 'dexterity'

                        # Only add if it's a valid stat
                        if key in valid_stats:
                            normalized_stats[key] = value

                    item = Item(
                        id=str(uuid.uuid4()),
                        name=item_data['name'],
                        description=item_data.get('special', ''),
                        type=type_mapping.get(item_data['type'], ItemType.CONSUMABLE),
                        stats=ItemStats(**normalized_stats)
                    )
                    room.loot.append(item)

    def save_game(self, slot: int = 1) -> None:
        """Save the current game."""
        theme_id = self.theme_config.id if self.theme_config else None
        success = self.save_manager.save_game(
            player_data=self.player.to_dict(),
            dungeon_data=self.dungeon.to_dict(),
            story_context=self.story_context,
            theme=self.theme,
            theme_id=theme_id,
            object_palette=self.object_palette,
            world_state_data=self.world_state.to_dict(),
            slot=slot
        )

        if success:
            self.add_log('system', f'💾 Spiel in Slot {slot} gespeichert!')
        else:
            self.add_log('error', f'❌ Speichern fehlgeschlagen!')

    def load_game(self, slot: int = 1) -> bool:
        """Load a game from slot."""
        save_data = self.save_manager.load_game(slot)

        if not save_data:
            self.add_log('error', f'❌ Kein Speicherstand in Slot {slot} gefunden!')
            return False

        try:
            # Restore player
            self.player = Player.from_dict(save_data['player'])

            # Restore dungeon
            self.dungeon = Dungeon.from_dict(save_data['dungeon'])

            # Restore context
            self.story_context = save_data['story_context']
            self.theme = save_data['theme']

            # Restore theme_config from theme_id
            theme_id = save_data.get('theme_id')
            if theme_id:
                from models.theme import THEME_CONFIGS
                self.theme_config = THEME_CONFIGS.get(theme_id)
            else:
                # Backwards compatibility: try to match by name
                from models.theme import get_theme_config
                self.theme_config = get_theme_config(self.theme)

            # Restore world state (optional, for backwards compatibility)
            from models.world_events import WorldState
            if 'world_state' in save_data:
                self.world_state = WorldState.from_dict(save_data['world_state'])
            else:
                self.world_state = WorldState()  # Fresh state for old saves

            # Restore object palette (optional, for backwards compatibility)
            if 'object_palette' in save_data:
                self.object_palette = save_data['object_palette']
            else:
                self.object_palette = []  # Empty for old saves

            # Set state
            self.state = GameState.EXPLORING

            self.add_log('system', f'💾 Spiel aus Slot {slot} geladen!')
            self.add_log('system', f'Willkommen zurück, {self.player.name}!')

            return True

        except Exception as e:
            self.add_log('error', f'❌ Fehler beim Laden: {e}')
            import traceback
            traceback.print_exc()
            return False

    def handle_death(self, death_cause: str = "Unknown") -> None:
        """Handle player death - create graveyard entry and preserve grimoire."""
        # Get death location
        room = self.dungeon.get_room(self.player.x, self.player.y, self.player.z)
        death_location = f"{room.type.value} ({self.player.x}, {self.player.y}) Ebene {self.player.z + 1}"

        # Create graveyard entry
        entry = GraveyardEntry(
            name=self.player.name,
            race=self.player.race,
            level=self.player.level,
            max_hp=self.player.max_hp,
            attack=self.player.attack,
            defense=self.player.defense,
            gold=self.player.gold,
            xp=self.player.xp,
            death_cause=death_cause,
            death_location=death_location,
            theme=self.theme,
            spells_discovered=len(self.player.grimoire.spells)
        )

        self.graveyard.add_entry(entry)

        # Preserve grimoire for next run
        self.preserved_grimoire = self.player.grimoire
        self.preserved_grimoire.reset_current_run()

        # Show death info
        self.add_log('error', f"💀 {self.player.name} ist gefallen...")
        self.add_log('error', f"   Ursache: {death_cause}")
        self.add_log('error', f"   Ort: {death_location}")
        self.add_log('error', f"   Level {self.player.level} | {self.player.gold} Gold verloren")

        if self.player.grimoire.spells:
            self.add_log('system', f"📖 Grimoire bewahrt: {len(self.player.grimoire.spells)} Zauber überleben den Tod!")

        self.add_log('system', 'Tippe (n)eu für neuen Char mit Grimoire, oder (q)uit zum Beenden.')

    def show_graveyard(self) -> None:
        """Show graveyard statistics and recent deaths."""
        stats = self.graveyard.get_stats()

        if stats['total_deaths'] == 0:
            self.add_log('system', '⚰️ Friedhof ist leer. Noch kein Abenteurer gefallen.')
            return

        self.add_log('system', '⚰️ === FRIEDHOF DER GEFALLENEN ===')
        self.add_log('system', f"   Gefallene Helden: {stats['total_deaths']}")
        self.add_log('system', f"   Höchstes Level: {stats['max_level']}")
        self.add_log('system', f"   Verlorenes Gold: {stats['total_gold_lost']}")
        self.add_log('system', f"   Häufigste Todesursache: {stats['most_common_cause']}")
        self.add_log('system', '')

        recent = self.graveyard.get_recent_entries(limit=5)
        if recent:
            self.add_log('system', 'Letzte Opfer:')
            for entry in recent:
                timestamp = entry.timestamp[:10]  # Just the date
                self.add_log('system', f"  💀 {entry.name} ({entry.race}) - Level {entry.level}")
                self.add_log('system', f"     {entry.death_cause} | {entry.death_location}")
                self.add_log('system', f"     {timestamp} | {entry.spells_discovered} Zauber entdeckt")


def main():
    """Entry point."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Check for API key
    if not os.getenv('API_KEY'):
        print("WARNUNG: API_KEY nicht gefunden in .env Datei!")
        print("AI-Features werden nicht funktionieren.")
        print()

    # Start game
    game = Game()
    try:
        game.start()
    except KeyboardInterrupt:
        print("\n\nSpiel beendet.")
    except Exception as e:
        print(f"\n\nFEHLER: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
