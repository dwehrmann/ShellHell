# NPCs for ShellHell

## NPC System Design

### Core Philosophy

**NPCs as Dynamic Characters:**
- Not quest vending machines
- Remember conversations (stored in world_memory.json)
- React to player's morality/reputation
- Can become allies, enemies, or traders
- LLM generates dialogue based on context + personality

---

## Implementation Priority

**Phase 1 (MVP):**
- Morality/Reputation System
- Attitude tracking
- Dynamic pricing for merchants
- Basic trading system
- NPC type differentiation (merchant, quest_giver, companion_potential, hostile)
- Quest offering (offers_quest flag)
- will_attack negotiation

**Phase 2 (Polish):**
- Companion recruitment
- Hostile NPCs with full negotiation
- Quest system with objectives
- Complex quest chains

**Phase 3 (Premium):**
- Meta-narrative NPCs
- Recurring characters across runs
- Mimic NPCs

---

## Current Status

### Implemented ✓
- Basic NPC model with memory
- LLM dialogue generation
- Conversation history (3 turns)
- Knowledge system
- Actions: heal, give_item, call_guards, unlock_door, reveal_secret

### To Implement (Phase 1)
- [ ] Morality system in game state
- [ ] Attitude tracking per NPC
- [ ] reaction_to_morality configs
- [ ] Merchant trading with dynamic pricing
- [ ] will_attack flag and negotiation
- [ ] offers_quest flag
- [ ] reveals_information flag

### To Implement (Phase 2+)
- [ ] Companion system
- [ ] Quest objectives tracking
- [ ] Bribe mechanics
- [ ] Recurring NPCs across runs
