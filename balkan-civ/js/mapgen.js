// ============================================================
// Procedural map generation — a rugged "peninsula" landmass
// with seas at the edges, mountain spines, forests, resources
// ============================================================
"use strict";

function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Smooth value noise built from a coarse random grid
function makeNoise(rng, w, h, cell) {
  const gw = Math.ceil(w / cell) + 2, gh = Math.ceil(h / cell) + 2;
  const grid = [];
  for (let i = 0; i < gw * gh; i++) grid.push(rng());
  const at = (x, y) => grid[y * gw + x];
  const fade = (t) => t * t * (3 - 2 * t);
  return (x, y) => {
    const fx = x / cell, fy = y / cell;
    const x0 = Math.floor(fx), y0 = Math.floor(fy);
    const tx = fade(fx - x0), ty = fade(fy - y0);
    const a = at(x0, y0) * (1 - tx) + at(x0 + 1, y0) * tx;
    const b = at(x0, y0 + 1) * (1 - tx) + at(x0 + 1, y0 + 1) * tx;
    return a * (1 - ty) + b * ty;
  };
}

function generateMap(w, h, seed, mapType = "peninsula") {
  const rng = mulberry32(seed);
  const arch = mapType === "archipelago";
  // archipelago: finer noise -> many scattered landmasses
  const elevN1 = makeNoise(rng, w, h, arch ? 4 : 9);
  const elevN2 = makeNoise(rng, w, h, arch ? 3 : 4);
  const elevN3 = makeNoise(rng, w, h, 2);
  const moistN = makeNoise(rng, w, h, 6);

  const tiles = new Array(w * h);
  const idx = (c, r) => r * w + c;

  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      // radial falloff pushes water toward the map edges
      const nx = (c / (w - 1)) * 2 - 1;
      const ny = (r / (h - 1)) * 2 - 1;
      const edge = Math.max(Math.abs(nx), Math.abs(ny));
      const falloff = arch ? Math.pow(edge, 3.2) * 0.45 : Math.pow(edge, 2.6) * 0.85;
      let e = elevN1(c, r) * 0.55 + elevN2(c, r) * 0.3 + elevN3(c, r) * 0.15;
      e = e - falloff + (arch ? 0.02 : 0.12);

      const m = moistN(c, r);
      const sea = arch ? 0.47 : 0.32;
      let terrain, feature = null;
      if (e < sea) terrain = "OCEAN";
      else if (e > sea + 0.46) terrain = "MOUNTAIN";
      else if (e > sea + 0.30) terrain = "HILLS";
      else terrain = m > 0.5 ? "GRASSLAND" : "PLAINS";

      if ((terrain === "GRASSLAND" || terrain === "PLAINS" || terrain === "HILLS") &&
          m > 0.62 && rng() < 0.55 && terrain !== "HILLS") {
        feature = "FOREST";
      } else if (terrain === "HILLS" && m > 0.72 && rng() < 0.3) {
        feature = "FOREST";
      }

      tiles[idx(c, r)] = {
        c, r, terrain, feature, resource: null, ruin: false,
        improvement: null,           // FARM / MINE / ROAD
        owner: -1, city: null,       // city object occupying this tile
        workedBy: null,              // city id working this tile
      };
    }
  }

  // COAST = water adjacent to land
  for (let r = 0; r < h; r++) {
    for (let c = 0; c < w; c++) {
      const t = tiles[idx(c, r)];
      if (t.terrain !== "OCEAN") continue;
      for (const [nc, nr] of HEX.neighbors(c, r)) {
        if (nc < 0 || nr < 0 || nc >= w || nr >= h) continue;
        const n = tiles[idx(nc, nr)];
        if (n.terrain !== "OCEAN" && n.terrain !== "COAST") { t.terrain = "COAST"; break; }
      }
    }
  }

  // Flood-fill landmasses. Peninsula keeps only the largest; archipelago
  // keeps every island of a playable size and sinks the specks.
  const landId = new Int32Array(w * h).fill(-1);
  const blobSizes = [];
  let bestBlob = -1, bestSize = 0, blob = 0;
  for (let i = 0; i < w * h; i++) {
    const t = tiles[i];
    if (!TERRAIN[t.terrain].passable && t.terrain !== "MOUNTAIN") continue;
    if (landId[i] !== -1) continue;
    let size = 0;
    const stack = [i];
    landId[i] = blob;
    while (stack.length) {
      const j = stack.pop();
      size++;
      const tj = tiles[j];
      for (const [nc, nr] of HEX.neighbors(tj.c, tj.r)) {
        if (nc < 0 || nr < 0 || nc >= w || nr >= h) continue;
        const k = idx(nc, nr);
        const tk = tiles[k];
        const isLand = TERRAIN[tk.terrain].passable || tk.terrain === "MOUNTAIN";
        if (isLand && landId[k] === -1) { landId[k] = blob; stack.push(k); }
      }
    }
    blobSizes[blob] = size;
    if (size > bestSize) { bestSize = size; bestBlob = blob; }
    blob++;
  }
  for (let i = 0; i < w * h; i++) {
    const t = tiles[i];
    const isLand = TERRAIN[t.terrain].passable || t.terrain === "MOUNTAIN";
    if (!isLand) continue;
    const drown = arch ? blobSizes[landId[i]] < 5 : landId[i] !== bestBlob;
    if (drown) t.terrain = "COAST";
  }

  // Resources
  const resKeys = Object.keys(RESOURCE);
  for (let i = 0; i < w * h; i++) {
    const t = tiles[i];
    if (rng() > 0.12) continue;
    const candidates = resKeys.filter(k => RESOURCE[k].terrains.includes(t.terrain));
    if (candidates.length) t.resource = candidates[Math.floor(rng() * candidates.length)];
  }

  // Ancient ruins for explorers to plunder
  for (let i = 0; i < w * h; i++) {
    const t = tiles[i];
    if (TERRAIN[t.terrain].passable && !t.resource && rng() < 0.015) t.ruin = true;
  }

  // Mirror worlds: the right half reflects the left, for fair multiplayer
  if (mapType === "mirror") {
    for (let r = 0; r < h; r++) {
      for (let c = Math.ceil(w / 2); c < w; c++) {
        const s = tiles[idx(w - 1 - c, r)];
        const t = tiles[idx(c, r)];
        t.terrain = s.terrain === "COAST" ? "OCEAN" : s.terrain;
        t.feature = s.feature;
        t.resource = s.resource;
        t.ruin = s.ruin;
      }
    }
    // recompute coast across the seam
    for (const t of tiles) if (t.terrain === "COAST") t.terrain = "OCEAN";
    for (let r = 0; r < h; r++) {
      for (let c = 0; c < w; c++) {
        const t = tiles[idx(c, r)];
        if (t.terrain !== "OCEAN") continue;
        for (const [nc, nr] of HEX.neighbors(c, r)) {
          if (nc < 0 || nr < 0 || nc >= w || nr >= h) continue;
          const n = tiles[idx(nc, nr)];
          if (n.terrain !== "OCEAN" && n.terrain !== "COAST") { t.terrain = "COAST"; break; }
        }
      }
    }
  }

  return { w, h, tiles, idx, seed };
}

// Score a tile as a city site (used for start positions and AI settling)
function siteScore(map, c, r) {
  const t = map.tiles[map.idx(c, r)];
  if (!TERRAIN[t.terrain].passable || t.city) return -1;
  let score = 0, coastal = false;
  for (const [nc, nr] of HEX.ring(c, r, 2)) {
    if (nc < 0 || nr < 0 || nc >= map.w || nr >= map.h) continue;
    const n = map.tiles[map.idx(nc, nr)];
    const terr = TERRAIN[n.terrain];
    let y = terr.food * 1.4 + terr.prod + terr.gold * 0.6;
    if (n.feature) y += FEATURE[n.feature].prod;
    if (n.resource) { const rs = RESOURCE[n.resource]; y += rs.food * 1.4 + rs.prod + rs.gold * 0.6 + 2; }
    if (n.terrain === "COAST") coastal = true;
    if (n.owner !== -1) y = 0; // don't crowd others
    score += y;
  }
  if (coastal) score += 3;
  if (t.terrain === "HILLS") score += 2; // defensible
  return score;
}

// Pick spread-out starting positions
function pickStartPositions(map, count, rng) {
  let candidates = [];
  for (const minScore of [20, 8, 1]) {
    candidates = [];
    for (let r = 2; r < map.h - 2; r++) {
      for (let c = 2; c < map.w - 2; c++) {
        const s = siteScore(map, c, r);
        if (s > minScore) candidates.push({ c, r, s });
      }
    }
    if (candidates.length >= count * 3) break; // enough good land
  }
  candidates.sort((a, b) => b.s - a.s);
  const picked = [];
  for (const cand of candidates) {
    if (picked.length >= count) break;
    if (picked.every(p => HEX.distance(p.c, p.r, cand.c, cand.r) >= 9)) picked.push(cand);
  }
  // relax spacing if the map couldn't fit everyone
  let minDist = 8;
  while (picked.length < count && minDist > 3) {
    for (const cand of candidates) {
      if (picked.length >= count) break;
      if (picked.every(p => HEX.distance(p.c, p.r, cand.c, cand.r) >= minDist)) picked.push(cand);
    }
    minDist--;
  }
  return picked;
}
