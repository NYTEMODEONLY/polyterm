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

test("fixed-seed AI simulations produce an identical strategic fingerprint", () => {
  const first = evaluate(loadGameContext(), simulationSource);
  const second = evaluate(loadGameContext(), simulationSource);
  assert.equal(second, first);
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
