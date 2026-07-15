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
