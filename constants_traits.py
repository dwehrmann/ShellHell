"""Character traits (quirks and gifts) definitions."""

# QUIRKS - Stat bonus but narrative/social malus
QUIRKS = [
    {
        'id': 'one_eyed',
        'name': 'Einäugig',
        'description': 'Du hast ein Auge verloren. (+2 WIS, aber NPCs reagieren verstört)',
        'stat_bonus': {'wisdom': 2},
        'narrative_tags': ['einäugig', 'narbe', 'verstümmelter']
    },
    {
        'id': 'limping',
        'name': 'Hinkend',
        'description': 'Eine alte Verletzung lässt dich hinken. (+2 STR, aber NPCs bemerken deine Schwäche)',
        'stat_bonus': {'strength': 2},
        'narrative_tags': ['hinkend', 'gebrechlich', 'verletzt']
    },
    {
        'id': 'scarred',
        'name': 'Extrem unattraktiv',
        'description': 'Schreckliche Narben entstellen dein Gesicht. (+2 INT, aber NPCs sind abgestoßen)',
        'stat_bonus': {'intelligence': 2},
        'narrative_tags': ['entstellt', 'hässlich', 'abstoßend']
    },
    {
        'id': 'haunted',
        'name': 'Wirre Gedanken',
        'description': 'Stimmen flüstern in deinem Kopf. (+2 INT, aber NPCs halten dich für verrückt)',
        'stat_bonus': {'intelligence': 2},
        'narrative_tags': ['wirr', 'verrückt', 'wahnsinnig']
    },
    {
        'id': 'paranoid',
        'name': 'Innere Zweifel',
        'description': 'Ständige Selbstzweifel plagen dich. (+2 WIS, aber NPCs spüren deine Unsicherheit)',
        'stat_bonus': {'wisdom': 2},
        'narrative_tags': ['unsicher', 'zweifelnd', 'ängstlich']
    },
    {
        'id': 'cursed_voice',
        'name': 'Verfluchte Stimme',
        'description': 'Deine Stimme klingt unheimlich. (+2 DEX, aber NPCs meiden Gespräche)',
        'stat_bonus': {'dexterity': 2},
        'narrative_tags': ['unheimlich', 'verstörend', 'gruselig']
    }
]

# GIFTS - Stat malus but secret mechanical bonus (discovered during gameplay)
GIFTS = [
    {
        'id': 'fire_resistant',
        'name': 'Feuerkind',
        'description': 'Du wurdest in der Nähe eines Vulkans geboren. (-1 WIS, +50% Feuerresistenz)',
        'stat_malus': {'wisdom': -1},
        'secret_bonus': {'fire_resistance': 0.5},
        'discovery_hint': 'Wenn du Feuerschaden nimmst, spürst du seltsamerweise nur ein Kribbeln...'
    },
    {
        'id': 'ice_touched',
        'name': 'Frostberührt',
        'description': 'Dein Blut ist unnatürlich kalt. (-1 STR, +50% Kälteresistenz)',
        'stat_malus': {'strength': -1},
        'secret_bonus': {'cold_resistance': 0.5},
        'discovery_hint': 'Eisige Kälte scheint dir nichts anzuhaben...'
    },
    {
        'id': 'acrobat',
        'name': 'Geborener Akrobat',
        'description': 'Dein Gleichgewichtssinn ist außergewöhnlich. (-1 INT, +2 auf DEX-Würfe)',
        'stat_malus': {'intelligence': -1},
        'secret_bonus': {'dexterity_rolls': 2},
        'discovery_hint': 'Deine Bewegungen sind geschmeidiger als du erwartet hast...'
    },
    {
        'id': 'perceptive',
        'name': 'Sechster Sinn',
        'description': 'Du spürst Dinge, die andere nicht sehen. (-1 STR, +2 auf WIS-Würfe)',
        'stat_malus': {'strength': -1},
        'secret_bonus': {'wisdom_rolls': 2},
        'discovery_hint': 'Deine Sinne erfassen Dinge, die anderen verborgen bleiben...'
    },
    {
        'id': 'lucky',
        'name': 'Glückskind',
        'description': 'Das Schicksal scheint dich zu begünstigen. (-1 DEX, kritische Treffer bei 19-20)',
        'stat_malus': {'dexterity': -1},
        'secret_bonus': {'crit_range': 19},
        'discovery_hint': 'Manchmal trifft deine Klinge perfekt, fast als wäre es vorherbestimmt...'
    },
    {
        'id': 'regenerative',
        'name': 'Schnellheilung',
        'description': 'Dein Körper heilt schneller als normal. (-1 INT, +1 HP pro Raum)',
        'stat_malus': {'intelligence': -1},
        'secret_bonus': {'hp_regen_per_room': 1},
        'discovery_hint': 'Deine Wunden schließen sich schneller als gewöhnlich...'
    }
]
