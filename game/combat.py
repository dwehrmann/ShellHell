"""Combat mechanics."""

from models.game_state import GameState


def apply_resistance(game, damage: int, damage_type: str = None) -> int:
    """
    Apply player's gift resistance to damage.

    Args:
        game: The Game instance
        damage: Raw damage amount
        damage_type: Type of damage ('fire', 'cold', etc.)

    Returns:
        Final damage after resistance
    """
    if not damage_type or not game.player.gift:
        return damage

    secret_bonus = game.player.gift.get('secret_bonus', {})
    resistance_key = f"{damage_type}_resistance"

    if resistance_key in secret_bonus:
        resistance = secret_bonus[resistance_key]
        reduced_damage = int(damage * (1 - resistance))

        # Check if this is first discovery
        discovery_attr = f'_gift_{damage_type}_resist_discovered'
        if not hasattr(game.player, discovery_attr):
            setattr(game.player, discovery_attr, True)
            gift = game.player.gift
            discovery_hint = gift.get('discovery_hint', 'Etwas an dir ist... anders.')
            game.add_log('system', f"🌟 GIFT ENTDECKT: {gift['name']}!")
            game.add_log('narrative', discovery_hint)

        game.add_log('system', f"🛡️ Resistenz! Schaden reduziert von {damage} auf {reduced_damage}")
        return reduced_damage

    return damage


def attack(game) -> None:
    """
    Player attacks the current monster.

    Args:
        game: The Game instance
    """
    from game.actions import DiceRoller

    room = game.dungeon.get_room(game.player.x, game.player.y, game.player.z)

    if not room or not room.monster:
        game.add_log('error', 'Kein Gegner hier.')
        return

    monster = room.monster

    # Check for backstab opportunity (unaware monster)
    is_backstab = hasattr(monster, 'unaware') and monster.unaware

    # Roll attack (DEX + STR)
    dex_mod = (game.player.attributes.dexterity - 10) // 2
    str_mod = (game.player.attributes.strength - 10) // 2

    attack_roll = DiceRoller.roll(20)

    # Backstab: Roll with advantage (2d20, take higher)
    if is_backstab:
        second_roll = DiceRoller.roll(20)
        game.add_log('system', f"🗡️ ÜBERRASCHUNGSANGRIFF! Vorteil: [{attack_roll}] vs [{second_roll}]", detail_level='verbose')
        attack_roll = max(attack_roll, second_roll)
        # Remove unaware status after first attack
        monster.unaware = False

    attack_total = attack_roll + dex_mod + str_mod

    # Check for critical hit (natural 20, or 19-20 with Glückskind gift)
    crit_range = 20  # Default: only natural 20
    if game.player.gift:
        secret_bonus = game.player.gift.get('secret_bonus', {})
        if 'crit_range' in secret_bonus:
            crit_range = secret_bonus['crit_range']

            # Check if this is first discovery (only trigger on actual crit)
            if attack_roll >= crit_range:
                if not hasattr(game.player, '_gift_crit_range_discovered'):
                    game.player._gift_crit_range_discovered = True
                    gift = game.player.gift
                    discovery_hint = gift.get('discovery_hint', 'Etwas an dir ist... anders.')
                    game.add_log('system', f"🌟 GIFT ENTDECKT: {gift['name']}!")
                    game.add_log('narrative', discovery_hint)

    is_crit = attack_roll >= crit_range

    # Monster's dodge DC (10 + DEX equivalent from monster stats)
    monster_dodge_dc = 10 + (monster.defense // 2)

    if is_crit:
        game.add_log('system', f"🎲 Angriff: [{attack_roll}] + {dex_mod + str_mod} = {attack_total} 💥 KRITISCH!", detail_level='verbose')
    else:
        game.add_log('system', f"🎲 Angriff: [{attack_roll}] + {dex_mod + str_mod} = {attack_total} vs DC {monster_dodge_dc}", detail_level='verbose')

    if attack_total < monster_dodge_dc and not is_crit:
        # Miss! (crits always hit)
        game.add_log('error', f"✗ Verfehlt! {monster.name} weicht aus.")
    else:
        # Hit! Roll damage
        base_damage = DiceRoller.roll(6)  # 1d6 base
        weapon_bonus = game.player.get_effective_attack()

        # Critical hits double the damage dice (not the bonuses)
        if is_crit:
            base_damage = DiceRoller.roll(6) + DiceRoller.roll(6)  # 2d6 on crit

        # Backstab: Add sneak attack damage (2d6)
        sneak_attack_damage = 0
        if is_backstab:
            sneak_attack_damage = DiceRoller.roll(6) + DiceRoller.roll(6)
            game.add_log('system', f"🗡️ SNEAK ATTACK: +{sneak_attack_damage} Bonusschaden!", detail_level='verbose')

        total_damage_roll = base_damage + weapon_bonus + sneak_attack_damage

        # Subtract monster's armor/defense
        damage_to_monster = max(1, total_damage_roll - monster.defense)

        if is_crit:
            game.add_log('system', f"⚔️ KRITISCHER SCHADEN: [{base_damage}] + {weapon_bonus} = {total_damage_roll}, nach Rüstung: {damage_to_monster}", detail_level='verbose')
        elif is_backstab:
            game.add_log('system', f"⚔️ BACKSTAB-SCHADEN: [{base_damage}] + {weapon_bonus} + [{sneak_attack_damage}] = {total_damage_roll}, nach Rüstung: {damage_to_monster}", detail_level='verbose')
        else:
            game.add_log('system', f"⚔️ Schaden: [{base_damage}] + {weapon_bonus} = {total_damage_roll}, nach Rüstung: {damage_to_monster}", detail_level='verbose')

        # Apply damage to monster
        monster.hp -= damage_to_monster
        game.add_log('system', f"✓ Treffer! {damage_to_monster} Schaden an {monster.name}.")

        # Check for weapon special effects (lifesteal, poison, etc.)
        equipped_weapon = game.player.equipment.get('weapon')
        if equipped_weapon and equipped_weapon.special_effects:
            # Poison damage (ignores armor!)
            poison_damage = equipped_weapon.special_effects.get('poison_damage', 0)
            if poison_damage > 0:
                monster.hp -= poison_damage
                game.add_log('system', f"☠️ Giftschaden: {poison_damage} (umgeht Rüstung)")

            # Lifesteal: Heal player for a portion of damage dealt
            lifesteal_percent = equipped_weapon.special_effects.get('lifesteal', 0)
            if lifesteal_percent > 0:
                lifesteal_amount = max(1, int(damage_to_monster * lifesteal_percent))

                if game.player.hp < game.player.max_hp:
                    old_hp = game.player.hp
                    game.player.hp = min(game.player.max_hp, game.player.hp + lifesteal_amount)
                    actual_heal = game.player.hp - old_hp
                    game.add_log('system', f"💚 Lifesteal: +{actual_heal} HP ({equipped_weapon.name})")

            # Fire damage (bonus elemental damage, ignores armor)
            fire_damage = equipped_weapon.special_effects.get('fire_damage', 0)
            if fire_damage > 0:
                monster.hp -= fire_damage
                game.add_log('system', f"🔥 Feuerschaden: {fire_damage} (umgeht Rüstung)")

            # Cold damage (bonus elemental damage, ignores armor)
            cold_damage = equipped_weapon.special_effects.get('cold_damage', 0)
            if cold_damage > 0:
                monster.hp -= cold_damage
                game.add_log('system', f"❄️ Kälteschaden: {cold_damage} (umgeht Rüstung)")

    # Check if monster is defeated
    if monster.hp <= 0:
        game.add_log('system', f"{monster.name} besiegt!")

        # Track world event for combat victory
        impact_level = "moderate" if monster.max_hp >= 25 else "minor"
        consequences = []

        if monster.max_hp >= 25:
            # Significant monster - add consequences
            consequences.append(f"Der Körper von {monster.name} liegt reglos im Raum")

        game.world_state.add_event(
            event_type="combat",
            description=f"{game.player.name} besiegte {monster.name} im Kampf",
            location=f"Raum ({room.x}, {room.y})",
            impact_level=impact_level,
            target=monster.name,
            consequences=consequences
        )

        # Reward
        gold_reward = 10 + (monster.max_hp // 2)
        xp_reward = monster.max_hp + monster.attack

        game.player.gold += gold_reward
        game.player.xp += xp_reward

        game.add_log('system', f"+{gold_reward} Gold, +{xp_reward} XP")

        # Roll for loot drop (theme-based)
        import random
        from constants import LOOT_DROP_CHANCE
        from game.loot import get_monster_loot

        if random.random() < LOOT_DROP_CHANCE:
            # Check if this was a boss monster
            is_boss = False
            if game.theme_config and game.theme_config.boss_monster:
                if monster.name == game.theme_config.boss_monster.get('name'):
                    is_boss = True

            # Get theme-based loot
            loot_item = get_monster_loot(game.theme_config, is_boss=is_boss)

            if loot_item:
                # Add to room loot
                room.loot.append(loot_item)
                game.add_log('system', f"💎 {monster.name} hat etwas fallen gelassen!")

        # Check for quest objective: kill target
        if game.player.quest_manager:
            result = game.player.quest_manager.find_quest_by_target(monster.name, 'kill')
            if result:
                quest, objective = result
                completed_obj = game.player.quest_manager.update_objective(quest.id, objective.id)
                if completed_obj:
                    game.add_log('system', f"📜 Quest Ziel: {objective.description} ({objective.count_current}/{objective.count_required})")

                    # Check if quest is fully completed
                    if quest.completed:
                        game.add_log('system', f"🎉 QUEST ABGESCHLOSSEN: {quest.title}!")
                        game.add_log('system', f"Belohnung: +{quest.xp_reward} XP, +{quest.gold_reward} Gold")
                        game.player.xp += quest.xp_reward
                        game.player.gold += quest.gold_reward

                        # TODO: Handle special rewards if any
                        if quest.special_reward:
                            game.add_log('system', f"🏆 Spezielle Belohnung: {quest.special_reward}")

        # Check for level up
        check_level_up(game)

        # Save monster name for room description updates
        room.defeated_monster_name = monster.name

        # Remove monster
        room.monster = None

        # Return to exploring
        game.state = GameState.EXPLORING
        return

    # Monster counter-attacks (only if still alive and player didn't kill it)
    if monster.hp > 0:
        # Monster rolls attack
        monster_roll = DiceRoller.roll(20)
        monster_attack_mod = (monster.attack - 10) // 2
        monster_total = monster_roll + monster_attack_mod

        # Player's dodge DC (10 + DEX mod)
        player_dodge_dc = 10 + dex_mod

        game.add_log('system', f"🎲 {monster.name} greift an: [{monster_roll}] + {monster_attack_mod} = {monster_total} vs DC {player_dodge_dc}", detail_level='verbose')

        if monster_total < player_dodge_dc:
            # Monster misses
            game.add_log('system', f"✓ Du weichst dem Angriff von {monster.name} aus!")
        else:
            # Monster hits! Roll damage
            base_monster_damage = DiceRoller.roll(6)
            monster_damage_total = base_monster_damage + monster.attack

            # Subtract player's armor
            player_defense = game.player.get_effective_defense()
            damage_to_player = max(1, monster_damage_total - player_defense)

            game.add_log('system', f"⚔️ Schaden: [{base_monster_damage}] + {monster.attack} = {monster_damage_total}, nach Rüstung: {damage_to_player}", detail_level='verbose')

            game.player.hp -= damage_to_player
            game.add_log('error', f"✗ {monster.name} trifft für {damage_to_player} Schaden.")

    # Apply curse damage from equipped cursed items
    curse_damage = game.player.apply_curse_damage()
    if curse_damage > 0:
        game.add_log('error', f"💀 Verfluchte Items: -{curse_damage} HP")

    # Check if player is dead
    if game.player.hp <= 0:
        game.player.hp = 0
        game.state = GameState.GAMEOVER
        # Handle death and create graveyard entry
        # Check if death was from curse
        if curse_damage > 0 and monster.hp > 0:
            game.handle_death(death_cause=f"Verflucht - gestorben durch verfluchte Ausrüstung")
        else:
            game.handle_death(death_cause=f"Besiegt von {monster.name}")


def check_level_up(game) -> None:
    """
    Check if player should level up.

    Args:
        game: The Game instance
    """
    # XP threshold: 100 * level^2
    xp_needed = 100 * (game.player.level ** 2)

    if game.player.xp >= xp_needed:
        game.player.level += 1
        game.player.xp -= xp_needed

        # Increase stats
        game.player.max_hp += 10
        game.player.hp = game.player.max_hp  # Full heal on level up
        game.player.attack += 2
        game.player.defense += 1

        game.add_log('system', f"LEVEL UP! Jetzt Level {game.player.level}")
        game.add_log('system', f"HP: +10, ATK: +2, DEF: +1")

        # TODO: Skill unlocks


def flee_combat(game) -> None:
    """
    Player attempts to flee from combat.

    Args:
        game: The Game instance
    """
    from game.actions import DiceRoller
    from models.game_state import GameState

    room = game.dungeon.get_room(game.player.x, game.player.y, game.player.z)

    if not room or not room.monster:
        game.add_log('error', 'Kein Gegner hier.')
        return

    monster = room.monster

    # DEX check to flee (DC = 10 + monster's defense/2)
    dex_mod = (game.player.attributes.dexterity - 10) // 2
    flee_dc = 10 + (monster.defense // 2)

    flee_roll = DiceRoller.roll(20)
    flee_total = flee_roll + dex_mod

    game.add_log('system', f"🎲 Flucht-Versuch (DEX): [{flee_roll}] + {dex_mod} = {flee_total} vs DC {flee_dc}", detail_level='verbose')

    if flee_total >= flee_dc:
        # Success! Flee to random adjacent room
        game.add_log('system', f"✓ Du entkommst {monster.name}!")

        # Find adjacent rooms
        adjacent_positions = []

        # North
        if game.player.y > 0:
            adjacent_positions.append((game.player.x, game.player.y - 1))
        # South
        if game.player.y < game.dungeon.size - 1:
            adjacent_positions.append((game.player.x, game.player.y + 1))
        # East
        if game.player.x < game.dungeon.size - 1:
            adjacent_positions.append((game.player.x + 1, game.player.y))
        # West
        if game.player.x > 0:
            adjacent_positions.append((game.player.x - 1, game.player.y))

        if adjacent_positions:
            import random
            new_x, new_y = random.choice(adjacent_positions)

            # Move player
            game.player.x = new_x
            game.player.y = new_y

            # Exit combat state
            game.state = GameState.EXPLORING

            # Show new room description
            new_room = game.dungeon.get_room(new_x, new_y, game.player.z)

            from services.ai_service import get_ai_service
            ai = get_ai_service()
            exits = game.dungeon.get_exits(new_x, new_y, game.player.z)

            separator = f"─────────── ({new_x},{new_y}) Ebene {game.player.z + 1}/{game.dungeon.num_levels} ───────────"
            game.add_log('system', separator)

            if new_room.description:
                game.add_log('narrative', new_room.description)
            else:
                if ai.is_available():
                    game.start_loading("🗺️ Erkunde Raum...")
                    try:
                        desc = ai._generate_single_room_description(
                            new_room, exits, game.theme, game.story_context, is_return=False,
                            quest_manager=game.player.quest_manager
                        )
                        new_room.description = desc
                        game.add_log('narrative', desc)
                    finally:
                        game.stop_loading()
                else:
                    game.add_log('narrative', f"Ein dunkler Raum. Ausgänge: {', '.join(exits)}.")

            # Show exits
            exit_parts = []
            for exit_name in exits:
                exit_parts.append(exit_name)
            if exit_parts:
                game.add_log('system', f"🧭 Ausgänge: {', '.join(exit_parts)}")

            # Check for new combat
            if new_room.monster and new_room.monster.hp > 0:
                game.state = GameState.COMBAT
                game.add_log('error', f"Kampf: {new_room.monster.name}!")
                game.add_log('system', f"{new_room.monster.name} - HP: {new_room.monster.hp}/{new_room.monster.max_hp}")
                game.add_log('system', "Befehle: (a)ngriff, (f)liehen")
        else:
            game.add_log('error', 'Keine angrenzenden Räume gefunden! Du bist eingeschlossen.')

    else:
        # Failed! Monster gets an opportunity attack with bonus damage
        game.add_log('error', f"✗ Flucht gescheitert! {monster.name} schlägt dich von hinten nieder!")

        # Monster makes opportunity attack (auto-hit with bonus damage)
        base_damage = DiceRoller.roll(6)
        bonus_damage = DiceRoller.roll(4)  # Extra 1d4 damage
        monster_damage_total = base_damage + bonus_damage + monster.attack

        # Subtract player's armor
        player_defense = game.player.get_effective_defense()
        damage_to_player = max(1, monster_damage_total - player_defense)

        game.add_log('system', f"⚔️ Gelegenheitsangriff: [{base_damage}+{bonus_damage}] + {monster.attack} = {monster_damage_total}, nach Rüstung: {damage_to_player}", detail_level='verbose')

        game.player.hp -= damage_to_player
        game.add_log('error', f"✗ Du nimmst {damage_to_player} Schaden!")

        # Check if player is dead
        if game.player.hp <= 0:
            game.player.hp = 0
            game.state = GameState.GAMEOVER
            game.handle_death(death_cause=f"Erschlagen auf der Flucht von {monster.name}")
