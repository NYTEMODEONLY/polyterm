// ============================================================
// AI players: settling, production, research, war, tactics
// ============================================================
"use strict";

const AI = (() => {

  function takeTurn(game, p) {
    if (p.isMinor) {
      chooseResearch(game, p);
      runMinorCities(game, p);
      runUnits(game, p);
      return;
    }
    diplomacy(game, p);
    religion(game, p);
    espionage(game, p);
    chooseResearch(game, p);
    runCities(game, p);
    runUnits(game, p);
  }

  // ---------- espionage ----------
  function espionage(game, p) {
    for (const spy of p.spies) {
      if (spy.deadUntil > game.turn || spy.cityId !== null) continue;
      // 1) keep one counterspy in the capital
      const cap = game.cities.find(c => c.owner === p.index && c.isCapital) ||
                  game.cities.find(c => c.owner === p.index);
      const defending = p.spies.some(s => s !== spy && s.deadUntil <= game.turn && s.cityId &&
        game.cities.some(c => c.id === s.cityId && c.owner === p.index));
      if (cap && !defending) { game.assignSpy(p.index, spy.id, cap.id); continue; }
      // 2) steal from the biggest tech rival
      const rivals = [...p.met].map(i => game.players[i])
        .filter(o => o.alive && !o.isMinor && o.techs.size > p.techs.size)
        .sort((a, b) => b.techs.size - a.techs.size);
      const target = rivals[0];
      if (target) {
        const tc = game.cities.find(c => c.owner === target.index && c.isCapital) ||
                   game.cities.find(c => c.owner === target.index);
        if (tc) { game.assignSpy(p.index, spy.id, tc.id); continue; }
      }
      // 3) otherwise rig a city-state
      const minor = [...p.met].map(i => game.players[i])
        .find(o => o.isMinor && o.alive && !p.atWarWith.has(o.index));
      if (minor) {
        const mc = game.cities.find(c => c.owner === minor.index);
        if (mc) game.assignSpy(p.index, spy.id, mc.id);
      }
    }
  }

  // ---------- religion ----------
  function religion(game, p) {
    if (game.canFoundReligion(p.index)) {
      const names = game.availableReligionNames();
      if (names.length) {
        const pref = names.find(n => n.name === CIV_RELIGION[p.civId]) ||
          names[Math.floor(game.rng() * names.length)];
        const beliefs = Object.keys(BELIEFS);
        game.foundReligion(p.index, pref.name, pref.icon, beliefs[Math.floor(game.rng() * beliefs.length)]);
      }
    }
    // buy a missionary when faith allows (keep a small buffer)
    if (p.religionId !== null && p.faith >= UNITS.MISSIONARY.faithCost + 40) {
      const nMissionaries = game.units.filter(u => u.owner === p.index && u.type === "MISSIONARY").length;
      if (nMissionaries < 2) {
        const home = game.cities.find(c => c.owner === p.index);
        if (home) game.buyMissionary(home);
      }
    }
  }

  function runMinorCities(game, p) {
    const myCities = game.cities.filter(c => c.owner === p.index);
    const military = game.units.filter(u => u.owner === p.index && !u.isCivilian);
    for (const city of myCities) {
      if (city.producing) continue;
      const opts = game.productionOptions(city);
      if (!opts.length) continue;
      const wantMilitary = 2 + p.era() + (p.atWarWith.size ? 2 : 0);
      let choice = null;
      if (military.length < wantMilitary) {
        const mil = opts.filter(o => o.kind === "unit" && !UNITS[o.key].civilian &&
          !UNITS[o.key].naval && o.key !== "SCOUT" && o.key !== "SETTLER");
        mil.sort((a, b) => Math.max(UNITS[b.key].cs, UNITS[b.key].rs || 0) - Math.max(UNITS[a.key].cs, UNITS[a.key].rs || 0));
        choice = mil[0] || null;
      }
      if (!choice) {
        const prio = ["WALLS", "GRANARY", "BARRACKS", "SHRINE", "LIBRARY", "MARKET", "CASTLE",
          "TEMPLE", "AQUEDUCT", "FORGE", "UNIVERSITY", "WORKSHOP", "BANK"];
        for (const key of prio) {
          const o = opts.find(x => x.kind === "building" && x.key === key);
          if (o) { choice = o; break; }
        }
      }
      if (choice) city.producing = { kind: choice.kind, key: choice.key };
    }
  }

  // ---------- diplomacy ----------
  function diplomacy(game, p) {
    // court city-states when rich
    if (p.gold > 350 && game.rng() < 0.15) {
      const minors = [...p.met].filter(i => game.players[i].isMinor && game.players[i].alive &&
        !p.atWarWith.has(i));
      if (minors.length) {
        const pick = minors[Math.floor(game.rng() * minors.length)];
        game.giftInfluence(p.index, pick, 250);
      }
    }
    for (const other of p.met) {
      const o = game.players[other];
      if (!o.alive) continue;
      // conquering city-states happens, but rarely
      if (o.isMinor && !p.atWarWith.has(other) && game.rng() > 0.08) continue;
      if (p.atWarWith.has(other)) {
        // sue for peace if clearly losing or war has dragged on
        const weary = (p.warWeariness[other] || 0) > 25;
        const losing = game.militaryPower(p.index) < game.militaryPower(other) * 0.55;
        if ((weary && game.rng() < 0.2) || (losing && game.rng() < 0.3)) {
          game.makePeace(p.index, other);
        }
      } else {
        // consider declaring war on a weaker neighbour
        const myPower = game.militaryPower(p.index);
        const theirPower = game.militaryPower(other);
        const myCities = game.cities.filter(c => c.owner === p.index);
        const theirCities = game.cities.filter(c => c.owner === other);
        if (!myCities.length || !theirCities.length) continue;
        const near = myCities.some(mc => theirCities.some(tc => HEX.distance(mc.c, mc.r, tc.c, tc.r) <= 9));
        if (near && myPower > theirPower * 1.6 && myPower > 40 && game.rng() < 0.06) {
          game.declareWar(p.index, other);
        }
      }
    }
  }

  // ---------- research ----------
  function chooseResearch(game, p) {
    if (p.researching) return;
    const av = p.availableTechs();
    if (!av.length) return;
    const atWar = p.atWarWith.size > 0;
    const milTechs = ["ARCHERY", "BRONZE_WORKING", "IRON_WORKING", "HORSEBACK_RIDING",
      "CHIVALRY", "STEEL", "MACHINERY", "GUNPOWDER", "MASONRY", "CONSTRUCTION", "PHYSICS", "MATHEMATICS",
      "SAILING", "COMPASS"];
    const ranked = av.sort((a, b) => {
      let sa = TECHS[a].cost, sb = TECHS[b].cost;
      if (atWar) { if (milTechs.includes(a)) sa *= 0.5; if (milTechs.includes(b)) sb *= 0.5; }
      return sa - sb;
    });
    p.researching = ranked[0];
  }

  // ---------- cities / production ----------
  function runCities(game, p) {
    const myCities = game.cities.filter(c => c.owner === p.index);
    const myUnits = game.units.filter(u => u.owner === p.index);
    const military = myUnits.filter(u => !u.isCivilian);
    const settlers = myUnits.filter(u => u.type === "SETTLER");
    const atWar = p.atWarWith.size > 0;
    const wantCities = 4 + Math.floor(game.map.w / 15);
    const wantMilitary = myCities.length * 2 + (atWar ? 4 : 1);

    for (const city of myCities) {
      if (city.producing) continue;
      const opts = game.productionOptions(city);
      if (!opts.length) continue;

      const pick = (pred) => {
        const c = opts.filter(pred);
        return c.length ? c[Math.floor(game.rng() * c.length)] : null;
      };
      const bestMilitary = () => {
        const mil = opts.filter(o => o.kind === "unit" && !UNITS[o.key].civilian &&
          !UNITS[o.key].naval && o.key !== "SCOUT");
        if (!mil.length) return null;
        mil.sort((a, b) => Math.max(UNITS[b.key].cs, UNITS[b.key].rs || 0) - Math.max(UNITS[a.key].cs, UNITS[a.key].rs || 0));
        return mil[Math.floor(game.rng() * Math.min(2, mil.length))];
      };
      const bestShip = () => {
        const ships = opts.filter(o => o.kind === "unit" && UNITS[o.key].naval);
        if (!ships.length) return null;
        ships.sort((a, b) => Math.max(UNITS[b.key].cs, UNITS[b.key].rs || 0) - Math.max(UNITS[a.key].cs, UNITS[a.key].rs || 0));
        return ships[0];
      };

      let choice = null;
      const garrison = game.combatUnitAt(city.c, city.r);
      if (!garrison && military.length < myCities.length) choice = bestMilitary();
      const happiness = game.happinessOf(p.index);
      if (!choice && happiness < 0) {
        // unhappy: happiness buildings before anything else
        choice = opts.find(o => o.kind === "building" && (o.key === "TAVERN" || o.key === "HAMMAM")) || null;
      }
      if (!choice && !atWar && happiness >= 2 && myCities.length + settlers.length < wantCities &&
          city.pop >= 3 && !settlers.length && game.rng() < 0.7) {
        choice = pick(o => o.key === "SETTLER");
      }
      const workers = myUnits.filter(u => u.type === "WORKER");
      if (!choice && workers.length < Math.min(myCities.length, 3) && game.rng() < 0.4) {
        choice = pick(o => o.key === "WORKER");
      }
      const navy = myUnits.filter(u => u.def.naval);
      if (!choice && city.coastal && navy.length < Math.max(1, Math.floor(myCities.length / 2)) &&
          game.rng() < (atWar ? 0.3 : 0.12)) {
        choice = bestShip();
      }
      if (!choice && military.length < wantMilitary && game.rng() < (atWar ? 0.85 : 0.35)) {
        choice = bestMilitary();
      }
      if (!choice) {
        // building priority order
        const prio = ["MONUMENT", "SHRINE", "GRANARY", "LIBRARY", "TAVERN", "WALLS", "MARKET", "BARRACKS",
          "TEMPLE", "HAMMAM", "AQUEDUCT", "FORGE", "UNIVERSITY", "CASTLE", "WORKSHOP", "BANK",
          "DIOCLETIAN", "HIPPODROME", "OHRID_SCHOOL", "STARI_MOST", "MOUNT_ATHOS", "BRAN_CASTLE",
          "HAGIA_SOPHIA", "STUDENICA", "RILA", "KALEMEGDAN"];
        for (const key of prio) {
          const o = opts.find(x => x.kind === "building" && x.key === key);
          if (o) { choice = o; break; }
        }
      }
      if (!choice) choice = bestMilitary() || opts[0];
      city.producing = { kind: choice.kind, key: choice.key };
    }
  }

  // ---------- unit control ----------
  function runUnits(game, p) {
    const myUnits = game.units.filter(u => u.owner === p.index);
    for (const u of myUnits) {
      if (!game.units.includes(u)) continue; // died mid-loop
      if (u.type === "SETTLER") runSettler(game, p, u);
      else if (u.type === "WORKER") runWorker(game, p, u);
      else if (u.type === "MISSIONARY") runMissionary(game, p, u);
      else if (u.type === "SCOUT") runScout(game, p, u);
      else if (u.def.naval) runShip(game, p, u);
      else if (!u.isCivilian) runMilitary(game, p, u);
    }
  }

  function runSettler(game, p, u) {
    // found here if it's a decent spot, else walk toward the best nearby site
    const hereScore = siteScore(game.map, u.c, u.r);
    const myCities = game.cities.filter(c => c.owner === p.index);
    const farEnough = myCities.every(c => HEX.distance(c.c, c.r, u.c, u.r) >= 4);
    const isFirst = myCities.length === 0;
    if ((isFirst && hereScore > 15) || (farEnough && hereScore > 28)) {
      if (game.foundCity(u)) return;
    }
    // search for a target site
    let best = null, bestS = isFirst ? 10 : 26;
    for (const [c, r] of HEX.ring(u.c, u.r, 10)) {
      const t = game.tile(c, r);
      if (!t || t.owner !== -1 && t.owner !== p.index) continue;
      if (!myCities.every(mc => HEX.distance(mc.c, mc.r, c, r) >= 4)) continue;
      const s = siteScore(game.map, c, r) - HEX.distance(u.c, u.r, c, r) * 1.5;
      if (s > bestS) { bestS = s; best = [c, r]; }
    }
    if (best) {
      game.moveUnitTo(u, best[0], best[1]);
      if (u.c === best[0] && u.r === best[1]) game.foundCity(u);
    } else if (isFirst && hereScore > 0) {
      game.foundCity(u); // desperate: settle in place
    }
  }

  function runWorker(game, p, u) {
    if (u.building) return; // keep working
    const wanted = (t) => {
      if (t.owner !== p.index || t.city || t.feature) return null;
      if (t.terrain === "HILLS" && t.improvement !== "MINE" && p.hasTech("MINING")) return "MINE";
      if ((t.terrain === "GRASSLAND" || t.terrain === "PLAINS") && t.improvement !== "FARM") return "FARM";
      return null;
    };
    // build here if useful
    const here = game.tile(u.c, u.r);
    const job = wanted(here);
    if (job && game.startImprovement(u, job)) return;
    // otherwise walk to the nearest tile that needs work (avoid tiles other workers target)
    const busy = new Set(game.units.filter(w => w.type === "WORKER" && w.owner === p.index && w !== u)
      .map(w => w.c + "," + w.r));
    let best = null, bestD = Infinity;
    for (const t of game.map.tiles) {
      if (!wanted(t) || busy.has(t.c + "," + t.r)) continue;
      const d = HEX.distance(u.c, u.r, t.c, t.r);
      if (d < bestD) { bestD = d; best = t; }
    }
    if (best) {
      game.moveUnitTo(u, best.c, best.r);
      const now = game.tile(u.c, u.r);
      const j = wanted(now);
      if (j) game.startImprovement(u, j);
    } else {
      // nothing to do: shelter in the nearest city
      const home = game.cities.filter(c => c.owner === p.index)
        .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
      if (home && !(u.c === home.c && u.r === home.r)) game.moveUnitTo(u, home.c, home.r);
    }
  }

  function runMissionary(game, p, u) {
    if (p.religionId === null) { u.moves = 0; return; }
    // preach if standing by a city that doesn't follow us yet
    const target = game.missionaryTarget(u);
    if (target && target.religion !== p.religionId) {
      if (game.spreadFromMissionary(u)) return;
    }
    // walk to the nearest convertible city: own first, then anyone's (not at war)
    let best = null, bestD = Infinity;
    for (const c of game.cities) {
      if (c.religion === p.religionId) continue;
      if (p.atWarWith.has(c.owner)) continue;
      let d = HEX.distance(u.c, u.r, c.c, c.r);
      if (c.owner !== p.index) d += 5; // prefer converting home cities
      if (d < bestD) { bestD = d; best = c; }
    }
    if (best) {
      game.moveUnitTo(u, best.c, best.r);
      const t2 = game.missionaryTarget(u);
      if (t2 && t2.religion !== p.religionId) game.spreadFromMissionary(u);
    } else {
      u.moves = 0; // everyone within reach already converted
    }
  }

  function runScout(game, p, u) {
    autoExplore(game, u);
  }

  // walk toward the nearest unexplored tile (with Sailing the unit will embark)
  function autoExplore(game, u) {
    const p = game.players[u.owner];
    let best = null, bestD = Infinity;
    for (let i = 0; i < game.map.tiles.length; i++) {
      if (p.visible[i]) continue;
      const t = game.map.tiles[i];
      if (!TERRAIN[t.terrain].passable) continue;
      const d = HEX.distance(u.c, u.r, t.c, t.r);
      if (d < bestD) { bestD = d; best = t; }
    }
    if (!best) { u.autoExplore = false; u.moves = 0; return; } // map fully explored
    if (!game.moveUnitTo(u, best.c, best.r)) {
      u.moves = 0; // unreachable this era — wait rather than rescan
    }
  }

  function runShip(game, p, u) {
    const enemies = [...p.atWarWith].filter(e => game.players[e].alive);
    if (tryAttack(game, p, u)) return;
    if (enemies.length) {
      // hunt enemy ships and embarked units, then coastal cities
      let target = null, bestD = Infinity;
      for (const e of game.units) {
        if (!enemies.includes(e.owner)) continue;
        const t = game.tile(e.c, e.r);
        if (!game.isWater(t)) continue;
        const d = HEX.distance(u.c, u.r, e.c, e.r);
        if (d < bestD) { bestD = d; target = e; }
      }
      for (const c of game.cities) {
        if (!enemies.includes(c.owner) || !c.coastal) continue;
        const d = HEX.distance(u.c, u.r, c.c, c.r) + 3; // prefer ships
        if (d < bestD) { bestD = d; target = c; }
      }
      if (target) {
        if (u.hp < 40 && bestD > 2) { u.fortified = true; return; }
        if (u.isRanged && bestD <= u.def.range) { tryAttack(game, p, u); return; }
        const dest = nearestApproach(game, u, target.c, target.r);
        if (dest) game.moveUnitTo(u, dest[0], dest[1]);
        tryAttack(game, p, u);
      }
      return;
    }
    // peacetime: loiter in home waters near a coastal city
    const home = game.cities.filter(c => c.owner === p.index && c.coastal)
      .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
    if (home && HEX.distance(u.c, u.r, home.c, home.r) > 3) {
      const dest = nearestApproach(game, u, home.c, home.r);
      if (dest) game.moveUnitTo(u, dest[0], dest[1]);
    } else {
      u.fortified = true;
    }
  }

  function runMilitary(game, p, u) {
    const enemies = [...p.atWarWith].filter(e => game.players[e].alive);

    // city-state troops never leave home
    if (p.isMinor) {
      const home = game.cities.find(c => c.owner === p.index);
      if (!home) return;
      if (tryAttack(game, p, u)) return;
      if (HEX.distance(u.c, u.r, home.c, home.r) > 2) {
        game.moveUnitTo(u, home.c, home.r);
      } else if (enemies.length) {
        // charge intruders inside the home zone
        let target = null, bestD = Infinity;
        for (const e of game.units) {
          if (!enemies.includes(e.owner) || e.isCivilian) continue;
          const d = HEX.distance(e.c, e.r, home.c, home.r);
          if (d <= 3 && d < bestD) { bestD = d; target = e; }
        }
        if (target) {
          const dest = nearestApproach(game, u, target.c, target.r);
          if (dest) game.moveUnitTo(u, dest[0], dest[1]);
          tryAttack(game, p, u);
        } else u.fortified = true;
      } else {
        u.fortified = true;
      }
      return;
    }

    // stranded at sea with nothing to do: head for the nearest friendly city
    if (game.isEmbarked(u) && !enemies.length) {
      const home = game.cities.filter(c => c.owner === p.index)
        .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
      if (home) game.moveUnitTo(u, home.c, home.r);
      return;
    }

    // 1. attack anything in reach
    if (tryAttack(game, p, u)) return;

    if (enemies.length) {
      // 2. march on the nearest enemy city
      let target = null, bestD = Infinity;
      for (const c of game.cities) {
        if (!enemies.includes(c.owner)) continue;
        const d = HEX.distance(u.c, u.r, c.c, c.r);
        if (d < bestD) { bestD = d; target = c; }
      }
      if (!target) {
        for (const e of game.units) {
          if (!enemies.includes(e.owner)) continue;
          const d = HEX.distance(u.c, u.r, e.c, e.r);
          if (d < bestD) { bestD = d; target = e; }
        }
      }
      if (target) {
        // wounded units hold back and heal
        if (u.hp < 40 && bestD > 2) { u.fortified = true; return; }
        // ranged units keep their distance
        if (u.isRanged && bestD <= u.def.range) { tryAttack(game, p, u); return; }
        // step toward target (stop next to it, attack handled next turn/iteration)
        const dest = nearestApproach(game, u, target.c, target.r);
        if (dest) game.moveUnitTo(u, dest[0], dest[1]);
        tryAttack(game, p, u);
      }
      return;
    }

    // 3. peace: garrison cities, otherwise fortify near home
    const myCities = game.cities.filter(c => c.owner === p.index);
    const emptyCity = myCities.find(c => {
      const g = game.combatUnitAt(c.c, c.r);
      return !g || g.id === u.id;
    });
    if (emptyCity && !(u.c === emptyCity.c && u.r === emptyCity.r)) {
      game.moveUnitTo(u, emptyCity.c, emptyCity.r);
    } else if (u.hp < 100 || game.rng() < 0.8) {
      u.fortified = true;
    } else if (myCities.length) {
      // wander the borders a little
      const home = myCities[Math.floor(game.rng() * myCities.length)];
      const spots = HEX.ring(home.c, home.r, 2).filter(([c, r]) => {
        const t = game.tile(c, r);
        return t && TERRAIN[t.terrain].passable && !game.combatUnitAt(c, r);
      });
      if (spots.length) {
        const [c, r] = spots[Math.floor(game.rng() * spots.length)];
        game.moveUnitTo(u, c, r);
      }
    }
  }

  function tryAttack(game, p, u) {
    if (u.attacked || u.moves <= 0 || game.isEmbarked(u)) return false;
    const range = u.isRanged ? u.def.range : 1;
    let best = null, bestValue = -Infinity;
    for (const [c, r] of HEX.ring(u.c, u.r, range)) {
      const t = game.tile(c, r);
      if (!t) continue;
      // melee reach restrictions across the shoreline
      if (!u.isRanged && !u.def.naval && game.isWater(t)) continue;
      if (!u.isRanged && u.def.naval && !game.isWater(t) && !t.city) continue;
      const enemyUnit = game.combatUnitAt(c, r);
      const enemyCity = t.city && p.atWarWith.has(t.city.owner) ? t.city : null;
      const enemyCiv = game.civilianAt(c, r);
      let value = -Infinity;
      if (enemyUnit && p.atWarWith.has(enemyUnit.owner)) {
        const myStr = game.strengthOf(u, { attacking: true, targetTile: t, ranged: u.isRanged });
        const theirStr = game.strengthOf(enemyUnit, {});
        value = myStr - theirStr + (100 - enemyUnit.hp) * 0.15;
        if (!u.isRanged && theirStr > myStr * 1.5) value = -Infinity; // suicide check
      } else if (enemyCity) {
        const myStr = game.strengthOf(u, { attacking: true, targetTile: t, ranged: u.isRanged });
        const cityStr = game.cityStrength(enemyCity);
        value = myStr - cityStr + (enemyCity.maxHp - enemyCity.hp) * 0.1 + 5;
        if (!u.isRanged && u.hp < 35) value = -Infinity;
      } else if (enemyCiv && p.atWarWith.has(enemyCiv.owner) && !u.isRanged) {
        value = 50; // free capture
      }
      if (value > bestValue) { bestValue = value; best = [c, r]; }
    }
    if (best && bestValue > -20) {
      const t = game.tile(best[0], best[1]);
      const civOnly = game.civilianAt(best[0], best[1]) && !game.combatUnitAt(best[0], best[1]) &&
        !(t.city && p.atWarWith.has(t.city.owner));
      if (civOnly) return game.moveUnitTo(u, best[0], best[1]);
      return game.attack(u, best[0], best[1]);
    }
    return false;
  }

  // find a tile this unit can stand on, adjacent to (tc,tr), to path to
  function nearestApproach(game, u, tc, tr) {
    const t = game.tile(tc, tr);
    if (game.unitPassable(u, t) && !game.combatUnitAt(tc, tr) && !t.city) return [tc, tr];
    let best = null, bestD = Infinity;
    for (const [c, r] of HEX.neighbors(tc, tr)) {
      const n = game.tile(c, r);
      if (!game.unitPassable(u, n)) continue;
      if (game.combatUnitAt(c, r)) continue;
      const d = HEX.distance(u.c, u.r, c, r);
      if (d < bestD) { bestD = d; best = [c, r]; }
    }
    return best;
  }

  return { takeTurn, autoExplore };
})();
