// ============================================================
// UI: DOM panels, input, screens
// ============================================================
"use strict";

const UI = (() => {
  let game = null, rend = null;
  let chosenCiv = CIV_IDS[0];
  let chosenLeader = 0;
  let pendingAttack = null, combatPanelTimer = null;
  let empireTab = "cities", empireCitySort = "capital", empireUnitSort = "readiness";
  const $ = (id) => document.getElementById(id);
  const SETUP_KEY = "balkan-civ-setup-v1";
  const SETUP_SELECTS = {
    humans: "sel-humans",
    opponents: "sel-opponents",
    mapSize: "sel-mapsize",
    mapType: "sel-maptype",
    speed: "sel-speed",
    difficulty: "sel-difficulty",
  };

  function randomSeed() {
    const values = new Uint32Array(1);
    if (globalThis.crypto && typeof globalThis.crypto.getRandomValues === "function") {
      globalThis.crypto.getRandomValues(values);
      return values[0];
    }
    return Math.floor(Math.random() * 0x100000000) >>> 0;
  }

  function validSeedText(value) {
    const raw = String(value ?? "").trim();
    return raw === "" || (/^\d{1,10}$/.test(raw) && Number(raw) <= 0xffffffff);
  }

  function readSeedInput(report = false) {
    const input = $("inp-seed");
    const raw = input.value.trim();
    const valid = validSeedText(raw);
    input.setCustomValidity(valid ? "" : "Enter a whole number from 0 to 4294967295.");
    if (!valid) {
      if (report) input.reportValidity();
      return { ok: false, seed: null };
    }
    return { ok: true, seed: raw === "" ? randomSeed() : Number(raw) >>> 0 };
  }

  function readStoredSetup() {
    try {
      const setup = JSON.parse(localStorage.getItem(SETUP_KEY) || "null");
      return setup && typeof setup === "object" ? setup : null;
    } catch (e) { return null; }
  }

  function restoreSetup() {
    const setup = readStoredSetup();
    if (!setup) return;
    if (CIVS[setup.civ]) {
      chosenCiv = setup.civ;
      const leader = Number(setup.leader);
      chosenLeader = Number.isInteger(leader) && leader >= 0 && leader < CIVS[chosenCiv].leaders.length
        ? leader : 0;
    }
    for (const [key, id] of Object.entries(SETUP_SELECTS)) {
      const select = $(id);
      const value = setup[key];
      const option = [...select.options].find(o => o.value === value && !o.disabled);
      if (option && (key !== "mapType" || value !== "custom" || localStorage.getItem("balkan-civ-custommap"))) {
        select.value = value;
      }
    }
    if (typeof setup.barbarians === "boolean") $("chk-barbs").checked = setup.barbarians;
    if (validSeedText(setup.seed)) $("inp-seed").value = String(setup.seed ?? "").trim();
  }

  function persistSetup() {
    const seed = $("inp-seed").value.trim();
    if (!validSeedText(seed)) return;
    const setup = { civ: chosenCiv, leader: chosenLeader, barbarians: $("chk-barbs").checked, seed };
    for (const [key, id] of Object.entries(SETUP_SELECTS)) setup[key] = $(id).value;
    try { localStorage.setItem(SETUP_KEY, JSON.stringify(setup)); } catch (e) { /* storage unavailable */ }
  }

  function bindSetupControls() {
    for (const id of Object.values(SETUP_SELECTS)) $(id).onchange = persistSetup;
    $("chk-barbs").onchange = persistSetup;
    $("inp-seed").oninput = () => {
      $("inp-seed").setCustomValidity("");
      persistSetup();
    };
    $("btn-random-seed").onclick = () => {
      $("inp-seed").value = String(randomSeed());
      $("inp-seed").setCustomValidity("");
      persistSetup();
    };
  }

  function shuffledWithSeed(values, seed) {
    const result = [...values];
    const rng = mulberry32((seed ^ 0xa5a5a5a5) >>> 0);
    for (let i = result.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      [result[i], result[j]] = [result[j], result[i]];
    }
    return result;
  }

  function unitArtCanvas(unitKey, className = "unit-art-inline") {
    const def = UNITS[unitKey];
    if (!def) return "";
    const pixels = className.includes("pedia-unit-art") ? 128 :
      className.includes("unit-art-combat") ? 76 : 48;
    return `<canvas class="${className}" width="${pixels}" height="${pixels}" data-unit-art="${unitKey}"
      role="img" aria-label="${def.name} silhouette"></canvas>`;
  }

  function paintUnitArt(root = document) {
    root.querySelectorAll("canvas[data-unit-art]").forEach(canvas => {
      const def = UNITS[canvas.dataset.unitArt];
      if (!def) return;
      const ctx = canvas.getContext("2d");
      const size = Math.min(canvas.width, canvas.height);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (canvas.classList.contains("pedia-unit-art")) {
        const ring = def.uu ? CIVS[def.uu].color : def.naval ? "#4fa3c7" : "#c9a648";
        ctx.fillStyle = "#172235";
        ctx.beginPath(); ctx.arc(size / 2, size / 2, size * 0.43, 0, Math.PI * 2); ctx.fill();
        ctx.strokeStyle = ring; ctx.lineWidth = size * 0.04; ctx.stroke();
      }
      const scale = canvas.classList.contains("pedia-unit-art") ? 0.67 : 0.74;
      UNIT_ART.draw(ctx, def, canvas.width / 2, canvas.height / 2, size * scale, "#f4ead3");
    });
  }

  function productionLabel(kind, key, def) {
    return kind === "unit"
      ? `<span class="unit-label">${unitArtCanvas(key)}<span>${def.name}</span></span>`
      : `${def.icon} ${def.name}`;
  }

  // In a network game only the client whose turn it is may act.
  function myTurn() {
    if (!NET.active) return true;
    return !!game && NET.connected && !NET.syncing && game.activeHuman === NET.myIndex;
  }

  // ---------------- start screen ----------------
  function showStartScreen() {
    campaignChapter = null; // leaving to the menu ends any campaign context
    restoreSetup();
    const wrap = $("civ-cards");
    wrap.innerHTML = "";
    const repaintAll = () => wrap.querySelectorAll(".civ-card").forEach(c => c._paint && c._paint());

    for (const id of CIV_IDS) {
      const civ = CIVS[id];
      const uu = UNITS[civ.uu];
      const card = document.createElement("div");
      card.className = "civ-card";
      card.dataset.civ = id;
      card.setAttribute("role", "group");
      card.setAttribute("aria-labelledby", `civ-${id.toLowerCase()}-name`);
      const selectCard = (leaderIdx = chosenCiv === id ? chosenLeader : 0) => {
        chosenCiv = id;
        chosenLeader = leaderIdx;
        repaintAll();
        refreshStartSummary();
        persistSetup();
      };
      const renderLeaders = (sel) => civ.leaders.map((L, li) =>
        `<button class="leader-chip${id === chosenCiv && li === sel ? " sel" : ""}" data-li="${li}"
          title="${L.trait}: ${L.traitDesc}">${L.leader}</button>`).join("");
      const traitLine = (li) => `<div class="trait"><b>${civ.leaders[li].trait}</b><br>${civ.leaders[li].traitDesc}</div>`;
      const paint = () => {
        const selected = id === chosenCiv;
        card.classList.toggle("sel", selected);
        card.setAttribute("aria-current", selected ? "true" : "false");
        card.querySelector(".leaders").innerHTML = renderLeaders(id === chosenCiv ? chosenLeader : 0);
        card.querySelector(".trait-slot").innerHTML = traitLine(id === chosenCiv ? chosenLeader : 0);
        const selectButton = card.querySelector(".civ-select");
        selectButton.setAttribute("aria-pressed", selected ? "true" : "false");
        selectButton.textContent = selected ? "✓" : "○";
        bindChips();
      };
      const bindChips = () => card.querySelectorAll(".leader-chip").forEach(b => b.onclick = (e) => {
        e.stopPropagation();
        selectCard(parseInt(b.dataset.li, 10));
      });
      card.innerHTML = `
        <div class="civ-flag" style="background:${civ.color};border-color:${civ.color2}" aria-hidden="true"></div>
        <div class="civ-card-title"><h3 id="civ-${id.toLowerCase()}-name">${civ.name}</h3>
          <button class="civ-select" aria-pressed="${id === chosenCiv}" aria-label="Select ${civ.name}"
            title="Select ${civ.name}">${id === chosenCiv ? "✓" : "○"}</button></div>
        <div class="leaders">${renderLeaders(id === chosenCiv ? chosenLeader : 0)}</div>
        <div class="trait-slot">${traitLine(id === chosenCiv ? chosenLeader : 0)}</div>
        <div class="uu">${unitArtCanvas(civ.uu)}<span><b>${uu.name}</b> — ${uu.blurb}</span></div>`;
      card.querySelector(".civ-select").onclick = (e) => {
        e.stopPropagation();
        selectCard();
      };
      card.onclick = (e) => { if (!e.target.closest("button")) selectCard(); };
      card._paint = paint;
      if (id === chosenCiv) card.classList.add("sel");
      bindChips();
      paintUnitArt(card);
      wrap.appendChild(card);
    }
    refreshStartSummary();
    buildScenarioCards();
    $("opt-custom").disabled = !localStorage.getItem("balkan-civ-custommap");
    bindSetupControls();
    $("btn-random-realm").onclick = () => {
      const current = Math.max(0, CIV_IDS.indexOf(chosenCiv));
      const offset = 1 + randomSeed() % (CIV_IDS.length - 1);
      chosenCiv = CIV_IDS[(current + offset) % CIV_IDS.length];
      chosenLeader = randomSeed() % CIVS[chosenCiv].leaders.length;
      repaintAll();
      refreshStartSummary();
      persistSetup();
      wrap.querySelector(`[data-civ="${chosenCiv}"]`)?.scrollIntoView({ block: "nearest", inline: "center" });
    };
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
      const seedInfo = readSeedInput(true);
      if (!seedInfo.ok) return;
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
      persistSetup();
      game = new Game({ playerCiv: chosenCiv, playerLeader: chosenLeader,
        numOpponents: numOpp, mapW: dims[0], mapH: dims[1],
        mapType, customMap, numHumans, difficulty: $("sel-difficulty").value,
        noBarbs: !$("chk-barbs").checked, speed: $("sel-speed").value,
        seed: seedInfo.seed });
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
      const leaderIdx = sc.leaders?.[sc.playerCiv] ?? 0;
      const leader = CIVS[sc.playerCiv].leaders[leaderIdx] || CIVS[sc.playerCiv].leaders[0];
      const v = sc.victory;
      let objective = "Special objective";
      if (v.type === "capture") objective = "Capture the rival capital";
      else if (v.type === "survive") objective = "Hold your capital";
      else if (v.type === "capitals") objective = `Control ${v.count} capitals`;
      else if (v.type === "research") objective = "Master every technology";
      else if (v.type === "kills") objective = `Defeat ${v.count} ${CIVS[v.target].adj} units`;
      else if (v.type === "resistance") objective = `Hold the capital and defeat ${v.count} ${CIVS[v.target].adj} units`;
      else if (v.type === "cities") objective = `Control ${v.count} cities`;
      card.innerHTML = `<div class="scenario-card-head"><h3>${sc.icon} ${sc.name}</h3>
          <span class="scenario-era">${ERAS[sc.techEra ?? 0]}</span></div>
        <div class="year">${sc.year} · <b style="color:${CIVS[sc.playerCiv].color}">${CIVS[sc.playerCiv].name}</b>
          under ${leader.leader} · ${sc.victory.turns} turns</div>
        <div class="scenario-objective">${objective}</div>
        <p>${sc.blurb}</p>`;
      card.onclick = () => launchScenario(key, null);
      card.setAttribute("role", "button");
      card.setAttribute("tabindex", "0");
      card.setAttribute("aria-label", `Play ${sc.name}, ${objective}`);
      card.onkeydown = (e) => {
        if (e.key === "Enter" || e.key === " ") { e.preventDefault(); launchScenario(key, null); }
      };
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
      const leaderIdx = sc.leaders?.[sc.playerCiv] ?? 0;
      const leader = CIVS[sc.playerCiv].leaders[leaderIdx] || CIVS[sc.playerCiv].leaders[0];
      const status = complete ? `<span style="color:#2ecc71">✓ complete</span>`
        : unlocked ? `<span class="alert">available</span>` : `🔒 locked`;
      html += `<div class="campaign-chapter ${unlocked ? "" : "locked"}">
        <div><b>${i + 1}. ${sc.icon} ${sc.name}</b> <span class="dim">— ${sc.year}, ${CIVS[sc.playerCiv].name}</span><br>
          <span class="dim">${leader.leader} · ${ERAS[sc.techEra ?? 0]} · ${status} · ${sc.victory.turns} turns</span></div>
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
    if (!NET.connected) {
      b.innerHTML = `🌐 <b class="war">Connection lost.</b> Turns are paused; a local recovery save is ready.`;
    } else if (NET.syncing) {
      b.innerHTML = `🌐 <b class="alert">Synchronizing turn…</b>`;
    } else if (myTurn()) {
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
      showTurnPrompts();
    }
  }

  function compatibleNetworkSnapshot(snapshot) {
    if (!game || !snapshot || !Array.isArray(snapshot.players) || !snapshot.map) return false;
    return snapshot.seed === game.seed && snapshot.humans === game.humans &&
      (snapshot.scenario || null) === game.scenario && (snapshot.speed || "standard") === game.speed &&
      snapshot.players.length === game.players.length && snapshot.map.w === game.map.w && snapshot.map.h === game.map.h &&
      snapshot.players.every((p, i) => p.civId === game.players[i].civId && p.isHuman === game.players[i].isHuman);
  }

  function applyNetworkState(state, meta = {}) {
    if (NET.isHost && meta.remote && meta.fromIndex !== game.activeHuman) return false;
    let snapshot;
    try { snapshot = JSON.parse(state); } catch (e) { return false; }
    if (!compatibleNetworkSnapshot(snapshot)) return false;
    if (NET.isHost && meta.remote) {
      if (snapshot.turn < game.turn || snapshot.turn > game.turn + 1) return false;
      if (snapshot.activeHuman < 0 || snapshot.activeHuman >= game.humans) return false;
    }
    const allocatorRecovery = game.serialize();
    let next;
    try { next = Game.deserialize(state); } catch (e) {
      try { Game.deserialize(allocatorRecovery); } catch (ignored) { /* current state was already valid */ }
      return false;
    }
    const cam = rend ? { ...rend.cam } : null;
    game = next;
    game._viewer = NET.myIndex;
    if (cam) rend.cam = cam;
    netAfterLoad();
    return true;
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
      <button onclick="UI.cancelNetworkLobby()">Cancel</button>
      <span class="dim" id="net-status"></span>`;
    hostAddSlot();
  }

  async function hostAddSlot() {
    if (NET.peers.length >= 3) return;
    let entry;
    try { entry = await NET.hostInvite(); } catch (e) {
      $("net-status").innerHTML = `<span class="war">Could not create an invite. Check browser WebRTC access and try again.</span>`;
      return;
    }
    const i = NET.peers.length - 1;
    const div = document.createElement("div");
    div.className = "net-slot";
    div.innerHTML = `<b>Friend ${i + 1}</b> — <span id="net-st-${i}">waiting for reply…</span><br>
      <label class="dim" for="net-invite-${i}">Send this invite code:</label>
      <textarea class="net-code" id="net-invite-${i}" readonly onclick="this.select()">${entry.inviteCode}</textarea>
      <label class="dim" for="net-reply-${i}">Paste their reply code:</label>
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
      if (!el) return;
      if (p.open && p.compatible) el.innerHTML = `<b style="color:#2ecc71">connected</b>` +
        (p.civ ? ` — wants ${CIVS[p.civ] ? CIVS[p.civ].name : "random"}` : "");
      else if (p.open && p.compatible === false) el.innerHTML = `<b class="war">version mismatch — both players must refresh</b>`;
      else if (p.open) el.textContent = "verifying game version…";
      else if (p.connectionState === "failed" || p.connectionState === "closed")
        el.innerHTML = `<b class="war">connection failed — create a new invite</b>`;
    });
    const btn = $("net-start-btn");
    if (btn) btn.disabled = !NET.peers.some(p => p.open && p.compatible);
  }

  function hostStartOnline() {
    const ready = NET.peers.filter(p => p.open && p.compatible);
    if (!ready.length) return;
    const seedInfo = readSeedInput(false);
    if (!seedInfo.ok) {
      $("net-status").innerHTML = `<span class="war">Enter a map seed from 0 to 4294967295, or leave it blank.</span>`;
      return;
    }
    const taken = new Set([chosenCiv]);
    for (const p of ready) {
      let c = (p.civ && CIVS[p.civ] && !taken.has(p.civ)) ? p.civ
        : CIV_IDS.find(x => !taken.has(x));
      taken.add(c);
      p.assignedCiv = c;
    }
    const aiCount = parseInt($("sel-opponents").value, 10);
    const rest = shuffledWithSeed(CIV_IDS.filter(c => !taken.has(c)), seedInfo.seed);
    const dims = { small: [36, 28], standard: [44, 34], large: [54, 42] }[$("sel-mapsize").value];
    const mapType = $("sel-maptype").value === "custom" ? "peninsula" : $("sel-maptype").value;
    game = new Game({ playerCiv: chosenCiv,
      fixedOpponents: [...ready.map(p => p.assignedCiv), ...rest.slice(0, aiCount)],
      numOpponents: ready.length + Math.min(aiCount, rest.length),
      numHumans: 1 + ready.length,
      mapW: dims[0], mapH: dims[1], mapType, difficulty: $("sel-difficulty").value,
      noBarbs: !$("chk-barbs").checked, speed: $("sel-speed").value,
      seed: seedInfo.seed });
    persistSetup();
    game._viewer = 0;
    if (!NET.hostStart(game, ready.length)) {
      game = null;
      $("net-status").innerHTML = `<span class="war">The connected roster changed. Verify each friend and start again.</span>`;
      refreshHostStatus();
      return;
    }
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
      <label class="dim" for="net-invite">Invite code</label>
      <textarea class="net-code" id="net-invite"></textarea>
      <button onclick="UI.joinCreateReply()">🔗 Create Reply</button>
      <button onclick="UI.cancelNetworkLobby()">Cancel</button>
      <div id="net-join-out"></div>`;
  }

  function cancelNetworkLobby() {
    NET.reset();
    $("net-modal").style.display = "none";
  }

  async function joinCreateReply() {
    try {
      const reply = await NET.joinWithInvite($("net-invite").value, chosenCiv);
      $("net-join-out").innerHTML = `<label class="dim" for="net-join-reply">Send this reply code back to the host,
        then wait — the game starts automatically:</label>
        <textarea class="net-code" id="net-join-reply" readonly onclick="this.select()">${reply}</textarea>
        <span class="alert">⏳ Waiting for the host to start…</span>`;
    } catch (e) {
      NET.reset();
      $("net-join-out").innerHTML = `<span class="war">Bad invite code — paste the whole thing.</span>`;
    }
  }

  function mapFocusPoint() {
    const canvas = $("map");
    const fallback = { x: canvas.width / 2, y: canvas.height / 2 };
    if (window.innerWidth > 700) return fallback;
    const mapRect = canvas.getBoundingClientRect();
    let top = 0, bottom = canvas.height;
    const occluders = [$("attention"), $("unit-panel"), $("city-panel"), document.querySelector(".command-bar")];
    for (const el of occluders) {
      if (!el || getComputedStyle(el).display === "none") continue;
      const rect = el.getBoundingClientRect();
      if (!rect.height || rect.width < mapRect.width * 0.72 || rect.bottom <= mapRect.top || rect.top >= mapRect.bottom) continue;
      const localTop = Math.max(0, rect.top - mapRect.top);
      const localBottom = Math.min(canvas.height, rect.bottom - mapRect.top);
      if (localTop < canvas.height * 0.35) top = Math.max(top, localBottom + 8);
      if (localBottom > canvas.height * 0.65) bottom = Math.min(bottom, localTop - 8);
    }
    if (bottom - top < 140) return fallback;
    return { x: canvas.width / 2, y: (top + bottom) / 2 };
  }

  function centerMapOn(target) {
    if (!target || !rend || !game) return;
    rend.centerOn(game, target.c, target.r, mapFocusPoint());
  }

  function centerMapHome() {
    const target = rend.selected || rend.selectedCity ||
      game.cities.find(city => city.owner === game.viewer && city.isCapital) ||
      game.cities.find(city => city.owner === game.viewer) ||
      game.units.find(unit => unit.owner === game.viewer);
    centerMapOn(target);
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
    applyMapPreferences();
    const rotateDisplay = rend.three ? "block" : "none";
    $("btn-rot-left").style.display = rotateDisplay;
    $("btn-rot-right").style.display = rotateDisplay;
    $("map-controls").querySelector(".control-rule").style.display = rotateDisplay;
    lastEraShown = null; // re-baseline era banners for this game
    const firstUnit = game.units.find(u => u.owner === game.viewer);
    selectUnit(firstUnit || null);
    if (firstUnit) {
      rend.cam.zoom = rend.three ? (window.innerWidth <= 700 ? 1.42 : 1.52)
        : (window.innerWidth <= 700 ? 1.08 : 1.12);
    }
    refreshAll();
    if (firstUnit) centerMapOn(firstUnit);
    showTurnPrompts();
  }

  // ---------------- selection ----------------
  function selectUnit(u) {
    hideCombatPreview();
    if (u && u !== rend.selected) SFX.play("select");
    rend.previewPath = null;
    rend.selected = u;
    rend.selectedCity = null;
    refreshSelectionOverlays();
    rend.dirty = true;
    refreshUnitPanel();
    $("city-panel").style.display = "none";
  }

  function computeAttackable(u) {
    if (u.isCivilian || u.attacked || u.moves <= 0 ||
        (game.isEmbarked(u) && !u.promos.includes("AMPHIBIOUS"))) return [];
    const p = game.players[game.viewer];
    const range = u.isRanged ? u.def.range : 1;
    const out = [];
    for (const [c, r] of HEX.ring(u.c, u.r, range)) {
      const t = game.tile(c, r);
      if (!t || !p.visible[game.map.idx(c, r)]) continue;
      if (game.isEmbarked(u) && !game.canAttackFromEmbarked(u, t)) continue;
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

  function surveyedSitePotential(unit, c, r) {
    const vis = game.players[game.viewer].visible;
    const tiles = HEX.ring(c, r, 2).map(([tc, tr]) => game.tile(tc, tr)).filter(Boolean);
    const surveyed = tiles.filter(t => vis[game.map.idx(t.c, t.r)] > 0);
    if (!surveyed.length) return { score: 0, coverage: 0 };
    let value = 0, coastal = false;
    for (const t of surveyed) {
      if (t.owner !== -1 && t.owner !== unit.owner && game.players[t.owner]?.alive) continue;
      const y = game.tileYield(t);
      value += y.food * 1.4 + y.prod + y.gold * 0.6 + (t.resource ? 2 : 0);
      if (t.terrain === "COAST") coastal = true;
    }
    value *= tiles.length / surveyed.length;
    if (coastal) value += 3;
    if (game.tile(c, r).terrain === "HILLS") value += 2;
    if (game.tile(c, r).river) value += RIVERS.cityFood * 1.4;
    return { score: Math.round(value), coverage: Math.round(surveyed.length / tiles.length * 100) };
  }

  function computeSettlementSites(unit) {
    if (!unit || unit.type !== "SETTLER" || unit.owner !== game.viewer) return [];
    const vis = game.players[game.viewer].visible;
    const candidates = [[unit.c, unit.r], ...rend.reachable];
    const seen = new Set(), sites = [];
    for (const [c, r] of candidates) {
      const key = `${c},${r}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const t = game.tile(c, r);
      if (!t || vis[game.map.idx(c, r)] !== 2) continue;
      if (!game.citySiteStatus(c, r, unit.owner).ok) continue;
      const survey = surveyedSitePotential(unit, c, r);
      let tier = survey.score >= 68 ? "excellent" : survey.score >= 56 ? "good" : "marginal";
      if (survey.coverage < 55 && tier === "excellent") tier = "good";
      if (survey.coverage < 35) tier = "marginal";
      const label = tier === "excellent" ? "Excellent" : tier === "good" ? "Promising" : "Marginal";
      const path = c === unit.c && r === unit.r ? [] : game.findPath(unit, c, r);
      const moveCost = path ? path.reduce((sum, [pc, pr]) => sum + game.moveCost(unit, pc, pr), 0) : Infinity;
      sites.push({ c, r, score: survey.score, coverage: survey.coverage, tier, label,
        canFoundThisTurn: myTurn() && unit.moves > moveCost });
    }
    return sites;
  }

  function refreshSelectionOverlays() {
    const unit = rend.selected;
    if (!unit) {
      rend.reachable = []; rend.controlled = []; rend.attackable = []; rend.settlementSites = [];
      return;
    }
    rend.reachable = game.reachableTiles(unit);
    rend.controlled = rend.reachable.filter(([c, r]) =>
      game.knownEnemyZoneOfControl(unit, c, r).length);
    rend.attackable = computeAttackable(unit);
    rend.settlementSites = computeSettlementSites(unit);
  }

  // Is the clicked tile a legal *war* target — an at-peace rival's unit or city
  // in this unit's strike range? Returns the owner index, or -1 if none.
  // Lets a player start a war the intuitive way: by attacking.
  function warTargetOwner(u, c, r) {
    if (!u || u.owner !== game.viewer || u.isCivilian || u.attacked || u.moves <= 0 ||
        (game.isEmbarked(u) && !u.promos.includes("AMPHIBIOUS"))) return -1;
    const p = game.players[game.viewer];
    const range = u.isRanged ? u.def.range : 1;
    if (HEX.distance(u.c, u.r, c, r) > range) return -1;
    const t = game.tile(c, r);
    if (!t || !p.visible[game.map.idx(c, r)]) return -1;
    if (game.isEmbarked(u) && !game.canAttackFromEmbarked(u, t)) return -1;
    if (!u.isRanged && !u.def.naval && game.isWater(t)) return -1;
    if (!u.isRanged && u.def.naval && !game.isWater(t) && !t.city) return -1;
    const cu = game.combatUnitAt(c, r);
    const civ = game.civilianAt(c, r);
    const owner = cu ? cu.owner : (t.city ? t.city.owner : (civ ? civ.owner : -1));
    if (owner < 0 || owner === game.viewer) return -1;
    const op = game.players[owner];
    // barbarians are already at war; skip our own pact partners and unmet powers
    if (!op || op.isBarb || !game.canDeclareWar(game.viewer, owner)) return -1;
    return owner;
  }

  function showWarConfirm(unit, c, r) {
    const owner = warTargetOwner(unit, c, r);
    if (owner < 0) return false;
    const civ = game.players[owner].civ;
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
    if (!game.declareWar(game.viewer, owner)) return;
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

  function combatNumber(value) {
    const rounded = Math.round(value * 10) / 10;
    return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
  }

  function combatFactorValue(factor) {
    if (factor.operation === "multiply") return `×${Math.round(factor.value * 100)}%`;
    if (factor.operation === "flat") return `${factor.value >= 0 ? "+" : "−"}${combatNumber(Math.abs(factor.value))}`;
    return `${factor.value >= 0 ? "+" : "−"}${Math.round(Math.abs(factor.value) * 100)}%`;
  }

  function combatStrengthLedger(label, breakdown) {
    const rows = breakdown.factors.map(factor => `
      <div class="combat-factor${factor.value < 0 || (factor.operation === "multiply" && factor.value < 1) ? " penalty" : ""}">
        <span>${factor.label}</span><b>${combatFactorValue(factor)}</b>
      </div>`).join("");
    return `<section class="combat-ledger">
      <header><span>${label}</span><strong>${combatNumber(breakdown.strength)}</strong></header>
      <div class="combat-factor base"><span>Base strength</span><b>${combatNumber(breakdown.base)}</b></div>
      ${rows || `<div class="combat-factor quiet"><span>No active modifiers</span></div>`}
    </section>`;
  }

  function combatBreakdown(forecast) {
    const expanded = window.innerWidth >= 700 ? " open" : "";
    return `<details class="combat-breakdown"${expanded}>
      <summary><span>Effective strength</span><b>${combatNumber(forecast.attackerBreakdown.strength)} <i>vs</i> ${combatNumber(forecast.defenderBreakdown.strength)}</b></summary>
      <div class="combat-ledgers">
        ${combatStrengthLedger("Attacker", forecast.attackerBreakdown)}
        ${combatStrengthLedger("Defender", forecast.defenderBreakdown)}
      </div>
    </details>`;
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
          ${unitArtCanvas(unit.type, "combat-icon unit-art-combat")}
          <span><b>${unit.def.name}</b><small>${game.players[unit.owner].civ.name} · ${unit.hp} HP</small>${hpMeter(unit.hp, 100, game.players[unit.owner].civ.color)}</span>
        </div>
        <span class="combat-vs">VS</span>
        <div class="combatant target">
          ${hitsCity ? `<span class="combat-icon">🏙️</span>` : unitArtCanvas(defender.type, "combat-icon unit-art-combat")}
          <span><b>${forecast.target}</b><small>${targetPlayer.civ.name} · ${forecast.targetHp} HP</small>${hpMeter(forecast.targetHp, hitsCity ? defender.maxHp : 100, targetPlayer.civ.color)}</span>
        </div>
      </div>
      <div class="combat-odds">
        <span>Deal <b>${forecast.out[0]}–${forecast.out[1]}</b></span>
        <span>${forecast.back ? `Take <b>${forecast.back[0]}–${forecast.back[1]}</b>` : "No retaliation"}</span>
        <strong class="${verdictClass}">${verdict}</strong>
      </div>
      ${combatBreakdown(forecast)}
      <div class="combat-actions"><button class="combat-confirm">⚔ Attack</button><button class="combat-cancel">Cancel</button></div>`;
    panel.style.display = "block";
    paintUnitArt(panel);
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
      ${report.flankBonus ? `<div class="combat-tactic">Formation bonus · ${report.flankSupport} supporting unit${report.flankSupport === 1 ? "" : "s"} · +${Math.round(report.flankBonus * 100)}% strength</div>` : ""}
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
    rend.reachable = []; rend.controlled = []; rend.attackable = []; rend.settlementSites = [];
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
    const hpPct = Math.max(0, Math.min(100, u.hp));
    const hpTone = u.hp > 65 ? "healthy" : u.hp > 30 ? "wounded" : "critical";
    const supply = def.naval ? game.navalSupply(u) : null;
    const movePips = Array.from({ length: u.maxMoves }, (_, i) =>
      `<i class="${i < u.moves ? "ready" : ""}"></i>`).join("");
    const states = [];
    if (game.isEmbarked(u)) states.push("⛵ Embarked");
    if (u.building) states.push(`${IMPROVEMENT[u.building.type].icon} ${IMPROVEMENT[u.building.type].name} · ${u.building.turnsLeft}t`);
    if (u.healFortify) states.push("➕ Healing");
    else if (u.fortified) states.push("🛡️ Fortified");
    if (u.autoExplore) states.push("🗺️ Auto-exploring");
    if (supply && supply.supplied)
      states.push(`⚓ Supplied · ${supply.source.name} · ${supply.distance}/${supply.range}`);
    else if (supply && supply.attritionActive)
      states.push(`⚠ Attrition · -${NAVAL_SUPPLY.attritionDamage} HP/turn · ` +
        `${Math.round((1 - NAVAL_SUPPLY.combatMultiplier) * 100)}% weaker`);
    else if (supply)
      states.push(supply.graceLeft > 0 ? `⚠ Beyond supply · ${supply.graceLeft}t grace`
        : "⚠ Beyond supply · attrition next turn");
    if (game.knownEnemyZoneOfControl(u, u.c, u.r).length)
      states.push("⚠ Inside enemy control");
    $("unit-info").innerHTML = `
      <canvas class="unit-icon unit-art-icon" width="42" height="42" role="img" aria-label="${def.name} silhouette"></canvas>
      <div class="unit-details">
        <div class="unit-heading"><b>${u.gpName ? u.gpName + " — " : ""}${def.name}</b>
          <span>${u.level ? "⭐".repeat(u.level) : ""}${u.promos.map(k => PROMOS[k].icon).join("")}</span></div>
        <div class="unit-readout">
          <span>HP <b>${u.hp}</b></span><span class="unit-health ${hpTone}"><i style="width:${hpPct}%"></i></span>
          <span class="move-label">Move <b>${u.moves}/${u.maxMoves}</b></span><span class="move-pips">${movePips}</span>
        </div>
        <div class="unit-badges">
          ${def.cs ? `<span>⚔ ${def.cs}</span>` : ""}${def.rs ? `<span>➶ ${def.rs} · r${def.range}</span>` : ""}
          ${!u.isCivilian ? `<span>XP ${u.xp}</span>` : ""}
          ${states.map(s => `<span class="unit-state">${s}</span>`).join("")}
        </div>
      </div>`;
    const art = $("unit-info").querySelector(".unit-art-icon");
    UNIT_ART.draw(art.getContext("2d"), def, 21, 21, 34, "#f4ead3");
    const actions = $("unit-actions");
    actions.innerHTML = "";
    let actionButtons = actions;
    const startGroup = (label) => {
      const group = document.createElement("div");
      group.className = "unit-action-group";
      const heading = document.createElement("span");
      heading.className = "unit-action-label";
      heading.textContent = label;
      actionButtons = document.createElement("div");
      actionButtons.className = "unit-action-buttons";
      group.append(heading, actionButtons);
      actions.appendChild(group);
    };
    const btn = (label, fn, enabled = true, className = "") => {
      const b = document.createElement("button");
      b.textContent = label;
      b.disabled = !enabled;
      if (className) b.className = className;
      b.onclick = fn;
      actionButtons.appendChild(b);
      return b;
    };
    const commandBtn = (label, order, detail = null, onDone = null, sound = null) => {
      const status = game.unitOrderStatus(u, order, game.viewer, detail);
      const b = btn(label, () => {
        if (!game.issueUnitOrder(u, order, game.viewer, detail)) return;
        if (sound) SFX.play(sound);
        if (onDone) onDone();
        else selectUnit(game.units.includes(u) ? u : null);
        refreshAll();
      }, status.ok);
      b.title = status.reason;
      b.dataset.order = order;
      return b;
    };
    if (u.promoPts > 0 && u.owner === game.viewer && !u.isCivilian) {
      startGroup("Promotions");
      for (const key of promotionChoices(u)) {
        if (u.promos.includes(key)) continue;
        const pr = PROMOS[key];
        const promotionButton = commandBtn(`⭐ ${pr.icon} ${pr.name}`, "promote", key, null, "build");
        promotionButton.title = pr.desc;
      }
    }
    startGroup("Abilities");
    if (u.type === "SETTLER") {
      const status = game.citySiteStatus(u.c, u.r, u.owner);
      const actor = game.unitActorStatus(u, game.viewer);
      const ready = actor.ok && status.ok && u.moves > 0;
      const foundButton = btn("🏛️ Found City", () => {
        const city = game.foundCity(u, game.viewer);
        if (city) { SFX.play("found"); selectCity(city); refreshAll(); }
      }, ready);
      foundButton.title = ready ? "Found a city on this tile"
        : !actor.ok ? actor.reason
        : status.ok ? "No movement points remaining; found next turn." : status.reason;
    }
    if (u.def.caravan) {
      const dests = game.tradeDestinations(u);
      const from = game.cityAt(u.c, u.r);
      const actor = game.unitActorStatus(u, game.viewer);
      if (from && from.owner === game.viewer) {
        for (const d of dests.slice(0, 4)) {
          const routeButton = btn(`🐫 → ${d.name} (+${game.routeIncome(from, d)}💰/t)`, () => {
            if (game.establishRoute(u, d.id, game.viewer)) { SFX.play("coin"); selectUnit(null); refreshAll(); }
          }, actor.ok && u.moves > 0);
          routeButton.title = !actor.ok ? actor.reason : u.moves > 0 ? "Establish this trade route"
            : "No movement points remain this turn.";
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
      const actor = game.unitActorStatus(u, game.viewer);
      if (u.def.great === "sci") {
        const discover = btn("🔭 Discover Technology", () => {
          if (game.useGreatPerson(u, game.viewer)) { SFX.play("research"); selectUnit(null); refreshAll(); }
        }, actor.ok);
        discover.title = actor.reason;
      } else if (u.def.great === "eng") {
        const inCity = game.cityAt(u.c, u.r) && game.cityAt(u.c, u.r).owner === game.viewer;
        const rush = btn(`🏗️ Rush Production (+${GP.engineerRush}⚙️)`, () => {
          if (game.useGreatPerson(u, game.viewer)) { SFX.play("build"); selectUnit(null); refreshAll(); }
        }, inCity && actor.ok);
        rush.title = !actor.ok ? actor.reason : inCity ? "Rush this city's current project" : "Move into one of your cities first.";
      } else {
        btn("🎖️ +15% combat within 2 tiles", () => {}, false);
      }
    }
    if (u.def.missionary) {
      const target = game.missionaryTarget(u);
      const actor = game.unitActorStatus(u, game.viewer);
      const spread = btn(`🕊️ Spread Religion (${u.charges} left)`, () => {
        if (game.spreadFromMissionary(u, game.viewer)) {
          selectUnit(game.units.includes(u) ? u : null);
          refreshAll();
        }
      }, actor.ok && !!target && u.moves > 0 && game.players[game.viewer].religionId !== null);
      spread.title = !actor.ok ? actor.reason : !target ? "Move next to a city first."
        : u.moves <= 0 ? "No movement points remain this turn." : "Spread your founded religion.";
    }
    if (u.def.worker) {
      if (u.building) {
        commandBtn("🚫 Cancel Job", "cancel_job", null, () => selectUnit(u));
      } else {
        const actor = game.unitActorStatus(u, game.viewer);
        for (const key of Object.keys(IMPROVEMENT)) {
          if (game.canBuildImprovement(u, key)) {
            const build = btn(`${IMPROVEMENT[key].icon} Build ${IMPROVEMENT[key].name} (${IMPROVEMENT[key].turns}t)`, () => {
              if (!game.startImprovement(u, key, game.viewer)) return;
              cycleNextUnit(); refreshAll();
            }, actor.ok && u.moves > 0);
            build.title = !actor.ok ? actor.reason : u.moves > 0 ? `Begin a ${IMPROVEMENT[key].turns}-turn job`
              : "No movement points remain this turn.";
          }
        }
      }
    }
    if (u.type === "SCOUT") {
      const enabling = !u.autoExplore;
      commandBtn(enabling ? "🗺️ Auto-Explore" : "🛑 Stop Exploring", "auto_explore", enabling,
        () => { if (enabling) { AI.autoExplore(game, u); cycleNextUnit(); } else selectUnit(u); });
    }
    if (!u.isCivilian) {
      const actor = game.unitActorStatus(u, game.viewer);
      const up = game.canUpgrade(u, game.viewer);
      if (u.def.upgrade) {
        const target = game.resolveUnitFor(game.players[game.viewer], u.def.upgrade);
        const upgrade = btn(`⬆️ ${UNITS[target].name} (${up ? up.cost : "—"}💰)`, () => {
          if (game.upgradeUnit(u, game.viewer)) { SFX.play("coin"); selectUnit(u); refreshAll(); }
        }, !!up);
        upgrade.title = !actor.ok ? actor.reason : up ? "Upgrade in friendly territory"
          : "Requires its technology, resource, gold, movement, and friendly territory.";
      }
    }
    if (!actionButtons.childElementCount) actionButtons.parentElement.remove();
    startGroup("Orders");
    if (!u.isCivilian) {
      if (u.fortified || u.healFortify) commandBtn("⛺ Wake", "wake", null, () => selectUnit(u));
      else commandBtn("🛡️ Fortify", "fortify", null, () => cycleNextUnit());
      if (u.hp < 100 && !u.healFortify)
        commandBtn("➕ Heal Up", "heal", null, () => cycleNextUnit());
    }
    if (undoInfo && undoInfo.id === u.id && undoInfo.turn === game.turn) {
      const actor = game.unitActorStatus(u, game.viewer);
      const undo = btn("↩️ Undo Move", () => undoMove(), actor.ok);
      undo.title = actor.reason;
    }
    commandBtn("⏭️ Skip", "skip", null, () => cycleNextUnit());
    const disbandStatus = game.unitOrderStatus(u, "disband", game.viewer);
    const disband = btn("🗑️ Disband", () => {
      if (disband.dataset.armed !== "true") {
        disband.dataset.armed = "true";
        disband.textContent = "Confirm Disband";
        disband.classList.add("armed");
        disband.title = "Click again to permanently remove this unit.";
        setTimeout(() => {
          if (!disband.isConnected || disband.dataset.armed !== "true") return;
          disband.dataset.armed = "false";
          disband.textContent = "🗑️ Disband";
          disband.classList.remove("armed");
          disband.title = disbandStatus.reason;
        }, 2500);
        return;
      }
      if (!game.issueUnitOrder(u, "disband", game.viewer)) return;
      selectUnit(null);
      refreshAll();
    }, disbandStatus.ok, "unit-disband");
    disband.title = disbandStatus.reason;
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
    if (!undoInfo || !u || !game.unitActorStatus(u, game.viewer).ok ||
        u.id !== undoInfo.id || undoInfo.turn !== game.turn) return;
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
    centerMapOn(next);
  }

  // ---------------- city panel ----------------
  function showCityPanel(city) {
    const panel = $("city-panel");
    panel.style.display = "block";
    const y = game.cityYields(city);
    const blockade = game.cityBlockade(city);
    const isMine = city.owner === game.viewer;
    const roadNetwork = isMine ? game.roadNetwork(game.viewer) : null;
    const isRoadHub = !!(roadNetwork && roadNetwork.capital && roadNetwork.capital.id === city.id);
    const hasCapitalRoad = !!(roadNetwork && roadNetwork.cityIds.has(city.id));
    const foodNeeded = city.foodNeeded();
    const surplus = game.cityFoodSurplus(city, y);
    const growthTurns = surplus > 0 ? Math.max(1, Math.ceil((foodNeeded - city.food) / surplus)) : null;
    const growthLabel = surplus > 0 ? `+${surplus}/turn · ${growthTurns}t`
      : surplus < 0 ? `${surplus}/turn · starving` : "Growth stalled";
    const foodPct = Math.max(0, Math.min(100, city.food / foodNeeded * 100));
    const worked = game.workedTiles(city).length;
    let html = `
      <div class="panel-head">
        <b>${city.name}</b> ${city.isCapital ? "★" : ""} <span class="dim">(${CIVS[game.players[city.owner].civId].name})</span>
        <button class="close" onclick="UI.closeCity()">✕</button>
      </div>
      <div class="city-stats">
        <div class="city-yields">
          <span>🍞 <b>${y.food}</b></span><span>⚙️ <b>${y.prod}</b></span><span>💰 <b>${y.gold}</b></span>
          <span>🔬 <b>${y.sci}</b></span><span>🎭 <b>${Math.floor(y.culture)}</b></span><span>☦️ <b>${y.faith}</b></span>
        </div>
        <div class="city-meter">
          <div><span>Population ${city.pop}</span><span class="dim">${growthLabel}</span></div>
          <span class="meter-track"><span style="width:${foodPct}%"></span></span>
        </div>
        <div class="city-vitals dim"><span>👥 ${worked}/${city.pop} worked tiles</span><span>♥ ${city.hp}/${city.maxHp}</span></div>
        ${isMine ? `<div class="city-connection ${isRoadHub || hasCapitalRoad ? "connected" : "unlinked"}">
          <b>${isRoadHub ? "🛤️ Road network hub" : hasCapitalRoad ? "🛤️ Capital road" : "○ Capital road unlinked"}</b>
          <span>${isRoadHub ? `${Math.max(0, roadNetwork.connectedCities.length - 1)}/${Math.max(0, roadNetwork.connectedCities.length + roadNetwork.disconnectedCities.length - 1)} cities linked` : hasCapitalRoad ? `+${game.roadConnectionIncome(city)} gold/turn` : "0 gold/turn"}</span>
        </div>` : ""}
        ${blockade.active ? `<div class="city-blockade" role="status"><b>⚓ Blockaded</b><span>Naval pressure ${Math.ceil(blockade.attackPower)} vs ${Math.ceil(blockade.defensePower)}. Gold halved; trade and repairs suspended.</span></div>` : ""}
        ${city.religion !== null ? `<br><span class="dim">Faith: ${game.religions[city.religion].icon} ${game.religions[city.religion].name}</span>` : ""}
      </div>`;
    if (city.buildings.length) {
      html += `<div class="city-buildings">${city.buildings.map(b => BUILDINGS[b].icon + " " + BUILDINGS[b].name).join(" · ")}</div>`;
    }
    if (isMine) {
      const p0 = game.players[game.viewer];
      const focus = CITY_FOCUS[city.focus] ? city.focus : "balanced";
      html += `<div class="city-section-title">Citizen focus</div>
        <div class="city-focus" role="group" aria-label="Citizen tile focus">${Object.entries(CITY_FOCUS).map(([key, f]) =>
          `<button class="${key === focus ? "active" : ""}" aria-pressed="${key === focus}" title="${f.hint}"
            onclick="UI.setCityFocus(${city.id},'${key}')">${f.icon} ${f.name}</button>`).join("")}</div>`;
      if (p0.religionId !== null) {
        const cost = game.missionaryCost(game.viewer);
        html += `<div class="city-actions"><button ${p0.faith >= cost ? "" : "disabled"}
          onclick="UI.buyMissionary(${city.id})">🙏 Missionary (${cost} ☦️)</button></div>`;
      }
      const opts = game.productionOptions(city);
      const cur = city.producing;
      const curDef = cur ? (cur.kind === "unit" ? UNITS[cur.key] : BUILDINGS[cur.key]) : null;
      const curCost = curDef ? curDef.cost : 0;
      const prodRate = cur ? game.cityProductionRate(city, cur, y) : y.prod;
      const blocked = !!(cur && cur.kind === "unit" && city.prodStored >= curCost && !game.productionUnitSpot(city, cur.key));
      const prodTurns = cur && !blocked ? Math.max(1, Math.ceil(Math.max(0, curCost - city.prodStored) / Math.max(1, prodRate))) : null;
      const prodPct = curCost ? Math.max(0, Math.min(100, city.prodStored / curCost * 100)) : 0;
      html += `<div class="city-section-title">Production</div>
        <div class="prod-current">
          <div><span>${curDef ? productionLabel(cur.kind, cur.key, curDef) : "Choose a project"}</span>
            ${cur ? `<button class="prod-cancel" title="Stop production" aria-label="Stop production" onclick="UI.cancelProduction(${city.id})">✕</button>` : ""}</div>
          ${cur ? `<div class="dim">${city.prodStored}/${curCost} ⚙️ · ${blocked ? "Waiting for unit space" : `${prodRate}/turn · ${prodTurns}t`}</div>
            <span class="meter-track production"><span style="width:${prodPct}%"></span></span>` : ""}
        </div>`;
      if (city.queue.length) {
        html += `<div class="prod-queue"><span class="dim">Queue</span>${city.queue.map((q, i) => {
          const d = q.kind === "unit" ? UNITS[q.key] : BUILDINGS[q.key];
          return `<span class="queue-entry">${productionLabel(q.kind, q.key, d)}<button title="Remove from queue" aria-label="Remove ${d.name} from queue"
            onclick="UI.unqueue(${city.id},${i})">✕</button></span>`;
        }).join("")}</div>`;
      }
      html += `<div class="prod-list">`;
      for (const o of opts) {
        const current = !!(cur && cur.kind === o.kind && cur.key === o.key);
        const queued = city.queue.some(q => q.kind === o.kind && q.key === o.key);
        const rate = game.cityProductionRate(city, { kind: o.kind, key: o.key }, y);
        const turns = Math.max(1, Math.ceil((o.cost - (current ? city.prodStored : 0)) / Math.max(1, rate)));
        const price = game.buyCost(o.cost, city.owner);
        const canPlace = o.kind !== "unit" || !!game.productionUnitSpot(city, o.key);
        const afford = p0.gold >= price;
        const canQueue = !!cur && !current && !queued && city.queue.length < 6;
        html += `<div class="prod-item ${o.wonder ? "wonder" : ""}">
          <span class="prod-name">${productionLabel(o.kind, o.key, o)}</span>
          <span class="prod-meta">${o.cost}⚙️ · ${rate}/t · ~${turns}t</span>
          <div class="prod-actions">
            <button ${current ? "disabled" : ""} title="${current ? "Current project" : "Build this now"}"
              onclick="UI.buildNow(${city.id},'${o.kind}','${o.key}')">${current ? "✓ Current" : "🔨 Build"}</button>
            ${cur ? `<button ${canQueue ? "" : "disabled"} title="${queued ? "Already queued" : city.queue.length >= 6 ? "Queue is full" : "Add to queue"}"
              onclick="UI.setProduction(${city.id},'${o.kind}','${o.key}')">${queued ? "✓ Queued" : "＋ Queue"}</button>` : ""}
            <button ${afford && canPlace ? "" : "disabled"} title="${!canPlace ? "No open tile for this unit" : !afford ? "Not enough gold" : "Purchase immediately"}"
              onclick="UI.buyItem(${city.id},'${o.kind}','${o.key}')">💰${price}</button>
          </div>
        </div>`;
      }
      html += `</div>`;
    }
    panel.innerHTML = html;
    paintUnitArt(panel);
  }

  function setCityFocus(cityId, focus) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city || !game.setCityFocus(city, focus, game.viewer)) return;
    SFX.play("click");
    showCityPanel(city);
    refreshAll();
  }

  function setProduction(cityId, kind, key) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city || !game.setCityProduction(city, { kind, key }, true, game.viewer)) return;
    SFX.play("click");
    showCityPanel(city);
    refreshAll();
  }

  // Switch what the city is building right now (stored production carries over).
  function buildNow(cityId, kind, key) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city || !game.setCityProduction(city, { kind, key }, false, game.viewer)) return;
    SFX.play("click");
    showCityPanel(city);
    refreshAll();
  }

  // Stop current production; if a queue exists, promote its next item.
  function cancelProduction(cityId) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city || !game.cancelCityProduction(city, game.viewer)) return;
    SFX.play("click");
    showCityPanel(city);
    refreshAll();
  }

  function unqueue(cityId, i) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city || !game.removeQueuedProduction(city, i, game.viewer)) return;
    showCityPanel(city);
  }

  function buyItem(cityId, kind, key) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId);
    if (!city) return;
    if (game.purchase(city, { kind, key }, game.viewer)) {
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
  function attitudeTone(value) {
    return value >= 10 ? "positive" : value <= -10 ? "negative" : "neutral";
  }

  function signedAttitude(value, precision = 0) {
    const rounded = precision ? Math.round(value * 10) / 10 : Math.round(value);
    return `${rounded >= 0 ? "+" : "−"}${Math.abs(rounded).toFixed(precision)}`;
  }

  function attitudeMeter(title, breakdown) {
    const position = Math.max(0, Math.min(100, (breakdown.value + 100) / 2));
    const tone = attitudeTone(breakdown.value);
    return `<div class="diplo-attitude">
      <div><span>${title}</span><b class="${tone}">${breakdown.label} ${signedAttitude(breakdown.value)}</b></div>
      <span class="diplo-attitude-track" aria-label="${title}: ${breakdown.label} ${signedAttitude(breakdown.value)}">
        <i class="${tone}" style="left:${position}%"></i>
      </span>
    </div>`;
  }

  function attitudeReasonColumn(title, breakdown) {
    const rows = breakdown.components.length ? breakdown.components.map(reason => {
      const precision = Math.abs(reason.value) < 1 ? 1 : 0;
      return `<div class="diplo-memory-row"><span>${reason.label}</span>
        <b class="${attitudeTone(reason.value)}">${signedAttitude(reason.value, precision)}</b></div>`;
    }).join("") : `<div class="diplo-memory-empty">No lasting diplomatic history</div>`;
    return `<section class="diplo-memory-column"><header><span>${title}</span>
      <strong class="${attitudeTone(breakdown.value)}">${breakdown.label} ${signedAttitude(breakdown.value)}</strong></header>${rows}</section>`;
  }

  function relationshipHistory(theirs, ours) {
    return `<details class="diplo-memory">
      <summary><span>Relationship history</span><b>They ${signedAttitude(theirs.value)} · You ${signedAttitude(ours.value)}</b></summary>
      <div class="diplo-memory-grid">
        ${attitudeReasonColumn("Their reasons", theirs)}
        ${attitudeReasonColumn("Your reasons", ours)}
      </div>
    </details>`;
  }

  function showDiploScreen() {
    const p = game.players[game.viewer];
    const modal = $("diplo-modal");
    modal.style.display = "flex";
    const body = $("diplo-body");
    let html = "";
    for (const p2 of game.players) {
      if (p2.index === game.viewer || p2.isMinor || p2.isBarb) continue;
      const met = p.met.has(p2.index);
      const civ = p2.civ;
      if (!met || !p2.alive) {
        html += `<div class="diplo-row" style="border-left:6px solid ${met ? civ.color : "#555"}">
          <div><b>${met ? civ.name : "Unknown Civilization"}</b>
            ${met ? `<span class="dim"> — ${civ.leader}</span>` : ""}
            ${!p2.alive ? " <span class='dead'>☠️ destroyed</span>" : ""}</div></div>`;
        continue;
      }
      if (met && p2.alive) {
        const atWar = p.atWarWith.has(p2.index);
        const theirs = game.attitudeBreakdown(p2.index, game.viewer);
        const ours = game.attitudeBreakdown(game.viewer, p2.index);
        const deal = p.deals.find(d => d.other === p2.index && d.ends > game.turn);
        const pact = p.pacts.has(p2.index);
        const truce = game.truceTurnsRemaining(game.viewer, p2.index);
        const warTurns = p.warWeariness[p2.index] || 0;
        const canWar = game.canDeclareWar(game.viewer, p2.index);
        const state = atWar ? `<span class="diplo-state war">At war · ${warTurns}t</span>`
          : truce ? `<span class="diplo-state truce">Truce · ${truce}t</span>`
          : pact ? `<span class="diplo-state allied">Defensive pact</span>`
          : `<span class="diplo-state peace">At peace</span>`;
        const treaties = [
          deal ? `<span>🤝 ${RESOURCE[deal.give].icon}${RESOURCE[deal.give].name} for ${RESOURCE[deal.get].icon}${RESOURCE[deal.get].name} · ${deal.ends - game.turn}t</span>` : "",
          pact ? `<span>🛡️ Mutual defense</span>` : "",
          truce ? `<span>☮️ War barred until turn ${game.turn + truce}</span>` : "",
        ].filter(Boolean).join("");
        html += `<article class="diplo-row diplo-major" style="--civ:${civ.color}">
          <header class="diplo-header"><i></i><div class="diplo-identity"><b>${civ.name}</b><span>${civ.leader}</span></div>${state}</header>
          <div class="diplo-stats"><span>Score <b>${game.score(p2.index)}</b></span><span>Military <b>${Math.floor(game.militaryPower(p2.index))}</b></span></div>
          ${attitudeMeter("Their view of you", theirs)}
          ${treaties ? `<div class="diplo-treaties">${treaties}</div>` : ""}
          ${relationshipHistory(theirs, ours)}
          <div class="diplo-actions">
            <button ${!atWar && !canWar ? "disabled" : ""}
              title="${atWar ? "Ask this civilization to end the war" : truce ? `${truce} turns remain in the peace treaty` : pact ? "A defensive pact prevents a declaration" : "Declare war"}"
              onclick="UI.diploAction(${p2.index})">${atWar ? "☮️ Propose Peace" : truce ? `☮️ Truce (${truce}t)` : "⚔️ Declare War"}</button>`;
        if (!atWar) {
          const canDeal = game.canLuxuryDeal(game.viewer, p2.index);
          const dealHint = canDeal ? `${RESOURCE[game.tradableLuxes(game.viewer, p2.index)[0]].icon} for ${RESOURCE[game.tradableLuxes(p2.index, game.viewer)[0]].icon}` : "";
          html += `<button ${canDeal ? "" : "disabled"} title="Swap surplus luxuries for ${DIPLO.luxuryDealTurns} turns — both sides gain happiness"
              onclick="UI.diploTrade(${p2.index})">🤝 Trade Luxuries ${dealHint}</button>
            <button ${game.canGiftGold(game.viewer, p2.index) ? "" : "disabled"} title="Improves their attitude toward you"
              onclick="UI.diploGift(${p2.index})">🎁 Gift ${DIPLO.giftGold}💰</button>
            <button ${game.canPact(game.viewer, p2.index) ? "" : "disabled"} title="Both views must reach ${DIPLO.pactThreshold}+. Current: they ${signedAttitude(theirs.value)}, you ${signedAttitude(ours.value)}."
              onclick="UI.diploPact(${p2.index})">🛡️ Defensive Pact</button>`;
        }
        html += `</div></article>`;
      }
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
    if (!game || game.over || !myTurn()) return false;
    const offers = game.pendingPeaceOffers(game.viewer);
    if (!offers.length) return false;
    showPeaceModal(offers);
    return true;
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
    else showTurnPrompts();
  }

  // ---------------- event decisions ----------------
  const EVENT_CHOICE_ICONS = {
    growth: "🌾", commerce: "💰", culture: "🎭", faith: "☦️",
    science: "🔬", industry: "⚙️", stability: "🛡️", risk: "⚠️",
  };

  function showEventDecision() {
    const modal = $("event-modal");
    if (!game || game.over || !myTurn()) { modal.style.display = "none"; return false; }
    const decision = game.eventDecision(game.viewer);
    if (!decision) { modal.style.display = "none"; return false; }
    const place = decision.city ? `${decision.city.name} · ` : "";
    const buttons = decision.choices.map(choice => `
      <button class="event-choice" data-tone="${choice.tone}" ${choice.available ? "" : "disabled"}
        title="${choice.available ? choice.description : choice.reason || "This response is unavailable"}"
        onclick='UI.answerEvent(${JSON.stringify(decision.id)}, ${JSON.stringify(choice.key)})'>
        <span class="event-choice-icon">${EVENT_CHOICE_ICONS[choice.tone] || "◆"}</span>
        <strong>${choice.label}</strong>
        <span>${choice.description}</span>
        ${choice.available ? "" : `<small>${choice.reason || "Unavailable"}</small>`}
      </button>`).join("");
    $("event-body").innerHTML = `
      <header class="event-head ${decision.kind}">
        <span class="event-icon">${decision.icon}</span>
        <div><span class="event-kicker">Court decision</span><h2>${decision.name}</h2>
          <div class="event-location">${place}reported on turn ${decision.turn}</div></div>
      </header>
      <p class="event-prompt">${decision.prompt}</p>
      <div class="event-choices">${buttons}</div>
      <div class="event-note">The court must choose before this turn can advance.</div>`;
    modal.style.display = "flex";
    return true;
  }

  function answerEvent(eventId, choiceKey) {
    if (!myTurn()) return;
    const outcome = game.chooseEvent(game.viewer, eventId, choiceKey);
    if (!outcome) return;
    $("event-modal").style.display = "none";
    try { localStorage.setItem("balkan-civ-save", game.serialize()); } catch (e) { /* storage full */ }
    if (NET.active) NET.sendState(game);
    refreshAll();
    showTurnPrompts();
  }

  function showTurnPrompts() {
    if (!game || game.over || !myTurn()) return false;
    if (showEventDecision()) return true;
    if (maybeShowPeaceOffers()) return true;
    return maybePromptFounding();
  }

  function diploAction(idx) {
    if (!myTurn()) return;
    const p = game.players[game.viewer];
    if (p.atWarWith.has(idx)) {
      const response = game.peaceAcceptance(game.viewer, idx);
      if (response.humanDecision) {
        if (game.offerPeace(game.viewer, idx)) game.notify("Peace proposal sent.", game.viewer);
      } else if (response.accepted) game.makePeace(game.viewer, idx);
      else game.notify(`${game.players[idx].civ.name} refuses to make peace!`, game.viewer);
    } else {
      if (!game.declareWar(game.viewer, idx))
        game.notify("War cannot be declared while a pact or peace treaty is active.", game.viewer);
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
    const economy = game.empireEconomy(game.viewer);
    const gold = economy.netGold, sci = economy.science, faith = economy.faith;
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
      : p.techs.size >= Object.keys(TECHS).length
        ? `🔬 <b>Research complete</b>`
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
    const cpt = Math.floor(economy.culture);
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

  // ---------------- empire overview ----------------
  const signed = value => {
    const n = Math.floor(value);
    return `${n > 0 ? "+" : ""}${n}`;
  };

  function showEmpireScreen(tab = empireTab) {
    if (!game) return;
    if (["cities", "military", "economy"].includes(tab)) empireTab = tab;
    renderEmpireScreen();
    $("empire-modal").style.display = "flex";
  }

  function setEmpireTab(tab) {
    if (!["cities", "military", "economy"].includes(tab)) return;
    empireTab = tab;
    renderEmpireScreen();
  }

  function renderEmpireScreen() {
    const p = game.players[game.viewer];
    const e = game.empireEconomy(game.viewer);
    const happiness = game.happinessOf(game.viewer);
    const tabs = [
      ["cities", "🏙️", "Cities"], ["military", "⚔️", "Military"], ["economy", "💰", "Economy"],
    ].map(([key, icon, label]) => `<button role="tab" aria-selected="${empireTab === key}"
      class="${empireTab === key ? "active" : ""}" onclick="UI.setEmpireTab('${key}')">${icon} ${label}</button>`).join("");
    const summary = [
      ["🏙️", "Cities", e.cities, ""],
      ["👥", "Population", e.population, ""],
      ["⚔️", "Units", e.units, ""],
      ["💰", "Gold / turn", signed(e.netGold), e.netGold < 0 ? "negative" : "positive"],
      ["🔬", "Science / turn", `+${e.science}`, ""],
      [happiness >= 0 ? "😊" : "😞", "Happiness", signed(happiness), happiness < 0 ? "negative" : "positive"],
    ].map(([icon, label, value, tone]) => `<div class="empire-stat ${tone}"><span>${icon}</span>
      <div><b>${value}</b><small>${label}</small></div></div>`).join("");
    const view = empireTab === "cities" ? renderEmpireCities()
      : empireTab === "military" ? renderEmpireMilitary() : renderEmpireEconomy(e);
    $("empire-body").innerHTML = `<div class="empire-banner" style="--civ:${p.civ.color}">
        <div class="empire-identity"><i></i><div><strong>${p.civ.name}</strong><span>${p.leaderName}</span></div></div>
        <div class="empire-summary">${summary}</div>
      </div>
      <div class="empire-tabs" role="tablist" aria-label="Empire overview">${tabs}</div>
      <div class="empire-view" role="tabpanel">${view}</div>`;
    paintUnitArt($("empire-body"));
  }

  function renderEmpireCities() {
    const roadNetwork = game.roadNetwork(game.viewer);
    const rows = game.cities.filter(c => c.owner === game.viewer).map(city => {
      const y = game.cityYields(city);
      const blockade = game.cityBlockade(city);
      const surplus = game.cityFoodSurplus(city, y);
      const growthTurns = surplus > 0
        ? Math.max(1, Math.ceil((city.foodNeeded() - city.food) / surplus)) : Infinity;
      const current = city.producing;
      const def = current ? (current.kind === "unit" ? UNITS[current.key] : BUILDINGS[current.key]) : null;
      const rate = current ? game.cityProductionRate(city, current, y) : y.prod;
      const blocked = !!(current && current.kind === "unit" && city.prodStored >= def.cost &&
        !game.productionUnitSpot(city, current.key));
      const productionTurns = current && !blocked
        ? Math.max(1, Math.ceil(Math.max(0, def.cost - city.prodStored) / Math.max(1, rate))) : Infinity;
      return { city, y, blockade, surplus, growthTurns, current, def, rate, blocked, productionTurns };
    });
    rows.sort((a, b) => {
      if (empireCitySort === "population") return b.city.pop - a.city.pop || a.city.name.localeCompare(b.city.name);
      if (empireCitySort === "growth") return a.growthTurns - b.growthTurns || b.surplus - a.surplus;
      if (empireCitySort === "production") return b.rate - a.rate || a.productionTurns - b.productionTurns;
      return Number(b.city.isCapital) - Number(a.city.isCapital) || a.city.name.localeCompare(b.city.name);
    });
    const sortOptions = [["capital", "Capital first"], ["population", "Population"],
      ["growth", "Growth forecast"], ["production", "Production output"]]
      .map(([key, label]) => `<option value="${key}" ${empireCitySort === key ? "selected" : ""}>${label}</option>`).join("");
    const cityRows = rows.map(({ city, y, blockade, surplus, growthTurns, current, def, rate, blocked, productionTurns }) => {
      const growth = surplus > 0 ? `+${surplus} food · ${growthTurns}t`
        : surplus < 0 ? `${surplus} food · starving` : "Growth stalled";
      const production = current
        ? `<strong>${productionLabel(current.kind, current.key, def)}</strong><span class="${blocked ? "alert" : "dim"}">${blocked ? "Waiting for unit space" : `${rate} ⚙️/turn · ${productionTurns}t`}${city.queue.length ? ` · ${city.queue.length} queued` : ""}</span>`
        : `<strong class="alert">Production needed</strong><span class="dim">No current project</span>`;
      const focusOptions = Object.entries(CITY_FOCUS).map(([key, focus]) =>
        `<option value="${key}" ${city.focus === key ? "selected" : ""}>${focus.icon} ${focus.name}</option>`).join("");
      const isHub = roadNetwork.capital && roadNetwork.capital.id === city.id;
      const connected = roadNetwork.cityIds.has(city.id);
      const roadStatus = isHub ? `Road hub · ${Math.max(0, roadNetwork.connectedCities.length - 1)}/${Math.max(0, rows.length - 1)} linked`
        : connected ? `Capital road · +${game.roadConnectionIncome(city)} gold`
        : "Capital road unlinked";
      return `<div class="empire-row empire-city-row${current ? "" : " needs-order"}${blockade.active ? " blockaded" : ""}">
        <button class="empire-jump" title="Center map on ${city.name}" aria-label="Center map on ${city.name}"
          onclick="UI.empireJumpCity(${city.id})">⌖</button>
        <div class="empire-primary"><strong>${city.name}${city.isCapital ? " ★" : ""}</strong>
          <span class="${blockade.active ? "alert" : !isHub && !connected ? "infrastructure-warning" : "dim"}">${blockade.active ? `⚓ Blockaded · ${Math.ceil(blockade.attackPower)} vs ${Math.ceil(blockade.defensePower)} pressure` : `${city.buildings.length} building${city.buildings.length === 1 ? "" : "s"} · ${city.hp}/${city.maxHp} HP · ${roadStatus}`}</span></div>
        <div class="empire-pop"><b>👥 ${city.pop}</b><span class="${surplus < 0 ? "alert" : "dim"}">${growth}</span></div>
        <div class="empire-yields" aria-label="City yields"><span>🍞 ${y.food}</span><span>⚙️ ${y.prod}</span>
          <span>💰 ${y.gold}</span><span>🔬 ${y.sci}</span><span>🎭 ${Math.floor(y.culture)}</span><span>☦️ ${y.faith}</span></div>
        <label class="empire-focus"><span>Citizen focus</span><select name="city-focus-${city.id}" aria-label="Citizen focus for ${city.name}"
          ${myTurn() ? "" : "disabled"} onchange="UI.empireSetFocus(${city.id},this.value)">${focusOptions}</select></label>
        <div class="empire-production">${production}</div>
      </div>`;
    }).join("");
    return `<div class="empire-toolbar"><div><strong>City administration</strong><span>${rows.length} settlement${rows.length === 1 ? "" : "s"}</span></div>
        <label>Sort <select name="empire-city-sort" onchange="UI.setEmpireCitySort(this.value)">${sortOptions}</select></label></div>
      <div class="empire-table empire-city-table">
        <div class="empire-row empire-head"><span></span><span>City</span><span>Population</span><span>Yields</span><span>Focus</span><span>Production</span></div>
        ${cityRows || `<div class="empire-empty">No cities under your control.</div>`}
      </div>`;
  }

  function setEmpireCitySort(sort) {
    if (!["capital", "population", "growth", "production"].includes(sort)) return;
    empireCitySort = sort;
    renderEmpireScreen();
  }

  function empireSetFocus(cityId, focus) {
    if (!myTurn()) return;
    const city = game.cities.find(c => c.id === cityId && c.owner === game.viewer);
    if (!city || !game.setCityFocus(city, focus, game.viewer)) return;
    SFX.play("click");
    refreshTopBar();
    rend.dirty = true;
    renderEmpireScreen();
  }

  function empireUnitOrder(unit, supply = unit.def.naval ? game.navalSupply(unit) : null) {
    if (unit.promoPts > 0 && !unit.isCivilian) return ["Promotion ready", "attention"];
    if (supply && !supply.supplied && supply.turns >= NAVAL_SUPPLY.graceTurns)
      return [supply.attritionActive ? "Taking naval attrition" : "Attrition next turn", "attention"];
    if (supply && !supply.supplied)
      return [`Beyond supply · ${supply.graceLeft}t grace`, "working"];
    if (unit.resupplying) return ["Returning to port", "working"];
    if (unit.building) return [`Building ${IMPROVEMENT[unit.building.type].name} · ${unit.building.turnsLeft}t`, "working"];
    if (unit.healFortify) return ["Fortified until healed", "working"];
    if (unit.fortified) return ["Fortified", "working"];
    if (unit.autoExplore) return ["Auto-exploring", "working"];
    if (unit.path && unit.path.length) return [`Moving · ${unit.path.length} hex${unit.path.length === 1 ? "" : "es"}`, "working"];
    if (unit.moves > 0 && !unit.attacked) return ["Ready for orders", "ready"];
    return ["Orders complete", "spent"];
  }

  function renderEmpireMilitary() {
    const units = game.units.filter(u => u.owner === game.viewer).map(unit => {
      const supply = unit.def.naval ? game.navalSupply(unit) : null;
      const order = empireUnitOrder(unit, supply);
      const strength = Math.max(unit.def.cs || 0, unit.def.rs || 0);
      return { unit, order, strength, supply };
    });
    const rank = { attention: 0, ready: 1, working: 2, spent: 3 };
    units.sort((a, b) => {
      if (empireUnitSort === "type") return a.unit.def.name.localeCompare(b.unit.def.name) || a.unit.id - b.unit.id;
      if (empireUnitSort === "strength") return b.strength - a.strength || a.unit.def.name.localeCompare(b.unit.def.name);
      if (empireUnitSort === "health") return a.unit.hp - b.unit.hp || b.strength - a.strength;
      return rank[a.order[1]] - rank[b.order[1]] || Number(a.unit.isCivilian) - Number(b.unit.isCivilian) || b.strength - a.strength;
    });
    const combat = units.filter(x => !x.unit.isCivilian).length;
    const ready = units.filter(x => x.order[1] === "ready" || x.order[1] === "attention").length;
    const supplyRisks = units.filter(x => x.supply && !x.supply.supplied).length;
    const economy = game.empireEconomy(game.viewer);
    const sortOptions = [["readiness", "Readiness"], ["type", "Unit type"], ["strength", "Strength"], ["health", "Lowest health"]]
      .map(([key, label]) => `<option value="${key}" ${empireUnitSort === key ? "selected" : ""}>${label}</option>`).join("");
    const unitRows = units.map(({ unit, order, supply }) => {
      const city = game.cityAt(unit.c, unit.r);
      const tile = game.tile(unit.c, unit.r);
      const location = city ? city.name : `${TERRAIN[tile.terrain].name} · ${unit.c + 1},${unit.r + 1}`;
      const power = [unit.def.cs ? `⚔ ${unit.def.cs}` : "", unit.def.rs ? `➶ ${unit.def.rs}` : ""].filter(Boolean).join(" · ") || "Civilian";
      const supplyText = !supply ? "" : supply.supplied
        ? `Supply: ${supply.source.name} · ${supply.distance}/${supply.range}`
        : supply.attritionActive ? `Out of supply · -${NAVAL_SUPPLY.attritionDamage} HP/turn`
        : `Beyond supply · ${supply.graceLeft}t grace`;
      const detail = [unit.promos.length ? unit.promos.map(key => PROMOS[key].name).join(", ") :
        (!unit.isCivilian ? "No promotions" : ""), supplyText].filter(Boolean).join(" · ");
      return `<div class="empire-row empire-unit-row ${order[1]} ${supply && !supply.supplied ?
          (supply.attritionActive ? "supply-critical" : "supply-warning") : ""}">
        <button class="empire-jump" title="Center map on ${unit.def.name}" aria-label="Center map on ${unit.def.name}"
          onclick="UI.empireJumpUnit(${unit.id})">⌖</button>
        <div class="empire-primary"><strong class="empire-unit-name">${unitArtCanvas(unit.type)}<span class="unit-name-text">${unit.gpName || unit.def.name}</span></strong>
          <span class="dim">${unit.gpName ? unit.def.name + " · " : ""}Level ${unit.level} · ${unit.xp} XP</span></div>
        <div class="empire-health"><span><b>${unit.hp}</b> HP</span><i><b style="width:${unit.hp}%"></b></i></div>
        <div class="empire-moves"><b>${unit.moves}/${unit.maxMoves}</b><span class="dim">Movement</span></div>
        <div class="empire-strength"><b>${power}</b><span class="dim">${detail}</span></div>
        <div class="empire-order"><b>${order[0]}</b><span class="dim">${location}</span></div>
      </div>`;
    }).join("");
    return `<div class="empire-toolbar"><div><strong>Armed forces</strong><span>${combat} combat · ${units.length - combat} civilian · ${ready} awaiting orders · ${economy.maintenance} upkeep${supplyRisks ? ` · ${supplyRisks} beyond supply` : ""}</span></div>
        <label>Sort <select name="empire-unit-sort" onchange="UI.setEmpireUnitSort(this.value)">${sortOptions}</select></label></div>
      <div class="empire-table empire-unit-table">
        <div class="empire-row empire-head"><span></span><span>Unit</span><span>Health</span><span>Moves</span><span>Strength</span><span>Orders / location</span></div>
        ${unitRows || `<div class="empire-empty">No units under your command.</div>`}
      </div>`;
  }

  function setEmpireUnitSort(sort) {
    if (!["readiness", "type", "strength", "health"].includes(sort)) return;
    empireUnitSort = sort;
    renderEmpireScreen();
  }

  function renderEmpireEconomy(e) {
    const p = game.players[game.viewer];
    const luxuries = game.luxuryTypesOf(game.viewer);
    const ledger = [
      ["City income", e.cityGold, `${e.cities} cit${e.cities === 1 ? "y" : "ies"}`],
      ["Golden Age", e.goldenAgeGold, p.goldenAgeTurns > 0 ? `${p.goldenAgeTurns} turns remaining` : "Inactive"],
      ["Capital roads", e.connectionGold, `${e.connectedCities}/${e.connectableCities} cities linked`],
      ["Trade routes", e.tradeGold, `${game.routes.filter(r => r.owner === game.viewer).length} outbound`],
      ["Guilds", e.guildGold, p.policies.has("GUILDS")
        ? `${luxuries.length} controlled luxur${luxuries.length === 1 ? "y" : "ies"}` : "Policy not adopted"],
      ["Čaršija finisher", e.carsijaGold, game.policyBranchDone(game.viewer, "CARSIJA")
        ? `${e.cities} cit${e.cities === 1 ? "y" : "ies"}` : "Branch incomplete"],
      ["City-state relations", e.cityStateGold, "Mercantile friends and allies"],
      ["Tithe", e.titheGold, e.titheGold ? `${e.titheGold} follower cit${e.titheGold === 1 ? "y" : "ies"}` : "No active tithe"],
      ["Unit upkeep", -e.maintenance, `${e.units} unit${e.units === 1 ? "" : "s"} · ${e.freeUnits} maintenance-free`],
    ].map(([label, value, detail]) => `<div class="ledger-row ${value > 0 ? "positive" : value < 0 ? "negative" : "zero"}">
      <span><b>${label}</b><small>${detail}</small></span><strong>${signed(value)}</strong></div>`).join("");
    const routes = game.routes.map(route => {
      const status = game.tradeRouteStatus(route);
      const { from, to } = status;
      if (!from || !to || (route.owner !== game.viewer && to.owner !== game.viewer)) return null;
      const income = status.active ? (route.owner === game.viewer ? game.routeIncome(from, to) : 1) : 0;
      const kind = route.owner === game.viewer ? "Outbound" : "Destination share";
      const blockedAt = [status.fromBlockade && status.fromBlockade.active ? from.name : null,
        status.toBlockade && status.toBlockade.active ? to.name : null].filter(Boolean).join(" and ");
      return `<div class="empire-route${status.active ? "" : " suspended"}"><span>🐫 <b>${from.name} → ${to.name}</b><small>${status.active ? kind : `Blockade at ${blockedAt}`}</small></span>
        <span><b>${status.active ? `+${income} 💰` : "⚓ Suspended"}</b><small>${Math.max(0, route.ends - game.turn)} turns</small></span></div>`;
    }).filter(Boolean).join("");
    const routeCap = TRADE.maxRoutes + (p.policies.has("CARAVANSERAI") ? 1 : 0);
    const outbound = game.routes.filter(r => r.owner === game.viewer).length;
    const happiness = game.happinessOf(game.viewer);
    const outputs = [["🍞", "Food", e.food], ["⚙️", "Production", e.production], ["🔬", "Science", e.science],
      ["🎭", "Culture", Math.floor(e.culture)], ["☦️", "Faith", e.faith]]
      .map(([icon, label, value]) => `<div><span>${icon}</span><b>${value}</b><small>${label} / turn</small></div>`).join("");
    return `<div class="empire-economy-grid">
      <section class="empire-ledger"><h3>Gold ledger</h3>${ledger}
        <div class="ledger-total"><span><b>Net income</b><small>Treasury ${Math.floor(p.gold)} 💰</small></span>
          <strong class="${e.netGold < 0 ? "negative" : "positive"}">${signed(e.netGold)}</strong></div>
      </section>
      <section class="empire-economic-status"><h3>Empire output</h3><div class="empire-output">${outputs}</div>
        <div class="empire-wellbeing"><div><span>Happiness</span><b class="${happiness < 0 ? "negative" : "positive"}">${signed(happiness)}</b></div>
          <div><span>Luxuries</span><b>${luxuries.length}</b></div>
          <div><span>Golden Age</span><b>${p.goldenAgeTurns > 0 ? `${p.goldenAgeTurns}t` : `${Math.floor(p.gaMeter)}/${GOLDEN_AGE.threshold(p.gaCount)}`}</b></div></div>
        <div class="empire-luxuries">${luxuries.length ? luxuries.map(key => `<span title="${RESOURCE[key].name}">${RESOURCE[key].icon} ${RESOURCE[key].name}</span>`).join("") : `<span class="dim">No controlled luxury resources</span>`}</div>
      </section>
      <section class="empire-trade"><h3>Trade routes <span>${outbound}/${routeCap} outbound</span></h3>
        ${routes || `<div class="empire-empty">No active trade routes.</div>`}
      </section>
    </div>`;
  }

  function empireJumpCity(cityId) {
    const city = game.cities.find(c => c.id === cityId && c.owner === game.viewer);
    if (!city) return;
    $("empire-modal").style.display = "none";
    selectCity(city);
    centerMapOn(city);
  }

  function empireJumpUnit(unitId) {
    const unit = game.units.find(u => u.id === unitId && u.owner === game.viewer);
    if (!unit) return;
    $("empire-modal").style.display = "none";
    selectUnit(unit);
    centerMapOn(unit);
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
      html += `<div class="prod-item menu-slot">
        <span>💾 Slot ${i}${meta ? ` <span class="dim">— ${meta.label}</span>` : ` <span class="dim">— empty</span>`}</span>
        <button onclick="UI.saveSlot(${i})">Save</button>
        <button ${meta ? "" : "disabled"} onclick="UI.loadSlot(${i})">Load</button>
      </div>`;
    }
    const is3d = !!rend.three;
    html += `</div>
      <div class="game-seed">
        <span>Map seed</span><code id="menu-seed">${game.seed >>> 0}</code>
        <button id="btn-copy-seed" class="icon-command" onclick="UI.copyGameSeed()"
          title="Copy map seed" aria-label="Copy map seed">⧉</button>
      </div>
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

  async function copyGameSeed() {
    const value = String(game.seed >>> 0);
    const button = $("btn-copy-seed");
    try {
      await navigator.clipboard.writeText(value);
      if (button) {
        button.textContent = "✓";
        setTimeout(() => { if (button.isConnected) button.textContent = "⧉"; }, 1200);
      }
      SFX.play("click");
    } catch (e) {
      const code = $("menu-seed");
      if (!code) return;
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(code);
      selection.removeAllRanges();
      selection.addRange(range);
    }
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

  function setYieldLens(on) {
    if (!rend) return;
    rend.showYields = on;
    rend.dirty = true;
    const button = $("btn-yields");
    button.classList.toggle("active", on);
    button.setAttribute("aria-pressed", on ? "true" : "false");
    button.setAttribute("aria-label", on ? "Hide tile yields" : "Show tile yields");
    button.title = `${on ? "Hide" : "Show"} tile yields (Y)`;
  }

  function applyMapPreferences() {
    setYieldLens(localStorage.getItem("balkan-civ-yields") === "1");
  }

  function toggleYieldLens() {
    const on = !rend.showYields;
    localStorage.setItem("balkan-civ-yields", on ? "1" : "0");
    setYieldLens(on);
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
      E.push({ cat: "Units", name: u.name, icon: "", unitKey: key,
        tags: key.toLowerCase() + (u.naval ? " naval ship fleet" : ""),
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
      for (const [uk, u] of Object.entries(UNITS)) if (u.tech === key) unlocks.push(u.name);
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
      const scope = pr.domain === "naval" ? "Naval units only."
        : pr.domain === "land" ? (pr.melee ? "Land melee units only." : "Land units only.")
        : "Available to all military units.";
      E.push({ cat: "Promotions", name: pr.name, icon: pr.icon, tags: "promotion " + pk.toLowerCase(),
        html: `<p>${pr.desc}</p><p class="dim">${scope} Chosen when a unit gains a level.</p>` });
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
    // Core systems
    E.push({ cat: "Mechanics", name: "Trade Routes", icon: "🐫", tags: "trade route caravan gold commerce",
      html: `<p>Build a Caravan and send it from one of your cities to a peaceful city within ${TRADE.maxDist} hexes. A route lasts ${TRADE.duration} turns and earns more gold over longer distances, with a bonus for foreign trade.</p><p class="dim">Hostile units can plunder the route path for ${TRADE.plunderGold} gold. A blockade at either endpoint suspends its income without destroying it.</p>` });
    E.push({ cat: "Mechanics", name: "Road Networks", icon: "🛤️", tags: "road capital connection infrastructure worker movement gold",
      html: `<p>Roads coexist with Farms and Mines and reduce movement through their hex to one. A continuous road corridor through owned or neutral land connects another city to your capital.</p><p>Each connected city earns <b>${INFRASTRUCTURE.connectionBaseGold} base gold plus 1 gold per ${INFRASTRUCTURE.populationPerGold} population</b> every turn. Connected segments are drawn in ochre; disconnected roads remain brown. A foreign border severs the link even when the road remains.</p>` });
    E.push({ cat: "Mechanics", name: "River Corridors", icon: "💧", tags: "river fresh water city settlement tile yield gold food map",
      html: `<p>Seeded rivers descend from inland highlands, may merge into tributaries, and always reach the coast. A river tile earns <b>+${RIVERS.tileGold} gold</b> when worked, while a city founded directly on a river gains <b>+${RIVERS.cityFood} food</b> every turn.</p><p class="dim">Farms, Mines, and Roads can coexist with a river. Roads are drawn above the water as bridges. The map editor can paint or clear river corridors on any passable land tile.</p>` });
    E.push({ cat: "Mechanics", name: "City Development", icon: "🏙️", tags: "city skyline era population walls religion factory wonder architecture",
      html: `<p>City architecture advances through the <b>${CITY_ART.STAGES.map(stage => stage.name).join(", ")}</b> eras. A denser skyline represents population growth, while Walls and Castles add fortifications, religious buildings add a dome, industrial buildings add factories and chimneys, and a completed wonder adds a gold landmark.</p><p class="dim">A rival city outside current vision uses a redacted settlement silhouette and hides live population, religion, damage, and construction until it is seen again.</p>` });
    E.push({ cat: "Mechanics", name: "Naval Blockades", icon: "⚓", tags: "naval blockade port pressure trade repair coastal gold",
      html: `<p>Warships within ${BLOCKADE.radius} hex of an enemy coastal city exert pressure based on combat strength, health, and level. If hostile pressure exceeds the nearby defending fleet, the port is blockaded.</p><p><b>Effects:</b> city gold is reduced by ${Math.round((1 - BLOCKADE.cityGoldMultiplier) * 100)}%, endpoint trade routes are suspended, and city repairs stop. The city can still bombard attackers; move enough friendly naval strength beside it to break the blockade immediately.</p>` });
    E.push({ cat: "Mechanics", name: "Fleet Logistics", icon: "⚓", tags: "naval fleet supply port logistics attrition range repair",
      html: `<p>Owned coastal cities project supply through connected water: ${NAVAL_SUPPLY.baseRange} hexes initially, ${NAVAL_SUPPLY.compassRange} with Compass, and ${NAVAL_SUPPLY.steamRange} with Steam Power. Land barriers block this coverage, making forward ports strategically important.</p><p>Warships may operate beyond supply for ${NAVAL_SUPPLY.graceTurns} turns. After that they suffer <b>${NAVAL_SUPPLY.attritionDamage} damage per turn</b>, fight ${Math.round((1 - NAVAL_SUPPLY.combatMultiplier) * 100)}% weaker, exert less blockade pressure, and cannot repair until they return to supply. AI fleets retreat to a friendly port and recover before resuming operations.</p>` });
    E.push({ cat: "Mechanics", name: "Tactical Formations", icon: "⚔️", tags: "combat tactics zone control zoc flank support formation surround",
      html: `<p>Land melee units at war control every adjacent land hex. Entering controlled ground ends the moving unit's remaining movement; reachable controlled hexes are outlined in amber when the controlling formation is visible. A hidden formation can still halt an advance when it is revealed.</p><p>Land melee attacks gain <b>+${Math.round(TACTICS.flankPerSupport * 100)}% strength</b> for each other friendly land melee unit adjacent to the target, capped at <b>+${Math.round(TACTICS.maxFlank * 100)}%</b>. Ranged, naval, and embarked units neither exert land control nor provide flanking support.</p>` });
    // Civilizations (with all their leaders)
    for (const id of CIV_IDS) {
      const civ = CIVS[id];
      const uu = UNITS[civ.uu];
      const leaders = civ.leaders.map(L => `<p><b>${L.leader}</b> — <i>${L.trait}</i>: ${L.traitDesc}</p>`).join("");
      E.push({ cat: "Civilizations", name: civ.name, icon: "", unitKey: civ.uu,
        tags: id.toLowerCase() + " " + civ.leaders.map(L => L.leader.toLowerCase()).join(" "),
        html: `<p><b>${uu.name}</b> — ${uu.blurb}</p><div class="dim">Leaders:</div>${leaders}` });
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
    const cats = ["All", "Units", "Buildings", "Wonders", "Techs", "Policies", "Promotions", "Mechanics", "Religion", "Civilizations", "Victory"];
    $("pedia-tabs").innerHTML = cats.map(c =>
      `<button role="tab" aria-selected="${c === pediaCat}" tabindex="${c === pediaCat ? 0 : -1}"
        class="pedia-tab${c === pediaCat ? " active" : ""}" data-cat="${c}">${c}</button>`).join("");
    $("pedia-tabs").querySelectorAll("button").forEach(b => b.onclick = () => { pediaCat = b.dataset.cat; renderPedia(); });
    if (initialQuery !== undefined) $("pedia-search").value = initialQuery;
    renderPedia();
    setTimeout(() => $("pedia-search").focus(), 30);
  }

  function renderPedia() {
    const q = $("pedia-search").value.trim().toLowerCase();
    $("pedia-tabs").querySelectorAll("button").forEach(b => {
      const active = b.dataset.cat === pediaCat;
      b.classList.toggle("active", active);
      b.setAttribute("aria-selected", active ? "true" : "false");
      b.tabIndex = active ? 0 : -1;
    });
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
      const art = e.unitKey ? `<canvas class="pedia-unit-art" data-unit-art="${e.unitKey}"
        width="128" height="128" role="img" aria-label="${e.name} silhouette"></canvas>` : "";
      html += `<div class="pedia-entry ${e.unitKey ? "unit" : ""}">${art}<div class="pedia-entry-main">
        <div class="pedia-name">${e.icon ? `${e.icon} ` : ""}<b>${e.name}</b></div>${e.html}</div></div>`;
    }
    body.innerHTML = html;
    paintUnitArt(body);
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
    if (rend.selected && !game.units.includes(rend.selected)) rend.selected = null;
    refreshSelectionOverlays();
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
    if (pending.event) {
      const event = RANDOM_EVENTS[pending.event.key];
      items.push({ icon: event ? event.icon : "⚖️", label: "Resolve court event",
        hint: "Choose how your realm responds before the turn can advance.", act: showEventDecision });
    }
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
        act: () => { selectUnit(promoUnit); centerMapOn(promoUnit); } });
    const idleCity = pending.cities[0];
    if (idleCity)
      items.push({ icon: "🏙️", label: "Set production", tipKey: "founded",
        hint: "Choose what this city should build; early military and workers establish momentum.",
        act: () => { selectCity(idleCity); centerMapOn(idleCity); } });
    const fleetRisk = game.units.find(unit => unit.owner === v && unit.def.naval &&
      !game.navalSupply(unit).supplied && (unit.unsuppliedTurns || 0) >= NAVAL_SUPPLY.graceTurns);
    if (fleetRisk)
      items.push({ icon: "⚓", label: "Fleet needs supply",
        hint: "Return this ship to a friendly port before attrition destroys it.",
        act: () => { selectUnit(fleetRisk); centerMapOn(fleetRisk); } });
    const idleUnits = pending.units.filter(unit => !fleetRisk || unit.id !== fleetRisk.id);
    if (idleUnits.length)
      items.push({ icon: "🎖️", label: `${idleUnits.length} unit${idleUnits.length > 1 ? "s" : ""} to move`,
        act: () => { selectUnit(idleUnits[0]); centerMapOn(idleUnits[0]); } });
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
      body: "A unit has earned a <b>promotion</b>. Select it to choose a role-specific upgrade: land troops can prepare amphibious assaults, while fleets can specialize in boarding, bombardment, or navigation." },
    { key: "cityState", title: "City-states", when: () => [...game.players[game.viewer].met].some(i => game.players[i].isMinor),
      body: "You've met a <b>city-state</b>. Win its friendship with gold gifts or by completing its <b>quests</b> (open Diplomacy to see them) for bonuses to your empire." },
  ];

  // ---------------- World Congress ----------------
  let congressSeenTurn = -1;

  function maybeShowCongress() {
    if (!game || game.over || !game.congressDue || !game.congressDue()) return;
    if (!myTurn()) return;
    if (game.pendingEventFor(game.viewer) || game.pendingPeaceOffers(game.viewer).length) return;
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
    if (!myTurn()) return;
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
    if (!advisorEnabled() || !game || game.over || game.pendingEventFor(game.viewer) ||
        $("advisor").style.display === "block") return;
    if (!myTurn()) return;
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
    if (pending.event) return { kind: "event", target: pending.event };
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
      event: "Resolve Event", congress: "Cast Vote", production: "Choose Production", ready: "End Turn ⏵",
    };
    button.textContent = action.kind === "unit" ? `Next Unit (${action.count})` : labels[action.kind];
    button.dataset.state = action.kind;
    button.disabled = action.kind === "over" || action.kind === "waiting";
    button.title = action.kind === "ready" ? "Advance to the next turn"
      : action.kind === "event" ? "Choose how your court responds to the pending event"
      : action.kind === "unit" ? "Select the next unit that needs orders"
      : action.kind === "production" ? "Select a city that needs production"
      : action.kind === "research" ? "Choose a technology before ending the turn"
      : action.kind === "congress" ? "Cast your World Congress vote" : "";
  }

  function endTurn() {
    const action = pendingTurnAction();
    if (action.kind === "waiting" || action.kind === "over") return;
    if (action.kind === "event") { showEventDecision(); return; }
    if (action.kind === "research") { showTechScreen(); return; }
    if (action.kind === "congress") { congressSeenTurn = -1; maybeShowCongress(); return; }
    if (action.kind === "production") {
      selectCity(action.target); centerMapOn(action.target); return;
    }
    if (action.kind === "unit") {
      selectUnit(action.target); centerMapOn(action.target); return;
    }
    hideCombatPreview();
    undoInfo = null;
    SFX.play("turn");
    snapshotForRecap(); // capture state so the next turn can recap what changed
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
      if (myTurn() && !game.over) { cycleNextUnit(); showTurnPrompts(); }
      return;
    }
    if (game.humans > 1 && !game.over) {
      showHandoff();
      return;
    }
    refreshAll();
    if (!game.over) cycleNextUnit();
    showTurnPrompts();
  }

  function maybePromptFounding() {
    if (game.canFoundReligion(game.viewer) &&
        foundingPromptTurn !== game.turn * 10 + game.viewer) {
      foundingPromptTurn = game.turn * 10 + game.viewer;
      showFoundingModal();
      return true;
    }
    return false;
  }

  // hotseat: blackout screen between human turns
  function showHandoff() {
    const p = game.players[game.viewer];
    $("handoff-modal").style.display = "flex";
    $("handoff-body").innerHTML = `
      <h2>🔄 Pass the device</h2>
      <p style="font-size:18px;margin:14px 0"><span aria-hidden="true" style="display:inline-block;width:13px;height:13px;
      margin-right:7px;background:${p.civ.color};border:2px solid ${p.civ.color2};vertical-align:-1px"></span><b>Player ${game.viewer + 1}</b>
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
    if (home) centerMapOn(home);
    refreshAll();
    cycleNextUnit();
    showTurnPrompts();
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

  const MODAL_FOCUSABLE = [
    "button:not([disabled])", "a[href]", "input:not([disabled])", "select:not([disabled])",
    "textarea:not([disabled])", "[role='button'][tabindex]:not([tabindex='-1'])",
    "[role='tab'][tabindex]:not([tabindex='-1'])", "[tabindex]:not([tabindex='-1'])",
  ].join(",");
  const ESCAPE_DISMISSIBLE_MODALS = new Set([
    "empire-modal", "tech-modal", "diplo-modal", "religion-modal", "founding-modal",
    "spy-modal", "policy-modal", "pedia-modal", "congress-modal", "campaign-modal",
    "progress-modal", "settings-modal", "log-modal", "menu-modal",
  ]);
  const modalOpenState = new WeakMap();
  const modalFocusOrigins = new WeakMap();
  let modalStack = [];

  function modalIsOpen(modal) {
    return !!modal && getComputedStyle(modal).display !== "none";
  }

  function modalFocusables(modal) {
    return [...modal.querySelectorAll(MODAL_FOCUSABLE)].filter(el =>
      !el.hidden && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden");
  }

  function activeModal() {
    modalStack = modalStack.filter(modal => modalIsOpen(modal));
    return modalStack[modalStack.length - 1] || null;
  }

  function configureModalSemantics(modal) {
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    const box = modal.querySelector(".modal-box");
    if (box && !box.hasAttribute("tabindex")) box.tabIndex = -1;
    const heading = modal.querySelector("h1, h2, h3");
    if (heading) {
      if (!heading.id) heading.id = `${modal.id}-title`;
      modal.setAttribute("aria-labelledby", heading.id);
      modal.removeAttribute("aria-label");
    } else if (!modal.hasAttribute("aria-labelledby")) {
      const label = modal.id.replace(/-modal$/, "").replace(/-/g, " ");
      modal.setAttribute("aria-label", label.charAt(0).toUpperCase() + label.slice(1));
    }
  }

  function setModalIsolation() {
    const top = activeModal();
    for (const child of document.body.children) {
      if (child.tagName === "SCRIPT" || child.tagName === "STYLE") continue;
      if (top && child !== top) {
        child.inert = true;
        child.dataset.modalInert = "1";
      } else if (child.dataset.modalInert === "1") {
        child.inert = false;
        delete child.dataset.modalInert;
      }
    }
  }

  function canRestoreFocus(el) {
    return !!(el && el.isConnected && !el.closest("[inert]") && el.getClientRects().length &&
      getComputedStyle(el).visibility !== "hidden");
  }

  function focusIntoModal(modal) {
    if (!modal || activeModal() !== modal || modal.contains(document.activeElement)) return;
    const target = modal.querySelector("[autofocus], .event-choice:not([disabled])") ||
      modalFocusables(modal)[0] || modal.querySelector(".modal-box");
    if (target) target.focus({ preventScroll: true });
  }

  function syncModalState(modal) {
    configureModalSemantics(modal);
    const open = modalIsOpen(modal), wasOpen = modalOpenState.get(modal) === true;
    modal.setAttribute("aria-hidden", open ? "false" : "true");
    if (open === wasOpen) {
      if (open && !modal.contains(document.activeElement)) queueMicrotask(() => focusIntoModal(modal));
      return;
    }
    modalOpenState.set(modal, open);
    if (open) {
      modalFocusOrigins.set(modal, document.activeElement);
      modalStack = modalStack.filter(item => item !== modal);
      modalStack.push(modal);
      setModalIsolation();
      queueMicrotask(() => focusIntoModal(modal));
      return;
    }
    modalStack = modalStack.filter(item => item !== modal);
    setModalIsolation();
    const origin = modalFocusOrigins.get(modal);
    queueMicrotask(() => {
      const top = activeModal();
      if (top) { focusIntoModal(top); return; }
      const fallback = $("btn-endturn") || $("btn-start");
      const target = canRestoreFocus(origin) ? origin : (canRestoreFocus(fallback) ? fallback : null);
      if (target) target.focus({ preventScroll: true });
    });
  }

  function installModalAccessibility() {
    const modals = [...document.querySelectorAll(".modal")];
    for (const modal of modals) {
      configureModalSemantics(modal);
      modalOpenState.set(modal, modalIsOpen(modal));
      modal.setAttribute("aria-hidden", modalIsOpen(modal) ? "false" : "true");
    }
    const observer = new MutationObserver(records => {
      const changed = new Set(records.map(record => record.target.closest(".modal")).filter(Boolean));
      for (const modal of changed) syncModalState(modal);
    });
    for (const modal of modals) observer.observe(modal, { attributes: true, attributeFilter: ["style", "class"] });
  }

  function handleModalKeydown(e) {
    const modal = activeModal();
    if (!modal) return false;
    if (e.key === "Tab") {
      const focusable = modalFocusables(modal);
      if (!focusable.length) {
        e.preventDefault();
        modal.querySelector(".modal-box")?.focus({ preventScroll: true });
      } else if (!focusable.includes(document.activeElement)) {
        e.preventDefault();
        focusable[e.shiftKey ? focusable.length - 1 : 0].focus({ preventScroll: true });
      } else if (!e.shiftKey && document.activeElement === focusable[focusable.length - 1]) {
        e.preventDefault(); focusable[0].focus({ preventScroll: true });
      } else if (e.shiftKey && document.activeElement === focusable[0]) {
        e.preventDefault(); focusable[focusable.length - 1].focus({ preventScroll: true });
      }
      return true;
    }
    if (e.key === "Escape") {
      e.preventDefault();
      if (!modal.classList.contains("decision-modal") && ESCAPE_DISMISSIBLE_MODALS.has(modal.id))
        modal.style.display = "none";
      return true;
    }
    // Let focused controls process Space/Enter, but suppress all map and turn shortcuts.
    return true;
  }

  function bindInput() {
    installModalAccessibility();
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
    $("btn-center-map").onclick = centerMapHome;
    $("btn-rot-left").onclick = () => { if (rend.rotate) rend.rotate(-1); };
    $("btn-rot-right").onclick = () => { if (rend.rotate) rend.rotate(1); };

    // minimap click
    $("minimap").addEventListener("mousedown", (e) => {
      const rect = e.target.getBoundingClientRect();
      const c = Math.floor((e.clientX - rect.left) / rect.width * game.map.w);
      const r = Math.floor((e.clientY - rect.top) / rect.height * game.map.h);
      centerMapOn({ c, r });
    });

    window.addEventListener("keydown", (e) => {
      if (handleModalKeydown(e)) return;
      if ($("start-screen").style.display !== "none") return;
      // don't hijack keys while typing in a text field (search, net codes)
      const tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select") {
        if (e.key === "Escape") e.target.blur();
        return;
      }
      if (e.target.closest && e.target.closest("button, a, [role='button'], [role='tab']")) return;
      if (e.key === "Enter") { e.preventDefault(); endTurn(); }
      else if (e.key === "Home") { e.preventDefault(); centerMapHome(); }
      else if (e.key === "." || e.key === "n") cycleNextUnit();
      else if (e.key === "f" && rend.selected) {
        if (game.issueUnitOrder(rend.selected, "fortify", game.viewer)) {
          cycleNextUnit();
          refreshAll();
        }
      }
      else if (e.key === "Escape") {
        $("empire-modal").style.display = "none";
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
      } else if (e.key === "o") showEmpireScreen();
      else if (e.key === "t") showTechScreen();
      else if (e.key === "p") showPolicyScreen();
      else if (e.key === "?" || e.key === "/") { e.preventDefault(); showPediaScreen(); }
      else if (e.key === "d") showDiploScreen();
      else if (e.key === "r") showReligionScreen();
      else if (e.key === "e") showSpyScreen();
      else if (e.key === "v") showVictoryProgress();
      else if (e.key === "y") toggleYieldLens();
      else if ((e.key === "q" || e.key === "w") && rend.rotate) rend.rotate(e.key === "q" ? -1 : 1);
    });

    $("btn-endturn").onclick = endTurn;
    $("btn-empire").onclick = () => showEmpireScreen();
    $("stat-gold").onclick = () => showEmpireScreen("economy");
    $("btn-tech").onclick = showTechScreen;
    $("stat-sci").onclick = showTechScreen;
    $("btn-diplo").onclick = showDiploScreen;
    $("btn-religion").onclick = showReligionScreen;
    $("stat-faith").onclick = showReligionScreen;
    $("stat-culture").onclick = showPolicyScreen;
    $("stat-score").onclick = showVictoryProgress;
    $("btn-yields").onclick = toggleYieldLens;
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
      m.addEventListener("mousedown", (e) => {
        if (e.target === m && !m.classList.contains("decision-modal")) m.style.display = "none";
      });
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
    const site = (rend.settlementSites || []).find(s => s.c === c && s.r === r);
    if (site) {
      html += `<br><b class="site-rating ${site.tier}">${site.label} city site</b> · potential ${site.score}`;
      if (site.coverage < 100) html += ` <span class="dim">(${site.coverage}% surveyed)</span>`;
      if (!site.canFoundThisTurn) html += `<br><span class="dim">Movement uses the remaining action; settle next turn.</span>`;
    }
    if (t.ruin) html += ` · 🏺 Ancient Ruins`;
    if (game.campAt && game.campAt(c, r)) html += ` · 🏕️ Barbarian Camp`;
    // combat forecast when hovering a legal target of the selected unit
    const sel0 = rend.selected;
    if (sel0 && sel0.owner === game.viewer && game.knownEnemyZoneOfControl(sel0, c, r).length)
      html += `<br><b class="tactical-warning">Enemy zone of control · movement ends here</b>`;
    if (sel0 && sel0.owner === game.viewer && rend.attackable.some(([ac, ar]) => ac === c && ar === r)) {
      const f = game.predictAttack(sel0, c, r);
      if (f) {
        const kills = f.out[0] >= f.targetHp;
        html += `<br><b class="war">⚔ vs ${f.target}</b> (${f.targetHp} HP)<br>` +
          `You deal <b>${f.out[0]}–${f.out[1]}</b>${kills ? " — <b class='alert'>lethal!</b>" : ""}` +
          (f.back ? `<br>You take <b>${f.back[0]}–${f.back[1]}</b>` : "<br><span class='dim'>no counterattack</span>");
        if (f.flankBonus)
          html += `<br><b class="tactical-warning">Flanking support ${f.flankSupport} · +${Math.round(f.flankBonus * 100)}% strength</b>`;
      }
    } else if (sel0 && warTargetOwner(sel0, c, r) >= 0) {
      html += `<br><b class="war">⚔ Click to declare war on ${game.players[warTargetOwner(sel0, c, r)].civ.name}</b>`;
    }
    if (t.resource) html += ` · ${RESOURCE[t.resource].icon} ${RESOURCE[t.resource].name}${RESOURCE[t.resource].luxury ? " (luxury)" : ""}`;
    if (t.river) html += ` · 💧 River (+${RIVERS.tileGold} gold; river city +${RIVERS.cityFood} food)`;
    if (t.improvement) html += ` · ${IMPROVEMENT[t.improvement].icon} ${IMPROVEMENT[t.improvement].name}`;
    if (t.road) {
      const connected = game.roadNetwork(game.viewer).tiles.has(game.map.idx(c, r));
      html += ` · 🛤️ ${connected ? "Capital road network" : "Road"}`;
    }
    html += `<br><span class="dim">🍞${y.food} ⚙️${y.prod} 💰${y.gold}</span>`;
    if (t.owner !== -1) html += `<br><span style="color:${CIVS[game.players[t.owner].civId].color}">${CIVS[game.players[t.owner].civId].name} territory</span>`;
    const visLevel = game.players[game.viewer].visible[game.map.idx(c, r)];
    if (visLevel === 2) {
      for (const u of game.unitsAt(c, r)) {
        html += `<br>${u.def.name}${u.level ? " " + "⭐".repeat(u.level) : ""} (${CIVS[game.players[u.owner].civId].name}) HP ${u.hp}`;
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
    NET.on("state", (state, meta) => applyNetworkState(state, meta));
    NET.on("drop", () => {
      if (!NET.active) {
        refreshHostStatus();
        if (!NET.isHost && $("net-join-out"))
          $("net-join-out").innerHTML = `<span class="war">The host connection closed. Cancel and request a new invite.</span>`;
        return;
      }
      if (game) {
        try { localStorage.setItem("balkan-civ-save", game.serialize()); } catch (e) { /* storage full */ }
        selectUnit(null);
        closeCity();
        refreshAll();
      }
      netUpdateBanner();
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

  return { init, setCityFocus, setProduction, buyItem, closeCity, pickTech, diploAction, newGame,
    showFoundingModal, confirmFounding, buyMissionary, gift, assignSpy, beginHotseatTurn,
    hostAddSlot, hostConnect, hostStartOnline, joinCreateReply, cancelNetworkLobby, unqueue,
    saveSlot, loadSlot, exportSave, copyGameSeed, toMainMenu, toggleGraphics, showSettings: showSettingsModal,
    diploTrade, diploGift, diploPact, adoptPolicy, congressVote, congressAbstain,
    playChapter, resetCampaign, openCampaign, answerPeace, answerEvent, cancelProduction, buildNow,
    declareWarAndAttack, setEmpireTab, setEmpireCitySort, setEmpireUnitSort, empireSetFocus,
    empireJumpCity, empireJumpUnit,
    get game() { return game; }, get renderer() { return rend; } };
})();
