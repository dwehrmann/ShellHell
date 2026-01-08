"""Theme configuration system for dungeons."""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ThemeConfig:
    """Configuration for a dungeon theme."""

    # Basic info
    id: str  # Unique identifier
    name: str  # Display name
    description: str  # Short flavor text

    # Monsters
    monster_pool: List[Dict[str, Any]] = field(default_factory=list)  # Theme-specific monsters
    boss_monster: Optional[Dict[str, Any]] = None  # Optional boss for stairs room

    # Loot
    common_loot: List[Dict[str, Any]] = field(default_factory=list)  # Common item templates
    rare_loot: List[Dict[str, Any]] = field(default_factory=list)  # Rare item templates

    # Environmental hazards
    hazards: List[str] = field(default_factory=list)  # Environmental dangers
    hazard_chance: float = 0.1  # Chance per room

    # NPCs
    npc_variants: List[str] = field(default_factory=list)  # Which NPC types fit this theme

    # Atmosphere
    ambient_effects: List[str] = field(default_factory=list)  # Background flavor
    room_prefixes: List[str] = field(default_factory=list)  # For room generation variety


# Theme Registry
THEME_CONFIGS = {
    "dwarf_halls": ThemeConfig(
        id="dwarf_halls",
        name="Verlassene Zwergenhalle",
        description="Uralte Steinhallen der Zwerge, verlassen und verflucht",
        monster_pool=[
            {"name": "Steingolem", "hp": 35, "attack": 6, "defense": 8},
            {"name": "Verfluchter Zwerg", "hp": 25, "attack": 7, "defense": 4},
            {"name": "Erzgeist", "hp": 20, "attack": 5, "defense": 3},
            {"name": "Höhlenspinne", "hp": 15, "attack": 4, "defense": 2},
            {"name": "Runenwächter", "hp": 28, "attack": 6, "defense": 6},
            {"name": "Schmiedefluch", "hp": 18, "attack": 8, "defense": 1},
            {"name": "Basaltkriecher", "hp": 22, "attack": 5, "defense": 5},
            {"name": "Eisenbiss-Käfer", "hp": 14, "attack": 4, "defense": 4},
            {"name": "Bergwerks-Spuk", "hp": 16, "attack": 6, "defense": 2},
            {"name": "Schlackenschlund", "hp": 26, "attack": 7, "defense": 4},
            {"name": "Ahnenschmied", "hp": 24, "attack": 6, "defense": 4},
            {"name": "Mythril-Sentinel", "hp": 32, "attack": 7, "defense": 7},
            {"name": "Schattenschürfer", "hp": 20, "attack": 6, "defense": 3},
            {"name": "Steinmetz-Phantom", "hp": 18, "attack": 5, "defense": 5},
            {"name": "Kettenhaken-Wicht", "hp": 16, "attack": 7, "defense": 2},
            {"name": "Schieferpirscher", "hp": 19, "attack": 6, "defense": 4},
            {"name": "Kohlenruß-Elementar", "hp": 27, "attack": 7, "defense": 3},
            {"name": "Obsidianwurm", "hp": 33, "attack": 8, "defense": 5},
        ],
        boss_monster={"name": "Steinkönig", "hp": 60, "attack": 10, "defense": 10},
        common_loot=[
            {"name": "Zwergen-Bier", "type": "consumable", "stats": {"hp": 10}},
            {"name": "Eisenerz-Klumpen", "type": "material", "stats": {}},
            {"name": "Mythril-Pulver", "type": "material", "stats": {}},
            {"name": "Schmiede-Öl", "type": "consumable", "stats": {"attack": 1}},
            {"name": "Runenstaub", "type": "material", "stats": {}},
            {"name": "Kohlenstück", "type": "material", "stats": {}},
            {"name": "Salzstein", "type": "material", "stats": {}},
            {"name": "Zwergen-Zwieback", "type": "consumable", "stats": {"hp": 5}},
            {"name": "Hammerstiel", "type": "material", "stats": {}},
            {"name": "Zinnbarren", "type": "material", "stats": {}},
            {"name": "Kupfernieten", "type": "material", "stats": {}},
            {"name": "Schlackeprobe", "type": "material", "stats": {}},
            {"name": "Gelehrtenkreide", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Wetzstein", "type": "consumable", "stats": {"attack": 1}},
            {"name": "Seilbündel", "type": "material", "stats": {}},
        ],
        rare_loot=[
            {"name": "Zwergenaxt", "type": "weapon", "stats": {"attack": 5}},
            {"name": "Steinschild", "type": "armor", "stats": {"defense": 6}},
            {"name": "Runenhammer", "type": "weapon", "stats": {"attack": 4, "wisdom": 1}},
            {"name": "Mythrilring", "type": "ring", "stats": {"defense": 2}},
            {"name": "Helm der Tiefen", "type": "head", "stats": {"defense": 2, "hp": 5}},
            {"name": "Kettenpanzer der Gilde", "type": "armor", "stats": {"defense": 5}},
            {"name": "Stollenstiefel", "type": "armor", "stats": {"defense": 2, "dexterity": 1}},
            {"name": "Ahnentalisman", "type": "ring", "stats": {"wisdom": 2}},
            {"name": "Brustplatte aus Basalt", "type": "armor", "stats": {"defense": 4, "hp": 6}},
            {"name": "Schlüssel des Throns", "type": "consumable", "stats": {"wisdom": 1}},
        ],
        hazards=[
            "Einsturzgefahr",
            "Lavafluss",
            "Giftgase aus Spalten",
            "Klingenpendel",
            "Runenentladung",
            "Magnetische Erzfelder",
            "Lockende Echo-Stimmen",
            "Splitternde Brücken",
            "Fallende Steinplatten",
            "Heißer Schlackeregen",
            "Drehende Zahnradtür",
            "Kettenzug reißt",
        ],
        npc_variants=["guard", "merchant", "hermit", "scholar", "priest", "smith", "miner", "engineer", "scout"],
        ambient_effects=[
            "Das Echo von Schmiedehämmern hallt aus der Ferne",
            "Runen an den Wänden glühen schwach",
            "Ein leises Kratzen am Fels",
            "In der Ferne hört man einen der riesigen Blasebälge",
            "Schleifende Schritte auf steinernen Stufen",
            "Der Geruch von Schwefel und Metall",
            "Feiner Metallstaub glitzert im Licht",
            "Ein entferntes Dröhnen wie von rollenden Steinen",
            "Kalte Luftzüge aus unsichtbaren Schächten",
            "Die eigene Stimme klingt fremd",
            "Ein Hammer fällt irgendwo zu Boden",
            "Wasser tropft in tiefen Schächten",
            "Ein Funkenregen flackert kurz auf",
        ],
        room_prefixes=[
            "Alte Schmiede", "Thronsaal", "Erzmine", "Waffenkammer",
            "Runenarchiv", "Schmelzofen", "Hall der Ahnen", "Einsturzschacht",
            "Bergwerkstunnel", "Quarantäne-Kaverne", "Gildenhalle", "Schleusentor",
            "Zahnradgalerie", "Schlackebecken", "Brückenhalle", "Kristallader"
        ]
    ),

    "orc_cave": ThemeConfig(
        id="orc_cave",
        name="Höhle des Orkhäuptlings",
        description="Brutale Kriegshöhle voller wilder Orks",
        monster_pool=[
            {"name": "Ork-Krieger", "hp": 30, "attack": 8, "defense": 3},
            {"name": "Ork-Späher", "hp": 20, "attack": 6, "defense": 2},
            {"name": "Höhlenwolf", "hp": 25, "attack": 7, "defense": 3},
            {"name": "Goblin-Sklave", "hp": 12, "attack": 3, "defense": 1},
            {"name": "Ork-Berserker", "hp": 34, "attack": 10, "defense": 2},
            {"name": "Ork-Schamane", "hp": 22, "attack": 5, "defense": 2},
            {"name": "Knochensammler", "hp": 18, "attack": 6, "defense": 4},
            {"name": "Bluthund", "hp": 24, "attack": 8, "defense": 2},
            {"name": "Trommelwächter", "hp": 28, "attack": 7, "defense": 4},
            {"name": "Ork-Harpunier", "hp": 26, "attack": 8, "defense": 3},
            {"name": "Goblin-Fackelträger", "hp": 14, "attack": 4, "defense": 1},
            {"name": "Ork-Kettenwerfer", "hp": 24, "attack": 7, "defense": 4},
            {"name": "Höhlenoger", "hp": 45, "attack": 11, "defense": 4},
            {"name": "Fleischer", "hp": 29, "attack": 9, "defense": 3},
            {"name": "Stammeshexer", "hp": 20, "attack": 9, "defense": 1},
            {"name": "Warg-Reiter", "hp": 38, "attack": 10, "defense": 4},
            {"name": "Spießmeister", "hp": 32, "attack": 9, "defense": 5},
        ],
        boss_monster={"name": "Orkhäuptling", "hp": 70, "attack": 12, "defense": 5},
        common_loot=[
            {"name": "Blutiges Fleisch", "type": "consumable", "stats": {"hp": 5}},
            {"name": "Kriegsbemalung", "type": "consumable", "stats": {"attack": 1}},
            {"name": "Zerbeulter Helm", "type": "armor", "stats": {"defense": 1}},
            {"name": "Trophäenzahn", "type": "material", "stats": {}},
            {"name": "Rauchsalz", "type": "consumable", "stats": {"dexterity": 1}},
            {"name": "Grobverband", "type": "consumable", "stats": {"hp": 4}},
            {"name": "Wetzknochen", "type": "consumable", "stats": {"attack": 1}},
            {"name": "Schwarzer Teer", "type": "material", "stats": {}},
            {"name": "Speerschaft", "type": "material", "stats": {}},
            {"name": "Ranziger Talg", "type": "material", "stats": {}},
        ],
        rare_loot=[
            {"name": "Ork-Streitaxt", "type": "weapon", "stats": {"attack": 6}},
            {"name": "Knochenrüstung", "type": "armor", "stats": {"defense": 4}},
            {"name": "Schamanentotem", "type": "ring", "stats": {"wisdom": 2}},
            {"name": "Kettenhaken", "type": "weapon", "stats": {"attack": 4, "dexterity": 1}},
            {"name": "Kriegstrommel-Fetisch", "type": "consumable", "stats": {"attack": 2}},
            {"name": "Wargleder-Weste", "type": "armor", "stats": {"defense": 3, "dexterity": 1}},
            {"name": "Maske des Stammes", "type": "head", "stats": {"defense": 2, "wisdom": 1}},
            {"name": "Blutrote Klinge", "type": "weapon", "stats": {"attack": 5, "hp": 3}},
            {"name": "Feldzeichen des Häuptlings", "type": "ring", "stats": {"attack": 2}},
        ],
        hazards=[
            "Fallgruben mit Spießen",
            "Alarm-Trommeln",
            "Wachposten",
            "Rauchkammer",
            "Schädelwarnsystem",
            "Schlechte Stützbalken",
            "Brandgruben",
            "Stacheldrahtgänge",
            "Knochenrutsch",
            "Pechtöpfe",
            "Schreigrube",
        ],
        npc_variants=["hermit", "priest", "merchant", "guard", "smith", "scout", "shaman", "slave", "tracker"],
        ambient_effects=[
            "Kriegstrommeln dröhnen in der Ferne",
            "Der Gestank von Blut und Schweiß",
            "Rauhe, kehlige Gesänge hallen durch die Höhle",
            "Laute Schmerzensschreie dringen durch die Wand",
            "Knochen klacken unter den Stiefeln",
            "Ein entferntes Grunzen, als würden Tiere gefüttert",
            "Fackeln knistern und werfen wilde Schatten",
            "Metall schlägt auf Stein",
            "Ein Wolf heult aus der Tiefe",
            "Ein Schlachtermesser schabt über Holz",
        ],
        room_prefixes=[
            "Kriegslager", "Sklavenpferch", "Waffenlager", "Thronsaal",
            "Schamanengrube", "Folterzelle", "Beutestapel", "Speerwald",
            "Hundezwinger", "Plünderaltar", "Trommelschacht", "Knochenhof",
            "Rauchgang", "Wargstall", "Prügelplatz"
        ]
    ),

    "ruined_city": ThemeConfig(
        id="ruined_city",
        name="Verlassene Stadt",
        description="Eine tote Stadt, von Schatten heimgesucht",
        monster_pool=[
            {"name": "Schattengeist", "hp": 20, "attack": 6, "defense": 1},
            {"name": "Wandelnde Leiche", "hp": 25, "attack": 5, "defense": 3},
            {"name": "Verlorene Seele", "hp": 15, "attack": 7, "defense": 0},
            {"name": "Rattenplage", "hp": 18, "attack": 4, "defense": 2},
            {"name": "Glockenturm-Spuk", "hp": 22, "attack": 7, "defense": 2},
            {"name": "Aschehund", "hp": 20, "attack": 6, "defense": 3},
            {"name": "Zerfallener Wächter", "hp": 30, "attack": 6, "defense": 5},
            {"name": "Schattenschleicher", "hp": 16, "attack": 8, "defense": 1},
            {"name": "Krähen-Schwarm", "hp": 14, "attack": 5, "defense": 2},
            {"name": "Fenstergeist", "hp": 18, "attack": 6, "defense": 2},
            {"name": "Pestträger", "hp": 28, "attack": 7, "defense": 3},
            {"name": "Kettenleiche", "hp": 34, "attack": 7, "defense": 6},
            {"name": "Schattenlaterner", "hp": 19, "attack": 7, "defense": 1},
            {"name": "Nebelstrolch", "hp": 17, "attack": 6, "defense": 3},
            {"name": "Knochenhund", "hp": 24, "attack": 8, "defense": 2},
            {"name": "Zerrissener Henker", "hp": 36, "attack": 9, "defense": 4},
            {"name": "Spiegelgeist", "hp": 16, "attack": 8, "defense": 1},
        ],
        boss_monster={"name": "Schattenkönig", "hp": 50, "attack": 9, "defense": 2},
        common_loot=[
            {"name": "Altes Brot", "type": "consumable", "stats": {"hp": 3}},
            {"name": "Verblichenes Buch", "type": "consumable", "stats": {}},
            {"name": "Kerzenstummel", "type": "material", "stats": {}},
            {"name": "Rostiger Schlüssel", "type": "material", "stats": {}},
            {"name": "Fetzenmantel", "type": "armor", "stats": {"defense": 1}},
            {"name": "Heilkräuter", "type": "consumable", "stats": {"hp": 6}},
            {"name": "Splitterglas", "type": "material", "stats": {}},
            {"name": "Alte Münze", "type": "material", "stats": {}},
            {"name": "Band", "type": "material", "stats": {}},
            {"name": "Salbe", "type": "consumable", "stats": {"hp": 4}},
            {"name": "Stadtplanfetzen", "type": "consumable", "stats": {"wisdom": 1}},
        ],
        rare_loot=[
            {"name": "Gestohlener Ring", "type": "ring", "stats": {"wisdom": 2}},
            {"name": "Nachtwächter-Schwert", "type": "weapon", "stats": {"attack": 4}},
            {"name": "Laterne der Dämmerung", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Silberne Kette", "type": "ring", "stats": {"defense": 2}},
            {"name": "Mantel des Flüsterns", "type": "armor", "stats": {"dexterity": 2}},
            {"name": "Siegelring der Zunft", "type": "ring", "stats": {"intelligence": 2}},
            {"name": "Klinge des Torwächters", "type": "weapon", "stats": {"attack": 5, "defense": 1}},
            {"name": "Maske aus Porzellan", "type": "head", "stats": {"wisdom": 2, "defense": 1}},
            {"name": "Reliktkette", "type": "ring", "stats": {"hp": 8}},
        ],
        hazards=[
            "Einstürzende Gebäude",
            "Verfluchte Straßen",
            "Giftige Nebel",
            "Nachgebender Boden",
            "Spiegelnde Pfützen",
            "Heulende Böen",
            "Schwarzes Glas",
            "Kippende Balkone",
            "Schattenschlinge",
            "Rattenlöcher",
            "Glockenalarm",
            "Knochenfalle",
        ],
        npc_variants=["scholar", "hermit", "priest", "merchant", "guard", "healer", "thief", "scout", "undertaker"],
        ambient_effects=[
            "Wind pfeift durch zerbrochene Fenster",
            "Schritte hallen auf leerem Kopfsteinpflaster",
            "Der Mond wirft lange Schatten",
            "Eine entfernte Glocke schlägt ohne Hände",
            "Fensterläden klappern, obwohl kein Wind weht",
            "Ein kaltes Flüstern hängt zwischen den Gassen",
            "Nebel kriecht über den Boden",
            "Ein Schatten huscht im Augenwinkel",
            "Kalte Tropfen fallen aus Dachrinnen",
            "Krähen schreien über den Ruinen",
        ],
        room_prefixes=[
            "Marktplatz", "Bibliothek", "Stadttor", "Kathedrale",
            "Glockenturm", "Alchemistengasse", "Ratskeller", "Zerbrochene Brücke",
            "Verwaistes Hospital", "Wachtstube", "Schlachthaus", "Brunnenplatz",
            "Gerichtsruine", "Kutschenhof", "Zunfthalle"
        ]
    ),

    "sewer": ThemeConfig(
        id="sewer",
        name="Schmutziger Abwasserkanal",
        description="Ein stinkender Kanal voller Krankheit und Gift",
        monster_pool=[
            {"name": "Giftschleim", "hp": 28, "attack": 4, "defense": 6},
            {"name": "Kanalratte", "hp": 12, "attack": 3, "defense": 1},
            {"name": "Mutant", "hp": 30, "attack": 7, "defense": 2},
            {"name": "Fäulnisschwarm", "hp": 20, "attack": 5, "defense": 0},
            {"name": "Rattenkönig", "hp": 26, "attack": 6, "defense": 3},
            {"name": "Leichenfresser", "hp": 24, "attack": 7, "defense": 2},
            {"name": "Schlammkrabbe", "hp": 18, "attack": 5, "defense": 5},
            {"name": "Pilzbefallener", "hp": 22, "attack": 6, "defense": 3},
            {"name": "Abflussgeist", "hp": 16, "attack": 4, "defense": 4},
            {"name": "Rostling", "hp": 20, "attack": 6, "defense": 4},
            {"name": "Schachtkriecher", "hp": 15, "attack": 7, "defense": 2},
            {"name": "Schleimling", "hp": 19, "attack": 5, "defense": 5},
            {"name": "Pestwurm", "hp": 27, "attack": 7, "defense": 3},
            {"name": "Abwasserkröte", "hp": 18, "attack": 6, "defense": 3},
            {"name": "Knochenschwarm", "hp": 16, "attack": 5, "defense": 2},
        ],
        boss_monster={"name": "Kanalisationsbestie", "hp": 55, "attack": 8, "defense": 7},
        common_loot=[
            {"name": "Verdorbenes Wasser", "type": "consumable", "stats": {"hp": -3}},
            {"name": "Alchemie-Reagenz", "type": "material", "stats": {}},
            {"name": "Seifenkraut", "type": "consumable", "stats": {"hp": 2}},
            {"name": "Rattenpelz", "type": "material", "stats": {}},
            {"name": "Schmierfett", "type": "material", "stats": {}},
            {"name": "Kupferdraht", "type": "material", "stats": {}},
            {"name": "Harz", "type": "material", "stats": {}},
            {"name": "Kalk", "type": "material", "stats": {}},
            {"name": "Tuchfetzen", "type": "material", "stats": {}},
            {"name": "Salz", "type": "material", "stats": {}},
            {"name": "Bitterschlamm", "type": "material", "stats": {}},
        ],
        rare_loot=[
            {"name": "Giftdolch", "type": "weapon", "stats": {"attack": 4, "intelligence": 1}},
            {"name": "Lederhandschuhe", "type": "armor", "stats": {"defense": 2, "dexterity": 1}},
            {"name": "Atemmaske", "type": "head", "stats": {"defense": 1, "hp": 3}},
            {"name": "Schleimfeste Stiefel", "type": "armor", "stats": {"dexterity": 2}},
            {"name": "Phiole: Antitoxin", "type": "consumable", "stats": {"hp": 8}},
            {"name": "Kettennetz", "type": "armor", "stats": {"defense": 4}},
            {"name": "Rostschutz-Salbe", "type": "consumable", "stats": {"defense": 2}},
            {"name": "Schlüsselbund", "type": "consumable", "stats": {"wisdom": 1}},
        ],
        hazards=[
            "Giftiges Wasser",
            "Krankheiten",
            "Explosive Gase",
            "Dampfstöße",
            "Rutschige Algen",
            "Einbrechende Gitter",
            "Schwemmstrom",
            "Säurepfützen",
            "Saugschacht",
            "Rattenschwarmgang",
            "Kippende Stege",
        ],
        npc_variants=["hermit", "merchant", "scholar", "thief", "guard", "alchemist", "rat_catcher"],
        ambient_effects=[
            "Wasser tropft von verrosteten Rohren",
            "Der Gestank ist überwältigend",
            "Etwas Großes bewegt sich im Wasser",
            "Das Licht flackert",
            "Ein fernes Quietschen von Metall",
            "Blasen steigen aus schwarzem Wasser auf",
            "Ein kalter Luftzug kommt aus einem Seitenschacht",
            "Schritte platschen irgendwo in der Dunkelheit",
            "Rattenaugen blitzen kurz auf",
        ],
        room_prefixes=[
            "Sammelstelle", "Filterraum", "Abflussrohr", "Pumpstation",
            "Wartungstunnel", "Überlaufbecken", "Schieberkammer", "Schlammgrube",
            "Ventilsaal", "Käfigschleuse", "Geröllsiphon", "Rostkammer"
        ]
    ),

    "pyramid": ThemeConfig(
        id="pyramid",
        name="Mystische Pyramide",
        description="Eine uralte Pyramide voller verfluchter Schätze",
        monster_pool=[
            {"name": "Mumie", "hp": 32, "attack": 6, "defense": 4},
            {"name": "Skorpion-Wächter", "hp": 25, "attack": 8, "defense": 3},
            {"name": "Skarabäenschwarm", "hp": 18, "attack": 5, "defense": 1},
            {"name": "Verfluchte Statue", "hp": 40, "attack": 4, "defense": 8},
            {"name": "Sandgeist", "hp": 20, "attack": 7, "defense": 2},
            {"name": "Grabwächter", "hp": 28, "attack": 6, "defense": 6},
            {"name": "Kobra-Priester", "hp": 22, "attack": 8, "defense": 2},
            {"name": "Hieroglyphen-Schrecken", "hp": 16, "attack": 5, "defense": 3},
            {"name": "Dünenjäger", "hp": 24, "attack": 7, "defense": 3},
            {"name": "Goldschakal", "hp": 22, "attack": 7, "defense": 3},
            {"name": "Sarkophag-Spuk", "hp": 18, "attack": 8, "defense": 1},
            {"name": "Sonnenspeer-Wächter", "hp": 30, "attack": 8, "defense": 5},
            {"name": "Auge des Tempels", "hp": 14, "attack": 9, "defense": 0},
            {"name": "Staubkobra", "hp": 16, "attack": 6, "defense": 2},
            {"name": "Goldskarabäus", "hp": 20, "attack": 5, "defense": 5},
            {"name": "Ritualklinge-Träger", "hp": 26, "attack": 9, "defense": 3},
        ],
        boss_monster={"name": "Pharao-Lich", "hp": 65, "attack": 10, "defense": 6},
        common_loot=[
            {"name": "Kanopen-Öl", "type": "consumable", "stats": {"hp": 8}},
            {"name": "Goldener Skarabäus", "type": "material", "stats": {}},
            {"name": "Bandagenrolle", "type": "consumable", "stats": {"hp": 5}},
            {"name": "Wüstenharz", "type": "material", "stats": {}},
            {"name": "Bronze-Amulett", "type": "material", "stats": {}},
            {"name": "Kleiner Obsidian", "type": "material", "stats": {}},
            {"name": "Opferrauch", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Grabsand", "type": "material", "stats": {}},
            {"name": "Goldflitter", "type": "material", "stats": {}},
            {"name": "Kalksteinfragment", "type": "material", "stats": {}},
            {"name": "Hieroglyphenfetzen", "type": "consumable", "stats": {"intelligence": 1}},
        ],
        rare_loot=[
            {"name": "Anubis-Stab", "type": "weapon", "stats": {"attack": 5, "wisdom": 2}},
            {"name": "Pharao-Maske", "type": "head", "stats": {"defense": 3, "intelligence": 3}},
            {"name": "Krummsäbel der Dämmerung", "type": "weapon", "stats": {"attack": 4, "dexterity": 2}},
            {"name": "Skarabäus-Ring", "type": "ring", "stats": {"wisdom": 1, "defense": 1}},
            {"name": "Goldschuppen-Panzer", "type": "armor", "stats": {"defense": 5}},
            {"name": "Sonnentalisman", "type": "ring", "stats": {"hp": 10}},
            {"name": "Kobrahelm", "type": "head", "stats": {"defense": 2, "wisdom": 2}},
            {"name": "Obsidian-Klinge", "type": "weapon", "stats": {"attack": 6}},
        ],
        hazards=[
            "Sandfallen",
            "Flüche",
            "Wandernde Wächter",
            "Drehwände",
            "Speerplatten",
            "Augenidole",
            "Giftpfeile",
            "Sarkophag-Siegel",
            "Schräge Sandrutschen",
            "Steinblock-Rollgänge",
            "Falsche Schätze",
        ],
        npc_variants=["scholar", "priest", "hermit", "merchant", "grave_robber", "guide"],
        ambient_effects=[
            "Hieroglyphen glühen an den Wänden",
            "Sand rieselt aus Ritzen",
            "Ein uralter Fluch liegt schwer in der Luft",
            "Die Luft ist trocken wie altes Papier",
            "Ein leises Rascheln gleitet über Stein",
            "Schritte klingen gedämpft",
            "Ein kalter Hauch weht aus einer versiegelten Kammer",
            "Ein fernes Klacken von Mechanismen",
            "Goldstaub glimmt kurz im Fackellicht",
        ],
        room_prefixes=[
            "Grabkammer", "Opferraum", "Schatzkammer", "Thronsaal",
            "Sternenschacht", "Mumienlager", "Priesterzelle", "Obsidianhalle",
            "Waage der Seelen", "Sonnentor", "Geheimgang", "Versiegelte Galerie",
            "Sarkophaghalle", "Schattensaal"
        ]
    ),

    "burned_castle": ThemeConfig(
        id="burned_castle",
        name="Verbrannte Schlossruine",
        description="Verkohlte Mauern, zerborstene Türme und ein Fluch in der Asche",
        monster_pool=[
            {"name": "Ascheritter", "hp": 34, "attack": 9, "defense": 5},
            {"name": "Rußgeist", "hp": 18, "attack": 7, "defense": 1},
            {"name": "Brandwürger", "hp": 22, "attack": 8, "defense": 2},
            {"name": "Kohlenhund", "hp": 24, "attack": 8, "defense": 3},
            {"name": "Verkohlter Bogenschütze", "hp": 20, "attack": 8, "defense": 2},
            {"name": "Schwelender Diener", "hp": 26, "attack": 7, "defense": 4},
            {"name": "Aschekrähe", "hp": 14, "attack": 5, "defense": 1},
            {"name": "Mauerkriecher", "hp": 19, "attack": 6, "defense": 4},
            {"name": "Fackelspuk", "hp": 16, "attack": 8, "defense": 0},
            {"name": "Schuttgolem", "hp": 38, "attack": 7, "defense": 8},
            {"name": "Glutwache", "hp": 28, "attack": 8, "defense": 5},
            {"name": "Kettengeist", "hp": 20, "attack": 7, "defense": 3},
            {"name": "Brandalchemist", "hp": 18, "attack": 9, "defense": 1},
            {"name": "Schwarzer Bannerträger", "hp": 30, "attack": 8, "defense": 4},
            {"name": "Schornsteinwurm", "hp": 24, "attack": 7, "defense": 4},
        ],
        boss_monster={"name": "Der Aschefürst", "hp": 85, "attack": 13, "defense": 8},
        common_loot=[
            {"name": "Aschebeutel", "type": "material", "stats": {}},
            {"name": "Rußsalbe", "type": "consumable", "stats": {"hp": 5}},
            {"name": "Brandöl", "type": "consumable", "stats": {"attack": 1}},
            {"name": "Verkohlter Schlüssel", "type": "material", "stats": {}},
            {"name": "Zerrissene Standarte", "type": "material", "stats": {}},
            {"name": "Altes Siegelwachs", "type": "material", "stats": {}},
            {"name": "Kohlenstück", "type": "material", "stats": {}},
            {"name": "Flaschenpost", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Gürtelschnalle", "type": "material", "stats": {}},
            {"name": "Wachsbündel", "type": "material", "stats": {}},
        ],
        rare_loot=[
            {"name": "Flamberge des Pyromanenkönigs", "type": "weapon", "stats": {"attack": 7, "wisdom": -3}},
            {"name": "Helm der Brandwache", "type": "head", "stats": {"defense": 3, "hp": 5}},
            {"name": "Umhang aus Aschefilz", "type": "armor", "stats": {"defense": 3, "dexterity": 2}},
            {"name": "Ring des letzten Schwurs", "type": "ring", "stats": {"wisdom": 2}},
            {"name": "Feuergehärteter Schild", "type": "armor", "stats": {"defense": 6}},
            {"name": "Glutdolch", "type": "weapon", "stats": {"attack": 4, "intelligence": 2}},
        ],
        hazards=[
            "Kollabierende Balken",
            "Schwelende Böden",
            "Einstürzende Treppen",
            "Schwarzer Rauch",
            "Versteckte Schießscharten",
            "Fallende Steine",
            "Glutnester",
            "Rutschige Asche",
            "Kettenzug-Fallen",
            "Brüchige Zinnen",
            "Verriegelte Brandtüren",
        ],
        npc_variants=["guard", "merchant", "hermit", "scholar", "priest", "knight", "scout", "blacksmith", "refugee"],
        ambient_effects=[
            "Asche wirbelt bei jedem Schritt auf",
            "Der Geruch von verbranntem Holz hängt in den Steinen",
            "Ferne Funken glimmen im Schutt",
            "Ein Turm knarrt im Wind",
            "Kalte Zugluft pfeift durch Pfeilspalten",
            "Ein Schild klappert irgendwo gegen Mauerwerk",
            "Flammen spiegeln sich, obwohl keine brennen",
            "Schwarzer Rauch zieht aus einem Riss im Boden",
            "Ein leises Knistern kommt aus den Wänden",
        ],
        room_prefixes=[
            "Zerborstener Turm", "Königshalle", "Brandhof", "Kapellenruine",
            "Waffenkammer", "Küche", "Kerker", "Zinnenweg",
            "Geheimgang", "Wachtstube", "Stallruine", "Archivkammer"
        ]
    ),

    "dark_crypt": ThemeConfig(
        id="dark_crypt",
        name="Dunkle Gruft",
        description="Kaltes Steinlabyrinth voller Knochen, Verfall und alter Flüche",
        monster_pool=[
            {"name": "Skelettwächter", "hp": 22, "attack": 6, "defense": 4},
            {"name": "Grabgeist", "hp": 18, "attack": 8, "defense": 1},
            {"name": "Knochenmagier", "hp": 20, "attack": 9, "defense": 2},
            {"name": "Leichendiener", "hp": 26, "attack": 6, "defense": 3},
            {"name": "Schattenpriester", "hp": 24, "attack": 8, "defense": 3},
            {"name": "Knochenschildträger", "hp": 28, "attack": 6, "defense": 6},
            {"name": "Grabspinne", "hp": 16, "attack": 5, "defense": 3},
            {"name": "Kerzenwurm", "hp": 14, "attack": 6, "defense": 2},
            {"name": "Seelenfänger", "hp": 20, "attack": 7, "defense": 4},
            {"name": "Sarkophagritter", "hp": 34, "attack": 9, "defense": 6},
            {"name": "Nekrochor", "hp": 18, "attack": 7, "defense": 1},
            {"name": "Würgewicht", "hp": 30, "attack": 8, "defense": 5},
            {"name": "Knochenschwarm", "hp": 16, "attack": 5, "defense": 2},
            {"name": "Grabklingenträger", "hp": 24, "attack": 9, "defense": 3},
            {"name": "Totenhüter", "hp": 32, "attack": 8, "defense": 7},
        ],
        boss_monster={"name": "Der Grabkönig", "hp": 82, "attack": 12, "defense": 9},
        common_loot=[
            {"name": "Grabkerze", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Salzbeutel", "type": "material", "stats": {}},
            {"name": "Knochensplitter", "type": "material", "stats": {}},
            {"name": "Schwarzband", "type": "material", "stats": {}},
            {"name": "Segenwasser", "type": "consumable", "stats": {"hp": 6}},
            {"name": "Rostige Kette", "type": "material", "stats": {}},
            {"name": "Grabstaub", "type": "material", "stats": {}},
            {"name": "Zerbrochener Siegelring", "type": "material", "stats": {}},
            {"name": "Leichenleinen", "type": "material", "stats": {}},
            {"name": "Mumiennadel", "type": "material", "stats": {}},
        ],
        rare_loot=[
            {"name": "Klinge der Gruft", "type": "weapon", "stats": {"attack": 6, "wisdom": 1}},
            {"name": "Schild des Eids", "type": "armor", "stats": {"defense": 6}},
            {"name": "Maske der Stille", "type": "head", "stats": {"defense": 2, "intelligence": 2}},
            {"name": "Ring der Schwelle", "type": "ring", "stats": {"hp": 8, "wisdom": 1}},
            {"name": "Mantel der Totenruhe", "type": "armor", "stats": {"defense": 4, "dexterity": 1}},
            {"name": "Gebetbuch der Finsternis", "type": "consumable", "stats": {"intelligence": 2}},
        ],
        hazards=[
            "Druckplatten",
            "Klingenwände",
            "Knochenstaub",
            "Fluchrunen",
            "Sarkophag-Alarme",
            "Fallgitter",
            "Einstürzende Gewölbe",
            "Irreführende Echos",
            "Schwarze Pfützen",
            "Seelenkorridore",
            "Versiegelte Türen",
        ],
        npc_variants=["priest", "scholar", "hermit", "grave_robber", "exorcist", "guard"],
        ambient_effects=[
            "Kalte Luft klebt an der Haut",
            "Kerzen flackern ohne Wind",
            "Ein fernes Murmeln zieht durch den Stein",
            "Knochen knacken unter den Stiefeln",
            "Ein metallisches Kratzen hallt durch einen Gang",
            "Feiner Staub rieselt von der Decke",
            "Ein leiser Choral kommt aus einer verschlossenen Kammer",
            "Der Geruch von Wachs und altem Eisen",
            "Ein Schatten bewegt sich, obwohl nichts da ist",
        ],
        room_prefixes=[
            "Sarkophaghalle", "Knochenkammer", "Eidgang", "Versiegeltes Heiligtum",
            "Katakombenweg", "Opferplatte", "Grabkapelle", "Wächterraum",
            "Schacht der Stille", "Schlüsselkammer", "Totensaal", "Schriftgewölbe"
        ]
    ),

    "tavern_cellar": ThemeConfig(
        id="tavern_cellar",
        name="Altes Kellergewölbe unter der Taverne",
        description="Feuchte Kellergänge, Schmugglerpfade und vergessene Geheimnisse",
        monster_pool=[
            {"name": "Riesenkellerassel", "hp": 16, "attack": 4, "defense": 4},
            {"name": "Fasskobold", "hp": 14, "attack": 5, "defense": 2},
            {"name": "Kellergeist", "hp": 18, "attack": 7, "defense": 1},
            {"name": "Schmugglerhand", "hp": 20, "attack": 6, "defense": 3},
            {"name": "Rattenschwarm", "hp": 18, "attack": 4, "defense": 2},
            {"name": "Schimmelgolem", "hp": 24, "attack": 5, "defense": 5},
            {"name": "Bierhexe", "hp": 18, "attack": 8, "defense": 1},
            {"name": "Kellerkriecher", "hp": 20, "attack": 6, "defense": 4},
            {"name": "Brennspiritus-Spuk", "hp": 16, "attack": 7, "defense": 2},
            {"name": "Ziegelwächter", "hp": 28, "attack": 6, "defense": 7},
            {"name": "Kettenratte", "hp": 22, "attack": 7, "defense": 3},
            {"name": "Spunddämon", "hp": 26, "attack": 8, "defense": 4},
            {"name": "Schattenwirt", "hp": 24, "attack": 7, "defense": 4},
            {"name": "Bottichschlurfer", "hp": 20, "attack": 6, "defense": 5},
            {"name": "Fackelträger", "hp": 18, "attack": 6, "defense": 2},
        ],
        boss_monster={"name": "Der Kellermeister", "hp": 70, "attack": 11, "defense": 7},
        common_loot=[
            {"name": "Brotkruste", "type": "consumable", "stats": {"hp": 3}},
            {"name": "Käsestück", "type": "consumable", "stats": {"hp": 4}},
            {"name": "Kellerbier", "type": "consumable", "stats": {"hp": 6}},
            {"name": "Kerze", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Korkenbeutel", "type": "material", "stats": {}},
            {"name": "Schlüssel (alt)", "type": "material", "stats": {}},
            {"name": "Schnurrolle", "type": "material", "stats": {}},
            {"name": "Schmugglerzettel", "type": "consumable", "stats": {"intelligence": 1}},
            {"name": "Münzbeutel", "type": "material", "stats": {}},
            {"name": "Salzfassprobe", "type": "material", "stats": {}},
            {"name": "Flasche: Essig", "type": "consumable", "stats": {"hp": 2}},
        ],
        rare_loot=[
            {"name": "Kellermesser", "type": "weapon", "stats": {"attack": 4, "dexterity": 1}},
            {"name": "Lederwams des Schmugglers", "type": "armor", "stats": {"defense": 3, "dexterity": 1}},
            {"name": "Ring der Tresenwache", "type": "ring", "stats": {"defense": 2}},
            {"name": "Schlüssel des Geheimfachs", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Flasche: Starkbrand", "type": "consumable", "stats": {"attack": 2}},
            {"name": "Umhang aus Sackleinen", "type": "armor", "stats": {"defense": 2, "hp": 4}},
        ],
        hazards=[
            "Rutschige Steine",
            "Schimmelsporen",
            "Einstürzende Regale",
            "Verknotete Gänge",
            "Dünne Fässerböden",
            "Brennspiritus-Pfützen",
            "Stacheldraht im Schmugglergang",
            "Fallkisten",
            "Zuglufttüren",
            "Falsche Wand",
        ],
        npc_variants=["merchant", "hermit", "thief", "guard", "bartender", "smuggler", "cook", "rat_catcher"],
        ambient_effects=[
            "Es riecht nach Bier, Holz und kaltem Stein",
            "Wasser tropft von Gewölbebögen",
            "Ratten huschen zwischen Fässern",
            "Ein Fass knackt, als würde es atmen",
            "Flammen flackern und werfen tanzende Schatten",
            "Ein fernes Lachen dringt durch die Decke",
            "Glas klirrt irgendwo im Dunkeln",
            "Ein kalter Hauch zieht aus einem Spalt",
            "Der Boden vibriert kurz, als würde oben jemand tanzen",
        ],
        room_prefixes=[
            "Fasslager", "Gewürzkammer", "Schmugglergang", "Käsekeller",
            "Brennraum", "Alte Zisterne", "Kistenlager", "Ziegelbogen",
            "Geheime Nische", "Wartungsloch", "Rattennest", "Hinterzimmer"
        ]
    ),

    "forgotten_graveyard": ThemeConfig(
        id="forgotten_graveyard",
        name="Vergessener Friedhof",
        description="Nebel zwischen Grabsteinen, zerbrochene Engel und eine Nacht ohne Ende",
        monster_pool=[
            {"name": "Nebelgeist", "hp": 18, "attack": 7, "defense": 1},
            {"name": "Grabschleicher", "hp": 22, "attack": 8, "defense": 2},
            {"name": "Knochengräber", "hp": 26, "attack": 7, "defense": 4},
            {"name": "Witwenkrähe", "hp": 14, "attack": 5, "defense": 2},
            {"name": "Grabwurm", "hp": 28, "attack": 6, "defense": 5},
            {"name": "Verfluchter Totengräber", "hp": 30, "attack": 8, "defense": 4},
            {"name": "Gargoyle-Schatten", "hp": 24, "attack": 7, "defense": 6},
            {"name": "Mausoleumwächter", "hp": 34, "attack": 8, "defense": 7},
            {"name": "Seelenhund", "hp": 24, "attack": 9, "defense": 3},
            {"name": "Grabkerzen-Spuk", "hp": 16, "attack": 8, "defense": 0},
            {"name": "Schädelreiter", "hp": 32, "attack": 10, "defense": 4},
            {"name": "Efeuklinge", "hp": 20, "attack": 7, "defense": 4},
        ],
        boss_monster={"name": "Die Witwenkönigin", "hp": 78, "attack": 12, "defense": 7},
        common_loot=[
            {"name": "Grabblume", "type": "material", "stats": {}},
            {"name": "Salzkranz", "type": "material", "stats": {}},
            {"name": "Kerzenstummel", "type": "material", "stats": {}},
            {"name": "Gebetsfetzen", "type": "consumable", "stats": {"wisdom": 1}},
            {"name": "Schaufelspitze", "type": "material", "stats": {}},
            {"name": "Altes Medaillon", "type": "material", "stats": {}},
            {"name": "Segenwasser", "type": "consumable", "stats": {"hp": 6}},
            {"name": "Knochenstaub", "type": "material", "stats": {}},
        ],
        rare_loot=[
            {"name": "Mausoleumklinge", "type": "weapon", "stats": {"attack": -5, "dexterity": 7}},
            {"name": "Ring der Dämmerung", "type": "ring", "stats": {"dexterity": 2}},
            {"name": "Kapuze des Totengräbers", "type": "head", "stats": {"defense": -2, "wisdom": 4}},
            {"name": "Schutzamulett", "type": "ring", "stats": {"defense": 3}},
            {"name": "Mantel aus Nebelstoff", "type": "armor", "stats": {"defense": 2, "dexterity": 2}},
        ],
        hazards=[
            "Nebelwände",
            "Aufbrechende Gräber",
            "Versinkende Erde",
            "Dornenhecken",
            "Glockenläuten",
            "Kalte Flüche",
            "Schiefe Grabplatten",
            "Mausoleumsiegel",
            "Rabenalarm",
        ],
        npc_variants=["priest", "hermit", "grave_robber", "guard", "healer", "undertaker", "scholar"],
        ambient_effects=[
            "Nebel liegt schwer zwischen Grabsteinen",
            "Eine entfernte Glocke schlägt dreizehn mal",
            "Flammen in Laternen flackern ohne Kerze",
            "Der Boden fühlt sich kühl und lebendig an",
            "Krähen kreisen lautlos über dem Mond",
            "Ein steinerner Engelskopf liegt zerbrochen im Gras",
            "Ein Grabstein steht schief",
            "Ein leises Scharren kommt aus der Erde",
        ],
        room_prefixes=[
            "Grabfeld", "Mausoleum", "Engelhof", "Totenweg",
            "Kapellenruine", "Kryptaeingang", "Beinhaus", "Gärtnerhaus",
            "Steinkreis", "Torhaus", "Nebelgarten"
        ]
    ),
}



def get_theme_config(theme_name: str) -> Optional[ThemeConfig]:
    """
    Get theme configuration by name.

    Args:
        theme_name: The theme display name

    Returns:
        ThemeConfig or None if not found
    """
    # Try exact match by name
    for config in THEME_CONFIGS.values():
        if config.name == theme_name:
            return config

    # Try by ID
    if theme_name in THEME_CONFIGS:
        return THEME_CONFIGS[theme_name]

    return None


def get_random_theme() -> ThemeConfig:
    """Get a random theme configuration."""
    import random
    return random.choice(list(THEME_CONFIGS.values()))
