"""Autocomplete for CLI commands."""

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class GameCompleter(Completer):
    """Context-aware autocomplete for game commands."""

    def __init__(self, game):
        """Initialize with game instance for context."""
        self.game = game

    def get_completions(self, document: Document, complete_event):
        """Generate completions based on current game state and input."""
        text = document.text_before_cursor.lower()
        words = text.split()

        # Base commands (always available)
        base_commands = [
            ('hilfe', 'Zeige Hilfe'),
            ('help', 'Show help'),
            ('menu', 'Zurück zum Hauptmenü'),
            ('hauptmenü', 'Zurück zum Hauptmenü'),
            ('quit', 'Spiel beenden'),
            ('exit', 'Exit game'),
        ]

        # State-specific commands
        if hasattr(self.game, 'state'):
            from models.game_state import GameState

            if self.game.state == GameState.START:
                state_commands = [
                    ('neu', 'Neues Spiel starten'),
                    ('laden', 'Spiel laden'),
                    ('load', 'Load game'),
                    ('friedhof', 'Graveyard ansehen'),
                    ('graveyard', 'View graveyard'),
                ]

            elif self.game.state == GameState.THEME_SELECTION:
                state_commands = [
                    ('r', 'Zufällig wählen'),
                    ('random', 'Random theme'),
                    ('1', 'Theme 1'),
                    ('2', 'Theme 2'),
                    ('3', 'Theme 3'),
                    ('4', 'Theme 4'),
                    ('5', 'Theme 5'),
                    ('6', 'Theme 6'),
                    ('7', 'Theme 7'),
                    ('8', 'Theme 8'),
                ]

            elif self.game.state == GameState.CHARACTER_CREATION:
                state_commands = [
                    ('bestätigen', 'Attribute bestätigen'),
                    ('b', 'Bestätigen'),
                ]

            elif self.game.state == GameState.CONVERSATION:
                state_commands = [
                    ('tschüss', 'Gespräch beenden'),
                    ('bye', 'End conversation'),
                    ('exit', 'Gespräch verlassen'),
                ]

            elif self.game.state == GameState.EXPLORING:
                state_commands = [
                    ('n', 'Nord'),
                    ('norden', 'Nach Norden gehen'),
                    ('north', 'Go north'),
                    ('s', 'Süd'),
                    ('süden', 'Nach Süden gehen'),
                    ('süd', 'Nach Süden gehen'),
                    ('south', 'Go south'),
                    ('o', 'Ost'),
                    ('osten', 'Nach Osten gehen'),
                    ('ost', 'Nach Osten gehen'),
                    ('east', 'Go east'),
                    ('w', 'West'),
                    ('westen', 'Nach Westen gehen'),
                    ('west', 'Go west'),
                    ('inventar', 'Inventar anzeigen'),
                    ('i', 'Inventar'),
                    ('status', 'Status anzeigen'),
                    ('zauber', 'Zauber anzeigen'),
                    ('z', 'Zauber'),
                    ('rast', 'Ausruhen und HP regenerieren'),
                    ('rasten', 'Ausruhen'),
                    ('rest', 'Rest and recover HP'),
                    ('save', 'Spiel speichern'),
                    ('speichern', 'Spiel speichern'),
                ]

                # Add attack if monster present
                if hasattr(self.game, 'player') and hasattr(self.game, 'dungeon'):
                    room = self.game.dungeon.get_room(
                        self.game.player.x,
                        self.game.player.y,
                        self.game.player.z
                    )
                    if room and room.monster and room.monster.hp > 0:
                        state_commands.extend([
                            ('angriff', 'Monster angreifen'),
                            ('a', 'Angreifen'),
                        ])

                # Add item-based autocomplete
                if hasattr(self.game, 'player') and self.game.player.inventory:
                    for item in self.game.player.inventory:
                        state_commands.append(
                            (f"e {item.name.lower()}", f"{item.name} ausrüsten")
                        )

            elif self.game.state == GameState.ENCOUNTER:
                state_commands = [
                    ('angriff', 'Angreifen'),
                    ('a', 'Angreifen'),
                    ('schleichen', 'Schleichen'),
                    ('s', 'Schleichen'),
                    ('fliehen', 'Fliehen'),
                    ('f', 'Fliehen'),
                ]

                # Add talk option for humanoids
                if hasattr(self.game, 'player') and hasattr(self.game, 'dungeon'):
                    room = self.game.dungeon.get_room(
                        self.game.player.x,
                        self.game.player.y,
                        self.game.player.z
                    )
                    if room and room.monster:
                        humanoid_types = ['ork', 'goblin', 'mensch', 'elf', 'zwerg', 'gnom', 'räuber', 'bandit', 'wache']
                        is_humanoid = any(h_type in room.monster.name.lower() for h_type in humanoid_types)
                        if is_humanoid:
                            state_commands.extend([
                                ('reden', 'Mit Monster reden'),
                                ('r', 'Reden'),
                            ])

            elif self.game.state == GameState.COMBAT:
                state_commands = [
                    ('angriff', 'Angreifen'),
                    ('a', 'Angreifen'),
                    ('fliehen', 'Fliehen'),
                    ('f', 'Fliehen'),
                ]

            else:
                state_commands = []

        else:
            state_commands = []

        # Combine all commands
        all_commands = base_commands + state_commands

        # Filter based on current input
        for command, description in all_commands:
            if command.startswith(text):
                yield Completion(
                    command,
                    start_position=-len(text),
                    display=command,
                    display_meta=description
                )
