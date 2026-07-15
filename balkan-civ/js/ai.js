// ============================================================
// AI players: settling, production, research, war, tactics
// ============================================================
"use strict";

const AI = (() => {

  // wars against real rivals — the eternal barbarian feud doesn't count
  function realWars(game, p) {
    return [...p.atWarWith].filter(e => e !== game.barbIndex && game.players[e].alive);
  }

  // Each leader leans into the victory route their bonuses support. Keeping
  // this derived from data makes alternate leaders play differently without
  // maintaining a second civilization-specific strategy table.
  function victoryFocus(p) {
    const c = p.civ;
    const n = (value) => Number(value) || 0;
    const weights = {
      science: n(c.cityScience) * 4,
      culture: n(c.cityCulture) * 3 + n(c.cultureBonus) * 10,
      religion: n(c.cityFaith) * 4,
      diplomacy: n(c.cityGold) * 2 + n(c.capitalGold) + n(c.coastalGold) * 2,
      domination: 1 + (n(c.attackBonus) + n(c.defendCiv) + n(c.vsCityBonus) +
        n(c.roughBonus) + n(c.homeBonus) + n(c.unitProdBonus)) * 10,
    };
    return Object.keys(weights).sort((a, b) => weights[b] - weights[a] || a.localeCompare(b))[0];
  }

  function techOnPath(key, target, seen = new Set()) {
    if (key === target) return true;
    if (seen.has(target) || !TECHS[target]) return false;
    seen.add(target);
    return TECHS[target].req.some(req => techOnPath(key, req, new Set(seen)));
  }

  const ARMY_ROLE_ORDER = ["siege", "ranged", "frontline"];

  function armyRole(key) {
    const def = UNITS[key];
    if (!def || def.civilian || def.naval || def.great || key === "SCOUT") return null;
    if (def.siege) return "siege";
    if (def.rs) return "ranged";
    return "frontline";
  }

  function armyRoleCounts(game, p) {
    const counts = { frontline: 0, ranged: 0, siege: 0 };
    const count = (key) => {
      const role = armyRole(key);
      if (role) counts[role]++;
    };
    for (const u of game.units) if (u.owner === p.index) count(u.type);
    for (const city of game.cities) {
      if (city.owner !== p.index) continue;
      if (city.producing && city.producing.kind === "unit") count(city.producing.key);
      for (const item of city.queue) if (item.kind === "unit") count(item.key);
    }
    return counts;
  }

  function desiredArmyRoles(total, atWar, focus, siegeAvailable) {
    total = Math.max(0, Math.floor(total));
    const siege = siegeAvailable && total >= 4
      ? Math.max(1, Math.round(total * (atWar || focus === "domination" ? 0.2 : 0.12))) : 0;
    const ranged = total >= 3 ? Math.max(1, Math.ceil(total * 0.25)) : 0;
    return { frontline: Math.max(0, total - ranged - siege), ranged, siege };
  }

  function bestMilitaryOption(opts, wantedRole = null, excluded = new Set()) {
    let choices = opts.filter(o => o.kind === "unit" && armyRole(o.key) && !excluded.has(o.key));
    const matching = wantedRole ? choices.filter(o => armyRole(o.key) === wantedRole) : [];
    if (matching.length) choices = matching;
    if (!choices.length) return null;
    choices.sort((a, b) => Math.max(UNITS[b.key].cs, UNITS[b.key].rs || 0) -
      Math.max(UNITS[a.key].cs, UNITS[a.key].rs || 0) ||
      UNITS[b.key].moves - UNITS[a.key].moves || UNITS[a.key].cost - UNITS[b.key].cost ||
      a.key.localeCompare(b.key));
    return choices[0];
  }

  function bestNavalOption(opts, excluded = new Set()) {
    const choices = opts.filter(o => o.kind === "unit" && UNITS[o.key].naval).sort((a, b) =>
      Math.max(UNITS[b.key].cs, UNITS[b.key].rs || 0) -
      Math.max(UNITS[a.key].cs, UNITS[a.key].rs || 0) ||
      Number(!!UNITS[b.key].rs) - Number(!!UNITS[a.key].rs) ||
      UNITS[b.key].moves - UNITS[a.key].moves || a.key.localeCompare(b.key));
    if (!choices.length || excluded.has(choices[0].key)) return null;
    return choices[0];
  }

  function neededArmyRole(opts, counts, targets) {
    const available = ARMY_ROLE_ORDER.filter(role =>
      opts.some(o => o.kind === "unit" && armyRole(o.key) === role));
    return available.sort((a, b) => {
      const pressure = (role) => targets[role] > 0
        ? (targets[role] - counts[role]) / targets[role] : -counts[role] - 1;
      return pressure(b) - pressure(a) || ARMY_ROLE_ORDER.indexOf(a) - ARMY_ROLE_ORDER.indexOf(b);
    })[0] || null;
  }

  function closestCityDistance(ours, theirs) {
    let distance = Infinity;
    for (const own of ours) for (const target of theirs) {
      distance = Math.min(distance, HEX.distance(own.c, own.r, target.c, target.r));
    }
    return distance;
  }

  function landmassMap(game) {
    if (game._aiLandmassMap && game._aiLandmassMap.length === game.map.tiles.length) {
      return game._aiLandmassMap;
    }
    const ids = Array(game.map.tiles.length).fill(-1);
    let nextId = 0;
    for (const start of game.map.tiles) {
      const startIdx = game.map.idx(start.c, start.r);
      if (ids[startIdx] !== -1 || game.isWater(start)) continue;
      ids[startIdx] = nextId;
      const frontier = [start];
      for (let cursor = 0; cursor < frontier.length; cursor++) {
        const tile = frontier[cursor];
        for (const [c, r] of HEX.neighbors(tile.c, tile.r)) {
          const neighbor = game.tile(c, r);
          if (!neighbor || game.isWater(neighbor)) continue;
          const idx = game.map.idx(c, r);
          if (ids[idx] !== -1) continue;
          ids[idx] = nextId;
          frontier.push(neighbor);
        }
      }
      nextId++;
    }
    game._aiLandmassMap = ids;
    return ids;
  }

  function sameLandmass(game, a, b) {
    if (!a || !b) return false;
    const ids = landmassMap(game);
    const first = ids[game.map.idx(a.c, a.r)];
    return first >= 0 && first === ids[game.map.idx(b.c, b.r)];
  }

  function campaignIsOverseas(game, p, target) {
    if (!target) return false;
    const homes = game.cities.filter(c => c.owner === p.index);
    return homes.length > 0 && homes.every(home => !sameLandmass(game, home, target));
  }

  function hasOverseasRival(game, p) {
    const homes = game.cities.filter(c => c.owner === p.index);
    if (!homes.length) return false;
    return [...p.met].some(i => {
      const rival = game.players[i];
      if (!rival || !rival.alive || rival.isMinor || rival.isBarb) return false;
      const cities = game.cities.filter(c => c.owner === rival.index);
      return cities.length > 0 && homes.every(home => cities.every(city => !sameLandmass(game, home, city)));
    });
  }

  function warTargetPlan(game, p, other) {
    if (!other || !other.alive || other.isBarb || other.index === p.index ||
        p.atWarWith.has(other.index) || p.pacts.has(other.index)) return null;
    const focus = victoryFocus(p);
    if (other.isMinor && focus !== "domination") return null;
    const ours = game.cities.filter(c => c.owner === p.index);
    const theirs = game.cities.filter(c => c.owner === other.index);
    if (!ours.length || !theirs.length) return null;

    const allyAtWar = [...p.pacts].some(a => game.players[a].alive &&
      game.players[a].atWarWith.has(other.index));
    const overseas = ours.every(own => theirs.every(target => !sameLandmass(game, own, target)));
    const distance = closestCityDistance(ours, theirs);
    const maxDistance = allyAtWar || overseas ? 12 : 9;
    const myPower = game.militaryPower(p.index);
    const theirPower = game.militaryPower(other.index);
    const ratio = myPower / Math.max(1, theirPower);
    const fleet = game.units.filter(u => u.owner === p.index && u.def.naval);
    if (overseas && (!p.hasTech("COMPASS") || !fleet.length)) return null;
    const powerNeeded = allyAtWar ? 1.0 : other.isMinor ? 2.0
      : (focus === "domination" ? 1.35 : 1.6) + (overseas ? 0.1 : 0);
    if (distance > maxDistance || myPower <= 40 || ratio <= powerNeeded) return null;

    const attitude = game.attitudeOf(p.index, other.index);
    const friendly = attitude >= DIPLO.pactThreshold;
    const chance = other.isMinor ? 0.025 : allyAtWar ? 0.3
      : focus === "domination" ? (friendly ? 0.025 : 0.1) : (friendly ? 0.012 : 0.055);
    const score = (maxDistance - distance) * 12 + (Math.min(ratio, 4) - powerNeeded) * 30 -
      attitude * 0.3 + (allyAtWar ? 45 : 0) - (other.isMinor ? 20 : 0) +
      Math.max(0, 3 - theirs.length) * 3 - (overseas ? 15 : 0);
    return { player: other.index, score, chance, distance, ratio, allyAtWar, overseas };
  }

  function chooseWarTarget(game, p) {
    return [...p.met].map(i => warTargetPlan(game, p, game.players[i])).filter(Boolean)
      .sort((a, b) => b.score - a.score || a.player - b.player)[0] || null;
  }

  function campaignTarget(game, p) {
    const enemies = new Set(realWars(game, p));
    const homes = game.cities.filter(c => c.owner === p.index);
    if (!enemies.size || !homes.length) return null;
    const targets = game.cities.filter(c => enemies.has(c.owner));
    const targetCost = (city) => {
      const distance = Math.min(...homes.map(home => HEX.distance(home.c, home.r, city.c, city.r)));
      return distance * 10 + (city.hp / Math.max(1, city.maxHp)) * 6 +
        game.cityStrength(city) * 0.2 + game.militaryPower(city.owner) * 0.02 -
        (city.isCapital ? 8 : 0) + (campaignIsOverseas(game, p, city) ?
          (p.hasTech("COMPASS") ? 8 : 40) : 0);
    };
    return targets.sort((a, b) => targetCost(a) - targetCost(b) || a.owner - b.owner || a.id - b.id)[0] || null;
  }

  function takeTurn(game, p) {
    if (p.isBarb) {
      runBarbarians(game, p);
      return;
    }
    if (p.isMinor) {
      chooseResearch(game, p);
      runMinorCities(game, p);
      runUnits(game, p);
      return;
    }
    diplomacy(game, p);
    adoptPolicies(game, p);
    autoPromote(game, p);
    religion(game, p);
    espionage(game, p);
    chooseResearch(game, p);
    runCities(game, p);
    runUnits(game, p);
  }

  // ---------- social policies ----------
  function adoptPolicies(game, p) {
    const focus = victoryFocus(p);
    const orders = {
      domination: ["JUNAK", "ZADRUGA", "CARSIJA", "SABOR"],
      science: ["SABOR", "ZADRUGA", "CARSIJA", "JUNAK"],
      culture: ["ZADRUGA", "SABOR", "CARSIJA", "JUNAK"],
      religion: ["SABOR", "ZADRUGA", "CARSIJA", "JUNAK"],
      diplomacy: ["CARSIJA", "ZADRUGA", "SABOR", "JUNAK"],
    };
    const order = orders[focus];
    let guard = 0;
    while (game.canAdoptPolicy(p.index) && guard++ < 20) {
      let picked = null;
      for (const b of order) {
        picked = Object.keys(POLICY_BRANCHES[b].policies).find(k => !p.policies.has(k));
        if (picked) break;
      }
      if (!picked || !game.adoptPolicy(p.index, picked)) break;
    }
  }

  // ---------- promotions ----------
  function autoPromote(game, p) {
    const campaign = realWars(game, p).length ? campaignTarget(game, p) : null;
    const amphibiousNeed = game.mapType === "archipelago" || hasOverseasRival(game, p) ||
      campaignIsOverseas(game, p, campaign);
    for (const u of game.units) {
      if (u.owner !== p.index || u.isCivilian) continue;
      while (u.promoPts > 0) {
        const open = promotionChoices(u).filter(k => !u.promos.includes(k));
        if (!open.length) { u.promoPts = 0; break; }
        let pick;
        if (u.def.naval && u.isRanged && open.includes("BOMBARDMENT")) pick = "BOMBARDMENT";
        else if (u.def.naval && !u.isRanged && open.includes("BOARDING")) pick = "BOARDING";
        else if (u.def.naval && open.includes("NAVIGATION")) pick = "NAVIGATION";
        else if (!u.isRanged && amphibiousNeed && open.includes("AMPHIBIOUS")) pick = "AMPHIBIOUS";
        else if (u.isRanged && open.includes("MIGHT")) pick = "MIGHT";
        else if (u.def.defendBonus && open.includes("BULWARK")) pick = "BULWARK";
        else if (open.includes("MIGHT")) pick = "MIGHT";
        else pick = open[0];
        u.addPromotion(pick);
        u.promoPts--;
      }
    }
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
    // Faith-led rulers sustain a larger mission network and spend closer to
    // their reserve; other rulers still defend and spread their own religion.
    const religious = victoryFocus(p) === "religion";
    const reserve = religious ? 10 : 40;
    if (p.religionId !== null && p.faith >= game.missionaryCost(p.index) + reserve) {
      const nMissionaries = game.units.filter(u => u.owner === p.index && u.type === "MISSIONARY").length;
      if (nMissionaries < (religious ? 3 : 2)) {
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
      if (choice) game.setCityProduction(city, { kind: choice.kind, key: choice.key }, false, p.index);
    }
  }

  // ---------- barbarians ----------
  function runBarbarians(game, p) {
    for (const u of game.units) {
      if (u.owner !== p.index) continue;
      if (u.isCivilian) continue; // captured workers just sit in camp
      if (tryAttack(game, p, u)) continue;
      // raid nearby soldiers and settlements; snatch civilians only point-blank
      let target = null, bestD = 5;
      for (const v of game.units) {
        if (v.owner === p.index) continue;
        const d = HEX.distance(u.c, u.r, v.c, v.r);
        if (v.isCivilian && d > 1) continue;
        if (d <= bestD) { bestD = d; target = v; }
      }
      if (!target) {
        for (const c of game.cities) {
          const d = HEX.distance(u.c, u.r, c.c, c.r);
          if (d <= bestD) { bestD = d; target = c; }
        }
      }
      if (target) {
        const dest = nearestApproach(game, u, target.c, target.r);
        if (dest) game.moveUnitTo(u, dest[0], dest[1]);
        tryAttack(game, p, u);
      } else {
        const camp = game.camps[0] ? game.camps.sort((a, b) =>
          HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0] : null;
        if (camp && HEX.distance(u.c, u.r, camp.c, camp.r) > 3) {
          game.moveUnitTo(u, camp.c, camp.r);
        } else {
          u.fortified = true;
        }
      }
    }
  }

  // ---------- diplomacy ----------
  function diplomacy(game, p) {
    const diplomatic = victoryFocus(p) === "diplomacy";
    // court city-states when rich
    if (p.gold > (diplomatic ? 250 : 350) && game.rng() < (diplomatic ? 0.4 : 0.15)) {
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
      if (p.atWarWith.has(other)) {
        // sue for peace if clearly losing or war has dragged on
        const weary = (p.warWeariness[other] || 0) > 25;
        const losing = game.militaryPower(p.index) < game.militaryPower(other) * 0.55;
        if ((weary && game.rng() < 0.2) || (losing && game.rng() < 0.3)) {
          // never end a war with a human unilaterally — offer it and let them decide
          if (o.isHuman) game.offerPeace(p.index, other);
          else game.makePeace(p.index, other);
        }
      } else {
        if (!o.isMinor) {
          // friendly overtures first: luxury deals, then pacts with friends
          if (game.canLuxuryDeal(p.index, other) && game.rng() < 0.35) {
            game.makeLuxuryDeal(p.index, other);
          }
          if (game.canPact(p.index, other) && game.rng() < 0.15) {
            game.makePact(p.index, other);
          }
        }
      }
    }
    // Pick one reviewed objective instead of rolling independently for every
    // known rival. Defensive pacts may widen a front, but the AI will not open
    // another opportunistic war while an existing campaign is active.
    if (!realWars(game, p).length) {
      const target = chooseWarTarget(game, p);
      if (target && game.rng() < target.chance) game.declareWar(p.index, target.player);
    }
  }

  // ---------- research ----------
  function chooseResearch(game, p) {
    if (p.researching) return;
    const av = p.availableTechs();
    if (!av.length) return;
    const atWar = realWars(game, p).length > 0;
    const objective = atWar ? campaignTarget(game, p) : null;
    const overseas = !p.isMinor && campaignIsOverseas(game, p, objective);
    const maritimeNeed = !p.isMinor && (overseas || game.mapType === "archipelago" ||
      hasOverseasRival(game, p));
    const milTechs = ["ARCHERY", "BRONZE_WORKING", "IRON_WORKING", "HORSEBACK_RIDING",
      "CHIVALRY", "STEEL", "MACHINERY", "GUNPOWDER", "MASONRY", "CONSTRUCTION", "PHYSICS", "MATHEMATICS",
      "SAILING", "COMPASS", "METALLURGY", "RIFLING", "MILITARY_SCIENCE", "STEAM_POWER"];
    const goals = {
      science: ["WRITING", "PHILOSOPHY", "EDUCATION", "INDUSTRIALIZATION", "SANITATION"],
      culture: ["PHILOSOPHY", "THEOLOGY", "EDUCATION", "INDUSTRIALIZATION"],
      religion: ["POTTERY", "PHILOSOPHY", "THEOLOGY", "EDUCATION"],
      diplomacy: ["CURRENCY", "CIVIL_SERVICE", "BANKING", "STEAM_POWER"],
      domination: milTechs,
    }[victoryFocus(p)];
    const score = (key) => {
      let value = TECHS[key].cost;
      if (goals.some(target => !p.hasTech(target) && techOnPath(key, target))) value *= 0.55;
      if (atWar && milTechs.includes(key)) value *= 0.5;
      if (maritimeNeed && !p.hasTech("COMPASS") && techOnPath(key, "COMPASS")) {
        value *= overseas ? 0.22 : 0.42;
      }
      return value;
    };
    const ranked = av.sort((a, b) => {
      return score(a) - score(b) || TECHS[a].cost - TECHS[b].cost || a.localeCompare(b);
    });
    p.researching = ranked[0];
  }

  // ---------- cities / production ----------
  function runCities(game, p) {
    const myCities = game.cities.filter(c => c.owner === p.index);
    const myUnits = game.units.filter(u => u.owner === p.index);
    const atWar = realWars(game, p).length > 0;
    const focus = victoryFocus(p);
    const objective = atWar ? campaignTarget(game, p) : null;
    const overseasWar = campaignIsOverseas(game, p, objective);
    const fleetPriority = overseasWar || (p.hasTech("SAILING") &&
      (game.mapType === "archipelago" || hasOverseasRival(game, p)));
    const wantCities = 4 + Math.floor(game.map.w / 15);
    const wantMilitary = myCities.length * (focus === "domination" ? 3 : 2) + (atWar ? 4 : 1);
    for (const city of myCities) {
      city.focus = atWar || focus === "domination" ? "production"
        : city.pop < 4 ? "growth" : focus === "diplomacy" ? "gold" : "balanced";
    }
    game.assignWorkedTiles(p.index);

    const optionsByCity = new Map(myCities.map(city => [city, game.productionOptions(city)]));
    const roleCounts = armyRoleCounts(game, p);
    const siegeAvailable = [...optionsByCity.values()].some(opts =>
      opts.some(o => o.kind === "unit" && armyRole(o.key) === "siege"));
    const roleTargets = desiredArmyRoles(wantMilitary, atWar, focus, siegeAvailable);
    const plannedByType = new Map();
    const addType = (key) => plannedByType.set(key, (plannedByType.get(key) || 0) + 1);
    for (const u of myUnits) addType(u.type);
    for (const city of myCities) {
      if (city.producing && city.producing.kind === "unit") addType(city.producing.key);
      for (const item of city.queue) if (item.kind === "unit") addType(item.key);
    }
    const plannedUnitTotal = (pred) => [...plannedByType].reduce((sum, [key, count]) =>
      sum + (UNITS[key] && pred(UNITS[key], key) ? count : 0), 0);
    const plannedNavySize = () => plannedUnitTotal(def => def.naval);
    const navyTarget = overseasWar ? Math.max(2, Math.ceil(myCities.length / 2))
      : fleetPriority ? Math.max(1, Math.ceil(myCities.length / 3))
      : Math.max(1, Math.floor(myCities.length / 2));
    const plannedArmySize = () => roleCounts.frontline + roleCounts.ranged + roleCounts.siege;
    const registerUnitPlan = (choice) => {
      if (!choice || choice.kind !== "unit") return;
      addType(choice.key);
      const role = armyRole(choice.key);
      if (role) roleCounts[role]++;
    };

    // Keep one reserve order behind current wartime production. This lets an
    // empire react to a new front without cancelling accumulated production.
    if (atWar && (plannedArmySize() < wantMilitary ||
        (overseasWar && plannedNavySize() < navyTarget))) {
      for (const city of myCities) {
        const needsReserve = plannedArmySize() < wantMilitary ||
          (overseasWar && plannedNavySize() < navyTarget);
        if (!city.producing || city.queue.length || !needsReserve) continue;
        const opts = optionsByCity.get(city);
        const excluded = new Set([city.producing.key, ...city.queue.map(item => item.key)]);
        let reserve = overseasWar && city.coastal && plannedNavySize() < navyTarget
          ? bestNavalOption(opts, excluded) : null;
        if (!reserve) {
          const role = neededArmyRole(opts, roleCounts, roleTargets);
          reserve = bestMilitaryOption(opts, role, excluded);
        }
        if (reserve && game.setCityProduction(city,
            { kind: reserve.kind, key: reserve.key }, true, p.index)) registerUnitPlan(reserve);
      }
    }

    for (const city of myCities) {
      if (city.producing) continue;
      const opts = optionsByCity.get(city);
      if (!opts.length) continue;

      const pick = (pred) => {
        const c = opts.filter(pred);
        return c.length ? c[Math.floor(game.rng() * c.length)] : null;
      };
      let choice = null;
      const garrison = game.combatUnitAt(city.c, city.r);
      if (!garrison && plannedArmySize() < myCities.length) {
        choice = bestMilitaryOption(opts, "frontline") ||
          bestMilitaryOption(opts, neededArmyRole(opts, roleCounts, roleTargets));
      }
      const happiness = game.happinessOf(p.index);
      if (!choice && happiness < 0) {
        // unhappy: happiness buildings before anything else
        choice = opts.find(o => o.kind === "building" && (o.key === "TAVERN" || o.key === "HAMMAM")) || null;
      }
      if (!choice && fleetPriority && city.coastal && plannedNavySize() < navyTarget) {
        choice = bestNavalOption(opts);
      }
      const settlers = plannedByType.get("SETTLER") || 0;
      if (!choice && !atWar && happiness >= 2 && myCities.length + settlers < wantCities &&
          city.pop >= 3 && settlers === 0 && game.rng() < 0.7) {
        choice = pick(o => o.key === "SETTLER");
      }
      const workers = plannedByType.get("WORKER") || 0;
      if (!choice && workers < Math.min(myCities.length, 3) && game.rng() < 0.4) {
        choice = pick(o => o.key === "WORKER");
      }
      const caravans = plannedUnitTotal(def => def.caravan);
      const myRoutes = game.routes.filter(r => r.owner === p.index).length;
      if (!choice && p.hasTech("CURRENCY") && myCities.length >= 2 &&
          caravans + myRoutes < Math.min(TRADE.maxRoutes, myCities.length) &&
          game.rng() < (focus === "diplomacy" ? 0.65 : 0.35)) {
        choice = pick(o => o.key === "CARAVAN");
      }
      if (!choice && !fleetPriority && city.coastal && plannedNavySize() < navyTarget &&
          game.rng() < (atWar ? 0.3 : 0.12)) {
        choice = bestNavalOption(opts);
      }
      if (!choice && plannedArmySize() < wantMilitary &&
          game.rng() < (atWar ? 0.85 : focus === "domination" ? 0.6 : 0.35)) {
        choice = bestMilitaryOption(opts, neededArmyRole(opts, roleCounts, roleTargets));
      }
      if (!choice) {
        const strategic = {
          science: ["LIBRARY", "UNIVERSITY", "OHRID_SCHOOL", "RILA", "ORIENT_EXPRESS"],
          culture: ["MONUMENT", "TEMPLE", "STUDENICA", "HAGIA_SOPHIA", "MOUNT_ATHOS"],
          religion: ["SHRINE", "TEMPLE", "MOUNT_ATHOS", "HAGIA_SOPHIA", "STUDENICA", "RILA"],
          diplomacy: ["MARKET", "BANK", "STOCK_EXCHANGE", "STARI_MOST", "ORIENT_EXPRESS"],
          domination: ["BARRACKS", "FORGE", "WALLS", "CASTLE", "ARSENAL", "KALEMEGDAN"],
        }[focus];
        const prio = [...strategic, "MONUMENT", "SHRINE", "GRANARY", "LIBRARY", "TAVERN", "WALLS", "MARKET", "BARRACKS",
          "TEMPLE", "HAMMAM", "AQUEDUCT", "FORGE", "UNIVERSITY", "CASTLE", "WORKSHOP", "BANK",
          "FACTORY", "HOSPITAL", "ARSENAL", "STOCK_EXCHANGE",
          "DIOCLETIAN", "HIPPODROME", "OHRID_SCHOOL", "STARI_MOST", "MOUNT_ATHOS", "BRAN_CASTLE",
          "HAGIA_SOPHIA", "STUDENICA", "RILA", "KALEMEGDAN", "IRON_GATES", "ORIENT_EXPRESS"];
        for (const key of prio) {
          const o = opts.find(x => x.kind === "building" && x.key === key);
          if (o) { choice = o; break; }
        }
      }
      if (!choice) choice = bestMilitaryOption(opts, neededArmyRole(opts, roleCounts, roleTargets)) || opts[0];
      if (game.setCityProduction(city, { kind: choice.kind, key: choice.key }, false, p.index)) {
        registerUnitPlan(choice);
      }
    }
  }

  // ---------- unit control ----------
  function runUnits(game, p) {
    const myUnits = game.units.filter(u => u.owner === p.index);
    const target = campaignTarget(game, p);
    const campaign = { target, overseas: campaignIsOverseas(game, p, target),
      approaches: new Set(), navalApproaches: new Set(), escortAssigned: false,
      blockaderAssigned: false, defenseApproaches: new Set(), roadClaims: new Map() };
    for (const worker of myUnits.filter(unit => unit.type === "WORKER")) {
      const destination = worker.building && worker.building.type === "ROAD" ? [worker.c, worker.r]
        : worker.path && worker.path.length ? worker.path[worker.path.length - 1] : null;
      if (destination) campaign.roadClaims.set(destination[0] + "," + destination[1], worker.id);
    }
    for (const u of myUnits) {
      if (!game.units.includes(u)) continue; // died mid-loop
      if (u.type === "SETTLER") runSettler(game, p, u);
      else if (u.type === "WORKER") runWorker(game, p, u, campaign);
      else if (u.def.caravan) runCaravan(game, p, u);
      else if (u.def.great) runGreatPerson(game, p, u);
      else if (u.type === "MISSIONARY") runMissionary(game, p, u);
      else if (u.type === "SCOUT") runScout(game, p, u);
      else if (u.def.naval) runShip(game, p, u, campaign);
      else if (!u.isCivilian) runMilitary(game, p, u, campaign);
    }
  }

  function runSettler(game, p, u) {
    // raiders nearby? run for the nearest city
    if (game.barbIndex >= 0) {
      const danger = game.units.some(v => v.owner === game.barbIndex && !v.isCivilian &&
        HEX.distance(v.c, v.r, u.c, u.r) <= 3);
      if (danger) {
        const home = game.cities.filter(c => c.owner === p.index)
          .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
        if (home) { game.moveUnitTo(u, home.c, home.r); return; }
      }
    }
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

  function runWorker(game, p, u, campaign = null) {
    if (u.building) return; // keep working
    if (p.hasTech("THE_WHEEL")) {
      const claims = campaign ? campaign.roadClaims : new Map();
      const candidates = [];
      for (const [planIndex, plan] of game.roadConnectionPlans(p.index).entries()) {
        plan.missing.forEach((tile, segmentIndex) => candidates.push({ tile, planIndex, segmentIndex }));
      }
      candidates.sort((a, b) =>
        HEX.distance(u.c, u.r, a.tile.c, a.tile.r) - HEX.distance(u.c, u.r, b.tile.c, b.tile.r) ||
        a.planIndex - b.planIndex || a.segmentIndex - b.segmentIndex ||
        a.tile.r - b.tile.r || a.tile.c - b.tile.c);
      const task = candidates.find(({ tile }) => {
        const key = tile.c + "," + tile.r;
        const claimedBy = claims.get(key);
        if (claimedBy !== undefined && claimedBy !== u.id) return false;
        if (game.unitsAt(tile.c, tile.r).some(other => other.id !== u.id)) return false;
        return game.findPath(u, tile.c, tile.r) !== null;
      });
      if (task) {
        const key = task.tile.c + "," + task.tile.r;
        claims.set(key, u.id);
        if (u.c === task.tile.c && u.r === task.tile.r) {
          if (game.startImprovement(u, "ROAD")) return;
        } else if (game.moveUnitTo(u, task.tile.c, task.tile.r)) {
          if (u.c === task.tile.c && u.r === task.tile.r) game.startImprovement(u, "ROAD");
          return;
        }
        if (claims.get(key) === u.id) claims.delete(key);
      }
    }
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

  function runCaravan(game, p, u) {
    const dests = game.tradeDestinations(u);
    if (dests.length) {
      const from = game.cityAt(u.c, u.r);
      game.establishRoute(u, dests.sort((a, b) =>
        game.routeIncome(from, b) - game.routeIncome(from, a))[0].id);
      return;
    }
    // walk to the nearest own city and try from there
    const home = game.cities.filter(c => c.owner === p.index)
      .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
    if (home && !(u.c === home.c && u.r === home.r)) game.moveUnitTo(u, home.c, home.r);
    else u.moves = 0;
  }

  function runGreatPerson(game, p, u) {
    if (u.def.great === "sci") { game.useGreatPerson(u); return; }
    if (u.def.great === "eng") {
      const city = game.cityAt(u.c, u.r);
      if (city && city.owner === p.index) { game.useGreatPerson(u); return; }
      const home = game.cities.filter(c => c.owner === p.index)
        .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
      if (home) game.moveUnitTo(u, home.c, home.r);
      return;
    }
    // generals ride with the largest nearby force when at war, else hold the capital
    if (realWars(game, p).length) {
      const troop = game.units.filter(v => v.owner === p.index && !v.isCivilian)
        .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
      if (troop && HEX.distance(u.c, u.r, troop.c, troop.r) > 1) {
        const dest = nearestApproach(game, u, troop.c, troop.r);
        if (dest) game.moveUnitTo(u, dest[0], dest[1]);
        return;
      }
    }
    u.fortified = true;
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

  function navalExploreTarget(game, p, u) {
    const supply = game.navalSupplyCoverage(u);
    const targets = game.map.tiles.filter(tile => p.visible[game.map.idx(tile.c, tile.r)] === 0 &&
      game.isWater(tile) && game.unitPassable(u, tile) && supply.has(game.map.idx(tile.c, tile.r))).sort((a, b) =>
      HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r) ||
      a.r - b.r || a.c - b.c);
    for (const tile of targets) if (game.findPath(u, tile.c, tile.r)) return tile;
    return null;
  }

  function navalInterceptionApproach(game, u, target) {
    const candidates = HEX.neighbors(target.c, target.r).sort((a, b) =>
      HEX.distance(u.c, u.r, a[0], a[1]) - HEX.distance(u.c, u.r, b[0], b[1]) ||
      a[1] - b[1] || a[0] - b[0]);
    for (const [c, r] of candidates) {
      const tile = game.tile(c, r);
      const occupant = game.combatUnitAt(c, r);
      if (!tile || !game.isWater(tile) || !game.unitPassable(u, tile) ||
          (occupant && occupant.id !== u.id) || !game.findPath(u, c, r)) continue;
      return [c, r];
    }
    return null;
  }

  function threatenedPort(game, p, u) {
    const ports = game.cities.filter(city => city.owner === p.index && city.coastal)
      .map(city => ({ city, blockade: game.cityBlockade(city) }))
      .filter(entry => entry.blockade.active)
      .sort((a, b) => HEX.distance(u.c, u.r, a.city.c, a.city.r) -
        HEX.distance(u.c, u.r, b.city.c, b.city.r) || b.blockade.attackPower - a.blockade.attackPower ||
        a.city.id - b.city.id);
    const range = u.isRanged ? u.def.range : 1;
    for (const port of ports) {
      const attackers = [...port.blockade.attackers].sort((a, b) =>
        HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r) || a.id - b.id);
      for (const attacker of attackers) {
        if (HEX.distance(u.c, u.r, attacker.c, attacker.r) <= range) {
          return { ...port, attacker, approach: null };
        }
        const approach = navalInterceptionApproach(game, u, attacker);
        if (approach) return { ...port, attacker, approach };
      }
    }
    return null;
  }

  function blockadeTarget(game, p, u, campaign, enemies) {
    const supply = game.navalSupplyCoverage(u);
    const candidates = game.cities.filter(city => city.coastal && enemies.includes(city.owner) &&
      HEX.neighbors(city.c, city.r).some(([c, r]) => {
        const tile = game.tile(c, r);
        return tile && game.isWater(tile) && game.unitPassable(u, tile) &&
          !game.combatUnitAt(c, r) && game.findPath(u, c, r);
      }));
    return candidates.map(city => {
      const routeValue = game.routes.filter(route => route.fromId === city.id || route.toId === city.id).length * 12;
      const yields = game.cityYields(city);
      const strategic = campaign && campaign.target && campaign.target.id === city.id ? 120 : 0;
      const supported = HEX.neighbors(city.c, city.r).some(([c, r]) => supply.has(game.map.idx(c, r)));
      return { city, score: strategic + (city.isCapital ? 35 : 0) + city.pop * 5 +
        yields.gold * 4 + routeValue + (supported ? 30 : -45) -
        HEX.distance(u.c, u.r, city.c, city.r) };
    }).sort((a, b) => b.score - a.score || a.city.id - b.city.id)[0]?.city || null;
  }

  function continueNavalResupply(game, u) {
    const supply = game.navalSupply(u);
    if (!u.resupplying && !supply.supplied && supply.turns >= NAVAL_SUPPLY.graceTurns)
      u.resupplying = true;
    if (!u.resupplying) return false;
    const destination = game.navalResupplyDestination(u);
    if (!destination) {
      u.path = null; u.fortified = true;
      return true;
    }
    const atPort = destination.c === u.c && destination.r === u.r;
    if (atPort && supply.supplied) {
      if (u.hp < NAVAL_SUPPLY.recoverHp) {
        u.path = null; u.fortified = true;
        return true;
      }
      u.resupplying = false;
      u.fortified = false;
      return false;
    }
    u.fortified = false;
    game.moveUnitTo(u, destination.c, destination.r);
    return true;
  }

  function runShip(game, p, u, campaign = null) {
    const enemies = realWars(game, p);
    if (continueNavalResupply(game, u)) return;
    if (!p.isMinor) {
      const upgrade = game.canUpgrade(u);
      const reserve = campaign && campaign.overseas ? 80 : 200;
      if (upgrade && p.gold > upgrade.cost + reserve && game.upgradeUnit(u)) return;
    }
    if (campaign && enemies.length && game.cities.some(city => city.coastal && enemies.includes(city.owner) &&
        game.cityBlockade(city).active && game.cityBlockade(city).attackers.some(ship => ship.owner === p.index))) {
      campaign.blockaderAssigned = true;
    }
    // A blockading ship is a higher-value target than an opportunistic city
    // shot: engage it directly so the threatened port can reopen this turn.
    const defense = enemies.length ? threatenedPort(game, p, u) : null;
    if (defense) {
      const { attacker } = defense;
      const range = u.isRanged ? u.def.range : 1;
      if (HEX.distance(u.c, u.r, attacker.c, attacker.r) <= range &&
          game.attack(u, attacker.c, attacker.r)) return;
      if (defense.approach) game.moveUnitTo(u, defense.approach[0], defense.approach[1]);
      if (HEX.distance(u.c, u.r, attacker.c, attacker.r) <= range) {
        game.attack(u, attacker.c, attacker.r);
      }
      return;
    }
    if (tryAttack(game, p, u)) return;
    if (enemies.length) {
      // Clear nearby hostile ships and transports before the fleet escorts its
      // own invasion force or converges on the shared coastal objective.
      let waterEnemy = null, waterEnemyD = Infinity;
      for (const e of game.units) {
        if (!enemies.includes(e.owner)) continue;
        const t = game.tile(e.c, e.r);
        if (!game.isWater(t) || (u.isRanged && e.isCivilian)) continue;
        const d = HEX.distance(u.c, u.r, e.c, e.r);
        if (d < waterEnemyD) { waterEnemyD = d; waterEnemy = e; }
      }
      const strategicCity = campaign && campaign.target && campaign.target.coastal &&
        enemies.includes(campaign.target.owner) ? campaign.target : null;
      const portTarget = campaign && !campaign.blockaderAssigned
        ? blockadeTarget(game, p, u, campaign, enemies) : null;
      let escort = null, escortD = Infinity;
      if (campaign && campaign.overseas && !campaign.escortAssigned) {
        for (const friendly of game.units) {
          if (friendly.owner !== p.index || friendly.isCivilian || friendly.def.naval ||
              !game.isEmbarked(friendly)) continue;
          const d = HEX.distance(u.c, u.r, friendly.c, friendly.r);
          if (d < escortD) { escortD = d; escort = friendly; }
        }
        if (escort) campaign.escortAssigned = true;
      }
      let target = waterEnemyD <= 6 ? waterEnemy : null;
      if (!target && escort) {
        if (escortD > 2) target = escort;
        else { u.fortified = true; return; }
      }
      let blockadeMission = false;
      if (!target && portTarget && campaign && !campaign.blockaderAssigned) {
        campaign.blockaderAssigned = true;
        blockadeMission = true;
        target = portTarget;
      }
      if (!target && strategicCity) target = strategicCity;
      if (!target && waterEnemy) target = waterEnemy;
      if (!target) target = game.cities.filter(c => enemies.includes(c.owner) && c.coastal)
        .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) -
          HEX.distance(u.c, u.r, b.c, b.r) || a.id - b.id)[0] || null;
      if (target) {
        const bestD = HEX.distance(u.c, u.r, target.c, target.r);
        if (u.hp < 40 && bestD > 2) { u.fortified = true; return; }
        if (!blockadeMission && u.isRanged && bestD <= u.def.range) { tryAttack(game, p, u); return; }
        const targetCity = target.name !== undefined ? target : null;
        const dest = targetCity && campaign
          ? (blockadeMission ? navalBlockadeApproach(game, u, targetCity, campaign) :
            navalCampaignApproach(game, u, targetCity, campaign))
          : nearestApproach(game, u, target.c, target.r);
        if (dest) game.moveUnitTo(u, dest[0], dest[1]);
        tryAttack(game, p, u);
      }
      return;
    }
    // Peacetime fleets chart reachable seas and reveal foreign shores. Once
    // their sailing range is explored, they return to defended home waters.
    const explore = navalExploreTarget(game, p, u);
    if (explore && game.moveUnitTo(u, explore.c, explore.r)) return;
    const home = game.cities.filter(c => c.owner === p.index && c.coastal)
      .sort((a, b) => HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r))[0];
    if (home && HEX.distance(u.c, u.r, home.c, home.r) > 3) {
      const dest = nearestApproach(game, u, home.c, home.r);
      if (dest) game.moveUnitTo(u, dest[0], dest[1]);
    } else {
      u.fortified = true;
    }
  }

  function runMilitary(game, p, u, campaign = null) {
    const enemies = realWars(game, p);
    // chase off raiders prowling nearby
    if (!enemies.length && game.barbIndex >= 0) {
      let raider = null, rd = 4;
      for (const v of game.units) {
        if (v.owner !== game.barbIndex || v.isCivilian) continue;
        const d = HEX.distance(u.c, u.r, v.c, v.r);
        if (d <= rd) { rd = d; raider = v; }
      }
      if (raider) {
        if (tryAttack(game, p, u)) return;
        const dest = nearestApproach(game, u, raider.c, raider.r);
        if (dest) game.moveUnitTo(u, dest[0], dest[1]);
        tryAttack(game, p, u);
        return;
      }
    }

    // modernize old troops when the treasury allows
    if (!p.isMinor) {
      const up = game.canUpgrade(u);
      if (up && p.gold > up.cost + 200) game.upgradeUnit(u);
    }

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
      // Survival and resistance chapters are positional battles. Keep the
      // defending army around its objective instead of launching a normal
      // cross-map city campaign, then intercept formations that enter the
      // capital's defensive perimeter.
      if (runScenarioDefense(game, p, u, campaign, enemies)) return;
      // 2. Concentrate the land army on a shared campaign objective. If a
      // unit captures it mid-loop, refresh the objective for the next unit.
      if (campaign && (!campaign.target || !game.cities.includes(campaign.target) ||
          !enemies.includes(campaign.target.owner))) campaign.target = campaignTarget(game, p);
      let target = campaign ? campaign.target : campaignTarget(game, p);
      let bestD = target ? HEX.distance(u.c, u.r, target.c, target.r) : Infinity;
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
        // melee waits at the walls while bombardment softens a healthy city
        const targetCity = target.name !== undefined ? target : null;
        if (targetCity && !u.isRanged && !u.def.siege && targetCity.hp > 120 && bestD <= 2) {
          if (!tryAttack(game, p, u, true)) u.fortified = true; // hit units, spare the walls
          return;
        }
        // step toward target (stop next to it, attack handled next turn/iteration)
        const dest = targetCity && campaign
          ? campaignApproach(game, u, targetCity, campaign)
          : nearestApproach(game, u, target.c, target.r);
        if (dest) game.moveUnitTo(u, dest[0], dest[1]);
        tryAttack(game, p, u);
      }
      return;
    }

    // 3. peace: escort exposed settlers first
    if (!p.isMinor) {
      const settler = game.units.find(v => v.owner === p.index && v.type === "SETTLER" &&
        HEX.distance(v.c, v.r, u.c, u.r) <= 4 &&
        !game.units.some(m => m !== u && m.owner === p.index && !m.isCivilian &&
          HEX.distance(m.c, m.r, v.c, v.r) <= 1));
      if (settler && HEX.distance(u.c, u.r, settler.c, settler.r) > 1) {
        const dest = nearestApproach(game, u, settler.c, settler.r);
        if (dest) { game.moveUnitTo(u, dest[0], dest[1]); return; }
      }
    }
    // then burn nearby barbarian camps for the bounty
    if (game.camps.length && !p.isMinor) {
      let camp = null, campD = 7;
      for (const cp of game.camps) {
        const d = HEX.distance(u.c, u.r, cp.c, cp.r);
        if (d <= campD) { campD = d; camp = cp; }
      }
      if (camp) {
        game.moveUnitTo(u, camp.c, camp.r);
        tryAttack(game, p, u);
        return;
      }
    }
    // garrison cities, otherwise fortify near home
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

  function runScenarioDefense(game, p, u, campaign, enemies) {
    const objective = game.scenario && SCENARIOS[game.scenario] && SCENARIOS[game.scenario].victory;
    if (p.index !== 0 || !objective || !["survive", "resistance"].includes(objective.type)) return false;
    const home = game.cities.find(c => c.id === p.originalCapitalId && c.owner === p.index) ||
      game.cities.find(c => c.owner === p.index && c.isCapital);
    if (!home) return false;

    const threats = game.units.filter(enemy => enemies.includes(enemy.owner) && !enemy.isCivilian &&
      HEX.distance(enemy.c, enemy.r, home.c, home.r) <= 7).sort((a, b) =>
      HEX.distance(a.c, a.r, home.c, home.r) - HEX.distance(b.c, b.r, home.c, home.r) ||
      HEX.distance(u.c, u.r, a.c, a.r) - HEX.distance(u.c, u.r, b.c, b.r) || a.id - b.id);
    if (threats.length) {
      const target = threats[0];
      const targetD = HEX.distance(u.c, u.r, target.c, target.r);
      if (u.hp < 40 && targetD > 2) { u.fortified = true; return true; }
      const attackRange = u.isRanged ? u.def.range : 1;
      const dest = HEX.ring(target.c, target.r, attackRange).filter(([c, r]) =>
        HEX.distance(c, r, target.c, target.r) === attackRange &&
        HEX.distance(c, r, home.c, home.r) <= 7).sort((a, b) =>
        HEX.distance(u.c, u.r, a[0], a[1]) - HEX.distance(u.c, u.r, b[0], b[1]) ||
        a[1] - b[1] || a[0] - b[0]).find(([c, r]) => {
          const tile = game.tile(c, r);
          const occupant = game.combatUnitAt(c, r);
          return tile && !game.isWater(tile) && game.unitPassable(u, tile) &&
            (!occupant || occupant.id === u.id) && game.findPath(u, c, r);
        });
      if (dest)
        game.moveUnitTo(u, dest[0], dest[1]);
      if (!tryAttack(game, p, u)) u.fortified = true;
      return true;
    }

    if (HEX.distance(u.c, u.r, home.c, home.r) <= 3) {
      u.path = null;
      u.fortified = true;
      return true;
    }
    const radius = u.isRanged ? 2 : 1;
    const reserved = campaign ? campaign.defenseApproaches : new Set();
    const positions = HEX.ring(home.c, home.r, radius).sort((a, b) =>
      HEX.distance(u.c, u.r, a[0], a[1]) - HEX.distance(u.c, u.r, b[0], b[1]) ||
      a[1] - b[1] || a[0] - b[0]);
    for (const [c, r] of positions) {
      const key = c + "," + r;
      const tile = game.tile(c, r);
      if (reserved.has(key) || !tile || game.isWater(tile) || !game.unitPassable(u, tile) ||
          game.combatUnitAt(c, r) || !game.findPath(u, c, r)) continue;
      reserved.add(key);
      game.moveUnitTo(u, c, r);
      return true;
    }
    u.fortified = true;
    return true;
  }

  function tryAttack(game, p, u, excludeCity = false) {
    if (u.attacked || u.moves <= 0 ||
        (game.isEmbarked(u) && !u.promos.includes("AMPHIBIOUS"))) return false;
    const range = u.isRanged ? u.def.range : 1;
    let best = null, bestValue = -Infinity;
    for (const [c, r] of HEX.ring(u.c, u.r, range)) {
      const t = game.tile(c, r);
      if (!t) continue;
      if (game.isEmbarked(u) && !game.canAttackFromEmbarked(u, t)) continue;
      // melee reach restrictions across the shoreline
      if (!u.isRanged && !u.def.naval && game.isWater(t)) continue;
      if (!u.isRanged && u.def.naval && !game.isWater(t) && !t.city) continue;
      const enemyUnit = game.combatUnitAt(c, r);
      const enemyCity = !excludeCity && t.city && p.atWarWith.has(t.city.owner) ? t.city : null;
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

  function campaignApproach(game, u, target, campaign) {
    const range = u.isRanged ? u.def.range : 1;
    const candidates = HEX.ring(target.c, target.r, range).filter(([c, r]) =>
      HEX.distance(c, r, target.c, target.r) === range).sort((a, b) =>
      HEX.distance(u.c, u.r, a[0], a[1]) - HEX.distance(u.c, u.r, b[0], b[1]) ||
      a[1] - b[1] || a[0] - b[0]);
    for (const [c, r] of candidates) {
      const key = c + "," + r;
      if (campaign.approaches.has(key)) continue;
      const tile = game.tile(c, r);
      if (!tile || game.isWater(tile) || !game.unitPassable(u, tile)) continue;
      const occupant = game.combatUnitAt(c, r);
      if (occupant && occupant.id !== u.id) continue;
      if (tile.city && tile.city.owner !== u.owner) continue;
      if (!game.findPath(u, c, r)) continue;
      campaign.approaches.add(key);
      return [c, r];
    }
    return nearestApproach(game, u, target.c, target.r);
  }

  function navalCampaignApproach(game, u, target, campaign) {
    const range = u.isRanged ? u.def.range : 1;
    const supply = game.navalSupplyCoverage(u);
    const candidates = HEX.ring(target.c, target.r, range).filter(([c, r]) =>
      HEX.distance(c, r, target.c, target.r) === range).sort((a, b) =>
      Number(!supply.has(game.map.idx(a[0], a[1]))) - Number(!supply.has(game.map.idx(b[0], b[1]))) ||
      HEX.distance(u.c, u.r, a[0], a[1]) - HEX.distance(u.c, u.r, b[0], b[1]) ||
      a[1] - b[1] || a[0] - b[0]);
    for (const [c, r] of candidates) {
      const key = c + "," + r;
      if (campaign.navalApproaches.has(key)) continue;
      const tile = game.tile(c, r);
      if (!tile || !game.isWater(tile) || !game.unitPassable(u, tile) || game.combatUnitAt(c, r)) continue;
      if (!game.findPath(u, c, r)) continue;
      campaign.navalApproaches.add(key);
      return [c, r];
    }
    return nearestApproach(game, u, target.c, target.r);
  }

  function navalBlockadeApproach(game, u, target, campaign) {
    const supply = game.navalSupplyCoverage(u);
    const candidates = HEX.ring(target.c, target.r, BLOCKADE.radius).filter(([c, r]) =>
      HEX.distance(c, r, target.c, target.r) === BLOCKADE.radius).sort((a, b) =>
      Number(!supply.has(game.map.idx(a[0], a[1]))) - Number(!supply.has(game.map.idx(b[0], b[1]))) ||
      HEX.distance(u.c, u.r, a[0], a[1]) - HEX.distance(u.c, u.r, b[0], b[1]) ||
      a[1] - b[1] || a[0] - b[0]);
    for (const [c, r] of candidates) {
      const key = c + "," + r;
      if (campaign.navalApproaches.has(key)) continue;
      const tile = game.tile(c, r);
      if (!tile || !game.isWater(tile) || !game.unitPassable(u, tile) || game.combatUnitAt(c, r)) continue;
      if (!game.findPath(u, c, r)) continue;
      campaign.navalApproaches.add(key);
      return [c, r];
    }
    return navalCampaignApproach(game, u, target, campaign);
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

  return { takeTurn, autoExplore, victoryFocus, chooseWarTarget, campaignTarget,
    campaignIsOverseas, hasOverseasRival, armyRole, desiredArmyRoles };
})();
