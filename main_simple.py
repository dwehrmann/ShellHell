"""Simple game loop without blessed for debugging."""

import sys
import os
import random
from pathlib import Path

from models.game_state import GameState, CreationStep
from models.player import Player
from models.dungeon import Dungeon
from constants import DUNGEON_SIZE


class SimpleGame:
    """Simple game controller without blessed."""

    def __init__(self):
        """Initialize the game."""
        self.state = GameState.START
        self.creation_step = CreationStep.ROLLING
        self.player = Player()
        self.dungeon = Dungeon(DUNGEON_SIZE)
        self.running = True

        # Story context
        self.theme = ""
        self.story_context = ""

        # Temporary state for character creation
        self.temp_attributes = None

    def start(self) -> None:
        """Start the game."""
        from services.ai_service import get_ai_service

        print("\n" + "="*60)
        print("SHELLHELL v0.7.2-sprint1-debug")
        print("="*60)
        print("\nGeneriere Dungeon...")

        # Pick theme
        from constants import THEMES
        self.theme = random.choice(THEMES)
        self.player.theme = self.theme

        # Generate dungeon layout
        self.dungeon.generate()

        # Get AI service
        ai = get_ai_service()

        # Generate plot
        if ai.is_available():
            print("⏳ Generiere Story-Hintergrund...")
            self.story_context = ai.generate_dungeon_plot(self.theme)
            print(f"✓ Thema: {self.theme}")
            print(f"   {self.story_context[:80]}...\n")
        else:
            self.story_context = self.theme
            print(f"⚠ AI nicht verfügbar - nutze Fallback-Texte\n")

        # Spawn monsters
        self.dungeon.spawn_monsters()

        print("\nTippe 'start' (s), um deine Reise zu beginnen.")

        self.main_loop()

    def main_loop(self) -> None:
        """Main game loop."""
        while self.running:
            # Get input
            print("\n" + "-"*60)
            command = input("$ ").strip()

            if not command:
                continue

            # Handle commands based on game state
            self.handle_command(command)

    def handle_command(self, command: str) -> None:
        """Handle a command based on current game state."""
        cmd = command.lower()

        if cmd in ['quit', 'exit', 'q']:
            self.running = False
            return

        if self.state == GameState.START:
            self.handle_start_command(cmd)
        elif self.state == GameState.CHARACTER_CREATION:
            self.handle_creation_command(cmd, command)
        elif self.state == GameState.EXPLORING:
            self.handle_exploring_command(cmd, command)
        elif self.state == GameState.COMBAT:
            self.handle_combat_command(cmd, command)
        elif self.state == GameState.GAMEOVER:
            print('Game Over. Tippe "quit" zum Beenden.')

    def handle_start_command(self, cmd: str) -> None:
        """Handle commands in START state."""
        if cmd in ['s', 'start']:
            from game.character_creation import roll_attributes
            self.temp_attributes = roll_attributes()
            self.state = GameState.CHARACTER_CREATION
            self.creation_step = CreationStep.ROLLING

            attrs = self.temp_attributes
            print("\nAttribute gewürfelt:")
            print(f"  STR: {attrs.strength}  DEX: {attrs.dexterity}  WIS: {attrs.wisdom}  INT: {attrs.intelligence}")
            print("\nBehalten? (b)estätigen oder neu würfeln (beliebige Taste)")

    def handle_creation_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in CHARACTER_CREATION state."""
        if self.creation_step == CreationStep.ROLLING:
            if cmd == 'b':
                self.player.attributes = self.temp_attributes
                self.creation_step = CreationStep.RACE
                print("\nWähle deine Rasse:")
                print("  (m)ensch  (o)rk  (e)lf  (h)albelf  (g)nom")
            else:
                self.handle_start_command('s')

        elif self.creation_step == CreationStep.RACE:
            from constants import get_race_by_key
            race = get_race_by_key(cmd)
            if race:
                self.player.race = race['name']
                self.creation_step = CreationStep.NAME
                print(f"\nName für deinen {race['name']}?")
            else:
                print('Ungültige Rasse.')

        elif self.creation_step == CreationStep.NAME:
            self.player.name = full_command
            self.state = GameState.EXPLORING
            print(f"\n{self.player.name} betritt den Dungeon...")
            print('Bewegung: (n)orden, (s)üden, (o)sten, (w)esten')
            print('Weitere Befehle: hilfe, inventar, status')

    def handle_exploring_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in EXPLORING state."""
        from game.exploration import move_player
        from game.actions import execute_free_action

        if cmd in ['n', 's', 'o', 'w']:
            move_player(self, cmd)
        elif cmd in ['hilfe', 'help', 'h']:
            print('Befehle: n/s/o/w (Bewegung), inventar (i), status, hilfe (h), quit')
            print('Oder versuche freie Aktionen: "untersuche wand", "hebe stein auf", etc.')
        elif cmd in ['inventar', 'i', 'inv']:
            self.show_inventory()
        elif cmd in ['status', 'stats']:
            self.show_status()
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
                    print(f"{item.name} angelegt.")
                else:
                    print(f"Kann {item.name} nicht anlegen.")
            else:
                print(f"Item nicht gefunden: {item_name}")
        else:
            # Free action
            print(f"\n[FREE ACTION] > {full_command}")
            execute_free_action(self, full_command)

    def handle_combat_command(self, cmd: str, full_command: str) -> None:
        """Handle commands in COMBAT state."""
        from game.combat import attack

        if cmd in ['a', 'angriff', 'attack']:
            attack(self)
        elif cmd in ['hilfe', 'help', 'h']:
            print('Kampf-Befehle: (a)ngriff, hilfe (h)')
        else:
            print(f'Unbekannter Kampf-Befehl: {full_command}')

    def show_inventory(self) -> None:
        """Show player inventory."""
        if not self.player.inventory:
            print('Inventar ist leer.')
        else:
            print('Inventar:')
            for item in self.player.inventory:
                equipped = " [ANGELEGT]" if item.equipped else ""
                print(f"  - {item.name}{equipped}")

    def show_status(self) -> None:
        """Show player status."""
        p = self.player
        print(f"{p.name} ({p.race}) - Level {p.level}")
        print(f"HP: {p.hp}/{p.max_hp}  Gold: {p.gold}  XP: {p.xp}")
        print(f"STR: {p.attributes.strength}  DEX: {p.attributes.dexterity}  WIS: {p.attributes.wisdom}  INT: {p.attributes.intelligence}")

    def add_log(self, log_type: str, text: str) -> None:
        """Add a log entry (just print for simple version)."""
        prefix = {
            'system': '[SYS]',
            'narrative': '[>>>]',
            'error': '[ERR]',
            'action': '[YOU]'
        }.get(log_type, '[   ]')

        print(f"{prefix} {text}")


def main():
    """Entry point."""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Start game
    game = SimpleGame()
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
