"""Save/Load system with checksums for integrity."""

import json
import hashlib
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime


class SaveManager:
    """Manages game saves with integrity checks."""

    def __init__(self, save_dir: Optional[Path] = None):
        """Initialize save manager."""
        if save_dir is None:
            # Use ~/.local/share/shellhell/saves/
            home = Path.home()
            save_dir = home / '.local' / 'share' / 'shellhell' / 'saves'

        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

    def _calculate_checksum(self, data: str) -> str:
        """Calculate SHA256 checksum of data."""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    def save_game(
        self,
        player_data: Dict[str, Any],
        dungeon_data: Dict[str, Any],
        story_context: str,
        theme: str,
        theme_id: Optional[str] = None,
        object_palette: Optional[List[Dict[str, Any]]] = None,
        world_state_data: Optional[Dict[str, Any]] = None,
        slot: int = 1
    ) -> bool:
        """
        Save game to a slot with checksum.

        Args:
            player_data: Serialized player dict
            dungeon_data: Serialized dungeon dict
            story_context: Story/plot context
            theme: Dungeon theme
            world_state_data: Serialized world state (events, flags)
            slot: Save slot (1-3)

        Returns:
            True if save successful
        """
        try:
            save_file = self.save_dir / f"save_{slot}.json"

            # Build save data
            save_data = {
                'version': '1.3',  # Bumped version for object_palette
                'timestamp': datetime.now().isoformat(),
                'player': player_data,
                'dungeon': dungeon_data,
                'story_context': story_context,
                'theme': theme,
                'theme_id': theme_id,  # Theme ID for restoring theme_config
                'object_palette': object_palette or [],  # Object palette for room descriptions
                'world_state': world_state_data or {}
            }

            # Serialize to JSON
            json_str = json.dumps(save_data, indent=2, ensure_ascii=False)

            # Calculate checksum
            checksum = self._calculate_checksum(json_str)

            # Add checksum to data
            save_data_with_checksum = {
                'checksum': checksum,
                'data': save_data
            }

            # Write to file
            final_json = json.dumps(save_data_with_checksum, indent=2, ensure_ascii=False)

            with open(save_file, 'w', encoding='utf-8') as f:
                f.write(final_json)

            return True

        except Exception as e:
            print(f"Save Error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_game(self, slot: int = 1) -> Optional[Dict[str, Any]]:
        """
        Load game from a slot with checksum verification.

        Args:
            slot: Save slot (1-3)

        Returns:
            Dict with player, dungeon, story_context, theme if successful
            None if load failed
        """
        try:
            save_file = self.save_dir / f"save_{slot}.json"

            if not save_file.exists():
                return None

            # Read file
            with open(save_file, 'r', encoding='utf-8') as f:
                save_data_with_checksum = json.load(f)

            # Extract data and checksum
            stored_checksum = save_data_with_checksum['checksum']
            save_data = save_data_with_checksum['data']

            # Verify checksum
            json_str = json.dumps(save_data, indent=2, ensure_ascii=False)
            calculated_checksum = self._calculate_checksum(json_str)

            if stored_checksum != calculated_checksum:
                print(f"⚠️ WARNUNG: Save-File {slot} ist korrupt (Checksum mismatch)!")
                print(f"Erwartet: {stored_checksum[:16]}...")
                print(f"Gefunden: {calculated_checksum[:16]}...")
                return None

            return save_data

        except Exception as e:
            print(f"Load Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def list_saves(self) -> Dict[int, Dict[str, Any]]:
        """
        List all available save slots with metadata.

        Returns:
            Dict mapping slot number to metadata (timestamp, player name, level)
        """
        saves = {}

        for slot in [1, 2, 3]:
            save_file = self.save_dir / f"save_{slot}.json"

            if save_file.exists():
                try:
                    with open(save_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    save_data = data.get('data', {})
                    player = save_data.get('player', {})

                    saves[slot] = {
                        'timestamp': save_data.get('timestamp', 'Unknown'),
                        'player_name': player.get('name', 'Unknown'),
                        'level': player.get('level', 1),
                        'hp': player.get('hp', 0),
                        'max_hp': player.get('max_hp', 0),
                        'theme': save_data.get('theme', 'Unknown')
                    }

                except Exception as e:
                    saves[slot] = {'error': str(e)}

        return saves

    def delete_save(self, slot: int) -> bool:
        """
        Delete a save slot.

        Args:
            slot: Save slot (1-3)

        Returns:
            True if deleted successfully
        """
        try:
            save_file = self.save_dir / f"save_{slot}.json"

            if save_file.exists():
                save_file.unlink()
                return True

            return False

        except Exception as e:
            print(f"Delete Error: {e}")
            return False
