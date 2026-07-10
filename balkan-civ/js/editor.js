// ============================================================
// Map editor: paint terrain, forests and resources, then save
// the map for use as a "Custom" world on the start screen.
// ============================================================
"use strict";

const EDITOR = (() => {
  const $ = (id) => document.getElementById(id);
  const W = 44, H = 34;
  let map = null, stub = null, erend = null;
  let brush = "GRASSLAND";
  let painting = false, panning = false, lastX = 0, lastY = 0;
  let inited = false;

  const PALETTE = [
    ["GRASSLAND", "🌿 Grass"], ["PLAINS", "🌾 Plains"], ["HILLS", "⛰ Hills"],
    ["MOUNTAIN", "🏔 Mountain"], ["OCEAN", "🌊 Sea"],
    ["FOREST", "🌲 Forest"], ["NO_FEATURE", "✂ Clear forest"],
    ["WHEAT", "🌾"], ["SHEEP", "🐑"], ["HORSES", "🐎"], ["IRON", "⚒️"],
    ["WINE", "🍇"], ["SILVER", "🪙"], ["OLIVES", "🫒"], ["SALT", "🧂"], ["FISH", "🐟"],
    ["NO_RESOURCE", "✂ Clear resource"],
  ];

  function makeStub() {
    stub = {
      map,
      tile: (c, r) => (c < 0 || r < 0 || c >= map.w || r >= map.h) ? null : map.tiles[map.idx(c, r)],
      players: [{ visible: new Uint8Array(map.w * map.h).fill(2), civId: "SERBIA" }],
      activeHuman: 0, viewer: 0,
      cities: [], units: [], effects: [], anims: [], religions: [],
      isEmbarked: () => false,
    };
  }

  function blankMap() {
    const tiles = [];
    for (let r = 0; r < H; r++) {
      for (let c = 0; c < W; c++) {
        tiles.push({ c, r, terrain: "OCEAN", feature: null, resource: null,
          improvement: null, owner: -1, city: null, workedBy: null });
      }
    }
    return { w: W, h: H, tiles, idx: (c, r) => r * W + c, seed: 0 };
  }

  function recomputeCoast() {
    for (const t of map.tiles) if (t.terrain === "COAST") t.terrain = "OCEAN";
    for (const t of map.tiles) {
      if (t.terrain !== "OCEAN") continue;
      for (const [nc, nr] of HEX.neighbors(t.c, t.r)) {
        if (nc < 0 || nr < 0 || nc >= map.w || nr >= map.h) continue;
        const n = map.tiles[map.idx(nc, nr)];
        if (n.terrain !== "OCEAN" && n.terrain !== "COAST") { t.terrain = "COAST"; break; }
      }
    }
  }

  function paint(c, r) {
    const t = stub.tile(c, r);
    if (!t) return;
    if (TERRAIN[brush]) {
      t.terrain = brush === "OCEAN" ? "OCEAN" : brush;
      if (brush === "OCEAN" || brush === "MOUNTAIN") { t.feature = null; t.resource = null; }
      if (t.resource && !RESOURCE[t.resource].terrains.includes(t.terrain)) t.resource = null;
      if (t.feature === "FOREST" && !["GRASSLAND", "PLAINS", "HILLS"].includes(t.terrain)) t.feature = null;
      recomputeCoast();
    } else if (brush === "FOREST") {
      if (["GRASSLAND", "PLAINS", "HILLS"].includes(t.terrain)) t.feature = "FOREST";
    } else if (brush === "NO_FEATURE") {
      t.feature = null;
    } else if (brush === "NO_RESOURCE") {
      t.resource = null;
    } else if (RESOURCE[brush]) {
      if (RESOURCE[brush].terrains.includes(t.terrain)) t.resource = brush;
    }
    erend.dirty = true;
    draw();
  }

  function draw() { erend.draw(stub); }

  function buildPalette() {
    const wrap = $("editor-palette");
    wrap.innerHTML = "";
    for (const [key, label] of PALETTE) {
      const b = document.createElement("button");
      b.textContent = label;
      b.className = "pal-btn" + (key === brush ? " sel" : "");
      b.onclick = () => {
        brush = key;
        wrap.querySelectorAll(".pal-btn").forEach(x => x.classList.remove("sel"));
        b.classList.add("sel");
      };
      wrap.appendChild(b);
    }
  }

  function bind() {
    const cv = $("editor-canvas");
    cv.addEventListener("mousedown", (e) => {
      if (e.button === 2) { panning = true; }
      else {
        painting = true;
        const rect = cv.getBoundingClientRect();
        const [c, r] = erend.screenToHex(e.clientX - rect.left, e.clientY - rect.top);
        paint(c, r);
      }
      lastX = e.clientX; lastY = e.clientY;
    });
    window.addEventListener("mousemove", (e) => {
      if (panning) {
        erend.cam.x -= e.clientX - lastX;
        erend.cam.y -= e.clientY - lastY;
        lastX = e.clientX; lastY = e.clientY;
        erend.dirty = true;
        draw();
      } else if (painting) {
        const rect = cv.getBoundingClientRect();
        const [c, r] = erend.screenToHex(e.clientX - rect.left, e.clientY - rect.top);
        paint(c, r);
      }
    });
    window.addEventListener("mouseup", () => { painting = false; panning = false; });
    cv.addEventListener("contextmenu", (e) => e.preventDefault());
    cv.addEventListener("wheel", (e) => {
      e.preventDefault();
      const oldSize = erend.size;
      erend.cam.zoom = Math.min(2.2, Math.max(0.45, erend.cam.zoom * (e.deltaY < 0 ? 1.12 : 0.89)));
      const scale = erend.size / oldSize;
      const rect = cv.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      erend.cam.x = (erend.cam.x + mx) * scale - mx;
      erend.cam.y = (erend.cam.y + my) * scale - my;
      draw();
    }, { passive: false });

    $("ed-random").onclick = () => {
      map = generateMap(W, H, Math.floor(Math.random() * 1e9),
        Math.random() < 0.5 ? "peninsula" : "archipelago");
      makeStub(); draw();
    };
    $("ed-clear").onclick = () => { map = blankMap(); makeStub(); draw(); };
    $("ed-save").onclick = () => {
      const land = map.tiles.filter(t => TERRAIN[t.terrain].passable).length;
      if (land < 120) { alert(`Only ${land} land tiles — paint more land (120+ recommended) so all civs fit.`); return; }
      const data = { w: map.w, h: map.h,
        tiles: map.tiles.map(t => ({ terrain: t.terrain, feature: t.feature, resource: t.resource })) };
      try { localStorage.setItem("balkan-civ-custommap", JSON.stringify(data)); } catch (e) { alert("Could not save map."); return; }
      alert("Map saved! Pick World: “Custom (from editor)” on the start screen.");
      exit();
    };
    $("ed-exit").onclick = exit;
  }

  function exit() {
    $("editor-screen").style.display = "none";
    $("start-screen").style.display = "flex";
    $("opt-custom").disabled = !localStorage.getItem("balkan-civ-custommap");
  }

  function open() {
    $("editor-screen").style.display = "flex";
    const cv = $("editor-canvas");
    cv.width = window.innerWidth;
    cv.height = window.innerHeight - 96;
    if (!inited) {
      erend = new Renderer(cv, $("editor-minimap"));
      buildPalette();
      bind();
      inited = true;
    }
    if (!map) {
      map = generateMap(W, H, Math.floor(Math.random() * 1e9), "peninsula");
      makeStub();
    }
    erend.centerOn(stub, Math.floor(W / 2), Math.floor(H / 2));
    draw();
  }

  return { open };
})();
