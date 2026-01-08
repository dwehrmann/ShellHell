# ShellHell - Terminal Dungeon Crawler

Ein Terminal-basierter Dungeon Crawler mit KI-generiertem Content (Google Gemini).

## Installation

```bash
# Virtual Environment wird automatisch erstellt beim ersten Start
./run.sh
```

Oder manuell:

```bash
python -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python main.py
```

## AI Provider Setup (Optional)

Das Spiel unterstützt mehrere AI-Provider für dynamische Raumbeschreibungen.

### 1. Provider wählen

Bearbeite `.env` und wähle deinen Provider:

```bash
# Optionen: gemini, deepseek, openai
AI_PROVIDER=gemini
```

### 2. API-Key eintragen

**Option A: Gemini (Standard, kostenlos)**
- Kostenlos bis 1500 Requests/Tag
- API Key von: https://aistudio.google.com/apikey
```
GEMINI_API_KEY=dein_gemini_key
```

**Option B: DeepSeek (sehr günstig)**
- ~$0.14 / 1M tokens (95% günstiger als GPT-4)
- API Key von: https://platform.deepseek.com/
```
DEEPSEEK_API_KEY=dein_deepseek_key
```

**Option C: OpenAI**
- GPT-5-mini: $0.15 / 1M tokens
- API Key von: https://platform.openai.com/api-keys
```
OPENAI_API_KEY=dein_openai_key
# Optional: Model wählen (default: gpt-5-mini)
OPENAI_MODEL=gpt-5-mini
```

**Hinweis:** Das Spiel läuft auch ohne API-Key mit statischen Fallback-Texten. <- Not recommended!

## Steuerung

### Start & Charaktererstellung
- `start` oder `s` - Spiel starten
- Attribute würfeln: `b` zum Bestätigen, beliebige Taste zum neu würfeln
- Rasse wählen: `m` (Mensch), `o` (Halbork), `e` (Elf), `h` (Halbelf), `g` (Gnom)
- Namen eingeben

### Exploration
- `n` - Norden
- `s` - Süden
- `o` - Osten
- `w` - Westen
- `i` oder `inventar` - Inventar anzeigen
- `status` - Status anzeigen
- `hilfe` oder `h` - Hilfe

### Kampf
- `a` oder `angriff` - Angreifen

### Allgemein
- `quit` oder `q` - Spiel beenden

## Features

- **KI-generierte Inhalte**: Dynamische Raumbeschreibungen und Story (mit API-Key)
- **Batch-Generation**: Alle Räume werden beim Start generiert (schnelles Gameplay)
- **Roguelike-Mechaniken**: 4d6 drop lowest Attributwürfel, Turn-based Kampf
- **Level-System**: XP sammeln, aufsteigen, stärker werden
- **Equipment-System**: Waffen, Rüstungen, Ringe, Helme
- **Terminal-UI**: Klassisches CLI-Feeling mit blessed

## Projektstruktur

```
dungeon_crawler/
├── main.py              # Game Loop
├── constants.py         # Konstanten (Themes, Monster, Skills)
├── models/             # Datenmodelle
│   ├── player.py
│   ├── dungeon.py
│   ├── items.py
│   └── game_state.py
├── services/           # Services
│   └── ai_service.py   # Gemini AI Integration
├── game/               # Gameplay-Logik
│   ├── character_creation.py
│   ├── exploration.py
│   └── combat.py
└── ui/                 # Terminal UI (TODO)
```

## Geplante Features (TODO)

- [ ] Bring your own AI / local AIs
- [ ] Skills & Abilities (Wuchtschlag, Schildwall, etc.)
- [X] Save/Load System
- [X] Verbesserte Terminal-UI (Farben, Panels)
- [X] Mehr Monster & Items

## Technologie

- **Python 3.10+**
- **blessed** - Terminal UI
- **google-generativeai** - KI-Integration
- **python-dotenv** - Environment Variables
