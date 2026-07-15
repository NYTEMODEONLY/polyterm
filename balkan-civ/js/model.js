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
    this.level = 0;              // veteran level (+5% strength each)
    this.promos = [];            // chosen promotions (keys into PROMOS)
    this.promoPts = 0;           // unspent promotion picks
    this.building = null;        // worker job: {type, turnsLeft}
    this.charges = UNITS[type].charges || 0; // missionary spreads
    this.healFortify = false;    // fortified until fully healed
    this.autoExplore = false;    // automated Scout exploration
    this.unsuppliedTurns = 0;    // consecutive completed turns beyond naval supply
    this.resupplying = false;    // AI return-to-port mission survives across turns
  }
  get def() { return UNITS[this.type]; }
  get isCivilian() { return !!this.def.civilian; }
  get isRanged() { return !!this.def.rs; }
  get maxMoves() { return this.def.moves + (this.promos.includes("NAVIGATION") ? 1 : 0); }
  resetTurn() { this.moves = this.building ? 0 : this.maxMoves; this.attacked = false; }

  addPromotion(key) {
    if (this.promos.includes(key)) return false;
    this.promos.push(key);
    if (key === "NAVIGATION" && !this.attacked && this.moves > 0) this.moves++;
    return true;
  }

  gainXp(amount) {
    if (this.isCivilian) return;
    this.xp += amount;
    const thresholds = [15, 45, 90];
    while (this.level < 3 && this.xp >= thresholds[this.level]) {
      this.level++;
      this.promoPts++;           // pick a promotion (or the AI auto-picks)
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
    this.queue = [];             // production queue after the current item
    this.focus = "balanced";     // citizen tile-assignment priority
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
    this.gpPoints = { sci: 0, eng: 0, gen: 0 };
    this.gpBorn = { sci: 0, eng: 0, gen: 0 };
    this.culture = 0;            // stored culture toward the next policy
    this.policies = new Set();   // adopted policy keys
    this.attitude = {};          // other player index -> -100..100
    this.pacts = new Set();      // defensive-pact partner indexes
    this.deals = [];             // luxury deals: {give, get, other, ends}
    this.quest = null;           // minors: the active quest they offer
    this.moodTurns = 0;          // turns left on a temporary happiness swing
    this.moodDelta = 0;          // size of that swing (+ festival, - unrest)
    this.lastEventTurn = -99;    // last turn a random event hit this player
    this.leaderIdx = 0;          // which of the civ's leaders is chosen
    this.congressVote = null;    // World Congress: chosen candidate index
    this.congressVoteTurn = -1;  // the session (turn) that vote belongs to
    this.missionarySpreads = 0;  // active spreads toward a Religious Victory
  }
  get civ() {
    const base = CIVS[this.civId];
    if (!base.leaders) return base;
    const L = base.leaders[this.leaderIdx] || base.leaders[0];
    // cache the merged view per (civId, leaderIdx) so hot paths stay cheap
    if (!this._civCache || this._civLeader !== this.leaderIdx) {
      this._civCache = Object.assign({}, base, L);
      this._civLeader = this.leaderIdx;
    }
    return this._civCache;
  }
  get leaderName() { const b = CIVS[this.civId]; return b.leaders ? (b.leaders[this.leaderIdx] || b.leaders[0]).leader : "—"; }
  get isMinor() { return !!this.civ.minor; }
  get isBarb() { return !!this.civ.barb; }
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
    this.maxTurns = SPEEDS[SPEEDS[opts.speed] ? opts.speed : "standard"].turns;
    this.seed = opts.seed ?? Math.floor(Math.random() * 1e9);
    this.rng = mulberry32(this.seed);
    this.mapType = opts.mapType || "peninsula";
    this.humans = Math.max(1, opts.numHumans || 1);
    this.activeHuman = 0;
    this._viewer = null;         // network client override (not saved)
    this.scenario = opts.scenario || null;
    this.scenarioKills = 0;      // for "kills"-type scenario objectives
    this.noBarbs = !!opts.noBarbs || !!opts.scenario; // scenarios stay historical
    this.camps = [];             // barbarian camps [{c, r, nextSpawn}]
    this.barbIndex = -1;
    this.speed = SPEEDS[opts.speed] ? opts.speed : "standard";
    this.routes = [];            // trade routes [{owner, fromId, toId, path, ends}]
    this.history = [];           // score history for the replay graph
    this.congressTurn = -999;    // last World Congress session turn
    this.congressLast = null;    // last session tally (for the UI)
    this.peaceOffers = [];       // AI->human peace proposals awaiting a decision [{from,to}]
    this.anims = [];             // transient movement animations (not saved)
    if (this.mapType === "custom" && opts.customMap) {
      const cm = opts.customMap;
      this.map = { w: cm.w, h: cm.h, idx: (c, r) => r * cm.w + c, seed: this.seed,
        tiles: cm.tiles.map((t, i) => ({ c: i % cm.w, r: Math.floor(i / cm.w),
          terrain: t.terrain, feature: t.feature || null, resource: t.resource || null,
          improvement: null, road: false, river: !!t.river,
          owner: -1, city: null, workedBy: null })) };
    } else {
      this.map = generateMap(opts.mapW || GAME_DEFAULTS.mapW, opts.mapH || GAME_DEFAULTS.mapH, this.seed, this.mapType);
    }
    this.units = [];
    this.cities = [];
    this.players = [];
    this.notifications = [];
    this.effects = [];           // transient combat popups (not saved)
    this.strikes = [];           // transient attack animations (not saved)
    this.lastCombat = null;      // latest resolved attack (transient UI/report data)
    this.stats = { steals: 0, catches: 0 };
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
      // leader selection: explicit per-player list (online), else player 0's
      // chosen leader and a random leader for everyone else
      const nLeaders = (CIVS[cid].leaders || [{}]).length;
      if (opts.leaders && opts.leaders[i] != null) p.leaderIdx = opts.leaders[i] % nLeaders;
      else if (i === 0 && opts.playerLeader != null) p.leaderIdx = opts.playerLeader % nLeaders;
      else if (this.scenario) {
        const scenarioLeader = SCENARIOS[this.scenario]?.leaders?.[cid];
        p.leaderIdx = scenarioLeader == null ? 0 : scenarioLeader % nLeaders;
      } else {
        // Scenario additions must not silently rebalance established seeded games.
        // They remain selectable by humans and explicit online rosters.
        const randomPool = CIVS[cid].leaders.map((leader, index) => ({ leader, index }))
          .filter(entry => entry.leader.randomAI !== false);
        p.leaderIdx = randomPool[Math.floor(this.rng() * randomPool.length)].index;
      }
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

    // the barbarian horde: a hidden player at war with everyone
    if (!this.noBarbs) {
      const bp = new Player(this.players.length, "BARBARIANS", false);
      bp.visible = new Uint8Array(this.map.w * this.map.h);
      this.barbIndex = bp.index;
      for (const p of this.players) {
        p.atWarWith.add(bp.index);
        bp.atWarWith.add(p.index);
        p.met.add(bp.index);
        bp.met.add(p.index);
      }
      this.players.push(bp);
      // seed camps on wild land, away from every start
      const landTiles = this.map.tiles.filter(t => TERRAIN[t.terrain].passable);
      const want = Math.max(2, Math.round(landTiles.length / BARB.campEvery));
      let guard = 0;
      while (this.camps.length < want && guard++ < 400) {
        const t = landTiles[Math.floor(this.rng() * landTiles.length)];
        if (t.owner !== -1 || t.city || t.ruin) continue;
        const farFromAll = this.units.every(u => HEX.distance(u.c, u.r, t.c, t.r) >= 5) &&
          this.camps.every(cp => HEX.distance(cp.c, cp.r, t.c, t.r) >= 5);
        if (farFromAll) this.camps.push({ c: t.c, r: t.r, nextSpawn: 12 + Math.floor(this.rng() * 8) });
      }
      this.maxCamps = this.camps.length;
    }
  }

  campAt(c, r) { return this.camps.find(cp => cp.c === c && cp.r === r); }

  // Camp spawning + occasional new camps (world phase, each turn)
  processBarbarians() {
    if (this.barbIndex < 0) return;
    const bp = this.players[this.barbIndex];
    const barbUnits = this.units.filter(u => u.owner === this.barbIndex);
    const cap = this.camps.length + 2;
    // spawn era-appropriate raiders
    const avgEra = Math.round(this.players.filter(p => !p.isMinor && !p.isBarb && p.alive)
      .reduce((a, p) => a + p.era(), 0) /
      Math.max(1, this.players.filter(p => !p.isMinor && !p.isBarb && p.alive).length));
    const pool = [["WARRIOR", "ARCHER"], ["SPEARMAN", "HORSEMAN"],
      ["PIKEMAN", "CROSSBOW"], ["MUSKETMAN", "CROSSBOW"]][Math.min(3, avgEra)];
    for (const camp of this.camps) {
      if (this.turn < camp.nextSpawn || barbUnits.length >= cap) continue;
      const spot = !this.combatUnitAt(camp.c, camp.r) ? [camp.c, camp.r]
        : this.freeAdjacent(camp.c, camp.r);
      if (!spot) continue;
      const type = pool[Math.floor(this.rng() * pool.length)];
      this.addUnit(type, this.barbIndex, spot[0], spot[1]);
      barbUnits.push(null); // count it against the cap
      camp.nextSpawn = this.turn + BARB.spawnEvery + Math.floor(this.rng() * 5);
    }
    // wilderness breeds new camps, but only while it is truly wild
    if (this.turn % BARB.newCampEvery === 0 && this.camps.length < Math.ceil(this.maxCamps / 2)) {
      const landTiles = this.map.tiles.filter(t => TERRAIN[t.terrain].passable &&
        t.owner === -1 && !t.city && !this.campAt(t.c, t.r));
      for (let tries = 0; tries < 40; tries++) {
        const t = landTiles[Math.floor(this.rng() * landTiles.length)];
        if (!t) break;
        if (this.cities.every(c => HEX.distance(c.c, c.r, t.c, t.r) >= 5)) {
          this.camps.push({ c: t.c, r: t.r, nextSpawn: this.turn + 3 });
          break;
        }
      }
    }
  }

  // Camp burning + ruin plundering when a unit arrives on a tile
  checkTileDiscoveries(unit) {
    const p = this.players[unit.owner];
    if (p.isBarb) return;
    const t = this.tile(unit.c, unit.r);
    if (!t) return;
    const camp = this.campAt(unit.c, unit.r);
    if (camp && !unit.isCivilian) {
      this.camps.splice(this.camps.indexOf(camp), 1);
      p.gold += BARB.clearReward;
      if (!this.stats) this.stats = { steals: 0, catches: 0 };
      this.stats.campsCleared = (this.stats.campsCleared || 0) + 1;
      this.addEffect(unit.c, unit.r, "+" + BARB.clearReward + "💰", "#f1c40f");
      this.notify(`🏕️ Barbarian camp burned — +${BARB.clearReward} gold!`, unit.owner);
      this.questEvent("CLEAR_CAMP", unit.owner, { c: unit.c, r: unit.r });
    }
    if (t.ruin) {
      t.ruin = false;
      if (!this.stats) this.stats = { steals: 0, catches: 0 };
      this.stats.ruins = (this.stats.ruins || 0) + 1;
      const reward = RUIN_REWARDS[Math.floor(this.rng() * RUIN_REWARDS.length)];
      if (reward === "gold") {
        p.gold += 45;
        this.addEffect(unit.c, unit.r, "+45💰", "#f1c40f");
        this.notify("🏺 Ancient ruins: a cache of gold (+45)!", unit.owner);
      } else if (reward === "faith") {
        p.faith += 25;
        this.notify("🏺 Ancient ruins: a forgotten shrine (+25 faith).", unit.owner);
      } else if (reward === "science") {
        p.scienceStored += 40;
        this.notify("🏺 Ancient ruins: lost writings (+40 science).", unit.owner);
      } else if (reward === "xp") {
        unit.gainXp(20);
        unit.hp = 100;
        this.notify("🏺 Ancient ruins: survivors join your ranks (+20 XP, healed).", unit.owner);
      } else {
        for (const [rc, rr] of HEX.ring(unit.c, unit.r, 4)) {
          const rt = this.tile(rc, rr);
          if (rt && p.visible[this.map.idx(rc, rr)] === 0) p.visible[this.map.idx(rc, rr)] = 1;
        }
        this.notify("🏺 Ancient ruins: an old map reveals the surrounding lands.", unit.owner);
      }
    }
  }

  techCost(key) {
    return Math.round(TECHS[key].cost * SPEEDS[this.speed].tech);
  }

  // ---------- trade routes ----------
  routeIncome(fromCity, toCity) {
    const dist = HEX.distance(fromCity.c, fromCity.r, toCity.c, toCity.r);
    return 2 + Math.floor(dist / 2) + (fromCity.owner === toCity.owner ? 0 : 2);
  }

  blockadeStrength(unit) {
    if (!unit || unit.isCivilian || !unit.def.naval) return 0;
    const base = Math.max(unit.def.cs || 0, unit.def.rs || 0);
    const health = 0.5 + 0.5 * Math.max(0, Math.min(100, unit.hp)) / 100;
    const supply = (unit.unsuppliedTurns || 0) > NAVAL_SUPPLY.graceTurns &&
      !this.navalSupply(unit).supplied
      ? NAVAL_SUPPLY.combatMultiplier : 1;
    return base * health * (1 + unit.level * 0.05) * supply;
  }

  cityBlockade(city) {
    const clear = { active: false, attackers: [], defenders: [], attackPower: 0, defensePower: 0 };
    if (!city || !city.coastal || !this.cities.includes(city)) return clear;
    const owner = this.players[city.owner];
    if (!owner || !owner.alive) return clear;
    for (const unit of this.units) {
      if (unit.isCivilian || !unit.def.naval ||
          HEX.distance(city.c, city.r, unit.c, unit.r) > BLOCKADE.radius) continue;
      if (unit.owner === city.owner) clear.defenders.push(unit);
      else if (owner.atWarWith.has(unit.owner)) clear.attackers.push(unit);
    }
    clear.attackPower = clear.attackers.reduce((sum, unit) => sum + this.blockadeStrength(unit), 0);
    clear.defensePower = clear.defenders.reduce((sum, unit) => sum + this.blockadeStrength(unit), 0);
    clear.active = clear.attackers.length > 0 && clear.attackPower > clear.defensePower;
    return clear;
  }

  navalSupplyRange(owner) {
    const p = this.players[owner];
    if (!p) return 0;
    if (p.hasTech("STEAM_POWER")) return NAVAL_SUPPLY.steamRange;
    if (p.hasTech("COMPASS")) return NAVAL_SUPPLY.compassRange;
    return NAVAL_SUPPLY.baseRange;
  }

  // Multi-source breadth-first coverage keeps supply tied to connected water,
  // so a nearby port on the other side of a peninsula cannot service a fleet.
  navalSupplyCoverage(unit) {
    const coverage = new Map();
    if (!unit || !unit.def.naval || !this.players[unit.owner]) return coverage;
    const range = this.navalSupplyRange(unit.owner);
    const queue = [];
    const ports = this.cities.filter(city => city.owner === unit.owner && city.coastal)
      .sort((a, b) => a.id - b.id);
    for (const city of ports) {
      for (const [c, r] of HEX.neighbors(city.c, city.r)) {
        const tile = this.tile(c, r);
        if (!tile || !this.isWater(tile) || !this.unitPassable(unit, tile)) continue;
        const key = this.map.idx(c, r);
        const prior = coverage.get(key);
        if (prior && prior.source.id <= city.id) continue;
        coverage.set(key, { source: city, distance: 0 });
        queue.push([c, r]);
      }
    }
    for (let head = 0; head < queue.length; head++) {
      const [c, r] = queue[head];
      const current = coverage.get(this.map.idx(c, r));
      if (!current || current.distance >= range) continue;
      for (const [nc, nr] of HEX.neighbors(c, r)) {
        const tile = this.tile(nc, nr);
        if (!tile || !this.isWater(tile) || !this.unitPassable(unit, tile)) continue;
        const key = this.map.idx(nc, nr);
        const nextDistance = current.distance + 1;
        const prior = coverage.get(key);
        if (prior && (prior.distance < nextDistance ||
            (prior.distance === nextDistance && prior.source.id <= current.source.id))) continue;
        coverage.set(key, { source: current.source, distance: nextDistance });
        queue.push([nc, nr]);
      }
    }
    return coverage;
  }

  navalSupply(unit) {
    if (!unit || !unit.def.naval) return { supplied: true, source: null, distance: 0,
      range: 0, turns: 0, graceLeft: NAVAL_SUPPLY.graceTurns, attritionActive: false };
    const entry = this.navalSupplyCoverage(unit).get(this.map.idx(unit.c, unit.r));
    const turns = Math.max(0, unit.unsuppliedTurns || 0);
    const supplied = !!entry;
    return { supplied, source: entry ? entry.source : null,
      distance: entry ? entry.distance : null, range: this.navalSupplyRange(unit.owner), turns,
      graceLeft: supplied ? NAVAL_SUPPLY.graceTurns : Math.max(0, NAVAL_SUPPLY.graceTurns - turns),
      attritionActive: !supplied && turns > NAVAL_SUPPLY.graceTurns };
  }

  navalResupplyDestination(unit) {
    if (!unit || !unit.def.naval) return null;
    const candidates = [];
    const ports = this.cities.filter(city => city.owner === unit.owner && city.coastal)
      .sort((a, b) => a.id - b.id);
    for (const city of ports) {
      for (const [c, r] of HEX.neighbors(city.c, city.r)) {
        const tile = this.tile(c, r);
        const occupant = this.combatUnitAt(c, r);
        if (!tile || !this.isWater(tile) || !this.unitPassable(unit, tile) ||
            (occupant && occupant.id !== unit.id)) continue;
        const path = this.findPath(unit, c, r);
        if (!path) continue;
        candidates.push({ c, r, city, pathLength: path.length });
      }
    }
    return candidates.sort((a, b) => a.pathLength - b.pathLength || a.city.id - b.city.id ||
      a.r - b.r || a.c - b.c)[0] || null;
  }

  tradeRouteStatus(route) {
    const from = route && this.cities.find(city => city.id === route.fromId);
    const to = route && this.cities.find(city => city.id === route.toId);
    if (!from || !to) return { active: false, reason: "invalid", from, to };
    const fromBlockade = this.cityBlockade(from);
    const toBlockade = this.cityBlockade(to);
    const blocked = fromBlockade.active || toBlockade.active;
    return { active: !blocked, reason: blocked ? "blockade" : null,
      from, to, fromBlockade, toBlockade };
  }

  // Cities a caravan standing in one of its own cities could trade with
  tradeDestinations(caravan) {
    const from = this.cityAt(caravan.c, caravan.r);
    const p = this.players[caravan.owner];
    if (!from || from.owner !== caravan.owner) return [];
    const routeCap = TRADE.maxRoutes + (p.policies.has("CARAVANSERAI") ? 1 : 0);
    if (this.routes.filter(r => r.owner === caravan.owner).length >= routeCap) return [];
    return this.cities.filter(c => {
      if (c === from) return false;
      if (HEX.distance(from.c, from.r, c.c, c.r) > TRADE.maxDist) return false;
      const o = this.players[c.owner];
      if (o.isBarb || p.atWarWith.has(c.owner)) return false;
      if (c.owner !== caravan.owner && !p.met.has(c.owner)) return false;
      if (this.routes.some(r => r.owner === caravan.owner && r.fromId === from.id && r.toId === c.id)) return false;
      return true;
    }).sort((a, b) => this.routeIncome(from, b) - this.routeIncome(from, a)).slice(0, 6);
  }

  establishRoute(caravan, destCityId, actorIdx = null) {
    if (!caravan || !this.units.includes(caravan) || !caravan.def.caravan || caravan.moves <= 0) return false;
    if (actorIdx !== null && !this.unitActorStatus(caravan, actorIdx).ok) return false;
    const from = this.cityAt(caravan.c, caravan.r);
    const dest = this.cities.find(c => c.id === destCityId);
    if (!from || !dest || !this.tradeDestinations(caravan).includes(dest)) return false;
    const path = this.findPath(caravan, dest.c, dest.r);
    if (!path) return false;
    this.routes.push({ owner: caravan.owner, fromId: from.id, toId: dest.id,
      path: [[caravan.c, caravan.r], ...path], ends: this.turn + TRADE.duration });
    this.removeUnit(caravan);
    if (!this.stats) this.stats = { steals: 0, catches: 0 };
    this.stats.routes = (this.stats.routes || 0) + 1;
    this.notify(`🐫 Trade route: ${from.name} → ${dest.name} (+${this.routeIncome(from, dest)} gold per turn).`, caravan.owner);
    return true;
  }

  tradeIncome(playerIdx) {
    let gold = 0;
    for (const r of this.routes) {
      const status = this.tradeRouteStatus(r);
      if (!status.active) continue;
      const { from, to } = status;
      if (r.owner === playerIdx) gold += this.routeIncome(from, to);
      else if (to.owner === playerIdx) gold += 1; // destination's cut
    }
    return gold;
  }

  processTradeRoutes() {
    for (let i = this.routes.length - 1; i >= 0; i--) {
      const r = this.routes[i];
      const from = this.cities.find(c => c.id === r.fromId);
      const to = this.cities.find(c => c.id === r.toId);
      const owner = this.players[r.owner];
      let dead = !from || !to || this.turn >= r.ends ||
        from.owner !== r.owner || owner.atWarWith.has(to.owner) || !owner.alive;
      let plunderer = -1;
      if (!dead) {
        // hostile boots on the caravan road plunder it
        for (const [c, rr] of r.path) {
          const u = this.combatUnitAt(c, rr);
          if (u && (owner.atWarWith.has(u.owner))) { dead = true; plunderer = u.owner; break; }
        }
      }
      if (dead) {
        this.routes.splice(i, 1);
        if (plunderer >= 0) {
          this.players[plunderer].gold += TRADE.plunderGold;
          this.notify(`🐫 Your trade route was plundered!`, r.owner);
          this.notify(`🐫 Trade caravan plundered — +${TRADE.plunderGold} gold!`, plunderer);
        } else if (this.turn >= r.ends && from && to) {
          this.notify(`🐫 The ${from.name} → ${to.name} trade route has run its course.`, r.owner);
        }
      }
    }
  }

  // ---------- great people ----------
  accrueGreatPeople(p) {
    if (p.isMinor || p.isBarb || !p.alive) return;
    let sci = 0, eng = 0;
    for (const c of this.cities) {
      if (c.owner !== p.index) continue;
      for (const b of c.buildings) {
        if (b === "LIBRARY") sci += 1;
        if (b === "UNIVERSITY" || b === "OHRID_SCHOOL") sci += 2;
        if (b === "FORGE") eng += 1;
        if (b === "WORKSHOP") eng += 2;
        if (BUILDINGS[b].wonder) eng += 1;
      }
    }
    p.gpPoints.sci += sci;
    p.gpPoints.eng += eng;
    const gpMul = this.policyBranchDone(p.index, "SABOR") ? 0.8 : 1;
    for (const type of ["sci", "eng", "gen"]) {
      if (p.gpPoints[type] < GP.threshold(p.gpBorn[type]) * gpMul) continue;
      const cap = this.cities.find(c => c.id === p.originalCapitalId && c.owner === p.index) ||
                  this.cities.find(c => c.owner === p.index);
      if (!cap) break;
      const spot = this.civilianAt(cap.c, cap.r) ? this.freeAdjacent(cap.c, cap.r) : [cap.c, cap.r];
      if (!spot) break;
      p.gpPoints[type] -= Math.floor(GP.threshold(p.gpBorn[type]) * gpMul);
      p.gpBorn[type]++;
      const key = { sci: "GREAT_SCIENTIST", eng: "GREAT_ENGINEER", gen: "GREAT_GENERAL" }[type];
      const u = this.addUnit(key, p.index, spot[0], spot[1]);
      u.gpName = GP_NAMES[type][(p.gpBorn[type] - 1) % GP_NAMES[type].length];
      if (!this.stats) this.stats = { steals: 0, catches: 0 };
      this.stats.greats = (this.stats.greats || 0) + 1;
      this.notify(`${UNITS[key].icon} A great soul is born in ${cap.name}: ${u.gpName} the ${UNITS[key].name.replace("Great ", "")}!`, p.index);
      this.addBurst(spot[0], spot[1], "#ffd700");
    }
  }

  useGreatPerson(unit, actorIdx = null) {
    if (!unit || !this.units.includes(unit) || !unit.def.great) return false;
    if (actorIdx !== null && !this.unitActorStatus(unit, actorIdx).ok) return false;
    const p = this.players[unit.owner];
    const kind = unit.def.great;
    if (kind === "sci") {
      if (p.researching) {
        p.techs.add(p.researching);
        this.notify(`🔭 ${unit.gpName || "The scientist"} completes ${TECHS[p.researching].name}!`, p.index);
        p.researching = null;
      } else {
        const av = p.availableTechs();
        if (!av.length) return false;
        const t = av.sort((a, b) => TECHS[a].cost - TECHS[b].cost)[0];
        p.techs.add(t);
        this.notify(`🔭 ${unit.gpName || "The scientist"} discovers ${TECHS[t].name}!`, p.index);
      }
      this.removeUnit(unit);
      return true;
    }
    if (kind === "eng") {
      const city = this.cityAt(unit.c, unit.r);
      if (!city || city.owner !== unit.owner) return false;
      city.prodStored += GP.engineerRush;
      this.notify(`🏗️ ${unit.gpName || "The engineer"} hurries the works of ${city.name} (+${GP.engineerRush} production).`, p.index);
      this.removeUnit(unit);
      return true;
    }
    return false; // generals are a passive aura
  }

  // ---------- unit upgrades ----------
  // Resolve base unit key to this civ's unique replacement, if any
  resolveUnitFor(p, key) {
    const uu = Object.entries(UNITS).find(([, v]) => v.uu === p.civId && v.replaces === key);
    return uu ? uu[0] : key;
  }

  canUpgrade(unit, actorIdx = null) {
    if (!unit || !this.units.includes(unit)) return null;
    if (actorIdx !== null && !this.unitActorStatus(unit, actorIdx).ok) return null;
    const p = this.players[unit.owner];
    const target = unit.def.upgrade ? this.resolveUnitFor(p, unit.def.upgrade) : null;
    if (!target) return null;
    const def = UNITS[target];
    if (def.tech && !p.hasTech(def.tech)) return null;
    if (def.needs && !this.playerHasResource(p.index, def.needs)) return null;
    const t = this.tile(unit.c, unit.r);
    if (!t || t.owner !== unit.owner) return null; // home territory only
    if (unit.moves <= 0 || unit.attacked) return null;
    const cost = 10 + Math.max(0, Math.round((def.cost - unit.def.cost) * 1.5));
    if (p.gold < cost) return null;
    return { to: target, cost };
  }

  upgradeUnit(unit, actorIdx = null) {
    const up = this.canUpgrade(unit, actorIdx);
    if (!up) return false;
    this.players[unit.owner].gold -= up.cost;
    unit.type = up.to;
    unit.moves = 0;
    unit.charges = UNITS[up.to].charges || 0;
    if (!this.stats) this.stats = { steals: 0, catches: 0 };
    this.stats.upgrades = (this.stats.upgrades || 0) + 1;
    return true;
  }

  // ---------- combat forecast (mirrors damageRoll's 0.85..1.15 spread) ----------
  predictAttack(unit, c, r) {
    if (!unit || unit.isCivilian) return null;
    const t = this.tile(c, r);
    if (!t) return null;
    if (this.isEmbarked(unit) && !this.canAttackFromEmbarked(unit, t)) return null;
    const ranged = unit.isRanged;
    const attStr = this.strengthOf(unit, { attacking: true, targetTile: t, ranged });
    const flankSupport = this.flankingSupport(unit, t).length;
    const flankBonus = Math.min(TACTICS.maxFlank, flankSupport * TACTICS.flankPerSupport);
    const span = (att, def) => {
      const base = 30 * Math.pow(att / Math.max(def, 0.5), 1.25);
      return [Math.max(1, Math.round(base * 0.85)), Math.max(1, Math.round(base * 1.15))];
    };
    const enemyCity = t.city && this.players[unit.owner].atWarWith.has(t.city.owner) ? t.city : null;
    const enemyUnit = (() => {
      const cu = this.combatUnitAt(c, r);
      return cu && this.players[unit.owner].atWarWith.has(cu.owner) ? cu : null;
    })();
    if (enemyCity && (!enemyUnit || !ranged)) {
      const defStr = this.cityStrength(enemyCity);
      return { target: enemyCity.name, targetHp: enemyCity.hp, city: true, flankSupport, flankBonus,
        out: span(attStr, defStr), back: ranged ? null : span(defStr, attStr) };
    }
    if (enemyUnit) {
      const defStr = this.strengthOf(enemyUnit, { attacking: false });
      return { target: enemyUnit.def.name, targetHp: enemyUnit.hp, city: false, flankSupport, flankBonus,
        out: span(attStr, defStr), back: ranged ? null : span(defStr, attStr) };
    }
    return null;
  }

  // One authoritative snapshot for every decision the human-facing turn UI tracks.
  pendingOrders(playerIdx) {
    const p = this.players[playerIdx];
    if (!p || !p.alive) return { research: false, congress: false, religion: false,
      policy: false, promotionUnit: null, cities: [], units: [] };
    return {
      research: !p.researching && p.availableTechs().length > 0,
      congress: !!(this.congressDue && this.congressDue() && p.congressVoteTurn !== this.turn),
      religion: this.canFoundReligion(playerIdx),
      policy: this.canAdoptPolicy(playerIdx),
      promotionUnit: this.units.find(u => u.owner === playerIdx && u.promoPts > 0 && !u.isCivilian) || null,
      cities: this.cities.filter(c => c.owner === playerIdx && !c.producing && !c.queue.length),
      units: this.units.filter(u => u.owner === playerIdx && u.moves > 0 && !u.fortified && !u.attacked &&
        !u.building && !u.autoExplore && !(u.path && u.path.length)),
    };
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
        const wantWater = !!UNITS[type].naval;
        for (const [c, r] of HEX.ring(home.c, home.r, 2)) {
          const t = this.tile(c, r);
          if (!t) continue;
          if (wantWater ? !this.isWater(t) : !TERRAIN[t.terrain].passable) continue;
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
    this.notify(`${sc.icon} ${sc.name}: ${this.scenarioStatus()}`, 0);
  }

  // Live objective readout for the top bar
  scenarioStatus() {
    if (!this.scenario) return "";
    const sc = SCENARIOS[this.scenario], v = sc.victory;
    const left = Math.max(0, this.maxTurns - this.turn + 1);
    const majors = this.players.filter(p => !p.isMinor);
    switch (v.type) {
      case "capture": {
        const target = this.players.find(p => p.civId === v.target);
        const cap = this.cities.find(c => c.id === target.originalCapitalId);
        return `🎯 Take ${cap ? cap.name : "the enemy capital"} · ${left} turns left`;
      }
      case "survive":
        return `🎯 Hold your capital · ${left} turns left`;
      case "capitals": {
        const n = this.cities.filter(c => c.owner === 0 &&
          majors.some(p => p.originalCapitalId === c.id)).length;
        return `🎯 Capitals ${n}/${v.count} · ${left} turns left`;
      }
      case "research":
        return `🎯 Techs ${this.players[0].techs.size}/${Object.keys(TECHS).length} · ${left} turns left`;
      case "kills":
        return `🎯 ${CIVS[v.target].adj} units slain ${this.scenarioKills}/${v.count} · ${left} turns left`;
      case "resistance": {
        const cap = this.cities.find(c => c.id === this.players[0].originalCapitalId);
        const hold = !cap ? "Found capital" : cap.owner === 0 ? `Hold ${cap.name}` : `${cap.name} fallen`;
        return `🎯 ${hold} · Kills ${this.scenarioKills}/${v.count} · ${left}t`;
      }
      case "cities":
        return `🎯 Cities ${this.cities.filter(c => c.owner === 0).length}/${v.count} · ${left} turns left`;
    }
    return "";
  }

  trackScenarioKill(killerIdx, victimIdx) {
    if (!this.scenario || killerIdx !== 0) return;
    const sc = SCENARIOS[this.scenario];
    if (sc.victory.type !== "kills" && sc.victory.type !== "resistance") return;
    const victim = this.players[victimIdx];
    if (victim && victim.civId === sc.victory.target) {
      this.scenarioKills++;
      this.checkVictory();
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

  canAttackFromEmbarked(unit, targetTile) {
    return !!(unit && targetTile && this.isEmbarked(unit) &&
      unit.promos.includes("AMPHIBIOUS") && !unit.isRanged && !unit.def.naval &&
      !this.isWater(targetTile) &&
      HEX.distance(unit.c, unit.r, targetTile.c, targetTile.r) === 1);
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

  // an expanding ring flourish at a tile (city founded, great person born)
  addBurst(c, r, color = "#f1c40f") {
    this.effects.push({ c, r, ring: true, color, ts: Date.now() });
    if (this.effects.length > 40) this.effects.shift();
  }

  // attacker lunge + defender flash, consumed by both renderers
  addStrike(unit, tc, tr, ranged) {
    this.strikes.push({ id: unit ? unit.id : null,
      fc: unit ? unit.c : tc, fr: unit ? unit.r : tr,
      tc, tr, ranged: !!ranged, ts: Date.now() });
    if (this.strikes.length > 24) this.strikes.shift();
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

  unitActorStatus(unit, actorIdx) {
    if (this.over) return { ok: false, code: "GAME_OVER", reason: "The game is complete." };
    if (!unit || !this.units.includes(unit))
      return { ok: false, code: "INVALID_UNIT", reason: "This unit is no longer available." };
    const actor = this.players[actorIdx];
    if (!actor || !actor.alive || !actor.isHuman)
      return { ok: false, code: "INVALID_ACTOR", reason: "No active player can issue this order." };
    if (unit.owner !== actorIdx)
      return { ok: false, code: "FOREIGN_UNIT", reason: "Only the owning civilization can command this unit." };
    if (this.activeHuman !== actorIdx)
      return { ok: false, code: "NOT_ACTIVE", reason: "Wait for this civilization's turn." };
    return { ok: true, code: "OK", reason: "Order available." };
  }

  unitOrderStatus(unit, order, actorIdx, detail = null) {
    const actor = this.unitActorStatus(unit, actorIdx);
    if (!actor.ok) return actor;
    const fail = (code, reason) => ({ ok: false, code, reason });
    if (order === "promote") {
      if (unit.isCivilian || unit.promoPts <= 0) return fail("NO_PROMOTION", "No promotion is available.");
      if (!promotionAvailable(unit, detail) || unit.promos.includes(detail))
        return fail("INVALID_PROMOTION", "This promotion cannot be selected.");
    } else if (order === "cancel_job") {
      if (!unit.def.worker || !unit.building) return fail("NO_JOB", "This Worker has no job to cancel.");
    } else if (order === "auto_explore") {
      if (unit.type !== "SCOUT") return fail("NOT_SCOUT", "Only Scouts can auto-explore.");
      const enabling = detail !== false;
      if (enabling && unit.autoExplore) return fail("ALREADY_AUTO", "Auto-explore is already active.");
      if (!enabling && !unit.autoExplore) return fail("NOT_AUTO", "Auto-explore is not active.");
      if (enabling && unit.moves <= 0) return fail("NO_MOVES", "No movement points remain this turn.");
    } else if (order === "fortify") {
      if (unit.isCivilian) return fail("CIVILIAN", "Civilian units cannot fortify.");
      if (unit.fortified) return fail("ALREADY_FORTIFIED", "This unit is already fortified.");
      if (unit.moves <= 0) return fail("NO_MOVES", "No movement points remain this turn.");
    } else if (order === "wake") {
      if (unit.isCivilian || (!unit.fortified && !unit.healFortify))
        return fail("NOT_FORTIFIED", "This unit is already awake.");
    } else if (order === "heal") {
      if (unit.isCivilian) return fail("CIVILIAN", "Civilian units cannot fortify to heal.");
      if (unit.hp >= 100) return fail("FULL_HEALTH", "This unit is already at full health.");
      if (unit.healFortify) return fail("ALREADY_HEALING", "This unit is already healing.");
      if (unit.moves <= 0) return fail("NO_MOVES", "No movement points remain this turn.");
    } else if (order === "skip") {
      if (unit.moves <= 0) return fail("NO_MOVES", "No movement points remain this turn.");
    } else if (order === "disband") {
      const ownsCity = this.cities.some(c => c.owner === actorIdx);
      const otherSettler = this.units.some(u => u !== unit && u.owner === actorIdx && u.type === "SETTLER");
      if (unit.type === "SETTLER" && !ownsCity && !otherSettler)
        return fail("LAST_SETTLER", "Found a capital before disbanding your only Settler.");
    } else {
      return fail("UNKNOWN_ORDER", "This unit order is not recognized.");
    }
    return { ok: true, code: "OK", reason: "Order available." };
  }

  issueUnitOrder(unit, order, actorIdx, detail = null) {
    if (!this.unitOrderStatus(unit, order, actorIdx, detail).ok) return false;
    if (order === "promote") {
      unit.addPromotion(detail);
      unit.promoPts--;
    } else if (order === "cancel_job") {
      unit.building = null;
      unit.path = null;
      unit.moves = 0;
    } else if (order === "auto_explore") {
      unit.autoExplore = detail !== false;
      if (unit.autoExplore) unit.path = null;
    } else if (order === "fortify") {
      unit.fortified = true;
      unit.healFortify = false;
      unit.autoExplore = false;
      unit.path = null;
      unit.moves = 0;
    } else if (order === "wake") {
      unit.fortified = false;
      unit.healFortify = false;
    } else if (order === "heal") {
      unit.fortified = true;
      unit.healFortify = true;
      unit.autoExplore = false;
      unit.path = null;
      unit.moves = 0;
    } else if (order === "skip") {
      unit.moves = 0;
    } else if (order === "disband") {
      this.removeUnit(unit);
      this.checkElimination(actorIdx);
    }
    return true;
  }

  moveCost(unit, c, r) {
    const t = this.tile(c, r);
    if (!this.unitPassable(unit, t)) return Infinity;
    if (this.isWater(t)) return 1;
    if (unit.def.naval) return Infinity;
    if (t.road || t.city) return 1;
    let cost = TERRAIN[t.terrain].moveCost;
    if (t.feature) cost = Math.max(cost, FEATURE[t.feature].moveCost);
    if (cost > 1 && cost < 99 && unit.promos && unit.promos.includes("PATHFINDER")) cost = 1;
    return cost;
  }

  // Land melee units control adjacent land while at war. Hidden controllers
  // still stop movement, but path and UI hints expose only currently seen ones.
  enemyZoneOfControl(unit, c, r) {
    const tile = this.tile(c, r);
    const owner = unit && this.players[unit.owner];
    if (!unit || !owner || unit.def.naval || this.isEmbarked(unit) || !tile || this.isWater(tile)) return [];
    return HEX.neighbors(c, r).map(([nc, nr]) => this.combatUnitAt(nc, nr)).filter(controller =>
      controller && controller.owner !== unit.owner && owner.atWarWith.has(controller.owner) &&
      !controller.def.naval && !controller.isRanged && !this.isEmbarked(controller));
  }

  knownEnemyZoneOfControl(unit, c, r) {
    const p = unit && this.players[unit.owner];
    if (!p || !p.visible) return [];
    return this.enemyZoneOfControl(unit, c, r).filter(controller =>
      p.visible[this.map.idx(controller.c, controller.r)] === 2);
  }

  // A player's own cities and roads in owned or neutral territory form a
  // capital network. Foreign borders sever the link even when a road survives.
  roadNetwork(playerIdx) {
    const ownCities = this.cities.filter(city => city.owner === playerIdx)
      .sort((a, b) => a.id - b.id);
    const empty = { capital: null, tiles: new Set(), cityIds: new Set(),
      connectedCities: [], disconnectedCities: ownCities, income: 0 };
    if (!ownCities.length) return empty;
    const p = this.players[playerIdx];
    const capital = ownCities.find(city => city.id === p.originalCapitalId) ||
      ownCities.find(city => city.isCapital) || ownCities[0];
    const start = this.map.idx(capital.c, capital.r);
    const tiles = new Set([start]);
    const queue = [[capital.c, capital.r]];
    while (queue.length) {
      const [c, r] = queue.shift();
      for (const [nc, nr] of HEX.neighbors(c, r)) {
        const tile = this.tile(nc, nr);
        if (!tile) continue;
        const idx = this.map.idx(nc, nr);
        if (tiles.has(idx)) continue;
        const ownCity = tile.city && tile.city.owner === playerIdx;
        const usableRoad = tile.road && (tile.owner === playerIdx || tile.owner === -1);
        if (!ownCity && !usableRoad) continue;
        tiles.add(idx);
        queue.push([nc, nr]);
      }
    }
    const connectedCities = ownCities.filter(city => tiles.has(this.map.idx(city.c, city.r)));
    const cityIds = new Set(connectedCities.map(city => city.id));
    const disconnectedCities = ownCities.filter(city => !cityIds.has(city.id));
    const income = connectedCities.reduce((sum, city) =>
      sum + (city.id === capital.id ? 0 : this.roadConnectionIncome(city)), 0);
    return { capital, tiles, cityIds, connectedCities, disconnectedCities, income };
  }

  roadConnectionIncome(city) {
    return city ? INFRASTRUCTURE.connectionBaseGold +
      Math.floor(city.pop / INFRASTRUCTURE.populationPerGold) : 0;
  }

  // Deterministic least-construction route between the capital and one city.
  // Existing roads are heavily preferred, so new corridors reuse trunk lines.
  roadConnectionPath(playerIdx, targetCity) {
    const network = this.roadNetwork(playerIdx);
    const capital = network.capital;
    if (!capital || !targetCity || targetCity.owner !== playerIdx) return null;
    const { w } = this.map;
    const key = (c, r) => r * w + c;
    const start = key(capital.c, capital.r), goal = key(targetCity.c, targetCity.r);
    if (start === goal) return [];
    const open = [[0, start]], closed = new Set();
    const came = new Map(), score = new Map([[start, 0]]);
    while (open.length) {
      let best = 0;
      for (let i = 1; i < open.length; i++) {
        if (open[i][0] < open[best][0] ||
            (open[i][0] === open[best][0] && open[i][1] < open[best][1])) best = i;
      }
      const [, current] = open.splice(best, 1)[0];
      if (closed.has(current)) continue;
      closed.add(current);
      if (current === goal) {
        const path = [];
        let cursor = goal;
        while (cursor !== start) {
          path.unshift([cursor % w, Math.floor(cursor / w)]);
          cursor = came.get(cursor);
        }
        return path;
      }
      const c = current % w, r = Math.floor(current / w);
      for (const [nc, nr] of HEX.neighbors(c, r)) {
        const tile = this.tile(nc, nr);
        if (!tile) continue;
        const ownCity = tile.city && tile.city.owner === playerIdx;
        const buildable = IMPROVEMENT.ROAD.terrains.includes(tile.terrain) &&
          (tile.owner === playerIdx || tile.owner === -1);
        if (!ownCity && !buildable) continue;
        const next = key(nc, nr);
        const step = ownCity ? 0.05 : tile.road ? 0.12 :
          1 + (TERRAIN[tile.terrain].moveCost || 1) * 0.05;
        const nextScore = score.get(current) + step;
        if (nextScore >= (score.get(next) ?? Infinity)) continue;
        score.set(next, nextScore);
        came.set(next, current);
        open.push([nextScore + HEX.distance(nc, nr, targetCity.c, targetCity.r) * 0.05, next]);
      }
      if (score.size > 5000) return null;
    }
    return null;
  }

  roadConnectionPlans(playerIdx) {
    const network = this.roadNetwork(playerIdx);
    return network.disconnectedCities.map(city => {
      const path = this.roadConnectionPath(playerIdx, city);
      if (!path) return null;
      const missing = path.map(([c, r]) => this.tile(c, r))
        .filter(tile => tile && !tile.city && !tile.road);
      return { city, path, missing };
    }).filter(Boolean).sort((a, b) => a.missing.length - b.missing.length ||
      a.path.length - b.path.length || a.city.id - b.city.id);
  }

  // ---------- workers ----------
  canBuildImprovement(unit, type) {
    if (!unit.def.worker) return false;
    const imp = IMPROVEMENT[type];
    const t = this.tile(unit.c, unit.r);
    const p = this.players[unit.owner];
    if (!imp || !t || !p.hasTech(imp.tech)) return false;
    if (t.city) return false;
    // roads may be laid in your own land or unclaimed neutral ground (to connect
    // distant cities); farms/mines still require your own territory.
    if (imp.road) { if (t.owner !== unit.owner && t.owner !== -1) return false; }
    else if (t.owner !== unit.owner) return false;
    if (!imp.terrains.includes(t.terrain)) return false;
    if (t.feature && !imp.road) return false;      // farms/mines need clear ground
    if (imp.road ? t.road : t.improvement === type) return false;
    return true;
  }

  startImprovement(unit, type, actorIdx = null) {
    if (!unit || !this.units.includes(unit) || unit.moves <= 0 || unit.building) return false;
    if (actorIdx !== null && !this.unitActorStatus(unit, actorIdx).ok) return false;
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
      // roads survive on neutral ground; other improvements need your territory
      const isRoad = IMPROVEMENT[u.building.type] && IMPROVEMENT[u.building.type].road;
      if (!t || (t.owner !== p.index && !(isRoad && t.owner === -1))) { u.building = null; continue; } // lost the tile
      u.building.turnsLeft--;
      if (u.building.turnsLeft <= 0) {
        if (isRoad) t.road = true;
        else t.improvement = u.building.type;
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
        const zocPenalty = this.knownEnemyZoneOfControl(unit, nc, nr).length ? unit.maxMoves : 0;
        const g = gScore.get(cur) + this.moveCost(unit, nc, nr) + zocPenalty;
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
      if (this.enemyZoneOfControl(unit, nc, nr).length) unit.moves = 0;
    }
    if (unit.path && !unit.path.length) unit.path = null;
    this.addMoveAnim(unit, hops);
    if (hops.length > 1) this.checkTileDiscoveries(unit);
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
        if (nd < (dist.get(nk) ?? Infinity) && this.canEnter(unit, nc, nr)) {
          dist.set(nk, nd);
          out.push([nc, nr]);
          if (!this.knownEnemyZoneOfControl(unit, nc, nr).length) frontier.push([nc, nr]);
        }
      }
    }
    return out;
  }

  // ---------- combat ----------
  flankingSupport(unit, targetTile) {
    if (!unit || !targetTile || unit.isRanged || unit.def.naval || this.isEmbarked(unit) || this.isWater(targetTile)) return [];
    return HEX.neighbors(targetTile.c, targetTile.r)
      .map(([c, r]) => this.combatUnitAt(c, r))
      .filter(support => support && support.id !== unit.id && support.owner === unit.owner &&
        !support.isCivilian && !support.isRanged && !support.def.naval && !this.isEmbarked(support))
      .sort((a, b) => a.id - b.id);
  }

  flankingBonus(unit, targetTile) {
    return Math.min(TACTICS.maxFlank,
      this.flankingSupport(unit, targetTile).length * TACTICS.flankPerSupport);
  }

  strengthOf(unit, { attacking, targetTile, ranged } = {}) {
    const p = this.players[unit.owner];
    let str = ranged ? (unit.def.rs || 0) : unit.def.cs;
    const amphibiousAttack = attacking && targetTile && this.canAttackFromEmbarked(unit, targetTile);
    if (this.isEmbarked(unit) && !amphibiousAttack) str = 2; // helpless at sea
    let mod = 1;
    const here = this.tile(unit.c, unit.r);
    // wounded units fight at 50–100%
    mod *= 0.5 + 0.5 * (unit.hp / 100);
    mod += unit.level * 0.05; // seasoning on top of chosen promotions
    if (attacking && unit.promos.includes("MIGHT")) mod += 0.15;
    if (!attacking && unit.promos.includes("BULWARK")) mod += 0.15;
    if (attacking && !ranged && targetTile) mod += this.flankingBonus(unit, targetTile);
    if (amphibiousAttack) mod -= 0.15;
    if (attacking && unit.def.naval && unit.promos.includes("BOARDING") && targetTile) {
      const foe = this.combatUnitAt(targetTile.c, targetTile.r);
      if (foe && (foe.def.naval || this.isEmbarked(foe))) mod += 0.20;
    }
    if (attacking && unit.def.naval && unit.promos.includes("BOMBARDMENT") &&
        targetTile && targetTile.city) mod += 0.20;
    if (!p.isMinor && !p.isBarb) {
      if (attacking && p.policies.has("WARRIOR_CULT")) mod += 0.10;
      if (attacking && p.policies.has("GUSLARS") && targetTile) {
        const foe = this.combatUnitAt(targetTile.c, targetTile.r);
        if ((foe && this.players[foe.owner].isBarb) || this.campAt(targetTile.c, targetTile.r)) mod += 0.25;
      }
    }
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
    if (civ.attackBonus && attacking) mod += civ.attackBonus;
    if (civ.defendCiv && !attacking) mod += civ.defendCiv;
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
    // Great General aura
    if (!unit.def.great && this.units.some(g => g.owner === unit.owner && g.def.great === "gen" &&
        HEX.distance(g.c, g.r, unit.c, unit.r) <= 2)) {
      mod += GP.generalAura;
    }
    if (unit.def.naval && (unit.unsuppliedTurns || 0) > NAVAL_SUPPLY.graceTurns &&
        !this.navalSupply(unit).supplied)
      mod *= NAVAL_SUPPLY.combatMultiplier;
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
    const t = this.tile(c, r);
    if (!t) return false;
    if (this.isEmbarked(unit) && !this.canAttackFromEmbarked(unit, t)) return false;
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
    const flankSupport = this.flankingSupport(unit, t).length;
    const flankBonus = Math.min(TACTICS.maxFlank, flankSupport * TACTICS.flankPerSupport);
    const hitsCity = !!(targetCity && (!targetUnit || !ranged));
    const defender = hitsCity ? targetCity : targetUnit;
    const report = {
      turn: this.turn,
      attackerId: unit.id,
      attackerOwner: unit.owner,
      attackerType: unit.type,
      attackerName: unit.def.name,
      attackerHpBefore: unit.hp,
      attackerHpAfter: unit.hp,
      attackerDestroyed: false,
      targetKind: hitsCity ? "city" : "unit",
      targetId: defender.id,
      targetOwner: defender.owner,
      targetType: hitsCity ? null : defender.type,
      targetName: hitsCity ? defender.name : defender.def.name,
      targetHpBefore: defender.hp,
      targetHpAfter: defender.hp,
      targetMaxHp: hitsCity ? defender.maxHp : 100,
      targetDestroyed: false,
      cityCaptured: false,
      damage: 0,
      counterDamage: 0,
      flankSupport,
      flankBonus,
      ranged,
      c, r,
      ts: Date.now(),
    };
    unit.fortified = false;
    this.addStrike(unit, c, r, ranged);

    if (hitsCity) {
      // attack the city itself (garrison protects a city only vs ranged pokes)
      const defStr = this.cityStrength(targetCity);
      const dmg = this.damageRoll(attStr, defStr);
      report.damage = dmg;
      targetCity.hp -= dmg;
      this.addEffect(c, r, "-" + dmg);
      if (!ranged) {
        const back = this.damageRoll(defStr, attStr);
        report.counterDamage = back;
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
        else {
          this.captureCity(targetCity, unit);
          report.cityCaptured = true;
        }
      }
    } else if (targetUnit) {
      const defStr = this.strengthOf(targetUnit, { attacking: false });
      const dmg = this.damageRoll(attStr, defStr);
      report.damage = dmg;
      targetUnit.hp -= dmg;
      this.addEffect(c, r, "-" + dmg);
      if (!ranged) {
        const back = this.damageRoll(defStr, attStr);
        report.counterDamage = back;
        unit.hp -= back;
        this.addEffect(unit.c, unit.r, "-" + back, "#ffaa33");
      }
      if (targetUnit.hp > 0) targetUnit.gainXp(4);
      if (unit.hp > 0) unit.gainXp((ranged ? 3 : 5) + (targetUnit.hp <= 0 ? 5 : 0));
      if (targetUnit.hp <= 0) {
        this.removeUnit(targetUnit);
        this.trackScenarioKill(unit.owner, targetUnit.owner);
        const kp = this.players[unit.owner];
        if (!kp.isBarb && !kp.isMinor) kp.gpPoints.gen += GP.killPts;
        if (!kp.isBarb && !kp.isMinor && this.policyBranchDone(unit.owner, "JUNAK")) {
          kp.gold += 8;
          this.addEffect(c, r, "+8💰", "#f1c40f");
        }
        if (this.players[targetUnit.owner].isBarb) this.questEvent("KILL_BARBS", unit.owner, {});
        if (unit.def.healOnKill) unit.hp = Math.min(100, unit.hp + unit.def.healOnKill);
        if (!ranged && unit.hp > 0 && !this.combatUnitAt(c, r) &&
            !(t.city && t.city.owner !== unit.owner) && this.unitPassable(unit, t)) {
          unit.c = c; unit.r = r; // advance into the tile
          this.updateVisibility(this.players[unit.owner]);
          this.checkTileDiscoveries(unit);
        }
      }
      if (unit.hp <= 0) this.removeUnit(unit);
    }

    report.attackerHpAfter = Math.max(0, unit.hp);
    report.attackerDestroyed = !this.units.includes(unit);
    report.targetHpAfter = report.cityCaptured ? 0 : Math.max(0, defender.hp);
    report.targetDestroyed = report.cityCaptured || (report.targetKind === "unit" && !this.units.includes(defender));
    this.lastCombat = report;

    const targetPlayer = this.players[report.targetOwner];
    if (targetPlayer && targetPlayer.isHuman && report.attackerOwner !== report.targetOwner) {
      const attackerCiv = this.players[report.attackerOwner].civ.name;
      const outcome = report.cityCaptured ? ` and captured ${report.targetName}`
        : report.targetDestroyed ? ` and destroyed ${report.targetName}` : "";
      const counter = report.counterDamage ? ` Your counterattack dealt ${report.counterDamage}.` : "";
      this.notify(`⚔️ ${attackerCiv} ${report.attackerName} dealt ${report.damage} damage${outcome}.${counter}`, report.targetOwner);
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
    city.queue = [];
    city.prodStored = 0;
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
    if (!p.alive || p.isBarb) return;
    const hasCities = this.cities.some(c => c.owner === playerIdx);
    const hasSettlers = this.units.some(u => u.owner === playerIdx && u.type === "SETTLER");
    if (!hasCities && !hasSettlers) {
      p.alive = false;
      this.units = this.units.filter(u => u.owner !== playerIdx);
      this.retirePlayerState(playerIdx);
      this.notify(p.isMinor ? `The city-state of ${p.civ.name} has been destroyed!`
                            : `${p.civ.name} has been destroyed!`, -1);
      this.checkVictory();
    }
  }

  retirePlayerState(playerIdx) {
    const retired = this.players[playerIdx];
    for (const p of this.players) {
      p.atWarWith.delete(playerIdx);
      p.pacts.delete(playerIdx);
      p.deals = p.deals.filter(d => d.other !== playerIdx);
      delete p.warWeariness[playerIdx];
      delete p.attitude[playerIdx];
      delete p.influence[playerIdx];
    }
    retired.atWarWith.clear();
    retired.pacts.clear();
    retired.deals = [];
    retired.warWeariness = {};
    retired.attitude = {};
    retired.influence = {};
    for (const tile of this.map.tiles) {
      if (tile.owner !== playerIdx) continue;
      tile.owner = -1;
      tile.workedBy = null;
    }
    this.routes = this.routes.filter(r => r.owner !== playerIdx);
    this.peaceOffers = this.peaceOffers.filter(o => o.from !== playerIdx && o.to !== playerIdx);
    this.dirtyHappiness();
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
  citySiteStatus(c, r, owner) {
    const t = this.tile(c, r);
    if (!t) return { ok: false, code: "OFF_MAP", reason: "Outside the map." };
    if (!TERRAIN[t.terrain].passable)
      return { ok: false, code: "IMPASSABLE", reason: "Cities require passable land." };
    if (t.city)
      return { ok: false, code: "OCCUPIED", reason: `${t.city.name} already occupies this tile.` };
    const claimant = this.players[owner];
    if (!claimant || !claimant.alive)
      return { ok: false, code: "INVALID_OWNER", reason: "No civilization can claim this site." };
    if (t.owner !== -1 && t.owner !== owner) {
      const foreign = this.players[t.owner];
      if (!foreign || foreign.alive)
        return { ok: false, code: "FOREIGN_TERRITORY",
          reason: `${foreign ? foreign.civ.name : "Another civilization"} controls this territory.` };
    }
    const nearby = this.cities.find(city => HEX.distance(c, r, city.c, city.r) <= 2);
    if (nearby)
      return { ok: false, code: "TOO_CLOSE", blockingCityId: nearby.id,
        reason: `Too close to ${nearby.name}; city centres must be at least three hexes apart.` };
    return { ok: true, code: "OK", reason: "A city can be founded here." };
  }

  foundCity(settler, actorIdx = null) {
    if (!settler || settler.type !== "SETTLER" || !this.units.includes(settler) || settler.moves <= 0)
      return null;
    if (actorIdx !== null && !this.unitActorStatus(settler, actorIdx).ok) return null;
    const status = this.citySiteStatus(settler.c, settler.r, settler.owner);
    if (!status.ok) return null;
    const t = this.tile(settler.c, settler.r);
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
    this.addBurst(city.c, city.r, CIVS[p.civId].color);
    return city;
  }

  cityWorkableTiles(city) {
    const out = [];
    for (const [c, r] of HEX.ring(city.c, city.r, 3)) {
      const t = this.tile(c, r);
      if (t && t.owner === city.owner && !t.city && !(t.c === city.c && t.r === city.r)) out.push(t);
    }
    return out;
  }

  assignWorkedTiles(owner) {
    const cities = this.cities.filter(c => c.owner === owner).sort((a, b) => a.id - b.id);
    const cityIds = new Set(cities.map(c => c.id));
    for (const t of this.map.tiles) {
      if (t.owner === owner || cityIds.has(t.workedBy)) t.workedBy = null;
    }
    const choices = new Map();
    for (const city of cities) {
      const focus = CITY_FOCUS[city.focus] || CITY_FOCUS.balanced;
      const ranked = this.cityWorkableTiles(city).map(t => {
        const y = this.tileYield(t);
        return { t, score: y.food * focus.food + y.prod * focus.prod + y.gold * focus.gold };
      }).sort((a, b) => b.score - a.score ||
        HEX.distance(city.c, city.r, a.t.c, a.t.r) - HEX.distance(city.c, city.r, b.t.c, b.t.r) ||
        a.t.r - b.t.r || a.t.c - b.t.c);
      choices.set(city.id, ranked.map(x => x.t));
    }
    const maxPop = cities.reduce((m, c) => Math.max(m, c.pop), 0);
    for (let slot = 0; slot < maxPop; slot++) {
      for (const city of cities) {
        if (slot >= city.pop) continue;
        const tile = choices.get(city.id).find(t => t.workedBy === null);
        if (tile) tile.workedBy = city.id;
      }
    }
  }

  workedTiles(city) {
    this.assignWorkedTiles(city.owner);
    return this.map.tiles.filter(t => t.workedBy === city.id);
  }

  setCityFocus(city, focus, actorIdx) {
    if (!city || city.owner !== actorIdx || !CITY_FOCUS[focus] || !this.cities.includes(city)) return false;
    city.focus = focus;
    this.assignWorkedTiles(city.owner);
    return true;
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
    if (t.river) gold += RIVERS.tileGold;
    return { food, prod, gold };
  }

  cityYields(city) {
    const p = this.players[city.owner];
    const civ = p.civ;
    // centre tile minimum yield
    const centre = this.tileYield(this.tile(city.c, city.r));
    let food = Math.max(2, centre.food), prod = Math.max(2, centre.prod), gold = Math.max(1, centre.gold);
    if (this.tile(city.c, city.r).river) food += RIVERS.cityFood;
    for (const t of this.workedTiles(city)) {
      const y = this.tileYield(t);
      food += y.food; prod += y.prod; gold += y.gold;
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
    // social policies
    if (!p.isMinor && !p.isBarb) {
      if (p.policies.has("HARVEST")) food += 1;
      if (p.policies.has("ICONS")) faith += 1;
      if (p.policies.has("FRESCOES")) culture += 2;
      if (city.isCapital) {
        if (p.policies.has("HEARTH")) food += 2;
        if (p.policies.has("BAZAAR")) gold = Math.floor(gold * 1.25);
      }
    }
    // civ traits
    if (civ.cityScience) sci += civ.cityScience;
    if (civ.cityCulture) culture += civ.cityCulture;
    if (civ.cityGold) gold += civ.cityGold;
    if (civ.cityFaith) faith += civ.cityFaith;
    if (civ.cityProd) prod += civ.cityProd;
    if (civ.cityFood) food += civ.cityFood;
    if (civ.capitalGold && city.isCapital) gold += civ.capitalGold;
    if (civ.coastalGold && city.coastal) gold += civ.coastalGold;
    if (civ.coastalFood && city.coastal) food += civ.coastalFood;
    if (civ.cultureBonus) culture *= (1 + civ.cultureBonus);
    if (!p.isHuman && !p.isMinor) {
      const mult = { easy: 0.75, normal: 1, hard: 1.3 }[this.difficulty] || 1;
      prod = Math.floor(prod * mult); gold = Math.floor(gold * mult);
      sci = sci * mult;
    }
    if (this.cityBlockade(city).active) gold = Math.floor(gold * BLOCKADE.cityGoldMultiplier);
    return { food, prod, gold, sci: Math.floor(sci), culture, faith };
  }

  cityFoodSurplus(city, yields = null) {
    const p = this.players[city.owner];
    const y = yields || this.cityYields(city);
    let surplus = y.food - city.pop * 2;
    if (!p.isMinor && surplus > 0) {
      const happiness = this.happinessOf(p.index);
      if (happiness < HAPPINESS.strikeAt) surplus = 0;
      else if (happiness < 0) surplus = Math.floor(surplus / 2);
    }
    return surplus;
  }

  cityProductionRate(city, item = null, yields = null) {
    const p = this.players[city.owner];
    const y = yields || this.cityYields(city);
    let prod = y.prod;
    const current = item || city.producing;
    if (current && current.kind === "building" && p.civ.buildingProdBonus)
      prod = Math.floor(prod * (1 + p.civ.buildingProdBonus));
    if (current && current.kind === "unit" && p.civ.unitProdBonus)
      prod = Math.floor(prod * (1 + p.civ.unitProdBonus));
    if (p.goldenAgeTurns > 0) prod = Math.floor(prod * (1 + GOLDEN_AGE.bonus));
    return prod;
  }

  productionStatus(city, item) {
    if (!city || !this.cities.includes(city) || !item)
      return { ok: false, code: "INVALID_CITY" };
    const p = this.players[city.owner];
    if (!p || !p.alive) return { ok: false, code: "INVALID_OWNER" };
    if (item.kind === "unit") {
      const u = UNITS[item.key];
      if (!u) return { ok: false, code: "UNKNOWN_ITEM" };
      if (u.faithCost || u.great) return { ok: false, code: "NOT_PRODUCIBLE" };
      if (u.uu && u.uu !== p.civId) return { ok: false, code: "WRONG_CIV" };
      if (u.replaces && p.civId !== u.uu) return { ok: false, code: "WRONG_CIV" };
      if (Object.entries(UNITS).some(([, v]) => v.uu === p.civId && v.replaces === item.key))
        return { ok: false, code: "REPLACED_UNIT" };
      if (u.tech && !p.hasTech(u.tech)) return { ok: false, code: "MISSING_TECH" };
      if (u.needs && !this.playerHasResource(p.index, u.needs))
        return { ok: false, code: "MISSING_RESOURCE" };
      if (u.naval && !city.coastal) return { ok: false, code: "INLAND_CITY" };
      return { ok: true, code: "OK", def: u };
    }
    if (item.kind !== "building") return { ok: false, code: "UNKNOWN_KIND" };
    const b = BUILDINGS[item.key];
    if (!b) return { ok: false, code: "UNKNOWN_ITEM" };
    if (city.buildings.includes(item.key)) return { ok: false, code: "ALREADY_BUILT" };
    if (b.tech && !p.hasTech(b.tech)) return { ok: false, code: "MISSING_TECH" };
    if (b.requires && !city.buildings.includes(b.requires)) return { ok: false, code: "MISSING_BUILDING" };
    if (b.wonder) {
      if (p.isMinor) return { ok: false, code: "MINOR_WONDER" };
      if (this.cities.some(c => c.buildings.includes(item.key)))
        return { ok: false, code: "WONDER_BUILT" };
      const reservedElsewhere = this.cities.some(c => c.owner === city.owner && c !== city &&
        ((c.producing && c.producing.key === item.key) || c.queue.some(q => q.key === item.key)));
      if (reservedElsewhere) return { ok: false, code: "WONDER_RESERVED" };
    }
    return { ok: true, code: "OK", def: b };
  }

  // Drop queue entries that became invalid (e.g. a wonder completed elsewhere).
  validQueueItem(city, item) { return this.productionStatus(city, item).ok; }

  productionOptions(city) {
    const opts = [];
    for (const [key, u] of Object.entries(UNITS)) {
      if (!this.productionStatus(city, { kind: "unit", key }).ok) continue;
      opts.push({ kind: "unit", key, cost: u.cost, name: u.name, icon: u.icon, naval: u.naval });
    }
    for (const [key, b] of Object.entries(BUILDINGS)) {
      if (!this.productionStatus(city, { kind: "building", key }).ok) continue;
      opts.push({ kind: "building", key, cost: b.cost, name: b.name, icon: b.icon, wonder: b.wonder });
    }
    return opts;
  }

  playerHasResource(playerIdx, res) {
    return this.map.tiles.some(t => t.owner === playerIdx && t.resource === res);
  }

  buyCost(cost, ownerIdx) {
    let price = cost * 3;
    if (ownerIdx !== undefined && this.players[ownerIdx].policies.has("MINTERS")) price = Math.floor(price * 0.85);
    return price;
  }

  setCityProduction(city, item, queue, actorIdx) {
    if (!city || city.owner !== actorIdx || !this.productionStatus(city, item).ok) return false;
    const normalized = { kind: item.kind, key: item.key };
    if (queue && city.producing) {
      if (city.queue.length >= 6 || city.producing.key === item.key || city.queue.some(q => q.key === item.key))
        return false;
      city.queue.push(normalized);
      return true;
    }
    if (city.producing && city.producing.kind === item.kind && city.producing.key === item.key) return true;
    city.queue = city.queue.filter(q => q.kind !== item.kind || q.key !== item.key);
    city.producing = normalized;
    return true;
  }

  advanceCityQueue(city) {
    do {
      city.producing = city.queue.length ? city.queue.shift() : null;
    } while (city.producing && !this.validQueueItem(city, city.producing));
    return city.producing;
  }

  cancelCityProduction(city, actorIdx) {
    if (!city || city.owner !== actorIdx || !this.cities.includes(city)) return false;
    this.advanceCityQueue(city);
    if (!city.producing) city.prodStored = 0;
    return true;
  }

  removeQueuedProduction(city, index, actorIdx) {
    if (!city || city.owner !== actorIdx || !Number.isInteger(index) || index < 0 || index >= city.queue.length)
      return false;
    city.queue.splice(index, 1);
    return true;
  }

  productionUnitSpot(city, unitKey) {
    const def = UNITS[unitKey];
    if (!def) return null;
    const open = (c, r) => {
      const t = this.tile(c, r);
      if (!t) return false;
      if (this.unitsAt(c, r).some(u => u.owner !== city.owner)) return false;
      if (def.naval) {
        if (!this.isWater(t) || (def.coastOnly && t.terrain !== "COAST")) return false;
        return !this.combatUnitAt(c, r);
      }
      if (!TERRAIN[t.terrain].passable) return false;
      return def.civilian ? !this.civilianAt(c, r) : !this.combatUnitAt(c, r);
    };
    if (!def.naval && open(city.c, city.r)) return [city.c, city.r];
    for (const [c, r] of HEX.neighbors(city.c, city.r)) if (open(c, r)) return [c, r];
    return null;
  }

  purchase(city, item, buyerIdx) {
    if (!city || city.owner !== buyerIdx) return false;
    const status = this.productionStatus(city, item);
    if (!status.ok) return false;
    const spot = item.kind === "unit" ? this.productionUnitSpot(city, item.key) : null;
    if (item.kind === "unit" && !spot) return false;
    const p = this.players[city.owner];
    const price = this.buyCost(status.def.cost, city.owner);
    if (p.gold < price || !this.completeProduction(city, item, spot)) return false;
    p.gold -= price;
    if (item.kind === "building") {
      city.queue = city.queue.filter(q => q.kind !== item.kind || q.key !== item.key);
      if (city.producing && city.producing.kind === item.kind && city.producing.key === item.key) {
        city.prodStored = 0;
        this.advanceCityQueue(city);
      }
    }
    return true;
  }

  completeProduction(city, item, unitSpot = null) {
    if (item.kind === "unit") {
      const spot = unitSpot || this.productionUnitSpot(city, item.key);
      if (!spot) return false;
      this.addUnit(item.key, city.owner, spot[0], spot[1]);
    } else {
      if (!BUILDINGS[item.key] || city.buildings.includes(item.key)) return false;
      if (BUILDINGS[item.key].wonder && this.cities.some(c => c.buildings.includes(item.key))) return false;
      city.buildings.push(item.key);
      this.dirtyHappiness();
      if (BUILDINGS[item.key].cityHp) city.hp += BUILDINGS[item.key].cityHp;
      if (BUILDINGS[item.key].wonder) {
        this.notify(`${BUILDINGS[item.key].name} has been completed in ${city.name}!`, -1);
      }
    }
    return true;
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
      if (pa.isBarb || pb.isBarb) return; // no first-contact fanfare for raiders
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
    this.changeAttitude(a, b, -40); this.changeAttitude(b, a, -40);
    // war dissolves any pact between the two, and cancels their deals
    pa.pacts.delete(b); pb.pacts.delete(a);
    pa.deals = pa.deals.filter(d => d.other !== b);
    pb.deals = pb.deals.filter(d => d.other !== a);
    // the victim's defensive-pact partners join the war
    for (const q of this.players) {
      if (!q.alive || q.isMinor || q.isBarb) continue;
      if (q.index !== a && q.index !== b && q.pacts.has(b) && !q.atWarWith.has(a)) {
        this.notify(`🤝 ${q.civ.name} honours its defensive pact with ${pb.civ.name}!`, -1);
        this.declareWar(q.index, a);
      }
    }
  }

  makePeace(a, b) {
    const pa = this.players[a], pb = this.players[b];
    if (pa.isBarb || pb.isBarb) return; // no peace with the horde
    if (!pa.atWarWith.has(b)) return;
    pa.atWarWith.delete(b); pb.atWarWith.delete(a);
    delete pa.warWeariness[b]; delete pb.warWeariness[a];
    this.peaceOffers = this.peaceOffers.filter(o =>
      !((o.from === a && o.to === b) || (o.from === b && o.to === a)));
    this.notify(`☮️ Peace between ${pa.civ.name} and ${pb.civ.name}.`, -1);
    this.changeAttitude(a, b, 10); this.changeAttitude(b, a, 10);
  }

  // An AI proposes peace to a human. It doesn't take effect until the player
  // accepts, so a war can never end without the human's say-so.
  offerPeace(from, to) {
    const pf = this.players[from], pt = this.players[to];
    if (!pf || !pt || pf.isBarb || pt.isBarb || !pf.atWarWith.has(to)) return;
    if (this.peaceOffers.some(o => o.from === from && o.to === to)) return;
    this.peaceOffers.push({ from, to });
    this.notify(`☮️ ${pf.civ.name} proposes peace.`, to);
  }
  pendingPeaceOffers(to) {
    return this.peaceOffers.filter(o => o.to === to &&
      this.players[o.from].alive && this.players[o.from].atWarWith.has(to));
  }
  acceptPeaceOffer(to, from) {
    if (!this.peaceOffers.some(o => o.from === from && o.to === to)) return false;
    this.makePeace(from, to); // also prunes the offer
    return true;
  }
  declinePeaceOffer(to, from) {
    this.peaceOffers = this.peaceOffers.filter(o => !(o.from === from && o.to === to));
    // spurning peace sours them a little
    this.changeAttitude(from, to, -4);
  }

  // ---------- attitude, deals & pacts ----------
  attitudeOf(a, b) { return Math.round(this.players[a].attitude[b] || 0); }

  changeAttitude(a, b, delta) {
    const p = this.players[a];
    if (p.isMinor || p.isBarb) return;
    p.attitude[b] = Math.max(-100, Math.min(100, (p.attitude[b] || 0) + delta));
  }

  attitudeLabel(a, b) {
    const v = this.attitudeOf(a, b);
    return v >= 40 ? "Friendly" : v >= 10 ? "Warm" : v > -10 ? "Neutral" : v > -40 ? "Wary" : "Hostile";
  }

  // luxury types a has that b lacks (counting imports)
  tradableLuxes(a, b) {
    const pb = this.players[b];
    const theirs = new Set(this.luxuryTypesOf(b));
    for (const d of pb.deals) if (d.ends > this.turn) theirs.add(d.get);
    return this.luxuryTypesOf(a).filter(l => !theirs.has(l));
  }

  activeDealBetween(a, b) {
    return this.players[a].deals.some(d => d.other === b && d.ends > this.turn);
  }

  canLuxuryDeal(a, b) {
    const pa = this.players[a], pb = this.players[b];
    if (pa.isMinor || pb.isMinor || pa.isBarb || pb.isBarb) return false;
    if (!pa.alive || !pb.alive || pa.atWarWith.has(b) || !pa.met.has(b)) return false;
    if (this.activeDealBetween(a, b)) return false;
    return this.tradableLuxes(a, b).length > 0 && this.tradableLuxes(b, a).length > 0;
  }

  makeLuxuryDeal(a, b) {
    if (!this.canLuxuryDeal(a, b)) return false;
    const give = this.tradableLuxes(a, b)[0], get = this.tradableLuxes(b, a)[0];
    const ends = this.turn + DIPLO.luxuryDealTurns;
    this.players[a].deals.push({ give, get, other: b, ends });
    this.players[b].deals.push({ give: get, get: give, other: a, ends });
    this.changeAttitude(a, b, 10); this.changeAttitude(b, a, 10);
    this.dirtyHappiness();
    this.notify(`🤝 ${this.players[a].civ.name} and ${this.players[b].civ.name} trade ` +
      `${RESOURCE[give].name} for ${RESOURCE[get].name} (${DIPLO.luxuryDealTurns} turns).`, -1);
    return true;
  }

  giftGold(a, b) {
    const pa = this.players[a];
    if (pa.gold < DIPLO.giftGold || pa.atWarWith.has(b)) return false;
    pa.gold -= DIPLO.giftGold;
    this.players[b].gold += DIPLO.giftGold;
    this.changeAttitude(b, a, DIPLO.giftAttitude);
    this.notify(`🎁 ${pa.civ.name} sends ${DIPLO.giftGold} gold to ${this.players[b].civ.name}.`, -1);
    return true;
  }

  canPact(a, b) {
    const pa = this.players[a], pb = this.players[b];
    if (pa.isMinor || pb.isMinor || pa.isBarb || pb.isBarb) return false;
    if (!pa.alive || !pb.alive || pa.atWarWith.has(b) || !pa.met.has(b)) return false;
    if (pa.pacts.has(b)) return false;
    return this.attitudeOf(a, b) >= DIPLO.pactThreshold && this.attitudeOf(b, a) >= DIPLO.pactThreshold;
  }

  makePact(a, b) {
    if (!this.canPact(a, b)) return false;
    this.players[a].pacts.add(b);
    this.players[b].pacts.add(a);
    this.changeAttitude(a, b, 15); this.changeAttitude(b, a, 15);
    this.notify(`🛡️ Defensive pact: ${this.players[a].civ.name} and ${this.players[b].civ.name}!`, -1);
    return true;
  }

  processDiplomacy() {
    for (const p of this.players) {
      if (p.isMinor || p.isBarb || !p.alive) continue;
      for (const k of Object.keys(p.attitude)) {
        const v = p.attitude[k];
        p.attitude[k] = Math.abs(v) <= DIPLO.attitudeDecay ? 0
          : v - Math.sign(v) * DIPLO.attitudeDecay;
      }
      const before = p.deals.length;
      p.deals = p.deals.filter(d => d.ends > this.turn);
      if (p.deals.length < before) this.dirtyHappiness();
    }
  }

  // ---------- social policies ----------
  policyBranchOf(key) {
    return Object.keys(POLICY_BRANCHES).find(b => POLICY_BRANCHES[b].policies[key]) || null;
  }

  policyBranchDone(idx, branch) {
    const p = this.players[idx];
    if (!p || p.isMinor || p.isBarb) return false;
    return Object.keys(POLICY_BRANCHES[branch].policies).every(k => p.policies.has(k));
  }

  branchesDone(idx) {
    return Object.keys(POLICY_BRANCHES).filter(b => this.policyBranchDone(idx, b)).length;
  }

  nextPolicyCost(idx) { return POLICY_COST(this.players[idx].policies.size); }

  canAdoptPolicy(idx) {
    const p = this.players[idx];
    const total = Object.values(POLICY_BRANCHES).reduce((a, b) => a + Object.keys(b.policies).length, 0);
    return !p.isMinor && !p.isBarb && p.alive && p.policies.size < total &&
      p.culture >= this.nextPolicyCost(idx);
  }

  adoptPolicy(idx, key) {
    const p = this.players[idx];
    const branch = this.policyBranchOf(key);
    if (!branch || p.policies.has(key) || !this.canAdoptPolicy(idx)) return false;
    p.culture -= this.nextPolicyCost(idx);
    p.policies.add(key);
    p._couldAdopt = this.canAdoptPolicy(idx);
    this.notify(`📜 ${p.civ.name} adopts ${POLICY_BRANCHES[branch].policies[key].name}.`, idx);
    if (this.policyBranchDone(idx, branch)) {
      this.notify(`📜 ${p.civ.name} completes the ${POLICY_BRANCHES[branch].name} branch! (${POLICY_BRANCHES[branch].finisher})`, -1);
      if (branch === "ZADRUGA") {
        for (const c of this.cities) if (c.owner === idx) c.pop++;
      }
    }
    this.dirtyHappiness();
    this.checkVictory();
    return true;
  }

  // ---------- city-state quests ----------
  processQuests() {
    for (const m of this.players) {
      if (!m.isMinor || !m.alive) continue;
      if (m.quest && m.quest.expires <= this.turn) m.quest = null;
      if (!m.quest && (this.turn + m.index * 7) % QUESTS.everyTurns === 0) {
        m.quest = this.rollQuest(m);
        if (m.quest) {
          this.notify(`🏛️ ${m.civ.name} asks: ${this.questText(m.quest)} (+${QUESTS.reward} influence)`, -1);
        }
      }
    }
  }

  rollQuest(m) {
    const expires = this.turn + QUESTS.duration;
    const mCity = this.cities.find(c => c.owner === m.index);
    if (this.camps.length && mCity && this.rng() < 0.45) {
      const camp = [...this.camps].sort((x, y) =>
        HEX.distance(x.c, x.r, mCity.c, mCity.r) - HEX.distance(y.c, y.r, mCity.c, mCity.r))[0];
      return { type: "CLEAR_CAMP", c: camp.c, r: camp.r, expires };
    }
    if (!this.noBarbs && this.rng() < 0.5) {
      return { type: "KILL_BARBS", progress: {}, expires };
    }
    const majors = this.players.filter(p => !p.isMinor && !p.isBarb && p.alive);
    const candidates = Object.keys(TECHS).filter(t =>
      majors.filter(p => !p.techs.has(t)).length >= 2 &&
      majors.some(p => p.availableTechs().includes(t)));
    if (candidates.length) {
      const tech = candidates.sort((a, b) => TECHS[a].cost - TECHS[b].cost)[0];
      return { type: "FIRST_TECH", tech, expires };
    }
    return !this.noBarbs ? { type: "KILL_BARBS", progress: {}, expires } : null;
  }

  questText(q) {
    if (q.type === "CLEAR_CAMP") return `burn the barbarian camp at (${q.c}, ${q.r})`;
    if (q.type === "KILL_BARBS") return `slay ${QUESTS.killCount} barbarians`;
    return `be first to research ${TECHS[q.tech].name}`;
  }

  // called from gameplay hooks; the first major to finish claims the reward
  questEvent(type, playerIdx, data) {
    const p = this.players[playerIdx];
    if (!p || p.isMinor || p.isBarb) return;
    for (const m of this.players) {
      if (!m.isMinor || !m.alive || !m.quest || m.quest.type !== type) continue;
      const q = m.quest;
      let done = false;
      if (type === "CLEAR_CAMP") done = q.c === data.c && q.r === data.r;
      else if (type === "KILL_BARBS") {
        q.progress[playerIdx] = (q.progress[playerIdx] || 0) + 1;
        done = q.progress[playerIdx] >= QUESTS.killCount;
      } else if (type === "FIRST_TECH") done = q.tech === data.tech;
      if (done) {
        p.influence[m.index] = (p.influence[m.index] || 0) + QUESTS.reward;
        m.quest = null;
        if (!this.stats) this.stats = { steals: 0, catches: 0 };
        this.stats.questsDone = (this.stats.questsDone || 0) + 1;
        this.notify(`🏛️ ${m.civ.name} is grateful to ${p.civ.name}! (+${QUESTS.reward} influence)`, -1);
      }
    }
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

  missionaryCost(ownerIdx) {
    const mul = this.players[ownerIdx].policies.has("SYNOD") ? 0.75 : 1;
    return Math.floor(UNITS.MISSIONARY.faithCost * mul);
  }

  buyMissionary(city) {
    const p = this.players[city.owner];
    if (p.religionId === null || p.faith < this.missionaryCost(city.owner)) return false;
    const spot = this.civilianAt(city.c, city.r) ? this.freeAdjacent(city.c, city.r) : [city.c, city.r];
    if (!spot) return false;
    p.faith -= this.missionaryCost(city.owner);
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

  spreadFromMissionary(unit, actorIdx = null) {
    if (!unit || !this.units.includes(unit) || !unit.def.missionary || unit.moves <= 0) return false;
    if (actorIdx !== null && !this.unitActorStatus(unit, actorIdx).ok) return false;
    const p = this.players[unit.owner];
    if (p.religionId === null || unit.charges <= 0) return false;
    const city = this.missionaryTarget(unit);
    if (!city) return false;
    city.pressure[p.religionId] = (city.pressure[p.religionId] || 0) + MISSIONARY_PRESSURE;
    this.updateCityReligion(city);
    p.missionarySpreads++;
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
    if (p.isMinor || p.isBarb || !p.alive) return 0;
    if (!this._hap) this._hap = {};
    if (this._hap[idx] !== undefined) return this._hap[idx];
    let hap = HAPPINESS.base;
    const lux = new Set(this.luxuryTypesOf(idx));
    for (const d of p.deals) if (d.ends > this.turn) lux.add(d.get);
    hap += lux.size * HAPPINESS.perLuxury;
    if (p.policies.has("ELDERS")) hap += 2;
    if (p.policies.has("PILGRIMS")) hap += 2;
    if (p.moodTurns > 0) hap += p.moodDelta;
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
      if (p.isMinor || p.isBarb || !p.alive) continue;
      // recruit up to the entitled number of spies
      if (p.isBarb) continue;
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
    if (!p.alive || p.isBarb) return 0;
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
    const surplus = this.cityFoodSurplus(city, y);
    city.food += surplus;
    if (city.food >= city.foodNeeded()) { city.food -= city.foodNeeded(); city.pop++; this.notify(`${city.name} grew to ${city.pop}.`, city.owner); }
    else if (city.food < 0) { city.food = 0; if (city.pop > 1) { city.pop--; this.notify(`${city.name} is starving!`, city.owner); } }

    // production
    // defensively drop a production item whose key no longer resolves (a
    // corrupted save, a removed def) so a bad entry can never crash a turn
    if (city.producing) {
      const it = city.producing;
      const def = it.kind === "unit" ? UNITS[it.key] : BUILDINGS[it.key];
      if (!def) { city.producing = null; }
    }
    if (city.producing) {
      const item = city.producing;
      const prod = this.cityProductionRate(city, item, y);
      city.prodStored += prod;
      const cost = item.kind === "unit" ? UNITS[item.key].cost : BUILDINGS[item.key].cost;
      if (city.prodStored >= cost) {
        let resolved = true;
        // wonder race check
        if (item.kind === "building" && BUILDINGS[item.key].wonder &&
            this.cities.some(c => c.buildings.includes(item.key))) {
          city.prodStored = Math.floor(city.prodStored * 0.5);
          this.notify(`${BUILDINGS[item.key].name} was completed elsewhere first!`, city.owner);
        } else {
          const complete = this.completeProduction(city, item);
          if (complete) {
            city.prodStored -= cost;
            this.notify(`${city.name} finished ${item.kind === "unit" ? UNITS[item.key].name : BUILDINGS[item.key].name}.`, city.owner);
          } else {
            city.prodStored = cost;
            resolved = false;
          }
        }
        if (resolved) {
          this.advanceCityQueue(city);
        }
      }
    }

    // border growth
    city.cultureStored += y.culture;
    const growCost = Math.floor(city.borderCost() *
      (this.players[city.owner].policies.has("HOMESTEAD") ? 0.75 : 1));
    if (city.cultureStored >= growCost) {
      city.cultureStored -= growCost;
      const target = this.bestBorderTile(city);
      if (target) { target.owner = city.owner; city.expansions++; }
    }

    // A fleet that controls the port prevents supplies and repairs from arriving.
    if (city.hp < city.maxHp && (!BLOCKADE.preventsRepair || !this.cityBlockade(city).active)) {
      city.hp = Math.min(city.maxHp, city.hp + 15);
    }

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

  // One authoritative forecast for the economy UI and end-of-turn accounting.
  // A turn may pass already-resolved city yields so growth and production are
  // processed only once while every gold modifier still uses the same rules.
  empireEconomy(playerIdx, yieldsByCity = null) {
    const p = this.players[playerIdx];
    if (!p || p.isBarb) return null;
    const out = {
      cities: 0, population: 0, units: 0, freeUnits: 0,
      food: 0, production: 0, science: 0, culture: 0, faith: 0,
      cityGold: 0, goldenAgeGold: 0, connectionGold: 0, tradeGold: 0, guildGold: 0,
      carsijaGold: 0, cityStateGold: 0, titheGold: 0,
      connectedCities: 0, connectableCities: 0,
      maintenance: 0, grossGold: 0, netGold: 0,
    };
    for (const city of this.cities) {
      if (city.owner !== playerIdx) continue;
      const supplied = yieldsByCity instanceof Map ? yieldsByCity.get(city.id) : null;
      const y = supplied || this.cityYields(city);
      out.cities++;
      out.population += city.pop;
      out.food += y.food;
      out.production += y.prod;
      out.cityGold += y.gold;
      out.science += y.sci;
      out.culture += y.culture || 0;
      out.faith += y.faith;
    }
    if (p.goldenAgeTurns > 0 && out.cityGold > 0) {
      out.goldenAgeGold = Math.floor(out.cityGold * (1 + GOLDEN_AGE.bonus)) - out.cityGold;
    }
    out.units = this.units.filter(u => u.owner === playerIdx).length;
    out.freeUnits = 4 + (p.policies.has("FRONTIERSMEN") ? 4 : 0);
    out.maintenance = Math.max(0, out.units - out.freeUnits);
    const roadNetwork = this.roadNetwork(playerIdx);
    out.connectionGold = roadNetwork.income;
    out.connectedCities = Math.max(0, roadNetwork.connectedCities.length - (roadNetwork.capital ? 1 : 0));
    out.connectableCities = Math.max(0, out.cities - (roadNetwork.capital ? 1 : 0));
    if (!p.isMinor) {
      out.tradeGold = this.tradeIncome(playerIdx);
      if (p.policies.has("GUILDS")) out.guildGold = this.luxuryTypesOf(playerIdx).length;
      if (this.policyBranchDone(playerIdx, "CARSIJA")) out.carsijaGold = 2 * out.cities;
      out.cityStateGold = this.minorBonuses(playerIdx).gold;
      const religion = p.religionId !== null ? this.religions[p.religionId] : null;
      if (religion && religion.belief === "TITHE") {
        out.titheGold = this.religionFollowers(p.religionId);
      }
    }
    out.grossGold = out.cityGold + out.goldenAgeGold + out.connectionGold + out.tradeGold + out.guildGold +
      out.carsijaGold + out.cityStateGold + out.titheGold;
    out.netGold = out.grossGold - out.maintenance;
    return out;
  }

  processPlayerEconomy(p) {
    if (!p.alive || p.isBarb) return;
    this.dirtyHappiness(); // borders/pop may have changed since last compute
    const yieldsByCity = new Map();
    for (const city of this.cities) {
      if (city.owner !== p.index) continue;
      const y = this.processCityTurn(city);
      yieldsByCity.set(city.id, y);
    }
    const economy = this.empireEconomy(p.index, yieldsByCity);
    if (!p.isMinor) {
      p.culture += economy.culture;
      p._cpt = economy.culture;
      const can = this.canAdoptPolicy(p.index);
      if (can && !p._couldAdopt && p.isHuman) {
        this.notify(`📜 Enough culture for a social policy — open the Policies screen!`, p.index);
      }
      p._couldAdopt = can;
    }
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
      this.accrueGreatPeople(p);
      p.faith += economy.faith;
    }
    p.gold += economy.netGold;
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
      p.scienceStored += economy.science;
      const t = TECHS[p.researching];
      if (p.scienceStored >= this.techCost(p.researching)) {
        const done = p.researching;
        p.scienceStored -= this.techCost(done);
        p.techs.add(done);
        this.notify(`🔬 Research complete: ${t.name}!`, p.index);
        p.researching = null;
        this.questEvent("FIRST_TECH", p.index, { tech: done });
      }
    } else if (p.isHuman) {
      p.scienceStored += economy.science; // banks until a tech is chosen
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
      this.addStrike(null, target.c, target.r, true);
      this.addEffect(target.c, target.r, "-" + dmg, "#66ccff");
      if (target.hp <= 0) {
        this.removeUnit(target);
        this.trackScenarioKill(city.owner, target.owner);
        this.notify(`Your ${target.def.name} fell to ${city.name}'s defenses!`, target.owner);
      }
    }
  }

  healUnits(p) {
    for (const u of this.units) {
      if (u.owner !== p.index || u.hp >= 100) continue;
      const t = this.tile(u.c, u.r);
      const moved = u.moves < u.maxMoves || u.attacked;
      if (moved) continue;
      if (u.def.naval && !this.navalSupply(u).supplied) continue;
      let heal = 5;
      if (this.isWater(t)) heal = u.def.naval && t.owner === p.index ? 10 : 0; // ships mend in home waters
      else if (t.owner === p.index) heal = 10;
      if (t.city && t.city.owner === p.index) heal = 20;
      if (t.owner !== -1 && this.players[p.index].atWarWith.has(t.owner)) heal = 0;
      if (heal > 0) {
        if (this.players[p.index].policies.has("BROTHERHOOD")) heal += 5;
        if (u.promos.includes("MEDIC")) heal += 5;
        else if (this.units.some(m => m !== u && m.owner === u.owner && m.promos.includes("MEDIC") &&
          HEX.distance(m.c, m.r, u.c, u.r) <= 1)) heal += 3;
      }
      u.hp = Math.min(100, u.hp + heal);
    }
  }

  processNavalSupply(p) {
    for (const u of [...this.units]) {
      if (u.owner !== p.index || !u.def.naval) continue;
      const state = this.navalSupply(u);
      if (state.supplied) {
        u.unsuppliedTurns = 0;
        continue;
      }
      u.unsuppliedTurns = (u.unsuppliedTurns || 0) + 1;
      if (u.unsuppliedTurns === 1) {
        this.notify(`${u.def.name} has left naval supply; attrition begins after ` +
          `${NAVAL_SUPPLY.graceTurns} turns unless it reaches a friendly port.`, u.owner);
      }
      if (u.unsuppliedTurns <= NAVAL_SUPPLY.graceTurns) continue;
      u.hp -= NAVAL_SUPPLY.attritionDamage;
      this.addEffect(u.c, u.r, `-${NAVAL_SUPPLY.attritionDamage} supply`, "#e27b4d");
      if (u.hp <= 0) {
        this.notify(`${u.def.name} was lost after operating too long without naval supply.`, u.owner);
        this.removeUnit(u);
      } else {
        this.notify(`${u.def.name} suffers ${NAVAL_SUPPLY.attritionDamage} damage from naval attrition.`, u.owner);
      }
    }
  }

  // Ends the ACTIVE human's turn. With multiple humans (hotseat) this
  // advances to the next human; after the last one the AI phase runs
  // and the world clock advances.
  endTurn() {
    if (this.over) return;
    const human = this.players[this.activeHuman];
    this.cityStrikes(human);
    this.processNavalSupply(human);
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
      this.processNavalSupply(p);
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
    this.processDiplomacy();
    this.processQuests();
    this.processRandomEvents();
    if (this.congressDue()) this.runCongress();
    this.processMinorGifts();
    this.decayInfluence();
    this.processEspionage();
    this.processBarbarians();
    this.processTradeRoutes();
    if (this.turn % 5 === 0) {
      this.history.push({ t: this.turn,
        s: this.players.filter(p => !p.isMinor && !p.isBarb).map(p => this.score(p.index)) });
      if (this.history.length > 130) this.history.shift();
    }

    this.turn++;
    for (const u of this.units) {
      u.resetTurn();
      if (u.healFortify && u.hp >= 100) { u.healFortify = false; u.fortified = false; }
    }
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

  // ---------- random events ----------
  processRandomEvents() {
    for (const p of this.players) {
      if (!p.alive || p.isMinor || p.isBarb) continue;
      if (p.moodTurns > 0) p.moodTurns--;
      if (this.turn < EVENTS.graceTurns) continue;
      if (this.turn - p.lastEventTurn < EVENTS.cooldown) continue;
      if (this.rng() > EVENTS.chancePerTurn) continue;
      const myCities = this.cities.filter(c => c.owner === p.index);
      const pool = Object.entries(RANDOM_EVENTS).filter(([k, e]) =>
        (!e.needsCity || myCities.length > 0) && this.turn >= (e.minTurn || 0));
      if (!pool.length) continue;
      const total = pool.reduce((a, [, e]) => a + e.weight, 0);
      let roll = this.rng() * total, pick = pool[0][0];
      for (const [k, e] of pool) { roll -= e.weight; if (roll <= 0) { pick = k; break; } }
      p.lastEventTurn = this.turn;
      this.applyEvent(p, pick, myCities);
    }
  }

  applyEvent(p, key, myCities) {
    const ev = RANDOM_EVENTS[key];
    const era = p.era();
    const rc = myCities.length ? myCities[Math.floor(this.rng() * myCities.length)] : null;
    const cap = this.cities.find(c => c.id === p.originalCapitalId && c.owner === p.index) || rc;
    let msg = "";
    switch (key) {
      case "HARVEST":
        rc.food += Math.floor(rc.foodNeeded() * 0.6);
        msg = `a bumper harvest fills the granaries of ${rc.name}`;
        break;
      case "MIGRATION":
        rc.pop += 1;
        this.dirtyHappiness();
        msg = `migrants settle in ${rc.name} (+1 population)`;
        break;
      case "RELICS": {
        const f = 25 + era * 15;
        p.faith += f;
        msg = `sacred relics are unearthed near ${rc.name} (+${f} faith)`;
        break;
      }
      case "SCHOLARS": {
        const s = 30 + era * 25;
        p.scienceStored += s;
        msg = `wandering scholars share their learning (+${s} science)`;
        break;
      }
      case "TRADE_WINDS": {
        const g = 40 + era * 30;
        p.gold += g;
        msg = `favourable winds bring a windfall of trade (+${g} gold)`;
        break;
      }
      case "FESTIVAL":
        p.moodTurns = 8; p.moodDelta = 3; this.dirtyHappiness();
        msg = `a spontaneous festival lifts spirits (+3 happiness for 8 turns)`;
        break;
      case "PLAGUE": {
        const loss = rc.pop > 3 ? 2 : 1;
        rc.pop = Math.max(1, rc.pop - loss);
        p.moodTurns = 6; p.moodDelta = -3; this.dirtyHappiness();
        msg = `plague sweeps through ${rc.name} (-${loss} population, unrest)`;
        break;
      }
      case "UNREST":
        p.moodTurns = 8; p.moodDelta = -4; this.dirtyHappiness();
        msg = `civil unrest spreads through your empire (-4 happiness for 8 turns)`;
        break;
      case "FIRE":
        rc.prodStored = Math.floor(rc.prodStored * 0.3);
        rc.hp = Math.max(1, rc.hp - 40);
        msg = `a great fire ravages ${rc.name} (production and defences set back)`;
        break;
      case "RAIDERS": {
        const g = Math.min(p.gold, 25 + era * 15);
        p.gold -= g;
        msg = `brigands raid your caravans (-${g} gold)`;
        break;
      }
      case "DROUGHT":
        rc.food = Math.floor(rc.food * 0.4);
        p.moodTurns = 6; p.moodDelta = -2; this.dirtyHappiness();
        msg = `drought withers the fields around ${rc.name}`;
        break;
    }
    const at = rc || cap;
    if (at && ev.kind !== "good") this.addEffect(at.c, at.r, ev.icon, ev.kind === "bad" ? "#e74c3c" : "#f1c40f");
    else if (at) this.addEffect(at.c, at.r, ev.icon, "#2ecc71");
    this.notify(`${ev.icon} <b>${ev.name}:</b> ${msg}.`, p.index);
  }

  // ---------- World Congress ----------
  congressUnlocked() {
    return this.players.some(p => !p.isMinor && !p.isBarb && p.alive && p.hasTech(WCONGRESS.unlockTech));
  }

  // is a session resolving this round?
  congressDue() {
    return !this.scenario && this.congressUnlocked() && this.turn >= WCONGRESS.startTurn &&
      (this.turn - (this.congressTurn ?? -999)) >= WCONGRESS.interval &&
      this.players.filter(p => !p.isMinor && !p.isBarb && p.alive).length >= 3;
  }

  congressDelegates(idx) {
    const p = this.players[idx];
    if (!p || p.isMinor || p.isBarb || !p.alive) return 0;
    let d = WCONGRESS.base;
    for (const m of this.players) {
      if (m.isMinor && m.alive && this.minorStatus(idx, m.index) === "ally") d += WCONGRESS.perAlly;
    }
    d += Math.floor(this.cities.filter(c => c.owner === idx).length / WCONGRESS.perCities);
    return d;
  }

  congressCandidates() {
    return this.players.filter(p => !p.isMinor && !p.isBarb && p.alive).map(p => p.index);
  }

  religiousVictoryProgress(playerIdx) {
    const p = this.players[playerIdx];
    const alive = this.players.filter(o => !o.isMinor && !o.isBarb && o.alive);
    const majorOwners = new Set(alive.map(o => o.index));
    const majorCities = this.cities.filter(c => majorOwners.has(c.owner));
    const religion = p && p.religionId !== null ? this.religions[p.religionId] : null;
    const converted = religion ? majorCities.filter(c => c.religion === religion.id) : [];
    const dominatedCivs = religion ? alive.filter(o => {
      const owned = majorCities.filter(c => c.owner === o.index);
      const convertedOwned = owned.filter(c => c.religion === religion.id).length;
      return owned.length > 0 && convertedOwned > owned.length / 2;
    }) : [];
    const target = Math.floor(majorCities.length * RELIGION_VICTORY.share) + 1;
    const enoughCities = majorCities.length >= Math.max(RELIGION_VICTORY.minCities, alive.length);
    const enoughReligions = this.religions.length >= RELIGION_VICTORY.minReligions;
    return {
      founded: !!religion,
      religionId: religion ? religion.id : null,
      name: religion ? religion.name : null,
      icon: religion ? religion.icon : null,
      current: converted.length,
      target,
      totalCities: majorCities.length,
      civs: dominatedCivs.length,
      civTarget: alive.length,
      religions: this.religions.length,
      religionTarget: RELIGION_VICTORY.minReligions,
      spreads: p ? p.missionarySpreads : 0,
      spreadTarget: RELIGION_VICTORY.minSpreads,
      complete: !!religion && enoughCities && enoughReligions &&
        p.missionarySpreads >= RELIGION_VICTORY.minSpreads && converted.length >= target && dominatedCivs.length === alive.length,
    };
  }

  victoryProgress(playerIdx) {
    const p = this.players[playerIdx];
    const majors = this.players.filter(o => !o.isMinor && !o.isBarb);
    const alive = majors.filter(o => o.alive);
    const capitalIds = new Set(majors.map(o => o.originalCapitalId).filter(id => id !== null));
    const capitals = this.cities.filter(c => capitalIds.has(c.id));
    const delegatesTotal = alive.reduce((sum, o) => sum + this.congressDelegates(o.index), 0);
    const scoreOrder = alive.slice().sort((a, b) => this.score(b.index) - this.score(a.index));
    return {
      domination: {
        current: capitals.filter(c => c.owner === playerIdx).length,
        // All major civilizations will eventually found or receive an original
        // capital; show the full race target even during the opening Settler turn.
        target: majors.length,
      },
      science: { current: p.techs.size, target: Object.keys(TECHS).length },
      culture: { current: this.branchesDone(playerIdx), target: CULTURE_VICTORY_BRANCHES },
      religion: this.religiousVictoryProgress(playerIdx),
      diplomacy: {
        current: this.congressDelegates(playerIdx),
        target: Math.ceil(delegatesTotal * WCONGRESS.winFraction),
        total: delegatesTotal,
        unlocked: this.congressUnlocked(),
      },
      score: {
        current: this.score(playerIdx),
        rank: Math.max(1, scoreOrder.findIndex(o => o.index === playerIdx) + 1),
        field: alive.length,
        turnsLeft: Math.max(0, this.maxTurns - this.turn + 1),
      },
    };
  }

  // AI ballot: back yourself if you lead, otherwise the friendliest major
  // who isn't at war with you (helps a would-be diplomatic winner build a bloc)
  aiCongressVote(p) {
    const cands = this.congressCandidates();
    const myDel = this.congressDelegates(p.index);
    const ranked = cands.filter(i => i !== p.index)
      .sort((a, b) => this.congressDelegates(b) - this.congressDelegates(a));
    const leader = ranked[0];
    // only lend support to a clear runaway ally you genuinely like — otherwise
    // vote yourself, so a diplomatic win takes real city-state dominance
    if (leader != null && this.congressDelegates(leader) > myDel * 2 &&
        !p.atWarWith.has(leader) && this.attitudeOf(p.index, leader) >= 20 && this.rng() < 0.35) {
      return leader;
    }
    return p.index; // otherwise vote for yourself
  }

  runCongress() {
    const cands = this.congressCandidates();
    if (cands.length < 2) { this.congressTurn = this.turn; return; }
    const tally = {};
    for (const i of cands) tally[i] = 0;
    let total = 0;
    for (const voter of cands) {
      const p = this.players[voter];
      let choice = (p.congressVoteTurn === this.turn && p.congressVote != null &&
        tally[p.congressVote] != null) ? p.congressVote : this.aiCongressVote(p);
      const del = this.congressDelegates(voter);
      tally[choice] = (tally[choice] || 0) + del;
      total += del;
    }
    // winner of the session
    let best = cands[0];
    for (const i of cands) if (tally[i] > tally[best]) best = i;
    const bestCiv = this.players[best].civ.name;
    this.congressTurn = this.turn;
    this.congressLast = { tally, total, winner: best, turn: this.turn };
    for (const p of this.players) { p.congressVote = null; }
    const need = Math.ceil(total * WCONGRESS.winFraction);
    if (tally[best] >= need) {
      this.over = true; this.winner = best; this.victoryType = "Diplomatic";
      this.notify(`🏛️ The World Congress elects ${bestCiv} World Leader with ${tally[best]}/${total} delegates — a Diplomatic Victory!`, -1);
    } else {
      this.notify(`🏛️ World Congress: ${bestCiv} leads the vote (${tally[best]}/${total}); ${need} delegates are needed to be elected World Leader.`, -1);
    }
  }

  checkVictory() {
    if (this.over) return;
    if (this.scenario) {
      const sc = SCENARIOS[this.scenario], v = sc.victory;
      const me = this.players[0];
      const majorsAll = this.players.filter(p => !p.isMinor);
      const timeUp = this.turn > this.maxTurns;
      let won = null;
      if (!me.alive) won = false;
      if (won === null) switch (v.type) {
        case "capture": {
          const target = this.players.find(p => p.civId === v.target);
          const cap = this.cities.find(c => c.id === target.originalCapitalId);
          if ((cap && cap.owner === 0) || !target.alive) won = true;
          else if (timeUp) won = false;
          break;
        }
        case "survive": {
          const myCap = this.cities.find(c => c.id === me.originalCapitalId);
          if (this.turn > 3 && (!myCap || myCap.owner !== 0)) won = false;
          else if (timeUp) won = true;
          break;
        }
        case "capitals": {
          const n = this.cities.filter(c => c.owner === 0 &&
            majorsAll.some(p => p.originalCapitalId === c.id)).length;
          if (n >= v.count) won = true;
          else if (timeUp) won = false;
          break;
        }
        case "research": {
          if (me.techs.size >= Object.keys(TECHS).length) won = true;
          else if (timeUp) won = false;
          break;
        }
        case "kills": {
          if (this.scenarioKills >= v.count) won = true;
          else if (timeUp) won = false;
          break;
        }
        case "resistance": {
          const myCap = this.cities.find(c => c.id === me.originalCapitalId);
          if (this.turn > 3 && (!myCap || myCap.owner !== 0)) won = false;
          else if (myCap && myCap.owner === 0 && this.scenarioKills >= v.count) won = true;
          else if (timeUp) won = false;
          break;
        }
        case "cities": {
          if (this.cities.filter(c => c.owner === 0).length >= v.count) won = true;
          else if (timeUp) won = false;
          break;
        }
      }
      if (won === true) {
        this.over = true; this.winner = 0; this.victoryType = "Scenario";
      } else if (won === false) {
        let foe = v.target ? this.players.find(p => p.civId === v.target) : null;
        if (!foe && sc.warsAtStart.length) {
          const foeCiv = sc.warsAtStart[0][0] === me.civId ? sc.warsAtStart[0][1] : sc.warsAtStart[0][0];
          foe = this.players.find(p => p.civId === foeCiv);
        }
        if (!foe) {
          foe = majorsAll.filter(p => p.index !== 0 && p.alive)
            .sort((a, b) => this.score(b.index) - this.score(a.index))[0];
        }
        this.over = true; this.winner = foe ? foe.index : 1; this.victoryType = "Scenario";
      }
      return; // scenario games skip the standard victory rules
    }
    const majors = this.players.filter(p => !p.isMinor && !p.isBarb);
    // cultural victory: complete three policy branches
    for (const p of majors) {
      if (p.alive && this.branchesDone(p.index) >= CULTURE_VICTORY_BRANCHES) {
        this.over = true; this.winner = p.index; this.victoryType = "Culture";
        return;
      }
    }
    // scientific victory: master the complete technology tree
    for (const p of majors) {
      if (p.alive && p.techs.size >= Object.keys(TECHS).length) {
        this.over = true; this.winner = p.index; this.victoryType = "Scientific";
        this.notify(`🔬 ${p.civ.name} has mastered every technology — a Scientific Victory!`, -1);
        return;
      }
    }
    // religious victory: a majority of major cities and every surviving
    // civilization. The minimum city count prevents opening rush wins.
    for (const p of majors) {
      const progress = this.religiousVictoryProgress(p.index);
      if (p.alive && progress.complete) {
        this.over = true; this.winner = p.index; this.victoryType = "Religious";
        this.notify(`${progress.icon} ${progress.name} has become the faith of the Balkans — a Religious Victory for ${p.civ.name}!`, -1);
        return;
      }
    }
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
      v: 4, turn: this.turn, seed: this.seed,
      rngState: typeof this.rng.getState === "function" ? this.rng.getState() : null,
      mapType: this.mapType,
      difficulty: this.difficulty, humans: this.humans, activeHuman: this.activeHuman,
      scenario: this.scenario, scenarioKills: this.scenarioKills,
      noBarbs: this.noBarbs, barbIndex: this.barbIndex, maxCamps: this.maxCamps || 0,
      camps: this.camps, speed: this.speed, routes: this.routes, history: this.history,
      congressTurn: this.congressTurn, congressLast: this.congressLast,
      peaceOffers: this.peaceOffers, over: this.over,
      winner: this.winner, victoryType: this.victoryType, nextId: NEXT_ID,
      religions: this.religions, stats: this.stats,
      map: { w: this.map.w, h: this.map.h, tiles: this.map.tiles.map(t => ({
        c: t.c, r: t.r, terrain: t.terrain, feature: t.feature, resource: t.resource,
        improvement: t.improvement, road: !!t.road, river: !!t.river, ruin: t.ruin || false,
        owner: t.owner, cityId: t.city ? t.city.id : null })) },
      players: this.players.map(p => ({
        index: p.index, civId: p.civId, isHuman: p.isHuman, alive: p.alive,
        gold: p.gold, scienceStored: p.scienceStored, researching: p.researching,
        techs: [...p.techs], atWarWith: [...p.atWarWith], met: [...p.met],
        warWeariness: p.warWeariness, cityNameCursor: p.cityNameCursor,
        visible: Array.from(p.visible), originalCapitalId: p.originalCapitalId,
        faith: p.faith, religionId: p.religionId, influence: p.influence,
        gaMeter: p.gaMeter, goldenAgeTurns: p.goldenAgeTurns, gaCount: p.gaCount,
        spies: p.spies, gpPoints: p.gpPoints, gpBorn: p.gpBorn,
        culture: p.culture, policies: [...p.policies], attitude: p.attitude,
        pacts: [...p.pacts], deals: p.deals, quest: p.quest,
        moodTurns: p.moodTurns, moodDelta: p.moodDelta, lastEventTurn: p.lastEventTurn,
        leaderIdx: p.leaderIdx, congressVote: p.congressVote, congressVoteTurn: p.congressVoteTurn,
        missionarySpreads: p.missionarySpreads })),
      cities: this.cities.map(c => ({ ...c })),
      units: this.units.map(u => ({ id: u.id, type: u.type, owner: u.owner, c: u.c, r: u.r,
        hp: u.hp, moves: u.moves, fortified: u.fortified, attacked: u.attacked, path: u.path,
        xp: u.xp, level: u.level, promos: u.promos, promoPts: u.promoPts,
        building: u.building, charges: u.charges,
        autoExplore: u.autoExplore || false, healFortify: u.healFortify || false,
        unsuppliedTurns: u.unsuppliedTurns || 0, resupplying: u.resupplying || false,
        gpName: u.gpName || null })),
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
    g.scenarioKills = d.scenarioKills || 0;
    g.noBarbs = d.noBarbs || false;
    g.barbIndex = d.barbIndex ?? -1;
    g.maxCamps = d.maxCamps || 0;
    g.camps = d.camps || [];
    g.speed = SPEEDS[d.speed] ? d.speed : "standard";
    g.routes = d.routes || [];
    g.history = d.history || [];
    g.congressTurn = d.congressTurn ?? -999;
    g.congressLast = d.congressLast || null;
    g.peaceOffers = d.peaceOffers || [];
    if (g.scenario && SCENARIOS[g.scenario]) g.maxTurns = SCENARIOS[g.scenario].victory.turns;
    g.effects = [];
    g.anims = [];
    g.strikes = [];
    g.lastCombat = null;
    g.winner = d.winner; g.victoryType = d.victoryType;
    if (!g.scenario) g.maxTurns = SPEEDS[g.speed].turns;
    // Version 2+ persists the exact PRNG state. Version 1 saves retain their
    // historical turn-derived fallback so existing local saves still load.
    const fallbackRngState = (d.seed + d.turn * 7919) >>> 0;
    g.rng = mulberry32(d.rngState ?? fallbackRngState);
    g.notifications = d.notifications || [];
    g.religions = d.religions || [];
    g.stats = d.stats || { steals: 0, catches: 0 };

    g.map = { w: d.map.w, h: d.map.h, tiles: [], idx: (c, r) => r * d.map.w + c, seed: d.seed };
    for (const td of d.map.tiles) {
      const legacyRoad = td.improvement === "ROAD";
      g.map.tiles.push({ c: td.c, r: td.r, terrain: td.terrain, feature: td.feature,
        resource: td.resource, improvement: legacyRoad ? null : (td.improvement ?? null),
        road: !!td.road || legacyRoad, river: !!td.river, ruin: td.ruin || false,
        owner: td.owner, city: null, workedBy: null, _cityId: td.cityId });
    }
    g.cities = d.cities.map(cd => Object.assign(new City(cd.name, cd.owner, cd.c, cd.r), cd));
    for (const t of g.map.tiles) {
      if (t._cityId != null) t.city = g.cities.find(c => c.id === t._cityId) || null;
      delete t._cityId;
    }
    g.units = d.units.map(ud => Object.assign(new Unit(ud.type, ud.owner, ud.c, ud.r), ud));
    for (const u of g.units) {
      if (!Array.isArray(u.promos)) u.promos = [];
      // pre-promotion saves: bank the earned levels as pending picks
      if (typeof u.promoPts !== "number") u.promoPts = Math.max(0, (u.level || 0) - u.promos.length);
      if (typeof u.unsuppliedTurns !== "number") u.unsuppliedTurns = 0;
      if (typeof u.resupplying !== "boolean") u.resupplying = false;
    }
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
      p.gpPoints = pd.gpPoints || { sci: 0, eng: 0, gen: 0 };
      p.gpBorn = pd.gpBorn || { sci: 0, eng: 0, gen: 0 };
      p.culture = pd.culture || 0;
      p.policies = new Set(pd.policies || []);
      p.attitude = pd.attitude || {};
      p.pacts = new Set(pd.pacts || []);
      p.deals = pd.deals || [];
      p.quest = pd.quest || null;
      p.moodTurns = pd.moodTurns || 0;
      p.moodDelta = pd.moodDelta || 0;
      p.lastEventTurn = pd.lastEventTurn ?? -99;
      p.leaderIdx = pd.leaderIdx || 0;
      p.congressVote = pd.congressVote ?? null;
      p.congressVoteTurn = pd.congressVoteTurn ?? -1;
      p.missionarySpreads = pd.missionarySpreads || 0;
      return p;
    });
    // City and Unit constructors allocate temporary IDs while rebuilding
    // prototypes. Reset the global allocator only after hydration so loading a
    // save cannot skip IDs and diverge from uninterrupted deterministic play.
    const existingIds = [...g.cities.map(c => c.id), ...g.units.map(u => u.id),
      ...g.players.flatMap(p => p.spies.map(s => s.id))].filter(Number.isFinite);
    NEXT_ID = Math.max(Number(d.nextId) || 1, (existingIds.length ? Math.max(...existingIds) : 0) + 1);
    return g;
  }
}
