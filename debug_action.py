#!/usr/bin/env python3
"""Debug script to test action execution with verbose output."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from models.player import Player, Attributes
from models.dungeon import Dungeon, Room, Monster
from models.game_state import RoomType
from constants import DUNGEON_SIZE

print("="*60)
print("DEBUG: Testing Free Action System")
print("="*60)

# Create a realistic game state
print("\n1. Creating player...")
player = Player()
player.name = "TestHero"
player.race = "Mensch"
player.theme = "Test Theme"
player.attributes = Attributes(strength=15, dexterity=12, wisdom=14, intelligence=10)
player.hp = 20
player.max_hp = 20
player.level = 1
player.xp = 0
player.gold = 10
print(f"   Player: {player.name}, Level {player.level}, HP {player.hp}/{player.max_hp}")

# Create dungeon
print("\n2. Creating dungeon...")
dungeon = Dungeon(DUNGEON_SIZE)
dungeon.generate()
dungeon.spawn_monsters()
print(f"   Dungeon size: {len(dungeon.levels[0])}x{len(dungeon.levels[0][0])}, {dungeon.num_levels} levels")

# Get starting room
print("\n3. Getting starting room...")
room = dungeon.get_room(player.x, player.y, player.z)
print(f"   Room type: {room.type.value}")
if room.monster:
    print(f"   Monster: {room.monster.name} (HP: {room.monster.hp})")
else:
    print("   No monster")

# Test action execution
print("\n4. Testing action: 'sprich die figur an'...")
print("-"*60)

# Import and test
from game.actions import ActionResolver

try:
    result = ActionResolver.resolve_free_action(
        action="sprich die figur an",
        player=player,
        room=room
    )

    print(f"\nResult:")
    print(f"  - Success: {result.get('success')}")
    print(f"  - Rejected: {result.get('rejected')}")

    if result.get('rejected'):
        print(f"  - Rejection Reason: {result.get('rejection_reason')}")
        print(f"\n  Intent that was rejected:")
        intent = result.get('intent', {})
        for key, value in intent.items():
            print(f"    - {key}: {value}")
    else:
        print(f"  - Attribute: {result.get('attribute')}")
        print(f"  - Plausibility: {result.get('plausibility')}")
        print(f"  - Difficulty: {result.get('difficulty')}")
        print(f"  - Roll: {result.get('roll')}")
        print(f"  - Total: {result.get('total')}")
        print(f"  - Impact: {result.get('impact')}")

except Exception as e:
    print(f"\n❌ EXCEPTION: {e}")
    print(f"   Type: {type(e).__name__}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("DEBUG: Test Complete")
print("="*60)
