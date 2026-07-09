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

- Procedurally generated hex maps — a rugged peninsula of grassland, plains,
  hills, mountain spines, forests and coastline, different every game
- Fog of war with explored/visible states
- Cities: population growth, worked tiles, culture-driven border expansion,
  production queues, gold purchasing, 14 buildings and 4 world wonders
  (Hagia Sophia, Studenica, Rila, Kalemegdan)
- 24-technology research tree across four eras (Ancient → Renaissance)
- Civ V-style combat: hit points, ranged vs melee, terrain defense bonuses,
  fortification, sieges, city bombardment and capture
- Unit promotions: combat earns XP; veterans gain up to three ⭐ levels,
  each worth +10% strength (and a morale heal on promotion)
- Workers and tile improvements: farms, mines, and roads (roads cut movement
  cost to 1 on any terrain)
- Strategic resources (horses, iron) gating unit types
- 3–8 AI opponents that scout, settle, improve their land, build, research,
  declare war, sue for peace, and march armies on your cities
- Diplomacy screen: declare war, propose peace, compare scores
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
| `D` | Diplomacy |
| `Esc` | Close panels |

## Code layout

Plain HTML/CSS/JavaScript — no frameworks, no build step.

```
index.html        page shell
css/style.css     all styling
js/data.js        civs, units, buildings, techs, terrain tables
js/hex.js         hex-grid math (odd-r offset, cube distance, pixel transforms)
js/mapgen.js      seeded value-noise map generation + start placement
js/model.js       game engine: cities, units, combat, research, turns, save/load
js/ai.js          AI: settling, production, research, diplomacy, tactics
js/render.js      canvas renderer + minimap
js/ui.js          panels, modals, input handling
```

## Ideas for future expansion

Naval units and embarkation (with island maps), happiness, religion,
city-states, more wonders, sound.
