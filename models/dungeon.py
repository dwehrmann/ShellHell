"""Dungeon, room, and monster models."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
import random
from models.game_state import RoomType
from models.items import Item
from models.door import Door, Direction
from models.npc import NPC
from constants import DUNGEON_SIZE, MONSTER_TEMPLATES


@dataclass
class Monster:
    """A monster enemy."""
    name: str
    hp: int
    max_hp: int
    attack: int
    defense: int
    stunned: bool = False

    @classmethod
    def from_template(cls, template: dict) -> 'Monster':
        """Create a monster from a template."""
        return cls(
            name=template['name'],
            hp=template['hp'],
            max_hp=template['hp'],
            attack=template['attack'],
            defense=template['defense']
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'hp': self.hp,
            'max_hp': self.max_hp,
            'attack': self.attack,
            'defense': self.defense,
            'stunned': self.stunned
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Monster':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class Room:
    """A room in the dungeon."""
    x: int
    y: int
    type: RoomType
    visited: bool = False
    description: Optional[str] = None
    monster: Optional[Monster] = None
    defeated_monster_name: Optional[str] = None  # Name of defeated monster for description updates
    npc: Optional[NPC] = None  # NPC in this room
    loot: List[Item] = field(default_factory=list)
    looted: bool = False  # Has treasure been taken?
    doors: Dict[Direction, Door] = field(default_factory=dict)  # Doors in each direction
    hidden_key: Optional[Item] = None  # Key hidden in wall/floor (can be found by searching)
    destroyed_objects: List[str] = field(default_factory=list)  # Objects that broke from repeated failures
    discovered_objects: List[str] = field(default_factory=list)  # Objects discovered by narrator (now interactable)
    hazard: Optional[str] = None  # Environmental hazard (theme-specific)
    hazard_triggered: bool = False  # Has the hazard been triggered already?
    assigned_object: Optional[Dict[str, Any]] = None  # Object from palette assigned to this room

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'x': self.x,
            'y': self.y,
            'type': self.type.value,
            'visited': self.visited,
            'description': self.description,
            'monster': self.monster.to_dict() if self.monster else None,
            'defeated_monster_name': self.defeated_monster_name,
            'npc': self.npc.to_dict() if self.npc else None,
            'loot': [item.to_dict() for item in self.loot],
            'looted': self.looted,
            'doors': {direction.value: door.to_dict() for direction, door in self.doors.items()},
            'hidden_key': self.hidden_key.to_dict() if self.hidden_key else None,
            'destroyed_objects': self.destroyed_objects,
            'discovered_objects': self.discovered_objects,
            'hazard': self.hazard,
            'hazard_triggered': self.hazard_triggered,
            'assigned_object': self.assigned_object
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Room':
        """Create from dictionary."""
        loot_data = data.get('loot', [])
        loot_items = [Item.from_dict(item_data) for item_data in loot_data] if loot_data else []

        # Deserialize doors
        doors_data = data.get('doors', {})
        doors = {
            Direction(dir_str): Door.from_dict(door_data)
            for dir_str, door_data in doors_data.items()
        }

        # Deserialize hidden key
        hidden_key_data = data.get('hidden_key')
        hidden_key = Item.from_dict(hidden_key_data) if hidden_key_data else None

        # Deserialize NPC
        npc_data = data.get('npc')
        npc = NPC.from_dict(npc_data) if npc_data else None

        # MIGRATION: Handle old saves with RoomType.STAIRS
        room_type_str = data['type']
        if room_type_str == 'STAIRS':
            # Old saves had STAIRS, migrate to STAIRS_DOWN (most common case)
            room_type_str = 'STAIRS_DOWN'

        return cls(
            x=data['x'],
            y=data['y'],
            type=RoomType(room_type_str),
            visited=data.get('visited', False),
            description=data.get('description'),
            monster=Monster.from_dict(data['monster']) if data.get('monster') else None,
            defeated_monster_name=data.get('defeated_monster_name'),
            npc=npc,
            loot=loot_items,
            looted=data.get('looted', False),
            doors=doors,
            hidden_key=hidden_key,
            destroyed_objects=data.get('destroyed_objects', []),
            discovered_objects=data.get('discovered_objects', []),
            hazard=data.get('hazard'),
            hazard_triggered=data.get('hazard_triggered', False),
            assigned_object=data.get('assigned_object')
        )


class Dungeon:
    """The multi-level dungeon."""

    def __init__(self, size: int = DUNGEON_SIZE, num_levels: int = 3, theme_config: Optional[Any] = None):
        """Initialize an empty dungeon."""
        self.size = size
        self.num_levels = num_levels
        self.levels: List[List[List[Room]]] = []  # levels[z][y][x]
        self.theme_config = theme_config  # ThemeConfig from models.theme

    def generate(self) -> None:
        """Generate the multi-level dungeon layout."""
        self.levels = []

        for z in range(self.num_levels):
            grid = []
            for y in range(self.size):
                row = []
                for x in range(self.size):
                    # Determine room type
                    room_type = RoomType.EMPTY
                    rand = random.random()

                    if rand < 0.25:
                        room_type = RoomType.MONSTER
                    elif rand < 0.4:
                        room_type = RoomType.TREASURE

                    # Starting room (top level only)
                    if z == 0 and x == 0 and y == 0:
                        room_type = RoomType.EMPTY

                    room = Room(x=x, y=y, type=room_type)
                    row.append(room)
                grid.append(row)
            self.levels.append(grid)

        # Place stairs between levels
        self._place_stairs()

        # Generate doors between rooms on each level
        for z in range(self.num_levels):
            self.generate_doors(z)

    def _place_stairs(self) -> None:
        """Place stairs between levels at coordinated positions."""
        # Place stairs down from each level (except the last)
        for z in range(self.num_levels - 1):
            # Stairs down at the end of the level
            x_down, y_down = self.size - 1, self.size - 1
            self.levels[z][y_down][x_down].type = RoomType.STAIRS_DOWN

            # Corresponding stairs up at the beginning of the next level
            x_up, y_up = self.size - 1, self.size - 1
            self.levels[z + 1][y_up][x_up].type = RoomType.STAIRS_UP

    def generate_doors(self, z: int = 0) -> None:
        """Generate doors between rooms, some locked with keys."""
        from constants import LOCKED_DOOR_CHANCE, KEY_TEMPLATES, KEY_DROP_CHANCE, HIDDEN_KEY_CHANCE
        from models.door import Door, DoorState, Direction
        from models.items import Item, ItemType, ItemStats

        # Get the grid for this level
        grid = self.levels[z]

        # Track which keys we've used
        used_key_templates = []
        available_keys = KEY_TEMPLATES.copy()

        # Iterate through all rooms
        for y in range(self.size):
            for x in range(self.size):
                room = grid[y][x]

                # Create doors to adjacent rooms (only in positive directions to avoid duplicates)
                # East door
                if x < self.size - 1:
                    # Decide if locked (but never lock starting room exits)
                    if random.random() < LOCKED_DOOR_CHANCE and available_keys and not (x == 0 and y == 0):
                        key_template = random.choice(available_keys)
                        available_keys.remove(key_template)
                        used_key_templates.append((key_template, room, Direction.EAST))

                        # Create locked door
                        door = Door(
                            direction=Direction.EAST,
                            state=DoorState.LOCKED,
                            key_id=key_template['key_id']
                        )
                    else:
                        # Create open door
                        door = Door(
                            direction=Direction.EAST,
                            state=DoorState.OPEN
                        )

                    room.doors[Direction.EAST] = door
                    # Mirror door in adjacent room
                    grid[y][x + 1].doors[Direction.WEST] = Door(
                        direction=Direction.WEST,
                        state=door.state,
                        key_id=door.key_id
                    )

                # South door
                if y < self.size - 1:
                    # Decide if locked (but never lock starting room exits)
                    if random.random() < LOCKED_DOOR_CHANCE and available_keys and not (x == 0 and y == 0):
                        key_template = random.choice(available_keys)
                        available_keys.remove(key_template)
                        used_key_templates.append((key_template, room, Direction.SOUTH))

                        # Create locked door
                        door = Door(
                            direction=Direction.SOUTH,
                            state=DoorState.LOCKED,
                            key_id=key_template['key_id']
                        )
                    else:
                        # Create open door
                        door = Door(
                            direction=Direction.SOUTH,
                            state=DoorState.OPEN
                        )

                    room.doors[Direction.SOUTH] = door
                    # Mirror door in adjacent room
                    grid[y + 1][x].doors[Direction.NORTH] = Door(
                        direction=Direction.NORTH,
                        state=door.state,
                        key_id=door.key_id
                    )

        # Place keys for locked doors
        for key_template, near_room, direction in used_key_templates:
            # Create key item
            key_item = Item(
                id=f"key_{key_template['key_id']}",
                name=key_template['name'],
                description=key_template['description'],
                type=ItemType.KEY,
                stats=ItemStats(),
                key_id=key_template['key_id']
            )

            # Decide where to place key: monster drop or hidden in wall
            if random.random() < KEY_DROP_CHANCE:
                # Find a monster room to add key to loot
                monster_rooms = [
                    grid[y][x]
                    for y in range(self.size)
                    for x in range(self.size)
                    if grid[y][x].type == RoomType.MONSTER
                ]

                if monster_rooms:
                    target_room = random.choice(monster_rooms)
                    target_room.loot.append(key_item)
            else:
                # Hide key in a random room wall
                if random.random() < HIDDEN_KEY_CHANCE:
                    # Find random room (not starting room)
                    empty_rooms = [
                        grid[y][x]
                        for y in range(self.size)
                        for x in range(self.size)
                        if not (x == 0 and y == 0 and z == 0)
                    ]

                    if empty_rooms:
                        target_room = random.choice(empty_rooms)
                        target_room.hidden_key = key_item

    def spawn_monsters(self) -> None:
        """Spawn monsters in monster rooms (theme-aware)."""
        # Determine monster pool
        if self.theme_config and self.theme_config.monster_pool:
            monster_pool = self.theme_config.monster_pool
            boss_template = self.theme_config.boss_monster
        else:
            # Fallback to generic monsters
            monster_pool = MONSTER_TEMPLATES
            boss_template = None

        # Iterate through all levels
        for z, grid in enumerate(self.levels):
            for row in grid:
                for room in row:
                    # Spawn boss on stairs down in the last level
                    is_last_level = (z == self.num_levels - 1)
                    if room.type == RoomType.STAIRS_DOWN and is_last_level and boss_template and not room.monster:
                        room.monster = Monster.from_template(boss_template)
                        continue

                    # Spawn regular monsters
                    if room.type == RoomType.MONSTER and not room.monster:
                        template = random.choice(monster_pool)
                        room.monster = Monster.from_template(template)

    def spawn_quest_npcs(self, quest: Any) -> None:
        """
        Spawn quest-related NPCs in the dungeon.

        Args:
            quest: Quest object with objectives that need NPC spawning
        """
        if not quest:
            return

        for objective in quest.objectives:
            if objective.type == "rescue":
                # Spawn hostages/prisoners for rescue objectives
                count = objective.count_required

                # Find random empty rooms (not stairs, not starting room, no monster, no NPC)
                available_rooms = []
                for z, grid in enumerate(self.levels):
                    for row in grid:
                        for room in row:
                            if (room.x == 0 and room.y == 0 and z == 0):  # Starting room
                                continue
                            if room.type in [RoomType.STAIRS_DOWN, RoomType.STAIRS_UP]:  # Stairs rooms
                                continue
                            if room.monster or room.npc:  # Already occupied
                                continue
                            available_rooms.append(room)

                # Spawn NPCs in random rooms
                import random
                selected_rooms = random.sample(available_rooms, min(count, len(available_rooms)))

                for i, room in enumerate(selected_rooms):
                    hostage = NPC(
                        id=f"{quest.id}_hostage_{i}",
                        name=f"Geisel #{i+1}",
                        role="hostage",
                        personality="frightened",
                        location=f"Raum ({room.x}, {room.y})",
                        knowledge=[
                            "Wir wurden von den Orks hierher verschleppt!",
                            "Der Häuptling sitzt im tiefsten Raum, bewacht von seinen besten Kriegern."
                        ],
                        sells_items=False,
                        base_attitude="friendly",
                        # Quest markers
                        reveals_information=True,
                        information_topics=["boss_location", "escape_route"]
                    )
                    # Add metadata for quest tracking
                    hostage.quest_id = quest.id
                    hostage.quest_objective_id = objective.id

                    room.npc = hostage

    def spawn_npcs(self) -> None:
        """Spawn NPCs in random rooms based on spawn chance (theme-aware)."""
        from constants import NPC_SPAWN_CHANCE, NPC_TEMPLATES
        from models.npc import NPC

        # Filter NPCs by theme
        if self.theme_config and self.theme_config.npc_variants:
            allowed_npcs = [
                template for template in NPC_TEMPLATES
                if template['role'] in self.theme_config.npc_variants
            ]
        else:
            allowed_npcs = NPC_TEMPLATES

        if not allowed_npcs:
            allowed_npcs = NPC_TEMPLATES  # Fallback

        # Counter for unique IDs
        npc_counts = {template['id_prefix']: 0 for template in NPC_TEMPLATES}

        for z, grid in enumerate(self.levels):
            for row in grid:
                for room in row:
                    # Don't spawn NPCs in:
                    # - Starting room (0, 0, 0)
                    # - Monster rooms
                    # - Stairs rooms
                    # - Rooms that already have an NPC
                    if (room.x == 0 and room.y == 0 and z == 0) or room.monster or \
                       room.type in [RoomType.STAIRS_DOWN, RoomType.STAIRS_UP] or room.npc:
                        continue

                    # Random spawn chance
                    if random.random() < NPC_SPAWN_CHANCE:
                        # Choose random NPC template from theme-allowed list
                        template = random.choice(allowed_npcs)

                        # Create unique ID
                        npc_counts[template['id_prefix']] += 1
                        npc_id = f"{template['id_prefix']}_{npc_counts[template['id_prefix']]}"

                        # Create NPC instance
                        npc = NPC(
                            id=npc_id,
                            name=template['name'],
                            role=template['role'],
                            personality=template['personality'],
                            location=f"Raum ({room.x}, {room.y})",
                            knowledge=template['knowledge'].copy(),
                            sells_items=template['sells_items'],
                            inventory_value=random.randint(100, 300) if template['sells_items'] else 0
                        )

                        room.npc = npc

    def spawn_hazards(self) -> None:
        """Spawn environmental hazards in rooms based on theme."""
        if not self.theme_config or not self.theme_config.hazards:
            return

        hazard_chance = self.theme_config.hazard_chance

        for z, grid in enumerate(self.levels):
            for row in grid:
                for room in row:
                    # Don't spawn hazards in:
                    # - Starting room (0, 0, 0)
                    # - Rooms with monsters (combat is hazard enough)
                    # - Rooms that already have a hazard
                    if (room.x == 0 and room.y == 0 and z == 0) or room.monster or room.hazard:
                        continue

                    # Random spawn chance
                    if random.random() < hazard_chance:
                        # Choose random hazard from theme
                        room.hazard = random.choice(self.theme_config.hazards)

    def get_room(self, x: int, y: int, z: int = 0) -> Optional[Room]:
        """Get a room at coordinates."""
        if 0 <= z < self.num_levels and 0 <= x < self.size and 0 <= y < self.size:
            return self.levels[z][y][x]
        return None

    def get_exits(self, x: int, y: int, z: int = 0) -> List[str]:
        """Get available exits from a position."""
        exits = []
        if y > 0:
            exits.append("Norden")
        if y < self.size - 1:
            exits.append("Süden")
        if x < self.size - 1:
            exits.append("Osten")
        if x > 0:
            exits.append("Westen")
        return exits

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'size': self.size,
            'num_levels': self.num_levels,
            'levels': [
                [[room.to_dict() for room in row] for row in grid]
                for grid in self.levels
            ]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Dungeon':
        """Create from dictionary."""
        # Handle old saves with 'grid' format (migrate to levels)
        if 'grid' in data and 'levels' not in data:
            # Old save format: convert grid to levels[0]
            dungeon = cls(size=data['size'], num_levels=1)
            grid = [
                [Room.from_dict(room_data) for room_data in row]
                for row in data['grid']
            ]
            dungeon.levels = [grid]
        else:
            # New format with levels
            num_levels = data.get('num_levels', 3)
            dungeon = cls(size=data['size'], num_levels=num_levels)
            dungeon.levels = [
                [[Room.from_dict(room_data) for room_data in row] for row in grid_data]
                for grid_data in data['levels']
            ]

        return dungeon
