"""Free action system with dice rolling and attribute checks."""

import random
from typing import Tuple, Dict, Any, Optional
from models.player import Player
from models.dungeon import Room


class DiceRoller:
    """Handles dice rolling and attribute checks."""

    @staticmethod
    def roll(sides: int = 20) -> int:
        """Roll a die."""
        return random.randint(1, sides)

    @staticmethod
    def d20() -> int:
        """Roll a d20."""
        return DiceRoller.roll(20)

    @staticmethod
    def attribute_check(
        attribute_value: int,
        difficulty: int = 10,
        advantage: bool = False,
        disadvantage: bool = False,
        gift_bonus: int = 0
    ) -> Tuple[bool, int, int]:
        """
        Perform an attribute check.

        Args:
            attribute_value: The attribute value (e.g., player.attributes.strength)
            difficulty: The DC (Difficulty Class)
            advantage: Roll twice, take higher
            disadvantage: Roll twice, take lower
            gift_bonus: Bonus from player's gift (e.g., +2 for Acrobat on DEX checks)

        Returns:
            Tuple of (success, roll, total)
        """
        roll1 = DiceRoller.d20()

        if advantage or disadvantage:
            roll2 = DiceRoller.d20()
            if advantage:
                roll = max(roll1, roll2)
            else:
                roll = min(roll1, roll2)
        else:
            roll = roll1

        # Calculate modifier from attribute (D&D style: (attr - 10) / 2)
        modifier = (attribute_value - 10) // 2
        total = roll + modifier + gift_bonus

        success = total >= difficulty
        return success, roll, total


class ActionValidator:
    """Validates player actions against physics and game rules."""

    # Actions that require special abilities/items
    FORBIDDEN_METHODS = [
        'teleport', 'fly', 'phase_through', 'time_travel',
        'summon', 'resurrect', 'omniscience', 'invincibility'
    ]

    @staticmethod
    def validate(intent: Dict[str, Any], player: Player, room: Room) -> Dict[str, Any]:
        """
        Validate an action intent from the LLM interpreter.

        Args:
            intent: The structured intent from LLM (action_type, target, method, etc.)
            player: The player object
            room: Current room

        Returns:
            Dictionary with 'allowed' (bool) and 'reason' (str) if denied
        """
        # If LLM already marked as invalid, respect that
        if not intent.get('valid', True):
            return {
                'allowed': False,
                'reason': intent.get('reason_if_invalid', 'INTERPRETER_REJECTION')
            }

        # Check plausibility threshold
        plausibility = intent.get('plausibility', 0.0)
        if plausibility < 0.1:
            return {
                'allowed': False,
                'reason': 'IMPLAUSIBLE'
            }

        # Check target existence (if targeting a monster or object)
        # Note: interact_object without target is valid (general room exploration)
        target = intent.get('target')
        if target and intent.get('action_type') in ['physical_attack', 'social', 'interact_object']:
            # Allow general exploration targets (always valid)
            exploration_targets = [
                'room', 'raum', 'environment', 'umgebung', 'self',
                'ausgänge', 'exits', 'ausgang', 'exit',
                'wände', 'walls', 'wand', 'wall',
                'boden', 'floor', 'decke', 'ceiling',
                'gegend', 'area', 'surroundings'
            ]

            # Check if monster exists
            if target.lower() not in exploration_targets:
                target_found = False

                # Check monster
                if room.monster and target.lower() in room.monster.name.lower():
                    target_found = True

                # Check room loot (items on the ground)
                if hasattr(room, 'loot') and room.loot:
                    for item in room.loot:
                        if target.lower() in item.name.lower():
                            target_found = True
                            break

                # Check player inventory
                if hasattr(player, 'inventory') and player.inventory:
                    for item in player.inventory:
                        if target.lower() in item.name.lower():
                            target_found = True
                            break

                # Check equipped items
                if hasattr(player, 'equipment') and player.equipment:
                    for slot, item in player.equipment.items():
                        if item and target.lower() in item.name.lower():
                            target_found = True
                            break

                # Check NPC in room (with fuzzy matching for declensions)
                if hasattr(room, 'npc') and room.npc and room.npc.alive:
                    target_lower = target.lower()
                    npc_name_lower = room.npc.name.lower()
                    npc_role_lower = room.npc.role.lower()

                    # Bidirectional substring match with stemming tolerance
                    # "gelehrten" should match "gelehrter", "priester" should match "priesters", etc.
                    def matches_with_declension(target_word, npc_word):
                        # Direct match
                        if target_word == npc_word:
                            return True
                        # Bidirectional substring (min 5 chars to avoid false positives)
                        if len(target_word) >= 5 and len(npc_word) >= 5:
                            # Check if one is substring of the other (handles gelehrten/gelehrter)
                            if target_word in npc_word or npc_word in target_word:
                                return True
                        return False

                    if matches_with_declension(target_lower, npc_name_lower) or matches_with_declension(target_lower, npc_role_lower):
                        target_found = True

                # Check assigned object from palette
                if hasattr(room, 'assigned_object') and room.assigned_object:
                    obj_name = room.assigned_object.get('name', '').lower()
                    target_lower = target.lower()

                    # Fuzzy match on object name
                    if obj_name in target_lower or target_lower in obj_name:
                        # Check if trying to TAKE the object
                        method_lower = intent.get('method', '').lower()
                        taking_keywords = ['nimm', 'nehm', 'take', 'grab', 'pick up', 'mitnehm', 'einsteck', 'pack']

                        is_taking = any(keyword in method_lower for keyword in taking_keywords)

                        if is_taking:
                            # Palette objects are fixed - but allow the action with a flag
                            # The narrator will decide if it can be taken (maybe with a skill check)
                            # Mark it for special handling
                            target_found = True
                            # We'll handle this specially in the action resolver
                        else:
                            # Other interactions are allowed
                            target_found = True

                # Check discovered objects (dynamically added by narrator)
                if hasattr(room, 'discovered_objects') and room.discovered_objects:
                    target_lower = target.lower()
                    for discovered_obj in room.discovered_objects:
                        discovered_lower = discovered_obj.lower()
                        # Fuzzy match on discovered object name
                        if discovered_lower in target_lower or target_lower in discovered_lower:
                            target_found = True
                            break

                # Check if target is mentioned in room description (anchor objects!)
                if hasattr(room, 'description') and room.description:
                    # First check if object was destroyed
                    if hasattr(room, 'destroyed_objects'):
                        target_lower = target.lower()
                        for destroyed in room.destroyed_objects:
                            if destroyed.lower() in target_lower or target_lower in destroyed.lower():
                                return {
                                    'allowed': False,
                                    'reason': f'OBJECT_DESTROYED: {target} ist irreparabel zerstört'
                                }

                    # Fuzzy match: check if key words appear in description
                    # Split on spaces AND hyphens for compound words like "Goblin-Sklave"
                    import re
                    target_words = [w for w in re.split(r'[\s\-]+', target.lower()) if len(w) > 3]  # Skip articles
                    desc_lower = room.description.lower()

                    # Match with stemming tolerance (sklaven → sklave)
                    # Check if any target word is contained in ANY word in description (substring match)
                    def word_matches(target_word, text):
                        # Check if target is substring of any word in text, or vice versa
                        text_words = re.split(r'[\s\-,.:;!?]+', text)
                        for text_word in text_words:
                            # Bidirectional substring match with min length 4
                            if len(target_word) >= 4 and len(text_word) >= 4:
                                if target_word in text_word or text_word in target_word:
                                    return True
                        return False

                    # If at least one significant word matches, it's an anchor object
                    if any(word_matches(word, desc_lower) for word in target_words):
                        # Check if player is trying to TAKE an anchor object
                        method_lower = intent.get('method', '').lower()
                        taking_keywords = ['nimm', 'nehm', 'take', 'grab', 'pick up', 'mitnehm', 'einsteck', 'pack']

                        is_taking = any(keyword in method_lower for keyword in taking_keywords)

                        if is_taking:
                            # BUT: If object is in room.loot, it's takeable (dropped item, not anchor)
                            is_loot_item = False
                            if hasattr(room, 'loot') and room.loot:
                                for item in room.loot:
                                    if target.lower() in item.name.lower():
                                        is_loot_item = True
                                        break

                            if not is_loot_item:
                                # Only HARD-BLOCK truly immovable objects (architecture, fixtures)
                                # Everything else gets passed to narrator for creative resolution
                                immovable_objects = [
                                    'altar', 'statue', 'wand', 'wall', 'mauer', 'boden', 'floor',
                                    'decke', 'ceiling', 'säule', 'column', 'pfeiler', 'pillar',
                                    'tür', 'door', 'tor', 'gate', 'treppe', 'stairs', 'leiter', 'ladder',
                                    'thron', 'throne', 'tisch', 'table', 'stuhl', 'chair',
                                    'sarkophag', 'sarcophagus', 'grab', 'grave', 'gruft', 'crypt',
                                    'brunnen', 'fountain', 'well', 'becken', 'basin', 'pool'
                                ]

                                is_truly_immovable = any(
                                    immov in target.lower() for immov in immovable_objects
                                )

                                if is_truly_immovable:
                                    # These objects are truly fixed - hard block
                                    return {
                                        'allowed': False,
                                        'reason': f'OBJECT_FIXED: {target} ist fest verbaut und kann nicht mitgenommen werden'
                                    }
                                # Otherwise: Allow action, narrator will handle it
                                # (e.g., "Mantel", "Kette", "Buch", "Schlüssel" etc. can potentially be taken)

                        # Other interactions (examine, use, etc.) are always allowed
                        target_found = True

                if not target_found:
                    return {
                        'allowed': False,
                        'reason': f'TARGET_NOT_PRESENT: {target}'
                    }

        # Check physics violations
        method = intent.get('method', '').lower()
        for forbidden in ActionValidator.FORBIDDEN_METHODS:
            if forbidden in method:
                if not ActionValidator.has_ability(player, forbidden):
                    return {
                        'allowed': False,
                        'reason': f'PHYSICS_VIOLATION: {forbidden}'
                    }

        # Check inventory requirements
        components_used = intent.get('components_used', [])
        if components_used:
            inventory_names = [item.name for item in player.inventory]
            for component in components_used:
                if component not in inventory_names:
                    return {
                        'allowed': False,
                        'reason': f'MISSING_COMPONENT: {component}'
                    }

        # All checks passed
        return {'allowed': True}

    @staticmethod
    def has_ability(player: Player, ability: str) -> bool:
        """
        Check if player has an item/ability enabling a forbidden action.

        Args:
            player: The player object
            ability: The ability name (e.g., 'fly', 'teleport')

        Returns:
            True if player has enabling item
        """
        # Check inventory for enabling items
        ability_items = {
            'fly': ['wings', 'levitation potion', 'flight spell'],
            'teleport': ['teleportation scroll', 'warp stone'],
            'phase_through': ['ethereal cloak', 'ghost potion']
        }

        enabling_items = ability_items.get(ability, [])
        inventory_names_lower = [item.name.lower() for item in player.inventory]

        for item in enabling_items:
            if item in inventory_names_lower:
                return True

        return False


class ActionResolver:
    """Resolves free-form player actions using LLM interpretation."""

    @staticmethod
    def get_gift_bonus(player, attribute_name: str) -> int:
        """
        Get gift bonus for a specific attribute check.

        Args:
            player: The player object
            attribute_name: Name of the attribute ('dexterity', 'wisdom', etc.)

        Returns:
            Bonus value (0 if no gift or no bonus for this attribute)
        """
        if not player.gift:
            return 0

        secret_bonus = player.gift.get('secret_bonus', {})

        # Check for attribute-specific bonuses
        bonus_key = f"{attribute_name}_rolls"
        if bonus_key in secret_bonus:
            return secret_bonus[bonus_key]

        return 0

    @staticmethod
    def determine_rewards(
        success: bool,
        roll_total: int,
        difficulty: int,
        plausibility: float = 0.5,
        action_type: str = None,
        action_text: str = None
    ) -> Dict[str, Any]:
        """
        Determine rewards based on check result.

        Args:
            success: Whether the check succeeded
            roll_total: The total roll result
            difficulty: The DC
            plausibility: Action plausibility (0.0-1.0)
            action_type: Type of action (to exclude social from gold rewards)
            action_text: The actual action text (to check for treasure keywords)

        Returns:
            Dictionary with hp, gold, xp, item
        """
        impact = {
            'hp': 0,
            'gold': 0,
            'xp': 0,
            'item': None
        }

        if success:
            # Success rewards
            margin = roll_total - difficulty

            # XP based on difficulty and INVERSE plausibility
            # Easy/obvious actions (high plausibility) give little/no XP
            # Creative/difficult actions (low plausibility) give more XP
            if plausibility >= 0.8:
                # Trivial action - no XP
                impact['xp'] = 0
            elif plausibility >= 0.6:
                # Easy action - minimal XP
                impact['xp'] = max(1, difficulty // 2)
            else:
                # Creative/risky action - good XP
                creativity_bonus = int((1.0 - plausibility) * 10)
                impact['xp'] = difficulty + (margin * 2) + creativity_bonus

            # Critical success (margin >= 10)
            # Gold ONLY for treasure-related actions (not every critical success)
            if margin >= 10 and action_type != 'social':
                # Check if action is treasure-related
                treasure_keywords = [
                    'schatz', 'treasure', 'gold', 'münz', 'coin', 'geld', 'money',
                    'plünder', 'loot', 'beute', 'wertsach', 'valuabl',
                    'durchsuch', 'search for', 'suche nach', 'finde', 'versteck', 'hidden',
                    'truhe', 'chest', 'kiste', 'box', 'schatzkammer', 'vault'
                ]
                is_treasure_action = False
                if action_text:
                    action_lower = action_text.lower()
                    # More specific matching to avoid false positives
                    # "durchsuche" = search thoroughly (treasure hunting)
                    # "suche nach" = search for (treasure hunting)
                    # NOT "untersuche" = examine (investigating)
                    is_treasure_action = any(keyword in action_lower for keyword in treasure_keywords)

                if is_treasure_action:
                    impact['gold'] = random.randint(5, 15)
                    # Small chance for item on critical success
                    if random.random() < 0.1:
                        # TODO: Generate item
                        pass

        else:
            # Failure consequences
            margin = difficulty - roll_total

            # HP loss on failure
            if margin >= 8:  # Gross failure (missed by 8+)
                # Severe consequences: traps, needles, cuts
                impact['hp'] = -random.randint(2, 5)
            elif margin >= 5:  # Moderate failure
                # Minor injuries
                impact['hp'] = -random.randint(1, 3)
            elif difficulty >= 14:  # Hard actions (even small failures hurt)
                impact['hp'] = -random.randint(1, margin // 2 + 1)

            # No XP for failure
            impact['xp'] = 0

        return impact

    @staticmethod
    def apply_spell_effect(spell: Any, player: Any, room: Any, target: str) -> Dict[str, Any]:
        """
        Apply the effect of a known spell.

        Args:
            spell: The Spell object from grimoire
            player: Player object
            room: Current room
            target: Target of the spell

        Returns:
            Impact dictionary with hp, gold, xp, item
        """
        import random

        # Base impact
        impact = {'hp': 0, 'gold': 0, 'xp': 1, 'item': None}  # Minimal XP for casting

        # Magnitude multipliers
        magnitude_mult = {
            'minor': 1.0,
            'moderate': 1.5,
            'major': 2.0
        }
        mult = magnitude_mult.get(spell.magnitude, 1.0)

        # Effect based on type
        if spell.effect_type == 'fire':
            # Fire damage to monster
            if room.monster and room.monster.hp > 0:
                damage = int(random.randint(5, 15) * mult)
                room.monster.hp -= damage
                impact['hp'] = 0  # No direct player HP change
                impact['xp'] = int(10 * mult)  # XP for damage
                # Note: Actual damage is applied to monster, narrator will describe
            else:
                impact['hp'] = -random.randint(1, 2)  # Backfire if no target

        elif spell.effect_type == 'ice':
            # Ice damage + slow/stun
            if room.monster and room.monster.hp > 0:
                damage = int(random.randint(3, 10) * mult)
                room.monster.hp -= damage
                room.monster.stunned = True  # Stun effect
                impact['xp'] = int(12 * mult)
            else:
                impact['hp'] = -random.randint(1, 2)

        elif spell.effect_type == 'lightning':
            # Lightning damage (high)
            if room.monster and room.monster.hp > 0:
                damage = int(random.randint(8, 20) * mult)
                room.monster.hp -= damage
                impact['xp'] = int(15 * mult)
            else:
                impact['hp'] = -random.randint(2, 4)  # Higher backfire

        elif spell.effect_type == 'heal':
            # Healing
            heal_amount = int(random.randint(10, 20) * mult)
            player.hp = min(player.max_hp, player.hp + heal_amount)
            impact['hp'] = heal_amount
            impact['xp'] = int(5 * mult)

        elif spell.effect_type == 'shield':
            # Defense buff
            from models.player import Buff
            buff_value = int(random.randint(3, 8) * mult)
            buff = Buff(name='Magic Shield', type='defense', value=buff_value, duration=3)
            player.buffs.append(buff)
            impact['xp'] = int(8 * mult)

        elif spell.effect_type == 'dark':
            # Dark magic - damage + debuff monster
            if room.monster and room.monster.hp > 0:
                damage = int(random.randint(6, 12) * mult)
                room.monster.hp -= damage
                room.monster.defense = max(0, room.monster.defense - 2)  # Reduce defense
                impact['xp'] = int(12 * mult)
            else:
                impact['hp'] = -random.randint(2, 5)  # Significant backfire

        elif spell.effect_type == 'light':
            # Light magic - reveal + small heal
            heal_amount = int(random.randint(5, 10) * mult)
            player.hp = min(player.max_hp, player.hp + heal_amount)
            impact['hp'] = heal_amount
            impact['xp'] = int(6 * mult)
            # TODO: Could reveal hidden keys in room

        else:
            # Unknown effect type - generic minor effect
            impact['xp'] = int(5 * mult)

        return impact

    @staticmethod
    def resolve_magic_attempt(
        action: str,
        intent: Dict[str, Any],
        player: Any,
        room: Any,
        ai_service: Any
    ) -> Dict[str, Any]:
        """
        Resolve a magic attempt using the magic evaluator.

        Args:
            action: The action text
            intent: The structured intent from interpreter
            player: The player object
            room: Current room
            ai_service: The AI service

        Returns:
            Dictionary with success, magic_data, spell_discovered, impact
        """
        components_used = intent.get('components_used', [])
        method = intent.get('method', '')
        target = intent.get('target', '')

        # Extract gesture and words from method
        # Method might be like: "gesture upward thrust, say 'ignis maxima'"
        gesture = method
        words = ""

        # Try to extract quoted words
        import re
        word_match = re.search(r'["\']([^"\']+)["\']', method)
        if word_match:
            words = word_match.group(1)

        # CHECK: Is this a known spell from the grimoire?
        known_spell = player.grimoire.find_spell(components_used, words)

        if known_spell:
            # CASTING A KNOWN SPELL - Higher success rate, guaranteed effect!
            # Boost plausibility for known spells
            plausibility = min(0.95, known_spell.plausibility + 0.2)  # +20% boost, max 95%
            difficulty = int(20 - (plausibility * 15))

            # Magic uses INTELLIGENCE
            attr_value = player.attributes.intelligence
            success, roll, total = DiceRoller.attribute_check(attr_value, difficulty)

            # Increment uses
            known_spell.uses += 1

            if success:
                # Apply spell effect based on type and magnitude
                spell_impact = ActionResolver.apply_spell_effect(
                    known_spell, player, room, target
                )

                return {
                    'success': True,
                    'magic_data': {
                        'spell_name': known_spell.name,
                        'effect_type': known_spell.effect_type,
                        'magnitude': known_spell.magnitude,
                        'is_valid_attempt': True,
                        'is_discovery': False,
                        'plausibility': plausibility
                    },
                    'spell_discovered': False,
                    'known_spell_cast': True,
                    'roll': roll,
                    'total': total,
                    'difficulty': difficulty,
                    'plausibility': plausibility,
                    'impact': spell_impact
                }
            else:
                # Failed to cast known spell
                return {
                    'success': False,
                    'magic_data': {
                        'spell_name': known_spell.name,
                        'effect_type': known_spell.effect_type,
                        'magnitude': known_spell.magnitude,
                        'is_valid_attempt': True,
                        'is_discovery': False,
                        'plausibility': plausibility
                    },
                    'spell_discovered': False,
                    'known_spell_cast': False,
                    'roll': roll,
                    'total': total,
                    'difficulty': difficulty,
                    'plausibility': plausibility,
                    'impact': {'hp': -random.randint(1, 3), 'gold': 0, 'xp': 0, 'item': None}  # Backfire
                }

        # NOT A KNOWN SPELL - Evaluate as new magic attempt
        # Evaluate magic with AI
        magic_data = ai_service.evaluate_magic(
            components=components_used,
            gesture=gesture,
            words=words,
            environment=room.description or room.type.value
        )

        if not magic_data or not magic_data.get('is_valid_attempt'):
            # Not a valid magic attempt
            return {
                'success': False,
                'magic_data': None,
                'spell_discovered': False,
                'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None}
            }

        # Use plausibility from magic evaluator
        plausibility = magic_data.get('plausibility', 0.1)

        # Convert to DC (same as regular actions)
        difficulty = int(20 - (plausibility * 15))

        # Magic uses INTELLIGENCE
        attr_value = player.attributes.intelligence

        # Perform check
        success, roll, total = DiceRoller.attribute_check(attr_value, difficulty)

        # Determine impact (magic attempts don't give gold on critical success)
        impact = ActionResolver.determine_rewards(
            success, total, difficulty, plausibility,
            action_text=action
        )

        # Check if spell is discovered
        spell_discovered = False
        if success and magic_data.get('is_discovery', False):
            from models.grimoire import Spell

            spell = Spell(
                name=magic_data['spell_name'],
                effect_type=magic_data['effect_type'],
                magnitude=magic_data['magnitude'],
                components=components_used,
                gesture=gesture,
                words=words,
                plausibility=plausibility,
                discovery_context=f"{room.type.value} - {player.level}"
            )

            spell_discovered = player.grimoire.add_spell(spell)

            # Check for moral consequences (dark magic)
            consequence = magic_data.get('consequence')
            if consequence == 'moral_corruption':
                karma_penalty = -15  # Dark magic corrupts
                player.adjust_morality(karma_penalty, f"Dunkle Magie: {spell.name}")

            # WICHTIG: Apply spell effect auch bei Entdeckung!
            # Der Zauber wirkt beim ersten Mal, nicht nur bei wiederholter Nutzung
            spell_impact = ActionResolver.apply_spell_effect(
                spell, player, room, target
            )
            # Merge mit existing impact (XP addieren, rest überschreiben wenn nicht 0)
            impact['xp'] += spell_impact['xp']
            if spell_impact['hp'] != 0:
                impact['hp'] = spell_impact['hp']
            if spell_impact['gold'] > 0:
                impact['gold'] = spell_impact['gold']
            if spell_impact.get('item'):
                impact['item'] = spell_impact['item']

        return {
            'success': success,
            'magic_data': magic_data,
            'spell_discovered': spell_discovered,
            'roll': roll,
            'total': total,
            'difficulty': difficulty,
            'plausibility': plausibility,
            'impact': impact
        }

    @staticmethod
    def _determine_target_location(target: str, player: Player, room: Room) -> str:
        """
        Determine where the target object is located.

        Args:
            target: The target name
            player: The player
            room: Current room

        Returns:
            'inventory', 'equipped', 'room', or 'environment'
        """
        if not target:
            return 'environment'

        target_lower = target.lower()

        # Check inventory
        for item in player.inventory:
            if target_lower in item.name.lower():
                return 'inventory'

        # Check equipped items
        for slot, item in player.equipment.items():
            if item and target_lower in item.name.lower():
                return 'equipped'

        # Check room loot
        if hasattr(room, 'loot') and room.loot:
            for item in room.loot:
                if target_lower in item.name.lower():
                    return 'room'

        # Check monster
        if room.monster and target_lower in room.monster.name.lower():
            return 'room'

        # Check NPC
        if hasattr(room, 'npc') and room.npc and room.npc.alive:
            if target_lower in room.npc.name.lower() or target_lower in room.npc.role.lower():
                return 'room'

        # Default: environment (walls, objects in description)
        return 'environment'

    @staticmethod
    def map_action_to_attribute(action_type: str, method: str) -> str:
        """
        Map action type and method to the most appropriate attribute.

        Args:
            action_type: The action type from LLM
            method: The method description

        Returns:
            Attribute name (strength, dexterity, wisdom, intelligence)
        """
        method_lower = method.lower()

        # Check method for attribute keywords
        if any(keyword in method_lower for keyword in ['force', 'break', 'smash', 'lift', 'push']):
            return 'strength'
        if any(keyword in method_lower for keyword in ['dodge', 'sneak', 'climb', 'jump', 'quick']):
            return 'dexterity'
        if any(keyword in method_lower for keyword in ['perceive', 'notice', 'sense', 'listen', 'spot']):
            return 'wisdom'
        if any(keyword in method_lower for keyword in ['investigate', 'recall', 'decipher', 'analyze']):
            return 'intelligence'

        # Fallback based on action type
        action_type_mapping = {
            'physical_attack': 'strength',
            'environment_action': 'strength',
            'move': 'dexterity',
            'interact_object': 'wisdom',
            'social': 'intelligence',
            'attempt_magic': 'intelligence',
            'use_item': 'wisdom',
            'equip': None  # No check needed - equipping is automatic
        }

        return action_type_mapping.get(action_type, 'wisdom')

    @staticmethod
    def _is_crafting_action(action: str, method: str) -> bool:
        """
        Check if the action is attempting to craft/create an item.

        Args:
            action: The full action string
            method: The method from interpreter

        Returns:
            True if this is a crafting action
        """
        crafting_keywords = [
            'baue', 'forme', 'erstelle', 'arbeite', 'fertige', 'schmiede',
            'konstruiere', 'bastle', 'zusammen', 'herstell',
            'craft', 'build', 'forge', 'create', 'make', 'assemble',
            'rüstung', 'waffe', 'dolch', 'schwert', 'schild', 'armor', 'weapon'
        ]

        action_lower = action.lower()
        method_lower = method.lower()

        return any(keyword in action_lower or keyword in method_lower for keyword in crafting_keywords)

    @staticmethod
    def _generate_crafted_item(action: str, room: 'Room', theme: str, ai_service) -> Optional['Item']:
        """
        Generate a crafted item using AI.

        Args:
            action: The crafting action
            room: Current room
            theme: Dungeon theme
            ai_service: AI service instance

        Returns:
            Item or None
        """
        import re

        # Extract materials mentioned in action and room description
        materials = []

        # Common material keywords
        material_keywords = [
            'holz', 'eisen', 'stahl', 'leder', 'fell', 'haut', 'metall', 'stein',
            'knochen', 'erz', 'splitter', 'schuppen', 'stoff', 'seil', 'kristall',
            'wood', 'iron', 'steel', 'leather', 'hide', 'metal', 'stone', 'bone',
            'ore', 'shard', 'scale', 'cloth', 'rope', 'crystal'
        ]

        # Extract from action
        for keyword in material_keywords:
            if keyword in action.lower():
                materials.append(keyword)

        # Extract from room description
        if room.description:
            for keyword in material_keywords:
                if keyword in room.description.lower():
                    if keyword not in materials:
                        materials.append(keyword)

        # Call AI to generate item
        crafted_item = ai_service.generate_crafted_item(
            action=action,
            materials_mentioned=materials,
            room_description=room.description or "Ein dunkler Raum",
            theme=theme
        )

        return crafted_item

    @staticmethod
    def resolve_free_action(
        action: str,
        player: Player,
        room: Room,
        game=None,
        ai_service=None
    ) -> Dict[str, Any]:
        """
        Resolve a free-form action using LLM interpreter.

        This method:
        1. Calls LLM interpreter to parse action into structured intent
        2. Validates intent with ActionValidator
        3. Determines attribute and rolls dice against plausibility
        4. Calculates impact (rewards/consequences)
        5. Returns context for the AI to narrate

        Args:
            action: The action text
            player: The player
            room: Current room
            ai_service: The AI service (optional, for testing)

        Returns:
            Dictionary with roll results and impact
        """
        # Step 1: LLM Interpretation
        if ai_service is None:
            from services.ai_service import get_ai_service
            ai_service = get_ai_service()

        intent = None
        if ai_service.is_available():
            try:
                # Get theme context from game
                theme_context = "Generic fantasy dungeon"
                if game:
                    if hasattr(game, 'story_context') and game.story_context:
                        theme_context = f"{game.theme}: {game.story_context}"
                    elif hasattr(game, 'theme'):
                        theme_context = game.theme

                intent = ai_service.interpret_action(action, player, room, theme_context)
            except Exception as e:
                print(f"LLM Interpreter Error: {e}")
                intent = None

        # Fallback if LLM not available or failed
        if not intent:
            intent = {
                'action_type': 'interact_object',
                'target': None,
                'method': action,
                'plausibility': 0.5,
                'valid': True,
                'reason_if_invalid': None,
                'components_used': []
            }

        # Step 2: Validation
        try:
            validation = ActionValidator.validate(intent, player, room)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'rejected': True,
                'rejection_reason': f'VALIDATION_ERROR: {type(e).__name__}: {str(e)}',
                'intent': intent,
                'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None},
                'context': {
                    'action': action,
                    'player_name': player.name if hasattr(player, 'name') else 'Unknown',
                    'player_race': player.race if hasattr(player, 'race') else 'Unknown',
                    'room_type': room.type.value if room else 'Unknown',
                    'room_description': room.description if room and hasattr(room, 'description') else 'Unknown',
                    'has_monster': room.monster is not None if room else False,
                    'monster_name': room.monster.name if room and room.monster else None,
                    'monster_alive': room.monster.hp > 0 if room and room.monster else False,
                    'monster_hp': room.monster.hp if room and room.monster else 0,
                    'is_treasure_room': room.type.value == 'TREASURE' if room else False,
                    'treasure_looted': room.looted if room and hasattr(room, 'looted') else False,
                    'room_loot': [item.name for item in room.loot] if room and hasattr(room, 'loot') else []
                }
            }

        if not validation['allowed']:
            # Action rejected by validator
            return {
                'success': False,
                'rejected': True,
                'rejection_reason': validation['reason'],
                'intent': intent,
                'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None},
                'context': {
                    'action': action,
                    'player_name': player.name,
                    'player_race': player.race,
                    'room_type': room.type.value,
                    'room_description': room.description,
                    'has_monster': room.monster is not None,
                    'monster_name': room.monster.name if room.monster else None,
                    'monster_alive': room.monster.hp > 0 if room.monster else False,
                    'monster_hp': room.monster.hp if room.monster else 0,
                    'is_treasure_room': room.type.value == 'TREASURE',
                    'treasure_looted': room.looted,
                    'room_loot': [item.name for item in room.loot] if hasattr(room, 'loot') else [],
                    'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                    'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                    'target_location': ActionResolver._determine_target_location(intent.get('target'), player, room)
                }
            }

        # SPECIAL CASE: Equip Item (no dice roll needed)
        if intent.get('action_type') == 'equip':
            target_name = intent.get('target', '').lower()

            # Find item in inventory
            target_item = None
            for item in player.inventory:
                if target_name in item.name.lower() or target_name in item.id.lower():
                    target_item = item
                    break

            if not target_item:
                return {
                    'success': False,
                    'rejected': True,
                    'rejection_reason': f"Du hast '{target_name}' nicht im Inventar.",
                    'intent': intent,
                    'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None},
                    'context': {
                        'action': action,
                        'player_name': player.name,
                        'player_race': player.race,
                        'room_type': room.type.value,
                        'room_description': room.description,
                        'has_monster': room.monster is not None,
                        'monster_name': room.monster.name if room.monster else None,
                        'monster_alive': room.monster.hp > 0 if room.monster else False,
                        'monster_hp': room.monster.hp if room.monster else 0,
                        'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                        'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                        'target_location': 'inventory'
                    }
                }

            # Check if item is equippable
            equippable_types = ['weapon', 'armor', 'ring', 'head']
            if target_item.type.value not in equippable_types:
                return {
                    'success': False,
                    'rejected': True,
                    'rejection_reason': f"{target_item.name} kann nicht angelegt werden (Typ: {target_item.type.value}).",
                    'intent': intent,
                    'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None},
                    'context': {
                        'action': action,
                        'player_name': player.name,
                        'player_race': player.race,
                        'room_type': room.type.value,
                        'room_description': room.description,
                        'has_monster': room.monster is not None,
                        'monster_name': room.monster.name if room.monster else None,
                        'monster_alive': room.monster.hp > 0 if room.monster else False,
                        'monster_hp': room.monster.hp if room.monster else 0,
                        'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                        'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                        'target_location': 'inventory'
                    }
                }

            # Check if trying to replace a cursed item
            slot = target_item.type.value
            current_item = player.equipment.get(slot)
            if current_item and current_item.is_curse:
                return {
                    'success': False,
                    'rejected': True,
                    'rejection_reason': f"💀 {current_item.name} ist verflucht und kann nicht abgelegt werden! Du brauchst einen Priester oder Einsiedler, um den Fluch zu brechen.",
                    'intent': intent,
                    'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None},
                    'context': {
                        'action': action,
                        'player_name': player.name,
                        'player_race': player.race,
                        'room_type': room.type.value,
                        'room_description': room.description,
                        'has_monster': room.monster is not None,
                        'monster_name': room.monster.name if room.monster else None,
                        'monster_alive': room.monster.hp > 0 if room.monster else False,
                        'monster_hp': room.monster.hp if room.monster else 0,
                        'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                        'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                        'target_location': 'inventory'
                    }
                }

            # Equip the item
            success = player.equip_item(target_item)

            if success:
                return {
                    'success': True,
                    'rejected': False,
                    'attribute': None,  # No attribute check for equipping
                    'attribute_value': 0,
                    'difficulty': 0,
                    'plausibility': 1.0,
                    'roll': 0,
                    'total': 0,
                    'intent': intent,
                    'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None},
                    'equipped_item': target_item,  # Add equipped item info
                    'context': {
                        'action': action,
                        'player_name': player.name,
                        'player_race': player.race,
                        'room_type': room.type.value,
                        'room_description': room.description,
                        'has_monster': room.monster is not None,
                        'monster_name': room.monster.name if room.monster else None,
                        'monster_alive': room.monster.hp > 0 if room.monster else False,
                        'monster_hp': room.monster.hp if room.monster else 0,
                        'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                        'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                        'target_location': 'inventory'
                    }
                }
            else:
                return {
                    'success': False,
                    'rejected': True,
                    'rejection_reason': f"Konnte {target_item.name} nicht anlegen.",
                    'intent': intent,
                    'impact': {'hp': 0, 'gold': 0, 'xp': 0, 'item': None},
                    'context': {
                        'action': action,
                        'player_name': player.name,
                        'player_race': player.race,
                        'room_type': room.type.value,
                        'room_description': room.description,
                        'has_monster': room.monster is not None,
                        'monster_name': room.monster.name if room.monster else None,
                        'monster_alive': room.monster.hp > 0 if room.monster else False,
                        'monster_hp': room.monster.hp if room.monster else 0,
                        'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                        'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                        'target_location': 'inventory'
                    }
                }

        # SPECIAL CASE: Magic Attempt
        if intent.get('action_type') == 'attempt_magic':
            magic_result = ActionResolver.resolve_magic_attempt(
                action, intent, player, room, ai_service
            )

            # Build magic result context
            return {
                'success': magic_result['success'],
                'rejected': False,
                'attribute': 'intelligence',
                'attribute_value': player.attributes.intelligence,
                'difficulty': magic_result.get('difficulty', 15),
                'plausibility': magic_result.get('plausibility', 0.1),
                'roll': magic_result.get('roll', 0),
                'total': magic_result.get('total', 0),
                'intent': intent,
                'impact': magic_result['impact'],
                'magic_data': magic_result['magic_data'],
                'spell_discovered': magic_result.get('spell_discovered', False),
                'known_spell_cast': magic_result.get('known_spell_cast', False),
                'context': {
                    'action': action,
                    'player_name': player.name,
                    'player_race': player.race,
                    'room_type': room.type.value,
                    'room_description': room.description,
                    'has_monster': room.monster is not None,
                    'monster_name': room.monster.name if room.monster else None,
                    'monster_alive': room.monster.hp > 0 if room.monster else False,
                    'monster_hp': room.monster.hp if room.monster else 0,
                    'is_treasure_room': room.type.value == 'TREASURE',
                    'treasure_looted': room.looted,
                    'room_loot': [item.name for item in room.loot] if hasattr(room, 'loot') else [],
                    'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                    'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                    'target_location': ActionResolver._determine_target_location(intent.get('target'), player, room)
                }
            }

        # Step 3: Determine attribute and roll
        attr_name = ActionResolver.map_action_to_attribute(
            intent['action_type'],
            intent['method']
        )
        attr_value = getattr(player.attributes, attr_name)

        # Convert plausibility (0.0-1.0) to DC (5-20)
        # High plausibility = low DC
        # plausibility 1.0 -> DC 5 (very easy)
        # plausibility 0.5 -> DC 12 (medium)
        # plausibility 0.1 -> DC 18 (very hard)
        plausibility = intent['plausibility']
        difficulty = int(20 - (plausibility * 15))  # Maps [0,1] -> [20,5]

        # Special case: Room searching should be harder
        action_lower = action.lower()
        search_keywords = ['untersuche', 'durchsuche', 'suche', 'inspect', 'search']
        is_searching = any(keyword in action_lower for keyword in search_keywords)

        if is_searching:
            # Minimum DC 12 for room searches (harder to find hidden things)
            difficulty = max(difficulty, 12)

        # Check for gift bonus
        gift_bonus = ActionResolver.get_gift_bonus(player, attr_name)

        # Perform check
        success, roll, total = DiceRoller.attribute_check(attr_value, difficulty, gift_bonus=gift_bonus)

        # Track if gift bonus was used (for discovery hint)
        gift_discovered = False
        if gift_bonus > 0 and player.gift:
            gift_discovered = True

        # Step 4: Determine impact
        impact = ActionResolver.determine_rewards(
            success, total, difficulty, plausibility,
            action_type=intent['action_type'],
            action_text=action
        )

        # Step 4b: Check for crafting/item creation
        if success and ActionResolver._is_crafting_action(action, intent['method']):
            # Player successfully crafted something!
            crafted_item = ActionResolver._generate_crafted_item(
                action, room, game.theme, ai_service
            )
            if crafted_item:
                impact['item'] = crafted_item

        # Step 4c: Check for taking objects from room description
        if success and intent['action_type'] == 'interact_object':
            method_lower = intent.get('method', '').lower()
            taking_keywords = ['nimm', 'nehm', 'take', 'grab', 'pick up', 'mitnehm', 'einsteck', 'pack']
            is_taking = any(keyword in method_lower for keyword in taking_keywords)

            if is_taking and intent.get('target'):
                target = intent['target']
                # Check if target is from room description (not already in loot)
                is_from_description = False

                if hasattr(room, 'description') and room.description:
                    import re
                    target_words = [w for w in re.split(r'[\s\-]+', target.lower()) if len(w) > 3]
                    desc_lower = room.description.lower()

                    # Check if target is mentioned in description
                    for word in target_words:
                        if word in desc_lower:
                            is_from_description = True
                            break

                # Also check assigned_object
                if hasattr(room, 'assigned_object') and room.assigned_object:
                    obj_name = room.assigned_object.get('name', '').lower()
                    if obj_name in target.lower() or target.lower() in obj_name:
                        is_from_description = True

                # Check if NOT already in loot
                is_loot_item = False
                if hasattr(room, 'loot') and room.loot:
                    for item in room.loot:
                        if target.lower() in item.name.lower():
                            is_loot_item = True
                            break

                # If taking object from description (not loot), generate item
                if is_from_description and not is_loot_item and not impact.get('item'):
                    # Generate item from description object
                    taken_item = ai_service.generate_crafted_item(
                        action=action,
                        materials_mentioned=[target],
                        room_description=room.description or "Ein dunkler Raum",
                        theme=game.theme
                    )
                    if taken_item:
                        impact['item'] = taken_item

        # Build result context
        result = {
            'success': success,
            'rejected': False,
            'attribute': attr_name,
            'attribute_value': attr_value,
            'difficulty': difficulty,
            'plausibility': plausibility,
            'roll': roll,
            'total': total,
            'intent': intent,
            'impact': impact,
            'gift_discovered': gift_discovered,
            'gift_bonus': gift_bonus,
            # Context for AI narration
            'context': {
                'action': action,
                'player_name': player.name,
                'player_race': player.race,
                'room_type': room.type.value,
                'room_description': room.description,
                'has_monster': room.monster is not None,
                'monster_name': room.monster.name if room.monster else None,
                'monster_alive': room.monster.hp > 0 if room.monster else False,
                'monster_hp': room.monster.hp if room.monster else 0,
                'is_treasure_room': room.type.value == 'TREASURE',
                'treasure_looted': room.looted,
                'player_inventory': [item.name for item in player.inventory] if player.inventory else [],
                'player_equipped': {slot: item.name for slot, item in player.equipment.items() if item},
                'target_location': ActionResolver._determine_target_location(intent.get('target'), player, room)
            }
        }

        return result


def _execute_npc_actions(game, room, actions: list) -> None:
    """
    Execute actions performed by an NPC.

    Args:
        game: The Game instance
        room: Current room with NPC
        actions: List of action dicts from NPC response
    """
    from models.items import Item, ItemType, ItemStats
    from models.game_state import GameState
    from models.door import DoorState, Direction

    for action in actions:
        action_type = action.get('type')
        value = action.get('value')

        if action_type == 'heal':
            # NPC heals the player
            heal_amount = int(value) if isinstance(value, (int, float)) else 20
            old_hp = game.player.hp
            game.player.hp = min(game.player.max_hp, game.player.hp + heal_amount)
            actual_heal = game.player.hp - old_hp

            if actual_heal > 0:
                game.add_log('system', f"💚 {room.npc.name} heilt dich für {actual_heal} HP!")
            else:
                game.add_log('system', f"{room.npc.name} legt dir die Hand auf, aber du bist bereits vollständig geheilt.")

        elif action_type == 'give_item':
            # NPC gives player an item
            item_desc = str(value)

            # Parse simple item format like "Heiltrank (HP +15)"
            import re
            hp_match = re.search(r'HP \+(\d+)', item_desc, re.IGNORECASE)
            atk_match = re.search(r'ATK \+(\d+)', item_desc, re.IGNORECASE)
            def_match = re.search(r'DEF \+(\d+)', item_desc, re.IGNORECASE)

            # Determine item type and stats
            item_name = item_desc.split('(')[0].strip()
            item_stats = ItemStats()

            if hp_match:
                item_stats.hp = int(hp_match.group(1))
                item_type = ItemType.CONSUMABLE
            elif atk_match:
                item_stats.attack = int(atk_match.group(1))
                item_type = ItemType.WEAPON
            elif def_match:
                item_stats.defense = int(def_match.group(1))
                item_type = ItemType.ARMOR
            else:
                item_type = ItemType.MATERIAL

            given_item = Item(
                id=f"npc_gift_{item_name.lower().replace(' ', '_')}",
                name=item_name,
                description=f"Ein Geschenk von {room.npc.name}.",
                type=item_type,
                stats=item_stats
            )

            game.player.inventory.append(given_item)
            game.add_log('system', f"🎁 {room.npc.name} gibt dir: {given_item.name}")

        elif action_type == 'call_guards':
            # NPC calls guards - spawn enemy in room!
            count = int(value) if isinstance(value, (int, float)) else 1
            game.add_log('error', f"⚠️ {room.npc.name} ruft nach Wachen!")

            # Spawn guard(s) as monster
            from models.dungeon import Monster
            guard_template = {
                'name': 'Wache',
                'hp': 25,
                'attack': 6,
                'defense': 4
            }

            if not room.monster or room.monster.hp <= 0:
                # Spawn new guard
                room.monster = Monster.from_template(guard_template)
                game.add_log('error', f"🛡️ Eine Wache erscheint!")
                game.state = GameState.COMBAT
            else:
                # Boost existing monster
                room.monster.hp += 15
                room.monster.attack += 2
                game.add_log('error', f"🛡️ Verstärkung ist eingetroffen! {room.monster.name} wird stärker!")

        elif action_type == 'unlock_door':
            # NPC unlocks a door
            direction_str = str(value).lower()
            door_dir = None

            # Parse direction
            if 'n' in direction_str or 'north' in direction_str:
                door_dir = Direction.NORTH
            elif 's' in direction_str or 'south' in direction_str:
                door_dir = Direction.SOUTH
            elif 'o' in direction_str or 'east' in direction_str:
                door_dir = Direction.EAST
            elif 'w' in direction_str or 'west' in direction_str:
                door_dir = Direction.WEST

            if door_dir and door_dir in room.doors:
                door = room.doors[door_dir]
                if door.state == DoorState.LOCKED:
                    door.state = DoorState.OPEN
                    game.add_log('system', f"🔓 {room.npc.name} öffnet die Tür nach {direction_str}!")
                else:
                    game.add_log('system', f"{room.npc.name} zeigt auf die bereits offene Tür.")
            else:
                game.add_log('system', f"{room.npc.name} deutet in eine Richtung, aber dort ist keine Tür.")

        elif action_type == 'reveal_secret':
            # NPC reveals a secret
            secret = str(value)
            game.add_log('narrative', f"🔍 {room.npc.name} enthüllt ein Geheimnis: {secret}")

            # Small XP bonus for discovering secrets
            game.player.xp += 5
            game.add_log('system', '+5 XP (Geheimnis entdeckt)')

        elif action_type == 'uncurse':
            # NPC removes curse from equipped item
            # Value format: "item_slot" or "item_name" or "cost:100"
            cost = 0
            item_to_uncurse = None

            # Parse value for cost
            value_str = str(value) if value else ""
            if 'cost:' in value_str:
                parts = value_str.split('cost:')
                if len(parts) > 1:
                    try:
                        cost = int(parts[1].strip())
                    except:
                        cost = 50  # Default cost

            # Find cursed equipped item
            for slot, item in game.player.equipment.items():
                if item and item.is_curse:
                    item_to_uncurse = item
                    break

            if not item_to_uncurse:
                game.add_log('system', f"{room.npc.name}: Ich sehe keinen Fluch an deiner Ausrüstung.")
                return

            # Check if player can afford
            if cost > 0:
                if game.player.gold < cost:
                    game.add_log('error', f"{room.npc.name}: Der Fluchbruch kostet {cost} Gold. Du hast nicht genug.")
                    return
                else:
                    game.player.gold -= cost
                    game.add_log('system', f"-{cost} Gold")

            # Remove curse
            success = game.player.uncurse_item(item_to_uncurse)
            if success:
                game.add_log('system', f"✨ {room.npc.name} entfernt den Fluch von {item_to_uncurse.name}!")
                game.add_log('narrative', f"{room.npc.name} murmelt alte Worte und zeichnet Symbole in die Luft. Ein schwarzer Rauch löst sich von {item_to_uncurse.name} und verflüchtigt sich.")
            else:
                game.add_log('error', f"{room.npc.name}: Seltsam, der Fluch lässt sich nicht lösen...")


def _handle_door_action(game, room, action_lower: str) -> bool:
    """
    Handle door opening/unlocking actions directly.

    Args:
        game: The Game instance
        room: Current room
        action_lower: Lowercase action string

    Returns:
        True if door action was handled, False if not applicable
    """
    from models.door import Direction, DoorState

    # Determine which direction door the player wants to open
    direction_map = {
        'nord': Direction.NORTH,
        'north': Direction.NORTH,
        'süd': Direction.SOUTH,
        'south': Direction.SOUTH,
        'ost': Direction.EAST,
        'east': Direction.EAST,
        'west': Direction.WEST,
        'westen': Direction.WEST
    }

    target_direction = None
    for keyword, direction in direction_map.items():
        if keyword in action_lower:
            target_direction = direction
            break

    # If no direction specified, try to find a locked door
    if not target_direction:
        for direction, door in room.doors.items():
            if door.state == DoorState.LOCKED:
                target_direction = direction
                break

    # If still no door found, return False (not a valid door action)
    if not target_direction or target_direction not in room.doors:
        return False

    door = room.doors[target_direction]

    if door.state == DoorState.LOCKED:
        # Try to unlock with key from inventory
        matching_key = None

        # First try to find key by key_id (direct match)
        for item in game.player.inventory:
            if item.key_id == door.key_id:
                matching_key = item
                break

        # If not found, check if player mentioned a key name in the action
        if not matching_key:
            for item in game.player.inventory:
                if item.key_id and item.name.lower() in action_lower:
                    # Check if this key matches the door
                    if item.key_id == door.key_id:
                        matching_key = item
                        break

        if matching_key:
            # Unlock door!
            door.unlock(matching_key.key_id)
            game.add_log('system', f"🔓 Tür aufgeschlossen mit {matching_key.name}!")

            # Also unlock the mirror door in adjacent room
            dx, dy = 0, 0
            mirror_dir = None

            if target_direction == Direction.NORTH:
                dy = -1
                mirror_dir = Direction.SOUTH
            elif target_direction == Direction.SOUTH:
                dy = 1
                mirror_dir = Direction.NORTH
            elif target_direction == Direction.EAST:
                dx = 1
                mirror_dir = Direction.WEST
            elif target_direction == Direction.WEST:
                dx = -1
                mirror_dir = Direction.EAST

            adjacent_room = game.dungeon.get_room(game.player.x + dx, game.player.y + dy, game.player.z)
            if adjacent_room and mirror_dir in adjacent_room.doors:
                adjacent_room.doors[mirror_dir].unlock(matching_key.key_id)

            # Remove key from inventory (consumed)
            game.player.inventory.remove(matching_key)
        else:
            # Find the key name for better error message
            from constants import KEY_TEMPLATES
            key_name = door.key_id
            for key_template in KEY_TEMPLATES:
                if key_template['key_id'] == door.key_id:
                    key_name = key_template['name']
                    break

            game.add_log('error', f"🔒 Du hast nicht den richtigen Schlüssel. Benötigt: {key_name}")

        return True  # Door action was handled

    elif door.state == DoorState.CLOSED:
        door.open()
        game.add_log('system', "🚪 Tür geöffnet.")
        return True

    else:
        game.add_log('system', "Die Tür ist bereits offen.")
        return True


def execute_free_action(game, action: str) -> None:
    """
    Execute a free-form action in the game.

    Args:
        game: The Game instance
        action: The action string
    """
    from services.ai_service import get_ai_service

    game.add_log('action', f"> {action}")

    # Get current room
    room = game.dungeon.get_room(game.player.x, game.player.y, game.player.z)

    # SPECIAL HANDLING: Door opening/unlocking (bypass LLM for deterministic door actions)
    action_lower = action.lower()
    door_keywords = ['tür', 'door', 'unlock', 'aufschließ', 'öffne', 'open']
    has_door_keyword = any(keyword in action_lower for keyword in door_keywords)

    if has_door_keyword:
        # Check if not a chest action
        chest_keywords = ['truhe', 'kiste', 'schatzkiste', 'chest']
        is_chest_action = any(keyword in action_lower for keyword in chest_keywords)

        if not is_chest_action:
            # Try to handle door directly
            handled = _handle_door_action(game, room, action_lower)
            if handled:  # Door action was handled
                return

    # Resolve the action (dice rolling, etc.)
    try:
        result = ActionResolver.resolve_free_action(action, game.player, room, game)
    except Exception as e:
        game.add_log('error', f"Fehler bei Action Resolution: {e}")
        import traceback
        traceback.print_exc()
        return

    # Check if action was rejected
    if result.get('rejected', False):
        reason = result['rejection_reason']
        game.add_log('error', f"❌ Aktion abgelehnt: {reason}")

        # Provide helpful feedback
        if reason.startswith('TARGET_NOT_PRESENT'):
            game.add_log('system', "Dieses Ziel ist hier nicht vorhanden.")
        elif reason.startswith('OBJECT_DESTROYED'):
            game.add_log('system', "Das Objekt ist durch deine Fehlversuche zerstört worden.")
        elif reason.startswith('PHYSICS_VIOLATION'):
            game.add_log('system', "Das verstößt gegen die Naturgesetze (fehlendes Item?).")
        elif reason.startswith('MISSING_COMPONENT'):
            game.add_log('system', "Dir fehlt eine benötigte Komponente.")
        elif reason == 'IMPLAUSIBLE':
            game.add_log('system', "Diese Aktion ist schlicht unmöglich.")
        elif reason == 'INTERPRETER_REJECTION':
            invalid_reason = result['intent'].get('reason_if_invalid', 'Unbekannt')
            game.add_log('system', f"Grund: {invalid_reason}")

        return

    # Log interpreter analysis
    intent = result.get('intent', {})
    action_type = intent.get('action_type', 'unknown')
    plausibility = result.get('plausibility', 0.5)

    # SPECIAL HANDLING: Equip action (no dice roll)
    if action_type == 'equip':
        if result['success']:
            equipped_item = result.get('equipped_item')
            if equipped_item:
                # Show equipped item with stats
                stats_parts = []
                if equipped_item.stats.attack > 0:
                    stats_parts.append(f"+{equipped_item.stats.attack} ATK")
                if equipped_item.stats.defense > 0:
                    stats_parts.append(f"+{equipped_item.stats.defense} DEF")
                if equipped_item.stats.strength > 0:
                    stats_parts.append(f"+{equipped_item.stats.strength} STR")
                if equipped_item.stats.dexterity > 0:
                    stats_parts.append(f"+{equipped_item.stats.dexterity} DEX")
                if equipped_item.stats.wisdom > 0:
                    stats_parts.append(f"+{equipped_item.stats.wisdom} WIS")
                if equipped_item.stats.intelligence > 0:
                    stats_parts.append(f"+{equipped_item.stats.intelligence} INT")

                stats_str = ", ".join(stats_parts) if stats_parts else "keine Boni"
                game.add_log('system', f"⚔️ {equipped_item.name} angelegt! ({stats_str})")
                game.add_log('narrative', f"{equipped_item.description}")

        return  # Skip narration and normal flow for equip

    # SPECIAL HANDLING: Physical attack on unaware monster -> Direct combat with backstab
    if action_type == 'physical_attack' and room.monster and room.monster.hp > 0:
        target = intent.get('target', '').lower()
        monster_name_lower = room.monster.name.lower()

        # Check if attacking the monster
        if target and target in monster_name_lower:
            # Check if monster is unaware
            is_unaware = hasattr(room.monster, 'unaware') and room.monster.unaware

            if is_unaware:
                # Direct backstab attack! Skip narration, go straight to combat
                from models.game_state import GameState
                from game.combat import attack

                game.add_log('system', f"🗡️ ÜBERRASCHUNGSANGRIFF auf {room.monster.name}!")
                game.state = GameState.COMBAT
                attack(game)
                return  # Skip normal action flow

    game.add_log('system', f"🔍 [{action_type}] Plausibilität: {plausibility:.1%}", detail_level='verbose')

    # Log the roll
    attr_name = result['attribute'].upper()[:3]
    attr_mod = (result['attribute_value'] - 10) // 2
    gift_bonus = result.get('gift_bonus', 0)

    if gift_bonus > 0:
        game.add_log('system', f"🎲 {attr_name} Check: [{result['roll']}] + {attr_mod} + {gift_bonus} (Gift!) = {result['total']} vs DC {result['difficulty']}", detail_level='verbose')
    else:
        game.add_log('system', f"🎲 {attr_name} Check: [{result['roll']}] + {attr_mod} = {result['total']} vs DC {result['difficulty']}", detail_level='verbose')

    if result['success']:
        game.add_log('system', f"✓ Erfolg! (Margin: +{result['total'] - result['difficulty']})")
        # Reset fail counter on success
        game.last_failed_action = ""
        game.fail_count = 0
    else:
        game.add_log('system', f"✗ Fehlschlag! (Margin: {result['total'] - result['difficulty']})")

        # Track repeated failures
        action_normalized = action.lower().strip()
        if action_normalized == game.last_failed_action:
            game.fail_count += 1
        else:
            game.last_failed_action = action_normalized
            game.fail_count = 1

        # After 3 failures, destroy the object
        if game.fail_count >= 3:
            target = intent.get('target')
            if target:
                room.destroyed_objects.append(target)
                game.add_log('error', f"💥 {target} zerbricht endgültig! (Zu viele Fehlversuche)")
                game.last_failed_action = ""
                game.fail_count = 0

    # PRE-NARRATION: Check for treasure room looting (so narrative can include it)
    treasure_found = None
    if result['success'] and result['intent'].get('action_type') == 'interact_object':
        from models.game_state import RoomType

        if room.type == RoomType.TREASURE and not room.looted:
            action_lower = action.lower()

            # Must explicitly mention chest/treasure container
            chest_keywords = ['truhe', 'kiste', 'schatzkiste', 'chest', 'treasure']
            has_chest_mention = any(keyword in action_lower for keyword in chest_keywords)

            # And must be opening/taking action
            action_keywords = ['öffne', 'nimm', 'plündere', 'durchsuche', 'inhalt', 'open', 'loot', 'search']
            has_action = any(keyword in action_lower for keyword in action_keywords)

            is_looting = has_chest_mention and has_action

            if is_looting:
                import random
                from constants import TREASURE_GENERATION_RULES
                from game.loot import get_treasure_loot

                # Determine tier
                tier_choices = ['minor', 'common', 'rare', 'epic']
                tier_weights = [0.1, 0.5, 0.3, 0.1]
                tier = random.choices(tier_choices, weights=tier_weights)[0]

                tier_rules = TREASURE_GENERATION_RULES['tiers'][tier]

                # Generate gold
                gold_amount = random.randint(*tier_rules['gold_range'])

                # Get theme-based loot items
                treasure_items = get_treasure_loot(game.theme_config, tier)

                # Store for narration
                treasure_found = {
                    'gold': gold_amount,
                    'items': treasure_items,
                    'tier': tier
                }

                # Mark as looted
                room.looted = True

                # Add treasure data to result for narrative
                result['treasure_found'] = treasure_found

    # Check if this is NPC conversation (skip narrator if so)
    is_npc_conversation = False
    if room.npc and room.npc.alive:
        action_lower = action.lower()
        talk_keywords = ['sprich', 'spreche', 'rede', 'frag', 'frage', 'talk', 'speak', 'ask', 'sag']
        is_npc_conversation = any(keyword in action_lower for keyword in talk_keywords)

    # Get AI narration (but skip if this is NPC conversation - that has its own dialogue system)
    if not is_npc_conversation:
        ai = get_ai_service()
        if ai.is_available():
            game.start_loading("🎲 DM erzählt...")
            try:
                # Add fail count to result for narrator context
                result['fail_count'] = game.fail_count

                # Add context about fixed objects in room
                fixed_objects = []
                if hasattr(room, 'assigned_object') and room.assigned_object:
                    fixed_objects.append(room.assigned_object.get('name', ''))
                result['fixed_objects'] = fixed_objects

                narration_result = ai.narrate_action_result(
                    action=action,
                    result=result,
                    story_context=game.story_context
                )

                # Display narrative
                if narration_result['narrative']:
                    game.add_log('narrative', narration_result['narrative'])

                # Process discoveries
                if narration_result['discovered_gold'] > 0:
                    game.player.gold += narration_result['discovered_gold']
                    game.add_log('system', f"+{narration_result['discovered_gold']} Gold (entdeckt)")

                if narration_result['discovered_items']:
                    # Add discovered items to room loot (can be picked up)
                    from models.items import Item, ItemType, ItemStats
                    import random

                    for item_name in narration_result['discovered_items']:
                        item_name_lower = item_name.lower()

                        # Check if this is currency (should be converted to gold, not item)
                        currency_keywords = ['münze', 'coin', 'gold', 'silber', 'kupfer', 'geld', 'money']
                        is_currency = any(keyword in item_name_lower for keyword in currency_keywords)

                        if is_currency:
                            # Convert to gold instead of item
                            gold_amount = random.randint(5, 20)  # Random amount for found coins
                            game.player.gold += gold_amount
                            game.add_log('system', f"+{gold_amount} Gold ({item_name})")
                        else:
                            # Create a generic material item
                            discovered_item = Item(
                                id=f"discovered_{len(room.loot)}_{item_name.lower().replace(' ', '_')}",
                                name=item_name,
                                description=f"Du hast {item_name} entdeckt.",
                                type=ItemType.MATERIAL,
                                stats=ItemStats()
                            )
                            room.loot.append(discovered_item)
                            game.add_log('system', f"💎 Entdeckt: {item_name} (jetzt aufhebbar)")

                if narration_result['discovered_objects']:
                    # Add discovered objects to room description note
                    if not hasattr(room, 'discovered_objects'):
                        room.discovered_objects = []
                    for obj_name in narration_result['discovered_objects']:
                        if obj_name not in room.discovered_objects:
                            room.discovered_objects.append(obj_name)
                            game.add_log('system', f"🔍 Entdeckt: {obj_name} (jetzt interagierbar)")
            finally:
                game.stop_loading()
        else:
            # Fallback narration
            if result['success']:
                game.add_log('narrative', f"Mit deiner {result['attribute']} gelingt dir die Aktion.")
            else:
                game.add_log('narrative', f"Deine {result['attribute']} reicht nicht aus.")

    # Apply impact
    impact = result['impact']
    if impact['hp'] != 0:
        game.player.hp = max(0, min(game.player.max_hp, game.player.hp + impact['hp']))
        if impact['hp'] < 0:
            game.add_log('error', f"{impact['hp']} HP")
        else:
            game.add_log('system', f"+{impact['hp']} HP")

    if impact['gold'] > 0:
        game.player.gold += impact['gold']
        game.add_log('system', f"+{impact['gold']} Gold")

    if impact['xp'] > 0:
        game.player.xp += impact['xp']
        game.add_log('system', f"+{impact['xp']} XP")

        # Check for level up
        from game.combat import check_level_up
        check_level_up(game)

    # Handle crafted/discovered items
    if impact.get('item'):
        crafted_item = impact['item']
        game.player.inventory.append(crafted_item)
        game.add_log('system', f"✨ +1 Item: {crafted_item.name}")
        game.add_log('narrative', f"{crafted_item.description}")

    # Remove used components from inventory (only on success)
    if result['success']:
        components_used = result['intent'].get('components_used', [])
        if components_used:
            for component_name in components_used:
                # Find and remove the component from inventory
                for item in game.player.inventory[:]:  # Create copy to safely modify during iteration
                    if component_name.lower() in item.name.lower():
                        game.player.inventory.remove(item)
                        game.add_log('system', f"🔧 Komponente verbraucht: {item.name}")
                        break  # Only remove first match

    # Check for gift discovery (if gift bonus was used)
    if result.get('gift_discovered', False) and game.player.gift:
        gift = game.player.gift
        discovery_hint = gift.get('discovery_hint', 'Etwas an dir ist... anders.')
        game.add_log('system', f"🌟 GIFT ENTDECKT: {gift['name']}!")
        game.add_log('narrative', discovery_hint)

    # Check for spell discovery (if successful magic attempt)
    if result.get('spell_discovered', False):
        spell_name = result['magic_data']['spell_name']
        effect_type = result['magic_data'].get('effect_type', 'unknown')
        magnitude = result['magic_data'].get('magnitude', 'minor')

        game.add_log('system', f"📖 ZAUBER ENTDECKT: {spell_name}!")
        game.add_log('narrative', f"Die Magie formt sich zu einem stabilen Muster. Du spürst, wie sich das Wissen in deinem Geist festigt.")

        # Track world event for spell discovery
        impact_level = "major" if magnitude == "major" else "moderate"
        game.world_state.add_event(
            event_type="magic",
            description=f"{game.player.name} entdeckte den Zauber '{spell_name}' ({effect_type})",
            location=f"Raum ({room.x}, {room.y})",
            impact_level=impact_level,
            consequences=[f"Magische Energie durchdringt den Raum"] if magnitude == "major" else []
        )

    # Check for known spell cast
    if result.get('known_spell_cast', False):
        spell_name = result['magic_data']['spell_name']
        effect_icons = {
            'fire': '🔥', 'ice': '❄️', 'heal': '💚',
            'shield': '🛡️', 'lightning': '⚡',
            'dark': '🌑', 'light': '✨'
        }
        icon = effect_icons.get(result['magic_data']['effect_type'], '🔮')
        game.add_log('system', f"{icon} Zauber gewirkt: {spell_name}!")

    # Note: Simple item pickup is now handled directly in main.py
    # This section is only for complex pickup scenarios that go through LLM

    # Check for finding hidden keys (wall searching)
    if result['success'] and result['intent'].get('action_type') == 'interact_object':
        action_lower = action.lower()
        search_keywords = ['untersuche', 'durchsuche', 'suche', 'inspect', 'search', 'wand', 'wall', 'boden', 'floor']

        is_searching = any(keyword in action_lower for keyword in search_keywords)

        if is_searching and room.hidden_key:
            # Found hidden key!
            game.player.inventory.append(room.hidden_key)
            game.add_log('system', f"🔍 Versteckt gefunden: {room.hidden_key.name}!")
            game.add_log('narrative', f"{room.hidden_key.description}")
            room.hidden_key = None  # Remove from room

    # Check for door unlocking/opening
    if result['success'] and result['intent'].get('action_type') == 'interact_object':
        action_lower = action.lower()
        door_keywords = ['tür', 'door', 'unlock', 'aufschließ']
        open_keywords = ['öffne', 'open']

        # Check if this is a door action (not a treasure chest!)
        chest_keywords = ['truhe', 'kiste', 'schatzkiste', 'chest']
        is_chest_action = any(keyword in action_lower for keyword in chest_keywords)

        # Only door keywords OR (open keywords AND no chest mention)
        is_door_action = (
            any(keyword in action_lower for keyword in door_keywords) or
            (any(keyword in action_lower for keyword in open_keywords) and not is_chest_action)
        )

        if is_door_action and not is_chest_action:
            from models.door import Direction, DoorState

            # Determine which direction door the player wants to open
            direction_map = {
                'nord': Direction.NORTH,
                'north': Direction.NORTH,
                'süd': Direction.SOUTH,
                'south': Direction.SOUTH,
                'ost': Direction.EAST,
                'east': Direction.EAST,
                'west': Direction.WEST,
                'west': Direction.WEST
            }

            target_direction = None
            for keyword, direction in direction_map.items():
                if keyword in action_lower:
                    target_direction = direction
                    break

            # If no direction specified, try to find a locked door
            if not target_direction:
                for direction, door in room.doors.items():
                    if door.state == DoorState.LOCKED:
                        target_direction = direction
                        break

            if target_direction and target_direction in room.doors:
                door = room.doors[target_direction]

                if door.state == DoorState.LOCKED:
                    # Try to unlock with key from inventory
                    matching_key = None
                    for item in game.player.inventory:
                        if item.key_id == door.key_id:
                            matching_key = item
                            break

                    if matching_key:
                        # Unlock door!
                        door.unlock(matching_key.key_id)
                        game.add_log('system', f"🔓 Tür aufgeschlossen mit {matching_key.name}!")

                        # Also unlock the mirror door in adjacent room
                        dx, dy = 0, 0
                        mirror_dir = None

                        if target_direction == Direction.NORTH:
                            dy = -1
                            mirror_dir = Direction.SOUTH
                        elif target_direction == Direction.SOUTH:
                            dy = 1
                            mirror_dir = Direction.NORTH
                        elif target_direction == Direction.EAST:
                            dx = 1
                            mirror_dir = Direction.WEST
                        elif target_direction == Direction.WEST:
                            dx = -1
                            mirror_dir = Direction.EAST

                        adjacent_room = game.dungeon.get_room(game.player.x + dx, game.player.y + dy, game.player.z)
                        if adjacent_room and mirror_dir in adjacent_room.doors:
                            adjacent_room.doors[mirror_dir].unlock(matching_key.key_id)

                        # Remove key from inventory (consumed)
                        game.player.inventory.remove(matching_key)
                    else:
                        game.add_log('error', f"🔒 Du hast nicht den richtigen Schlüssel. Benötigt: {door.key_id}")
                elif door.state == DoorState.CLOSED:
                    door.open()
                    game.add_log('system', "🚪 Tür geöffnet.")
                else:
                    game.add_log('system', "Die Tür ist bereits offen.")

    # Apply treasure findings (already computed pre-narration)
    if treasure_found:
        # Add gold
        game.player.gold += treasure_found['gold']
        game.add_log('system', f"💰 +{treasure_found['gold']} Gold!")

        # Add items
        if treasure_found['items']:
            for treasure_item in treasure_found['items']:
                game.player.inventory.append(treasure_item)
                game.add_log('system', f"✨ +1 Item: {treasure_item.name}")
                game.add_log('narrative', treasure_item.description)

                # Check for quest objective: collect item
                if game.player.quest_manager:
                    result = game.player.quest_manager.find_quest_by_target(treasure_item.name, 'collect')
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

                                if quest.special_reward:
                                    game.add_log('system', f"🏆 Spezielle Belohnung: {quest.special_reward}")

    # Check for NPC conversation
    if room.npc and room.npc.alive:
        action_lower = action.lower()
        talk_keywords = ['sprich', 'spreche', 'rede', 'frag', 'frage', 'talk', 'speak', 'ask', 'sag']

        is_talking = any(keyword in action_lower for keyword in talk_keywords)

        if is_talking:
            from services.ai_service import get_ai_service
            ai = get_ai_service()

            if ai.is_available():
                game.start_loading(f"💬 {room.npc.name} antwortet...")
                try:
                    # Generate NPC response (now returns dict with response + actions + flags)
                    npc_result = ai.generate_npc_dialogue(
                        player_message=action,
                        npc=room.npc,
                        world_state=game.world_state,
                        story_context=game.story_context,
                        player_hp=game.player.hp,
                        player_max_hp=game.player.max_hp,
                        player_quirk=game.player.quirk,
                        player_morality=game.player.morality,
                        relationship=game.player.get_relationship(room.npc.id),
                        quest_manager=game.player.quest_manager,
                        player_equipment=game.player.equipment
                    )

                    response_text = npc_result['response']
                    npc_actions = npc_result.get('actions', [])
                    attitude_change = npc_result.get('attitude_change', 0)
                    reveals_information = npc_result.get('reveals_information', False)
                    information_revealed = npc_result.get('information_revealed')
                    offers_quest = npc_result.get('offers_quest', False)
                    will_attack = npc_result.get('will_attack', False)

                    # Record interaction in NPC memory
                    room.npc.add_interaction(
                        player_action=action,
                        npc_response=response_text,
                        topic="general"
                    )

                    # Check for quest objective: rescue/interact with NPC
                    if room.npc.quest_id and room.npc.quest_objective_id:
                        if game.player.quest_manager:
                            completed_obj = game.player.quest_manager.update_objective(
                                room.npc.quest_id,
                                room.npc.quest_objective_id
                            )
                            if completed_obj:
                                quest = game.player.quest_manager.get_quest(room.npc.quest_id)
                                if quest:
                                    game.add_log('system', f"📜 Quest Ziel: {completed_obj.description} ({completed_obj.count_current}/{completed_obj.count_required})")

                                    # Karma for helping NPCs (rescue, interact objectives)
                                    if completed_obj.type in ['rescue', 'interact']:
                                        karma_gain = 15  # Good deed
                                        game.player.adjust_morality(karma_gain, f"Geholfen: {completed_obj.description}")
                                        game.add_log('system', f"⚖️ Karma: +{karma_gain}", detail_level='verbose')

                                    # Check if quest is fully completed
                                    if quest.completed:
                                        game.add_log('system', f"🎉 QUEST ABGESCHLOSSEN: {quest.title}!")
                                        game.add_log('system', f"Belohnung: +{quest.xp_reward} XP, +{quest.gold_reward} Gold")
                                        game.player.xp += quest.xp_reward
                                        game.player.gold += quest.gold_reward

                                        # Additional karma for completing quests
                                        quest_karma = 20
                                        game.player.adjust_morality(quest_karma, f"Quest abgeschlossen: {quest.title}")
                                        game.add_log('system', f"⚖️ Karma: +{quest_karma}", detail_level='verbose')

                                        if quest.special_reward:
                                            game.add_log('system', f"🏆 Spezielle Belohnung: {quest.special_reward}")

                    # Display response
                    npc_icon = {
                        'merchant': '🛒',
                        'scholar': '📚',
                        'hermit': '🧙',
                        'guard': '⚔️',
                        'priest': '✨'
                    }.get(room.npc.role, '👤')

                    game.add_log('narrative', f"{npc_icon} {room.npc.name}: \"{response_text}\"")

                    # Process attitude change
                    if attitude_change != 0:
                        game.player.adjust_relationship(room.npc.id, attitude_change * 5)
                        if attitude_change > 0:
                            game.add_log('system', f"💚 {room.npc.name} mag dich etwas mehr.")
                            # Positive interactions give karma
                            karma_gain = attitude_change * 5  # Scale with attitude change
                            game.player.adjust_morality(karma_gain, f"Gute Tat: {room.npc.name}")
                            game.add_log('system', f"⚖️ Karma: +{karma_gain}", detail_level='verbose')
                        elif attitude_change < 0:
                            game.add_log('system', f"💔 {room.npc.name} ist enttäuscht von dir.")
                            # Negative interactions reduce karma slightly
                            karma_loss = attitude_change * 3  # Less severe than positive
                            game.player.adjust_morality(karma_loss, f"Schlechte Tat: {room.npc.name}")
                            game.add_log('system', f"⚖️ Karma: {karma_loss}", detail_level='verbose')

                    # Process information revelation
                    if reveals_information and information_revealed:
                        game.add_log('system', f"ℹ️ {room.npc.name} hat dir etwas Wichtiges verraten!")
                        game.player.xp += 10
                        game.add_log('system', '+10 XP (Information)')

                    # Process quest offer
                    if offers_quest:
                        game.add_log('system', f"⚡ {room.npc.name} bietet dir eine Quest an!")
                        game.player.xp += 5
                        game.add_log('system', '+5 XP (Quest)')

                    # Process attack flag
                    if will_attack:
                        game.add_log('error', f"⚔️ {room.npc.name} wird feindlich!")
                        room.npc.hostile = True
                        # TODO: Convert to combat

                    # Small XP for conversation
                    if not reveals_information and not offers_quest:
                        game.player.xp += 2
                        game.add_log('system', '+2 XP (Gespräch)')

                finally:
                    game.stop_loading()

                # Execute NPC actions
                _execute_npc_actions(game, room, npc_actions)
            else:
                # Fallback without AI
                game.add_log('narrative', f"{room.npc.name} nickt dir zu.")

    # Check for death
    if game.player.hp <= 0:
        from models.game_state import GameState
        game.state = GameState.GAMEOVER
        game.handle_death(death_cause="Fehlgeschlagene Aktion")
