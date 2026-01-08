"""Exploration and movement mechanics."""

import random
import re
from models.game_state import GameState, RoomType
from models.door import Direction, DoorState


def _remove_monster_from_description(desc: str, monster_name: str = None) -> str:
    """
    Remove sentences mentioning a living monster from the description.

    Args:
        desc: Original room description
        monster_name: Name of the defeated monster (optional)

    Returns:
        Cleaned description without monster mentions
    """
    # Split into sentences (by . ! ?)
    sentences = re.split(r'(?<=[.!?])\s+', desc)

    # Active verbs that indicate a living creature
    active_verbs = [
        'lauert', 'bewacht', 'steht', 'sitzt', 'wartet', 'patroulliert',
        'beobachtet', 'schleicht', 'kämpft', 'droht', 'brüllt', 'knurrt',
        'hockt', 'lehnt', 'wandert', 'kreist', 'schnarcht', 'liegt... und atmet'
    ]

    # Monster keywords
    monster_keywords = [
        'krieger', 'goblin', 'skelett', 'ork', 'wächter', 'wache', 'bestie',
        'mumie', 'geist', 'zombie', 'spinne', 'wolf', 'ratte', 'schleim',
        'häuptling', 'schamane', 'kämpfer', 'späher', 'wache', 'gnom'
    ]

    # If we know the monster name, add it to keywords
    if monster_name:
        monster_keywords.append(monster_name.lower())

    cleaned_sentences = []
    for sentence in sentences:
        sentence_lower = sentence.lower()

        # Check if sentence mentions monster with active verb
        has_monster = any(keyword in sentence_lower for keyword in monster_keywords)
        has_active_verb = any(verb in sentence_lower for verb in active_verbs)

        # Keep sentence if it doesn't mention living monster
        if not (has_monster and has_active_verb):
            cleaned_sentences.append(sentence)

    return ' '.join(cleaned_sentences).strip()


def move_player(game, direction: str) -> None:
    """
    Move the player in a direction.

    Args:
        game: The Game instance
        direction: Direction to move (n, s, o, w)
    """
    # Calculate new position and door direction
    dx, dy = 0, 0
    door_dir = None

    if direction == 'n':
        dy = -1
        door_dir = Direction.NORTH
    elif direction == 's':
        dy = 1
        door_dir = Direction.SOUTH
    elif direction == 'o':
        dx = 1
        door_dir = Direction.EAST
    elif direction == 'w':
        dx = -1
        door_dir = Direction.WEST

    new_x = game.player.x + dx
    new_y = game.player.y + dy

    # Check bounds
    if new_x < 0 or new_x >= game.dungeon.size or new_y < 0 or new_y >= game.dungeon.size:
        game.add_log('error', 'Wand.')
        return

    # Check if there's a door in this direction and if it's locked
    current_room = game.dungeon.get_room(game.player.x, game.player.y, game.player.z)
    if door_dir and door_dir in current_room.doors:
        door = current_room.doors[door_dir]

        if door.state == DoorState.LOCKED:
            # Try to auto-unlock with key from inventory
            matching_key = None
            for item in game.player.inventory:
                if item.key_id == door.key_id:
                    matching_key = item
                    break

            if matching_key:
                # Auto-unlock the door!
                door.unlock(matching_key.key_id)
                game.add_log('system', f'🔓 Tür automatisch aufgeschlossen mit {matching_key.name}!')

                # Also unlock the mirror door in adjacent room
                mirror_dir = None
                if door_dir == Direction.NORTH:
                    mirror_dir = Direction.SOUTH
                elif door_dir == Direction.SOUTH:
                    mirror_dir = Direction.NORTH
                elif door_dir == Direction.EAST:
                    mirror_dir = Direction.WEST
                elif door_dir == Direction.WEST:
                    mirror_dir = Direction.EAST

                adjacent_room = game.dungeon.get_room(new_x, new_y, game.player.z)
                if adjacent_room and mirror_dir in adjacent_room.doors:
                    adjacent_room.doors[mirror_dir].unlock(matching_key.key_id)

                # Remove key from inventory
                game.player.inventory.remove(matching_key)

                # Door is now unlocked, continue with movement
            else:
                # No matching key found
                game.add_log('error', '🚪 Die Tür ist verschlossen. Du brauchst einen Schlüssel.')
                if door.key_id:
                    # Show hint about which key is needed
                    from constants import KEY_TEMPLATES
                    key_name = door.key_id
                    for key_template in KEY_TEMPLATES:
                        if key_template['key_id'] == door.key_id:
                            key_name = key_template['name']
                            break
                    game.add_log('system', f'Benötigt: {key_name}')
                return

    # Move player
    game.player.x = new_x
    game.player.y = new_y

    # Get the new room
    room = game.dungeon.get_room(new_x, new_y, game.player.z)

    # Mark as visited
    was_visited = room.visited
    room.visited = True

    # Check for quest objective: explore rooms
    if not was_visited and game.player.quest_manager:
        # Player just visited this room for first time
        result = game.player.quest_manager.find_quest_by_target(game.theme, 'explore')
        if result:
            quest, objective = result
            completed_obj = game.player.quest_manager.update_objective(quest.id, objective.id)
            if completed_obj:
                # Don't show for hidden objectives (auto-complete exploration)
                if not objective.hidden:
                    game.add_log('system', f"📜 Quest Ziel: {objective.description} ({objective.count_current}/{objective.count_required})")

                # Check if quest is fully completed
                if quest.completed:
                    game.add_log('system', f"🎉 QUEST ABGESCHLOSSEN: {quest.title}!")
                    game.add_log('system', f"Belohnung: +{quest.xp_reward} XP, +{quest.gold_reward} Gold")
                    game.player.xp += quest.xp_reward
                    game.player.gold += quest.gold_reward

                    if quest.special_reward:
                        game.add_log('system', f"🏆 Spezielle Belohnung: {quest.special_reward}")

    # Show description (generate on-the-fly if first visit)
    from services.ai_service import get_ai_service
    ai = get_ai_service()

    exits = game.dungeon.get_exits(new_x, new_y, game.player.z)

    # Visual separator with room coordinates and level
    separator = f"─────────── ({new_x},{new_y}) Ebene {game.player.z + 1}/{game.dungeon.num_levels} ───────────"
    game.add_log('system', separator)

    if ai.is_available():
        if was_visited and room.description:
            # RÜCKKEHR: Zeige gecachte Beschreibung
            desc = room.description

            # WICHTIG: Wenn Monster in Description erwähnt wurden aber jetzt tot sind, bereinigen
            monster_keywords = ['krieger', 'goblin', 'skelett', 'ork', 'wächter', 'wache', 'bestie',
                               'mumie', 'geist', 'zombie', 'spinne', 'wolf', 'ratte', 'schleim',
                               'häuptling', 'schamane']

            has_monster_mention = any(keyword in desc.lower() for keyword in monster_keywords)
            monster_dead = room.monster is None or (room.monster and room.monster.hp <= 0)

            if has_monster_mention and monster_dead:
                # Entferne Sätze über lebendes Monster
                desc = _remove_monster_from_description(desc, room.defeated_monster_name)

                # Füge spezifischen Hinweis auf besiegtes Monster hinzu
                if room.defeated_monster_name:
                    desc += f" Die Leiche des besiegten {room.defeated_monster_name}s liegt reglos am Boden."
                else:
                    desc += " Die Leichen der besiegten Gegner liegen reglos am Boden."

            game.add_log('narrative', desc)

            # Sehr kleine Chance (5%) auf eine Veränderung
            import random
            if random.random() < 0.05:
                game.start_loading("🔍 Etwas hat sich verändert...")
                try:
                    delta_desc = ai._generate_single_room_description(
                        room, exits, game.theme, game.story_context, is_return=True,
                        quest_manager=game.player.quest_manager
                    )
                    # Zeige die Veränderung zusätzlich
                    game.add_log('narrative', f"⚠️ Veränderung: {delta_desc}")
                finally:
                    game.stop_loading()
        else:
            # ERSTES MAL: Volle Beschreibung
            game.start_loading("🗺️ Erkunde Raum...")
            try:
                desc = ai._generate_single_room_description(
                    room, exits, game.theme, game.story_context, is_return=False,
                    quest_manager=game.player.quest_manager
                )
                room.description = desc  # Cache it!
                game.add_log('narrative', desc)
            finally:
                game.stop_loading()
    else:
        # Fallback ohne AI
        exit_str = ", ".join(exits)
        if was_visited and room.description:
            desc = room.description

            # Auch im Fallback: Monster-Sätze entfernen wenn tot
            if room.defeated_monster_name:
                desc = _remove_monster_from_description(desc, room.defeated_monster_name)
                desc += f" Die Leiche des besiegten {room.defeated_monster_name}s liegt reglos am Boden."

            game.add_log('narrative', desc)
        else:
            desc = f"Ein dunkler Raum. Ausgänge: {exit_str}."
            room.description = desc
            game.add_log('narrative', desc)

    # Check for HP regeneration gift
    if game.player.gift:
        secret_bonus = game.player.gift.get('secret_bonus', {})
        hp_regen = secret_bonus.get('hp_regen_per_room', 0)

        if hp_regen > 0 and game.player.hp < game.player.max_hp:
            old_hp = game.player.hp
            game.player.hp = min(game.player.max_hp, game.player.hp + hp_regen)
            healed = game.player.hp - old_hp

            if healed > 0:
                # Check if this is first discovery
                if not hasattr(game.player, '_gift_hp_regen_discovered'):
                    game.player._gift_hp_regen_discovered = True
                    gift = game.player.gift
                    discovery_hint = gift.get('discovery_hint', 'Etwas an dir ist... anders.')
                    game.add_log('system', f"🌟 GIFT ENTDECKT: {gift['name']}!")
                    game.add_log('narrative', discovery_hint)

                game.add_log('system', f"💚 Du regenerierst {healed} HP. ({game.player.hp}/{game.player.max_hp})")

    # Show available exits
    direction_names = {
        'Norden': 'n',
        'Süden': 's',
        'Osten': 'o',
        'Westen': 'w'
    }

    # Build exit string with door states
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
        if door_dir and door_dir in room.doors:
            door = room.doors[door_dir]
            if door.state == DoorState.LOCKED:
                exit_parts.append(f"{exit_name} 🔒")
            else:
                exit_parts.append(exit_name)
        else:
            exit_parts.append(exit_name)

    if exit_parts:
        game.add_log('system', f"🧭 Ausgänge: {', '.join(exit_parts)}")

    # Show loot in room
    if room.loot:
        loot_names = ", ".join([item.name for item in room.loot])
        game.add_log('system', f"💎 Hier liegt: {loot_names}")

    # Check for environmental hazards
    if room.hazard and not room.hazard_triggered:
        trigger_hazard(game, room)

    # Check for combat - but give player a chance to react first!
    # Roll for awareness if this is first encounter with monster
    if room.monster and room.monster.hp > 0:
        # Check if this is the first time encountering this monster
        if not hasattr(room.monster, 'unaware'):
            # Roll WIS check: Does monster notice player?
            from game.actions import DiceRoller
            wis_value = game.player.attributes.wisdom
            dc = 12  # Base DC for stealth on entry

            success, roll, total = DiceRoller.attribute_check(wis_value, dc)

            if success:
                # Player is stealthy - monster doesn't notice
                room.monster.unaware = True
                game.add_log('system', f"💤 {room.monster.name} hat dich nicht bemerkt! Du kannst einen Überraschungsangriff starten.")
            else:
                # Monster notices player
                room.monster.unaware = False
                game.state = GameState.ENCOUNTER
                game.add_log('error', f"⚠️ {room.monster.name} bemerkt deine Anwesenheit!")
                game.add_log('system', f"{room.monster.name} - HP: {room.monster.hp}/{room.monster.max_hp}")

                # Check if monster is humanoid (can be reasoned with)
                humanoid_types = ['ork', 'goblin', 'mensch', 'elf', 'zwerg', 'gnom', 'räuber', 'bandit', 'wache']
                is_humanoid = any(h_type in room.monster.name.lower() for h_type in humanoid_types)

                if is_humanoid:
                    game.add_log('system', "Optionen: (a)ngriff, (r)eden, (f)liehen")
                else:
                    game.add_log('system', "Optionen: (a)ngriff, (f)liehen")
        elif room.monster.unaware:
            # Monster is still unaware - hint to player
            game.add_log('system', f"💤 {room.monster.name} hat dich immer noch nicht bemerkt.")
        else:
            # Monster is aware - enter encounter
            game.state = GameState.ENCOUNTER
            game.add_log('error', f"⚠️ {room.monster.name} bemerkt deine Anwesenheit!")
            game.add_log('system', f"{room.monster.name} - HP: {room.monster.hp}/{room.monster.max_hp}")

            # Check if monster is humanoid (can be reasoned with)
            humanoid_types = ['ork', 'goblin', 'mensch', 'elf', 'zwerg', 'gnom', 'räuber', 'bandit', 'wache']
            is_humanoid = any(h_type in room.monster.name.lower() for h_type in humanoid_types)

            if is_humanoid:
                game.add_log('system', "Optionen: (a)ngriff, (r)eden, (f)liehen")
            else:
                game.add_log('system', "Optionen: (a)ngriff, (f)liehen")

    # Check for stairs - set a flag and ask the player
    if room.type == RoomType.STAIRS_DOWN:
        # Going down to a deeper level
        max_z = game.dungeon.num_levels - 1
        if game.player.z < max_z:
            game.add_log('system', '🪜 Eine Treppe führt hinab in die Tiefe.')
            game.add_log('system', 'Hinabsteigen? Tippe "j" für Ja, "n" für Nein.')
            game.pending_stairs_action = 'down'
        else:
            game.add_log('system', '🪜 Eine Treppe führt weiter hinab, aber du bist bereits auf der tiefsten Ebene.')
    elif room.type == RoomType.STAIRS_UP:
        # Going up to a higher level
        if game.player.z > 0:
            game.add_log('system', '🪜 Eine Treppe führt nach oben.')
            game.add_log('system', 'Hinaufsteigen? Tippe "j" für Ja, "n" für Nein.')
            game.pending_stairs_action = 'up'
        else:
            game.add_log('system', '🪜 Eine Treppe führt nach oben - der Ausgang aus dem Dungeon!')


def trigger_hazard(game, room) -> None:
    """
    Trigger an environmental hazard in the room.

    Args:
        game: The Game instance
        room: The Room with the hazard
    """
    from game.actions import DiceRoller

    hazard = room.hazard

    # Determine hazard difficulty and attribute based on hazard type
    # Most hazards use WIS (perception) or DEX (agility)
    hazard_lower = hazard.lower()

    # High-damage hazards
    high_damage_keywords = ['lava', 'sturz', 'einsturz', 'explosion', 'fallgrube mit spießen']
    # Medium-damage hazards
    medium_damage_keywords = ['gift', 'gas', 'falle', 'dornen', 'fluch', 'wächter']
    # Low-damage hazards (warnings/alarms)
    low_damage_keywords = ['alarm', 'trommel', 'wachposten']

    # Determine damage tier and damage type
    damage = 0
    dc = 12  # Default DC
    attribute = 'wisdom'  # Default attribute
    damage_type = None  # For resistances

    if any(keyword in hazard_lower for keyword in high_damage_keywords):
        damage = random.randint(8, 15)
        dc = 14
        if 'lava' in hazard_lower:
            attribute = 'dexterity'  # Need to dodge
            damage_type = 'fire'  # Lava does fire damage
        elif 'fallgrube' in hazard_lower:
            attribute = 'dexterity'
    elif any(keyword in hazard_lower for keyword in medium_damage_keywords):
        damage = random.randint(3, 8)
        dc = 12
        if 'falle' in hazard_lower or 'sandfalle' in hazard_lower:
            attribute = 'dexterity'
    elif any(keyword in hazard_lower for keyword in low_damage_keywords):
        damage = random.randint(1, 3)
        dc = 10
    else:
        # Generic hazard
        damage = random.randint(3, 8)
        dc = 12

    # Check for additional damage types
    if 'feuer' in hazard_lower or 'flamme' in hazard_lower or 'brand' in hazard_lower:
        damage_type = 'fire'
    elif 'eis' in hazard_lower or 'frost' in hazard_lower or 'kälte' in hazard_lower:
        damage_type = 'cold'

    # Get attribute value
    attr_value = getattr(game.player.attributes, attribute)

    # Make check
    success, roll, total = DiceRoller.attribute_check(attr_value, dc)

    # Calculate modifier for display
    attr_modifier = (attr_value - 10) // 2

    # Mark hazard as triggered
    room.hazard_triggered = True

    if success:
        # Avoided the hazard
        game.add_log('system', f"⚠️ {hazard}!")
        game.add_log('system', f"🎲 {attribute.upper()} Check: [{roll}] + {attr_modifier} = {total} vs DC {dc}", detail_level='verbose')
        game.add_log('system', f"✓ Du entkommst der Gefahr!")
    else:
        # Took damage
        game.add_log('error', f"💥 {hazard}!")
        game.add_log('system', f"🎲 {attribute.upper()} Check: [{roll}] + {attr_modifier} = {total} vs DC {dc}", detail_level='verbose')

        # Apply resistance if applicable
        from game.combat import apply_resistance
        final_damage = apply_resistance(game, damage, damage_type)

        game.add_log('error', f"✗ Du nimmst {final_damage} Schaden!")

        game.player.hp = max(0, game.player.hp - final_damage)

        # Check for death
        if game.player.hp <= 0:
            game.state = GameState.GAMEOVER
            game.handle_death(death_cause=f"Gestorben durch {hazard}")


def rest_player(game) -> None:
    """
    Attempt to rest and recover HP.

    Checks for nearby monsters and performs a WIS check for a safe rest.

    Args:
        game: The Game instance
    """
    from game.actions import DiceRoller

    current_room = game.dungeon.get_room(game.player.x, game.player.y, game.player.z)

    # Check if there's a monster in the current room
    if current_room.monster and current_room.monster.hp > 0:
        game.add_log('error', '⚔️ Du kannst nicht rasten, während ein Monster hier ist!')
        return

    # Check adjacent rooms for monsters
    # Directions: N, S, O, W
    adjacent_coords = [
        (game.player.x, game.player.y - 1, game.player.z),  # North
        (game.player.x, game.player.y + 1, game.player.z),  # South
        (game.player.x + 1, game.player.y, game.player.z),  # East
        (game.player.x - 1, game.player.y, game.player.z),  # West
    ]

    nearby_monsters = []
    for x, y, z in adjacent_coords:
        # Check bounds
        if 0 <= x < game.dungeon.size and 0 <= y < game.dungeon.size:
            adjacent_room = game.dungeon.get_room(x, y, z)
            if adjacent_room and adjacent_room.monster and adjacent_room.monster.hp > 0:
                nearby_monsters.append(adjacent_room.monster.name)

    # If monsters nearby, warn player
    if nearby_monsters:
        game.add_log('error', '🔊 Du hörst Monster in der Nähe...')
        game.add_log('narrative', 'Hier ist kein sicherer Platz zum Ausruhen. Die Schritte und Geräusche der Kreaturen lassen dich wachsam bleiben.')
        return

    # No monsters nearby - attempt rest
    game.add_log('system', '😴 Du suchst dir einen ruhigen Platz zum Rasten...')

    # WIS check for quality of rest (DC 10 - should usually succeed)
    dc = 10
    wis_value = game.player.attributes.wisdom
    success, roll, total = DiceRoller.attribute_check(wis_value, dc)

    wis_modifier = (wis_value - 10) // 2
    game.add_log('system', f"🎲 WIS Check: [{roll}] + {wis_modifier} = {total} vs DC {dc}", detail_level='verbose')

    if success:
        # Good rest - heal more HP
        con_modifier = (game.player.attributes.constitution - 10) // 2
        healing = random.randint(1, 8) + max(1, con_modifier)  # 1d8 + CON (min 1)

        old_hp = game.player.hp
        game.player.hp = min(game.player.max_hp, game.player.hp + healing)
        actual_healing = game.player.hp - old_hp

        game.add_log('system', f"✓ Du findest einen sicheren Platz und erholst dich.")
        game.add_log('system', f"💚 +{actual_healing} HP (gut erholt)")
        game.add_log('narrative', 'Du streckst dich aus, schließt die Augen und gönnst dir eine wohlverdiente Pause. Die Stille des Dungeons wiegt dich in einen kurzen, aber erholsamen Schlaf.')
    else:
        # Poor rest - heal less HP
        healing = random.randint(1, 4)  # 1d4 only

        old_hp = game.player.hp
        game.player.hp = min(game.player.max_hp, game.player.hp + healing)
        actual_healing = game.player.hp - old_hp

        game.add_log('system', f"✓ Du rastest, aber die Umgebung ist unruhig.")
        game.add_log('system', f"💚 +{actual_healing} HP (unbequem)")
        game.add_log('narrative', 'Der harte Boden und die bedrückende Atmosphäre machen es schwer, sich wirklich zu entspannen. Du erhältst nur wenig Erholung.')

    # Small XP for surviving/resting
    game.player.xp += 1

    if game.player.hp >= game.player.max_hp:
        game.add_log('system', '✨ Du bist vollständig erholt!')
