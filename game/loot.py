"""Theme-based loot generation."""

import random
from typing import Optional, List
from models.items import Item, ItemType, ItemStats


def create_item_from_template(template: dict, id_suffix: str = "") -> Item:
    """
    Create an Item from a theme loot template.

    Args:
        template: Loot template dict with 'name', 'type', 'stats'
        id_suffix: Optional suffix for item ID (e.g., monster name)

    Returns:
        Item instance
    """
    # Generate unique ID
    item_id = template['name'].lower().replace(' ', '_').replace('-', '_')
    if id_suffix:
        item_id = f"{id_suffix}_{item_id}"

    # Parse stats
    stats_data = template.get('stats', {})
    item_stats = ItemStats(
        attack=stats_data.get('attack', 0),
        defense=stats_data.get('defense', 0),
        strength=stats_data.get('strength', 0),
        dexterity=stats_data.get('dexterity', 0),
        wisdom=stats_data.get('wisdom', 0),
        intelligence=stats_data.get('intelligence', 0),
        hp=stats_data.get('hp', 0)
    )

    # Determine item type
    item_type_str = template.get('type', 'consumable')
    try:
        item_type = ItemType(item_type_str)
    except ValueError:
        # Fallback for unknown types → material (spell components)
        item_type = ItemType.MATERIAL

    # Create description if not provided
    description = template.get('description', f"Ein {template['name']}")

    return Item(
        id=item_id,
        name=template['name'],
        description=description,
        type=item_type,
        stats=item_stats
    )


def get_theme_loot(theme_config, tier: str = 'common', count: int = 1) -> List[Item]:
    """
    Get random loot from theme's loot tables.

    Args:
        theme_config: ThemeConfig object
        tier: 'common' or 'rare'
        count: Number of items to generate

    Returns:
        List of Item instances
    """
    if not theme_config:
        return []

    # Choose loot pool based on tier
    if tier == 'rare' and theme_config.rare_loot:
        loot_pool = theme_config.rare_loot
    elif theme_config.common_loot:
        loot_pool = theme_config.common_loot
    else:
        return []

    if not loot_pool:
        return []

    # Generate items
    items = []
    for i in range(count):
        template = random.choice(loot_pool)
        item = create_item_from_template(template, id_suffix=f"theme_{i}")
        items.append(item)

    return items


def get_monster_loot(theme_config, is_boss: bool = False) -> Optional[Item]:
    """
    Get loot drop from defeated monster based on theme.

    Args:
        theme_config: ThemeConfig object
        is_boss: Whether this is a boss monster

    Returns:
        Item or None
    """
    if not theme_config:
        return None

    # Bosses drop rare loot, regular monsters drop common loot
    if is_boss:
        loot_pool = theme_config.rare_loot if theme_config.rare_loot else theme_config.common_loot
    else:
        loot_pool = theme_config.common_loot

    if not loot_pool:
        return None

    template = random.choice(loot_pool)
    return create_item_from_template(template, id_suffix='monster')


def get_treasure_loot(theme_config, tier: str) -> List[Item]:
    """
    Get treasure room loot based on tier.

    Tier mapping:
    - minor/common: 1 common item (60% chance)
    - rare: 1-2 items from common or rare pool (80% chance)
    - epic: 2 items from rare pool (100% chance)

    Args:
        theme_config: ThemeConfig object
        tier: Treasure tier ('minor', 'common', 'rare', 'epic')

    Returns:
        List of Item instances
    """
    if not theme_config:
        return []

    items = []

    if tier == 'minor':
        # 60% chance for 1 common item
        if random.random() < 0.6 and theme_config.common_loot:
            items = get_theme_loot(theme_config, tier='common', count=1)

    elif tier == 'common':
        # 70% chance for 1 common item
        if random.random() < 0.7 and theme_config.common_loot:
            items = get_theme_loot(theme_config, tier='common', count=1)

    elif tier == 'rare':
        # 80% chance for 1-2 items (50/50 common or rare)
        if random.random() < 0.8:
            count = random.randint(1, 2)
            loot_tier = 'rare' if random.random() < 0.5 and theme_config.rare_loot else 'common'
            items = get_theme_loot(theme_config, tier=loot_tier, count=count)

    elif tier == 'epic':
        # 100% chance for 2 rare items
        if theme_config.rare_loot:
            items = get_theme_loot(theme_config, tier='rare', count=2)
        elif theme_config.common_loot:
            # Fallback to common if no rare loot
            items = get_theme_loot(theme_config, tier='common', count=2)

    return items
