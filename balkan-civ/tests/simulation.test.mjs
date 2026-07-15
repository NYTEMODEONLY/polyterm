import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const gameRoot = path.resolve(here, "..");

function loadGameContext() {
  const context = vm.createContext({ console, Math, Date, Uint8Array, Set, Map, JSON });
  for (const file of ["data.js", "hex.js", "mapgen.js", "model.js", "ai.js"]) {
    vm.runInContext(fs.readFileSync(path.join(gameRoot, "js", file), "utf8"), context, { filename: file });
  }
  return context;
}

function loadUnitArtContext() {
  const context = vm.createContext({ console, Math, Set, Map, JSON });
  for (const file of ["data.js", "unitart.js"]) {
    vm.runInContext(fs.readFileSync(path.join(gameRoot, "js", file), "utf8"), context, { filename: file });
  }
  return context;
}

function evaluate(context, source) {
  return vm.runInContext(`(() => { ${source} })()`, context);
}

const simulationSource = `
  const run = (seed, turns = 45) => {
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 4, seed,
      mapW: 34, mapH: 26, mapType: "peninsula", difficulty: "normal" });
    for (let i = 0; i < turns && !g.over; i++) {
      AI.takeTurn(g, g.players[0]);
      g.endTurn();
    }
    const majors = g.players.filter(p => !p.isMinor && !p.isBarb);
    const players = majors.map(p => ({
      civ: p.civId, alive: p.alive, gold: Math.floor(p.gold), science: Math.floor(p.scienceStored),
      researching: p.researching, techs: [...p.techs].sort(), score: g.score(p.index),
      cities: g.cities.filter(c => c.owner === p.index).length,
      units: g.units.filter(u => u.owner === p.index).map(u => u.type).sort(),
      wars: [...p.atWarWith].filter(i => majors.some(m => m.index === i)).sort((a, b) => a - b),
    }));
    const cities = g.cities.filter(c => majors.some(p => p.index === c.owner)).map(c => ({
      owner: c.owner, name: c.name, c: c.c, r: c.r, pop: c.pop,
      buildings: [...c.buildings].sort(), producing: c.producing && c.producing.key,
    })).sort((a, b) => a.owner - b.owner || a.name.localeCompare(b.name));
    return JSON.stringify({ turn: g.turn, over: g.over, winner: g.winner,
      victory: g.victoryType, players, cities });
  };
  return run(424242);
`;

const controlledWorldSource = `
  const resetWorld = (g) => {
    g.units = []; g.cities = []; g.camps = []; g.routes = []; g.peaceOffers = [];
    g._hap = {}; g._aiLandmassMap = null;
    for (const tile of g.map.tiles) {
      tile.terrain = "PLAINS"; tile.feature = null; tile.resource = null;
      tile.improvement = null; tile.owner = -1; tile.city = null; tile.workedBy = null;
    }
    for (const p of g.players) {
      p.atWarWith.clear(); p.pacts.clear(); p.met.clear();
      p.attitude = {}; p.warWeariness = {}; p.deals = [];
    }
  };
  const addCity = (g, owner, c, r, name, capital = false) => {
    const city = new City(name, owner, c, r);
    city.isCapital = capital; city.pop = 5;
    g.cities.push(city); g.tile(c, r).city = city; g.tile(c, r).owner = owner;
    if (capital) g.players[owner].originalCapitalId = city.id;
    return city;
  };
  const addUnit = (g, type, owner, c, r) => {
    const unit = new Unit(type, owner, c, r); g.units.push(unit); return unit;
  };
`;

test("fixed-seed AI simulations produce an identical strategic fingerprint", () => {
  const first = evaluate(loadGameContext(), simulationSource);
  const second = evaluate(loadGameContext(), simulationSource);
  assert.equal(second, first);
});

test("AI war planning chooses one viable target and will not open a second front", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 2, seed: 61001,
      mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    resetWorld(g);
    addCity(g, 0, 3, 8, "Home", true);
    addCity(g, 1, 8, 8, "Hostile Border", true);
    addCity(g, 2, 10, 8, "Warm Border", true);
    [[2, 7], [2, 8], [2, 9], [3, 7], [3, 9], [4, 8]].forEach(([c, r]) =>
      addUnit(g, "WARRIOR", 0, c, r));
    addUnit(g, "WARRIOR", 1, 8, 9);
    addUnit(g, "WARRIOR", 2, 10, 9);
    g.players[0].met = new Set([2, 1]);
    g.players[1].met.add(0); g.players[2].met.add(0);
    g.players[0].attitude[1] = -60; g.players[1].attitude[0] = -60;
    g.players[0].attitude[2] = 10; g.players[2].attitude[0] = 10;

    const plan = AI.chooseWarTarget(g, g.players[0]);
    g.declareWar(0, plan.player);
    g.rng = () => 0;
    AI.takeTurn(g, g.players[0]);
    return JSON.stringify({ plan, wars: [...g.players[0].atWarWith].sort((a, b) => a - b) });
  `));

  assert.equal(result.plan.player, 1, "target scoring should beat met-player insertion order");
  assert.ok(result.plan.score > 0);
  assert.deepEqual(result.wars, [1], "an active campaign must block another opportunistic declaration");
});

test("AI production plans support arms, reserves, and only one expansion unit", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const wartime = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 62001,
      mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    resetWorld(wartime);
    const cities = [addCity(wartime, 0, 3, 5, "A", true),
      addCity(wartime, 0, 3, 9, "B"), addCity(wartime, 0, 6, 7, "C")];
    addCity(wartime, 1, 16, 7, "Enemy", true);
    cities.forEach((city, i) => {
      city.producing = { kind: "building", key: "MONUMENT" };
      addUnit(wartime, "MUSKETMAN", 0, city.c, city.r);
    });
    addUnit(wartime, "WARRIOR", 1, 15, 7);
    wartime.players[0].techs = new Set(Object.keys(TECHS));
    wartime.players[0].met.add(1); wartime.players[1].met.add(0);
    wartime.declareWar(0, 1); wartime.rng = () => 0.5;
    AI.takeTurn(wartime, wartime.players[0]);
    const queued = cities.flatMap(city => city.queue).filter(item => item.kind === "unit");

    const peace = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 62002,
      mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    resetWorld(peace);
    [[3, 5], [3, 9], [6, 7]].forEach(([c, r], i) => {
      const city = addCity(peace, 0, c, r, "P" + i, i === 0);
      city.pop = 4; addUnit(peace, "WARRIOR", 0, c, r);
    });
    peace.rng = () => 0;
    AI.takeTurn(peace, peace.players[0]);
    return JSON.stringify({
      queued: queued.map(item => item.key), queuedRoles: queued.map(item => AI.armyRole(item.key)),
      settlers: peace.cities.filter(c => c.owner === 0 && c.producing && c.producing.key === "SETTLER").length,
      desired: AI.desiredArmyRoles(10, true, "science", true),
    });
  `));

  assert.equal(result.queued.length, 3, "busy wartime cities should maintain a one-order reserve");
  assert.ok(result.queuedRoles.includes("siege"), "the reserve should include city bombardment");
  assert.ok(result.queuedRoles.includes("ranged"), "the reserve should include ranged support");
  assert.deepEqual(result.desired, { frontline: 5, ranged: 3, siege: 2 });
  assert.equal(result.settlers, 1, "parallel cities must not all start Settlers in the same turn");
});

test("AI land campaigns reserve coordinated frontline and ranged approach positions", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 63001,
      mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    resetWorld(g);
    const home = addCity(g, 0, 3, 8, "Home", true);
    home.producing = { kind: "building", key: "MONUMENT" };
    addCity(g, 1, 15, 8, "Border Capital", true);
    addCity(g, 1, 19, 13, "Rear City");
    const army = [addUnit(g, "WARRIOR", 0, 4, 6), addUnit(g, "SPEARMAN", 0, 4, 10),
      addUnit(g, "ARCHER", 0, 5, 7), addUnit(g, "CATAPULT", 0, 5, 11)];
    g.players[0].techs = new Set(Object.keys(TECHS));
    g.players[0].met.add(1); g.players[1].met.add(0);
    g.declareWar(0, 1); g.rng = () => 0.5;
    const target = AI.campaignTarget(g, g.players[0]);
    AI.takeTurn(g, g.players[0]);
    const endpoints = army.map(unit => unit.path && unit.path.length
      ? unit.path[unit.path.length - 1] : [unit.c, unit.r]);
    return JSON.stringify({ target: target.id, endpoints,
      distances: endpoints.map(([c, r]) => HEX.distance(c, r, target.c, target.r)) });
  `));

  assert.deepEqual([...result.distances].sort((a, b) => a - b), [1, 1, 2, 2]);
  assert.equal(new Set(result.endpoints.map(([c, r]) => c + "," + r)).size, 4,
    "units should not reserve the same final approach tile");
});

test("AI overseas war plans require transport technology and an existing fleet", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64001,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(g);
    for (const tile of g.map.tiles) if (tile.c >= 8 && tile.c <= 15) tile.terrain =
      tile.c === 8 || tile.c === 15 ? "COAST" : "OCEAN";
    const home = addCity(g, 0, 7, 8, "Home", true); home.coastal = true;
    const target = addCity(g, 1, 16, 8, "Other Shore", true); target.coastal = true;
    [[5, 6], [5, 7], [5, 8], [5, 9], [5, 10], [6, 8]].forEach(([c, r]) =>
      addUnit(g, "WARRIOR", 0, c, r));
    addUnit(g, "WARRIOR", 1, 17, 8);
    addUnit(g, "GALLEY", 0, 8, 8);
    g.players[0].met.add(1); g.players[1].met.add(0);
    g.players[0].attitude[1] = -60; g.players[1].attitude[0] = -60;

    const beforeCompass = AI.chooseWarTarget(g, g.players[0]);
    g.players[0].techs.add("COMPASS");
    const ready = AI.chooseWarTarget(g, g.players[0]);
    return JSON.stringify({ beforeCompass, ready,
      overseas: AI.campaignIsOverseas(g, g.players[0], target),
      rival: AI.hasOverseasRival(g, g.players[0]) });
  `));

  assert.equal(result.beforeCompass, null);
  assert.equal(result.ready.player, 1);
  assert.equal(result.ready.overseas, true);
  assert.equal(result.overseas, true);
  assert.equal(result.rival, true);
});

test("imposed overseas wars prioritize Compass research and queue a fleet reserve", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64002,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(g);
    for (const tile of g.map.tiles) if (tile.c >= 8 && tile.c <= 15) tile.terrain =
      tile.c === 8 || tile.c === 15 ? "COAST" : "OCEAN";
    const home = addCity(g, 0, 7, 8, "Home", true); home.coastal = true;
    home.producing = { kind: "building", key: "MONUMENT" };
    const target = addCity(g, 1, 16, 8, "Invader", true); target.coastal = true;
    addUnit(g, "WARRIOR", 0, 6, 8); addUnit(g, "WARRIOR", 1, 17, 8);
    g.players[0].techs = new Set(["AGRICULTURE", "POTTERY", "SAILING", "ANIMAL_HUSBANDRY",
      "THE_WHEEL", "ARCHERY", "MINING", "BRONZE_WORKING", "MASONRY", "WRITING"]);
    g.players[0].met.add(1); g.players[1].met.add(0);
    g.declareWar(0, 1); g.rng = () => 0.5;
    AI.takeTurn(g, g.players[0]);
    return JSON.stringify({ research: g.players[0].researching, queue: home.queue,
      overseas: AI.campaignIsOverseas(g, g.players[0], target) });
  `));

  assert.equal(result.overseas, true);
  assert.equal(result.research, "MATHEMATICS", "the next available Compass prerequisite should outrank land techs");
  assert.ok(result.queue.some(item => item.kind === "unit" && item.key === "GALLEY"),
    "a busy coastal city should queue the available fleet unit");
});

test("AI ships upgrade, explore in peace, and reserve distinct bombardment positions", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const upgradeGame = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64003,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(upgradeGame);
    const port = addCity(upgradeGame, 0, 7, 8, "Port", true); port.coastal = true;
    upgradeGame.tile(8, 8).terrain = "COAST"; upgradeGame.tile(8, 8).owner = 0;
    const oldShip = addUnit(upgradeGame, "GALLEY", 0, 8, 8);
    upgradeGame.players[0].techs.add("COMPASS"); upgradeGame.players[0].gold = 1000;
    upgradeGame.rng = () => 0.5; AI.takeTurn(upgradeGame, upgradeGame.players[0]);

    const exploreGame = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64004,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(exploreGame);
    const explorePort = addCity(exploreGame, 0, 7, 8, "Port", true); explorePort.coastal = true;
    for (const tile of exploreGame.map.tiles) if (tile.c >= 8) tile.terrain = "COAST";
    const explorer = addUnit(exploreGame, "GALLEY", 0, 8, 8);
    exploreGame.players[0].visible.fill(0); exploreGame.updateVisibility(exploreGame.players[0]);
    const start = [explorer.c, explorer.r]; exploreGame.rng = () => 0.5;
    AI.takeTurn(exploreGame, exploreGame.players[0]);

    const battle = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64005,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(battle);
    for (const tile of battle.map.tiles) if (tile.c >= 8 && tile.c <= 15) tile.terrain =
      tile.c === 8 || tile.c === 15 ? "COAST" : "OCEAN";
    const battlePort = addCity(battle, 0, 7, 8, "Port", true); battlePort.coastal = true;
    const enemy = addCity(battle, 1, 16, 8, "Enemy Port", true); enemy.coastal = true;
    const fleet = [addUnit(battle, "GALLEASS", 0, 8, 7), addUnit(battle, "GALLEASS", 0, 8, 9)];
    battle.players[0].techs.add("COMPASS"); battle.players[0].met.add(1); battle.players[1].met.add(0);
    battle.declareWar(0, 1); battle.rng = () => 0.5;
    AI.takeTurn(battle, battle.players[0]);
    const endpoints = fleet.map(ship => ship.path && ship.path.length
      ? ship.path[ship.path.length - 1] : [ship.c, ship.r]);
    return JSON.stringify({ upgraded: oldShip.type, start, explored: [explorer.c, explorer.r],
      explorePath: explorer.path, endpoints,
      distances: endpoints.map(([c, r]) => HEX.distance(c, r, enemy.c, enemy.r)) });
  `));

  assert.equal(result.upgraded, "GALLEASS");
  assert.ok(result.explored[0] !== result.start[0] || result.explored[1] !== result.start[1] || result.explorePath,
    "a peacetime ship should leave port to chart unseen reachable water");
  assert.deepEqual([...result.distances].sort((a, b) => a - b), [2, 2]);
  assert.equal(new Set(result.endpoints.map(([c, r]) => c + "," + r)).size, 2);
});

test("naval progression and promotion choices remain role-specific across upgrades", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64006,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(g);
    const port = addCity(g, 0, 7, 8, "Port", true); port.coastal = true;
    g.tile(8, 8).terrain = "COAST"; g.tile(8, 8).owner = 0;
    g.players[0].techs = new Set(Object.keys(TECHS)); g.players[0].gold = 10000;
    const ship = addUnit(g, "GALLEY", 0, 8, 8); ship.promoPts = 1;
    const navigated = g.issueUnitOrder(ship, "promote", 0, "NAVIGATION");
    const immediateMoves = ship.moves;
    const upgrades = [];
    while (true) {
      const next = g.canUpgrade(ship, 0);
      if (!next) break;
      upgrades.push(next.to);
      g.upgradeUnit(ship, 0);
      ship.moves = ship.maxMoves;
    }

    const warrior = addUnit(g, "WARRIOR", 0, 6, 8);
    const archer = addUnit(g, "ARCHER", 0, 6, 9);
    const galley = addUnit(g, "GALLEY", 0, 8, 9);
    galley.promoPts = 1;
    const invalidNaval = g.issueUnitOrder(galley, "promote", 0, "PATHFINDER");
    const validNaval = g.issueUnitOrder(galley, "promote", 0, "BOARDING");
    const spentShip = addUnit(g, "GALLEY", 0, 9, 9);
    spentShip.promoPts = 1; spentShip.attacked = true; spentShip.moves = 0;
    const spentNavigation = g.issueUnitOrder(spentShip, "promote", 0, "NAVIGATION");
    warrior.promoPts = 1;
    const invalidLand = g.issueUnitOrder(warrior, "promote", 0, "BOARDING");
    return JSON.stringify({ upgrades, finalType: ship.type, finalMoves: ship.maxMoves,
      navigated, immediateMoves,
      warrior: promotionChoices(warrior), archer: promotionChoices(archer),
      naval: promotionChoices(galley), invalidNaval, validNaval, invalidLand,
      spentNavigation, spentMoves: spentShip.moves,
      frigate: { tech: UNITS.FRIGATE.tech, ranged: UNITS.FRIGATE.rs, moves: UNITS.FRIGATE.moves } });
  `));

  assert.deepEqual(result.upgrades, ["GALLEASS", "FRIGATE", "IRONCLAD"]);
  assert.equal(result.finalType, "IRONCLAD");
  assert.equal(result.finalMoves, 6, "Navigation should survive upgrades and raise maximum movement");
  assert.deepEqual({ navigated: result.navigated, immediateMoves: result.immediateMoves },
    { navigated: true, immediateMoves: 5 });
  assert.deepEqual(result.warrior, ["MIGHT", "BULWARK", "MEDIC", "PATHFINDER", "AMPHIBIOUS"]);
  assert.deepEqual(result.archer, ["MIGHT", "BULWARK", "MEDIC", "PATHFINDER"]);
  assert.deepEqual(result.naval, ["MIGHT", "BULWARK", "MEDIC", "BOARDING", "BOMBARDMENT", "NAVIGATION"]);
  assert.deepEqual({ invalidNaval: result.invalidNaval, validNaval: result.validNaval,
    invalidLand: result.invalidLand, spentNavigation: result.spentNavigation,
    spentMoves: result.spentMoves }, { invalidNaval: false, validNaval: true, invalidLand: false,
    spentNavigation: true, spentMoves: 0 });
  assert.deepEqual(result.frigate, { tech: "GUNPOWDER", ranged: 24, moves: 6 });
});

test("shared naval unit art assigns every upgrade era a distinct silhouette", () => {
  const profiles = JSON.parse(evaluate(loadUnitArtContext(), `
    return JSON.stringify(Object.fromEntries(["GALLEY", "GALLEASS", "FRIGATE", "IRONCLAD"]
      .map(key => [key, UNIT_ART.kind(UNITS[key])])));
  `));

  assert.deepEqual(profiles,
    { GALLEY: "galley", GALLEASS: "galleass", FRIGATE: "frigate", IRONCLAD: "steamship" });
  assert.equal(new Set(Object.values(profiles)).size, 4);
});

test("Amphibious Assault enables forecasted shore attacks with a controlled penalty", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64007,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(g);
    addCity(g, 0, 5, 8, "Home", true);
    addCity(g, 1, 12, 8, "Enemy", true);
    g.tile(8, 8).terrain = "COAST";
    const attacker = addUnit(g, "RIFLEMAN", 0, 8, 8);
    const defender = addUnit(g, "WARRIOR", 1, 9, 8);
    g.players[0].techs.add("SAILING");
    g.players[0].met.add(1); g.players[1].met.add(0); g.declareWar(0, 1);
    const target = g.tile(9, 8);
    const embarkedStrength = g.strengthOf(attacker, { attacking: true, targetTile: target, ranged: false });
    const blockedForecast = g.predictAttack(attacker, 9, 8);
    const blockedAttack = g.attack(attacker, 9, 8);
    attacker.promoPts = 1;
    const promoted = g.issueUnitOrder(attacker, "promote", 0, "AMPHIBIOUS");
    const assaultStrength = g.strengthOf(attacker, { attacking: true, targetTile: target, ranged: false });
    const forecast = g.predictAttack(attacker, 9, 8);
    g.rng = () => 0.5;
    const attacked = g.attack(attacker, 9, 8);
    return JSON.stringify({ embarkedStrength, blockedForecast, blockedAttack, promoted,
      assaultStrength, forecast, attacked, landed: [attacker.c, attacker.r],
      defenderAlive: g.units.includes(defender), attackerHp: attacker.hp });
  `));

  assert.equal(result.embarkedStrength, 2);
  assert.equal(result.blockedForecast, null);
  assert.equal(result.blockedAttack, false);
  assert.equal(result.promoted, true);
  assert.ok(Math.abs(result.assaultStrength - 28.9) < 0.001);
  assert.ok(result.forecast && result.forecast.out[0] > 100);
  assert.equal(result.attacked, true);
  assert.deepEqual(result.landed, [9, 8]);
  assert.equal(result.defenderAlive, false);
  assert.ok(result.attackerHp > 0);
});

test("naval promotions affect combat and AI specialization deterministically", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    ${controlledWorldSource}
    const combat = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64008,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(combat);
    addCity(combat, 0, 5, 8, "Home", true);
    const enemyCity = addCity(combat, 1, 10, 10, "Enemy Port", true); enemyCity.coastal = true;
    for (const [c, r] of [[6, 8], [7, 8], [8, 10]]) combat.tile(c, r).terrain = "COAST";
    const boarder = addUnit(combat, "GALLEY", 0, 6, 8);
    addUnit(combat, "GALLEY", 1, 7, 8);
    const bomber = addUnit(combat, "GALLEASS", 0, 8, 10);
    combat.players[0].met.add(1); combat.players[1].met.add(0); combat.declareWar(0, 1);
    const boardingBase = combat.strengthOf(boarder,
      { attacking: true, targetTile: combat.tile(7, 8), ranged: false });
    boarder.promos.push("BOARDING");
    const boardingBoost = combat.strengthOf(boarder,
      { attacking: true, targetTile: combat.tile(7, 8), ranged: false });
    const bombardBase = combat.strengthOf(bomber,
      { attacking: true, targetTile: combat.tile(10, 10), ranged: true });
    bomber.promos.push("BOMBARDMENT");
    const bombardBoost = combat.strengthOf(bomber,
      { attacking: true, targetTile: combat.tile(10, 10), ranged: true });
    const navigator = addUnit(combat, "FRIGATE", 0, 8, 11);
    navigator.promos.push("NAVIGATION"); navigator.moves = 0; navigator.resetTurn();

    const strategy = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 64009,
      mapW: 24, mapH: 18, mapType: "archipelago", noMinors: true, noBarbs: true });
    resetWorld(strategy);
    const port = addCity(strategy, 0, 5, 8, "Port", true); port.coastal = true;
    strategy.tile(6, 8).terrain = "COAST"; strategy.tile(6, 9).terrain = "COAST";
    const meleeShip = addUnit(strategy, "GALLEY", 0, 6, 8);
    const rangedShip = addUnit(strategy, "GALLEASS", 0, 6, 9);
    const marine = addUnit(strategy, "WARRIOR", 0, 5, 8);
    meleeShip.promoPts = 1; rangedShip.promoPts = 1; marine.promoPts = 1;
    strategy.rng = () => 0.5; AI.takeTurn(strategy, strategy.players[0]);
    return JSON.stringify({ boardingBase, boardingBoost, bombardBase, bombardBoost,
      navigation: { moves: navigator.moves, max: navigator.maxMoves },
      choices: { melee: meleeShip.promos, ranged: rangedShip.promos, marine: marine.promos } });
  `));

  assert.equal(result.boardingBoost / result.boardingBase, 1.2);
  assert.equal(result.bombardBoost / result.bombardBase, 1.2);
  assert.deepEqual(result.navigation, { moves: 7, max: 7 });
  assert.deepEqual(result.choices,
    { melee: ["BOARDING"], ranged: ["BOMBARDMENT"], marine: ["AMPHIBIOUS"] });
});

test("seeded AI campaigns sustain support arms without opportunistic extra fronts", () => {
  const metrics = JSON.parse(evaluate(loadGameContext(), `
    const metrics = { extraFronts: 0, doubleDeclarations: 0, captures: 0,
      warArmyTurns: 0, rangedTurns: 0, siegeReadyTurns: 0, siegeCoveredTurns: 0 };
    for (let seed = 1; seed <= 6; seed++) {
      const g = new Game({ playerCiv: CIV_IDS[seed % CIV_IDS.length], numOpponents: 5,
        seed: seed * 7919, mapW: 38, mapH: 28,
        mapType: seed % 3 === 0 ? "archipelago" : "peninsula", difficulty: "normal" });
      let activeAI = null;
      const originalTakeTurn = AI.takeTurn;
      AI.takeTurn = (game, p) => {
        activeAI = p.index;
        try { return originalTakeTurn(game, p); } finally { activeAI = null; }
      };
      const declarations = [];
      const originalDeclareWar = g.declareWar.bind(g);
      g.declareWar = (a, b) => {
        const fresh = !g.players[a].atWarWith.has(b);
        const prior = [...g.players[a].atWarWith].filter(i => g.players[i].alive &&
          !g.players[i].isMinor && !g.players[i].isBarb).length;
        if (fresh && a === activeAI && !g.players[a].isMinor && !g.players[b].isMinor &&
            !g.players[b].isBarb) declarations.push({ turn: g.turn, actor: a, prior });
        return originalDeclareWar(a, b);
      };
      const originalCapture = g.captureCity.bind(g);
      g.captureCity = (...args) => { metrics.captures++; return originalCapture(...args); };

      for (let step = 0; step < 130 && !g.over; step++) {
        AI.takeTurn(g, g.players[0]); g.endTurn();
        for (const p of g.players.filter(p => p.alive && !p.isMinor && !p.isBarb)) {
          const wars = [...p.atWarWith].filter(i => g.players[i].alive &&
            !g.players[i].isMinor && !g.players[i].isBarb);
          if (!wars.length) continue;
          metrics.warArmyTurns++;
          const army = g.units.filter(u => u.owner === p.index && !u.isCivilian &&
            !u.def.naval && !u.def.great && u.type !== "SCOUT");
          if (army.some(u => u.isRanged && !u.def.siege)) metrics.rangedTurns++;
          const siegeReady = Object.keys(UNITS).some(key => UNITS[key].siege &&
            (!UNITS[key].tech || p.hasTech(UNITS[key].tech)));
          const siegePlanned = army.some(u => u.def.siege) || g.cities.some(city =>
            city.owner === p.index &&
            ((city.producing && city.producing.kind === "unit" && UNITS[city.producing.key].siege) ||
             city.queue.some(item => item.kind === "unit" && UNITS[item.key].siege)));
          if (siegeReady) {
            metrics.siegeReadyTurns++;
            if (siegePlanned) metrics.siegeCoveredTurns++;
          }
        }
      }
      metrics.extraFronts += declarations.filter(d => d.prior > 0).length;
      const byTurnActor = new Map();
      for (const d of declarations) {
        const key = d.turn + ":" + d.actor;
        byTurnActor.set(key, (byTurnActor.get(key) || 0) + 1);
      }
      metrics.doubleDeclarations += [...byTurnActor.values()].filter(count => count > 1).length;
      AI.takeTurn = originalTakeTurn;
    }
    return JSON.stringify(metrics);
  `));

  assert.equal(metrics.extraFronts, 0);
  assert.equal(metrics.doubleDeclarations, 0);
  assert.ok(metrics.captures >= 1, "the reviewed sample should convert campaigns into city captures");
  assert.ok(metrics.rangedTurns / metrics.warArmyTurns >= 0.35,
    "ranged support should accompany a meaningful share of wartime armies");
  assert.ok(metrics.siegeReadyTurns > 0 &&
    metrics.siegeCoveredTurns / metrics.siegeReadyTurns >= 0.75,
    "siege-capable wartime empires should usually field or queue siege");
});

test("seeded archipelago campaigns build active fleets and resolve overseas objectives", () => {
  const metrics = JSON.parse(evaluate(loadGameContext(), `
    const metrics = { warTurns: 0, quietWarTurns: 0, attacks: 0, navalAttacks: 0,
      captures: 0, shipsBuilt: 0, overseasTurns: 0, preparedOverseasTurns: 0 };
    for (let seed = 1; seed <= 5; seed++) {
      const g = new Game({ playerCiv: CIV_IDS[seed % CIV_IDS.length], numOpponents: 5,
        seed: seed * 7919, mapW: 38, mapH: 28, mapType: "archipelago", difficulty: "normal" });
      let gameAttacks = 0;
      const originalAddUnit = g.addUnit.bind(g);
      g.addUnit = (type, ...args) => {
        if (g.turn > 1 && UNITS[type].naval) metrics.shipsBuilt++;
        return originalAddUnit(type, ...args);
      };
      const originalCapture = g.captureCity.bind(g);
      g.captureCity = (...args) => { metrics.captures++; return originalCapture(...args); };
      const originalAttack = g.attack.bind(g);
      g.attack = (unit, c, r) => {
        const tile = g.tile(c, r);
        const targetUnit = g.combatUnitAt(c, r);
        const majorTarget = tile && tile.city && !g.players[tile.city.owner].isMinor &&
          !g.players[tile.city.owner].isBarb || targetUnit &&
          !g.players[targetUnit.owner].isMinor && !g.players[targetUnit.owner].isBarb;
        const attacked = originalAttack(unit, c, r);
        if (attacked && majorTarget && !g.players[unit.owner].isMinor && !g.players[unit.owner].isBarb) {
          metrics.attacks++; gameAttacks++;
          if (unit.def.naval) metrics.navalAttacks++;
        }
        return attacked;
      };

      for (let step = 0; step < 150 && !g.over; step++) {
        const attacksBefore = gameAttacks;
        AI.takeTurn(g, g.players[0]); g.endTurn();
        const majors = g.players.filter(p => p.alive && !p.isMinor && !p.isBarb);
        const anyWar = majors.some(p => [...p.atWarWith].some(i => g.players[i].alive &&
          !g.players[i].isMinor && !g.players[i].isBarb));
        if (anyWar) {
          metrics.warTurns++;
          if (gameAttacks === attacksBefore) metrics.quietWarTurns++;
        }
        for (const p of majors) {
          const target = AI.campaignTarget(g, p);
          if (!AI.campaignIsOverseas(g, p, target)) continue;
          metrics.overseasTurns++;
          if (p.hasTech("COMPASS") && g.units.some(u => u.owner === p.index && u.def.naval)) {
            metrics.preparedOverseasTurns++;
          }
        }
      }
    }
    return JSON.stringify(metrics);
  `));

  assert.ok(metrics.shipsBuilt >= 30, "island civilizations should establish expedition fleets");
  assert.ok(metrics.navalAttacks >= 20, "fleets should participate directly in major wars");
  assert.ok(metrics.captures >= 3, "island campaigns should convert pressure into captures");
  assert.ok(metrics.overseasTurns > 0, "the sample should exercise genuine cross-landmass campaigns");
  assert.ok(metrics.preparedOverseasTurns / metrics.overseasTurns >= 0.5,
    "most active overseas campaigns should have Compass and a fleet");
  assert.ok(metrics.quietWarTurns / metrics.warTurns <= 0.4,
    "archipelago wars should not spend most turns completely stalled");
});

test("empire economy forecasts every modifier and matches the applied turn", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 43021,
      mapW: 28, mapH: 22, mapType: "peninsula", noMinors: true, noBarbs: true });
    const p = g.players[0];
    const capital = g.foundCity(g.units.find(u => u.owner === 0 && u.type === "SETTLER"));
    const rivalCity = g.foundCity(g.units.find(u => u.owner === 1 && u.type === "SETTLER"));

    for (const key of Object.keys(POLICY_BRANCHES.CARSIJA.policies)) p.policies.add(key);
    p.policies.add("FRONTIERSMEN");
    p.goldenAgeTurns = 3;
    for (const tile of g.map.tiles) {
      if (tile.owner === 0 && tile.resource && RESOURCE[tile.resource].luxury) tile.resource = null;
    }
    const luxuryTile = g.map.tiles.find(tile => tile.owner === 0 && !tile.city);
    luxuryTile.resource = "WINE";

    while (g.units.filter(u => u.owner === 0).length < 11) {
      g.units.push(new Unit("WORKER", 0, capital.c, capital.r));
    }
    g.routes.push({ owner: 0, fromId: capital.id, toId: rivalCity.id,
      path: [[capital.c, capital.r]], ends: g.turn + 10 });

    const minor = new Player(g.players.length, "RAGUSA", false);
    minor.visible = new Uint8Array(g.map.w * g.map.h);
    g.players.push(minor);
    p.influence[minor.index] = 100;

    p.faith = 1000;
    const religion = g.availableReligionNames()[0];
    g.foundReligion(0, religion.name, religion.icon, "TITHE");
    rivalCity.religion = p.religionId;
    p.gold = 10000;
    p.scienceStored = 0;
    p.culture = 0;

    const forecast = g.empireEconomy(0);
    const routeGold = g.routeIncome(capital, rivalCity);
    const before = { gold: p.gold, science: p.scienceStored, faith: p.faith, culture: p.culture };
    g.processPlayerEconomy(p);
    return JSON.stringify({
      forecast, routeGold,
      delta: { gold: p.gold - before.gold, science: p.scienceStored - before.science,
        faith: p.faith - before.faith, culture: p.culture - before.culture },
    });
  `));

  const e = result.forecast;
  assert.equal(e.cities, 1);
  assert.equal(e.units, 11);
  assert.equal(e.freeUnits, 8);
  assert.equal(e.maintenance, 3);
  assert.equal(e.goldenAgeGold, Math.floor(e.cityGold * 1.2) - e.cityGold);
  assert.equal(e.tradeGold, result.routeGold);
  assert.equal(e.guildGold, 1);
  assert.equal(e.carsijaGold, 2);
  assert.equal(e.cityStateGold, 4);
  assert.equal(e.titheGold, 2);
  assert.equal(e.grossGold, e.cityGold + e.goldenAgeGold + e.tradeGold + e.guildGold +
    e.carsijaGold + e.cityStateGold + e.titheGold);
  assert.equal(e.netGold, e.grossGold - e.maintenance);
  assert.deepEqual(result.delta,
    { gold: e.netGold, science: e.science, faith: e.faith, culture: e.culture });
});

test("long AI simulations preserve core state invariants", () => {
  const result = evaluate(loadGameContext(), `
    const failures = [];
    const seeds = [7, 19, 73, 211, 997];
    for (const seed of seeds) {
      const g = new Game({ playerCiv: "BULGARIA", numOpponents: 4, seed,
        mapW: 34, mapH: 26, mapType: seed % 2 ? "peninsula" : "archipelago", difficulty: "normal" });
      for (let step = 0; step < 60 && !g.over; step++) {
        AI.takeTurn(g, g.players[0]);
        g.endTurn();
        const occupied = new Set();
        for (const u of g.units) {
          if (!g.tile(u.c, u.r)) failures.push(seed + ": unit outside map");
          if (!Number.isFinite(u.hp) || u.hp <= 0 || u.hp > 100) failures.push(seed + ": invalid unit HP");
          if (!u.isCivilian) {
            const key = u.c + "," + u.r;
            if (occupied.has(key)) failures.push(seed + ": stacked combat units at " + key);
            occupied.add(key);
          }
        }
        for (const city of g.cities) {
          const tile = g.tile(city.c, city.r);
          if (!tile || tile.city !== city || city.owner < 0 || !g.players[city.owner])
            failures.push(seed + ": invalid city ownership/reference");
          if (!city.producing && city.queue.length)
            failures.push(seed + ": city has an orphaned production queue");
        }
        for (const p of g.players) {
          if (![p.gold, p.scienceStored, p.faith, p.culture].every(Number.isFinite))
            failures.push(seed + ": non-finite player economy");
          for (const enemy of p.atWarWith) {
            if (!g.players[enemy] || !g.players[enemy].alive) failures.push(seed + ": invalid war target");
            else if (!g.players[enemy].atWarWith.has(p.index)) failures.push(seed + ": asymmetric war");
          }
          for (const ally of p.pacts) {
            if (!g.players[ally] || !g.players[ally].alive) failures.push(seed + ": invalid pact target");
            else if (!g.players[ally].pacts.has(p.index)) failures.push(seed + ": asymmetric pact");
          }
          for (const deal of p.deals) if (!g.players[deal.other] || !g.players[deal.other].alive)
            failures.push(seed + ": deal with defeated player");
          if (!p.alive && (p.atWarWith.size || p.pacts.size || p.deals.length))
            failures.push(seed + ": defeated player retained diplomatic state");
        }
        for (const route of g.routes) {
          const from = g.cities.find(c => c.id === route.fromId);
          const to = g.cities.find(c => c.id === route.toId);
          if (!g.players[route.owner] || !g.players[route.owner].alive || !from || !to || from.owner !== route.owner)
            failures.push(seed + ": invalid trade route state");
        }
        if (failures.length) break;
      }
      const restored = Game.deserialize(g.serialize());
      if (restored.turn !== g.turn || restored.players.length !== g.players.length ||
          restored.cities.length !== g.cities.length || restored.units.length !== g.units.length)
        failures.push(seed + ": save round-trip changed collection sizes");
    }
    return failures;
  `);
  assert.deepEqual(Array.from(result), []);
});

test("standard-game victory routes stay inside deterministic balance bands", () => {
  const outcomes = JSON.parse(evaluate(loadGameContext(), `
    const results = [];
    for (let seed = 1; seed <= 8; seed++) {
      const g = new Game({ playerCiv: CIV_IDS[seed % CIV_IDS.length], playerLeader: seed % 3,
        numOpponents: 4, seed: seed * 7919, mapW: 34, mapH: 26,
        mapType: seed % 3 === 0 ? "archipelago" : "peninsula", difficulty: "normal" });
      while (!g.over && g.turn <= g.maxTurns + 2) {
        AI.takeTurn(g, g.players[0]);
        g.endTurn();
      }
      results.push({ turn: g.turn, type: g.victoryType, winner: g.winner });
    }
    return JSON.stringify(results);
  `));

  assert.equal(outcomes.length, 8);
  assert.ok(outcomes.every(o => o.type && o.winner !== null), "every sampled game should resolve");
  assert.ok(outcomes.every(o => o.turn >= 100 && o.turn <= 301), "victories should land in the mid or late game");
  const counts = new Map();
  for (const o of outcomes) counts.set(o.type, (counts.get(o.type) || 0) + 1);
  assert.ok(counts.size >= 2, "the sample should exercise more than one victory route");
  assert.ok(Math.max(...counts.values()) <= 6, "no route should take more than 75% of the reviewed sample");
});

test("scenario openings stay inside their reviewed military balance bands", () => {
  const metrics = evaluate(loadGameContext(), `
    return Object.entries(SCENARIOS).map(([key, sc]) => {
      const g = new Game({ playerCiv: sc.playerCiv, fixedOpponents: sc.opponents,
        numOpponents: sc.opponents.length, seed: sc.seed, mapType: sc.mapType,
        difficulty: sc.difficulty, scenario: key, noMinors: true });
      const majors = g.players.filter(p => !p.isMinor && !p.isBarb);
      const mine = Math.round(g.militaryPower(0));
      const strongestFoe = Math.round(Math.max(...majors.slice(1).map(p => g.militaryPower(p.index))));
      for (let i = 0; i < 20 && !g.over; i++) {
        AI.takeTurn(g, g.players[0]);
        g.endTurn();
      }
      return { key, mine, strongestFoe, ratio: mine / Math.max(1, strongestFoe),
        turn: g.turn, over: g.over, winner: g.winner,
        objective: g.scenarioStatus(), cities: g.cities.filter(c => c.owner === 0).length };
    });
  `);
  const expected = {
    SAMUIL_976: [42, 30], FALL_1453: [120, 81], DUSHAN_1346: [76, 42],
    SIMEON_893: [55, 27], BASIL_1014: [67, 42], TOMISLAV_925: [51, 61],
    VLAD_1462: [100, 110], TVRTKO_1377: [52, 8], SKANDERBEG_1443: [84, 74],
  };
  for (const metric of metrics) {
    assert.deepEqual([metric.mine, metric.strongestFoe], expected[metric.key], `${metric.key} opening power changed`);
    assert.ok(metric.ratio >= 0.75 && metric.ratio <= 7, `${metric.key} opens outside the playable power band`);
    assert.ok(metric.turn > 3, `${metric.key} terminated before meaningful play`);
    assert.ok(metric.objective || metric.over, `${metric.key} lost its objective tracker`);
    assert.ok(metric.cities >= 1, `${metric.key} failed to establish a player city`);
  }
});

test("combat reports preserve damage accounting and notify human defenders", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, numHumans: 2,
      seed: 8181, mapW: 24, mapH: 18, mapType: "peninsula", difficulty: "normal" });
    g.units = [];
    g.cities = [];
    g.camps = [];
    for (const tile of g.map.tiles) {
      tile.city = null; tile.owner = -1; tile.workedBy = null;
    }
    let pair = null;
    for (const tile of g.map.tiles) {
      if (!TERRAIN[tile.terrain].passable) continue;
      const next = HEX.neighbors(tile.c, tile.r).map(([c, r]) => g.tile(c, r))
        .find(t => t && TERRAIN[t.terrain].passable);
      if (next) { pair = [tile, next]; break; }
    }
    if (!pair) throw new Error("test map did not contain adjacent land");
    pair[0].terrain = "GRASSLAND"; pair[0].feature = null;
    pair[1].terrain = "GRASSLAND"; pair[1].feature = null;
    const attacker = g.addUnit("WARRIOR", 0, pair[0].c, pair[0].r);
    const defender = g.addUnit("WARRIOR", 1, pair[1].c, pair[1].r);
    g.players[0].atWarWith.add(1);
    g.players[1].atWarWith.add(0);
    const ok = g.attack(attacker, defender.c, defender.r);
    return JSON.stringify({ ok, report: g.lastCombat,
      defenderNotices: g.notifications.filter(n => n.p === 1).map(n => n.msg) });
  `));

  assert.equal(result.ok, true);
  assert.equal(result.report.attackerOwner, 0);
  assert.equal(result.report.targetOwner, 1);
  assert.equal(result.report.attackerName, "Warrior");
  assert.equal(result.report.targetName, "Warrior");
  assert.equal(result.report.targetKind, "unit");
  assert.ok(result.report.damage > 0);
  assert.ok(result.report.counterDamage > 0);
  assert.equal(result.report.attackerHpAfter, 100 - result.report.counterDamage);
  assert.equal(result.report.targetHpAfter, 100 - result.report.damage);
  assert.match(result.defenderNotices.at(-1), /Serbia Warrior dealt \d+ damage/);
});

test("capturing the last city resets production and retires defeated-player state", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 2, seed: 8844,
      mapW: 28, mapH: 22, mapType: "peninsula", noMinors: true, noBarbs: true });
    for (const p of g.players) {
      const settler = g.units.find(u => u.owner === p.index && u.type === "SETTLER");
      if (!g.foundCity(settler)) throw new Error("could not found conquest test city");
    }
    const home = g.cities.find(c => c.owner === 0);
    const captured = g.cities.find(c => c.owner === 1);
    const survivor = g.cities.find(c => c.owner === 2);
    home.producing = { kind: "unit", key: "WARRIOR" };
    captured.producing = { kind: "unit", key: "WARRIOR" };
    captured.queue = [{ kind: "building", key: "MONUMENT" }];
    captured.prodStored = 31;

    g.players[0].atWarWith.add(1); g.players[1].atWarWith.add(0);
    g.players[1].pacts.add(2); g.players[2].pacts.add(1);
    g.players[1].deals.push({ give: "WINE", get: "SALT", other: 2, ends: 30 });
    g.players[2].deals.push({ give: "SALT", get: "WINE", other: 1, ends: 30 });
    g.offerPeace(1, 0);
    g.routes.push({ owner: 1, fromId: captured.id, toId: survivor.id, path: [], ends: 30 });
    g.routes.push({ owner: 2, fromId: survivor.id, toId: captured.id, path: [], ends: 30 });

    const attacker = g.units.find(u => u.owner === 0 && !u.isCivilian);
    g.captureCity(captured, attacker);
    const defeated = g.players[1];
    return JSON.stringify({
      captured: { owner: captured.owner, producing: captured.producing,
        queue: captured.queue, prodStored: captured.prodStored },
      pendingCityIds: g.pendingOrders(0).cities.map(c => c.id),
      defeated: { alive: defeated.alive, wars: [...defeated.atWarWith],
        pacts: [...defeated.pacts], deals: defeated.deals },
      survivor: { atWar: g.players[0].atWarWith.has(1), pact: g.players[2].pacts.has(1),
        deal: g.players[2].deals.some(d => d.other === 1) },
      routes: g.routes.map(r => ({ owner: r.owner, fromId: r.fromId, toId: r.toId })),
      staleOffers: g.peaceOffers.filter(o => o.from === 1 || o.to === 1).length,
      orphanedTiles: g.map.tiles.filter(t => t.owner === 1).length,
      defeatedEconomy: g.empireEconomy(1),
      capturedId: captured.id, survivorId: survivor.id,
    });
  `));

  assert.deepEqual(result.captured, { owner: 0, producing: null, queue: [], prodStored: 0 });
  assert.deepEqual(result.pendingCityIds, [result.capturedId]);
  assert.deepEqual(result.defeated, { alive: false, wars: [], pacts: [], deals: [] });
  assert.deepEqual(result.survivor, { atWar: false, pact: false, deal: false });
  assert.deepEqual(result.routes, [{ owner: 2,
    fromId: result.survivorId, toId: result.capturedId }]);
  assert.equal(result.staleOffers, 0);
  assert.equal(result.orphanedTiles, 0);
  assert.deepEqual(result.defeatedEconomy, {
    cities: 0, population: 0, units: 0, freeUnits: 4,
    food: 0, production: 0, science: 0, culture: 0, faith: 0,
    cityGold: 0, goldenAgeGold: 0, tradeGold: 0, guildGold: 0,
    carsijaGold: 0, cityStateGold: 0, titheGold: 0,
    maintenance: 0, grossGold: 0, netGold: 0,
  });
});

test("city founding enforces unit, movement, territory, and spacing rules", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 49117,
      mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    const settler = g.units.find(u => u.owner === 0 && u.type === "SETTLER");
    const warrior = g.units.find(u => u.owner === 0 && u.type === "WARRIOR");
    const start = g.tile(settler.c, settler.r);
    const originalOwner = start.owner;

    start.owner = 1;
    g.players[1].alive = false;
    const retiredStatus = g.citySiteStatus(settler.c, settler.r, settler.owner);
    g.players[1].alive = true;
    const foreignStatus = g.citySiteStatus(settler.c, settler.r, settler.owner);
    const foreignFound = g.foundCity(settler);
    start.owner = originalOwner;

    settler.moves = 0;
    const spentFound = g.foundCity(settler);
    settler.moves = settler.def.moves;
    const imposterFound = g.foundCity(warrior);
    const city = g.foundCity(settler);

    const closeTile = HEX.ring(city.c, city.r, 2)
      .map(([c, r]) => g.tile(c, r))
      .find(t => t && !t.city && TERRAIN[t.terrain].passable);
    const second = g.addUnit("SETTLER", 0, closeTile.c, closeTile.r);
    const closeStatus = g.citySiteStatus(second.c, second.r, second.owner);
    const closeFound = g.foundCity(second);

    return JSON.stringify({
      foreign: { retiredClaimable: retiredStatus.ok, code: foreignStatus.code, found: !!foreignFound },
      spentFound: !!spentFound, imposterFound: !!imposterFound,
      first: { founded: !!city, owner: city && city.owner,
        settlerRemoved: !g.units.includes(settler) },
      close: { code: closeStatus.code, blockingCityId: closeStatus.blockingCityId,
        found: !!closeFound, settlerPresent: g.units.includes(second) },
    });
  `));

  assert.deepEqual(result.foreign,
    { retiredClaimable: true, code: "FOREIGN_TERRITORY", found: false });
  assert.equal(result.spentFound, false);
  assert.equal(result.imposterFound, false);
  assert.deepEqual(result.first, { founded: true, owner: 0, settlerRemoved: true });
  assert.equal(result.close.code, "TOO_CLOSE");
  assert.ok(result.close.blockingCityId);
  assert.equal(result.close.found, false);
  assert.equal(result.close.settlerPresent, true);
});

test("production commands enforce prerequisites, ownership, uniqueness, and spawn space", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 61221,
      mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    const mine = g.units.find(u => u.owner === 0 && u.type === "SETTLER");
    const theirs = g.units.find(u => u.owner === 1 && u.type === "SETTLER");
    const city = g.foundCity(mine);
    const foreignCity = g.foundCity(theirs);
    const p = g.players[0];
    p.gold = 10000;
    const startingGold = p.gold;

    const lockedPurchase = g.purchase(city, { kind: "unit", key: "RIFLEMAN" }, 0);
    const goldAfterLockedPurchase = p.gold;
    const foreignCommand = g.setCityProduction(foreignCity,
      { kind: "unit", key: "WARRIOR" }, false, 0);
    const firstMonument = g.purchase(city, { kind: "building", key: "MONUMENT" }, 0);
    const goldAfterMonument = p.gold;
    const duplicateMonument = g.purchase(city, { kind: "building", key: "MONUMENT" }, 0);

    for (const u of [...g.units]) if (u.owner === 0) g.removeUnit(u);
    const occupied = [[city.c, city.r], ...HEX.neighbors(city.c, city.r)]
      .filter(([c, r]) => g.tile(c, r));
    const blockers = [];
    for (const [c, r] of occupied) {
      const tile = g.tile(c, r);
      tile.terrain = "GRASSLAND";
      blockers.push(g.addUnit("WARRIOR", 0, c, r));
    }
    city.producing = { kind: "unit", key: "WARRIOR" };
    city.queue = [];
    city.prodStored = UNITS.WARRIOR.cost;
    const notificationCount = g.notifications.length;
    const unitCount = g.units.length;
    g.processCityTurn(city);
    const blocked = {
      producing: city.producing && city.producing.key,
      stored: city.prodStored,
      unitsAdded: g.units.length - unitCount,
      notificationsAdded: g.notifications.length - notificationCount,
    };

    const released = blockers.find(u => u.c !== city.c || u.r !== city.r);
    g.removeUnit(released);
    const beforeRelease = g.units.length;
    const notificationsBeforeRelease = g.notifications.length;
    g.processCityTurn(city);
    const completed = {
      producing: city.producing,
      unitsAdded: g.units.length - beforeRelease,
      notificationsAdded: g.notifications.length - notificationsBeforeRelease,
      warriorAtReleasedTile: !!g.units.find(u => u.owner === 0 && u.type === "WARRIOR" &&
        u.c === released.c && u.r === released.r),
    };

    return JSON.stringify({
      lockedPurchase, foreignCommand, firstMonument, duplicateMonument,
      lockedCost: startingGold - goldAfterLockedPurchase,
      monumentCost: startingGold - goldAfterMonument,
      monuments: city.buildings.filter(key => key === "MONUMENT").length,
      blocked, completed,
    });
  `));

  assert.equal(result.lockedPurchase, false);
  assert.equal(result.foreignCommand, false);
  assert.equal(result.firstMonument, true);
  assert.equal(result.duplicateMonument, false);
  assert.equal(result.lockedCost, 0);
  assert.equal(result.monumentCost, 135);
  assert.equal(result.monuments, 1);
  assert.deepEqual(result.blocked,
    { producing: "WARRIOR", stored: 40, unitsAdded: 0, notificationsAdded: 0 });
  assert.deepEqual(result.completed,
    { producing: null, unitsAdded: 1, notificationsAdded: 1, warriorAtReleasedTile: true });
});

test("unit orders enforce turn ownership and cannot refund Worker movement or strand an empire", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, numHumans: 2,
      seed: 77221, mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    const p = g.players[0];
    const warrior = g.units.find(u => u.owner === 0 && u.type === "WARRIOR");
    const settler = g.units.find(u => u.owner === 0 && u.type === "SETTLER");
    const startingMoves = warrior.moves;

    g.activeHuman = 1;
    const outOfTurnStatus = g.unitOrderStatus(warrior, "skip", 0);
    const outOfTurn = g.issueUnitOrder(warrior, "skip", 0);
    const foreignStatus = g.unitOrderStatus(warrior, "skip", 1);
    const foreign = g.issueUnitOrder(warrior, "skip", 1);
    const movesAfterRejectedOrders = warrior.moves;

    g.activeHuman = 0;
    warrior.promoPts = 1;
    const promoted = g.issueUnitOrder(warrior, "promote", 0, "MIGHT");
    warrior.promoPts = 1;
    const duplicatePromotion = g.issueUnitOrder(warrior, "promote", 0, "MIGHT");
    const promotionState = { promos: [...warrior.promos], points: warrior.promoPts };

    warrior.moves = warrior.def.moves;
    const fortified = g.issueUnitOrder(warrior, "fortify", 0);
    const fortifiedState = { fortified: warrior.fortified, moves: warrior.moves };
    const woke = g.issueUnitOrder(warrior, "wake", 0);
    warrior.hp = 42;
    warrior.moves = warrior.def.moves;
    const healing = g.issueUnitOrder(warrior, "heal", 0);
    const healingState = { fortified: warrior.fortified, healing: warrior.healFortify, moves: warrior.moves };
    g.issueUnitOrder(warrior, "wake", 0);

    const scout = g.addUnit("SCOUT", 0, warrior.c, warrior.r);
    const wrongAutoUnit = g.issueUnitOrder(warrior, "auto_explore", 0, true);
    const autoStarted = g.issueUnitOrder(scout, "auto_explore", 0, true);
    const autoStopped = g.issueUnitOrder(scout, "auto_explore", 0, false);

    const workTile = g.tile(warrior.c, warrior.r);
    Object.assign(workTile, { owner: 0, terrain: "HILLS", feature: null,
      resource: null, improvement: null, city: null });
    p.techs.add("MINING");
    const worker = g.addUnit("WORKER", 0, workTile.c, workTile.r);
    const jobStarted = g.startImprovement(worker, "MINE", 0);
    const cancelled = g.issueUnitOrder(worker, "cancel_job", 0);
    const jobRestarted = g.startImprovement(worker, "MINE", 0);
    const workerState = { job: worker.building, moves: worker.moves };

    const lastSettlerStatus = g.unitOrderStatus(settler, "disband", 0);
    const lastSettlerDisbanded = g.issueUnitOrder(settler, "disband", 0);
    const settlerStillPresent = g.units.includes(settler);
    const city = g.foundCity(settler, 0);
    const spareSettler = g.addUnit("SETTLER", 0, city.c, city.r);
    const spareDisbanded = g.issueUnitOrder(spareSettler, "disband", 0);

    warrior.moves = warrior.def.moves;
    const skipped = g.issueUnitOrder(warrior, "skip", 0);
    return JSON.stringify({
      rejected: { outOfTurn: outOfTurnStatus.code, foreign: foreignStatus.code,
        outOfTurnIssued: outOfTurn, foreignIssued: foreign,
        startingMoves, movesAfterRejectedOrders },
      promotion: { promoted, duplicatePromotion, ...promotionState },
      fortify: { fortified, woke, ...fortifiedState },
      heal: { healing, ...healingState },
      auto: { wrongAutoUnit, autoStarted, autoStopped, active: scout.autoExplore },
      worker: { jobStarted, cancelled, jobRestarted, ...workerState },
      settler: { code: lastSettlerStatus.code, lastSettlerDisbanded,
        settlerStillPresent, cityFounded: !!city, spareDisbanded,
        sparePresent: g.units.includes(spareSettler), alive: p.alive },
      skipped: { ok: skipped, moves: warrior.moves },
    });
  `));

  assert.deepEqual(result.rejected,
    { outOfTurn: "NOT_ACTIVE", foreign: "FOREIGN_UNIT", outOfTurnIssued: false,
      foreignIssued: false, startingMoves: 2, movesAfterRejectedOrders: 2 });
  assert.deepEqual(result.promotion,
    { promoted: true, duplicatePromotion: false, promos: ["MIGHT"], points: 1 });
  assert.deepEqual(result.fortify,
    { fortified: true, woke: true, moves: 0 });
  assert.deepEqual(result.heal,
    { healing: true, fortified: true, moves: 0 });
  assert.deepEqual(result.auto,
    { wrongAutoUnit: false, autoStarted: true, autoStopped: true, active: false });
  assert.deepEqual(result.worker,
    { jobStarted: true, cancelled: true, jobRestarted: false, job: null, moves: 0 });
  assert.deepEqual(result.settler,
    { code: "LAST_SETTLER", lastSettlerDisbanded: false, settlerStillPresent: true,
      cityFounded: true, spareDisbanded: true, sparePresent: false, alive: true });
  assert.deepEqual(result.skipped, { ok: true, moves: 0 });
});

test("city focus assigns strategic yields without double-working shared tiles", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 81717,
      mapW: 24, mapH: 18, mapType: "peninsula", noMinors: true, noBarbs: true });
    const settler = g.units.find(u => u.owner === 0 && u.type === "SETTLER");
    const city = g.foundCity(settler);
    const candidates = HEX.ring(city.c, city.r, 3)
      .map(([c, r]) => g.tile(c, r))
      .filter(t => t && !t.city);
    for (const tile of candidates) {
      tile.owner = 0;
      tile.terrain = "MOUNTAIN";
      tile.feature = null;
      tile.resource = null;
      tile.improvement = null;
    }
    const featured = candidates.slice(0, 3);
    Object.assign(featured[0], { terrain: "GRASSLAND", resource: "WHEAT" });
    Object.assign(featured[1], { terrain: "HILLS", resource: "IRON" });
    Object.assign(featured[2], { terrain: "PLAINS", resource: "WINE" });
    city.pop = 1;

    const choose = focus => {
      g.setCityFocus(city, focus, 0);
      const tile = g.workedTiles(city)[0];
      return { focus: city.focus, terrain: tile.terrain, resource: tile.resource,
        yields: g.cityYields(city) };
    };
    const growth = choose("growth");
    const production = choose("production");
    const gold = choose("gold");

    const site = candidates.find(t => HEX.distance(city.c, city.r, t.c, t.r) === 3);
    const second = new City("Nis", 0, site.c, site.r);
    second.pop = 3;
    second.focus = "production";
    city.pop = 3;
    city.focus = "growth";
    g.cities.push(second);
    site.city = second;
    for (const [c, r] of HEX.ring(second.c, second.r, 3)) {
      const tile = g.tile(c, r);
      if (tile) tile.owner = 0;
    }
    g.assignWorkedTiles(0);
    const firstTiles = g.workedTiles(city).map(t => t.c + "," + t.r);
    const secondTiles = g.workedTiles(second).map(t => t.c + "," + t.r);
    const overlap = firstTiles.filter(key => secondTiles.includes(key));
    const restored = Game.deserialize(g.serialize());

    return JSON.stringify({ growth, production, gold,
      allocation: { first: firstTiles.length, second: secondTiles.length, overlap },
      savedFocus: restored.cities.find(c => c.id === city.id).focus });
  `));

  assert.deepEqual([result.growth.terrain, result.growth.resource], ["GRASSLAND", "WHEAT"]);
  assert.deepEqual([result.production.terrain, result.production.resource], ["HILLS", "IRON"]);
  assert.deepEqual([result.gold.terrain, result.gold.resource], ["PLAINS", "WINE"]);
  assert.ok(result.growth.yields.food > result.production.yields.food);
  assert.ok(result.production.yields.prod > result.growth.yields.prod);
  assert.ok(result.gold.yields.gold > result.growth.yields.gold);
  assert.deepEqual(result.allocation, { first: 3, second: 3, overlap: [] });
  assert.equal(result.savedFocus, "growth");
});

test("pending-order snapshots track research, production, and unit decisions", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const g = new Game({ playerCiv: "SERBIA", numOpponents: 1, seed: 9191,
      mapW: 24, mapH: 18, mapType: "peninsula", difficulty: "normal" });
    const initial = g.pendingOrders(0);
    g.players[0].researching = g.players[0].availableTechs()[0];
    const settler = g.units.find(u => u.owner === 0 && u.type === "SETTLER");
    const city = g.foundCity(settler);
    for (const unit of g.units) if (unit.owner === 0) unit.moves = 0;
    const needsProduction = g.pendingOrders(0);
    city.producing = { kind: "unit", key: "WARRIOR" };
    const ready = g.pendingOrders(0);
    return JSON.stringify({
      initial: { research: initial.research, cities: initial.cities.length, units: initial.units.length },
      needsProduction: { research: needsProduction.research, cities: needsProduction.cities.length,
        units: needsProduction.units.length, cityId: needsProduction.cities[0] && needsProduction.cities[0].id },
      ready: { research: ready.research, cities: ready.cities.length, units: ready.units.length },
      foundedCityId: city.id,
    });
  `));

  assert.equal(result.initial.research, true);
  assert.equal(result.initial.cities, 0);
  assert.ok(result.initial.units >= 2);
  assert.deepEqual(result.needsProduction, {
    research: false, cities: 1, units: 0, cityId: result.foundedCityId,
  });
  assert.deepEqual(result.ready, { research: false, cities: 0, units: 0 });
});

test("save round-trips preserve the exact deterministic future", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const advance = (g, turns) => {
      for (let i = 0; i < turns && !g.over; i++) {
        AI.takeTurn(g, g.players[0]);
        g.endTurn();
      }
    };
    const g = new Game({ playerCiv: "MACEDONIA", numOpponents: 4, seed: 737373,
      mapW: 34, mapH: 26, mapType: "archipelago", difficulty: "hard" });
    advance(g, 18);
    g.stats.routes = 3;
    const saved = g.serialize();
    const saveData = JSON.parse(saved);
    advance(g, 24);
    const uninterrupted = g.serialize();

    const resumed = Game.deserialize(saved);
    advance(resumed, 24);
    const afterResume = resumed.serialize();

    const legacy = JSON.parse(saved);
    delete legacy.rngState;
    legacy.v = 1;
    const oldSave = Game.deserialize(JSON.stringify(legacy));
    const expectedLegacyRng = mulberry32((legacy.seed + legacy.turn * 7919) >>> 0)();
    return JSON.stringify({
      version: saveData.v,
      rngState: saveData.rngState,
      stats: saveData.stats,
      exact: uninterrupted === afterResume,
      legacyRng: oldSave.rng(),
      expectedLegacyRng,
    });
  `));

  assert.equal(result.version, 2);
  assert.ok(Number.isInteger(result.rngState));
  assert.equal(result.stats.routes, 3);
  assert.equal(result.exact, true);
  assert.equal(result.legacyRng, result.expectedLegacyRng);
});

test("scientific and religious victories enforce their complete requirements", () => {
  const result = JSON.parse(evaluate(loadGameContext(), `
    const science = new Game({ playerCiv: "BULGARIA", numOpponents: 2, seed: 1414,
      mapW: 28, mapH: 22, mapType: "peninsula", noMinors: true });
    science.players[0].techs = new Set(Object.keys(TECHS));
    science.checkVictory();

    const religion = new Game({ playerCiv: "BYZANTIUM", numOpponents: 5, seed: 1515,
      mapW: 40, mapH: 30, mapType: "peninsula", noMinors: true });
    for (const p of religion.players.filter(p => !p.isMinor && !p.isBarb)) {
      const settler = religion.units.find(u => u.owner === p.index && u.type === "SETTLER");
      if (!religion.foundCity(settler)) throw new Error("could not found test city");
    }
    religion.players[0].faith = 1000;
    const faith = religion.availableReligionNames()[0];
    religion.foundReligion(0, faith.name, faith.icon, Object.keys(BELIEFS)[0]);
    const rid = religion.players[0].religionId;
    religion.players[0].missionarySpreads = RELIGION_VICTORY.minSpreads;
    const majorCities = religion.cities.filter(c => !religion.players[c.owner].isMinor);
    for (const city of majorCities) city.religion = rid;
    const oneFaithOnly = religion.religiousVictoryProgress(0);
    religion.players[1].faith = 1000;
    const rivalFaith = religion.availableReligionNames()[0];
    religion.foundReligion(1, rivalFaith.name, rivalFaith.icon, Object.keys(BELIEFS)[1]);
    for (const city of majorCities.slice(0, 5)) city.religion = rid;
    majorCities[5].religion = religion.players[1].religionId;
    const guarded = religion.religiousVictoryProgress(0);
    religion.checkVictory();
    const beforeCoverage = religion.over;
    majorCities[5].religion = rid;
    const complete = religion.religiousVictoryProgress(0);
    religion.checkVictory();
    const overview = religion.victoryProgress(0);

    return JSON.stringify({
      science: { over: science.over, winner: science.winner, type: science.victoryType },
      oneFaithOnly, guarded, beforeCoverage, complete,
      religion: { over: religion.over, winner: religion.winner, type: religion.victoryType },
      overview: { science: overview.science, culture: overview.culture,
        domination: overview.domination, religion: overview.religion },
    });
  `));

  assert.deepEqual(result.science, { over: true, winner: 0, type: "Scientific" });
  assert.equal(result.oneFaithOnly.religions, 1);
  assert.equal(result.oneFaithOnly.religionTarget, 2);
  assert.equal(result.oneFaithOnly.complete, false);
  assert.equal(result.guarded.current, 5);
  assert.equal(result.guarded.target, 4);
  assert.equal(result.guarded.civs, 5);
  assert.equal(result.guarded.civTarget, 6);
  assert.equal(result.guarded.religions, 2);
  assert.equal(result.guarded.spreads, 6);
  assert.equal(result.guarded.complete, false);
  assert.equal(result.beforeCoverage, false);
  assert.equal(result.complete.complete, true);
  assert.deepEqual(result.religion, { over: true, winner: 0, type: "Religious" });
  assert.equal(result.overview.religion.current, 6);
  assert.equal(result.overview.religion.civs, 6);
  assert.ok(result.overview.science.target > result.overview.science.current);
  assert.equal(result.overview.culture.target, 3);
  assert.equal(result.overview.domination.target, 6);
});

test("AI victory focus follows the selected leader's strengths", () => {
  const focuses = JSON.parse(evaluate(loadGameContext(), `
    const focus = (civ, leader) => {
      const p = new Player(0, civ, false);
      p.leaderIdx = leader;
      return AI.victoryFocus(p);
    };
    return JSON.stringify({
      simeon: focus("BULGARIA", 0),
      boris: focus("BULGARIA", 2),
      nemanja: focus("SERBIA", 1),
      kresimir: focus("CROATIA", 1),
      skanderbeg: focus("ALBANIA", 0),
    });
  `));

  assert.deepEqual(focuses, {
    simeon: "science",
    boris: "religion",
    nemanja: "culture",
    kresimir: "diplomacy",
    skanderbeg: "domination",
  });
});
