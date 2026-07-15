// ============================================================
// UI: DOM panels, input, screens
// ============================================================
"use strict";

const UI = (() => {
  let game = null, rend = null;
  let chosenCiv = CIV_IDS[0];
  let chosenLeader = 0;
  let pendingAttack = null, combatPanelTimer = null;
  const $ = (id) => document.getElementById(id);

  // In a network game only the client whose turn it is may act.
  function myTurn() {
    return !NET.active || game.activeHuman === NET.myIndex;
  }

  // ---------------- start screen ----------------
  function showStartScreen() {
    campaignChapter = null; // leaving to the menu ends any campaign context
    const wrap = $("civ-cards");
    wrap.innerHTML = "";

    for (const id of CIV_IDS) {
      const civ = CIVS[id];
      const uu = UNITS[civ.uu];
      const card = document.createElement("div");
      card.className = "civ-card";
      const renderLeaders = (sel) => civ.leaders.map((L, li) =>
        `<button class="leader-chip${id === chosenCiv && li === sel ? " sel" : ""}" data-li="${li}"
          title="${L.trait}: ${L.traitDesc}">${L.leader}</button>`).join("");
      const traitLine = (li) => `<div class="trait"><b>${civ.leaders[li].trait}</b><br>${civ.leaders[li].traitDesc}</div>`;
      const paint = () => {
        card.querySelector(".leaders").innerHTML = renderLeaders(id === chosenCiv ? chosenLeader : 0);
        card.querySelector(".trait-slot").innerHTML = traitLine(id === chosenCiv ? chosenLeader : 0);
        bindChips();
      };
      const bindChips = () => card.querySelectorAll(".leader-chip").forEach(b => b.onclick = (e) => {
        e.stopPropagation();
        chosenCiv = id; chosenLeader = parseInt(b.dataset.li, 10);
        document.querySelectorAll(".civ-card").forEach(c => c.classList.remove("sel"));
        card.classList.add("sel");
        repaintAll();
        refreshStartSummary();
      });
      card.innerHTML = `
        <div class="civ-flag" style="background:${civ.color};border-color:${civ.color2}"></div>
        <h3>${civ.name}</h3>
        <div class="leaders">${renderLeaders(id === chosenCiv ? chosenLeader : 0)}</div>
        <div class="trait-slot">${traitLine(id === chosenCiv ? chosenLeader : 0)}</div>
        <div class="uu">${uu.icon} <b>${uu.name}</b> — ${uu.blurb}</div>`;
      card.onclick = () => {
        if (chosenCiv !== id) { chosenCiv = id; chosenLeader = 0; }
        document.querySelectorAll(".civ-card").forEach(c => c.classList.remove("sel"));
        card.classList.add("sel");
        repaintAll();
        refreshStartSummary();
      };
      card._paint = paint;
      if (id === chosenCiv) card.classList.add("sel");
      bindChips();
      wrap.appendChild(card);
    }
    const repaintAll = () => wrap.querySelectorAll(".civ-card").forEach(c => c._paint && c._paint());
    refreshStartSummary();
    buildScenarioCards();
    $("opt-custom").disabled = !localStorage.getItem("balkan-civ-custommap");
    $("btn-host").onclick = showHostModal;
    $("btn-join").onclick = showJoinModal;
    $("btn-campaign").onclick = showCampaignScreen;
    $("btn-editor").onclick = () => { $("start-screen").style.display = "none"; EDITOR.open(); };
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
      const numHumans = parseInt($("sel-humans").value, 10);
      const mapType = $("sel-maptype").value;
      let customMap = null;
      if (mapType === "custom") {
        try { customMap = JSON.parse(localStorage.getItem("balkan-civ-custommap")); } catch (e) { /* fall through */ }
        if (!customMap) { alert("No custom map saved — open the Map Editor first."); return; }
      }
      game = new Game({ playerCiv: chosenCiv, playerLeader: chosenLeader,
        numOpponents: numOpp, mapW: dims[0], mapH: dims[1],
        mapType, customMap, numHumans, difficulty: $("sel-difficulty").value,
        noBarbs: !$("chk-barbs").checked, speed: $("sel-speed").value });
      startPlaying();
    };
    $("start-screen").style.display = "flex";
    $("game-ui").style.display = "none";
  }

  function refreshStartSummary() {
    const el = $("selected-civ-summary");
    if (!el) return;
    const civ = CIVS[chosenCiv];
    const leader = civ.leaders[chosenLeader] || civ.leaders[0];
    el.style.borderColor = civ.color2;
    el.innerHTML = `<div class="pick-name">${civ.name}</div>
      <div class="pick-leader">${leader.leader} · ${leader.trait}</div>
      <div class="pick-trait">${leader.traitDesc}</div>`;
  }

  function buildScenarioCards() {
    const wrap = $("scenario-cards");
    wrap.innerHTML = "";
    for (const [key, sc] of Object.entries(SCENARIOS)) {
      const card = document.createElement("div");
      card.className = "scenario-card";
      card.innerHTML = `<h3>${sc.icon} ${sc.name}</h3><div class="year">${sc.year} ·
        play as <b style="color:${CIVS[sc.playerCiv].color}">${CIVS[sc.playerCiv].name}</b> ·
        ${sc.victory.turns} turns</div><p>${sc.blurb}</p>`;
      card.onclick = () => launchScenario(key, null);
      wrap.appendChild(card);
    }
  }

  function launchScenario(key, chapter) {
    const sc = SCENARIOS[key];
    NET.reset();
    campaignChapter = chapter;
    game = new Game({ playerCiv: sc.playerCiv, fixedOpponents: sc.opponents,
      numOpponents: sc.opponents.length, seed: sc.seed, mapType: sc.mapType,
      difficulty: sc.difficulty, scenario: key });
    startPlaying();
  }

  // ---------------- campaign ----------------
  let campaignChapter = null; // scenario key when a game was launched from the campaign

  function campaignState() {
    try {
      const d = JSON.parse(localStorage.getItem("balkan-civ-campaign") || "{}");
      return { completed: Array.isArray(d.completed) ? d.completed : [], glory: d.glory || 0 };
    } catch (e) { return { completed: [], glory: 0 }; }
  }

  function saveCampaign(st) {
    try { localStorage.setItem("balkan-civ-campaign", JSON.stringify(st)); } catch (e) { /* full */ }
  }

  function chapterUnlocked(i, st) {
    return i === 0 || st.completed.includes(CAMPAIGN.chapters[i - 1]);
  }

  function showCampaignScreen() {
    const st = campaignState();
    $("campaign-modal").style.display = "flex";
    const done = st.completed.length, total = CAMPAIGN.chapters.length;
    let html = `<p class="dim">${CAMPAIGN.intro}</p>
      <div class="campaign-progress">🎖️ Glory: <b>${st.glory}</b> · Chapters: <b>${done}/${total}</b></div>
      <div class="prod-list">`;
    CAMPAIGN.chapters.forEach((key, i) => {
      const sc = SCENARIOS[key];
      const complete = st.completed.includes(key);
      const unlocked = chapterUnlocked(i, st);
      const status = complete ? `<span style="color:#2ecc71">✓ complete</span>`
        : unlocked ? `<span class="alert">available</span>` : `🔒 locked`;
      html += `<div class="campaign-chapter ${unlocked ? "" : "locked"}">
        <div><b>${i + 1}. ${sc.icon} ${sc.name}</b> <span class="dim">— ${sc.year}, ${CIVS[sc.playerCiv].name}</span><br>
          <span class="dim">${status} · ${sc.victory.turns} turns</span></div>
        <button ${unlocked ? "" : "disabled"} onclick="UI.playChapter('${key}')">${complete ? "Replay" : "Play"}</button>
      </div>`;
    });
    html += `</div>`;
    if (done === total) html += `<div class="campaign-outro">🏆 <b>Campaign complete!</b> ${CAMPAIGN.outro}</div>`;
    html += `<div style="margin-top:10px"><button onclick="document.getElementById('campaign-modal').style.display='none'">Close</button>
      ${done ? `<button onclick="UI.resetCampaign()">Reset progress</button>` : ""}</div>`;
    $("campaign-body").innerHTML = html;
  }

  function playChapter(key) {
    $("campaign-modal").style.display = "none";
    launchScenario(key, key);
  }

  // return to the campaign screen from the victory modal
  function openCampaign() {
    $("victory-modal").style.display = "none";
    NET.reset();
    showStartScreen();
    showCampaignScreen();
  }

  function resetCampaign() {
    if (!confirm("Reset all campaign progress and glory?")) return;
    saveCampaign({ completed: [], glory: 0 });
    showCampaignScreen();
  }

  // called from showVictory when a campaign chapter is finished
  function recordCampaignResult(won) {
    if (!campaignChapter) return null;
    const key = campaignChapter, sc = SCENARIOS[key];
    const st = campaignState();
    let gained = 0, firstTime = false;
    if (won) {
      firstTime = !st.completed.includes(key);
      gained = 100 + Math.max(0, sc.victory.turns - game.turn);
      st.glory += gained;
      if (firstTime) st.completed.push(key);
      saveCampaign(st);
    }
    const idx = CAMPAIGN.chapters.indexOf(key);
    const nextKey = idx >= 0 && idx + 1 < CAMPAIGN.chapters.length ? CAMPAIGN.chapters[idx + 1] : null;
    const campaignDone = st.completed.length === CAMPAIGN.chapters.length;
    return { won, gained, firstTime, nextKey, campaignDone, glory: st.glory };
  }

  // ---------------- online multiplayer ----------------
  function netUpdateBanner() {
    const b = $("net-banner");
    if (!NET.active || !game || game.over) { b.style.display = "none"; return; }
    b.style.display = "block";
    if (myTurn()) {
      b.innerHTML = `🌐 <b class="alert">Your turn</b> — you are ${CIVS[game.players[NET.myIndex].civId].name}`;
    } else {
      const p = game.players[game.activeHuman];
      b.innerHTML = `🌐 Waiting for <b style="color:${p.civ.color}">${p.civ.name}</b> (Player ${game.activeHuman + 1})…`;
    }
  }

  function netAfterLoad() {
    selectUnit(null);
    closeCity();
    notifSeen = Math.max(0, game.notifications.length - 3);
    refreshAll();
    netUpdateBanner();
    if (myTurn() && !game.over) {
      SFX.play("turn");
      cycleNextUnit();
      maybePromptFounding();
    }
  }

  async function showHostModal() {
    NET.reset();
    $("net-modal").style.display = "flex";
    const body = $("net-body");
    body.innerHTML = `<h2>🌐 Host Online Game</h2>
      <p class="dim">You are <b>${CIVS[chosenCiv].name}</b> (pick a different civ card first if you like).
      For each friend: create an invite, send them the code (any chat app), paste back their reply.
      Friends pick their civ on their own start screen before joining.</p>
      <div id="net-slots"></div>
      <button onclick="UI.hostAddSlot()">➕ Invite a friend</button>
      <button id="net-start-btn" disabled onclick="UI.hostStartOnline()">🚀 Start Online Game</button>
      <span class="dim" id="net-status"></span>`;
    hostAddSlot();
  }

  async function hostAddSlot() {
    if (NET.peers.length >= 3) return;
    const entry = await NET.hostInvite();
    const i = NET.peers.length - 1;
    const div = document.createElement("div");
    div.className = "net-slot";
    div.innerHTML = `<b>Friend ${i + 1}</b> — <span id="net-st-${i}">waiting for reply…</span><br>
      <span class="dim">Send this invite code:</span>
      <textarea class="net-code" readonly onclick="this.select()">${entry.inviteCode}</textarea>
      <span class="dim">Paste their reply code:</span>
      <textarea class="net-code" id="net-reply-${i}"></textarea>
      <button onclick="UI.hostConnect(${i})">🔗 Connect</button>`;
    $("net-slots").appendChild(div);
  }

  async function hostConnect(i) {
    try {
      await NET.hostAcceptReply(NET.peers[i], $(`net-reply-${i}`).value);
      $(`net-st-${i}`).textContent = "connecting…";
    } catch (e) {
      $(`net-st-${i}`).textContent = "bad code — paste the full reply";
    }
  }

  function refreshHostStatus() {
    NET.peers.forEach((p, i) => {
      const el = $(`net-st-${i}`);
      if (el && p.open) el.innerHTML = `<b style="color:#2ecc71">connected</b>` +
        (p.civ ? ` — wants ${CIVS[p.civ] ? CIVS[p.civ].name : "random"}` : "");
    });
    const btn = $("net-start-btn");
    if (btn) btn.disabled = !NET.peers.some(p => p.open);
  }

  function hostStartOnline() {
    const ready = NET.peers.filter(p => p.open);
    if (!ready.length) return;
    const taken = new Set([chosenCiv]);
    for (const p of ready) {
      let c = (p.civ && CIVS[p.civ] && !taken.has(p.civ)) ? p.civ
        : CIV_IDS.find(x => !taken.has(x));
      taken.add(c);
      p.assignedCiv = c;
    }
    const aiCount = parseInt($("sel-opponents").value, 10);
    const rest = CIV_IDS.filter(c => !taken.has(c)).sort(() => Math.random() - 0.5);
    const dims = { small: [36, 28], standard: [44, 34], large: [54, 42] }[$("sel-mapsize").value];
    const mapType = $("sel-maptype").value === "custom" ? "peninsula" : $("sel-maptype").value;
    game = new Game({ playerCiv: chosenCiv,
      fixedOpponents: [...ready.map(p => p.assignedCiv), ...rest.slice(0, aiCount)],
      numOpponents: ready.length + Math.min(aiCount, rest.length),
      numHumans: 1 + ready.length,
      mapW: dims[0], mapH: dims[1], mapType, difficulty: $("sel-difficulty").value,
      noBarbs: !$("chk-barbs").checked, speed: $("sel-speed").value });
    game._viewer = 0;
    NET.hostStart(game);
    $("net-modal").style.display = "none";
    startPlaying();
    netUpdateBanner();
  }

  function showJoinModal() {
    NET.reset();
    $("net-modal").style.display = "flex";
    $("net-body").innerHTML = `<h2>🌐 Join Online Game</h2>
      <p class="dim">You will play as <b>${CIVS[chosenCiv].name}</b> (close this and pick another civ card to change).
      Paste the host's invite code:</p>
      <textarea class="net-code" id="net-invite"></textarea>
      <button onclick="UI.joinCreateReply()">🔗 Create Reply</button>
      <div id="net-join-out"></div>`;
  }

  async function joinCreateReply() {
    try {
      const reply = await NET.joinWithInvite($("net-invite").value, chosenCiv);
      $("net-join-out").innerHTML = `<span class="dim">Send this reply code back to the host,
        then wait — the game starts automatically:</span>
        <textarea class="net-code" readonly onclick="this.select()">${reply}</textarea>
        <span class="alert">⏳ Waiting for the host to start…</span>`;
    } catch (e) {
      $("net-join-out").innerHTML = `<span class="war">Bad invite code — paste the whole thing.</span>`;
    }
  }

  function startPlaying() {
    $("start-screen").style.display = "none";
    $("game-ui").style.display = "block";
    notifSeen = game.notifications.length; // don't replay loaded history
    $("btn-mute").textContent = SFX.muted ? "🔇" : "🔊";
    $("btn-music").textContent = SFX.musicOn ? "🎵" : "♪";
    SFX.startMusic();
    resize();
    applyAccessibility();
    const rotateDisplay = rend.three ? "block" : "none";
    $("btn-rot-left").style.display = rotateDisplay;
    $("btn-rot-right").style.display = rotateDisplay;
    $("map-controls").querySelector(".control-rule").style.display = rotateDisplay;
    lastEraShown = null; // re-baseline era banners for this game
    const firstUnit = game.units.find(u => u.owner === game.viewer);
    if (firstUnit) rend.centerOn(game, firstUnit.c, firstUnit.r);
    selectUnit(firstUnit || null);
    refreshAll();
  }

  // ---------------- selection ----------------
  function selectUnit(u) {
    hideCombatPreview();
    if (u && u !== rend.selected) SFX.play("select");
    rend.previewPath = null;
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
    const p = game.players[game.viewer];
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

  // Is the clicked tile a legal *war* target — an at-peace rival's unit or city
  // in this unit's strike range? Returns the owner index, or -1 if none.
  // Lets a player start a war the intuitive way: by attacking.
  function warTargetOwner(u, c, r) {
    if (!u || u.owner !== game.viewer || u.isCivilian || u.attacked || u.moves <= 0 || game.isEmbarked(u)) return -1;
    const p = game.players[game.viewer];
    const range = u.isRanged ? u.def.range : 1;
    if (HEX.distance(u.c, u.r, c, r) > range) return -1;
    const t = game.tile(c, r);
    if (!t || !p.visible[game.map.idx(c, r)]) return -1;
    if (!u.isRanged && !u.def.naval && game.isWater(t)) return -1;
    if (!u.isRanged && u.def.naval && !game.isWater(t) && !t.city) return -1;
    const cu = game.combatUnitAt(c, r);
    const civ = game.civilianAt(c, r);
    const owner = cu ? cu.owner : (t.city ? t.city.owner : (civ ? civ.owner : -1));
    if (owner < 0 || owner === game.viewer) return -1;
    const op = game.players[owner];
    // barbarians are already at war; skip our own pact partners and unmet powers
    if (!op || op.isBarb || p.atWarWith.has(owner) || p.pacts.has(owner) || !p.met.has(owner)) return -1;
    return owner;
  }

  function showWarConfirm(unit, c, r) {
    const owner = warTargetOwner(unit, c, r);
    if (owner < 0) return false;
    const civ = game.players[owner].civ;
    const pactAllies = [...game.players[game.viewer].pacts].filter(a =>
      game.players[a] && game.players[a].alive && game.players[a].pacts.has(owner));
    $("war-body").innerHTML = `
      <div class="diplo-row" style="border-left:6px solid ${civ.color}">
        <div>Attack <b>${civ.name}</b> <span class="dim">— ${civ.leader}</span>?</div>
        <div class="dim">This declares <b>war</b>. Military ${Math.floor(game.militaryPower(owner))} ·
          they feel <b>${game.attitudeLabel(owner, game.viewer)}</b> toward you.</div>
        ${game.players[owner].pacts.size ? `<div class="dim">⚠️ Their defensive-pact allies may join against you.</div>` : ""}
      </div>
      <div style="display:flex;gap:10px;margin-top:6px">
        <button onclick="UI.declareWarAndAttack(${c}, ${r})">⚔️ Declare War & Attack</button>
        <button onclick="document.getElementById('war-modal').style.display='none'">Cancel</button>
      </div>`;
    $("war-modal").style.display = "flex";
    return true;
  }

  function declareWarAndAttack(c, r) {
    $("war-modal").style.display = "none";
    if (!myTurn()) return;
    const sel = rend.selected;
    const owner = warTargetOwner(sel, c, r);
    if (owner < 0) return;
    game.declareWar(game.viewer, owner);
    executePlayerAttack(sel, c, r);
  }

  function hideCombatPreview() {
    const panel = $("combat-preview");
    if (panel) {
      panel.style.display = "none";
      panel.classList.remove("resolved");
      panel.innerHTML = "";
    }
    pendingAttack = null;
    clearTimeout(combatPanelTimer);
  }

  function hpMeter(current, max, color) {
    const pct = Math.max(0, Math.min(100, current / Math.max(1, max) * 100));
    return `<span class="combat-hp"><span style="width:${pct}%;background:${color}"></span></span>`;
  }

  function combatVerdict(unit, forecast) {
    if (forecast.out[0] >= forecast.targetHp) return ["Decisive strike", "good"];
    if (!forecast.back) return ["No counterattack", "good"];
    const dealt = (forecast.out[0] + forecast.out[1]) / 2;
    const taken = (forecast.back[0] + forecast.back[1]) / 2;
    if (taken >= unit.hp) return ["Attacker at risk", "bad"];
    if (dealt >= taken * 1.45) return ["Favourable", "good"];
    if (taken >= dealt * 1.45) return ["Unfavourable", "bad"];
    return ["Even engagement", "even"];
  }

  function showCombatPreview(unit, c, r) {
    const forecast = game.predictAttack(unit, c, r);
    if (!forecast) return false;
    const tile = game.tile(c, r);
    const targetUnit = game.combatUnitAt(c, r);
    const hitsCity = !!(tile.city && (!targetUnit || !unit.isRanged));
    const defender = hitsCity ? tile.city : targetUnit;
    if (!defender) return false;
    const targetPlayer = game.players[defender.owner];
    const [verdict, verdictClass] = combatVerdict(unit, forecast);
    const panel = $("combat-preview");
    pendingAttack = { unitId: unit.id, c, r };
    clearTimeout(combatPanelTimer);
    panel.className = "";
    panel.innerHTML = `
      <div class="combat-title"><span>Combat forecast</span><button class="combat-close" title="Cancel attack">✕</button></div>
      <div class="combat-versus">
        <div class="combatant">
          <span class="combat-icon">${unit.def.icon}</span>
          <span><b>${unit.def.name}</b><small>${game.players[unit.owner].civ.name} · ${unit.hp} HP</small>${hpMeter(unit.hp, 100, game.players[unit.owner].civ.color)}</span>
        </div>
        <span class="combat-vs">VS</span>
        <div class="combatant target">
          <span class="combat-icon">${hitsCity ? "🏙️" : defender.def.icon}</span>
          <span><b>${forecast.target}</b><small>${targetPlayer.civ.name} · ${forecast.targetHp} HP</small>${hpMeter(forecast.targetHp, hitsCity ? defender.maxHp : 100, targetPlayer.civ.color)}</span>
        </div>
      </div>
      <div class="combat-odds">
        <span>Deal <b>${forecast.out[0]}–${forecast.out[1]}</b></span>
        <span>${forecast.back ? `Take <b>${forecast.back[0]}–${forecast.back[1]}</b>` : "No retaliation"}</span>
        <strong class="${verdictClass}">${verdict}</strong>
      </div>
      <div class="combat-actions"><button class="combat-confirm">⚔ Attack</button><button class="combat-cancel">Cancel</button></div>`;
    panel.style.display = "block";
    panel.querySelector(".combat-close").onclick = hideCombatPreview;
    panel.querySelector(".combat-cancel").onclick = hideCombatPreview;
    panel.querySelector(".combat-confirm").onclick = () => {
      const current = game.units.find(u => u.id === pendingAttack?.unitId);
      if (current) executePlayerAttack(current, c, r);
    };
    return true;
  }

  function showCombatResult(report) {
    if (!report) return;
    const panel = $("combat-preview");
    const attacker = game.players[report.attackerOwner];
    const defender = game.players[report.targetOwner];
    const outcome = report.cityCaptured ? `${report.targetName} captured`
      : report.targetDestroyed ? `${report.targetName} destroyed`
      : report.attackerDestroyed ? `${report.attackerName} lost` : "Engagement complete";
    panel.className = "resolved";
    panel.innerHTML = `
      <div class="combat-title"><span>Battle report</span><button class="combat-close" title="Dismiss">✕</button></div>
      <div class="combat-result-title">${outcome}</div>
      <div class="combat-result-line">
        <span style="color:${attacker.civ.color}">${report.attackerName}</span>
        <b>dealt ${report.damage}</b>
        ${report.counterDamage ? `<span>· took ${report.counterDamage}</span>` : `<span>· no retaliation</span>`}
      </div>
      <div class="combat-survivors">
        <span>${report.attackerDestroyed ? "Defeated" : `${report.attackerHpAfter} HP`} · ${report.attackerName}</span>
        <span>${report.targetDestroyed ? "Defeated" : `${report.targetHpAfter} HP`} · <span style="color:${defender.civ.color}">${report.targetName}</span></span>
      </div>`;
    panel.style.display = "block";
    panel.querySelector(".combat-close").onclick = hideCombatPreview;
    clearTimeout(combatPanelTimer);
    combatPanelTimer = setTimeout(hideCombatPreview, rend.reduceMotion ? 6500 : 4500);
  }

  function executePlayerAttack(unit, c, r) {
    hideCombatPreview();
    const tile = game.tile(c, r);
    SFX.play(tile && tile.city ? "cityhit" : "attack");
    const ok = game.attack(unit, c, r);
    const report = ok ? game.lastCombat : null;
    selectUnit(game.units.includes(unit) ? unit : null);
    refreshAll();
    if (report) showCombatResult(report);
    return ok;
  }

  function selectCity(city) {
    hideCombatPreview();
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
      <div><b>${u.gpName ? u.gpName + " — " : ""}${def.name}</b>${u.level ? " " + "⭐".repeat(u.level) : ""}${u.promos.map(k => PROMOS[k].icon).join("")}${game.isEmbarked(u) ? " <span class='alert'>⛵ embarked</span>" : ""}<br>
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
    if (u.promoPts > 0 && u.owner === game.viewer && !u.isCivilian) {
      for (const key of Object.keys(PROMOS)) {
        if (u.promos.includes(key)) continue;
        const pr = PROMOS[key];
        btn(`⭐ ${pr.icon} ${pr.name}`, () => {
          u.promos.push(key);
          u.promoPts--;
          SFX.play("build");
          refreshAll();
        }, myTurn());
      }
    }
    if (u.type === "SETTLER") {
      const t = game.tile(u.c, u.r);
      const canFound = t && TERRAIN[t.terrain].passable && !t.city &&
        ![...HEX.ring(u.c, u.r, 2)].some(([c, r]) => {
          const n = game.tile(c, r); return n && n.city;
        });
      btn("🏛️ Found City", () => {
        const city = game.foundCity(u);
        if (city) { SFX.play("found"); selectCity(city); refreshAll(); }
      }, canFound && u.moves > 0);
    }
    if (u.def.caravan) {
      const dests = game.tradeDestinations(u);
      const from = game.cityAt(u.c, u.r);
      if (from && from.owner === game.viewer) {
        for (const d of dests.slice(0, 4)) {
          btn(`🐫 → ${d.name} (+${game.routeIncome(from, d)}💰/t)`, () => {
            if (game.establishRoute(u, d.id)) { SFX.play("coin"); selectUnit(null); refreshAll(); }
          }, myTurn());
        }
        if (!dests.length) {
          const cap = game.routes.filter(r => r.owner === game.viewer).length >= TRADE.maxRoutes;
          btn(cap ? `🐫 All ${TRADE.maxRoutes} routes busy` : "🐫 No destinations in range", () => {}, false);
        }
      } else {
        btn("🐫 Move to one of your cities to trade", () => {}, false);
      }
    }
    if (u.def.great) {
      if (u.def.great === "sci") {
        btn("🔭 Discover Technology", () => {
          if (game.useGreatPerson(u)) { SFX.play("research"); selectUnit(null); refreshAll(); }
        }, myTurn());
      } else if (u.def.great === "eng") {
        const inCity = game.cityAt(u.c, u.r) && game.cityAt(u.c, u.r).owner === game.viewer;
        btn(`🏗️ Rush Production (+${GP.engineerRush}⚙️)`, () => {
          if (game.useGreatPerson(u)) { SFX.play("build"); selectUnit(null); refreshAll(); }
        }, inCity && myTurn());
      } else {
        btn("🎖️ +15% combat within 2 tiles", () => {}, false);
      }
    }
    if (u.def.missionary) {
      const target = game.missionaryTarget(u);
      btn(`🕊️ Spread Religion (${u.charges} left)`, () => {
        if (game.spreadFromMissionary(u)) {
          selectUnit(game.units.includes(u) ? u : null);
          refreshAll();
        }
      }, !!target && u.moves > 0 && game.players[game.viewer].religionId !== null);
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
    if (u.type === "SCOUT") {
      btn(u.autoExplore ? "🛑 Stop Exploring" : "🗺️ Auto-Explore", () => {
        u.autoExplore = !u.autoExplore;
        if (u.autoExplore) { AI.autoExplore(game, u); cycleNextUnit(); }
        refreshAll();
      });
    }
    if (!u.isCivilian) {
      const up = game.canUpgrade(u);
      if (u.def.upgrade) {
        const target = game.resolveUnitFor(game.players[game.viewer], u.def.upgrade);
        btn(`⬆️ ${UNITS[target].name} (${up ? up.cost : "—"}💰)`, () => {
          if (game.upgradeUnit(u)) { SFX.play("coin"); selectUnit(u); refreshAll(); }
        }, !!up && myTurn());
      }
      btn(u.fortified ? "⛺ Wake" : "🛡️ Fortify", () => {
        u.fortified = !u.fortified;
        u.healFortify = false;
        if (u.fortified) u.moves = 0;
        selectUnit(u); refreshAll();
      });
      if (u.hp < 100 && !u.healFortify) {
        btn("➕ Heal Up", () => {
          u.fortified = true;
          u.healFortify = true;
          u.moves = 0;
          cycleNextUnit(); refreshAll();
        });
      }
    }
    if (undoInfo && undoInfo.id === u.id && undoInfo.turn === game.turn) {
      btn("↩️ Undo Move", () => undoMove(), myTurn());
    }
    btn("⏭️ Skip", () => { u.moves = 0; cycleNextUnit(); refreshAll(); });
    btn("❌ Disband", () => { game.removeUnit(u); selectUnit(null); refreshAll(); });
  }

  // ---------------- undo (simple moves only) ----------------
  let undoInfo = null;

  function snapshotUndo(u) {
    undoInfo = {
      id: u.id, c: u.c, r: u.r, moves: u.moves, turn: game.turn,
      visible: Uint8Array.from(game.players[game.viewer].visible),
      marker: game.notifications.length + "|" + JSON.stringify(game.stats || {}) + "|" +
        Math.floor(game.players[game.viewer].gold),
    };
  }

  // moves that triggered events (ruins, camps, captures...) can't be undone
  function validateUndo(u) {
    if (!undoInfo) return;
    const marker = game.notifications.length + "|" + JSON.stringify(game.stats || {}) + "|" +
      Math.floor(game.players[game.viewer].gold);
    if (marker !== undoInfo.marker || u.id !== undoInfo.id) undoInfo = null;
  }

  function undoMove() {
    const u = rend.selected;
    if (!undoInfo || !u || u.id !== undoInfo.id || undoInfo.turn !== game.turn) return;
    u.c = undoInfo.c; u.r = undoInfo.r; u.moves = undoInfo.moves; u.path = null;
    game.players[game.viewer].visible = undoInfo.visible;
    undoInfo = null;
    game.anims = game.anims.filter(a => a.id !== u.id);
    selectUnit(u);
    refreshAll();
  }

  function cycleNextUnit() {
    const candidates = game.units.filter(u => u.owner === game.viewer && u.moves > 0 && !u.fortified &&
      !u.building && !u.autoExplore && !(u.path && u.path.length));
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
    const isMine = city.owner === game.viewer;
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
      const p0 = game.players[game.viewer];
      if (p0.religionId !== null) {
        const cost = game.missionaryCost(game.viewer);
        html += `<div class="prod-current"><button ${p0.faith >= cost ? "" : "disabled"}
          onclick="UI.buyMissionary(${city.id})">🙏 Missionary (${cost} ☦️)</button></div>`;
      }
      const opts = game.productionOptions(city);
      const cur = city.producing;
      html += `<div class="prod-current">Producing: <b>${cur
        ? (cur.kind === "unit" ? UNITS[cur.key].icon + " " + UNITS[cur.key].name : BUILDINGS[cur.key].icon + " " + BUILDINGS[cur.key].name) +
          ` (${city.prodStored}/${cur.kind === "unit" ? UNITS[cur.key].cost : BUILDINGS[cur.key].cost})`
        : "—"}</b>${cur ? ` <a href="#" class="prod-cancel" title="Stop producing this" onclick="UI.cancelProduction(${city.id});return false">✕ cancel</a>` : ""}</div>`;
      if (city.queue.length) {
        html += `<div class="prod-current">Queue: ${city.queue.map((q, i) =>
          `${q.kind === "unit" ? UNITS[q.key].icon : BUILDINGS[q.key].icon}
           <a href="#" onclick="UI.unqueue(${city.id},${i});return false" title="remove">✕</a>`).join(" → ")}</div>`;
      }
      html += `<div class="prod-list">`;
      for (const o of opts) {
        const turns = Math.max(1, Math.ceil((o.cost - (cur && cur.key === o.key ? city.prodStored : 0)) / Math.max(1, y.prod)));
        const price = game.buyCost(o.cost, game.viewer);
        const afford = game.players[game.viewer].gold >= price;
        html += `<div class="prod-item ${o.wonder ? "wonder" : ""}">
          <span>${o.icon} ${o.name}</span>
          <span class="dim">${o.cost}⚙️ ~${turns}t</span>
          <button title="Build this now${cur ? " (replaces current production)" : ""}" onclick="UI.buildNow(${city.id},'${o.kind}','${o.key}')">🔨 Build</button>
          ${cur ? `<button title="Add to the build queue" onclick="UI.setProduction(${city.id},'${o.kind}','${o.key}')">＋ Queue</button>` : ""}
          <button ${afford ? "" : "disabled"} onclick="UI.buyItem(${city.id},'${o.kind}','${o.key}')">💰${price}</button>
        </div>`;
      }
      html += `</div>`;
    }
    panel.innerHTML = html;
  }

  function setProduction(cityId, kind, key) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    if (city.producing && city.producing.key !== key) {
      if (city.queue.length < 6 && !city.queue.some(q => q.key === key)) {
        city.queue.push({ kind, key });
      }
    } else {
      city.producing = { kind, key };
    }
    SFX.play("click");
    showCityPanel(city);
    refreshAll();
  }

  // Switch what the city is building right now (stored production carries over).
  function buildNow(cityId, kind, key) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    if (city.producing && city.producing.key === key) return;
    // dropping a half-built wonder shouldn't silently waste all its hammers, but
    // switching between ordinary items keeps progress (Civ-style)
    city.producing = { kind, key };
    SFX.play("click");
    showCityPanel(city);
    refreshAll();
  }

  // Stop current production; if a queue exists, promote its next item.
  function cancelProduction(cityId) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    city.producing = city.queue.length ? city.queue.shift() : null;
    if (!city.producing) city.prodStored = 0;
    SFX.play("click");
    showCityPanel(city);
    refreshAll();
  }

  function unqueue(cityId, i) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    city.queue.splice(i, 1);
    showCityPanel(city);
  }

  function buyItem(cityId, kind, key) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    const cost = kind === "unit" ? UNITS[key].cost : BUILDINGS[key].cost;
    if (game.purchase(city, { kind, key, cost })) {
      SFX.play("coin");
      showCityPanel(city);
      refreshAll();
    }
  }

  function closeCity() {
    rend.selectedCity = null;
    $("city-panel").style.display = "none";
    rend.dirty = true;
  }

  // ---------------- tech dependency tree ----------------
  let techFocusKey = null;

  function techDepths() {
    const memo = {};
    const depthOf = (key) => {
      if (memo[key] !== undefined) return memo[key];
      const req = TECHS[key].req;
      memo[key] = req.length ? 1 + Math.max(...req.map(depthOf)) : 0;
      return memo[key];
    };
    for (const key of Object.keys(TECHS)) depthOf(key);
    return memo;
  }

  function techAncestors(key, out = new Set()) {
    if (!key || !TECHS[key]) return out;
    out.add(key);
    for (const req of TECHS[key].req) techAncestors(req, out);
    return out;
  }

  function highlightTechPath(key) {
    const tree = $("tech-tree");
    if (!tree) return;
    const path = techAncestors(key);
    tree.querySelectorAll(".tech").forEach(n => {
      n.classList.toggle("path", path.has(n.dataset.tech));
      n.classList.toggle("strategy", n.dataset.tech === key);
      n.setAttribute("aria-pressed", n.dataset.tech === techFocusKey ? "true" : "false");
    });
    tree.querySelectorAll(".tech-link").forEach(edge => {
      edge.classList.toggle("path", path.has(edge.dataset.from) && path.has(edge.dataset.to));
    });
  }

  function drawTechConnections() {
    const tree = $("tech-tree");
    const svg = $("tech-links");
    if (!tree || !svg) return;
    const root = tree.getBoundingClientRect();
    const width = tree.scrollWidth, height = tree.scrollHeight;
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", width);
    svg.setAttribute("height", height);
    let paths = "";
    for (const [to, tech] of Object.entries(TECHS)) {
      const target = tree.querySelector(`[data-tech="${to}"]`);
      if (!target) continue;
      const tr = target.getBoundingClientRect();
      for (const from of tech.req) {
        const source = tree.querySelector(`[data-tech="${from}"]`);
        if (!source) continue;
        const sr = source.getBoundingClientRect();
        const x1 = sr.right - root.left + tree.scrollLeft;
        const y1 = sr.top + sr.height / 2 - root.top + tree.scrollTop;
        const x2 = tr.left - root.left + tree.scrollLeft;
        const y2 = tr.top + tr.height / 2 - root.top + tree.scrollTop;
        const bend = Math.max(24, (x2 - x1) * 0.46);
        paths += `<path class="tech-link" data-from="${from}" data-to="${to}"
          d="M ${x1} ${y1} C ${x1 + bend} ${y1}, ${x2 - bend} ${y2}, ${x2} ${y2}"/>`;
      }
    }
    svg.innerHTML = paths;
    highlightTechPath(techFocusKey || game.players[game.viewer].researching);
  }

  function showTechScreen() {
    const p = game.players[game.viewer];
    const modal = $("tech-modal");
    modal.style.display = "flex";
    const body = $("tech-body");
    const depth = techDepths();
    const maxDepth = Math.max(...Object.values(depth));
    const layers = Array.from({ length: maxDepth + 1 }, () => []);
    for (const key of Object.keys(TECHS)) layers[depth[key]].push(key);
    const rows = Math.max(...layers.map(x => x.length));
    const eraRanges = ERAS.map((_, era) => {
      const ds = Object.keys(TECHS).filter(k => TECHS[k].era === era).map(k => depth[k]);
      return [Math.min(...ds), Math.max(...ds)];
    });
    let html = `<div class="tech-help">Select a gold technology to research. Select or hover any other technology to trace its prerequisite path.</div>
      <div id="tech-tree" class="tech-tree" style="--tech-cols:${maxDepth + 1};--tech-rows:${rows}">
        <svg id="tech-links" class="tech-links" aria-hidden="true"></svg>
        <div class="tech-era-ruler">`;
    ERAS.forEach((era, i) => {
      html += `<div class="tech-era" style="grid-column:${eraRanges[i][0] + 1}/${eraRanges[i][1] + 2}">${era}</div>`;
    });
    html += `</div><div class="tech-node-grid">`;
    layers.forEach((layer, d) => layer.forEach((key, i) => {
      const t = TECHS[key];
      const has = p.techs.has(key);
      const avail = !has && t.req.every(r => p.techs.has(r));
      const researching = p.researching === key;
      const unlocks = [];
      for (const u of Object.values(UNITS)) if (u.tech === key && (!u.uu || u.uu === p.civId)) unlocks.push(u.icon + " " + u.name);
      for (const b of Object.values(BUILDINGS)) if (b.tech === key) unlocks.push(b.icon + " " + b.name);
      const row = layer.length === 1 ? 1 + Math.floor((rows - 1) / 2)
        : 1 + Math.round(i * (rows - 1) / (layer.length - 1));
      html += `<div class="tech ${has ? "done" : avail ? "avail" : "locked"} ${researching ? "active" : ""}"
        data-tech="${key}" data-avail="${avail ? "1" : "0"}" role="button" tabindex="0"
        style="grid-column:${d + 1};grid-row:${row}" aria-label="${t.name}, ${game.techCost(key)} science">
        <div class="tech-name"><b>${t.name}</b><span>${game.techCost(key)}🔬</span></div>
        ${researching ? `<div class="tech-progress"><i style="width:${Math.min(100, p.scienceStored / game.techCost(key) * 100)}%"></i></div>` : ""}
        ${unlocks.length ? `<div class="unlocks">${unlocks.join(" · ")}</div>` : `<div class="unlocks dim">No direct unlock</div>`}
        ${t.req.length ? `<div class="req">← ${t.req.map(r => TECHS[r].name).join(" + ")}</div>` : `<div class="req">Starting knowledge</div>`}
      </div>`;
    }));
    html += `</div></div>`;
    body.innerHTML = html;
    const tree = $("tech-tree");
    tree.querySelectorAll(".tech").forEach(node => {
      const key = node.dataset.tech;
      node.onclick = () => {
        if (node.dataset.avail === "1") pickTech(key);
        else { techFocusKey = key; highlightTechPath(key); }
      };
      node.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); node.click(); }
      };
      node.onmouseenter = () => highlightTechPath(key);
      node.onmouseleave = () => highlightTechPath(techFocusKey || p.researching);
      node.onfocus = () => highlightTechPath(key);
      node.onblur = () => highlightTechPath(techFocusKey || p.researching);
    });
    requestAnimationFrame(drawTechConnections);
  }

  function pickTech(key) {
    if (!myTurn()) return;
    SFX.play("click");
    game.players[game.viewer].researching = key;
    $("tech-modal").style.display = "none";
    refreshAll();
  }

  // ---------------- religion ----------------
  let foundingPromptTurn = -1;

  function showReligionScreen() {
    const p = game.players[game.viewer];
    $("religion-modal").style.display = "flex";
    const body = $("religion-body");
    let html = `<div class="diplo-row">Your faith: <b>☦️ ${Math.floor(p.faith)}</b>`;
    if (p.religionId === null) {
      if (game.religions.length >= MAX_RELIGIONS) {
        html += ` <span class="dim">— all ${MAX_RELIGIONS} religions have been founded.</span>`;
      } else {
        html += ` <span class="dim">— found a religion at ${RELIGION_FOUND_COST(game.religions.length)} faith.</span>`;
        if (game.canFoundReligion(game.viewer)) html += ` <button onclick="UI.showFoundingModal()">🕊️ Found Religion</button>`;
      }
    } else {
      const r = game.religions[p.religionId];
      html += ` <span class="dim">— buy a Missionary for ${game.missionaryCost(game.viewer)} faith from any city panel.</span>`;
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
    const p = game.players[game.viewer];
    if (!game.canFoundReligion(game.viewer)) return;
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
    if (!myTurn()) return;
    const name = $("sel-religion-name").value;
    const entry = RELIGION_NAMES.find(r => r.name === name);
    const belief = document.querySelector("input[name=belief]:checked").value;
    if (game.foundReligion(game.viewer, entry.name, entry.icon, belief)) {
      $("founding-modal").style.display = "none";
      refreshAll();
    }
  }

  function buyMissionary(cityId) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (city && game.buyMissionary(city)) { SFX.play("coin"); showCityPanel(city); refreshAll(); }
  }

  // ---------------- espionage ----------------
  function showSpyScreen() {
    const p = game.players[game.viewer];
    $("spy-modal").style.display = "flex";
    const body = $("spy-body");
    if (!p.spies.length) {
      const next = SPY_TECHS.find(t => !p.techs.has(t));
      body.innerHTML = `<div class="diplo-row dim">You have no spies yet. Agents are recruited with
        ${SPY_TECHS.map(t => TECHS[t].name).join(", ")}${next ? ` — research <b>${TECHS[next].name}</b> next` : ""}.</div>`;
      return;
    }
    let html = `<div class="diplo-row dim">Assign spies to your cities (counter-intelligence), rival cities
      (steal technology, ~${Math.ceil(SPY.stealThreshold / SPY.stealRate)} turns per attempt), or city-states
      (+${SPY.rigPerTurn} influence per turn).</div>`;
    for (const spy of p.spies) {
      html += `<div class="diplo-row"><b>🕵️ ${spy.name}</b> — `;
      if (spy.deadUntil > game.turn) {
        html += `<span class="war">training replacement (${spy.deadUntil - game.turn} turns)</span></div>`;
        continue;
      }
      const city = spy.cityId !== null ? game.cities.find(c => c.id === spy.cityId) : null;
      if (!city) {
        html += `<span class="alert">idle</span>`;
      } else if (city.owner === game.viewer) {
        html += `guarding <b>${city.name}</b>`;
      } else if (game.players[city.owner].isMinor) {
        html += `rigging elections in <b>${city.name}</b>`;
      } else {
        html += `stealing in <b>${city.name}</b> (${CIVS[game.players[city.owner].civId].name}) — ${spy.progress}%`;
      }
      // assignment dropdown
      let opts = `<option value="">— reassign —</option>`;
      const mine = game.cities.filter(c => c.owner === game.viewer);
      if (mine.length) opts += `<optgroup label="Defend">` +
        mine.map(c => `<option value="${c.id}">${c.name}</option>`).join("") + `</optgroup>`;
      for (const o of game.players) {
        if (o.index === game.viewer || !o.alive || !p.met.has(o.index)) continue;
        const theirs = game.cities.filter(c => c.owner === o.index);
        if (!theirs.length) continue;
        const label = o.isMinor ? `Rig — ${o.civ.name}` : `Steal — ${o.civ.name}`;
        opts += `<optgroup label="${label}">` +
          theirs.map(c => `<option value="${c.id}">${c.name}</option>`).join("") + `</optgroup>`;
      }
      html += ` <select onchange="UI.assignSpy(${spy.id}, this.value)">${opts}</select></div>`;
    }
    body.innerHTML = html;
  }

  function assignSpy(spyId, cityIdStr) {
    if (!myTurn() || cityIdStr === "") return;
    game.assignSpy(game.viewer, spyId, parseInt(cityIdStr, 10));
    SFX.play("spy");
    showSpyScreen();
  }

  // ---------------- diplomacy screen ----------------
  function showDiploScreen() {
    const p = game.players[game.viewer];
    const modal = $("diplo-modal");
    modal.style.display = "flex";
    const body = $("diplo-body");
    let html = "";
    for (const p2 of game.players) {
      if (p2.index === game.viewer || p2.isMinor) continue;
      const met = p.met.has(p2.index);
      const civ = p2.civ;
      html += `<div class="diplo-row" style="border-left:6px solid ${met ? civ.color : "#555"}">
        <div><b>${met ? civ.name : "Unknown Civilization"}</b>
          ${met ? `<span class="dim"> — ${civ.leader}</span>` : ""}
          ${!p2.alive ? " <span class='dead'>☠️ destroyed</span>" : ""}</div>`;
      if (met && p2.alive) {
        const atWar = p.atWarWith.has(p2.index);
        const att = game.attitudeOf(p2.index, game.viewer);
        const attColor = att >= 10 ? "#2ecc71" : att <= -10 ? "#e74c3c" : "#aaa";
        const deal = p.deals.find(d => d.other === p2.index && d.ends > game.turn);
        const pact = p.pacts.has(p2.index);
        html += `<div class="dim">Score ${game.score(p2.index)} · Military ${Math.floor(game.militaryPower(p2.index))} ·
          ${atWar ? "<b class='war'>AT WAR</b>" : "at peace"} ·
          feels <b style="color:${attColor}">${game.attitudeLabel(p2.index, game.viewer)}</b> (${att >= 0 ? "+" : ""}${att})</div>`;
        if (deal) html += `<div class="dim">🤝 Trading your ${RESOURCE[deal.give].icon}${RESOURCE[deal.give].name} for their ${RESOURCE[deal.get].icon}${RESOURCE[deal.get].name} (until turn ${deal.ends})</div>`;
        if (pact) html += `<div class="dim">🛡️ Defensive pact — an attack on one is an attack on both</div>`;
        html += `<button onclick="UI.diploAction(${p2.index})">${atWar ? "☮️ Propose Peace" : "⚔️ Declare War"}</button>`;
        if (!atWar) {
          const canDeal = game.canLuxuryDeal(game.viewer, p2.index);
          const dealHint = canDeal ? `${RESOURCE[game.tradableLuxes(game.viewer, p2.index)[0]].icon} for ${RESOURCE[game.tradableLuxes(p2.index, game.viewer)[0]].icon}` : "";
          html += `<button ${canDeal ? "" : "disabled"} title="Swap surplus luxuries for ${DIPLO.luxuryDealTurns} turns — both sides gain happiness"
              onclick="UI.diploTrade(${p2.index})">🤝 Trade Luxuries ${dealHint}</button>
            <button ${p.gold >= DIPLO.giftGold ? "" : "disabled"} title="Improves their attitude toward you"
              onclick="UI.diploGift(${p2.index})">🎁 Gift ${DIPLO.giftGold}💰</button>
            <button ${game.canPact(game.viewer, p2.index) ? "" : "disabled"} title="Both sides must feel Friendly (attitude ${DIPLO.pactThreshold}+). If either is attacked, the other joins the war."
              onclick="UI.diploPact(${p2.index})">🛡️ Defensive Pact</button>`;
        }
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
        const status = game.minorStatus(game.viewer, m.index);
        const inf = Math.floor(p.influence[m.index] || 0);
        const statusTxt = { war: "<b class='war'>AT WAR</b>", ally: "<b style='color:#2ecc71'>ALLY</b>",
          friend: "<b style='color:#f1c40f'>Friend</b>", neutral: "neutral" }[status];
        html += `<div class="diplo-row" style="border-left:6px solid ${m.civ.color}">
          <div><b>${m.civ.name}</b> <span class="dim">${type.icon} ${type.name}</span> · ${statusTxt}</div>
          <div class="dim">${type.desc}</div>
          <div class="dim">Influence: ${inf} (friend ${INFLUENCE_FRIEND} · ally ${INFLUENCE_ALLY})</div>` +
          (m.quest ? `<div><b class="alert">🏛️ Quest:</b> ${game.questText(m.quest)} — +${QUESTS.reward} influence, ${m.quest.expires - game.turn} turns left` +
            (m.quest.type === "KILL_BARBS" ? ` <span class="dim">(you: ${(m.quest.progress[game.viewer] || 0)}/${QUESTS.killCount})</span>` : "") + `</div>` : "");
        if (status !== "war") {
          html += `<button ${p.gold >= 100 ? "" : "disabled"} onclick="UI.gift(${m.index},100)">🎁 100💰 (+25)</button>
            <button ${p.gold >= 250 ? "" : "disabled"} onclick="UI.gift(${m.index},250)">🎁 250💰 (+70)</button>`;
        }
        html += `<button onclick="UI.diploAction(${m.index})">${status === "war" ? "☮️ Propose Peace" : "⚔️ Declare War"}</button>
        </div>`;
      }
    }
    html += `<div class="diplo-row"><b>Your score:</b> ${game.score(game.viewer)} · Military ${Math.floor(game.militaryPower(game.viewer))}</div>`;
    body.innerHTML = html;
  }

  function gift(minorIdx, amount) {
    if (!myTurn()) return;
    if (game.giftInfluence(game.viewer, minorIdx, amount)) {
      SFX.play("coin");
      showDiploScreen();
      refreshAll();
    }
  }

  // ---- peace proposals from the AI (shown at the start of your turn) ----
  function maybeShowPeaceOffers() {
    if (!game || game.over || !myTurn()) return;
    const offers = game.pendingPeaceOffers(game.viewer);
    if (!offers.length) return;
    showPeaceModal(offers);
  }
  function showPeaceModal(offers) {
    const modal = $("peace-modal");
    const o = offers[0];
    const other = game.players[o.from];
    const civ = other.civ;
    $("peace-body").innerHTML = `
      <div class="diplo-row" style="border-left:6px solid ${civ.color}">
        <div><b>${civ.name}</b> <span class="dim">— ${civ.leader}</span></div>
        <div class="dim">Military ${Math.floor(game.militaryPower(o.from))} · they feel
          <b>${game.attitudeLabel(o.from, game.viewer)}</b> toward you</div>
        <p style="margin:10px 0">“Let us end this war and make peace.”</p>
      </div>
      <div style="display:flex;gap:10px;margin-top:6px">
        <button onclick="UI.answerPeace(${o.from}, true)">☮️ Accept Peace</button>
        <button onclick="UI.answerPeace(${o.from}, false)">⚔️ Fight On</button>
      </div>
      ${offers.length > 1 ? `<div class="dim" style="margin-top:8px">${offers.length - 1} more proposal${offers.length > 2 ? "s" : ""} pending…</div>` : ""}`;
    modal.style.display = "flex";
  }
  function answerPeace(fromIdx, accept) {
    if (accept) { game.acceptPeaceOffer(game.viewer, fromIdx); SFX.play("policy"); }
    else { game.declinePeaceOffer(game.viewer, fromIdx); }
    $("peace-modal").style.display = "none";
    refreshAll();
    // chain to the next pending offer, if any
    const rest = game.pendingPeaceOffers(game.viewer);
    if (rest.length) showPeaceModal(rest);
  }

  function diploAction(idx) {
    if (!myTurn()) return;
    const p = game.players[game.viewer];
    if (p.atWarWith.has(idx)) {
      // AI accepts peace if weary or losing
      const weary = (game.players[idx].warWeariness[0] || 0) > 12;
      const losing = game.militaryPower(idx) < game.militaryPower(game.viewer) * 0.8;
      if (weary || losing) game.makePeace(game.viewer, idx);
      else game.notify(`${game.players[idx].civ.name} refuses to make peace!`);
    } else {
      game.declareWar(game.viewer, idx);
    }
    showDiploScreen();
    refreshAll();
  }

  function diploTrade(idx) {
    if (!myTurn()) return;
    if (game.makeLuxuryDeal(game.viewer, idx)) { SFX.play("coin"); showDiploScreen(); refreshAll(); }
  }

  function diploGift(idx) {
    if (!myTurn()) return;
    if (game.giftGold(game.viewer, idx)) { SFX.play("coin"); showDiploScreen(); refreshAll(); }
  }

  function diploPact(idx) {
    if (!myTurn()) return;
    if (game.makePact(game.viewer, idx)) { SFX.play("peace"); showDiploScreen(); refreshAll(); }
  }

  // ---------------- social policies ----------------
  function showPolicyScreen() {
    const p = game.players[game.viewer];
    $("policy-modal").style.display = "flex";
    const cost = game.nextPolicyCost(game.viewer);
    const can = game.canAdoptPolicy(game.viewer);
    let html = `<div class="dim" style="margin-bottom:8px">
      🎭 Culture: <b>${Math.floor(p.culture)}</b> / ${cost} for the next policy (+${Math.floor(p._cpt || 0)} per turn)
      · Complete <b>${CULTURE_VICTORY_BRANCHES} branches</b> for a Cultural Victory
      (you have <b>${game.branchesDone(game.viewer)}</b>)</div><div class="policy-grid">`;
    for (const [bk, br] of Object.entries(POLICY_BRANCHES)) {
      const done = game.policyBranchDone(game.viewer, bk);
      html += `<div class="policy-branch${done ? " done" : ""}">
        <h3>${br.icon} ${br.name}</h3>
        <div class="dim">${br.blurb}</div>`;
      for (const [pk, pol] of Object.entries(br.policies)) {
        const has = p.policies.has(pk);
        html += `<div class="policy${has ? " has" : ""}">
          <b>${pol.name}</b><br><span class="dim">${pol.desc}</span>
          ${has ? `<span class="policy-check">✓</span>`
                : `<button ${can && myTurn() ? "" : "disabled"} onclick="UI.adoptPolicy('${pk}')">Adopt (${cost}🎭)</button>`}
        </div>`;
      }
      html += `<div class="dim policy-finisher">${done ? "✓ " : ""}Branch bonus: ${br.finisher}</div></div>`;
    }
    html += `</div>`;
    $("policy-body").innerHTML = html;
  }

  function adoptPolicy(key) {
    if (!myTurn()) return;
    if (game.adoptPolicy(game.viewer, key)) {
      SFX.play("policy");
      showPolicyScreen();
      refreshAll();
    }
  }

  // ---------------- top bar / notifications ----------------
  function refreshTopBar() {
    const p = game.players[game.viewer];
    let gold = 0, sci = 0, faith = 0;
    for (const c of game.cities) {
      if (c.owner !== game.viewer) continue;
      const y = game.cityYields(c);
      gold += y.gold; sci += y.sci; faith += y.faith;
    }
    gold -= Math.max(0, game.units.filter(u => u.owner === game.viewer).length - 4);
    gold += game.minorBonuses(game.viewer).gold;
    if (p.religionId !== null && game.religions[p.religionId].belief === "TITHE") {
      gold += game.religionFollowers(p.religionId);
    }
    const tech = p.researching ? TECHS[p.researching] : null;
    $("stat-turn").textContent = `Turn ${game.turn}/${game.maxTurns}`;
    const era = p.era();
    $("stat-era").textContent = ERAS[era] + " Era";
    SFX.setEra(era); // brighten the music (and chime) as ages pass
    // headline banner the first time the viewer reaches a new era
    if (lastEraShown === null) lastEraShown = era;
    else if (era > lastEraShown) {
      const icons = ["🏺", "🏛️", "⚔️", "📜", "⚙️"];
      showBanner(`${icons[era] || "✨"} You have entered the <b>${ERAS[era]} Era</b>`);
      lastEraShown = era;
    }
    $("stat-gold").textContent = `💰 ${Math.floor(p.gold)} (${gold >= 0 ? "+" : ""}${gold})`;
    $("stat-sci").innerHTML = tech
      ? `🔬 ${tech.name} ${Math.floor(p.scienceStored)}/${game.techCost(p.researching)} (+${sci})`
      : `🔬 <b class="alert">choose research!</b> (+${sci})`;
    // happiness + golden age
    const hap = game.happinessOf(game.viewer);
    const lux = game.luxuryTypesOf(game.viewer);
    const nCities = game.cities.filter(c => c.owner === game.viewer).length;
    const popTotal = game.cities.filter(c => c.owner === game.viewer).reduce((a, c) => a + c.pop, 0);
    const happyEl = $("stat-happy");
    if (p.goldenAgeTurns > 0) {
      happyEl.innerHTML = `✨ <b style="color:#f1c40f">GOLDEN AGE</b> (${p.goldenAgeTurns})`;
      happyEl.title = "+20% gold and production";
    } else {
      happyEl.innerHTML = hap >= 0 ? `😊 +${hap}` : `<b class="${hap < HAPPINESS.strikeAt ? "war" : "alert"}">😞 ${hap}</b>`;
      happyEl.title = `Happiness: ${HAPPINESS.base} base + ${lux.length * HAPPINESS.perLuxury} luxuries (${lux.map(l => RESOURCE[l].icon).join("") || "none"}) + buildings − ${nCities * HAPPINESS.perCity} cities − ${Math.floor(popTotal * HAPPINESS.perPop)} population` +
        `\nGolden Age: ${Math.floor(p.gaMeter)}/${GOLDEN_AGE.threshold(p.gaCount)} (surplus happiness fills the meter)`;
    }
    const cpt = Math.floor(p._cpt || 0);
    $("stat-culture").innerHTML = game.canAdoptPolicy(game.viewer)
      ? `🎭 <b class="alert">new policy!</b>`
      : `🎭 ${Math.floor(p.culture)}/${game.nextPolicyCost(game.viewer)} (+${cpt})`;
    const relIcon = p.religionId !== null ? game.religions[p.religionId].icon : "☦️";
    $("stat-faith").innerHTML = game.canFoundReligion(game.viewer)
      ? `${relIcon} <b class="alert">found a religion!</b>`
      : `${relIcon} ${Math.floor(p.faith)} (+${faith})`;
    $("stat-score").textContent = game.scenario ? game.scenarioStatus() : `🏆 ${game.score(game.viewer)}`;
    refreshEndTurnButton();
  }

  // ---------------- victory progress ----------------
  function showVictoryProgress() {
    if (!game) return;
    const body = $("progress-body");
    if (game.scenario) {
      const sc = SCENARIOS[game.scenario];
      body.innerHTML = `<div class="scenario-progress">
        <strong>${sc.icon} ${sc.name}</strong>
        <div>${game.scenarioStatus()}</div>
        <p class="dim">${sc.blurb}</p>
        <span class="dim">Turn ${game.turn} of ${game.maxTurns}</span>
      </div>`;
      $("progress-modal").style.display = "flex";
      return;
    }

    const me = game.players[game.viewer];
    const v = game.victoryProgress(game.viewer);
    const percent = (current, target) => target > 0 ? Math.min(100, Math.round(current / target * 100)) : 0;
    const route = (icon, title, value, progress, color, description) => `
      <div class="victory-route" style="--route:${color};--progress:${progress}%">
        <div class="victory-route-head"><span class="victory-route-icon">${icon}</span>
          <span class="victory-route-title">${title}</span><span class="victory-route-value">${value}</span></div>
        <div class="victory-meter"><i></i></div><p>${description}</p>
      </div>`;

    const religionValue = v.religion.founded
      ? `${v.religion.current}/${v.religion.target} cities`
      : "Not founded";
    const religionDesc = v.religion.founded
      ? `${v.religion.icon} ${v.religion.name} leads ${v.religion.civs}/${v.religion.civTarget} civilizations and ${v.religion.current}/${v.religion.target} major cities. Complete ${v.religion.spreads}/${v.religion.spreadTarget} missionary spreads; ${v.religion.religions}/${v.religion.religionTarget} competing religions exist.`
      : "Found a religion, complete six missionary spreads, then make it the majority faith in every surviving civilization and over 60% of all major cities. At least two religions must compete.";
    const diploValue = v.diplomacy.unlocked
      ? `${v.diplomacy.current}/${v.diplomacy.target} delegates`
      : "Congress locked";
    const diploDesc = v.diplomacy.unlocked
      ? `Ally city-states and reach ${Math.round(WCONGRESS.winFraction * 100)}% of ${v.diplomacy.total} delegates in one World Congress vote.`
      : `Research ${TECHS[WCONGRESS.unlockTech].name}; Congress sessions begin on turn ${WCONGRESS.startTurn}.`;

    const routes = [
      route("⚔️", "Domination", `${v.domination.current}/${v.domination.target} capitals`,
        percent(v.domination.current, v.domination.target), "#dc765f", "Capture and hold every civilization's original capital, or become the last major power standing."),
      route("🔬", "Scientific", `${v.science.current}/${v.science.target} technologies`,
        percent(v.science.current, v.science.target), "#63b6d8", "Master the complete technology tree before another civilization closes out its own victory route."),
      route("🎭", "Cultural", `${v.culture.current}/${v.culture.target} branches`,
        percent(v.culture.current, v.culture.target), "#d8a85e", `Complete every policy in ${CULTURE_VICTORY_BRANCHES} social-policy branches.`),
      route(v.religion.icon || "☦️", "Religious", religionValue,
        v.religion.founded ? percent(v.religion.current, v.religion.target) : 0, "#c28bd8", religionDesc),
      route("🏛️", "Diplomatic", diploValue,
        v.diplomacy.unlocked ? percent(v.diplomacy.current, v.diplomacy.target) : 0, "#79b88a", diploDesc),
      route("🏆", "Score", `#${v.score.rank} · ${v.score.current} points`,
        percent(game.turn, game.maxTurns), "#d9ba68", `${v.score.turnsLeft} turns remain. If no one wins another way, the highest score takes the game.`),
    ].join("");

    const known = game.players.filter(p => !p.isMinor && !p.isBarb && p.alive &&
      (p.index === game.viewer || me.met.has(p.index)))
      .sort((a, b) => game.score(b.index) - game.score(a.index));
    const standings = known.map((p, i) => {
      const religion = p.religionId !== null && game.religions[p.religionId];
      return `<div class="standing-row${p.index === game.viewer ? " me" : ""}">
        <span class="standing-rank">${i + 1}</span><span class="standing-civ" style="color:${p.civ.color}">${p.civ.name}${p.index === game.viewer ? " · you" : ""}</span>
        <span>${game.score(p.index)} pts</span><span>${game.cities.filter(c => c.owner === p.index).length} cities</span>
        <span>${p.techs.size} techs</span><span>${religion ? religion.icon + " " + religion.name : "No religion"}</span>
      </div>`;
    }).join("");
    const unknown = game.players.filter(p => !p.isMinor && !p.isBarb && p.alive &&
      p.index !== game.viewer && !me.met.has(p.index)).length;
    body.innerHTML = `<div class="victory-intro"><span>Six distinct paths can end the campaign.</span>
      <span><b>${me.civ.name}</b> · Turn ${game.turn}/${game.maxTurns}</span></div>
      <div class="victory-routes">${routes}</div>
      <div class="victory-standings"><h3>Known standings</h3>
        <div class="standing-row header"><span>#</span><span>Civilization</span><span>Score</span><span>Cities</span><span>Tech</span><span>Faith</span></div>
        ${standings}${unknown ? `<div class="dim" style="padding:8px">${unknown} civilization${unknown > 1 ? "s remain" : " remains"} unmet.</div>` : ""}
      </div>`;
    $("progress-modal").style.display = "flex";
  }

  // ---------------- headline banner ----------------
  let lastEraShown = null, bannerTimer = null;
  function showBanner(html) {
    const b = $("game-banner");
    b.innerHTML = html;
    b.classList.remove("show"); void b.offsetWidth; // restart the animation
    b.classList.add("show");
    clearTimeout(bannerTimer);
    bannerTimer = setTimeout(() => b.classList.remove("show"), 3200);
  }

  let notifSeen = 0;
  const NOTIF_SOUNDS = [
    [/WAR!/, "war"], [/Peace between|refuses to make peace/, "peace"],
    [/GOLDEN AGE/, "golden"], [/Research complete/, "research"],
    [/has been completed/, "wonder"], [/A great soul is born/, "greatperson"],
    [/adopts .*(branch|Hearth|Elders|Homestead|Harvest|Warrior|Brotherhood|Frontiersmen|Guslars|Bazaar|Caravanserai|Guilds|Minters|Icons|Frescoes|Synod|Pilgrims)|completes the .* branch/, "policy"],
    [/World Congress|World Leader/, "vote"],
    [/founded|now follows/, "bell"],
    [/captured/, "capture"], [/🕵️/, "spy"], [/destroyed/, "defeat"],
    [/gifts you/, "coin"], [/grew to/, "grow"], [/finished/, "build"],
    [/Bumper Harvest|Migrants|Sacred Relics|Wandering Scholars|Favourable Trade|Festival/, "goodevent"],
    [/Plague|Civil Unrest|Great Fire|Brigands|Drought/, "badevent"],
  ];

  // ---------------- menu: save slots, export/import ----------------
  function slotMeta(i) {
    try {
      const raw = localStorage.getItem("balkan-civ-slot" + i);
      if (!raw) return null;
      const d = JSON.parse(raw);
      return d.ts ? d : null;
    } catch (e) { return null; }
  }

  function showMenuModal() {
    $("menu-modal").style.display = "flex";
    let html = `<h2>☰ Menu</h2><div class="prod-list">`;
    for (let i = 1; i <= 3; i++) {
      const meta = slotMeta(i);
      html += `<div class="prod-item">
        <span>💾 Slot ${i}${meta ? ` <span class="dim">— ${meta.label}</span>` : ` <span class="dim">— empty</span>`}</span>
        <button onclick="UI.saveSlot(${i})">Save</button>
        <button ${meta ? "" : "disabled"} onclick="UI.loadSlot(${i})">Load</button>
        <span></span>
      </div>`;
    }
    const is3d = !!rend.three;
    html += `</div>
      <div style="margin-top:12px">
        <button onclick="UI.exportSave()">📤 Export save file</button>
        <button onclick="document.getElementById('file-import').click()">📥 Import save file</button>
        <button onclick="UI.toggleGraphics()">🎨 Switch to ${is3d ? "Classic 2D" : "3D"} graphics</button>
        <button onclick="UI.showSettings()">⚙️ Settings</button>
        <button onclick="document.getElementById('menu-modal').style.display='none'">▶ Resume</button>
        <button onclick="UI.toMainMenu()">🚪 Main Menu</button>
      </div>
      <p class="dim" style="margin-top:8px">The game also auto-saves every turn. Exported files can be
      shared to continue a game on another machine.${is3d ? " In 3D mode, rotate the camera with Q / W." : ""}</p>`;
    $("menu-body").innerHTML = html;
  }

  function saveSlot(i) {
    const p = game.players[game.viewer];
    try {
      localStorage.setItem("balkan-civ-slot" + i, JSON.stringify({
        ts: Date.now(),
        label: `${p.civ.name}, turn ${game.turn}`,
        state: game.serialize(),
      }));
      SFX.play("click");
      showMenuModal();
    } catch (e) { alert("Could not save (storage full?)."); }
  }

  function loadSlot(i) {
    const meta = slotMeta(i);
    if (!meta) return;
    try {
      game = Game.deserialize(meta.state);
      NET.reset();
      $("menu-modal").style.display = "none";
      startPlaying();
    } catch (e) { alert("That slot could not be loaded."); }
  }

  function exportSave() {
    const blob = new Blob([game.serialize()], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    const p = game.players[game.viewer];
    a.download = `balkan-civ-${p.civ.name.toLowerCase()}-turn${game.turn}.json`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function toMainMenu() {
    $("menu-modal").style.display = "none";
    NET.reset();
    showStartScreen();
  }

  // ---------------- settings & accessibility ----------------
  let civColorOriginals = null;

  function applyColorblind(on) {
    if (!civColorOriginals) {
      civColorOriginals = {};
      for (const id of CIV_IDS) civColorOriginals[id] = { color: CIVS[id].color, color2: CIVS[id].color2 };
    }
    for (const id of CIV_IDS) {
      const src = on && COLORBLIND_PALETTE[id] ? COLORBLIND_PALETTE[id] : civColorOriginals[id];
      CIVS[id].color = src.color; CIVS[id].color2 = src.color2;
    }
    // Player.civ caches a merged civ+leader object (which includes colour), so
    // invalidate it or the diplomacy/congress/graph UI would keep stale colours.
    if (game) for (const p of game.players) p._civCache = null;
    if (rend) {
      rend._visSnap = null; rend._ownSnap = null; // force 3D recolor + border/banner rebuild
      rend.dirty = true;
    }
  }

  function applyReduceMotion(on) {
    if (rend) rend.reduceMotion = on;
  }

  // apply saved accessibility prefs; called at boot and after a renderer swap
  function applyAccessibility() {
    applyColorblind(localStorage.getItem("balkan-civ-colorblind") === "1");
    applyReduceMotion(localStorage.getItem("balkan-civ-reduce-motion") === "1");
  }

  function showSettingsModal() {
    $("settings-modal").style.display = "flex";
    const cb = localStorage.getItem("balkan-civ-colorblind") === "1";
    const rm = localStorage.getItem("balkan-civ-reduce-motion") === "1";
    const tipsOff = localStorage.getItem("balkan-civ-tips-off") === "1";
    $("settings-body").innerHTML = `
      <label class="setting"><input type="checkbox" id="set-colorblind" ${cb ? "checked" : ""}>
        <span><b>Colorblind-friendly colours</b><br><span class="dim">Recolours the nine civilizations with a palette distinguishable under common colour blindness.</span></span></label>
      <label class="setting"><input type="checkbox" id="set-motion" ${rm ? "checked" : ""}>
        <span><b>Reduce motion</b><br><span class="dim">Stops the animated sea, drifting sun, and attack lunges. Helps on slower devices and for motion sensitivity.</span></span></label>
      <label class="setting"><input type="checkbox" id="set-tips" ${tipsOff ? "" : "checked"}>
        <span><b>Show advisor tips</b><br><span class="dim">One-time contextual hints for newcomers.</span></span></label>
      <div style="margin-top:12px">
        <button onclick="document.getElementById('settings-modal').style.display='none'">▶ Close</button>
      </div>`;
    $("set-colorblind").onchange = (e) => {
      localStorage.setItem("balkan-civ-colorblind", e.target.checked ? "1" : "0");
      applyColorblind(e.target.checked);
      if (rend.selectedCity) showCityPanel(rend.selectedCity);
    };
    $("set-motion").onchange = (e) => {
      localStorage.setItem("balkan-civ-reduce-motion", e.target.checked ? "1" : "0");
      applyReduceMotion(e.target.checked);
    };
    $("set-tips").onchange = (e) => {
      localStorage.setItem("balkan-civ-tips-off", e.target.checked ? "0" : "1");
    };
  }

  // switching between the WebGL and 2D canvas renderers needs a reload
  // (a canvas can hold only one kind of context); autosave first.
  function toggleGraphics() {
    if (NET.active) { alert("Finish the online game first — switching graphics reloads the page."); return; }
    const is3d = !!rend.three;
    localStorage.setItem("balkan-civ-gfx", is3d ? "2d" : "3d");
    if (game && !game.over) {
      try {
        localStorage.setItem("balkan-civ-save", game.serialize());
        localStorage.setItem("balkan-civ-resume", "1");
      } catch (e) { /* storage full — reload to the menu instead */ }
    }
    location.reload();
  }

  function showLogModal() {
    const p = game.players[game.viewer];
    $("log-modal").style.display = "flex";
    const forMe = (n) => n.p === undefined || n.p === -1 || n.p === game.viewer;
    const mine = game.notifications.filter(forMe).slice(-100).reverse();
    $("log-body").innerHTML = mine.map(n =>
      `<div class="notif" style="pointer-events:auto"><span class="dim">T${n.turn}</span> ${n.msg}</div>`).join("") ||
      `<div class="dim">Nothing has happened yet.</div>`;
  }

  // ---------------- Civilopedia ----------------
  // A searchable reference generated straight from the data tables, so it
  // never drifts from the rules. Entries: {cat, name, icon, tags, html}.
  let pediaEntries = null, pediaCat = "All";

  function buildPediaEntries() {
    const E = [];
    const yields = (o) => {
      const parts = [];
      for (const [k, lbl] of [["food", "🍞"], ["prod", "⚙️"], ["gold", "💰"], ["sci", "🔬"],
        ["culture", "🎭"], ["faith", "☦️"], ["happy", "😊"], ["cityHp", "🏰HP"], ["cityStr", "🏰Str"]]) {
        if (o[k]) parts.push(`${lbl}+${o[k]}`);
      }
      return parts.join(" ");
    };
    // Units
    for (const [key, u] of Object.entries(UNITS)) {
      const stats = [];
      if (u.cs) stats.push(`⚔️ ${u.cs}`);
      if (u.rs) stats.push(`🎯 ${u.rs} (range ${u.range})`);
      stats.push(`👟 ${u.moves}`);
      if (u.cost) stats.push(`⚙️ ${u.cost}`);
      if (u.faithCost) stats.push(`☦️ ${u.faithCost}`);
      const notes = [];
      if (u.tech) notes.push(`Needs <b>${TECHS[u.tech].name}</b>`);
      if (u.needs) notes.push(`Requires <b>${RESOURCE[u.needs].name}</b>`);
      if (u.uu) notes.push(`Unique to <b>${CIVS[u.uu].name}</b> (replaces ${UNITS[u.replaces].name})`);
      if (u.upgrade) notes.push(`Upgrades to ${UNITS[u.upgrade].name}`);
      if (u.siege) notes.push("Siege: +100% vs cities");
      if (u.naval) notes.push("Naval unit — built in coastal cities");
      if (u.great) notes.push("Great Person — earned, not built");
      E.push({ cat: "Units", name: u.name, icon: u.icon, tags: key.toLowerCase(),
        html: `<div class="dim">${stats.join(" · ")}</div>${u.blurb ? `<p>${u.blurb}</p>` : ""}${notes.length ? `<p class="dim">${notes.join(" · ")}</p>` : ""}` });
    }
    // Buildings & wonders
    for (const [key, b] of Object.entries(BUILDINGS)) {
      const notes = [];
      if (b.tech) notes.push(`Needs <b>${TECHS[b.tech].name}</b>`);
      if (b.requires) notes.push(`Requires ${BUILDINGS[b.requires].name}`);
      E.push({ cat: b.wonder ? "Wonders" : "Buildings", name: b.name, icon: b.icon, tags: key.toLowerCase(),
        html: `<div class="dim">⚙️ ${b.cost} · ${yields(b)}</div>${b.blurb ? `<p>${b.blurb}</p>` : ""}${notes.length ? `<p class="dim">${notes.join(" · ")}</p>` : ""}${b.wonder ? `<p class="dim">World wonder — only one may exist.</p>` : ""}` });
    }
    // Techs
    for (const [key, t] of Object.entries(TECHS)) {
      const unlocks = [];
      for (const [uk, u] of Object.entries(UNITS)) if (u.tech === key) unlocks.push(u.icon + u.name);
      for (const [bk, b] of Object.entries(BUILDINGS)) if (b.tech === key) unlocks.push(b.icon + b.name);
      E.push({ cat: "Techs", name: t.name, icon: "🔬", tags: key.toLowerCase(),
        html: `<div class="dim">${ERAS[t.era]} Era · 🔬 ${t.cost}${t.req.length ? " · after " + t.req.map(r => TECHS[r].name).join(", ") : ""}</div>${unlocks.length ? `<p>Unlocks: ${unlocks.join(", ")}</p>` : ""}` });
    }
    // Policies
    for (const [bk, br] of Object.entries(POLICY_BRANCHES)) {
      let inner = `<p class="dim">${br.blurb}</p>`;
      for (const [pk, pol] of Object.entries(br.policies)) inner += `<p><b>${pol.name}</b> — ${pol.desc}</p>`;
      inner += `<p class="dim">Branch bonus: ${br.finisher}</p>`;
      E.push({ cat: "Policies", name: br.name + " branch", icon: br.icon, tags: bk.toLowerCase(),
        html: inner });
    }
    // Promotions
    for (const [pk, pr] of Object.entries(PROMOS)) {
      E.push({ cat: "Policies", name: pr.name + " (promotion)", icon: pr.icon, tags: "promotion " + pk.toLowerCase(),
        html: `<p>${pr.desc}</p><p class="dim">Chosen when a unit gains a level.</p>` });
    }
    // Religion
    for (const [bk, bl] of Object.entries(BELIEFS)) {
      E.push({ cat: "Religion", name: bl.name, icon: "☦️", tags: "belief " + bk.toLowerCase(),
        html: `<p>${bl.desc}</p><p class="dim">A founder belief, chosen when you found a religion.</p>` });
    }
    for (const [mk, mt] of Object.entries(MINOR_TYPES)) {
      E.push({ cat: "Religion", name: mt.name + " city-state", icon: mt.icon, tags: "city-state minor " + mk,
        html: `<p>${mt.desc}</p><p class="dim">Raise influence with gifts or by completing its quests to become Friend (${INFLUENCE_FRIEND}) or Ally (${INFLUENCE_ALLY}).</p>` });
    }
    // Civilizations (with all their leaders)
    for (const id of CIV_IDS) {
      const civ = CIVS[id];
      const uu = UNITS[civ.uu];
      const leaders = civ.leaders.map(L => `<p><b>${L.leader}</b> — <i>${L.trait}</i>: ${L.traitDesc}</p>`).join("");
      E.push({ cat: "Civilizations", name: civ.name, icon: "⚔️",
        tags: id.toLowerCase() + " " + civ.leaders.map(L => L.leader.toLowerCase()).join(" "),
        html: `<p><b>${uu.icon} ${uu.name}</b> — ${uu.blurb}</p><div class="dim">Leaders:</div>${leaders}` });
    }
    // Victory conditions
    E.push({ cat: "Victory", name: "Domination Victory", icon: "⚔️", tags: "victory domination conquest",
      html: `<p>Be the last major civilization standing, or capture and hold every major civ's original capital.</p>` });
    E.push({ cat: "Victory", name: "Cultural Victory", icon: "🎭", tags: "victory culture policy",
      html: `<p>Complete every policy in <b>${CULTURE_VICTORY_BRANCHES} of the ${Object.keys(POLICY_BRANCHES).length} social-policy branches</b>. Culture accumulates from Monuments, Temples, wonders, and policies.</p>` });
    E.push({ cat: "Victory", name: "Scientific Victory", icon: "🔬", tags: "victory science research technology",
      html: `<p>Research all <b>${Object.keys(TECHS).length} technologies</b> in the tree. Libraries, Universities, scientific wonders, Great Scientists, and espionage can accelerate the race.</p>` });
    E.push({ cat: "Victory", name: "Religious Victory", icon: "☦️", tags: "victory religion faith missionary",
      html: `<p>Complete at least <b>${RELIGION_VICTORY.minSpreads} Missionary spreads</b>, then make your founded religion the majority faith in <b>every surviving major civilization</b> and in over ${Math.round(RELIGION_VICTORY.share * 100)}% of all major-civilization cities. At least ${RELIGION_VICTORY.minCities} major cities and ${RELIGION_VICTORY.minReligions} competing religions must exist.</p>` });
    E.push({ cat: "Victory", name: "Diplomatic Victory", icon: "🏛️", tags: "victory diplomacy congress world leader",
      html: `<p>Once a civilization researches <b>${TECHS[WCONGRESS.unlockTech].name}</b>, the <b>World Congress</b> convenes every ${WCONGRESS.interval} turns to elect a World Leader. Each civ casts delegates — ${WCONGRESS.base} base, <b>+${WCONGRESS.perAlly} per allied city-state</b>, and +1 per ${WCONGRESS.perCities} cities. Win <b>${Math.round(WCONGRESS.winFraction * 100)}%</b> of all delegates in a single vote to be elected and win. Allying city-states is the key.</p>` });
    E.push({ cat: "Victory", name: "Score Victory", icon: "🏆", tags: "victory score time",
      html: `<p>If no one has won when the turn limit is reached, the civilization with the highest score (cities, population, techs, wonders) wins.</p>` });
    return E;
  }

  function showPediaScreen(initialQuery) {
    if (!pediaEntries) pediaEntries = buildPediaEntries();
    $("pedia-modal").style.display = "flex";
    const cats = ["All", "Units", "Buildings", "Wonders", "Techs", "Policies", "Religion", "Civilizations", "Victory"];
    $("pedia-tabs").innerHTML = cats.map(c =>
      `<button class="pedia-tab${c === pediaCat ? " active" : ""}" data-cat="${c}">${c}</button>`).join("");
    $("pedia-tabs").querySelectorAll("button").forEach(b => b.onclick = () => { pediaCat = b.dataset.cat; renderPedia(); });
    if (initialQuery !== undefined) $("pedia-search").value = initialQuery;
    renderPedia();
    setTimeout(() => $("pedia-search").focus(), 30);
  }

  function renderPedia() {
    const q = $("pedia-search").value.trim().toLowerCase();
    $("pedia-tabs").querySelectorAll("button").forEach(b =>
      b.classList.toggle("active", b.dataset.cat === pediaCat));
    let list = pediaEntries.filter(e => pediaCat === "All" || e.cat === pediaCat);
    if (q) list = list.filter(e => e.name.toLowerCase().includes(q) || e.tags.includes(q) ||
      e.html.toLowerCase().includes(q) || e.cat.toLowerCase().includes(q));
    // group by category when showing All
    const body = $("pedia-body");
    if (!list.length) { body.innerHTML = `<div class="dim">No entries match “${q}”.</div>`; return; }
    let html = "";
    let lastCat = null;
    for (const e of list) {
      if (pediaCat === "All" && e.cat !== lastCat) { html += `<h3>${e.cat}</h3>`; lastCat = e.cat; }
      html += `<div class="pedia-entry"><div class="pedia-name">${e.icon} <b>${e.name}</b></div>${e.html}</div>`;
    }
    body.innerHTML = html;
  }

  // Notifications surface as transient toasts that fade after a few seconds so
  // they never pile up and cover the map; the full history lives in the log
  // (click the panel). Only genuinely new entries toast — notifSeen advances.
  function addNotifToast(n) {
    const list = $("notif-list");
    const div = document.createElement("div");
    div.className = "notif";
    div.innerHTML = `<span class="dim">T${n.turn}</span> ${n.msg}`;
    list.appendChild(div);
    while (list.children.length > 6) list.removeChild(list.firstChild);
    list.scrollTop = list.scrollHeight;
    const dwell = rend && rend.reduceMotion ? 9000 : 6500;
    setTimeout(() => {
      div.classList.add("fade");
      setTimeout(() => { if (div.parentNode) div.parentNode.removeChild(div); }, 700);
    }, dwell);
  }
  function refreshNotifications() {
    const all = game.notifications;
    const forMe = (n) => n.p === undefined || n.p === -1 || n.p === game.viewer;
    let playedSound = false;
    for (let i = notifSeen; i < all.length; i++) {
      if (!forMe(all[i])) continue;
      if (!playedSound) {
        const hit = NOTIF_SOUNDS.find(([re]) => re.test(all[i].msg));
        if (hit) { SFX.play(hit[1]); playedSound = true; } // at most one sound per refresh
      }
      addNotifToast(all[i]);
    }
    notifSeen = all.length;
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
    refreshAttention();
    maybeAdvise();
    maybeShowCongress();
    maybeShowRecap();
    if (game.over) showVictory();
  }

  // ---------------- needs-attention panel ----------------
  // Compact clickable checklist of what still needs the player's decision
  // this turn, so a long turn never leaves you wondering "what now?".
  function computeAttention() {
    const items = [];
    if (!myTurn() || game.over) return items;
    const v = game.viewer;
    const pending = game.pendingOrders(v);
    if (pending.research)
      items.push({ icon: "🔬", label: "Choose research", tipKey: "research",
        hint: "Choose the technology path that will shape your next units and buildings.", act: showTechScreen });
    if (pending.congress)
      items.push({ icon: "🗳️", label: "Congress vote", act: () => { congressSeenTurn = -1; maybeShowCongress(); } });
    if (pending.religion)
      items.push({ icon: "☦️", label: "Found religion", tipKey: "religion",
        hint: "Choose a founder belief, then spread the faith with Missionaries.", act: showReligionScreen });
    if (pending.policy)
      items.push({ icon: "🎭", label: "Adopt policy", tipKey: "policy",
        hint: "Spend culture on a policy branch; completing three branches wins a Cultural Victory.", act: showPolicyScreen });
    const promoUnit = pending.promotionUnit;
    if (promoUnit)
      items.push({ icon: "⭐", label: "Promote unit", tipKey: "promote",
        hint: "Select a veteran upgrade before sending this unit back into battle.",
        act: () => { selectUnit(promoUnit); rend.centerOn(game, promoUnit.c, promoUnit.r); } });
    const idleCity = pending.cities[0];
    if (idleCity)
      items.push({ icon: "🏙️", label: "Set production", tipKey: "founded",
        hint: "Choose what this city should build; early military and workers establish momentum.",
        act: () => { selectCity(idleCity); rend.centerOn(game, idleCity.c, idleCity.r); } });
    const idleUnits = pending.units;
    if (idleUnits.length)
      items.push({ icon: "🎖️", label: `${idleUnits.length} unit${idleUnits.length > 1 ? "s" : ""} to move`, act: cycleNextUnit });
    return items;
  }

  function refreshAttention() {
    const el = $("attention");
    const items = computeAttention();
    if (!items.length) { el.style.display = "none"; el.innerHTML = ""; return; }
    for (const it of items) if (it.tipKey) markAdvisorSeen(it.tipKey);
    if (items.some(it => it.tipKey === $("advisor").dataset.tipKey)) hideAdvisor();
    el.style.display = "flex";
    el.innerHTML = `<span class="attention-title">Needs you:</span>` +
      items.map((it, i) => `<button class="attention-chip" data-i="${i}" title="${it.hint || ""}">${it.icon} ${it.label}</button>`).join("");
    el.querySelectorAll(".attention-chip").forEach(b => b.onclick = () => items[parseInt(b.dataset.i, 10)].act());
  }

  // ---------------- turn recap ----------------
  // A brief note at the start of your turn recapping what happened while the
  // world advanced — grown cities, finished builds, research, events.
  let recapSnapshot = null;
  function snapshotForRecap() {
    if (!game || game.over) { recapSnapshot = null; return; }
    const v = game.viewer, p = game.players[v];
    recapSnapshot = { turn: game.turn, gold: Math.floor(p.gold), notifLen: game.notifications.length };
  }
  function maybeShowRecap() {
    if (!recapSnapshot || game.over || !myTurn() || game.turn <= recapSnapshot.turn) return;
    const v = game.viewer, p = game.players[v];
    // gather this player's notifications logged since the snapshot
    const fresh = game.notifications.slice(recapSnapshot.notifLen)
      .filter(n => n.p === undefined || n.p === -1 || n.p === v);
    const goldDelta = Math.floor(p.gold) - recapSnapshot.gold;
    recapSnapshot = null;
    const bits = [];
    if (goldDelta) bits.push(`${goldDelta > 0 ? "+" : ""}${goldDelta}💰`);
    // pull the most salient events (strip player-tag noise), max 3
    const salient = fresh.map(n => n.msg.replace(/<[^>]+>/g, "")).slice(0, 3);
    for (const s of salient) bits.push(s.length > 46 ? s.slice(0, 44) + "…" : s);
    if (!bits.length) return;
    const el = $("recap");
    el.innerHTML = `<b>Last turn:</b> ${bits.join(" · ")}`;
    el.classList.remove("show"); void el.offsetWidth;
    el.classList.add("show");
    clearTimeout(maybeShowRecap._t);
    maybeShowRecap._t = setTimeout(() => el.classList.remove("show"), 4500);
  }

  // ---------------- advisor tips ----------------
  // Contextual, one-time hints for newcomers. Each fires the first time its
  // `when` predicate holds; shown one at a time and remembered in localStorage.
  const ADVISOR_TIPS = [
    { key: "welcome", title: "Welcome, ruler!", when: () => game.turn <= 1,
      body: "Select your <b>Settler</b> and press <b>🏛️ Found City</b> on good ground (grassland near water, hills, or a resource). Your capital is the heart of your empire. Press <b>?</b> any time to open the Civilopedia." },
    { key: "founded", title: "Your first city", when: () => game.cities.some(c => c.owner === game.viewer),
      body: "Click a city to set what it <b>builds</b> and which tiles it works. Build a <b>Warrior</b> or <b>Scout</b> to explore and defend, then a <b>Worker</b> to improve your land. Cities grow with food and expand their borders with culture." },
    { key: "research", title: "Choose research", when: () => !game.players[game.viewer].researching && game.players[game.viewer].availableTechs().length > 0,
      body: "Press <b>T</b> to open the tech tree and pick what to research. Technologies unlock new units, buildings, and wonders — the path you choose shapes your civilization." },
    { key: "met", title: "You are not alone", when: () => [...game.players[game.viewer].met].some(i => !game.players[i].isMinor && !game.players[i].isBarb),
      body: "You've met a rival civilization. Press <b>D</b> for diplomacy — trade luxuries, send gifts, sign defensive pacts, or declare war. Watch their <b>attitude</b> toward you." },
    { key: "policy", title: "A social policy awaits", when: () => game.canAdoptPolicy(game.viewer),
      body: "Your culture has funded a <b>social policy</b> — press <b>P</b>. Policies come in four branches; complete three branches to win a <b>Cultural Victory</b>." },
    { key: "religion", title: "Found a religion", when: () => game.canFoundReligion(game.viewer),
      body: "You have enough <b>faith</b> to found a religion — click the faith readout or press <b>R</b>. Pick a belief that suits your strategy, then spread it with Missionaries." },
    { key: "promote", title: "Promote your veteran", when: () => game.units.some(u => u.owner === game.viewer && u.promoPts > 0),
      body: "A unit has earned a <b>promotion</b>. Select it and choose an upgrade — Might, Bulwark, Field Medic, or Pathfinder. Promotions stack, so seasoned units become formidable." },
    { key: "cityState", title: "City-states", when: () => [...game.players[game.viewer].met].some(i => game.players[i].isMinor),
      body: "You've met a <b>city-state</b>. Win its friendship with gold gifts or by completing its <b>quests</b> (open Diplomacy to see them) for bonuses to your empire." },
  ];

  // ---------------- World Congress ----------------
  let congressSeenTurn = -1;

  function maybeShowCongress() {
    if (!game || game.over || !game.congressDue || !game.congressDue()) return;
    if (!myTurn()) return;
    if (congressSeenTurn === game.turn) return;       // shown once this session
    const p = game.players[game.viewer];
    if (p.congressVoteTurn === game.turn) return;      // already voted
    congressSeenTurn = game.turn;
    showCongressModal();
  }

  function showCongressModal() {
    const me = game.viewer;
    const cands = game.congressCandidates();
    const total = cands.reduce((a, i) => a + game.congressDelegates(i), 0);
    const need = Math.ceil(total * WCONGRESS.winFraction);
    let html = `<p class="dim">Delegates come from your empire and, above all, your <b>city-state allies</b>.
      Cast your ${game.congressDelegates(me)} delegate(s). Whoever reaches <b>${need}</b> of ${total} is elected
      World Leader — a <b>Diplomatic Victory</b>.</p><div class="prod-list">`;
    for (const i of cands) {
      const pl = game.players[i];
      const del = game.congressDelegates(i);
      const isMe = i === me;
      html += `<div class="prod-item">
        <span><b style="color:${pl.civ.color}">${pl.civ.name}</b>${isMe ? " (you)" : ""}
          <span class="dim">— ${pl.leaderName} · ${del} delegate${del !== 1 ? "s" : ""}</span></span>
        <button ${myTurn() ? "" : "disabled"} onclick="UI.congressVote(${i})">🗳️ Vote</button>
      </div>`;
    }
    html += `</div><div style="margin-top:10px"><button onclick="UI.congressAbstain()">Abstain</button></div>`;
    $("congress-body").innerHTML = html;
    $("congress-modal").style.display = "flex";
  }

  function congressVote(idx) {
    if (!myTurn()) return;
    const p = game.players[game.viewer];
    p.congressVote = idx; p.congressVoteTurn = game.turn;
    SFX.play("vote");
    $("congress-modal").style.display = "none";
  }

  function congressAbstain() {
    const p = game.players[game.viewer];
    p.congressVote = null; p.congressVoteTurn = game.turn; // recorded so we don't renag
    $("congress-modal").style.display = "none";
  }

  function advisorEnabled() { return localStorage.getItem("balkan-civ-tips-off") !== "1"; }

  function advisorSeenKeys() {
    try { return new Set(JSON.parse(localStorage.getItem("balkan-civ-tips-seen") || "[]")); }
    catch (e) { return new Set(); }
  }

  function markAdvisorSeen(key) {
    if (!key) return;
    const seen = advisorSeenKeys();
    if (seen.has(key)) return;
    seen.add(key);
    try { localStorage.setItem("balkan-civ-tips-seen", JSON.stringify([...seen])); } catch (e) { /* storage full */ }
  }

  function maybeAdvise() {
    if (!advisorEnabled() || !game || game.over || $("advisor").style.display === "block") return;
    if (NET.active && game.activeHuman !== NET.myIndex) return;
    const seen = advisorSeenKeys();
    for (const tip of ADVISOR_TIPS) {
      if (seen.has(tip.key)) continue;
      let ok = false;
      try { ok = tip.when(); } catch (e) { ok = false; }
      if (!ok) continue;
      showAdvisor(tip);
      markAdvisorSeen(tip.key);
      return;
    }
  }

  function showAdvisor(tip) {
    $("advisor").dataset.tipKey = tip.key;
    $("advisor-title").innerHTML = "💡 " + tip.title;
    $("advisor-body").innerHTML = tip.body;
    $("advisor").style.display = "block";
    SFX.play("bell");
  }

  function hideAdvisor() { $("advisor").style.display = "none"; $("advisor").dataset.tipKey = ""; }

  // ---------------- end turn ----------------
  function pendingTurnAction() {
    if (!game || game.over) return { kind: "over" };
    if (!myTurn()) return { kind: "waiting" };
    const pending = game.pendingOrders(game.viewer);
    if (pending.research) return { kind: "research" };
    if (pending.congress) return { kind: "congress" };
    if (pending.cities.length) return { kind: "production", target: pending.cities[0] };
    if (pending.units.length) return { kind: "unit", target: pending.units[0], count: pending.units.length };
    return { kind: "ready" };
  }

  function refreshEndTurnButton() {
    const button = $("btn-endturn");
    if (!button) return;
    const action = pendingTurnAction();
    const labels = {
      over: "Game Complete", waiting: "Waiting…", research: "Choose Research",
      congress: "Cast Vote", production: "Choose Production", ready: "End Turn ⏵",
    };
    button.textContent = action.kind === "unit" ? `Next Unit (${action.count})` : labels[action.kind];
    button.dataset.state = action.kind;
    button.disabled = action.kind === "over" || action.kind === "waiting";
    button.title = action.kind === "ready" ? "Advance to the next turn"
      : action.kind === "unit" ? "Select the next unit that needs orders"
      : action.kind === "production" ? "Select a city that needs production"
      : action.kind === "research" ? "Choose a technology before ending the turn"
      : action.kind === "congress" ? "Cast your World Congress vote" : "";
  }

  function endTurn() {
    const action = pendingTurnAction();
    if (action.kind === "waiting" || action.kind === "over") return;
    if (action.kind === "research") { showTechScreen(); return; }
    if (action.kind === "congress") { congressSeenTurn = -1; maybeShowCongress(); return; }
    if (action.kind === "production") {
      selectCity(action.target); rend.centerOn(game, action.target.c, action.target.r); return;
    }
    if (action.kind === "unit") {
      selectUnit(action.target); rend.centerOn(game, action.target.c, action.target.r); return;
    }
    hideCombatPreview();
    undoInfo = null;
    SFX.play("turn");
    snapshotForRecap(); // capture state so the next turn can recap what changed
    const before = game.viewer;
    game.endTurn();
    try { localStorage.setItem("balkan-civ-save", game.serialize()); } catch (e) { /* storage full */ }
    if (rend.selected && !game.units.includes(rend.selected)) rend.selected = null;
    selectUnit(null);
    closeCity();
    if (NET.active) {
      game._viewer = NET.myIndex;
      NET.sendState(game);
      refreshAll();
      netUpdateBanner();
      if (myTurn() && !game.over) { cycleNextUnit(); maybePromptFounding(); maybeShowPeaceOffers(); }
      return;
    }
    if (game.humans > 1 && !game.over) {
      showHandoff();
      return;
    }
    refreshAll();
    if (!game.over) cycleNextUnit();
    maybePromptFounding();
    maybeShowPeaceOffers();
  }

  function maybePromptFounding() {
    if (game.canFoundReligion(game.viewer) &&
        foundingPromptTurn !== game.turn * 10 + game.viewer) {
      foundingPromptTurn = game.turn * 10 + game.viewer;
      showFoundingModal();
    }
  }

  // hotseat: blackout screen between human turns
  function showHandoff() {
    const p = game.players[game.viewer];
    $("handoff-modal").style.display = "flex";
    $("handoff-body").innerHTML = `
      <h2>🔄 Pass the device</h2>
      <p style="font-size:18px;margin:14px 0"><b style="color:${p.civ.color}">Player ${game.viewer + 1}</b>
      — ${p.civ.name} (${p.civ.leader})</p>
      <p class="dim">Turn ${game.turn}. No peeking at the other empires!</p>
      <button onclick="UI.beginHotseatTurn()" style="font-size:16px;padding:10px 28px;margin-top:10px">⚔ Begin Turn</button>`;
  }

  function beginHotseatTurn() {
    $("handoff-modal").style.display = "none";
    // start this player's toasts fresh; the recap panel covers what they missed
    notifSeen = game.notifications.length - Math.min(game.notifications.length, 3);
    const p = game.players[game.viewer];
    const home = game.cities.find(c => c.owner === game.viewer) ||
                 game.units.find(u => u.owner === game.viewer);
    if (home) rend.centerOn(game, home.c, home.r);
    refreshAll();
    cycleNextUnit();
    maybePromptFounding();
    maybeShowPeaceOffers();
  }

  function showVictory() {
    const modal = $("victory-modal");
    modal.style.display = "flex";
    const won = NET.active ? game.winner === NET.myIndex : game.players[game.winner].isHuman;
    SFX.play(won ? "fanfare" : "defeat");
    if (game.scenario) {
      const sc = SCENARIOS[game.scenario];
      const camp = recordCampaignResult(won);
      let extra = "", buttons = `<button onclick="UI.newGame()">Back to Menu</button>`;
      if (camp) {
        if (won) {
          extra = `<p class="campaign-progress">🎖️ +${camp.gained} glory${camp.firstTime ? " — chapter cleared!" : " (replay)"} · Total: <b>${camp.glory}</b></p>`;
          if (camp.campaignDone) {
            extra += `<p style="margin:12px 0"><b>🏆 The campaign is complete!</b><br>${CAMPAIGN.outro}</p>`;
            buttons = `<button onclick="UI.openCampaign()">🎖️ Campaign</button> <button onclick="UI.newGame()">Menu</button>`;
          } else if (camp.nextKey) {
            const ns = SCENARIOS[camp.nextKey];
            buttons = `<button onclick="UI.playChapter('${camp.nextKey}')">▶ Next: ${ns.icon} ${ns.name}</button>
              <button onclick="UI.openCampaign()">🎖️ Campaign</button>`;
          }
        } else {
          extra = `<p class="dim">The chapter is not yet won — try again.</p>`;
          buttons = `<button onclick="UI.playChapter('${game.scenario}')">↻ Retry Chapter</button>
            <button onclick="UI.openCampaign()">🎖️ Campaign</button>`;
        }
      }
      $("victory-body").innerHTML = `
        <h2>${won ? "🏆 SCENARIO COMPLETE" : "☠️ SCENARIO FAILED"}</h2>
        <h3>${sc.icon} ${sc.name} — ${sc.year}</h3>
        <p style="margin:14px 0;font-size:16px">${won ? sc.winText : sc.loseText}</p>
        <p class="dim">Finished on turn ${game.turn} of ${game.maxTurns}.</p>
        ${extra}
        <div>${buttons}</div>`;
      return;
    }
    const civ = CIVS[game.players[game.winner].civId];
    $("victory-body").innerHTML = `
      <h2>${won ? "🏆 VICTORY!" : "☠️ DEFEAT"}</h2>
      <p>${civ.name} ${won ? "— your empire —" : ""} has won a <b>${game.victoryType}</b> victory
      on turn ${game.turn}.</p>
      <p class="dim">Final score: ${game.players.filter(p => !p.isMinor && !p.isBarb).map(p => `${p.civ.name} ${game.score(p.index)}`).join(" · ")}</p>
      <canvas id="vic-graph" width="560" height="220" style="max-width:100%"></canvas>
      <div class="dim" id="vic-legend"></div>
      <button onclick="UI.newGame()">New Game</button>`;
    drawHistoryGraph();
  }

  function drawHistoryGraph() {
    const cv = $("vic-graph");
    if (!cv || game.history.length < 2) { if (cv) cv.style.display = "none"; return; }
    const ctx = cv.getContext("2d");
    const majors = game.players.filter(p => !p.isMinor && !p.isBarb);
    const W = cv.width, H = cv.height, pad = 24;
    ctx.fillStyle = "#0d1421";
    ctx.fillRect(0, 0, W, H);
    const maxScore = Math.max(1, ...game.history.map(h => Math.max(...h.s)));
    const n = game.history.length;
    majors.forEach((p, pi) => {
      ctx.strokeStyle = p.civ.color;
      ctx.lineWidth = 2;
      ctx.beginPath();
      game.history.forEach((h, i) => {
        const x = pad + (W - 2 * pad) * (i / (n - 1));
        const y = H - pad - (H - 2 * pad) * ((h.s[pi] || 0) / maxScore);
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      });
      ctx.stroke();
    });
    ctx.fillStyle = "#9a927e";
    ctx.font = "11px sans-serif";
    ctx.fillText("score", 4, 14);
    ctx.fillText("turn " + game.history[n - 1].t, W - 60, H - 6);
    $("vic-legend").innerHTML = majors.map(p =>
      `<span style="color:${p.civ.color}">■</span> ${p.civ.name}`).join(" &nbsp; ");
  }

  function newGame() {
    NET.reset();
    localStorage.removeItem("balkan-civ-save");
    $("victory-modal").style.display = "none";
    showStartScreen();
  }

  // ---------------- input ----------------
  function onMapClick(sx, sy, rightClick) {
    if (!myTurn()) return;
    const [c, r] = rend.screenToHex(sx, sy);
    const t = game.tile(c, r);
    if (!t) return;
    const p = game.players[game.viewer];
    if (!p.visible[game.map.idx(c, r)]) { selectUnit(null); return; }

    const sel = rend.selected;
    // attack?
    if (sel && !rightClick && rend.attackable.some(([ac, ar]) => ac === c && ar === r)) {
      if (pendingAttack && pendingAttack.unitId === sel.id && pendingAttack.c === c && pendingAttack.r === r)
        executePlayerAttack(sel, c, r);
      else showCombatPreview(sel, c, r);
      return;
    }
    // clicking an at-peace rival's unit/city in range: offer to declare war & strike
    if (sel && !rightClick && warTargetOwner(sel, c, r) >= 0) {
      showWarConfirm(sel, c, r);
      return;
    }
    // move?
    if (sel && sel.owner === game.viewer && (rightClick || rend.reachable.some(([mc, mr]) => mc === c && mr === r) ||
        (!game.combatUnitAt(c, r) && !t.city && !game.unitsAt(c, r).length))) {
      const isOwnTile = sel.c === c && sel.r === r;
      if (!isOwnTile && game.unitPassable(sel, t)) {
        SFX.play("move");
        snapshotUndo(sel);
        game.moveUnitTo(sel, c, r);
        validateUndo(sel);
        selectUnit(game.units.includes(sel) ? sel : null);
        refreshAll();
        return;
      }
    }
    // select city / unit
    if (t.city && t.city.owner === game.viewer) { selectCity(t.city); return; }
    if (t.city && t.city.owner !== game.viewer) { showCityPanel(t.city); rend.selected = null; rend.dirty = true; return; }
    const mine = game.unitsAt(c, r).filter(u => u.owner === game.viewer);
    if (mine.length) {
      // toggle through stacked units
      const cur = mine.indexOf(rend.selected);
      selectUnit(mine[(cur + 1) % mine.length]);
      return;
    }
    selectUnit(null);
  }

  // Generic touch: tap, long-press, one-finger pan, two-finger pinch/twist
  function bindTouch(cv, h) {
    let mode = null, sx = 0, sy = 0, lx = 0, ly = 0, t0 = 0, longTimer = null;
    let pinchD = 0, pinchMX = 0, pinchMY = 0, pinchA = 0;
    const pt = (t) => {
      const r = cv.getBoundingClientRect();
      return [t.clientX - r.left, t.clientY - r.top];
    };
    cv.addEventListener("touchstart", (e) => {
      e.preventDefault();
      if (e.touches.length === 1) {
        [sx, sy] = pt(e.touches[0]);
        [lx, ly] = [sx, sy];
        t0 = Date.now();
        mode = "tap";
        longTimer = setTimeout(() => {
          if (mode === "tap") { mode = "long"; h.longpress(sx, sy); }
        }, 550);
      } else if (e.touches.length === 2) {
        clearTimeout(longTimer);
        mode = "pinch";
        const [x1, y1] = pt(e.touches[0]), [x2, y2] = pt(e.touches[1]);
        pinchD = Math.hypot(x2 - x1, y2 - y1);
        pinchMX = (x1 + x2) / 2; pinchMY = (y1 + y2) / 2;
        pinchA = Math.atan2(y2 - y1, x2 - x1);
      }
    }, { passive: false });
    cv.addEventListener("touchmove", (e) => {
      e.preventDefault();
      if (e.touches.length === 1 && (mode === "tap" || mode === "pan")) {
        const [x, y] = pt(e.touches[0]);
        if (mode === "tap" && Math.hypot(x - sx, y - sy) > 9) {
          mode = "pan";
          clearTimeout(longTimer);
        }
        if (mode === "pan") {
          h.pan(x - lx, y - ly, x, y);
          [lx, ly] = [x, y];
        }
      } else if (e.touches.length === 2 && mode === "pinch") {
        const [x1, y1] = pt(e.touches[0]), [x2, y2] = pt(e.touches[1]);
        const d = Math.hypot(x2 - x1, y2 - y1);
        const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
        if (pinchD > 0) h.pinch(d / pinchD, mx, my, mx - pinchMX, my - pinchMY);
        if (h.twist) {
          const a = Math.atan2(y2 - y1, x2 - x1);
          let da = a - pinchA;
          if (da > Math.PI) da -= 2 * Math.PI;
          if (da < -Math.PI) da += 2 * Math.PI;
          h.twist(da);
          pinchA = a;
        }
        pinchD = d; pinchMX = mx; pinchMY = my;
      }
    }, { passive: false });
    cv.addEventListener("touchend", (e) => {
      e.preventDefault();
      clearTimeout(longTimer);
      if (mode === "tap" && Date.now() - t0 < 500) h.tap(sx, sy);
      if (e.touches.length === 0) mode = null;
    }, { passive: false });
  }

  function zoomAt(factor, mx, my) {
    const oldSize = rend.size;
    rend.cam.zoom = Math.min(2.2, Math.max(0.45, rend.cam.zoom * factor));
    const scale = rend.size / oldSize;
    rend.cam.x = (rend.cam.x + mx) * scale - mx;
    rend.cam.y = (rend.cam.y + my) * scale - my;
    rend.dirty = true;
  }

  function bindInput() {
    const cv = rend.canvas;
    bindTouch(cv, {
      tap: (x, y) => onMapClick(x, y, false),
      longpress: (x, y) => onMapClick(x, y, true),
      pan: (dx, dy) => { rend.cam.x -= dx; rend.cam.y -= dy; rend.dirty = true; },
      pinch: (f, mx, my, dx, dy) => { zoomAt(f, mx, my); rend.cam.x -= dx; rend.cam.y -= dy; },
      // two-finger twist rotates the 3D camera (no-op in classic 2D)
      twist: (da) => {
        if (!rend.three) return;
        rend.cam.rot = (rend.cam.rot || 0) - da;
        rend.dirty = true;
      },
    });
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
        updateHover(e);
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
      const rect = cv.getBoundingClientRect();
      zoomAt(e.deltaY < 0 ? 1.12 : 0.89, e.clientX - rect.left, e.clientY - rect.top);
    }, { passive: false });

    $("btn-zoom-in").onclick = () => zoomAt(1.18, cv.width / 2, cv.height / 2);
    $("btn-zoom-out").onclick = () => zoomAt(0.84, cv.width / 2, cv.height / 2);
    $("btn-rot-left").onclick = () => { if (rend.rotate) rend.rotate(-1); };
    $("btn-rot-right").onclick = () => { if (rend.rotate) rend.rotate(1); };

    // minimap click
    $("minimap").addEventListener("mousedown", (e) => {
      const rect = e.target.getBoundingClientRect();
      const c = Math.floor((e.clientX - rect.left) / rect.width * game.map.w);
      const r = Math.floor((e.clientY - rect.top) / rect.height * game.map.h);
      rend.centerOn(game, c, r);
    });

    window.addEventListener("keydown", (e) => {
      if ($("start-screen").style.display !== "none") return;
      // don't hijack keys while typing in a text field (search, net codes)
      const tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea") {
        if (e.key === "Escape") e.target.blur();
        return;
      }
      if (e.key === "Enter") { endTurn(); }
      else if (e.key === "." || e.key === "n") cycleNextUnit();
      else if (e.key === "f" && rend.selected) { rend.selected.fortified = true; rend.selected.moves = 0; cycleNextUnit(); refreshAll(); }
      else if (e.key === "Escape") {
        $("tech-modal").style.display = "none";
        $("diplo-modal").style.display = "none";
        $("religion-modal").style.display = "none";
        $("founding-modal").style.display = "none";
        $("spy-modal").style.display = "none";
        $("policy-modal").style.display = "none";
        $("pedia-modal").style.display = "none";
        $("congress-modal").style.display = "none";
        $("campaign-modal").style.display = "none";
        $("progress-modal").style.display = "none";
        $("settings-modal").style.display = "none";
        $("log-modal").style.display = "none";
        $("menu-modal").style.display = "none";
        closeCity();
        selectUnit(null);
      } else if (e.key === "t") showTechScreen();
      else if (e.key === "p") showPolicyScreen();
      else if (e.key === "?" || e.key === "/") { e.preventDefault(); showPediaScreen(); }
      else if (e.key === "d") showDiploScreen();
      else if (e.key === "r") showReligionScreen();
      else if (e.key === "e") showSpyScreen();
      else if (e.key === "v") showVictoryProgress();
      else if ((e.key === "q" || e.key === "w") && rend.rotate) rend.rotate(e.key === "q" ? -1 : 1);
    });

    $("btn-endturn").onclick = endTurn;
    $("btn-tech").onclick = showTechScreen;
    $("stat-sci").onclick = showTechScreen;
    $("btn-diplo").onclick = showDiploScreen;
    $("btn-religion").onclick = showReligionScreen;
    $("stat-faith").onclick = showReligionScreen;
    $("stat-culture").onclick = showPolicyScreen;
    $("stat-score").onclick = showVictoryProgress;
    $("btn-spies").onclick = showSpyScreen;
    $("btn-pedia").onclick = () => showPediaScreen();
    $("pedia-search").addEventListener("input", renderPedia);
    $("advisor-close").onclick = hideAdvisor;
    $("advisor-off-chk").onchange = (e) => {
      localStorage.setItem("balkan-civ-tips-off", e.target.checked ? "1" : "0");
      if (e.target.checked) hideAdvisor();
    };
    $("notif-list").onclick = showLogModal;
    $("btn-mute").onclick = () => {
      $("btn-mute").textContent = SFX.toggleMute() ? "🔇" : "🔊";
    };
    $("btn-music").onclick = () => {
      $("btn-music").textContent = SFX.toggleMusic() ? "🎵" : "♪";
    };
    $("btn-menu").onclick = showMenuModal;
    $("file-import").addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          game = Game.deserialize(reader.result);
          NET.reset();
          $("menu-modal").style.display = "none";
          startPlaying();
        } catch (err) {
          alert("That file is not a valid Balkan Civilizations save.");
        }
        e.target.value = "";
      };
      reader.readAsText(file);
    });
    document.querySelectorAll(".modal").forEach(m => {
      m.addEventListener("mousedown", (e) => { if (e.target === m) m.style.display = "none"; });
    });
  }

  function updateHover(e) {
    if (!game || $("start-screen").style.display !== "none") return;
    const cv = rend.canvas;
    const rect = cv.getBoundingClientRect();
    if (e.clientX < rect.left || e.clientY < rect.top || e.clientY > rect.bottom) {
      if (rend.hoverTile) { rend.hoverTile = null; rend.previewPath = null; rend.dirty = true; }
      return;
    }
    const [c, r] = rend.screenToHex(e.clientX - rect.left, e.clientY - rect.top);
    const prev = rend.hoverTile;
    if (prev && prev[0] === c && prev[1] === r) return;
    rend.hoverTile = game.tile(c, r) ? [c, r] : null;
    rend.previewPath = null;
    const sel = rend.selected;
    if (sel && sel.owner === game.viewer && rend.hoverTile && !(sel.c === c && sel.r === r)) {
      const t = game.tile(c, r);
      if (game.players[game.viewer].visible[game.map.idx(c, r)] && game.unitPassable(sel, t)) {
        rend.previewPath = game.findPath(sel, c, r);
      }
    }
    rend.dirty = true;
  }

  function updateTooltip(e) {
    const tip = $("tooltip");
    if (!game || $("start-screen").style.display !== "none") { tip.style.display = "none"; return; }
    const cv = rend.canvas;
    const rect = cv.getBoundingClientRect();
    if (e.clientX < rect.left || e.clientY < rect.top || e.clientY > rect.bottom) { tip.style.display = "none"; return; }
    const [c, r] = rend.screenToHex(e.clientX - rect.left, e.clientY - rect.top);
    const t = game.tile(c, r);
    if (!t || !game.players[game.viewer].visible[game.map.idx(c, r)]) { tip.style.display = "none"; return; }
    const y = game.tileYield(t);
    let html = `<b>${TERRAIN[t.terrain].name}</b>${t.feature ? " / " + FEATURE[t.feature].name : ""}`;
    if (t.ruin) html += ` · 🏺 Ancient Ruins`;
    if (game.campAt && game.campAt(c, r)) html += ` · 🏕️ Barbarian Camp`;
    // combat forecast when hovering a legal target of the selected unit
    const sel0 = rend.selected;
    if (sel0 && sel0.owner === game.viewer && rend.attackable.some(([ac, ar]) => ac === c && ar === r)) {
      const f = game.predictAttack(sel0, c, r);
      if (f) {
        const kills = f.out[0] >= f.targetHp;
        html += `<br><b class="war">⚔ vs ${f.target}</b> (${f.targetHp} HP)<br>` +
          `You deal <b>${f.out[0]}–${f.out[1]}</b>${kills ? " — <b class='alert'>lethal!</b>" : ""}` +
          (f.back ? `<br>You take <b>${f.back[0]}–${f.back[1]}</b>` : "<br><span class='dim'>no counterattack</span>");
      }
    } else if (sel0 && warTargetOwner(sel0, c, r) >= 0) {
      html += `<br><b class="war">⚔ Click to declare war on ${game.players[warTargetOwner(sel0, c, r)].civ.name}</b>`;
    }
    if (t.resource) html += ` · ${RESOURCE[t.resource].icon} ${RESOURCE[t.resource].name}${RESOURCE[t.resource].luxury ? " (luxury)" : ""}`;
    if (t.improvement) html += ` · ${IMPROVEMENT[t.improvement].icon} ${IMPROVEMENT[t.improvement].name}`;
    html += `<br><span class="dim">🍞${y.food} ⚙️${y.prod} 💰${y.gold}</span>`;
    if (t.owner !== -1) html += `<br><span style="color:${CIVS[game.players[t.owner].civId].color}">${CIVS[game.players[t.owner].civId].name} territory</span>`;
    const visLevel = game.players[game.viewer].visible[game.map.idx(c, r)];
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
    const oldW = cv.width || window.innerWidth;
    const oldH = cv.height || window.innerHeight;
    const hudHeight = Math.round($("topbar").getBoundingClientRect().height) || 48;
    const newW = window.innerWidth;
    const newH = Math.max(1, window.innerHeight - hudHeight);
    if (rend && game) {
      rend.cam.x += (oldW - newW) / 2;
      rend.cam.y += (oldH - newH) / 2;
    }
    cv.style.top = hudHeight + "px";
    cv.width = newW;
    cv.height = newH;
    if (rend) rend.dirty = true;
  }

  function init() {
    NET.on("peers", () => refreshHostStatus());
    NET.on("start", (state) => {
      game = Game.deserialize(state);
      game._viewer = NET.myIndex;
      $("net-modal").style.display = "none";
      startPlaying();
      netAfterLoad();
    });
    NET.on("state", (state) => {
      const cam = rend ? { ...rend.cam } : null;
      game = Game.deserialize(state);
      game._viewer = NET.myIndex;
      if (cam) rend.cam = cam;
      netAfterLoad();
    });
    NET.on("drop", () => {
      const b = $("net-banner");
      b.style.display = "block";
      b.innerHTML = `🌐 <b class="war">A player disconnected.</b> The game is auto-saved locally.`;
    });
    const want3d = (localStorage.getItem("balkan-civ-gfx") || "3d") === "3d";
    rend = (want3d && typeof Renderer3D !== "undefined" && Renderer3D.supported())
      ? new Renderer3D($("map"), $("minimap"))
      : new Renderer($("map"), $("minimap"));
    window.addEventListener("resize", resize);
    resize();
    bindInput();
    showStartScreen();
    // resume seamlessly after a graphics-mode switch reloaded the page
    if (localStorage.getItem("balkan-civ-resume") === "1") {
      localStorage.removeItem("balkan-civ-resume");
      const saved = localStorage.getItem("balkan-civ-save");
      if (saved) {
        try { game = Game.deserialize(saved); startPlaying(); } catch (e) { console.error(e); }
      }
    }
    (function loop() {
      if (game && $("start-screen").style.display === "none" &&
          $("editor-screen").style.display !== "flex" &&
          (rend.dirty || game.effects.length || game.anims.length ||
           (game.strikes && game.strikes.length) ||
           // 3D water swell: a slow ambient tick when otherwise idle
           (rend.three && !rend.reduceMotion && Date.now() - (rend._lastDraw || 0) > 140))) {
        rend.draw(game);
      }
      requestAnimationFrame(loop);
    })();
  }

  return { init, setProduction, buyItem, closeCity, pickTech, diploAction, newGame,
    showFoundingModal, confirmFounding, buyMissionary, gift, assignSpy, beginHotseatTurn,
    hostAddSlot, hostConnect, hostStartOnline, joinCreateReply, unqueue,
    saveSlot, loadSlot, exportSave, toMainMenu, toggleGraphics, showSettings: showSettingsModal,
    diploTrade, diploGift, diploPact, adoptPolicy, congressVote, congressAbstain,
    playChapter, resetCampaign, openCampaign, answerPeace, cancelProduction, buildNow,
    declareWarAndAttack,
    get game() { return game; }, get renderer() { return rend; } };
})();
