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
        }
        for (const p of g.players) {
          if (![p.gold, p.scienceStored, p.faith, p.culture].every(Number.isFinite))
            failures.push(seed + ": non-finite player economy");
          for (const enemy of p.atWarWith) if (!g.players[enemy]) failures.push(seed + ": invalid war target");
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
