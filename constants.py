"""Game constants and templates."""

DUNGEON_SIZE = 6

THEMES = [
    "Verlassene Zwergenhalle",
    "Höhle des Orkhäuptlings",
    "Verlassene Stadt",
    "Schmutziger Abwasserkanal",
    "Mystische Pyramide"
]

MONSTER_TEMPLATES = [
    {"name": "Schattenratte", "hp": 10, "attack": 3, "defense": 1},
    {"name": "Skelettwächter", "hp": 20, "attack": 5, "defense": 3},
    {"name": "Dunkler Akolyth", "hp": 15, "attack": 7, "defense": 1},
    {"name": "Eisenschleim", "hp": 30, "attack": 4, "defense": 5},
]

# Monster loot table - 40% drop chance
MONSTER_LOOT = {
    "Schattenratte": {
        "name": "Rattenzahn",
        "description": "Ein spitzer Rattenzahn. Könnte als Dolch dienen.",
        "type": "weapon",
        "stats": {"attack": 2}
    },
    "Skelettwächter": {
        "name": "Rostiges Beil",
        "description": "Ein verrostetes Beil mit Knochenmark-Flecken.",
        "type": "weapon",
        "stats": {"attack": 3}
    },
    "Dunkler Akolyth": {
        "name": "Unheiliges Symbol",
        "description": "Ein dunkles Amulett, das böse Macht ausstrahlt.",
        "type": "ring",
        "stats": {"intelligence": 2, "attack": 1}
    },
    "Eisenschleim": {
        "name": "Gehärteter Schleim",
        "description": "Erstarrter Eisenschleim, hart wie Metall.",
        "type": "armor",
        "stats": {"defense": 4}
    }
}

LOOT_DROP_CHANCE = 0.4  # 40% chance to drop loot

# Key templates - different keys for different locked doors
KEY_TEMPLATES = [
    {
        "key_id": "rusty_key",
        "name": "Rostiger Schlüssel",
        "description": "Ein alter, verrosteter Schlüssel. Passt zu alten Schlössern."
    },
    {
        "key_id": "golden_key",
        "name": "Goldener Schlüssel",
        "description": "Ein glänzender goldener Schlüssel. Sieht wertvoll aus."
    },
    {
        "key_id": "bone_key",
        "name": "Knochenschlüssel",
        "description": "Ein Schlüssel aus Knochen geschnitzt. Gruselig, aber funktional."
    },
    {
        "key_id": "crystal_key",
        "name": "Kristallschlüssel",
        "description": "Ein durchsichtiger Kristallschlüssel, der schwach leuchtet."
    },
    {
        "key_id": "iron_key",
        "name": "Eiserner Schlüssel",
        "description": "Ein schwerer eiserner Schlüssel. Sieht robust aus."
    }
]

# Door generation settings
LOCKED_DOOR_CHANCE = 0.3  # 30% chance a door is locked
KEY_DROP_CHANCE = 0.5  # 50% chance key drops from monster (if door exists)
HIDDEN_KEY_CHANCE = 0.4  # 40% chance key is hidden in wall (if door exists)

# NPC templates
NPC_SPAWN_CHANCE = 0.15  # 15% chance for NPC in a room
NPC_TEMPLATES = [
    {
        "id_prefix": "merchant",
        "name": "Wandernder Händler",
        "role": "merchant",
        "personality": "friendly",
        "knowledge": [
            "Die Treppe ist ganz hinten im Dungeon",
            "Manche Monster tragen Schlüssel",
            "Zauber können in alten Büchern gefunden werden"
        ],
        "sells_items": True
    },
    {
        "id_prefix": "scholar",
        "name": "Verschollener Gelehrter",
        "role": "scholar",
        "personality": "mysterious",
        "knowledge": [
            "Die alten Magier haben Zauber in die Wände geritzt",
            "Kombiniere Komponenten mit gesprochenen Worten",
            "Intelligenz ist der Schlüssel zur Magie"
        ],
        "sells_items": False
    },
    {
        "id_prefix": "hermit",
        "name": "Einsiedler",
        "role": "hermit",
        "personality": "paranoid",
        "knowledge": [
            "Vertraue niemandem in diesen Hallen",
            "Die Schatten flüstern von verborgenen Schätzen",
            "Durchsuche die Wände nach Geheimnissen"
        ],
        "sells_items": False
    },
    {
        "id_prefix": "guard",
        "name": "Gefallener Wächter",
        "role": "guard",
        "personality": "grumpy",
        "knowledge": [
            "Früher war ich ein Abenteurer wie du",
            "Die Monster werden stärker, je tiefer man geht",
            "Achte auf verschlossene Türen"
        ],
        "sells_items": False
    },
    {
        "id_prefix": "priest",
        "name": "Blinder Priester",
        "role": "priest",
        "personality": "holy",
        "knowledge": [
            "Heilmagie kann Leben retten",
            "Dunkle Magie verlangt einen Preis",
            "Die Toten ruhen nicht in Frieden hier"
        ],
        "sells_items": False
    }
]

# Treasure generation rules (AI uses these to create themed items)
TREASURE_GENERATION_RULES = {
    "tiers": {
        "minor": {
            "gold_range": [20, 50],
            "item_chance": 0.5,
            "stat_bonus_range": [1, 2]
        },
        "common": {
            "gold_range": [30, 80],
            "item_chance": 0.6,
            "stat_bonus_range": [2, 4]
        },
        "rare": {
            "gold_range": [50, 120],
            "item_chance": 0.8,
            "stat_bonus_range": [4, 6]
        },
        "epic": {
            "gold_range": [100, 200],
            "item_chance": 1.0,
            "stat_bonus_range": [6, 9]
        }
    },
    "weapon_types": {
        "light": ["Dolch", "Kurzschwert", "Wurfmesser", "Kurzbogen"],
        "medium": ["Langschwert", "Streitaxt", "Morgenstern", "Langbogen"],
        "heavy": ["Hellebarde", "Flamberge", "Großaxt", "Zweihänder", "Kriegshammer"]
    },
    "armor_types": {
        "light": ["Lederrüstung", "Kettenhemd", "Lederarmschienen"],
        "medium": ["Schuppenpanzer", "Brustpanzer", "Ringpanzer"],
        "heavy": ["Plattenpanzer", "Drachenschuppen", "Vollrüstung"]
    },
    "accessory_types": ["Ring", "Amulett", "Talisman", "Armreif", "Krone", "Gürtel"],
    "stat_types": ["attack", "defense", "strength", "dexterity", "wisdom", "intelligence", "hp"]
}

RACES = [
    {"name": "Mensch", "key": "m"},
    {"name": "Halbork", "key": "o"},
    {"name": "Elf", "key": "e"},
    {"name": "Halbelf", "key": "h"},
    {"name": "Gnom", "key": "g"}
]

SKILLS = [
    {
        "id": "heavy_strike",
        "name": "Wuchtschlag",
        "description": "Ein mächtiger Hieb, der doppelten Schaden verursacht.",
        "level_required": 2,
        "cooldown": 3,
        "type": "damage",
        "value": 2,
    },
    {
        "id": "shield_wall",
        "name": "Schildwall",
        "description": "Erhöht die Verteidigung um 10 für 3 Züge.",
        "level_required": 3,
        "cooldown": 5,
        "type": "buff",
        "value": 10,
        "duration": 3,
    },
    {
        "id": "concussion",
        "name": "Erschütterung",
        "description": "Betäubt den Gegner für einen Zug.",
        "level_required": 4,
        "cooldown": 6,
        "type": "stun",
    }
]

# Theme-specific quests
THEME_QUESTS = {
    "dwarf_halls": {
        "id": "dwarf_halls_main",
        "title": "Der Verfluchte Edelstein",
        "description": "Die Zwerge verschwanden vor 100 Jahren. Ein verfluchter Edelstein in der Schatzkammer ist die Ursache. Zerstöre ihn!",
        "theme_id": "dwarf_halls",
        "xp_reward": 200,
        "gold_reward": 100,
        "objectives": [
            {
                "id": "explore_halls",
                "description": "Durchquere die Zwergenhallen",
                "type": "explore",
                "target": "Zwergenhallen",
                "count_required": 8,  # Visit 8 rooms
                "hidden": True  # Don't show this, auto-completes
            },
            {
                "id": "defeat_stone_king",
                "description": "Besiege den Steinkönig",
                "type": "kill",
                "target": "Steinkönig",
                "count_required": 1
            }
        ]
    },

    "orc_cave": {
        "id": "orc_cave_main",
        "title": "Der Orkhäuptling",
        "description": "Die Orks haben Dorfbewohner entführt und terrorisieren die Gegend. Rette die Geiseln und besiege den Häuptling!",
        "theme_id": "orc_cave",
        "xp_reward": 250,
        "gold_reward": 120,
        "objectives": [
            {
                "id": "rescue_hostages",
                "description": "Rette die Geiseln",
                "type": "rescue",
                "target": "Geisel",
                "count_required": 3
            },
            {
                "id": "defeat_chieftain",
                "description": "Besiege den Orkhäuptling",
                "type": "kill",
                "target": "Orkhäuptling",
                "count_required": 1
            }
        ]
    },

    "ruined_city": {
        "id": "ruined_city_main",
        "title": "Der Schattenkönig",
        "description": "Eine tote Stadt, von Schatten heimgesucht. Der Schattenkönig muss vernichtet werden, um die Seelen zu befreien.",
        "theme_id": "ruined_city",
        "xp_reward": 180,
        "gold_reward": 80,
        "objectives": [
            {
                "id": "find_lost_souls",
                "description": "Finde 2 verlorene Seelen",
                "type": "interact",
                "target": "Verlorene Seele",
                "count_required": 2
            },
            {
                "id": "defeat_shadow_king",
                "description": "Vernichte den Schattenkönig",
                "type": "kill",
                "target": "Schattenkönig",
                "count_required": 1
            }
        ]
    },

    "sewer": {
        "id": "sewer_main",
        "title": "Die Kanalisationsbestie",
        "description": "Etwas Monströses haust in den tiefsten Kanälen. Finde es und töte es, bevor es an die Oberfläche kommt.",
        "theme_id": "sewer",
        "xp_reward": 220,
        "gold_reward": 90,
        "objectives": [
            {
                "id": "collect_samples",
                "description": "Sammle 3 Alchemie-Reagenzien",
                "type": "collect",
                "target": "Alchemie-Reagenz",
                "count_required": 3
            },
            {
                "id": "defeat_beast",
                "description": "Töte die Kanalisationsbestie",
                "type": "kill",
                "target": "Kanalisationsbestie",
                "count_required": 1
            }
        ]
    },

    "pyramid": {
        "id": "pyramid_main",
        "title": "Der Fluch des Pharao",
        "description": "Die Pyramide birgt uralte Schätze, aber der Pharao-Lich wacht über sie. Durchbrich den Fluch und plündere die Grabkammer!",
        "theme_id": "pyramid",
        "xp_reward": 300,
        "gold_reward": 150,
        "special_reward": "pharao_schatz",  # Special item
        "objectives": [
            {
                "id": "deactivate_traps",
                "description": "Deaktiviere 4 Sandfallen",
                "type": "interact",
                "target": "Sandfalle",
                "count_required": 4,
                "hidden": True
            },
            {
                "id": "defeat_pharao_lich",
                "description": "Besiege den Pharao-Lich",
                "type": "kill",
                "target": "Pharao-Lich",
                "count_required": 1
            }
        ]
    },

    "burned_castle": {
        "id": "burned_castle_main",
        "title": "Flammen der Vergeltung",
        "description": "Das Schloss brennt seit 50 Jahren ohne zu erlöschen. Der Aschefürst muss vernichtet werden, um den ewigen Brand zu beenden.",
        "theme_id": "burned_castle",
        "xp_reward": 280,
        "gold_reward": 140,
        "objectives": [
            {
                "id": "extinguish_flames",
                "description": "Lösche 3 verfluchte Flammen",
                "type": "interact",
                "target": "Verfluchte Flamme",
                "count_required": 3,
                "hidden": True
            },
            {
                "id": "defeat_ash_lord",
                "description": "Besiege den Aschefürst",
                "type": "kill",
                "target": "Aschefürst",
                "count_required": 1
            }
        ]
    },

    "dark_crypt": {
        "id": "dark_crypt_main",
        "title": "Der Ewige Schlaf",
        "description": "Die Gruft erwacht. Der Grabkönig sammelt eine untote Armee. Nur sein Fall kann die Lebenden retten.",
        "theme_id": "dark_crypt",
        "xp_reward": 260,
        "gold_reward": 130,
        "objectives": [
            {
                "id": "seal_sarcophagi",
                "description": "Versiegle 4 Sarkophage",
                "type": "interact",
                "target": "Sarkophag",
                "count_required": 4,
                "hidden": True
            },
            {
                "id": "defeat_tomb_king",
                "description": "Besiege den Grabkönig",
                "type": "kill",
                "target": "Grabkönig",
                "count_required": 1
            }
        ]
    },

    "tavern_cellar": {
        "id": "tavern_cellar_main",
        "title": "Die Schmugglerkönig",
        "description": "Unter der Taverne verbirgt sich ein Schmugglernetzwerk. Der Kellermeister kontrolliert die Unterwelt - beende seine Herrschaft!",
        "theme_id": "tavern_cellar",
        "xp_reward": 240,
        "gold_reward": 110,
        "objectives": [
            {
                "id": "confiscate_smuggled_goods",
                "description": "Beschlagnahme 3 Schmuggelware-Fässer",
                "type": "collect",
                "target": "Schmuggelware",
                "count_required": 3
            },
            {
                "id": "defeat_cellar_master",
                "description": "Besiege den Kellermeister",
                "type": "kill",
                "target": "Kellermeister",
                "count_required": 1
            }
        ]
    },

    "forgotten_graveyard": {
        "id": "forgotten_graveyard_main",
        "title": "Die Witwenkönigin",
        "description": "Der Friedhof ist verflucht, die Toten finden keine Ruhe. Die Witwenkönigin hält ihre Seelen gefangen.",
        "theme_id": "forgotten_graveyard",
        "xp_reward": 270,
        "gold_reward": 135,
        "objectives": [
            {
                "id": "light_memorial_candles",
                "description": "Entzünde 5 Gedenkkerzen",
                "type": "interact",
                "target": "Gedenkkerze",
                "count_required": 5,
                "hidden": True
            },
            {
                "id": "defeat_widow_queen",
                "description": "Besiege die Witwenkönigin",
                "type": "kill",
                "target": "Witwenkönigin",
                "count_required": 1
            }
        ]
    }
}


def get_race_by_key(key: str):
    """Get race dict by key."""
    for race in RACES:
        if race['key'] == key:
            return race
    return None
