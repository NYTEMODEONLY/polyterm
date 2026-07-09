# ⚔ Balkan Civilizations

A local, single-player, turn-based 4X strategy game in the spirit of Civilization V,
set entirely in the Balkans. Runs 100% in your browser — no install, no server, no
internet connection needed.

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

- Procedurally generated hex maps, different every game — choose a rugged
  **Peninsula** or an island-dotted **Archipelago**
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
  besieger every turn, so bring catapults
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
- **Sound**: procedurally synthesized effects (WebAudio, no files) for
  combat, research, golden ages, spies and more — mute with the 🔊 button
- Workers and tile improvements: farms, mines, and roads (roads cut movement
  cost to 1 on any terrain)
- Strategic resources (horses, iron) gating unit types; luxury resources
  feeding happiness
- 3–8 AI opponents that scout, settle (across the sea, too), improve their
  land, build navies, research, declare war, sue for peace, and march
  armies on your cities
- Diplomacy screen: declare war, propose peace, compare scores
- Three difficulty levels (Prince / King / Emperor) scaling AI output
- Hover any hex for a movement path preview with turn count; scouts can
  **auto-explore**
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
js/render.js      canvas renderer + minimap
js/ui.js          panels, modals, input handling
```

## Ideas for future expansion

Hotseat multiplayer, a map editor, unit animations, music.
