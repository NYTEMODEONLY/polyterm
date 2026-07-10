// ============================================================
// Core game model: Game, Player, City, Unit, combat, turns
// ============================================================
"use strict";

let NEXT_ID = 1;
const uid = () => NEXT_ID++;

// ------------------------------------------------------------
// Unit
// ------------------------------------------------------------
class Unit {
  constructor(type, owner, c, r) {
    this.id = uid();
    this.type = type;            // key into UNITS
    this.owner = owner;          // player index
    this.c = c; this.r = r;
    this.hp = 100;
    this.moves = UNITS[type].moves;
    this.fortified = false;
    this.attacked = false;
    this.path = null;            // queued multi-turn path [[c,r],...]
    this.xp = 0;
    this.level = 0;              // each level: +10% combat strength
    this.building = null;        // worker job: {type, turnsLeft}
    this.charges = UNITS[type].charges || 0; // missionary spreads
  }
  get def() { return UNITS[this.type]; }
  get isCivilian() { return !!this.def.civilian; }
  get isRanged() { return !!this.def.rs; }
  resetTurn() { this.moves = this.building ? 0 : this.def.moves; this.attacked = false; }

  gainXp(amount) {
    if (this.isCivilian) return;
    this.xp += amount;
    const thresholds = [15, 45, 90];
    while (this.level < 3 && this.xp >= thresholds[this.level]) {
      this.level++;
      this.hp = Math.min(100, this.hp + 20); // veterans rally on promotion
    }
  }
}

// ------------------------------------------------------------
// City
// ------------------------------------------------------------
class City {
  constructor(name, owner, c, r) {
    this.id = uid();
    this.name = name;
    this.owner = owner;
    this.c = c; this.r = r;
    this.pop = 1;
    this.food = 0;
    this.prodStored = 0;
    this.producing = null;       // {kind:'unit'|'building', key}
    this.buildings = [];
    this.hp = 200;
    this.cultureStored = 0;
    this.expansions = 0;
    this.isCapital = false;
    this.coastal = false;
    this.religion = null;        // majority religion id
    this.pressure = {};          // religionId -> accumulated pressure
  }

  get maxHp() {
    let hp = 200;
    for (const b of this.buildings) hp += BUILDINGS[b].cityHp || 0;
    return hp;
  }

  foodNeeded() { return Math.floor(15 + 6 * (this.pop - 1) + Math.pow(this.pop - 1, 1.8)); }
  borderCost() { return Math.floor(20 + 12 * Math.pow(this.expansions, 1.35)); }
}

// ------------------------------------------------------------
// Player
// ------------------------------------------------------------
class Player {
  constructor(index, civId, isHuman) {
    this.index = index;
    this.civId = civId;
    this.isHuman = isHuman;
    this.alive = true;
    this.gold = 40;
    this.scienceStored = 0;
    this.researching = null;
    this.techs = new Set(["AGRICULTURE"]);
    this.atWarWith = new Set();  // player indexes
    this.met = new Set();
    this.warWeariness = {};      // playerIndex -> turns at war
    this.cityNameCursor = 0;
    this.visible = null;         // Uint8Array: 0 unseen 1 explored 2 visible
    this.originalCapitalId = null;
    this.faith = 0;
    this.religionId = null;      // id of the religion this player founded
    this.influence = {};         // minor player index -> influence points
    this.gaMeter = 0;            // golden age progress
    this.goldenAgeTurns = 0;     // turns of golden age remaining
    this.gaCount = 0;            // golden ages enjoyed so far
    this.spies = [];             // {id, name, cityId, progress, deadUntil}
  }
  get civ() { return CIVS[this.civId]; }
  get isMinor() { return !!this.civ.minor; }
  hasTech(t) { return this.techs.has(t); }

  era() {
    let e = 0;
    for (const t of this.techs) e = Math.max(e, TECHS[t].era);
    return e;
  }

  availableTechs() {
    return Object.keys(TECHS).filter(k =>
      !this.techs.has(k) && TECHS[k].req.every(r => this.techs.has(r)));
  }

  nextCityName() {
    const names = this.civ.cities;
    const n = names[this.cityNameCursor % names.length];
    const suffix = Math.floor(this.cityNameCursor / names.length);
    this.cityNameCursor++;
    return suffix ? `${n} ${["II","III","IV","V","VI"][suffix-1] || suffix+1}` : n;
  }
}

// ------------------------------------------------------------
// Game
// ------------------------------------------------------------
class Game {
  constructor(opts) {
    // opts: {playerCiv, numOpponents, seed, mapW, mapH}
    this.turn = 1;
    this.maxTurns = GAME_DEFAULTS.maxTurns;
    this.seed = opts.seed ?? Math.floor(Math.random() * 1e9);
    this.rng = mulberry32(this.seed);
    this.mapType = opts.mapType || "peninsula";
    this.humans = Math.max(1, opts.numHumans || 1);
    this.activeHuman = 0;
    this._viewer = null;         // network client override (not saved)
    this.scenario = opts.scenario || null;
    this.anims = [];             // transient movement animations (not saved)
    if (this.mapType === "custom" && opts.customMap) {
      const cm = opts.customMap;
      this.map = { w: cm.w, h: cm.h, idx: (c, r) => r * cm.w + c, seed: this.seed,
        tiles: cm.tiles.map((t, i) => ({ c: i % cm.w, r: Math.floor(i / cm.w),
          terrain: t.terrain, feature: t.feature || null, resource: t.resource || null,
          improvement: null, owner: -1, city: null, workedBy: null })) };
    } else {
      this.map = generateMap(opts.mapW || GAME_DEFAULTS.mapW, opts.mapH || GAME_DEFAULTS.mapH, this.seed, this.mapType);
    }
    this.units = [];
    this.cities = [];
    this.players = [];
    this.notifications = [];
    this.effects = [];           // transient combat popups (not saved)
    this.difficulty = opts.difficulty || "normal";
    this.over = false;
    this.winner = null;
    this.victoryType = null;

    // players: humans first, then AI civs (scenarios pin the lineup)
    let civPool = CIV_IDS.filter(id => id !== opts.playerCiv);
    if (opts.fixedOpponents) {
      civPool = [...opts.fixedOpponents];
    } else {
      for (let i = civPool.length - 1; i > 0; i--) {
        const j = Math.floor(this.rng() * (i + 1));
        [civPool[i], civPool[j]] = [civPool[j], civPool[i]];
      }
    }
    this.religions = [];

    const civs = [opts.playerCiv, ...civPool.slice(0, opts.numOpponents)];
    civs.forEach((cid, i) => {
      const p = new Player(i, cid, i < this.humans);
      p.visible = new Uint8Array(this.map.w * this.map.h);
      this.players.push(p);
    });
    const nMajors = this.players.length;

    // city-states, scaled to map area
    const minorPool = Object.keys(MINORS);
    for (let i = minorPool.length - 1; i > 0; i--) {
      const j = Math.floor(this.rng() * (i + 1));
      [minorPool[i], minorPool[j]] = [minorPool[j], minorPool[i]];
    }
    const nMinors = opts.noMinors ? 0 :
      Math.min(minorPool.length, Math.max(2, Math.round((this.map.w * this.map.h) / 400)));
    for (let m = 0; m < nMinors; m++) {
      const p = new Player(nMajors + m, minorPool[m], false);
      p.visible = new Uint8Array(this.map.w * this.map.h);
      this.players.push(p);
    }

    const starts = pickStartPositions(this.map, this.players.length, this.rng);
    this.players.forEach((p, i) => {
      const s = starts[i];
      if (!s) { p.alive = false; return; }
      if (p.isMinor) {
        // city-states begin as a fortified standing city
        const city = new City(p.civ.cities[0], i, s.c, s.r);
        city.isCapital = true;
        city.pop = 2;
        city.buildings.push("WALLS");
        city.hp = city.maxHp;
        p.originalCapitalId = city.id;
        const t = this.tile(s.c, s.r);
        t.city = city; t.owner = i;
        for (const [nc, nr] of HEX.neighbors(s.c, s.r)) {
          const nt = this.tile(nc, nr);
          if (nt) {
            if (nt.owner === -1) nt.owner = i;
            if (this.isWater(nt)) city.coastal = true;
          }
        }
        this.cities.push(city);
        this.addUnit("WARRIOR", i, s.c, s.r);
      } else {
        this.addUnit("SETTLER", i, s.c, s.r);
        const wPos = this.freeAdjacent(s.c, s.r) || [s.c, s.r];
        this.addUnit("WARRIOR", i, wPos[0], wPos[1]);
      }
      this.updateVisibility(p);
    });

    if (this.scenario) this.applyScenario();
  }

  // Scenario setup: shared tech era, gold, starting armies, opening wars
  applyScenario() {
    const sc = SCENARIOS[this.scenario];
    if (!sc) { this.scenario = null; return; }
    this.maxTurns = sc.victory.turns;
    const byCiv = (id) => this.players.find(p => p.civId === id);
    for (const p of this.players) {
      if (p.isMinor || !p.alive) continue;
      for (const [key, t] of Object.entries(TECHS)) {
        if (t.era <= (sc.techEra ?? 0)) p.techs.add(key);
      }
      if (p.civId === sc.playerCiv) for (const t of sc.extraTechs || []) p.techs.add(t);
      p.gold += sc.gold || 0;
    }
    for (const [civId, units] of Object.entries(sc.armies || {})) {
      const p = byCiv(civId);
      if (!p || !p.alive) continue;
      const home = this.units.find(u => u.owner === p.index);
      if (!home) continue;
      for (const type of units) {
        for (const [c, r] of HEX.ring(home.c, home.r, 2)) {
          const t = this.tile(c, r);
          if (!t || !TERRAIN[t.terrain].passable) continue;
          if (!UNITS[type].civilian && this.combatUnitAt(c, r)) continue;
          if (UNITS[type].civilian && this.civilianAt(c, r)) continue;
          this.addUnit(type, p.index, c, r);
          break;
        }
      }
      this.updateVisibility(p);
    }
    for (const [a, b] of sc.warsAtStart || []) {
      const pa = byCiv(a), pb = byCiv(b);
      if (pa && pb) { this.meet(pa.index, pb.index); this.declareWar(pa.index, pb.index); }
    }
  }

  get viewer() { return this._viewer ?? this.activeHuman; }

  // ---------- lookups ----------
  tile(c, r) {
    if (c < 0 || r < 0 || c >= this.map.w || r >= this.map.h) return null;
    return this.map.tiles[this.map.idx(c, r)];
  }
  unitsAt(c, r) { return this.units.filter(u => u.c === c && u.r === r); }
  combatUnitAt(c, r) { return this.units.find(u => u.c === c && u.r === r && !u.isCivilian); }
  civilianAt(c, r) { return this.units.find(u => u.c === c && u.r === r && u.isCivilian); }
  cityAt(c, r) { const t = this.tile(c, r); return t ? t.city : null; }
  player(i) { return this.players[i]; }

  freeAdjacent(c, r, naval = false) {
    for (const [nc, nr] of HEX.neighbors(c, r)) {
      const t = this.tile(nc, nr);
      if (!t || this.combatUnitAt(nc, nr)) continue;
      if (naval ? this.isWater(t) : TERRAIN[t.terrain].passable) return [nc, nr];
    }
    return null;
  }

  // ---------- water / embarkation ----------
  isWater(t) { return t.terrain === "OCEAN" || t.terrain === "COAST"; }

  isEmbarked(unit) {
    const t = this.tile(unit.c, unit.r);
    return !unit.def.naval && t && this.isWater(t);
  }

  // Can this unit's type ever stand on tile t (given its owner's techs)?
  unitPassable(unit, t) {
    if (!t) return false;
    if (unit.def.naval) {
      if (!this.isWater(t)) return false;
      return !unit.def.coastOnly || t.terrain === "COAST";
    }
    if (!this.isWater(t)) return TERRAIN[t.terrain].passable;
    const p = this.players[unit.owner];
    if (t.terrain === "COAST") return p.hasTech("SAILING");
    return p.hasTech("COMPASS");
  }

  notify(msg, playerIdx = -1) {
    this.notifications.push({ turn: this.turn, msg, p: playerIdx });
    if (this.notifications.length > 200) this.notifications.shift();
  }

  addEffect(c, r, text, color = "#ff5544") {
    this.effects.push({ c, r, text, color, ts: Date.now() });
    if (this.effects.length > 40) this.effects.shift();
  }

  // ---------- units ----------
  addUnit(type, owner, c, r) {
    const u = new Unit(type, owner, c, r);
    this.units.push(u);
    return u;
  }

  removeUnit(u) {
    const i = this.units.indexOf(u);
    if (i >= 0) this.units.splice(i, 1);
  }

  moveCost(unit, c, r) {
    const t = this.tile(c, r);
    if (!this.unitPassable(unit, t)) return Infinity;
    if (this.isWater(t)) return 1;
    if (unit.def.naval) return Infinity;
    if (t.improvement === "ROAD" || t.city) return 1;
    let cost = TERRAIN[t.terrain].moveCost;
    if (t.feature) cost = Math.max(cost, FEATURE[t.feature].moveCost);
    return cost;
  }

  // ---------- workers ----------
  canBuildImprovement(unit, type) {
    if (!unit.def.worker) return false;
    const imp = IMPROVEMENT[type];
    const t = this.tile(unit.c, unit.r);
    const p = this.players[unit.owner];
    if (!imp || !t || !p.hasTech(imp.tech)) return false;
    if (t.owner !== unit.owner || t.city) return false;
    if (!imp.terrains.includes(t.terrain)) return false;
    if (t.feature && !imp.road) return false;      // farms/mines need clear ground
    if (imp.road ? t.improvement === "ROAD" : t.improvement === type) return false;
    return true;
  }

  startImprovement(unit, type) {
    if (!this.canBuildImprovement(unit, type)) return false;
    unit.building = { type, turnsLeft: IMPROVEMENT[type].turns };
    unit.path = null;
    unit.moves = 0;
    return true;
  }

  progressWorkers(p) {
    for (const u of this.units) {
      if (u.owner !== p.index || !u.building) continue;
      const t = this.tile(u.c, u.r);
      if (!t || t.owner !== p.index) { u.building = null; continue; } // lost the tile
      u.building.turnsLeft--;
      if (u.building.turnsLeft <= 0) {
        t.improvement = u.building.type;
        this.notify(`${IMPROVEMENT[u.building.type].name} completed.`, p.index);
        u.building = null;
      }
    }
  }

  // Can `unit` end its move / pass through (c,r)?
  canEnter(unit, c, r) {
    const t = this.tile(c, r);
    if (!this.unitPassable(unit, t)) return false;
    const cu = this.combatUnitAt(c, r);
    if (cu && !(unit.isCivilian && cu.owner === unit.owner)) {
      if (cu.owner !== unit.owner) return false; // must attack instead
      if (!unit.isCivilian) return false;        // 1 combat unit per tile
    }
    const civ = this.civilianAt(c, r);
    if (civ && unit.isCivilian) return false;
    if (t.city && t.city.owner !== unit.owner) return false; // must capture instead
    return true;
  }

  // A* pathfinding. Returns [[c,r],...] excluding start, or null.
  findPath(unit, tc, tr) {
    const { w, h } = this.map;
    const key = (c, r) => r * w + c;
    const start = key(unit.c, unit.r), goal = key(tc, tr);
    if (start === goal) return [];
    const open = [[0, start]];
    const came = new Map(), gScore = new Map([[start, 0]]);
    while (open.length) {
      let bi = 0;
      for (let i = 1; i < open.length; i++) if (open[i][0] < open[bi][0]) bi = i;
      const [, cur] = open.splice(bi, 1)[0];
      if (cur === goal) {
        const path = [];
        let n = goal;
        while (n !== start) { path.unshift([n % w, Math.floor(n / w)]); n = came.get(n); }
        return path;
      }
      const cc = cur % w, cr = Math.floor(cur / w);
      for (const [nc, nr] of HEX.neighbors(cc, cr)) {
        const t = this.tile(nc, nr);
        if (!this.unitPassable(unit, t)) continue;
        const nk = key(nc, nr);
        // block tiles occupied by other units except at the goal
        if (nk !== goal && this.combatUnitAt(nc, nr) && !unit.isCivilian) continue;
        if (nk !== goal && t.city && t.city.owner !== unit.owner) continue;
        const g = gScore.get(cur) + this.moveCost(unit, nc, nr);
        if (g < (gScore.get(nk) ?? Infinity)) {
          gScore.set(nk, g);
          came.set(nk, cur);
          open.push([g + HEX.distance(nc, nr, tc, tr), nk]);
        }
      }
      if (gScore.size > 4000) return null; // safety valve
    }
    return null;
  }

  addMoveAnim(unit, hops) {
    if (hops.length < 2) return;
    this.anims = this.anims.filter(a => a.id !== unit.id);
    this.anims.push({ id: unit.id, hops, ts: Date.now() });
    if (this.anims.length > 24) this.anims.shift();
  }

  // Execute as much of unit.path as movement allows this turn
  stepAlongPath(unit) {
    const hops = [[unit.c, unit.r]];
    while (unit.path && unit.path.length && unit.moves > 0) {
      const [nc, nr] = unit.path[0];
      if (!this.canEnter(unit, nc, nr)) { unit.path = null; return; }
      const cost = this.moveCost(unit, nc, nr);
      unit.path.shift();
      unit.c = nc; unit.r = nr;
      hops.push([nc, nr]);
      unit.moves = Math.max(0, unit.moves - cost);
      unit.fortified = false;
      unit.building = null; // moving abandons any construction job
      this.updateVisibility(this.players[unit.owner]);
      // capture undefended enemy civilians
      const civ = this.civilianAt(nc, nr);
      if (civ && civ.owner !== unit.owner && !unit.isCivilian) {
        this.removeUnit(civ);
        this.notify(`${CIVS[this.players[unit.owner].civId].adj} forces captured a ${civ.def.name}!`, -1);
      }
    }
    if (unit.path && !unit.path.length) unit.path = null;
    this.addMoveAnim(unit, hops);
  }

  // Tiles reachable this turn (Dijkstra within unit.moves)
  reachableTiles(unit) {
    const { w } = this.map;
    const key = (c, r) => r * w + c;
    const dist = new Map([[key(unit.c, unit.r), 0]]);
    const frontier = [[unit.c, unit.r]];
    const out = [];
    while (frontier.length) {
      const [c, r] = frontier.shift();
      const d = dist.get(key(c, r));
      for (const [nc, nr] of HEX.neighbors(c, r)) {
        const cost = this.moveCost(unit, nc, nr);
        if (!isFinite(cost)) continue;
        const nd = d + cost;
        if (nd > unit.moves) continue;
        const nk = key(nc, nr);
        if (nd < (dist.get(nk) ?? Infinity)) {
          dist.set(nk, nd);
          if (this.canEnter(unit, nc, nr)) out.push([nc, nr]);
          frontier.push([nc, nr]);
        }
      }
    }
    return out;
  }

  // ---------- combat ----------
  strengthOf(unit, { attacking, targetTile, ranged } = {}) {
    const p = this.players[unit.owner];
    let str = ranged ? (unit.def.rs || 0) : unit.def.cs;
    if (this.isEmbarked(unit)) str = 2; // helpless at sea
    let mod = 1;
    const here = this.tile(unit.c, unit.r);
    // wounded units fight at 50–100%
    mod *= 0.5 + 0.5 * (unit.hp / 100);
    mod += unit.level * 0.1; // veteran promotions
    if (!attacking) {
      if (here) {
        mod += TERRAIN[here.terrain].defense || 0;
        if (here.feature) mod += FEATURE[here.feature].defense || 0;
      }
      if (unit.fortified) mod += 0.25;
      if (unit.def.defendBonus) mod += unit.def.defendBonus;
    }
    // civ traits
    const civ = p.civ;
    if (civ.roughBonus && here && (here.terrain === "HILLS" || here.feature === "FOREST")) mod += civ.roughBonus;
    if (civ.homeBonus && here && here.owner === unit.owner) mod += civ.homeBonus;
    if (civ.vsCityBonus && attacking && targetTile && targetTile.city) mod += civ.vsCityBonus;
    if (unit.def.terrainBonus && here && (here.terrain === "HILLS" || here.feature === "FOREST")) mod += unit.def.terrainBonus;
    if (unit.def.siege && attacking && targetTile && targetTile.city) mod += 1.0; // siege vs cities
    // Holy Warriors: faith-fuelled fighting near follower cities
    if (!p.isMinor && p.religionId !== null && this.religions[p.religionId].belief === "ZEAL") {
      const rid = p.religionId;
      if (this.cities.some(c => c.religion === rid && HEX.distance(c.c, c.r, unit.c, unit.r) <= 2)) {
        mod += 0.15;
      }
    }
    // a miserable empire fights poorly
    if (!p.isMinor && this.happinessOf(p.index) < HAPPINESS.strikeAt) mod -= 0.15;
    return str * mod;
  }

  cityStrength(city) {
    let str = 8 + city.pop * 1.2;
    for (const b of city.buildings) str += BUILDINGS[b].cityStr || 0;
    const garrison = this.combatUnitAt(city.c, city.r);
    if (garrison) str += this.strengthOf(garrison, {}) * 0.25;
    const era = this.players[city.owner].era();
    str += era * 3;
    if (this.players[city.owner].isMinor) str += 6; // city-states dig in
    return str;
  }

  damageRoll(attStr, defStr) {
    const ratio = attStr / Math.max(defStr, 0.5);
    const base = 30 * Math.pow(ratio, 1.25);
    const rand = 0.85 + this.rng() * 0.3;
    return Math.max(1, Math.round(base * rand));
  }

  // unit attacks tile (c,r): enemy unit or city
  attack(unit, c, r) {
    if (unit.attacked || unit.moves <= 0 || unit.isCivilian) return false;
    if (this.isEmbarked(unit)) return false; // no fighting from transports
    const t = this.tile(c, r);
    if (!t) return false;
    const dist = HEX.distance(unit.c, unit.r, c, r);
    const ranged = unit.isRanged;
    const range = ranged ? unit.def.range : 1;
    if (dist > range) return false;
    // land melee can't strike out to sea; naval melee can't strike inland (cities excepted)
    if (!ranged && !unit.def.naval && this.isWater(t)) return false;
    if (!ranged && unit.def.naval && !this.isWater(t) && !t.city) return false;

    const targetCity = t.city && this.players[unit.owner].atWarWith.has(t.city.owner) ? t.city : null;
    const targetUnit = (() => {
      const cu = this.combatUnitAt(c, r);
      if (cu && this.players[unit.owner].atWarWith.has(cu.owner)) return cu;
      return null;
    })();

    if (!targetCity && !targetUnit) {
      // undefended civilian capture handled by movement
      const civ = this.civilianAt(c, r);
      if (civ && this.players[unit.owner].atWarWith.has(civ.owner) && dist === 1 && !ranged) {
        return this.moveUnitTo(unit, c, r);
      }
      return false;
    }

    const attStr = this.strengthOf(unit, { attacking: true, targetTile: t, ranged });
    unit.fortified = false;

    if (targetCity && (!targetUnit || !ranged)) {
      // attack the city itself (garrison protects a city only vs ranged pokes)
      const defStr = this.cityStrength(targetCity);
      const dmg = this.damageRoll(attStr, defStr);
      targetCity.hp -= dmg;
      this.addEffect(c, r, "-" + dmg);
      if (!ranged) {
        const back = this.damageRoll(defStr, attStr);
        unit.hp -= back;
        this.addEffect(unit.c, unit.r, "-" + back, "#ffaa33");
        if (unit.hp <= 0) {
          this.removeUnit(unit);
          if (targetCity.hp <= 0) targetCity.hp = 1; // no one left to capture it
        }
      }
      if (this.units.includes(unit)) unit.gainXp(ranged ? 3 : 5);
      if (targetCity.hp <= 0 && this.units.includes(unit)) {
        if (ranged) targetCity.hp = 1; // ranged can't capture
        else this.captureCity(targetCity, unit);
      }
    } else if (targetUnit) {
      const defStr = this.strengthOf(targetUnit, { attacking: false });
      const dmg = this.damageRoll(attStr, defStr);
      targetUnit.hp -= dmg;
      this.addEffect(c, r, "-" + dmg);
      if (!ranged) {
        const back = this.damageRoll(defStr, attStr);
        unit.hp -= back;
        this.addEffect(unit.c, unit.r, "-" + back, "#ffaa33");
      }
      if (targetUnit.hp > 0) targetUnit.gainXp(4);
      if (unit.hp > 0) unit.gainXp((ranged ? 3 : 5) + (targetUnit.hp <= 0 ? 5 : 0));
      if (targetUnit.hp <= 0) {
        this.removeUnit(targetUnit);
        if (unit.def.healOnKill) unit.hp = Math.min(100, unit.hp + unit.def.healOnKill);
        if (!ranged && unit.hp > 0 && !this.combatUnitAt(c, r) &&
            !(t.city && t.city.owner !== unit.owner) && this.unitPassable(unit, t)) {
          unit.c = c; unit.r = r; // advance into the tile
          this.updateVisibility(this.players[unit.owner]);
        }
      }
      if (unit.hp <= 0) this.removeUnit(unit);
    }

    unit.attacked = true;
    unit.moves = 0;
    return true;
  }

  captureCity(city, unit) {
    const oldOwner = city.owner;
    const newOwner = unit.owner;
    const t = this.tile(city.c, city.r);
    // the garrison falls with the city
    for (const g of this.unitsAt(city.c, city.r)) {
      if (g !== unit && g.owner !== newOwner) this.removeUnit(g);
    }
    city.owner = newOwner;
    city.hp = Math.floor(city.maxHp * 0.4);
    city.pop = Math.max(1, city.pop - 1);
    city.producing = null;
    // reassign tile ownership
    for (const tile of this.map.tiles) if (tile.workedBy === city.id) tile.workedBy = null;
    for (const tile of this.map.tiles) {
      if (tile.owner === oldOwner && HEX.distance(tile.c, tile.r, city.c, city.r) <= 2) {
        // keep only tiles closer to this city than to any other old-owner city
        const closerOther = this.cities.some(o => o.owner === oldOwner && o !== city &&
          HEX.distance(tile.c, tile.r, o.c, o.r) < HEX.distance(tile.c, tile.r, city.c, city.r));
        if (!closerOther) tile.owner = newOwner;
      }
    }
    t.owner = newOwner;
    if (!unit.def.naval) { unit.c = city.c; unit.r = city.r; } // ships stay offshore
    unit.moves = 0;
    this.updateVisibility(this.players[newOwner]);
    this.dirtyHappiness();
    this.notify(`${CIVS[this.players[newOwner].civId].name} captured ${city.name}!`, -1);
    this.checkElimination(oldOwner);
    this.checkVictory();
  }

  checkElimination(playerIdx) {
    const p = this.players[playerIdx];
    if (!p.alive) return;
    const hasCities = this.cities.some(c => c.owner === playerIdx);
    const hasSettlers = this.units.some(u => u.owner === playerIdx && u.type === "SETTLER");
    if (!hasCities && !hasSettlers) {
      p.alive = false;
      this.units = this.units.filter(u => u.owner !== playerIdx);
      this.notify(p.isMinor ? `The city-state of ${p.civ.name} has been destroyed!`
                            : `${p.civ.name} has been destroyed!`, -1);
      this.checkVictory();
    }
  }

  // ---------- movement API ----------
  moveUnitTo(unit, tc, tr) {
    const path = this.findPath(unit, tc, tr);
    if (!path) return false;
    unit.path = path;
    this.stepAlongPath(unit);
    return true;
  }

  // ---------- cities ----------
  foundCity(settler) {
    const t = this.tile(settler.c, settler.r);
    if (!t || t.city || !TERRAIN[t.terrain].passable) return null;
    // not adjacent to another city
    for (const [nc, nr] of HEX.ring(settler.c, settler.r, 2)) {
      const nt = this.tile(nc, nr);
      if (nt && nt.city) return null;
    }
    const p = this.players[settler.owner];
    const city = new City(p.nextCityName(), settler.owner, settler.c, settler.r);
    const isFirst = !this.cities.some(c => c.owner === settler.owner);
    if (isFirst) { city.isCapital = true; p.originalCapitalId = city.id; }
    for (const [nc, nr] of HEX.neighbors(settler.c, settler.r)) {
      const nt = this.tile(nc, nr);
      if (nt && (nt.terrain === "COAST" || nt.terrain === "OCEAN")) city.coastal = true;
    }
    this.cities.push(city);
    t.city = city;
    // claim centre + ring 1
    t.owner = settler.owner;
    for (const [nc, nr] of HEX.neighbors(settler.c, settler.r)) {
      const nt = this.tile(nc, nr);
      if (nt && nt.owner === -1) nt.owner = settler.owner;
    }
    this.removeUnit(settler);
    this.updateVisibility(p);
    this.dirtyHappiness();
    return city;
  }

  cityWorkableTiles(city) {
    const out = [];
    for (const [c, r] of HEX.ring(city.c, city.r, 3)) {
      const t = this.tile(c, r);
      if (t && t.owner === city.owner && !(t.c === city.c && t.r === city.r)) out.push(t);
    }
    return out;
  }

  tileYield(t) {
    const terr = TERRAIN[t.terrain];
    let food = terr.food, prod = terr.prod, gold = terr.gold;
    if (t.feature) { const f = FEATURE[t.feature]; food += f.food; prod += f.prod; gold += f.gold; }
    if (t.resource) { const rs = RESOURCE[t.resource]; food += rs.food; prod += rs.prod; gold += rs.gold; }
    if (t.improvement) {
      const imp = IMPROVEMENT[t.improvement];
      food += imp.food || 0; prod += imp.prod || 0; gold += imp.gold || 0;
    }
    return { food, prod, gold };
  }

  cityYields(city) {
    const p = this.players[city.owner];
    const civ = p.civ;
    // centre tile minimum yield
    const centre = this.tileYield(this.tile(city.c, city.r));
    let food = Math.max(2, centre.food), prod = Math.max(2, centre.prod), gold = Math.max(1, centre.gold);
    // work best tiles up to pop
    const tiles = this.cityWorkableTiles(city)
      .map(t => ({ t, y: this.tileYield(t) }))
      .sort((a, b) => (b.y.food * 1.3 + b.y.prod + b.y.gold * 0.5) - (a.y.food * 1.3 + a.y.prod + a.y.gold * 0.5));
    for (let i = 0; i < Math.min(city.pop, tiles.length); i++) {
      food += tiles[i].y.food; prod += tiles[i].y.prod; gold += tiles[i].y.gold;
    }
    let sci = 2 + city.pop * 0.5;
    let culture = 1;
    let faith = 0;
    for (const b of city.buildings) {
      const bd = BUILDINGS[b];
      food += bd.food || 0; prod += bd.prod || 0; gold += bd.gold || 0;
      sci += bd.sci || 0; culture += bd.culture || 0; faith += bd.faith || 0;
    }
    // founder beliefs reward your own following cities
    if (!p.isMinor && p.religionId !== null && city.religion === p.religionId) {
      const belief = this.religions[p.religionId].belief;
      if (belief === "HEARTH") food += 2;
      if (belief === "SCHOLAR") sci += 2;
    }
    // city-state friendships boost the capital
    if (city.isCapital && !p.isMinor) {
      const mb = this.minorBonuses(city.owner);
      food += mb.food; culture += mb.culture;
    }
    // civ traits
    if (civ.cityScience) sci += civ.cityScience;
    if (civ.cityCulture) culture += civ.cityCulture;
    if (civ.cityGold) gold += civ.cityGold;
    if (civ.capitalGold && city.isCapital) gold += civ.capitalGold;
    if (civ.coastalGold && city.coastal) gold += civ.coastalGold;
    if (civ.coastalFood && city.coastal) food += civ.coastalFood;
    if (civ.cultureBonus) culture *= (1 + civ.cultureBonus);
    if (!p.isHuman && !p.isMinor) {
      const mult = { easy: 0.75, normal: 1, hard: 1.3 }[this.difficulty] || 1;
      prod = Math.floor(prod * mult); gold = Math.floor(gold * mult);
      sci = sci * mult;
    }
    return { food, prod, gold, sci: Math.floor(sci), culture, faith };
  }

  productionOptions(city) {
    const p = this.players[city.owner];
    const opts = [];
    for (const [key, u] of Object.entries(UNITS)) {
      if (u.faithCost) continue; // missionaries are bought with faith
      if (u.uu && u.uu !== p.civId) continue;
      if (u.replaces && p.civId !== u.uu) continue;
      // if civ has a UU replacing this unit, hide the base unit
      const replacedBy = Object.entries(UNITS).find(([, v]) => v.uu === p.civId && v.replaces === key);
      if (replacedBy) continue;
      if (u.tech && !p.hasTech(u.tech)) continue;
      if (u.needs && !this.playerHasResource(p.index, u.needs)) continue;
      if (u.naval && !city.coastal) continue; // shipyards need the sea
      opts.push({ kind: "unit", key, cost: u.cost, name: u.name, icon: u.icon, naval: u.naval });
    }
    for (const [key, b] of Object.entries(BUILDINGS)) {
      if (city.buildings.includes(key)) continue;
      if (b.tech && !p.hasTech(b.tech)) continue;
      if (b.requires && !city.buildings.includes(b.requires)) continue;
      if (b.wonder) {
        if (p.isMinor) continue; // city-states don't race for wonders
        const builtAnywhere = this.cities.some(c => c.buildings.includes(key)) ||
          this.cities.some(c => c !== city && c.producing && c.producing.key === key && c.owner === city.owner);
        if (builtAnywhere) continue;
      }
      opts.push({ kind: "building", key, cost: b.cost, name: b.name, icon: b.icon, wonder: b.wonder });
    }
    return opts;
  }

  playerHasResource(playerIdx, res) {
    return this.map.tiles.some(t => t.owner === playerIdx && t.resource === res);
  }

  buyCost(cost) { return cost * 3; }

  purchase(city, opt) {
    const p = this.players[city.owner];
    const price = this.buyCost(opt.cost);
    if (p.gold < price) return false;
    p.gold -= price;
    this.completeProduction(city, opt);
    return true;
  }

  completeProduction(city, item) {
    if (item.kind === "unit") {
      let spot;
      if (UNITS[item.key].naval) {
        spot = this.freeAdjacent(city.c, city.r, true); // launch onto water
      } else {
        spot = this.combatUnitAt(city.c, city.r) && !UNITS[item.key].civilian
          ? this.freeAdjacent(city.c, city.r) : [city.c, city.r];
      }
      if (!spot) { city.prodStored = UNITS[item.key].cost; return; } // wait for space
      this.addUnit(item.key, city.owner, spot[0], spot[1]);
    } else {
      city.buildings.push(item.key);
      this.dirtyHappiness();
      if (BUILDINGS[item.key].cityHp) city.hp += BUILDINGS[item.key].cityHp;
      if (BUILDINGS[item.key].wonder) {
        this.notify(`${BUILDINGS[item.key].name} has been completed in ${city.name}!`, -1);
      }
    }
  }

  // ---------- visibility ----------
  updateVisibility(p) {
    if (!p || !p.alive) return;
    const vis = p.visible;
    // downgrade visible -> explored
    for (let i = 0; i < vis.length; i++) if (vis[i] === 2) vis[i] = 1;
    const reveal = (c, r, sight) => {
      for (const [nc, nr] of HEX.ring(c, r, sight)) {
        const t = this.tile(nc, nr);
        if (t) vis[this.map.idx(nc, nr)] = 2;
      }
    };
    for (const u of this.units) if (u.owner === p.index) reveal(u.c, u.r, u.def.sight || 2);
    for (const c of this.cities) if (c.owner === p.index) reveal(c.c, c.r, 2);
    // meet players whose units/cities we can now see
    for (const u of this.units) {
      if (u.owner !== p.index && vis[this.map.idx(u.c, u.r)] === 2) this.meet(p.index, u.owner);
    }
    for (const c of this.cities) {
      if (c.owner !== p.index && vis[this.map.idx(c.c, c.r)] === 2) this.meet(p.index, c.owner);
    }
  }

  meet(a, b) {
    const pa = this.players[a], pb = this.players[b];
    if (!pa.met.has(b)) {
      pa.met.add(b); pb.met.add(a);
      for (const [me, other] of [[pa, pb], [pb, pa]]) {
        if (!me.isHuman) continue;
        this.notify(other.isMinor
          ? `You have met the city-state of ${other.civ.name} (${MINOR_TYPES[other.civ.minorType].name}).`
          : `You have met ${other.civ.name} (${other.civ.leader}).`, me.index);
      }
    }
  }

  // ---------- diplomacy ----------
  declareWar(a, b) {
    const pa = this.players[a], pb = this.players[b];
    if (pa.atWarWith.has(b)) return;
    pa.atWarWith.add(b); pb.atWarWith.add(a);
    pa.warWeariness[b] = 0; pb.warWeariness[a] = 0;
    this.notify(`⚔️ ${pa.civ.name} declares war on ${pb.civ.name}!`, -1);
  }

  makePeace(a, b) {
    const pa = this.players[a], pb = this.players[b];
    if (!pa.atWarWith.has(b)) return;
    pa.atWarWith.delete(b); pb.atWarWith.delete(a);
    delete pa.warWeariness[b]; delete pb.warWeariness[a];
    this.notify(`☮️ Peace between ${pa.civ.name} and ${pb.civ.name}.`, -1);
  }

  // ---------- religion ----------
  availableReligionNames() {
    const used = new Set(this.religions.map(r => r.name));
    return RELIGION_NAMES.filter(r => !used.has(r.name));
  }

  canFoundReligion(playerIdx) {
    const p = this.players[playerIdx];
    return !p.isMinor && p.religionId === null && this.religions.length < MAX_RELIGIONS &&
      p.faith >= RELIGION_FOUND_COST(this.religions.length) &&
      this.cities.some(c => c.owner === playerIdx);
  }

  foundReligion(playerIdx, name, icon, beliefKey) {
    if (!this.canFoundReligion(playerIdx)) return false;
    const p = this.players[playerIdx];
    const holy = this.cities.find(c => c.id === p.originalCapitalId && c.owner === playerIdx) ||
                 this.cities.find(c => c.owner === playerIdx);
    p.faith -= RELIGION_FOUND_COST(this.religions.length);
    const id = this.religions.length;
    this.religions.push({ id, name, icon, founder: playerIdx, holyCityId: holy.id, belief: beliefKey });
    p.religionId = id;
    holy.pressure[id] = 250;
    this.updateCityReligion(holy);
    this.notify(`${p.civ.name} founded ${icon} ${name} in ${holy.name}! (${BELIEFS[beliefKey].name})`, -1);
    return true;
  }

  updateCityReligion(city) {
    let best = null, bestP = 0;
    for (const [rid, pr] of Object.entries(city.pressure)) {
      if (pr > bestP) { bestP = pr; best = +rid; }
    }
    if (best !== null && bestP >= 60 && city.religion !== best) {
      city.religion = best;
      const r = this.religions[best];
      this.notify(`${city.name} now follows ${r.icon} ${r.name}.`, city.owner);
    }
  }

  spreadReligionPressure() {
    if (!this.religions.length) return;
    const adds = [];
    for (const src of this.cities) {
      if (src.religion === null) continue;
      const holy = this.religions[src.religion].holyCityId === src.id;
      for (const dst of this.cities) {
        if (dst === src) continue;
        if (HEX.distance(src.c, src.r, dst.c, dst.r) > 7) continue;
        adds.push([dst, src.religion, holy ? 6 : 3]);
      }
    }
    for (const [dst, rid, amt] of adds) dst.pressure[rid] = (dst.pressure[rid] || 0) + amt;
    for (const c of this.cities) this.updateCityReligion(c);
  }

  buyMissionary(city) {
    const p = this.players[city.owner];
    if (p.religionId === null || p.faith < UNITS.MISSIONARY.faithCost) return false;
    const spot = this.civilianAt(city.c, city.r) ? this.freeAdjacent(city.c, city.r) : [city.c, city.r];
    if (!spot) return false;
    p.faith -= UNITS.MISSIONARY.faithCost;
    this.addUnit("MISSIONARY", city.owner, spot[0], spot[1]);
    return true;
  }

  // City (if any) that a missionary standing at (c,r) could preach to
  missionaryTarget(unit) {
    const here = this.cityAt(unit.c, unit.r);
    if (here) return here;
    for (const [nc, nr] of HEX.neighbors(unit.c, unit.r)) {
      const city = this.cityAt(nc, nr);
      if (city) return city;
    }
    return null;
  }

  spreadFromMissionary(unit) {
    const p = this.players[unit.owner];
    if (p.religionId === null || unit.charges <= 0) return false;
    const city = this.missionaryTarget(unit);
    if (!city) return false;
    city.pressure[p.religionId] = (city.pressure[p.religionId] || 0) + MISSIONARY_PRESSURE;
    this.updateCityReligion(city);
    unit.charges--;
    unit.moves = 0;
    if (unit.charges <= 0) this.removeUnit(unit);
    return true;
  }

  religionFollowers(rid) {
    return this.cities.filter(c => c.religion === rid).length;
  }

  // ---------- happiness & golden ages ----------
  happinessOf(idx) {
    const p = this.players[idx];
    if (p.isMinor || !p.alive) return 0;
    if (!this._hap) this._hap = {};
    if (this._hap[idx] !== undefined) return this._hap[idx];
    let hap = HAPPINESS.base;
    const lux = new Set();
    for (const t of this.map.tiles) {
      if (t.owner === idx && t.resource && RESOURCE[t.resource].luxury) lux.add(t.resource);
    }
    hap += lux.size * HAPPINESS.perLuxury;
    let nCities = 0, pop = 0;
    for (const c of this.cities) {
      if (c.owner !== idx) continue;
      nCities++; pop += c.pop;
      for (const b of c.buildings) hap += BUILDINGS[b].happy || 0;
    }
    hap -= nCities * HAPPINESS.perCity + Math.floor(pop * HAPPINESS.perPop);
    hap = Math.floor(hap);
    this._hap[idx] = hap;
    return hap;
  }

  luxuryTypesOf(idx) {
    const lux = new Set();
    for (const t of this.map.tiles) {
      if (t.owner === idx && t.resource && RESOURCE[t.resource].luxury) lux.add(t.resource);
    }
    return [...lux];
  }

  dirtyHappiness() { this._hap = {}; }

  // ---------- espionage ----------
  spySlots(p) {
    return SPY_TECHS.reduce((a, t) => a + (p.hasTech(t) ? 1 : 0), 0);
  }

  assignSpy(playerIdx, spyId, cityId) {
    const p = this.players[playerIdx];
    const spy = p.spies.find(s => s.id === spyId);
    if (!spy || spy.deadUntil > this.turn) return false;
    if (cityId !== null && !this.cities.find(c => c.id === cityId)) return false;
    spy.cityId = cityId;
    spy.progress = 0;
    return true;
  }

  processEspionage() {
    if (!this.stats) this.stats = { steals: 0, catches: 0 };
    for (const p of this.players) {
      if (p.isMinor || !p.alive) continue;
      // recruit up to the entitled number of spies
      while (p.spies.length < this.spySlots(p)) {
        p.spies.push({ id: uid(), name: SPY_NAMES[(p.index * 5 + p.spies.length * 3) % SPY_NAMES.length],
          cityId: null, progress: 0, deadUntil: 0 });
        this.notify(`🕵️ A new spy is ready — assign them in the Espionage panel (E).`, p.index);
      }
      for (const spy of p.spies) {
        if (spy.deadUntil > this.turn || spy.cityId === null) continue;
        const city = this.cities.find(c => c.id === spy.cityId);
        if (!city) { spy.cityId = null; spy.progress = 0; continue; } // city razed/gone
        const owner = this.players[city.owner];
        if (city.owner === p.index) continue; // counter-intelligence is passive
        if (owner.isMinor) {
          // rig elections
          if (!p.atWarWith.has(city.owner)) {
            p.influence[city.owner] = (p.influence[city.owner] || 0) + SPY.rigPerTurn;
          }
          continue;
        }
        // steal technology
        spy.progress += SPY.stealRate;
        if (spy.progress < SPY.stealThreshold) continue;
        spy.progress = 0;
        const defended = owner.spies.some(s => s.cityId === city.id && s.deadUntil <= this.turn);
        if (this.rng() < (defended ? SPY.catchDefended : SPY.catchBase)) {
          spy.cityId = null;
          spy.deadUntil = this.turn + SPY.deadTurns;
          this.stats.catches++;
          this.notify(`🕵️ ${spy.name} was caught in ${city.name} and executed! A replacement trains for ${SPY.deadTurns} turns.`, p.index);
          this.notify(`🕵️ Your agents caught a ${p.civ.adj} spy in ${city.name}!`, city.owner);
        } else {
          const stealable = [...owner.techs].filter(t =>
            !p.techs.has(t) && TECHS[t].req.every(r => p.techs.has(r)));
          if (stealable.length) {
            const t = stealable[Math.floor(this.rng() * stealable.length)];
            p.techs.add(t);
            this.stats.steals++;
            if (p.researching && p.techs.has(p.researching)) p.researching = null;
            this.notify(`🕵️ ${spy.name} stole ${TECHS[t].name} from ${owner.civ.name}!`, p.index);
            this.notify(`🕵️ Technology was stolen from ${city.name}! Station a spy there to catch thieves.`, city.owner);
          } else {
            this.notify(`🕵️ ${spy.name} reports nothing left to steal in ${city.name}.`, p.index);
          }
        }
      }
    }
  }

  // ---------- city-states ----------
  minorStatus(majorIdx, minorIdx) {
    if (this.players[majorIdx].atWarWith.has(minorIdx)) return "war";
    const inf = this.players[majorIdx].influence[minorIdx] || 0;
    if (inf < INFLUENCE_FRIEND) return "neutral";
    if (inf < INFLUENCE_ALLY) return "friend";
    for (const o of this.players) {
      if (o.index === majorIdx || o.isMinor || !o.alive) continue;
      if ((o.influence[minorIdx] || 0) >= inf) return "friend"; // ally must be sole highest
    }
    return "ally";
  }

  minorBonuses(majorIdx) {
    const out = { gold: 0, food: 0, culture: 0 };
    for (const m of this.players) {
      if (!m.isMinor || !m.alive) continue;
      const s = this.minorStatus(majorIdx, m.index);
      if (s === "neutral" || s === "war") continue;
      const ally = s === "ally";
      const type = m.civ.minorType;
      if (type === "mercantile") out.gold += ally ? 4 : 2;
      if (type === "maritime") out.food += ally ? 3 : 1;
      if (type === "cultured") out.culture += ally ? 4 : 2;
    }
    return out;
  }

  giftInfluence(majorIdx, minorIdx, gold) {
    const p = this.players[majorIdx];
    if (p.gold < gold || p.atWarWith.has(minorIdx)) return false;
    p.gold -= gold;
    const gain = gold >= 250 ? 70 : gold >= 100 ? 25 : 10;
    p.influence[minorIdx] = (p.influence[minorIdx] || 0) + gain;
    return true;
  }

  // strongest basic land unit `p` could field (for militaristic gifts)
  bestGiftUnit(p) {
    let best = "WARRIOR", bestStr = 0;
    for (const [key, u] of Object.entries(UNITS)) {
      if (u.civilian || u.naval || u.siege || u.uu || u.faithCost) continue;
      if (u.tech && !p.hasTech(u.tech)) continue;
      const str = Math.max(u.cs, u.rs || 0);
      if (str > bestStr) { bestStr = str; best = key; }
    }
    return best;
  }

  processMinorGifts() {
    if (this.turn % 15 !== 0) return;
    for (const m of this.players) {
      if (!m.isMinor || !m.alive || m.civ.minorType !== "militaristic") continue;
      for (const p of this.players) {
        if (p.isMinor || !p.alive) continue;
        if (this.minorStatus(p.index, m.index) !== "ally") continue;
        const cap = this.cities.find(c => c.id === p.originalCapitalId && c.owner === p.index) ||
                    this.cities.find(c => c.owner === p.index);
        if (!cap) continue;
        const spot = this.freeAdjacent(cap.c, cap.r);
        if (!spot) continue;
        const type = this.bestGiftUnit(p);
        this.addUnit(type, p.index, spot[0], spot[1]);
        this.notify(`${m.civ.name} gifts you a ${UNITS[type].name}!`, p.index);
      }
    }
  }

  decayInfluence() {
    for (const p of this.players) {
      if (p.isMinor) continue;
      for (const k of Object.keys(p.influence)) {
        p.influence[k] = Math.max(0, p.influence[k] - 0.5);
      }
    }
  }

  militaryPower(playerIdx) {
    let power = 0;
    for (const u of this.units) {
      if (u.owner !== playerIdx || u.isCivilian) continue;
      power += Math.max(u.def.cs, u.def.rs || 0) * (u.hp / 100);
    }
    return power;
  }

  score(playerIdx) {
    const p = this.players[playerIdx];
    if (!p.alive) return 0;
    let s = 0;
    for (const c of this.cities) if (c.owner === playerIdx) s += 25 + c.pop * 6 +
      c.buildings.reduce((a, b) => a + (BUILDINGS[b].wonder ? 25 : 5), 0);
    s += p.techs.size * 8;
    s += this.map.tiles.filter(t => t.owner === playerIdx).length;
    return Math.floor(s);
  }

  // ---------- turn processing ----------
  processCityTurn(city) {
    const p = this.players[city.owner];
    const y = this.cityYields(city);

    // growth (unhappy empires grow slowly; miserable ones not at all)
    let surplus = y.food - city.pop * 2;
    if (!p.isMinor && surplus > 0) {
      const hap = this.happinessOf(p.index);
      if (hap < HAPPINESS.strikeAt) surplus = 0;
      else if (hap < 0) surplus = Math.floor(surplus / 2);
    }
    city.food += surplus;
    if (city.food >= city.foodNeeded()) { city.food -= city.foodNeeded(); city.pop++; this.notify(`${city.name} grew to ${city.pop}.`, city.owner); }
    else if (city.food < 0) { city.food = 0; if (city.pop > 1) { city.pop--; this.notify(`${city.name} is starving!`, city.owner); } }

    // production
    if (city.producing) {
      let prod = y.prod;
      const item = city.producing;
      if (item.kind === "building" && p.civ.buildingProdBonus) prod = Math.floor(prod * (1 + p.civ.buildingProdBonus));
      if (p.goldenAgeTurns > 0) prod = Math.floor(prod * (1 + GOLDEN_AGE.bonus));
      city.prodStored += prod;
      const cost = item.kind === "unit" ? UNITS[item.key].cost : BUILDINGS[item.key].cost;
      if (city.prodStored >= cost) {
        // wonder race check
        if (item.kind === "building" && BUILDINGS[item.key].wonder &&
            this.cities.some(c => c.buildings.includes(item.key))) {
          city.prodStored = Math.floor(city.prodStored * 0.5);
          this.notify(`${BUILDINGS[item.key].name} was completed elsewhere first!`, city.owner);
        } else {
          city.prodStored -= cost;
          this.completeProduction(city, item);
          this.notify(`${city.name} finished ${item.kind === "unit" ? UNITS[item.key].name : BUILDINGS[item.key].name}.`, city.owner);
        }
        city.producing = null;
      }
    }

    // border growth
    city.cultureStored += y.culture;
    if (city.cultureStored >= city.borderCost()) {
      city.cultureStored -= city.borderCost();
      const target = this.bestBorderTile(city);
      if (target) { target.owner = city.owner; city.expansions++; }
    }

    // heal city
    if (city.hp < city.maxHp) city.hp = Math.min(city.maxHp, city.hp + 15);

    return y;
  }

  bestBorderTile(city) {
    let best = null, bestScore = -1;
    for (const [c, r] of HEX.ring(city.c, city.r, 3)) {
      const t = this.tile(c, r);
      if (!t || t.owner !== -1) continue;
      // must touch already-owned territory
      const touches = HEX.neighbors(c, r).some(([nc, nr]) => {
        const n = this.tile(nc, nr);
        return n && n.owner === city.owner;
      });
      if (!touches) continue;
      const y = this.tileYield(t);
      let s = y.food * 1.3 + y.prod + y.gold * 0.5 + (t.resource ? 3 : 0);
      s -= HEX.distance(c, r, city.c, city.r) * 0.3;
      if (s > bestScore) { bestScore = s; best = t; }
    }
    return best;
  }

  processPlayerEconomy(p) {
    if (!p.alive) return;
    this.dirtyHappiness(); // borders/pop may have changed since last compute
    let gold = 0, sci = 0, faith = 0;
    for (const city of this.cities) {
      if (city.owner !== p.index) continue;
      const y = this.processCityTurn(city);
      gold += y.gold; sci += y.sci; faith += y.faith;
    }
    if (p.goldenAgeTurns > 0 && gold > 0) gold = Math.floor(gold * (1 + GOLDEN_AGE.bonus));
    // unit maintenance: first 4 free
    const nUnits = this.units.filter(u => u.owner === p.index).length;
    gold -= Math.max(0, nUnits - 4);
    if (!p.isMinor) {
      // golden age bookkeeping: surplus happiness fills the meter
      const hap = this.happinessOf(p.index);
      if (p.goldenAgeTurns > 0) {
        p.goldenAgeTurns--;
        if (p.goldenAgeTurns === 0) this.notify("The Golden Age has ended.", p.index);
      } else {
        p.gaMeter += Math.max(0, hap);
        if (p.gaMeter >= GOLDEN_AGE.threshold(p.gaCount)) {
          p.gaMeter = 0;
          p.gaCount++;
          p.goldenAgeTurns = GOLDEN_AGE.duration;
          this.notify(`✨ ${p.civ.name} enters a GOLDEN AGE! (+20% gold and production for ${GOLDEN_AGE.duration} turns)`, -1);
        }
      }
      if (hap < 0 && (p._lastHap ?? 0) >= 0) {
        this.notify(`😞 Your empire is unhappy (${hap}) — growth is slowed. Build Taverns and secure luxuries!`, p.index);
      }
      if (hap < HAPPINESS.strikeAt && (p._lastHap ?? 0) >= HAPPINESS.strikeAt) {
        this.notify(`🔥 Unrest! Happiness ${hap}: growth has stopped and your units fight at -15% strength.`, p.index);
      }
      p._lastHap = hap;
    }
    if (!p.isMinor) {
      gold += this.minorBonuses(p.index).gold;
      // Tithe: gold from every follower city in the world
      if (p.religionId !== null && this.religions[p.religionId].belief === "TITHE") {
        gold += this.religionFollowers(p.religionId);
      }
      p.faith += faith;
    }
    p.gold += gold;
    if (p.gold < 0) {
      p.gold = 0;
      const armies = this.units.filter(u => u.owner === p.index && !u.isCivilian);
      if (armies.length > 1) {
        const victim = armies[Math.floor(this.rng() * armies.length)];
        this.removeUnit(victim);
        this.notify(`A ${victim.def.name} disbanded — the treasury is empty!`, p.index);
      }
    }

    // research
    if (p.researching && p.techs.has(p.researching)) p.researching = null; // e.g. stolen by spies
    if (!p.researching) {
      const av = p.availableTechs();
      if (av.length && !p.isHuman) p.researching = av.sort((x, y2) => TECHS[x].cost - TECHS[y2].cost)[0];
    }
    if (p.researching) {
      p.scienceStored += sci;
      const t = TECHS[p.researching];
      if (p.scienceStored >= t.cost) {
        p.scienceStored -= t.cost;
        p.techs.add(p.researching);
        this.notify(`🔬 Research complete: ${t.name}!`, p.index);
        p.researching = null;
      }
    } else if (p.isHuman) {
      p.scienceStored += sci; // banks until a tech is chosen
    }
  }

  // Cities bombard one hostile unit within range 2 every turn
  cityStrikes(p) {
    for (const city of this.cities) {
      if (city.owner !== p.index) continue;
      let target = null, bestScore = -Infinity;
      for (const [c, r] of HEX.ring(city.c, city.r, 2)) {
        const u = this.combatUnitAt(c, r);
        if (!u || !p.atWarWith.has(u.owner)) continue;
        const score = 100 - u.hp + (this.isEmbarked(u) ? 50 : 0);
        if (score > bestScore) { bestScore = score; target = u; }
      }
      if (!target) continue;
      const dmg = this.damageRoll(this.cityStrength(city) * 0.5, this.strengthOf(target, {}));
      target.hp -= dmg;
      this.addEffect(target.c, target.r, "-" + dmg, "#66ccff");
      if (target.hp <= 0) {
        this.removeUnit(target);
        this.notify(`Your ${target.def.name} fell to ${city.name}'s defenses!`, target.owner);
      }
    }
  }

  healUnits(p) {
    for (const u of this.units) {
      if (u.owner !== p.index || u.hp >= 100) continue;
      const t = this.tile(u.c, u.r);
      const moved = u.moves < u.def.moves || u.attacked;
      if (moved) continue;
      let heal = 5;
      if (this.isWater(t)) heal = u.def.naval && t.owner === p.index ? 10 : 0; // ships mend in home waters
      else if (t.owner === p.index) heal = 10;
      if (t.city && t.city.owner === p.index) heal = 20;
      if (t.owner !== -1 && this.players[p.index].atWarWith.has(t.owner)) heal = 0;
      u.hp = Math.min(100, u.hp + heal);
    }
  }

  // Ends the ACTIVE human's turn. With multiple humans (hotseat) this
  // advances to the next human; after the last one the AI phase runs
  // and the world clock advances.
  endTurn() {
    if (this.over) return;
    const human = this.players[this.activeHuman];
    this.cityStrikes(human);
    this.healUnits(human);
    this.progressWorkers(human);
    this.processPlayerEconomy(human);
    this.updateVisibility(human);

    // hand over to the next living human, if any
    let next = this.activeHuman + 1;
    while (next < this.humans && !this.players[next].alive) next++;
    if (next < this.humans) {
      this.activeHuman = next;
      this.beginHumanTurn(next);
      return;
    }

    // AI phase (majors beyond the humans, then city-states)
    for (let i = this.humans; i < this.players.length; i++) {
      const p = this.players[i];
      if (!p.alive) continue;
      AI.takeTurn(this, p);
      this.cityStrikes(p);
      this.healUnits(p);
      this.progressWorkers(p);
      this.processPlayerEconomy(p);
      this.updateVisibility(p);
    }

    // war weariness bookkeeping
    for (const p of this.players) {
      for (const enemy of p.atWarWith) {
        p.warWeariness[enemy] = (p.warWeariness[enemy] || 0) + 1;
      }
    }

    this.spreadReligionPressure();
    this.processMinorGifts();
    this.decayInfluence();
    this.processEspionage();

    this.turn++;
    for (const u of this.units) u.resetTurn();
    let first = 0;
    while (first < this.humans - 1 && !this.players[first].alive) first++;
    this.activeHuman = first;
    this.beginHumanTurn(first);
    this.checkVictory();
  }

  // Housekeeping when a human's turn starts: queued paths + auto-explore
  beginHumanTurn(idx) {
    for (const u of this.units) {
      if (u.owner === idx && u.path && u.path.length) this.stepAlongPath(u);
    }
    for (const u of this.units) {
      if (u.owner === idx && u.autoExplore && u.moves > 0) AI.autoExplore(this, u);
    }
    this.updateVisibility(this.players[idx]);
  }

  checkVictory() {
    if (this.over) return;
    if (this.scenario) {
      const sc = SCENARIOS[this.scenario];
      const me = this.players[0];
      if (sc.victory.type === "capture") {
        const target = this.players.find(p => p.civId === sc.victory.target);
        const cap = this.cities.find(c => c.id === target.originalCapitalId);
        if ((cap && cap.owner === 0) || !target.alive) {
          this.over = true; this.winner = 0; this.victoryType = "Scenario";
        } else if (this.turn > this.maxTurns || !me.alive) {
          this.over = true; this.winner = target.index; this.victoryType = "Scenario";
        }
      } else { // survive
        const myCap = this.cities.find(c => c.id === me.originalCapitalId);
        const foe = this.players.find(p => p.civId ===
          (sc.warsAtStart[0][0] === me.civId ? sc.warsAtStart[0][1] : sc.warsAtStart[0][0]));
        if (!me.alive || (this.turn > 3 && (!myCap || myCap.owner !== 0))) {
          this.over = true; this.winner = foe ? foe.index : 1; this.victoryType = "Scenario";
        } else if (this.turn > this.maxTurns) {
          this.over = true; this.winner = 0; this.victoryType = "Scenario";
        }
      }
      return; // scenario games skip the standard victory rules
    }
    const majors = this.players.filter(p => !p.isMinor);
    const alive = majors.filter(p => p.alive);
    if (alive.length === 1) {
      this.over = true; this.winner = alive[0].index; this.victoryType = "Domination";
      return;
    }
    // domination: hold every major civ's original capital
    if (this.cities.length) {
      const capitals = this.cities.filter(c => majors.some(p => p.originalCapitalId === c.id));
      if (capitals.length >= 2) {
        const owners = new Set(capitals.map(c => c.owner));
        if (owners.size === 1 && !this.players[[...owners][0]].isMinor) {
          this.over = true; this.winner = [...owners][0]; this.victoryType = "Domination";
          return;
        }
      }
    }
    if (this.turn > this.maxTurns) {
      let best = -1, bestScore = -1;
      for (const p of majors) {
        const s = this.score(p.index);
        if (p.alive && s > bestScore) { bestScore = s; best = p.index; }
      }
      this.over = true; this.winner = best; this.victoryType = "Score";
    }
  }

  // ---------- save / load ----------
  serialize() {
    return JSON.stringify({
      v: 1, turn: this.turn, seed: this.seed, mapType: this.mapType,
      difficulty: this.difficulty, humans: this.humans, activeHuman: this.activeHuman,
      scenario: this.scenario, over: this.over,
      winner: this.winner, victoryType: this.victoryType, nextId: NEXT_ID,
      religions: this.religions,
      map: { w: this.map.w, h: this.map.h, tiles: this.map.tiles.map(t => ({
        c: t.c, r: t.r, terrain: t.terrain, feature: t.feature, resource: t.resource,
        improvement: t.improvement, owner: t.owner, cityId: t.city ? t.city.id : null })) },
      players: this.players.map(p => ({
        index: p.index, civId: p.civId, isHuman: p.isHuman, alive: p.alive,
        gold: p.gold, scienceStored: p.scienceStored, researching: p.researching,
        techs: [...p.techs], atWarWith: [...p.atWarWith], met: [...p.met],
        warWeariness: p.warWeariness, cityNameCursor: p.cityNameCursor,
        visible: Array.from(p.visible), originalCapitalId: p.originalCapitalId,
        faith: p.faith, religionId: p.religionId, influence: p.influence,
        gaMeter: p.gaMeter, goldenAgeTurns: p.goldenAgeTurns, gaCount: p.gaCount,
        spies: p.spies })),
      cities: this.cities.map(c => ({ ...c })),
      units: this.units.map(u => ({ id: u.id, type: u.type, owner: u.owner, c: u.c, r: u.r,
        hp: u.hp, moves: u.moves, fortified: u.fortified, attacked: u.attacked, path: u.path,
        xp: u.xp, level: u.level, building: u.building, charges: u.charges,
        autoExplore: u.autoExplore || false })),
      notifications: this.notifications.slice(-30),
    });
  }

  static deserialize(json) {
    const d = JSON.parse(json);
    const g = Object.create(Game.prototype);
    g.turn = d.turn; g.seed = d.seed; g.mapType = d.mapType || "peninsula"; g.over = d.over;
    g.difficulty = d.difficulty || "normal";
    g.humans = d.humans || 1;
    g.activeHuman = d.activeHuman || 0;
    g._viewer = null;
    g.scenario = d.scenario || null;
    if (g.scenario && SCENARIOS[g.scenario]) g.maxTurns = SCENARIOS[g.scenario].victory.turns;
    g.effects = [];
    g.anims = [];
    g.winner = d.winner; g.victoryType = d.victoryType;
    if (!g.scenario) g.maxTurns = GAME_DEFAULTS.maxTurns;
    g.rng = mulberry32((d.seed + d.turn * 7919) >>> 0);
    g.notifications = d.notifications || [];
    g.religions = d.religions || [];
    NEXT_ID = d.nextId;

    g.map = { w: d.map.w, h: d.map.h, tiles: [], idx: (c, r) => r * d.map.w + c, seed: d.seed };
    for (const td of d.map.tiles) {
      g.map.tiles.push({ c: td.c, r: td.r, terrain: td.terrain, feature: td.feature,
        resource: td.resource, improvement: td.improvement ?? null,
        owner: td.owner, city: null, workedBy: null, _cityId: td.cityId });
    }
    g.cities = d.cities.map(cd => Object.assign(new City(cd.name, cd.owner, cd.c, cd.r), cd));
    for (const t of g.map.tiles) {
      if (t._cityId != null) t.city = g.cities.find(c => c.id === t._cityId) || null;
      delete t._cityId;
    }
    g.units = d.units.map(ud => Object.assign(new Unit(ud.type, ud.owner, ud.c, ud.r), ud));
    g.players = d.players.map(pd => {
      const p = new Player(pd.index, pd.civId, pd.isHuman);
      p.alive = pd.alive; p.gold = pd.gold; p.scienceStored = pd.scienceStored;
      p.researching = pd.researching; p.techs = new Set(pd.techs);
      p.atWarWith = new Set(pd.atWarWith); p.met = new Set(pd.met);
      p.warWeariness = pd.warWeariness || {}; p.cityNameCursor = pd.cityNameCursor;
      p.visible = Uint8Array.from(pd.visible); p.originalCapitalId = pd.originalCapitalId;
      p.faith = pd.faith || 0; p.religionId = pd.religionId ?? null;
      p.influence = pd.influence || {};
      p.gaMeter = pd.gaMeter || 0; p.goldenAgeTurns = pd.goldenAgeTurns || 0;
      p.gaCount = pd.gaCount || 0; p.spies = pd.spies || [];
      return p;
    });
    return g;
  }
}
