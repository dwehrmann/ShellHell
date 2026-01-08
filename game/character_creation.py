"""Character creation utilities."""

import random
from models.player import Attributes
from constants import RACES


def roll_attribute() -> int:
    """
    Roll an attribute using 4d6, drop lowest.

    Returns:
        The rolled attribute value
    """
    rolls = [random.randint(1, 6) for _ in range(4)]
    rolls.sort()
    # Sum the highest 3
    return sum(rolls[1:])


def roll_attributes() -> Attributes:
    """
    Roll a full set of attributes.

    Returns:
        An Attributes object with rolled values
    """
    return Attributes(
        strength=roll_attribute(),
        dexterity=roll_attribute(),
        wisdom=roll_attribute(),
        intelligence=roll_attribute(),
        vitality=roll_attribute()
    )


def get_race_by_key(key: str) -> dict:
    """
    Get a race by its shortcut key.

    Args:
        key: The race key (m, o, e, h, g) or full name

    Returns:
        The race dict or None if not found
    """
    key = key.lower()
    for race in RACES:
        if race['key'] == key or race['name'].lower() == key:
            return race
    return None
