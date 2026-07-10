# ⚔ Balkan Civilizations

A local, turn-based 4X strategy game in the spirit of Civilization V, set
entirely in the Balkans — single-player against the AI, **hotseat** on one
device, or **online with friends** over a direct browser-to-browser
connection (no game server, no accounts). Runs 100% in your browser: no
install needed.

![Balkan Civilizations mid-game](screenshot.png)

## How to play

Just open `index.html` in any modern browser (Chrome, Firefox, Edge, Safari):

- **Double-click `index.html`**, or
- serve the folder locally: `python3 -m http.server 8000` then visit
  <http://localhost:8000>.

Your game **auto-saves every turn** (browser localStorage) — use *Continue Saved
Game* on the title screen to pick up where you left off.

## The nine civilizations

| Civilization | Leader | Trait | Unique unit |
|---|---|---|---|
| **Macedonia** | Tsar Samuil | +2 culture, +1 science in every city | **Samuil's Guard** — +25% on defense |
| **Serbia** | Stefan Dušan | +25% production toward buildings | **Gusar** — 5-move light cavalry |
| **Bulgaria** | Simeon I the Great | +2 science in every city | **Konnik** — heavy horseman |
| **Byzantium** | Basil II | +4 gold in capital, +1 elsewhere | **Cataphract** — armoured cavalry |
| **Ottomans** | Mehmed II | +20% strength attacking cities | **Janissary** — heals 50 HP on kill |
| **Albania** | Skanderbeg | +30% strength in hills & forest | **Stradiot** — mountain cavalry |
| **Croatia** | Tomislav | +2 gold, +1 food in coastal cities | **Uskok** — fast raider |
| **Wallachia** | Vlad III Drăculea | +25% strength in own territory | **Călărași** — heals 30 HP on kill |
| **Bosnia** | Tvrtko I | +50% culture (faster borders) | **Krstjani Guard** — elite pikeman |

## Features

- Procedurally generated hex maps with smooth coastlines, different every
  game — choose a rugged **Peninsula**, an island-dotted **Archipelago**,
  or a **custom map** you painted yourself in the built-in **Map Editor**
  (terrain, forests, and resources, saved locally)
- **Hotseat multiplayer**: 2–3 humans share the device — each gets their
  own fog of war, notifications, and a pass-the-device screen between turns
- **Online multiplayer** (up to 4 humans, each with their own civilization):
  serverless WebRTC. The host clicks *Host Online*, sends each friend an
  invite code over any chat app, pastes back their replies, and starts —
  after that the connection is direct between browsers. Each player picks
  their civ on their own start screen, sees only their own fog of war, and
  plays in turn while the others watch a waiting banner
- **Campaign scenarios — one for every civilization**, each with its own
  victory rule and a live objective tracker in the top bar:
  - *The Rise of Samuil* (Macedonia, 976) — take Constantinople in 150 turns
  - *The Golden Age of Simeon* (Bulgaria, 893) — first to master every
    technology, with Byzantium at your door
  - *The Bulgar-Slayer* (Byzantium, 1014) — take Samuil's Ohrid in 100 turns
  - *The Kingdom Crowned* (Croatia, 925) — survive Tsar Simeon's invasion
  - *Dušan's Dream* (Serbia, 1346) — hold three imperial capitals
  - *The Night Attack* (Wallachia, 1462) — destroy 12 Ottoman units as
    Vlad Drăculea, on hard difficulty
  - *Tvrtko's Crown* (Bosnia, 1377) — control six cities, by charter or sword
  - *The Fall of Constantinople* (Ottomans, 1453) — breach the Theodosian
    Walls in 60 turns
  - *Skanderbeg's Rebellion* (Albania, 1443) — hold Krujë for 100 turns,
    on hard difficulty
- Naval warfare: research Sailing to embark land units onto the coast and
  build Galleys; Compass opens the deep sea and the ranged War Galleass.
  Ships hunt transports, bombard shores, and can capture coastal cities;
  embarked units are nearly defenseless — escort them
- Fog of war with explored/visible states
- Cities: population growth, worked tiles, culture-driven border expansion,
  production queues, gold purchasing, 16 buildings and 10 world wonders
  (Hagia Sophia, Mount Athos, the Hippodrome, Diocletian's Palace,
  Stari Most, Bran Castle, and more — each buildable once per world)
- 26-technology research tree across four eras (Ancient → Renaissance)
- Civ V-style combat: hit points, ranged vs melee, terrain defense bonuses,
  fortification, floating damage numbers, and sieges — cities bombard one
  besieger every turn, so bring catapults. Hover a target for a **combat
  forecast** (damage dealt and taken) before you commit
- **Barbarians** (optional toggle): camps seed the wilds and spawn raiders
  that scale with the era; burn a camp for a 40-gold bounty. **Ancient
  ruins** reward explorers with gold, faith, science, veteran experience,
  or maps of the surrounding land
- **Unit upgrades**: pay gold in home territory to modernize veterans along
  their line (Warrior → Swordsman → Longswordsman → Musketman, and so on),
  keeping their promotions — unique units included
- Unit promotions: combat earns XP; veterans gain up to three ⭐ levels,
  each worth +10% strength (and a morale heal on promotion)
- **Religion**: Shrines, Temples and monasteries generate faith. Found one
  of six historical faiths — Orthodoxy, Catholicism, Islam, Bogomilism,
  Tengrism, Hellenism — pick a founder belief (food, science, gold tithe,
  or holy-warrior combat bonus), and spread it: religion flows between
  nearby cities and Missionaries (bought with faith) convert them directly
- **City-states**: independent minors like Ragusa, Kotor and Rhodes.
  Win them over with gold gifts — friends and allies pay gold, food or
  culture, and militaristic allies gift you units — or conquer them, if
  you can breach their walls
- **Happiness & Golden Ages**: your empire's mood (top bar) rises with
  luxuries (wine, silver, olives, salt) and Taverns/Hammams, and falls as
  cities and population grow. Unhappy empires grow at half speed; below −10
  growth stops and units fight at −15%. Surplus happiness fills a meter
  that triggers **Golden Ages**: 10 turns of +20% gold and production
- **Espionage**: spies unlock with Civil Service, Education and Gunpowder.
  Station them in rival cities to steal technology (and risk execution),
  in your own cities as counter-intelligence, or in city-states to rig
  elections for influence
- **Sound & music**: procedurally synthesized effects (WebAudio, no audio
  files) for combat, research, golden ages, spies and more, plus an ambient
  score — a low drone under a wandering melody in the double-harmonic
  "Balkan" scale. Toggle effects (🔊) and music (🎵) separately
- Workers and tile improvements: farms, mines, and roads (roads cut movement
  cost to 1 on any terrain)
- Strategic resources (horses, iron) gating unit types; luxury resources
  feeding happiness
- 3–8 AI opponents that scout, settle (across the sea, too), improve their
  land, build navies, research, declare war, sue for peace, and march
  armies on your cities
- Cities support a **production queue** (queue up to 6 items) and a full
  clickable **message log**; wounded units can fortify until healed
- Diplomacy screen: declare war, propose peace, compare scores
- Three difficulty levels (Prince / King / Emperor) scaling AI output
- Hover any hex for a movement path preview with turn count; scouts can
  **auto-explore**; units glide between hexes instead of teleporting
- Victory by **Domination** (control every capital) or **Score** at turn 300
- Autosave + continue

## Controls

| Input | Action |
|---|---|
| Left-click | Select unit / city; click highlighted hex to move or attack |
| Right-click | Move selected unit |
| Drag | Pan the map |
| Mouse wheel | Zoom |
| `Enter` | End turn |
| `N` / `.` | Next idle unit |
| `F` | Fortify selected unit |
| `T` | Technology tree |
| `R` | Religion overview |
| `E` | Espionage |
| `D` | Diplomacy |
| `Esc` | Close panels |

## Code layout

Plain HTML/CSS/JavaScript — no frameworks, no build step.

```
index.html        page shell
css/style.css     all styling
js/data.js        civs, units, buildings, techs, terrain tables
js/sound.js       procedural WebAudio sound effects
js/hex.js         hex-grid math (odd-r offset, cube distance, pixel transforms)
js/mapgen.js      seeded value-noise map generation + start placement
js/model.js       game engine: cities, units, combat, research, turns, save/load
js/ai.js          AI: settling, production, research, diplomacy, tactics
js/render.js      canvas renderer + minimap (terrain shading, animations)
js/editor.js      map editor
js/net.js         serverless WebRTC multiplayer (invite codes, state relay)
js/ui.js          panels, modals, input handling
```

## Notes on online play

The invite/reply codes are standard WebRTC session descriptions — exchange
them over any messenger. A STUN server (Google's public one) is used for
NAT traversal; on very restrictive networks a direct connection may fail.
The full game state is auto-saved locally on every turn, so if a connection
drops mid-game the host can continue against the AI or re-host later.

## Ideas for future expansion

Unit artwork, save-transfer for resuming online games, scenario chains.
