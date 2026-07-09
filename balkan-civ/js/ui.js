// ============================================================
// UI: DOM panels, input, screens
// ============================================================
"use strict";

const UI = (() => {
  let game = null, rend = null;
  const $ = (id) => document.getElementById(id);

  // ---------------- start screen ----------------
  function showStartScreen() {
    const wrap = $("civ-cards");
    wrap.innerHTML = "";
    let chosen = CIV_IDS[0];
    for (const id of CIV_IDS) {
      const civ = CIVS[id];
      const uu = UNITS[civ.uu];
      const card = document.createElement("div");
      card.className = "civ-card";
      card.innerHTML = `
        <div class="civ-flag" style="background:${civ.color};border-color:${civ.color2}"></div>
        <h3>${civ.name}</h3>
        <div class="leader">${civ.leader}</div>
        <div class="trait"><b>${civ.trait}</b><br>${civ.traitDesc}</div>
        <div class="uu">${uu.icon} <b>${uu.name}</b> — ${uu.blurb}</div>`;
      card.onclick = () => {
        document.querySelectorAll(".civ-card").forEach(c => c.classList.remove("sel"));
        card.classList.add("sel");
        chosen = id;
      };
      if (id === chosen) card.classList.add("sel");
      wrap.appendChild(card);
    }
    const saved = localStorage.getItem("balkan-civ-save");
    $("btn-continue").style.display = saved ? "inline-block" : "none";
    $("btn-continue").onclick = () => {
      try {
        game = Game.deserialize(saved);
        startPlaying();
      } catch (e) {
        console.error(e);
        alert("Save file could not be loaded — starting fresh.");
        localStorage.removeItem("balkan-civ-save");
      }
    };
    $("btn-start").onclick = () => {
      const numOpp = parseInt($("sel-opponents").value, 10);
      const size = $("sel-mapsize").value;
      const dims = { small: [36, 28], standard: [44, 34], large: [54, 42] }[size];
      game = new Game({ playerCiv: chosen, numOpponents: numOpp, mapW: dims[0], mapH: dims[1],
        mapType: $("sel-maptype").value });
      startPlaying();
    };
    $("start-screen").style.display = "flex";
    $("game-ui").style.display = "none";
  }

  function startPlaying() {
    $("start-screen").style.display = "none";
    $("game-ui").style.display = "block";
    resize();
    const firstUnit = game.units.find(u => u.owner === 0);
    if (firstUnit) rend.centerOn(game, firstUnit.c, firstUnit.r);
    selectUnit(firstUnit || null);
    refreshAll();
  }

  // ---------------- selection ----------------
  function selectUnit(u) {
    rend.selected = u;
    rend.selectedCity = null;
    if (u) {
      rend.reachable = game.reachableTiles(u);
      rend.attackable = computeAttackable(u);
    } else {
      rend.reachable = []; rend.attackable = [];
    }
    rend.dirty = true;
    refreshUnitPanel();
    $("city-panel").style.display = "none";
  }

  function computeAttackable(u) {
    if (u.isCivilian || u.attacked || u.moves <= 0 || game.isEmbarked(u)) return [];
    const p = game.players[0];
    const range = u.isRanged ? u.def.range : 1;
    const out = [];
    for (const [c, r] of HEX.ring(u.c, u.r, range)) {
      const t = game.tile(c, r);
      if (!t || !p.visible[game.map.idx(c, r)]) continue;
      if (!u.isRanged && !u.def.naval && game.isWater(t)) continue;      // no melee out to sea
      if (!u.isRanged && u.def.naval && !game.isWater(t) && !t.city) continue; // ships raid coasts only
      const cu = game.combatUnitAt(c, r);
      const civ = game.civilianAt(c, r);
      if ((cu && p.atWarWith.has(cu.owner)) ||
          (t.city && p.atWarWith.has(t.city.owner) && t.city.hp > 0) ||
          (civ && p.atWarWith.has(civ.owner))) {
        out.push([c, r]);
      }
    }
    return out;
  }

  function selectCity(city) {
    rend.selected = null;
    rend.reachable = []; rend.attackable = [];
    rend.selectedCity = city;
    rend.dirty = true;
    $("unit-panel").style.display = "none";
    showCityPanel(city);
  }

  // ---------------- unit panel ----------------
  function refreshUnitPanel() {
    const u = rend.selected;
    const panel = $("unit-panel");
    if (!u || !game.units.includes(u)) { panel.style.display = "none"; return; }
    panel.style.display = "flex";
    const def = u.def;
    $("unit-info").innerHTML = `
      <span class="unit-icon">${def.icon}</span>
      <div><b>${def.name}</b>${u.level ? " " + "⭐".repeat(u.level) : ""}${game.isEmbarked(u) ? " <span class='alert'>⛵ embarked</span>" : ""}<br>
      <span class="dim">HP ${u.hp}/100 · Moves ${u.moves}/${def.moves}
      ${def.cs ? " · Str " + def.cs : ""}${def.rs ? " · Ranged " + def.rs + " (r" + def.range + ")" : ""}
      ${!u.isCivilian ? " · XP " + u.xp : ""}</span>
      ${u.building ? `<br><span class="alert">Building ${IMPROVEMENT[u.building.type].name} — ${u.building.turnsLeft} turn${u.building.turnsLeft > 1 ? "s" : ""} left</span>` : ""}</div>`;
    const actions = $("unit-actions");
    actions.innerHTML = "";
    const btn = (label, fn, enabled = true) => {
      const b = document.createElement("button");
      b.textContent = label;
      b.disabled = !enabled;
      b.onclick = fn;
      actions.appendChild(b);
    };
    if (u.type === "SETTLER") {
      const t = game.tile(u.c, u.r);
      const canFound = t && TERRAIN[t.terrain].passable && !t.city &&
        ![...HEX.ring(u.c, u.r, 2)].some(([c, r]) => {
          const n = game.tile(c, r); return n && n.city;
        });
      btn("🏛️ Found City", () => {
        const city = game.foundCity(u);
        if (city) { selectCity(city); refreshAll(); }
      }, canFound && u.moves > 0);
    }
    if (u.def.missionary) {
      const target = game.missionaryTarget(u);
      btn(`🕊️ Spread Religion (${u.charges} left)`, () => {
        if (game.spreadFromMissionary(u)) {
          selectUnit(game.units.includes(u) ? u : null);
          refreshAll();
        }
      }, !!target && u.moves > 0 && game.players[0].religionId !== null);
    }
    if (u.def.worker) {
      if (u.building) {
        btn("🚫 Cancel Job", () => { u.building = null; u.moves = u.def.moves; selectUnit(u); refreshAll(); });
      } else {
        for (const key of Object.keys(IMPROVEMENT)) {
          if (game.canBuildImprovement(u, key)) {
            btn(`${IMPROVEMENT[key].icon} Build ${IMPROVEMENT[key].name} (${IMPROVEMENT[key].turns}t)`, () => {
              game.startImprovement(u, key);
              cycleNextUnit(); refreshAll();
            }, u.moves > 0);
          }
        }
      }
    }
    if (!u.isCivilian) {
      btn(u.fortified ? "⛺ Wake" : "🛡️ Fortify", () => {
        u.fortified = !u.fortified;
        if (u.fortified) u.moves = 0;
        selectUnit(u); refreshAll();
      });
    }
    btn("⏭️ Skip", () => { u.moves = 0; cycleNextUnit(); refreshAll(); });
    btn("❌ Disband", () => { game.removeUnit(u); selectUnit(null); refreshAll(); });
  }

  function cycleNextUnit() {
    const candidates = game.units.filter(u => u.owner === 0 && u.moves > 0 && !u.fortified &&
      !u.building && !(u.path && u.path.length));
    if (!candidates.length) { selectUnit(null); return; }
    const cur = rend.selected ? candidates.indexOf(rend.selected) : -1;
    const next = candidates[(cur + 1) % candidates.length];
    selectUnit(next);
    rend.centerOn(game, next.c, next.r);
  }

  // ---------------- city panel ----------------
  function showCityPanel(city) {
    const panel = $("city-panel");
    panel.style.display = "block";
    const y = game.cityYields(city);
    const isMine = city.owner === 0;
    let html = `
      <div class="panel-head">
        <b>${city.name}</b> ${city.isCapital ? "★" : ""} <span class="dim">(${CIVS[game.players[city.owner].civId].name})</span>
        <button class="close" onclick="UI.closeCity()">✕</button>
      </div>
      <div class="city-stats">
        Pop ${city.pop} · 🍞${y.food} ⚙️${y.prod} 💰${y.gold} 🔬${y.sci} 🎭${Math.floor(y.culture)}${y.faith ? " ☦️" + y.faith : ""}<br>
        <span class="dim">Growth ${city.food}/${city.foodNeeded()} · HP ${city.hp}/${city.maxHp}</span>
        ${city.religion !== null ? `<br><span class="dim">Faith: ${game.religions[city.religion].icon} ${game.religions[city.religion].name}</span>` : ""}
      </div>`;
    if (city.buildings.length) {
      html += `<div class="city-buildings">${city.buildings.map(b => BUILDINGS[b].icon + " " + BUILDINGS[b].name).join(" · ")}</div>`;
    }
    if (isMine) {
      const p0 = game.players[0];
      if (p0.religionId !== null) {
        const cost = UNITS.MISSIONARY.faithCost;
        html += `<div class="prod-current"><button ${p0.faith >= cost ? "" : "disabled"}
          onclick="UI.buyMissionary(${city.id})">🙏 Missionary (${cost} ☦️)</button></div>`;
      }
      const opts = game.productionOptions(city);
      const cur = city.producing;
      html += `<div class="prod-current">Producing: <b>${cur
        ? (cur.kind === "unit" ? UNITS[cur.key].icon + " " + UNITS[cur.key].name : BUILDINGS[cur.key].icon + " " + BUILDINGS[cur.key].name) +
          ` (${city.prodStored}/${cur.kind === "unit" ? UNITS[cur.key].cost : BUILDINGS[cur.key].cost})`
        : "—"}</b></div>`;
      html += `<div class="prod-list">`;
      for (const o of opts) {
        const turns = Math.max(1, Math.ceil((o.cost - (cur && cur.key === o.key ? city.prodStored : 0)) / Math.max(1, y.prod)));
        const price = game.buyCost(o.cost);
        const afford = game.players[0].gold >= price;
        html += `<div class="prod-item ${o.wonder ? "wonder" : ""}">
          <span>${o.icon} ${o.name}</span>
          <span class="dim">${o.cost}⚙️ ~${turns}t</span>
          <button onclick="UI.setProduction(${city.id},'${o.kind}','${o.key}')">Build</button>
          <button ${afford ? "" : "disabled"} onclick="UI.buyItem(${city.id},'${o.kind}','${o.key}')">💰${price}</button>
        </div>`;
      }
      html += `</div>`;
    }
    panel.innerHTML = html;
  }

  function setProduction(cityId, kind, key) {
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    city.producing = { kind, key };
    showCityPanel(city);
    refreshAll();
  }

  function buyItem(cityId, kind, key) {
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    const cost = kind === "unit" ? UNITS[key].cost : BUILDINGS[key].cost;
    if (game.purchase(city, { kind, key, cost })) {
      showCityPanel(city);
      refreshAll();
    }
  }

  function closeCity() {
    rend.selectedCity = null;
    $("city-panel").style.display = "none";
    rend.dirty = true;
  }

  // ---------------- tech screen ----------------
  function showTechScreen() {
    const p = game.players[0];
    const modal = $("tech-modal");
    modal.style.display = "flex";
    const body = $("tech-body");
    let html = "";
    for (let era = 0; era < ERAS.length; era++) {
      html += `<h3>${ERAS[era]} Era</h3><div class="tech-row">`;
      for (const [key, t] of Object.entries(TECHS)) {
        if (t.era !== era) continue;
        const has = p.techs.has(key);
        const avail = !has && t.req.every(r => p.techs.has(r));
        const researching = p.researching === key;
        const unlocks = [];
        for (const [uk, u] of Object.entries(UNITS)) {
          if (u.tech === key && (!u.uu || u.uu === p.civId)) unlocks.push(u.icon + " " + u.name);
        }
        for (const [bk, b] of Object.entries(BUILDINGS)) if (b.tech === key) unlocks.push(b.icon + " " + b.name);
        html += `<div class="tech ${has ? "done" : avail ? "avail" : "locked"} ${researching ? "active" : ""}"
          ${avail ? `onclick="UI.pickTech('${key}')"` : ""}>
          <b>${t.name}</b> <span class="dim">${t.cost}🔬</span>
          ${researching ? `<div class="dim">researching (${Math.floor(p.scienceStored)}/${t.cost})</div>` : ""}
          ${unlocks.length ? `<div class="unlocks">${unlocks.join(", ")}</div>` : ""}
          ${t.req.length ? `<div class="req dim">needs: ${t.req.map(r => TECHS[r].name).join(", ")}</div>` : ""}
        </div>`;
      }
      html += `</div>`;
    }
    body.innerHTML = html;
  }

  function pickTech(key) {
    game.players[0].researching = key;
    $("tech-modal").style.display = "none";
    refreshAll();
  }

  // ---------------- religion ----------------
  let foundingPromptTurn = -1;

  function showReligionScreen() {
    const p = game.players[0];
    $("religion-modal").style.display = "flex";
    const body = $("religion-body");
    let html = `<div class="diplo-row">Your faith: <b>☦️ ${Math.floor(p.faith)}</b>`;
    if (p.religionId === null) {
      if (game.religions.length >= MAX_RELIGIONS) {
        html += ` <span class="dim">— all ${MAX_RELIGIONS} religions have been founded.</span>`;
      } else {
        html += ` <span class="dim">— found a religion at ${RELIGION_FOUND_COST(game.religions.length)} faith.</span>`;
        if (game.canFoundReligion(0)) html += ` <button onclick="UI.showFoundingModal()">🕊️ Found Religion</button>`;
      }
    } else {
      const r = game.religions[p.religionId];
      html += ` <span class="dim">— buy a Missionary for ${UNITS.MISSIONARY.faithCost} faith from any city panel.</span>`;
    }
    html += `</div>`;
    if (!game.religions.length) {
      html += `<div class="diplo-row dim">No religion has been founded yet. Build Shrines and Temples to generate faith.</div>`;
    }
    for (const r of game.religions) {
      const founder = game.players[r.founder];
      const holy = game.cities.find(c => c.id === r.holyCityId);
      html += `<div class="diplo-row" style="border-left:6px solid ${founder.civ.color}">
        <b>${r.icon} ${r.name}</b> <span class="dim">founded by ${founder.civ.name}${holy ? " · holy city " + holy.name : ""}</span><br>
        <span class="dim">${BELIEFS[r.belief].name}: ${BELIEFS[r.belief].desc} · ${game.religionFollowers(r.id)} following cities</span>
      </div>`;
    }
    body.innerHTML = html;
  }

  function showFoundingModal() {
    const p = game.players[0];
    if (!game.canFoundReligion(0)) return;
    $("religion-modal").style.display = "none";
    $("founding-modal").style.display = "flex";
    const names = game.availableReligionNames();
    const pref = names.find(n => n.name === CIV_RELIGION[p.civId]) || names[0];
    let html = `<p>Your prophets await (${RELIGION_FOUND_COST(game.religions.length)} faith). Choose a faith and a founder belief:</p>
      <div class="diplo-row">Religion:
      <select id="sel-religion-name">${names.map(n =>
        `<option value="${n.name}" ${n.name === pref.name ? "selected" : ""}>${n.icon} ${n.name}</option>`).join("")}
      </select></div>`;
    html += Object.entries(BELIEFS).map(([key, b], i) =>
      `<div class="diplo-row"><label><input type="radio" name="belief" value="${key}" ${i === 0 ? "checked" : ""}>
       <b>${b.name}</b> — <span class="dim">${b.desc}</span></label></div>`).join("");
    html += `<div style="margin-top:10px"><button onclick="UI.confirmFounding()">🕊️ Found Religion</button>
      <button onclick="document.getElementById('founding-modal').style.display='none'">Later</button></div>`;
    $("founding-body").innerHTML = html;
  }

  function confirmFounding() {
    const name = $("sel-religion-name").value;
    const entry = RELIGION_NAMES.find(r => r.name === name);
    const belief = document.querySelector("input[name=belief]:checked").value;
    if (game.foundReligion(0, entry.name, entry.icon, belief)) {
      $("founding-modal").style.display = "none";
      refreshAll();
    }
  }

  function buyMissionary(cityId) {
    const city = game.cities.find(c => c.id === cityId);
    if (city && game.buyMissionary(city)) { showCityPanel(city); refreshAll(); }
  }

  // ---------------- diplomacy screen ----------------
  function showDiploScreen() {
    const p = game.players[0];
    const modal = $("diplo-modal");
    modal.style.display = "flex";
    const body = $("diplo-body");
    let html = "";
    for (const p2 of game.players) {
      if (p2.index === 0 || p2.isMinor) continue;
      const met = p.met.has(p2.index);
      const civ = p2.civ;
      html += `<div class="diplo-row" style="border-left:6px solid ${met ? civ.color : "#555"}">
        <div><b>${met ? civ.name : "Unknown Civilization"}</b>
          ${met ? `<span class="dim"> — ${civ.leader}</span>` : ""}
          ${!p2.alive ? " <span class='dead'>☠️ destroyed</span>" : ""}</div>`;
      if (met && p2.alive) {
        const atWar = p.atWarWith.has(p2.index);
        html += `<div class="dim">Score ${game.score(p2.index)} · Military ${Math.floor(game.militaryPower(p2.index))} ·
          ${atWar ? "<b class='war'>AT WAR</b>" : "at peace"}</div>
          <button onclick="UI.diploAction(${p2.index})">${atWar ? "☮️ Propose Peace" : "⚔️ Declare War"}</button>`;
      }
      html += `</div>`;
    }
    const minors = game.players.filter(p2 => p2.isMinor && p.met.has(p2.index));
    if (minors.length) {
      html += `<h3>City-States</h3>`;
      for (const m of minors) {
        const type = MINOR_TYPES[m.civ.minorType];
        if (!m.alive) {
          html += `<div class="diplo-row" style="border-left:6px solid #555"><b>${m.civ.name}</b>
            <span class='dead'>☠️ destroyed</span></div>`;
          continue;
        }
        const status = game.minorStatus(0, m.index);
        const inf = Math.floor(p.influence[m.index] || 0);
        const statusTxt = { war: "<b class='war'>AT WAR</b>", ally: "<b style='color:#2ecc71'>ALLY</b>",
          friend: "<b style='color:#f1c40f'>Friend</b>", neutral: "neutral" }[status];
        html += `<div class="diplo-row" style="border-left:6px solid ${m.civ.color}">
          <div><b>${m.civ.name}</b> <span class="dim">${type.icon} ${type.name}</span> · ${statusTxt}</div>
          <div class="dim">${type.desc}</div>
          <div class="dim">Influence: ${inf} (friend ${INFLUENCE_FRIEND} · ally ${INFLUENCE_ALLY})</div>`;
        if (status !== "war") {
          html += `<button ${p.gold >= 100 ? "" : "disabled"} onclick="UI.gift(${m.index},100)">🎁 100💰 (+25)</button>
            <button ${p.gold >= 250 ? "" : "disabled"} onclick="UI.gift(${m.index},250)">🎁 250💰 (+70)</button>`;
        }
        html += `<button onclick="UI.diploAction(${m.index})">${status === "war" ? "☮️ Propose Peace" : "⚔️ Declare War"}</button>
        </div>`;
      }
    }
    html += `<div class="diplo-row"><b>Your score:</b> ${game.score(0)} · Military ${Math.floor(game.militaryPower(0))}</div>`;
    body.innerHTML = html;
  }

  function gift(minorIdx, amount) {
    if (game.giftInfluence(0, minorIdx, amount)) {
      showDiploScreen();
      refreshAll();
    }
  }

  function diploAction(idx) {
    const p = game.players[0];
    if (p.atWarWith.has(idx)) {
      // AI accepts peace if weary or losing
      const weary = (game.players[idx].warWeariness[0] || 0) > 12;
      const losing = game.militaryPower(idx) < game.militaryPower(0) * 0.8;
      if (weary || losing) game.makePeace(0, idx);
      else game.notify(`${game.players[idx].civ.name} refuses to make peace!`);
    } else {
      game.declareWar(0, idx);
    }
    showDiploScreen();
    refreshAll();
  }

  // ---------------- top bar / notifications ----------------
  function refreshTopBar() {
    const p = game.players[0];
    let gold = 0, sci = 0, faith = 0;
    for (const c of game.cities) {
      if (c.owner !== 0) continue;
      const y = game.cityYields(c);
      gold += y.gold; sci += y.sci; faith += y.faith;
    }
    gold -= Math.max(0, game.units.filter(u => u.owner === 0).length - 4);
    gold += game.minorBonuses(0).gold;
    if (p.religionId !== null && game.religions[p.religionId].belief === "TITHE") {
      gold += game.religionFollowers(p.religionId);
    }
    const tech = p.researching ? TECHS[p.researching] : null;
    $("stat-turn").textContent = `Turn ${game.turn}/${game.maxTurns}`;
    $("stat-era").textContent = ERAS[p.era()] + " Era";
    $("stat-gold").textContent = `💰 ${Math.floor(p.gold)} (${gold >= 0 ? "+" : ""}${gold})`;
    $("stat-sci").innerHTML = tech
      ? `🔬 ${tech.name} ${Math.floor(p.scienceStored)}/${tech.cost} (+${sci})`
      : `🔬 <b class="alert">choose research!</b> (+${sci})`;
    // happiness + golden age
    const hap = game.happinessOf(0);
    const lux = game.luxuryTypesOf(0);
    const nCities = game.cities.filter(c => c.owner === 0).length;
    const popTotal = game.cities.filter(c => c.owner === 0).reduce((a, c) => a + c.pop, 0);
    const happyEl = $("stat-happy");
    if (p.goldenAgeTurns > 0) {
      happyEl.innerHTML = `✨ <b style="color:#f1c40f">GOLDEN AGE</b> (${p.goldenAgeTurns})`;
      happyEl.title = "+20% gold and production";
    } else {
      happyEl.innerHTML = hap >= 0 ? `😊 +${hap}` : `<b class="${hap < HAPPINESS.strikeAt ? "war" : "alert"}">😞 ${hap}</b>`;
      happyEl.title = `Happiness: ${HAPPINESS.base} base + ${lux.length * HAPPINESS.perLuxury} luxuries (${lux.map(l => RESOURCE[l].icon).join("") || "none"}) + buildings − ${nCities * HAPPINESS.perCity} cities − ${Math.floor(popTotal * HAPPINESS.perPop)} population` +
        `\nGolden Age: ${Math.floor(p.gaMeter)}/${GOLDEN_AGE.threshold(p.gaCount)} (surplus happiness fills the meter)`;
    }
    const relIcon = p.religionId !== null ? game.religions[p.religionId].icon : "☦️";
    $("stat-faith").innerHTML = game.canFoundReligion(0)
      ? `${relIcon} <b class="alert">found a religion!</b>`
      : `${relIcon} ${Math.floor(p.faith)} (+${faith})`;
    $("stat-score").textContent = `🏆 ${game.score(0)}`;
  }

  function refreshNotifications() {
    const list = $("notif-list");
    const recent = game.notifications.slice(-6);
    list.innerHTML = recent.map(n => `<div class="notif"><span class="dim">T${n.turn}</span> ${n.msg}</div>`).join("");
    list.scrollTop = list.scrollHeight;
  }

  function refreshAll() {
    refreshTopBar();
    refreshNotifications();
    refreshUnitPanel();
    if (rend.selectedCity) showCityPanel(rend.selectedCity);
    if (rend.selected) {
      rend.reachable = game.reachableTiles(rend.selected);
      rend.attackable = computeAttackable(rend.selected);
    }
    rend.dirty = true;
    if (game.over) showVictory();
  }

  // ---------------- end turn ----------------
  function endTurn() {
    const p = game.players[0];
    if (!p.researching && p.availableTechs().length) { showTechScreen(); return; }
    const idle = game.units.find(u => u.owner === 0 && u.moves > 0 && !u.fortified && !u.attacked &&
      !u.building && !(u.path && u.path.length));
    const cityIdle = game.cities.find(c => c.owner === 0 && !c.producing);
    if (cityIdle) { selectCity(cityIdle); rend.centerOn(game, cityIdle.c, cityIdle.r); return; }
    if (idle && !endTurn.skipIdle) {
      selectUnit(idle);
      rend.centerOn(game, idle.c, idle.r);
      endTurn.skipIdle = true; // second click ends anyway
      $("btn-endturn").textContent = "Units idle — End Anyway";
      return;
    }
    endTurn.skipIdle = false;
    $("btn-endturn").textContent = "End Turn ⏵";
    game.endTurn();
    try { localStorage.setItem("balkan-civ-save", game.serialize()); } catch (e) { /* storage full */ }
    if (rend.selected && !game.units.includes(rend.selected)) rend.selected = null;
    refreshAll();
    if (!game.over) cycleNextUnit();
    if (game.canFoundReligion(0) && foundingPromptTurn !== game.turn) {
      foundingPromptTurn = game.turn;
      showFoundingModal();
    }
  }

  function showVictory() {
    const modal = $("victory-modal");
    modal.style.display = "flex";
    const won = game.winner === 0;
    const civ = CIVS[game.players[game.winner].civId];
    $("victory-body").innerHTML = `
      <h2>${won ? "🏆 VICTORY!" : "☠️ DEFEAT"}</h2>
      <p>${civ.name} ${won ? "— your empire —" : ""} has won a <b>${game.victoryType}</b> victory
      on turn ${game.turn}.</p>
      <p class="dim">Final score: ${game.players.filter(p => !p.isMinor).map(p => `${p.civ.name} ${game.score(p.index)}`).join(" · ")}</p>
      <button onclick="UI.newGame()">New Game</button>`;
  }

  function newGame() {
    localStorage.removeItem("balkan-civ-save");
    $("victory-modal").style.display = "none";
    showStartScreen();
  }

  // ---------------- input ----------------
  function onMapClick(sx, sy, rightClick) {
    const [c, r] = rend.screenToHex(sx, sy);
    const t = game.tile(c, r);
    if (!t) return;
    const p = game.players[0];
    if (!p.visible[game.map.idx(c, r)]) { selectUnit(null); return; }

    const sel = rend.selected;
    // attack?
    if (sel && !rightClick && rend.attackable.some(([ac, ar]) => ac === c && ar === r)) {
      game.attack(sel, c, r);
      if (game.units.includes(sel)) selectUnit(sel); else selectUnit(null);
      refreshAll();
      return;
    }
    // move?
    if (sel && sel.owner === 0 && (rightClick || rend.reachable.some(([mc, mr]) => mc === c && mr === r) ||
        (!game.combatUnitAt(c, r) && !t.city && !game.unitsAt(c, r).length))) {
      const isOwnTile = sel.c === c && sel.r === r;
      if (!isOwnTile && game.unitPassable(sel, t)) {
        game.moveUnitTo(sel, c, r);
        selectUnit(game.units.includes(sel) ? sel : null);
        refreshAll();
        return;
      }
    }
    // select city / unit
    if (t.city && t.city.owner === 0) { selectCity(t.city); return; }
    if (t.city && t.city.owner !== 0) { showCityPanel(t.city); rend.selected = null; rend.dirty = true; return; }
    const mine = game.unitsAt(c, r).filter(u => u.owner === 0);
    if (mine.length) {
      // toggle through stacked units
      const cur = mine.indexOf(rend.selected);
      selectUnit(mine[(cur + 1) % mine.length]);
      return;
    }
    selectUnit(null);
  }

  function bindInput() {
    const cv = rend.canvas;
    let dragging = false, dragMoved = false, lastX = 0, lastY = 0;

    cv.addEventListener("mousedown", (e) => {
      dragging = true; dragMoved = false;
      lastX = e.clientX; lastY = e.clientY;
    });
    window.addEventListener("mousemove", (e) => {
      if (dragging) {
        const dx = e.clientX - lastX, dy = e.clientY - lastY;
        if (Math.abs(dx) + Math.abs(dy) > 3) dragMoved = true;
        if (dragMoved) {
          rend.cam.x -= dx; rend.cam.y -= dy;
          rend.dirty = true;
        }
        lastX = e.clientX; lastY = e.clientY;
      } else {
        updateTooltip(e);
      }
    });
    window.addEventListener("mouseup", (e) => {
      if (dragging && !dragMoved && e.target === cv) {
        onMapClick(e.clientX, e.clientY - cv.getBoundingClientRect().top, e.button === 2);
      }
      dragging = false;
    });
    cv.addEventListener("contextmenu", (e) => e.preventDefault());
    cv.addEventListener("wheel", (e) => {
      e.preventDefault();
      const oldSize = rend.size;
      rend.cam.zoom = Math.min(2.2, Math.max(0.45, rend.cam.zoom * (e.deltaY < 0 ? 1.12 : 0.89)));
      const scale = rend.size / oldSize;
      // zoom toward cursor
      const rect = cv.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      rend.cam.x = (rend.cam.x + mx) * scale - mx;
      rend.cam.y = (rend.cam.y + my) * scale - my;
      rend.dirty = true;
    }, { passive: false });

    // minimap click
    $("minimap").addEventListener("mousedown", (e) => {
      const rect = e.target.getBoundingClientRect();
      const c = Math.floor((e.clientX - rect.left) / rect.width * game.map.w);
      const r = Math.floor((e.clientY - rect.top) / rect.height * game.map.h);
      rend.centerOn(game, c, r);
    });

    window.addEventListener("keydown", (e) => {
      if ($("start-screen").style.display !== "none") return;
      if (e.key === "Enter") { endTurn(); }
      else if (e.key === "." || e.key === "n") cycleNextUnit();
      else if (e.key === "f" && rend.selected) { rend.selected.fortified = true; rend.selected.moves = 0; cycleNextUnit(); refreshAll(); }
      else if (e.key === "Escape") {
        $("tech-modal").style.display = "none";
        $("diplo-modal").style.display = "none";
        $("religion-modal").style.display = "none";
        $("founding-modal").style.display = "none";
        closeCity();
        selectUnit(null);
      } else if (e.key === "t") showTechScreen();
      else if (e.key === "d") showDiploScreen();
      else if (e.key === "r") showReligionScreen();
    });

    $("btn-endturn").onclick = endTurn;
    $("btn-tech").onclick = showTechScreen;
    $("btn-diplo").onclick = showDiploScreen;
    $("btn-religion").onclick = showReligionScreen;
    $("stat-faith").onclick = showReligionScreen;
    $("btn-menu").onclick = () => { if (confirm("Return to the main menu? (progress is auto-saved)")) showStartScreen(); };
    document.querySelectorAll(".modal").forEach(m => {
      m.addEventListener("mousedown", (e) => { if (e.target === m) m.style.display = "none"; });
    });
  }

  function updateTooltip(e) {
    const tip = $("tooltip");
    if (!game || $("start-screen").style.display !== "none") { tip.style.display = "none"; return; }
    const cv = rend.canvas;
    const rect = cv.getBoundingClientRect();
    if (e.clientX < rect.left || e.clientY < rect.top || e.clientY > rect.bottom) { tip.style.display = "none"; return; }
    const [c, r] = rend.screenToHex(e.clientX - rect.left, e.clientY - rect.top);
    const t = game.tile(c, r);
    if (!t || !game.players[0].visible[game.map.idx(c, r)]) { tip.style.display = "none"; return; }
    const y = game.tileYield(t);
    let html = `<b>${TERRAIN[t.terrain].name}</b>${t.feature ? " / " + FEATURE[t.feature].name : ""}`;
    if (t.resource) html += ` · ${RESOURCE[t.resource].icon} ${RESOURCE[t.resource].name}${RESOURCE[t.resource].luxury ? " (luxury)" : ""}`;
    if (t.improvement) html += ` · ${IMPROVEMENT[t.improvement].icon} ${IMPROVEMENT[t.improvement].name}`;
    html += `<br><span class="dim">🍞${y.food} ⚙️${y.prod} 💰${y.gold}</span>`;
    if (t.owner !== -1) html += `<br><span style="color:${CIVS[game.players[t.owner].civId].color}">${CIVS[game.players[t.owner].civId].name} territory</span>`;
    const visLevel = game.players[0].visible[game.map.idx(c, r)];
    if (visLevel === 2) {
      for (const u of game.unitsAt(c, r)) {
        html += `<br>${u.def.icon} ${u.def.name}${u.level ? " " + "⭐".repeat(u.level) : ""} (${CIVS[game.players[u.owner].civId].name}) HP ${u.hp}`;
      }
    }
    tip.innerHTML = html;
    tip.style.display = "block";
    tip.style.left = Math.min(window.innerWidth - 230, e.clientX + 14) + "px";
    tip.style.top = (e.clientY + 14) + "px";
  }

  // ---------------- boot ----------------
  function resize() {
    const cv = $("map");
    cv.width = window.innerWidth;
    cv.height = window.innerHeight - 44;
    if (rend) rend.dirty = true;
  }

  function init() {
    rend = new Renderer($("map"), $("minimap"));
    window.addEventListener("resize", resize);
    resize();
    bindInput();
    showStartScreen();
    (function loop() {
      if (game && rend.dirty && $("start-screen").style.display === "none") rend.draw(game);
      requestAnimationFrame(loop);
    })();
  }

  return { init, setProduction, buyItem, closeCity, pickTech, diploAction, newGame,
    showFoundingModal, confirmFounding, buyMissionary, gift,
    get game() { return game; }, get renderer() { return rend; } };
})();
