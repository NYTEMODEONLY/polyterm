// ============================================================
// Canvas renderer: map, fog of war, borders, units, cities
// ============================================================
"use strict";

// which two neighbour directions flank each hex corner
const CORNER_DIRS = [[0, 5], [4, 5], [3, 4], [2, 3], [1, 2], [0, 1]];
const EDGE_CORNERS = [[5, 0], [4, 5], [3, 4], [2, 3], [1, 2], [0, 1]];

// deterministic per-tile brightness variation
function tileJitter(c, r) {
  let h = (c * 73856093) ^ (r * 19349663);
  h = (h ^ (h >> 13)) >>> 0;
  return ((h % 100) / 100 - 0.5) * 0.14; // -7%..+7%
}

const _shadeCache = {};
const SETTLEMENT_COLORS_2D = {
  excellent: ["#8fd18a", "rgba(92,162,92,0.2)"],
  good: ["#e0c77d", "rgba(190,156,68,0.18)"],
  marginal: ["#a8b1ad", "rgba(125,139,134,0.14)"],
};
function shade(color, f) {
  const key = color + "|" + f.toFixed(2);
  if (_shadeCache[key]) return _shadeCache[key];
  const n = parseInt(color.slice(1), 16);
  let R = (n >> 16) & 255, G = (n >> 8) & 255, B = n & 255;
  R = Math.max(0, Math.min(255, Math.round(R * (1 + f))));
  G = Math.max(0, Math.min(255, Math.round(G * (1 + f))));
  B = Math.max(0, Math.min(255, Math.round(B * (1 + f))));
  const out = "#" + ((R << 16) | (G << 8) | B).toString(16).padStart(6, "0");
  _shadeCache[key] = out;
  return out;
}

function drawMapStar(ctx, x, y, radius, color = "#f4cf55") {
  ctx.save();
  ctx.beginPath();
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + i * Math.PI / 5;
    const r = i % 2 ? radius * 0.43 : radius;
    const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
    if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.fillStyle = color;
  ctx.fill();
  ctx.strokeStyle = "rgba(28,22,12,0.85)";
  ctx.lineWidth = Math.max(1, radius * 0.18);
  ctx.stroke();
  ctx.restore();
}

function drawMapShield(ctx, x, y, size) {
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(x, y - size * 0.55);
  ctx.lineTo(x + size * 0.46, y - size * 0.34);
  ctx.lineTo(x + size * 0.34, y + size * 0.24);
  ctx.quadraticCurveTo(x, y + size * 0.62, x - size * 0.34, y + size * 0.24);
  ctx.lineTo(x - size * 0.46, y - size * 0.34);
  ctx.closePath();
  ctx.fillStyle = "#e8dfc9";
  ctx.fill();
  ctx.strokeStyle = "#202724";
  ctx.lineWidth = Math.max(1.2, size * 0.15);
  ctx.stroke();
  ctx.restore();
}

function drawMapBoat(ctx, x, y, size) {
  ctx.save();
  ctx.fillStyle = "#e8dfc9";
  ctx.strokeStyle = "#202724";
  ctx.lineWidth = Math.max(1.2, size * 0.14);
  ctx.beginPath();
  ctx.moveTo(x - size * 0.58, y + size * 0.18);
  ctx.lineTo(x + size * 0.58, y + size * 0.18);
  ctx.lineTo(x + size * 0.34, y + size * 0.48);
  ctx.lineTo(x - size * 0.34, y + size * 0.48);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.beginPath();
  ctx.moveTo(x, y + size * 0.16);
  ctx.lineTo(x, y - size * 0.58);
  ctx.lineTo(x + size * 0.42, y - size * 0.05);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

const MINIMAP_ART = (() => {
  const layouts = new WeakMap();
  const blendCache = new Map();

  function blend(a, b, amount) {
    const key = `${a}|${b}|${amount}`;
    if (blendCache.has(key)) return blendCache.get(key);
    const an = parseInt(a.slice(1), 16), bn = parseInt(b.slice(1), 16);
    const channel = (shift) => Math.round(((an >> shift) & 255) * (1 - amount) + ((bn >> shift) & 255) * amount);
    const out = `#${((channel(16) << 16) | (channel(8) << 8) | channel(0)).toString(16).padStart(6, "0")}`;
    blendCache.set(key, out);
    return out;
  }

  function layout(map, W, H) {
    const cached = layouts.get(map);
    if (cached && cached.W === W && cached.H === H) return cached;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    const rx = Math.cos(Math.PI / 6), ry = 1;
    for (const t of map.tiles) {
      const [x, y] = HEX.toPixel(t.c, t.r, 1);
      minX = Math.min(minX, x - rx); maxX = Math.max(maxX, x + rx);
      minY = Math.min(minY, y - ry); maxY = Math.max(maxY, y + ry);
    }
    const padding = 6;
    const scale = Math.min((W - padding * 2) / Math.max(1, maxX - minX),
      (H - padding * 2) / Math.max(1, maxY - minY));
    const drawW = (maxX - minX) * scale, drawH = (maxY - minY) * scale;
    const ox = (W - drawW) / 2 - minX * scale;
    const oy = (H - drawH) / 2 - minY * scale;
    const tileX = new Float32Array(map.tiles.length);
    const tileY = new Float32Array(map.tiles.length);
    for (let i = 0; i < map.tiles.length; i++) {
      const t = map.tiles[i];
      const x = Math.sqrt(3) * (t.c + 0.5 * (t.r & 1));
      const y = 1.5 * t.r;
      tileX[i] = ox + x * scale;
      tileY[i] = oy + y * scale;
    }
    const result = {
      W, H, scale, ox, oy, tileX, tileY,
      worldToMini(x, y) { return [ox + x * scale, oy + y * scale]; },
      tileToMini(c, r) {
        const [x, y] = HEX.toPixel(c, r, 1);
        return [ox + x * scale, oy + y * scale];
      },
      miniToTile(x, y) {
        const [c, r] = HEX.fromPixel((x - ox) / scale, (y - oy) / scale, 1);
        return [Math.max(0, Math.min(map.w - 1, c)), Math.max(0, Math.min(map.h - 1, r))];
      },
    };
    layouts.set(map, result);
    return result;
  }

  function draw(ctx, canvas, game) {
    const W = canvas.width, H = canvas.height;
    const fit = layout(game.map, W, H);
    ctx.save();
    ctx.globalAlpha = 1;
    ctx.fillStyle = "#0d1b2a";
    ctx.fillRect(0, 0, W, H);
    const vis = game.players[game.viewer].visible;
    const cellW = Math.max(1.25, fit.scale * 1.80);
    const cellH = Math.max(1.25, fit.scale * 1.56);
    for (let i = 0; i < game.map.tiles.length; i++) {
      const t = game.map.tiles[i];
      const v = vis[i];
      let color = "#2a4045";
      if (v > 0) {
        color = TERRAIN[t.terrain].color;
        if (t.owner !== -1) color = blend(color, CIVS[game.players[t.owner].civId].color, 0.46);
      }
      const x = fit.tileX[i], y = fit.tileY[i];
      ctx.globalAlpha = v === 2 ? 1 : v === 1 ? 0.62 : 0.92;
      ctx.fillStyle = color;
      ctx.fillRect(Math.floor(x - cellW / 2), Math.floor(y - cellH / 2),
        Math.ceil(cellW), Math.ceil(cellH));
    }
    ctx.globalAlpha = 1;
    for (const city of game.cities) {
      if (!vis[game.map.idx(city.c, city.r)]) continue;
      const [x, y] = fit.tileToMini(city.c, city.r);
      ctx.beginPath();
      ctx.arc(x, y, Math.max(2, fit.scale * 0.78), 0, Math.PI * 2);
      ctx.fillStyle = CIVS[game.players[city.owner].civId].color;
      ctx.fill();
      ctx.strokeStyle = "#fff7df";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
    ctx.restore();
    return fit;
  }

  function viewport(ctx, fit, points) {
    if (!points || !points.every(Boolean)) return;
    const clamped = points.map(([x, y]) => [
      Math.max(1.5, Math.min(fit.W - 1.5, x)),
      Math.max(1.5, Math.min(fit.H - 1.5, y)),
    ]);
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, fit.W, fit.H);
    ctx.clip();
    ctx.beginPath();
    clamped.forEach(([x, y], i) => i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y));
    ctx.closePath();
    ctx.fillStyle = "rgba(255,255,255,0.055)";
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.92)";
    ctx.lineWidth = 1.25;
    ctx.stroke();
    ctx.restore();
  }

  return { layout, draw, viewport };
})();

class Renderer {
  constructor(canvas, minimap) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");
    this.mini = minimap;
    this.mctx = minimap.getContext("2d");
    this.cam = { x: 0, y: 0, zoom: 1 };
    this.hexSize = 34;
    this.selected = null;        // selected unit
    this.selectedCity = null;
    this.reachable = [];         // [[c,r],...] move highlights
    this.controlled = [];        // reachable tiles inside visible enemy ZOC
    this.attackable = [];        // [[c,r],...] attack highlights
    this.settlementSites = [];   // surveyed one-turn sites for a selected Settler
    this.hoverTile = null;   // [c, r] under the cursor
    this.previewPath = null; // path preview for the selected unit
    this.showYields = false;
    this.connectedRoads = new Set();
    this.foamAnimated = true;
    this.dirty = true;
  }

  get size() { return this.hexSize * this.cam.zoom; }

  worldToScreen(c, r) {
    const [x, y] = HEX.toPixel(c, r, this.size);
    return [x - this.cam.x + 30, y - this.cam.y + 30];
  }

  screenToHex(sx, sy) {
    return HEX.fromPixel(sx + this.cam.x - 30, sy + this.cam.y - 30, this.size);
  }

  centerOn(game, c, r, screenPoint = null) {
    const [x, y] = HEX.toPixel(c, r, this.size);
    const targetX = screenPoint?.x ?? this.canvas.width / 2;
    const targetY = screenPoint?.y ?? this.canvas.height / 2;
    this.cam.x = x + 30 - targetX;
    this.cam.y = y + 30 - targetY;
    this.dirty = true;
  }

  draw(game) {
    const ctx = this.ctx;
    const W = this.canvas.width, H = this.canvas.height;
    ctx.fillStyle = "#0d1b2a";
    ctx.fillRect(0, 0, W, H);
    const vis = game.players[game.viewer].visible;
    const s = this.size;
    const stepX = s * Math.sqrt(3), stepY = s * 1.5;
    this.connectedRoads = game.roadNetwork ? game.roadNetwork(game.viewer).tiles : new Set();

    // visible tile range
    for (let r = 0; r < game.map.h; r++) {
      const sy = stepY * r - this.cam.y + 30;
      const rowOffset = 0.5 * (r & 1);
      for (let c = 0; c < game.map.w; c++) {
        const sx = stepX * (c + rowOffset) - this.cam.x + 30;
        if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
        const v = vis[game.map.idx(c, r)];
        if (v === 0) continue; // unseen
        const t = game.map.tiles[game.map.idx(c, r)];
        this.drawTile(ctx, game, t, sx, sy, s, v);
      }
    }

    // borders (drawn over tiles)
    for (let r = 0; r < game.map.h; r++) {
      const sy = stepY * r - this.cam.y + 30;
      const rowOffset = 0.5 * (r & 1);
      for (let c = 0; c < game.map.w; c++) {
        const i = game.map.idx(c, r);
        if (vis[i] === 0) continue;
        const t = game.map.tiles[i];
        if (t.owner === -1) continue;
        const sx = stepX * (c + rowOffset) - this.cam.x + 30;
        if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
        this.drawBorder(ctx, game, t, sx, sy, s);
      }
    }

    // Strategic yield lens. Current visibility is required so an improvement
    // built inside the fog cannot leak information to the viewer.
    if (this.showYields && s >= 18) {
      const badgeSize = Math.max(12, Math.min(19, s * 0.44));
      for (const t of game.map.tiles) {
        if (vis[game.map.idx(t.c, t.r)] !== 2) continue;
        const [sx, sy] = this.worldToScreen(t.c, t.r);
        if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
        WORLD_ART.yields(ctx, game.tileYield(t), sx, sy + s * 0.47, badgeSize);
      }
    }

    // movement / attack highlights
    if (this.selected) {
      ctx.save();
      for (const [c, r] of this.reachable) {
        const [sx, sy] = this.worldToScreen(c, r);
        this.hexPath(ctx, sx, sy, s * 0.92);
        ctx.fillStyle = "rgba(255,255,255,0.16)";
        ctx.fill();
      }
      for (const [c, r] of this.controlled) {
        const [sx, sy] = this.worldToScreen(c, r);
        this.hexPath(ctx, sx, sy, s * 0.76);
        ctx.strokeStyle = "rgba(241,196,15,0.95)";
        ctx.lineWidth = Math.max(2, s * 0.07);
        ctx.setLineDash([Math.max(3, s * 0.12), Math.max(2, s * 0.08)]);
        ctx.stroke();
      }
      ctx.setLineDash([]);
      for (const [c, r] of this.attackable) {
        const [sx, sy] = this.worldToScreen(c, r);
        this.hexPath(ctx, sx, sy, s * 0.92);
        ctx.fillStyle = "rgba(231,76,60,0.35)";
        ctx.fill();
        ctx.strokeStyle = "rgba(231,76,60,0.9)";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
      ctx.restore();
    }

    // Surveyed city sites sit above movement fills but below pieces and cities.
    if (this.settlementSites.length) {
      ctx.save();
      for (const site of this.settlementSites) {
        const [sx, sy] = this.worldToScreen(site.c, site.r);
        if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
        const [stroke, fill] = SETTLEMENT_COLORS_2D[site.tier];
        ctx.globalAlpha = site.canFoundThisTurn ? 1 : 0.62;
        this.hexPath(ctx, sx, sy, s * 0.72);
        ctx.fillStyle = fill;
        ctx.fill();
        ctx.strokeStyle = stroke;
        ctx.lineWidth = Math.max(2, s * 0.075);
        ctx.setLineDash(site.canFoundThisTurn ? [] : [Math.max(3, s * 0.13), Math.max(2, s * 0.09)]);
        ctx.stroke();
      }
      ctx.restore();
    }

    if (this.selectedCity && this.selectedCity.owner === game.viewer) {
      ctx.save();
      for (const t of game.workedTiles(this.selectedCity)) {
        if (!vis[game.map.idx(t.c, t.r)]) continue;
        const [sx, sy] = this.worldToScreen(t.c, t.r);
        if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
        this.hexPath(ctx, sx, sy, s * 0.78);
        ctx.fillStyle = "rgba(240,216,144,0.1)";
        ctx.fill();
        ctx.strokeStyle = "rgba(240,216,144,0.86)";
        ctx.lineWidth = Math.max(1.5, s * 0.055);
        ctx.setLineDash([Math.max(2, s * 0.08), Math.max(2, s * 0.08)]);
        ctx.stroke();
      }
      ctx.restore();
    }

    // cities
    for (const city of game.cities) {
      const i = game.map.idx(city.c, city.r);
      if (vis[i] === 0) continue;
      const [sx, sy] = this.worldToScreen(city.c, city.r);
      if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
      this.drawCity(ctx, game, city, sx, sy, s);
    }

    // strike flashes on defenders
    const nowMs = Date.now();
    game.strikes = (game.strikes || []).filter(st => nowMs - st.ts < 450);
    for (const st of game.strikes) {
      if (!vis[game.map.idx(st.tc, st.tr)]) continue;
      const age = (nowMs - st.ts) / 450;
      const [fx, fy] = this.worldToScreen(st.tc, st.tr);
      this.hexPath(ctx, fx, fy, s * 0.92);
      ctx.fillStyle = `rgba(255,68,51,${(0.5 * (1 - age)).toFixed(3)})`;
      ctx.fill();
    }

    // units (only on currently-visible tiles), with movement animation
    const ANIM_HOP = 110; // ms per tile
    game.anims = game.anims.filter(a => nowMs - a.ts < (a.hops.length - 1) * ANIM_HOP + 80);
    for (const u of game.units) {
      const i = game.map.idx(u.c, u.r);
      if (u.owner !== game.viewer && vis[i] !== 2) continue;
      if (u.owner === game.viewer && vis[i] === 0) continue;
      let [sx, sy] = this.worldToScreen(u.c, u.r);
      const anim = game.anims.find(a => a.id === u.id);
      if (anim) {
        const prog = (nowMs - anim.ts) / ANIM_HOP;
        const total = anim.hops.length - 1;
        if (prog < total) {
          const seg = Math.floor(prog), f = prog - seg;
          const [x1, y1] = this.worldToScreen(anim.hops[seg][0], anim.hops[seg][1]);
          const [x2, y2] = this.worldToScreen(anim.hops[seg + 1][0], anim.hops[seg + 1][1]);
          sx = x1 + (x2 - x1) * f;
          sy = y1 + (y2 - y1) * f;
        }
      }
      // attacker lunges toward its target
      const strike = !this.reduceMotion && game.strikes.find(st => st.id === u.id);
      if (strike) {
        const f = Math.min(1, (nowMs - strike.ts) / 300);
        const k = Math.sin(f * Math.PI) * (strike.ranged ? 0.16 : 0.4);
        const [tx, ty] = this.worldToScreen(strike.tc, strike.tr);
        sx += (tx - sx) * k; sy += (ty - sy) * k;
      }
      if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
      this.drawUnit(ctx, game, u, sx, sy, s);
    }

    // trade routes of the viewing player (dashed gold roads)
    for (const route of game.routes || []) {
      if (route.owner !== game.viewer) continue;
      const suspended = !game.tradeRouteStatus(route).active;
      ctx.save();
      ctx.strokeStyle = suspended ? "rgba(222,104,75,0.72)" : "rgba(241,196,15,0.5)";
      ctx.lineWidth = Math.max(1.5, s * 0.07);
      ctx.setLineDash(suspended ? [s * 0.08, s * 0.18] : [s * 0.2, s * 0.25]);
      ctx.beginPath();
      route.path.forEach(([pc, pr], i) => {
        const [px, py] = this.worldToScreen(pc, pr);
        if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
      });
      ctx.stroke();
      ctx.restore();
    }

    // hover highlight + path preview
    if (this.hoverTile) {
      const [hc, hr] = this.hoverTile;
      if (game.tile(hc, hr) && game.players[game.viewer].visible[game.map.idx(hc, hr)]) {
        const [sx, sy] = this.worldToScreen(hc, hr);
        this.hexPath(ctx, sx, sy, s * 0.96);
        ctx.strokeStyle = "rgba(255,255,255,0.55)";
        ctx.lineWidth = 2;
        ctx.stroke();
      }
    }
    if (this.previewPath && this.previewPath.length && this.selected) {
      ctx.save();
      ctx.strokeStyle = "rgba(255,255,255,0.65)";
      ctx.lineWidth = Math.max(2, s * 0.09);
      ctx.setLineDash([s * 0.25, s * 0.2]);
      ctx.lineCap = "round";
      ctx.beginPath();
      let [px, py] = this.worldToScreen(this.selected.c, this.selected.r);
      ctx.moveTo(px, py);
      for (const [pc, pr] of this.previewPath) {
        [px, py] = this.worldToScreen(pc, pr);
        ctx.lineTo(px, py);
      }
      ctx.stroke();
      ctx.setLineDash([]);
      // destination dot + rough turn estimate
      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.beginPath();
      ctx.arc(px, py, Math.max(3, s * 0.12), 0, Math.PI * 2);
      ctx.fill();
      const turns = Math.max(1, Math.ceil(this.previewPath.length / Math.max(1, this.selected.maxMoves)));
      if (turns > 1) {
        ctx.fillStyle = "#fff";
        ctx.font = `bold ${Math.max(11, Math.floor(s * 0.35))}px sans-serif`;
        ctx.textAlign = "center";
        ctx.fillText(String(turns), px, py - s * 0.35);
      }
      ctx.restore();
    }

    // floating combat numbers
    const now = Date.now();
    game.effects = game.effects.filter(e => now - e.ts < 1300);
    for (const e of game.effects) {
      if (!vis[game.map.idx(e.c, e.r)]) continue; // don't reveal events in the unexplored world
      const age = (now - e.ts) / 1300;
      const [ex, ey] = this.worldToScreen(e.c, e.r);
      if (e.ring) {
        if (this.reduceMotion) continue;
        ctx.save();
        ctx.globalAlpha = (1 - age) * 0.8;
        ctx.strokeStyle = e.color;
        ctx.lineWidth = Math.max(2, s * 0.09);
        ctx.beginPath();
        ctx.arc(ex, ey, s * (0.2 + age * 1.1), 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();
        continue;
      }
      ctx.save();
      ctx.globalAlpha = 1 - age;
      ctx.fillStyle = e.color;
      ctx.strokeStyle = "rgba(0,0,0,0.8)";
      ctx.lineWidth = 3;
      ctx.font = `bold ${Math.max(13, Math.floor(s * 0.5))}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const yy = ey - s * 0.3 - age * s * 0.9;
      ctx.strokeText(e.text, ex, yy);
      ctx.fillText(e.text, ex, yy);
      ctx.restore();
    }

    // selection ring
    if (this.selected && game.units.includes(this.selected)) {
      const [sx, sy] = this.worldToScreen(this.selected.c, this.selected.r);
      const pulse = this.reduceMotion ? 0 : (Math.sin(Date.now() * 0.007) + 1) / 2;
      ctx.save();
      ctx.beginPath();
      ctx.ellipse(sx, sy + s * 0.22, s * (0.55 + pulse * 0.045), s * (0.28 + pulse * 0.025), 0, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(255,255,255,${this.reduceMotion ? 1 : 0.72 + pulse * 0.28})`;
      ctx.lineWidth = Math.max(3, s * 0.075);
      ctx.stroke();
      ctx.beginPath();
      ctx.ellipse(sx, sy + s * 0.22, s * 0.45, s * 0.21, 0, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(20,28,28,0.9)";
      ctx.lineWidth = Math.max(1.5, s * 0.035);
      ctx.stroke();
      ctx.restore();
    }
    if (this.selectedCity) {
      const [sx, sy] = this.worldToScreen(this.selectedCity.c, this.selectedCity.r);
      this.hexPath(ctx, sx, sy, s * 0.95);
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    this.drawMinimap(game);
    this._lastDraw = Date.now();
    this.dirty = false;
  }

  // Hex path with selected corners rounded (used to soften coastlines).
  smoothHexPath(ctx, cx, cy, size, rounded) {
    const pts = HEX.corners(cx, cy, size);
    const k = 0.42;
    const lerp = (a, b, f) => [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f];
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
      const prev = pts[(i + 5) % 6], cur = pts[i], next = pts[(i + 1) % 6];
      if (rounded[i]) {
        const p1 = lerp(cur, prev, k), p2 = lerp(cur, next, k);
        if (i === 0) ctx.moveTo(p1[0], p1[1]); else ctx.lineTo(p1[0], p1[1]);
        ctx.quadraticCurveTo(cur[0], cur[1], p2[0], p2[1]);
      } else {
        if (i === 0) ctx.moveTo(cur[0], cur[1]); else ctx.lineTo(cur[0], cur[1]);
      }
    }
    ctx.closePath();
  }

  hexPath(ctx, cx, cy, size) {
    const pts = HEX.corners(cx, cy, size);
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < 6; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
  }

  drawRiver(ctx, game, t, sx, sy, s, v) {
    const branches = RIVER_ART.branches(game, t);
    const paths = branches.map(branch => {
      const [nx, ny] = this.worldToScreen(branch.tile.c, branch.tile.r);
      const ex = (sx + nx) / 2, ey = (sy + ny) / 2;
      const dx = ex - sx, dy = ey - sy, len = Math.hypot(dx, dy) || 1;
      return { x1: sx, y1: sy, x2: ex, y2: ey,
        cx: (sx + ex) / 2 - dy / len * branch.bend * s,
        cy: (sy + ey) / 2 + dx / len * branch.bend * s };
    });
    if (!paths.length) {
      const [dx, dy] = RIVER_ART.stubVector(t);
      paths.push({ x1: sx - dx * s * 0.24, y1: sy - dy * s * 0.24,
        x2: sx + dx * s * 0.24, y2: sy + dy * s * 0.24,
        cx: sx - dy * s * 0.05, cy: sy + dx * s * 0.05 });
    }

    ctx.save();
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    for (const [width, color] of [
      [0.22, v === 1 ? "rgba(19,48,55,0.62)" : "rgba(20,57,67,0.92)"],
      [0.125, v === 1 ? "rgba(46,112,128,0.68)" : "rgba(71,174,202,0.98)"],
      [0.035, v === 1 ? "rgba(146,188,193,0.3)" : "rgba(197,239,241,0.62)"],
    ]) {
      ctx.strokeStyle = color;
      ctx.lineWidth = Math.max(1, s * width);
      for (const path of paths) {
        ctx.beginPath();
        ctx.moveTo(path.x1, path.y1);
        ctx.quadraticCurveTo(path.cx, path.cy, path.x2, path.y2);
        ctx.stroke();
      }
    }
    ctx.restore();
  }

  drawTile(ctx, game, t, sx, sy, s, v) {
    const water = t.terrain === "OCEAN" || t.terrain === "COAST";
    const waterNeighbors = water ? HEX.neighbors(t.c, t.r).reduce((count, [c, r]) => {
      const n = game.tile(c, r);
      return count + (n && (n.terrain === "OCEAN" || n.terrain === "COAST") ? 1 : 0);
    }, 0) : 0;
    // round the corners of land tiles that touch the sea
    let rounded = null;
    if (!water) {
      const neigh = HEX.neighbors(t.c, t.r);
      const wet = (d) => {
        const n = game.tile(neigh[d][0], neigh[d][1]);
        return !n || n.terrain === "OCEAN" || n.terrain === "COAST";
      };
      for (let i = 0; i < 6; i++) {
        if (wet(CORNER_DIRS[i][0]) || wet(CORNER_DIRS[i][1])) {
          if (!rounded) rounded = [false, false, false, false, false, false];
          rounded[i] = true;
        }
      }
    }
    if (rounded) {
      // fill the notch behind rounded corners with sea
      this.hexPath(ctx, sx, sy, s + 0.5);
      ctx.fillStyle = shade(TERRAIN.COAST.color, tileJitter(t.c, t.r) * 0.5);
      ctx.fill();
      this.smoothHexPath(ctx, sx, sy, s + 0.5, rounded);
    } else {
      this.hexPath(ctx, sx, sy, s + 0.5);
    }
    const variation = water
      ? tileJitter(t.c, t.r) * 0.12 + (t.terrain === "COAST"
        ? 0.035 + (6 - waterNeighbors) * 0.012
        : -0.025 - waterNeighbors * 0.004)
      : tileJitter(t.c, t.r);
    ctx.fillStyle = shade(TERRAIN[t.terrain].color, variation);
    ctx.fill();
    this.hexPath(ctx, sx, sy, s + 0.5);
    ctx.strokeStyle = water ? "rgba(4,39,58,0.008)" : "rgba(0,0,0,0.13)";
    ctx.lineWidth = water ? 0.3 : 0.7;
    ctx.stroke();
    // gentle waves on some water tiles
    if (water && s > 12) {
      const h = ((t.c * 7 + t.r * 13) % 7);
      if (h === 0) {
        ctx.strokeStyle = "rgba(255,255,255,0.075)";
        ctx.lineWidth = Math.max(1, s * 0.05);
        for (const [dx, dy] of h === 0 ? [[-0.25, -0.1], [0.1, 0.2]] : [[0.05, -0.2]]) {
          ctx.beginPath();
          ctx.arc(sx + dx * s, sy + dy * s + s * 0.15, s * 0.22, Math.PI * 1.15, Math.PI * 1.85);
          ctx.stroke();
        }
      }
    }
    // sunlit edge on land for a hint of relief
    if (!water) {
      const pts = HEX.corners(sx, sy, s * 0.98);
      ctx.strokeStyle = "rgba(255,255,240,0.07)";
      ctx.lineWidth = Math.max(1, s * 0.08);
      ctx.beginPath();
      ctx.moveTo(pts[3][0], pts[3][1]);
      ctx.lineTo(pts[4][0], pts[4][1]);
      ctx.lineTo(pts[5][0], pts[5][1]);
      ctx.stroke();

      // A narrow sand transition and animated broken foam line sit only on
      // true land/water borders. Reduce-motion removes the foam entirely.
      const edgePts = HEX.corners(sx, sy, s * 0.985);
      ctx.save();
      ctx.globalAlpha = v === 1 ? 0.55 : 1;
      HEX.neighbors(t.c, t.r).forEach(([nc, nr], dir) => {
        const n = game.tile(nc, nr);
        if (!n || (n.terrain !== "OCEAN" && n.terrain !== "COAST")) return;
        const edge = EDGE_CORNERS[dir];
        const p1 = edgePts[edge[0]], p2 = edgePts[edge[1]];
        ctx.beginPath();
        ctx.moveTo(p1[0], p1[1]);
        ctx.lineTo(p2[0], p2[1]);
        ctx.strokeStyle = t.terrain === "PLAINS" ? "rgba(225,196,119,0.78)" : "rgba(216,204,145,0.72)";
        ctx.lineWidth = Math.max(1.5, s * 0.055);
        ctx.stroke();
        if (!this.reduceMotion) {
          ctx.beginPath();
          ctx.moveTo(p1[0], p1[1]);
          ctx.lineTo(p2[0], p2[1]);
          ctx.strokeStyle = "rgba(231,248,239,0.72)";
          ctx.lineWidth = Math.max(1, s * 0.022);
          ctx.setLineDash([Math.max(3, s * 0.13), Math.max(3, s * 0.11)]);
          ctx.lineDashOffset = -Date.now() * 0.012;
          ctx.stroke();
          ctx.setLineDash([]);
        }
      });
      ctx.restore();
    }

    // feature / terrain decorations
    if (t.terrain === "MOUNTAIN") {
      ctx.fillStyle = "#777b7b";
      ctx.beginPath();
      ctx.moveTo(sx - s * 0.5, sy + s * 0.4);
      ctx.lineTo(sx - s * 0.1, sy - s * 0.45);
      ctx.lineTo(sx + s * 0.25, sy + s * 0.4);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#aeb3b0";
      ctx.beginPath();
      ctx.moveTo(sx - s * 0.02, sy + s * 0.4);
      ctx.lineTo(sx + s * 0.3, sy - s * 0.3);
      ctx.lineTo(sx + s * 0.58, sy + s * 0.4);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#5e6464";
      ctx.beginPath();
      ctx.moveTo(sx - s * 0.52, sy + s * 0.4);
      ctx.lineTo(sx - s * 0.29, sy - s * 0.05);
      ctx.lineTo(sx - s * 0.08, sy + s * 0.4);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#f0f0f5";
      ctx.beginPath();
      ctx.moveTo(sx - s * 0.18, sy - s * 0.25);
      ctx.lineTo(sx - s * 0.1, sy - s * 0.45);
      ctx.lineTo(sx - s * 0.02, sy - s * 0.25);
      ctx.closePath(); ctx.fill();
    } else if (t.terrain === "HILLS") {
      const tone = shade(TERRAIN.HILLS.color, tileJitter(t.c + 11, t.r + 7) - 0.08);
      for (const [dx, width, height, alpha] of [[-0.24, 0.46, 0.24, 0.78], [0.22, 0.38, 0.19, 0.58]]) {
        ctx.beginPath();
        ctx.moveTo(sx + (dx - width) * s, sy + s * 0.29);
        ctx.quadraticCurveTo(sx + dx * s, sy + (0.29 - height * 2) * s,
          sx + (dx + width) * s, sy + s * 0.29);
        ctx.quadraticCurveTo(sx + dx * s, sy + (0.29 + height * 0.34) * s,
          sx + (dx - width) * s, sy + s * 0.29);
        ctx.closePath();
        ctx.globalAlpha = alpha;
        ctx.fillStyle = tone;
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }
    if (t.feature === "FOREST") {
      const variants = [[-0.30, 0.13, 0.82], [0.05, -0.13, 1.08], [0.34, 0.18, 0.76]];
      for (let i = 0; i < variants.length; i++) {
        const [dx, dy, sc] = variants[(i + Math.abs((t.c * 5 + t.r * 3) % 3)) % 3];
        ctx.fillStyle = "rgba(91,61,35,0.9)";
        ctx.fillRect(sx + dx * s - s * 0.035 * sc, sy + dy * s + s * 0.08,
          s * 0.07 * sc, s * 0.24 * sc);
        ctx.fillStyle = shade(FEATURE.FOREST.color, (i - 1) * 0.11 + tileJitter(t.c + i, t.r - i) * 0.5);
        ctx.beginPath();
        ctx.moveTo(sx + dx * s - s * 0.19 * sc, sy + dy * s + s * 0.19 * sc);
        ctx.lineTo(sx + dx * s, sy + dy * s - s * 0.33 * sc);
        ctx.lineTo(sx + dx * s + s * 0.19 * sc, sy + dy * s + s * 0.19 * sc);
        ctx.closePath(); ctx.fill();
      }
    }
    if (t.river) this.drawRiver(ctx, game, t, sx, sy, s, v);
    if (t.road) {
      // connect toward neighbouring roads/cities
      const connected = this.connectedRoads.has(game.map.idx(t.c, t.r));
      ctx.strokeStyle = connected ? "rgba(181,125,55,0.96)" : "rgba(90,60,30,0.82)";
      ctx.lineWidth = Math.max(2, s * 0.12);
      ctx.lineCap = "round";
      let drewAny = false;
      for (const [nc, nr] of HEX.neighbors(t.c, t.r)) {
        const n = game.tile(nc, nr);
        if (!n || !game.players[game.viewer].visible[game.map.idx(nc, nr)] || (!n.road && !n.city)) continue;
        const [nx, ny] = this.worldToScreen(nc, nr);
        ctx.beginPath();
        ctx.moveTo(sx, sy);
        ctx.lineTo((sx + nx) / 2, (sy + ny) / 2);
        ctx.stroke();
        drewAny = true;
      }
      if (!drewAny) {
        ctx.beginPath();
        ctx.arc(sx, sy, s * 0.14, 0, Math.PI * 2);
        ctx.stroke();
      }
    }
    if (t.improvement === "FARM") {
      ctx.strokeStyle = "rgba(240,220,120,0.75)";
      ctx.lineWidth = Math.max(1, s * 0.05);
      for (const dy of [-0.18, 0, 0.18]) {
        ctx.beginPath();
        ctx.moveTo(sx - s * 0.34, sy + dy * s + s * 0.28);
        ctx.lineTo(sx + s * 0.34, sy + dy * s + s * 0.28);
        ctx.stroke();
      }
    } else if (t.improvement === "MINE" && s > 14) {
      WORLD_ART.site(ctx, "MINE", sx + s * 0.42, sy + s * 0.34, s * 0.62);
    }
    if (t.ruin && s > 12) {
      WORLD_ART.site(ctx, "RUIN", sx, sy + s * 0.06, s * 0.72);
    }
    if (game.campAt && game.campAt(t.c, t.r) && s > 12) {
      WORLD_ART.site(ctx, "CAMP", sx, sy + s * 0.05, s * 0.76);
    }
    if (t.resource && s > 14) {
      WORLD_ART.resource(ctx, t.resource, sx - s * 0.53, sy - s * 0.4, s * 0.58);
    }

    // fog: explored but not visible
    if (v === 1) {
      this.hexPath(ctx, sx, sy, s + 0.5);
      ctx.fillStyle = "rgba(38,53,54,0.38)";
      ctx.fill();
      this.hexPath(ctx, sx, sy, s * 0.91);
      ctx.strokeStyle = "rgba(151,168,159,0.08)";
      ctx.lineWidth = Math.max(1, s * 0.025);
      ctx.stroke();
    }
  }

  drawBorder(ctx, game, t, sx, sy, s) {
    const color = CIVS[game.players[t.owner].civId].color;
    const dim = game.players[game.viewer].visible[game.map.idx(t.c, t.r)] === 1;
    const pts = HEX.corners(sx, sy, s * 0.96);
    ctx.save();
    if (dim) ctx.globalAlpha = 0.52;
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(1.5, s * 0.055);
    ctx.lineCap = "round";
    // draw only edges facing tiles NOT owned by same player
    HEX.neighbors(t.c, t.r).forEach(([nc, nr], dir) => {
      const n = game.tile ? game.tile(nc, nr) : null;
      if (n && n.owner === t.owner) return;
      // edge between corner dir and dir+1 (aligned with DIRS ordering below)
      const EDGE = EDGE_CORNERS[dir];
      ctx.beginPath();
      ctx.moveTo(pts[EDGE[0]][0], pts[EDGE[0]][1]);
      ctx.lineTo(pts[EDGE[1]][0], pts[EDGE[1]][1]);
      ctx.stroke();
    });
    // faint fill
    this.hexPath(ctx, sx, sy, s);
    ctx.fillStyle = color + "12";
    ctx.fill();
    ctx.restore();
  }

  drawCity(ctx, game, city, sx, sy, s) {
    const player = game.players[city.owner];
    const civ = CIVS[player.civId];
    const visibility = game.players[game.viewer].visible[game.map.idx(city.c, city.r)];
    const seenNow = visibility === 2;
    const obscured = !seenNow && city.owner !== game.viewer;
    const appearance = CITY_ART.profile(city, player, obscured);
    // city hex base
    ctx.save();
    this.hexPath(ctx, sx, sy, s * 0.8);
    ctx.fillStyle = appearance.palette.ground;
    if (obscured) ctx.globalAlpha *= 0.58;
    ctx.fill();
    ctx.restore();
    CITY_ART.draw(ctx, appearance, sx, sy, s);

    // banner
    const reportDetails = city.owner === game.viewer || seenNow;
    const rel = reportDetails && city.religion !== null && game.religions[city.religion];
    const blockaded = (city.owner === game.viewer || seenNow) && game.cityBlockade(city).active;
    const label = `${blockaded ? "⚓ " : ""}${reportDetails ? city.pop : "?"}  ${rel ? rel.icon + " " : ""}${city.name}${city.isCapital ? " ★" : ""}`;
    ctx.font = `bold ${Math.max(11, Math.floor(s * 0.34))}px 'Segoe UI', sans-serif`;
    const tw = ctx.measureText(label).width;
    const bx = sx - tw / 2 - 8, by = sy - s * 1.05, bh = Math.max(16, s * 0.46);
    ctx.fillStyle = "rgba(15,15,20,0.82)";
    ctx.beginPath();
    ctx.roundRect(bx, by - bh / 2, tw + 16, bh, 4);
    ctx.fill();
    ctx.strokeStyle = blockaded ? "#de684b" : civ.color;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = blockaded ? "#de684b" : civ.color;
    ctx.fillRect(bx + 3, by - bh / 2 + 3, 5, bh - 6);
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, sx + 2, by + 1);

    // HP bar when damaged
    if (reportDetails && city.hp < city.maxHp) {
      const w = s * 1.4;
      ctx.fillStyle = "#222";
      ctx.fillRect(sx - w / 2, by + bh / 2 + 2, w, 4);
      ctx.fillStyle = "#e74c3c";
      ctx.fillRect(sx - w / 2, by + bh / 2 + 2, w * (city.hp / city.maxHp), 4);
    }
  }

  drawUnit(ctx, game, u, sx, sy, s) {
    const civ = CIVS[game.players[u.owner].civId];
    const baseX = s * 0.40, baseY = s * 0.18;
    const artSize = s * 0.70;
    const spent = u.owner === game.viewer && u.moves <= 0;
    ctx.save();
    if (spent) ctx.globalAlpha = 0.58;

    // A low, owner-coloured plinth grounds the piece without covering the tile.
    ctx.beginPath();
    ctx.ellipse(sx, sy + s * 0.25, baseX * 1.08, baseY * 1.12, 0, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0,0,0,0.44)";
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(sx, sy + s * 0.20, baseX, baseY, 0, 0, Math.PI * 2);
    ctx.fillStyle = civ.color;
    ctx.fill();
    ctx.strokeStyle = u.owner === game.viewer ? "#f7f0dc" : civ.color2;
    ctx.lineWidth = Math.max(2, s * 0.055);
    ctx.stroke();
    ctx.beginPath();
    ctx.ellipse(sx, sy + s * 0.19, baseX * 0.72, baseY * 0.62, 0, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(24,30,28,0.78)";
    ctx.fill();

    // Upright shared silhouette: dark offset gives it a readable edge at range.
    UNIT_ART.draw(ctx, u.def, sx + s * 0.022, sy - s * 0.075 + s * 0.022, artSize, "rgba(12,18,17,0.9)");
    UNIT_ART.draw(ctx, u.def, sx, sy - s * 0.075, artSize, "#f4ead3");

    // HP bar
    if (u.hp < 100) {
      const w = s * 0.82, h = Math.max(4, s * 0.075);
      const x = sx - w / 2, y = sy - s * 0.53;
      ctx.fillStyle = "rgba(16,20,19,0.94)";
      ctx.fillRect(x - 1, y - 1, w + 2, h + 2);
      ctx.fillStyle = u.hp > 60 ? "#2ecc71" : u.hp > 30 ? "#f39c12" : "#e74c3c";
      ctx.fillRect(x, y, w * (u.hp / 100), h);
    }
    if (u.owner === game.viewer && u.def.naval) {
      const supply = game.navalSupply(u);
      if (!supply.supplied) {
        const warning = supply.attritionActive ? "#d94f3d" : "#e7a447";
        ctx.beginPath();
        ctx.moveTo(sx - s * 0.39, sy - s * 0.43);
        ctx.lineTo(sx - s * 0.11, sy - s * 0.43);
        ctx.lineTo(sx - s * 0.39, sy - s * 0.15);
        ctx.closePath();
        ctx.fillStyle = warning;
        ctx.fill();
        ctx.fillStyle = "#17120c";
        ctx.font = `bold ${Math.max(8, Math.floor(s * 0.18))}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("!", sx - s * 0.30, sy - s * 0.34);
      }
    }
    if (u.fortified) drawMapShield(ctx, sx + s * 0.39, sy - s * 0.37, s * 0.23);
    if (game.isEmbarked(u)) drawMapBoat(ctx, sx - s * 0.39, sy - s * 0.37, s * 0.22);
    // Veteran stars are shape-coded and remain legible without colour.
    if (u.level > 0) {
      const gap = s * 0.15;
      for (let i = 0; i < Math.min(3, u.level); i++)
        drawMapStar(ctx, sx + (i - (Math.min(3, u.level) - 1) / 2) * gap, sy + s * 0.46, Math.max(3.2, s * 0.075));
    }
    ctx.restore();
  }

  drawMinimap(game) {
    const m = this.mctx;
    const s = this.size;
    const fit = MINIMAP_ART.draw(m, this.mini, game);
    const points = [[0, 0], [this.canvas.width, 0], [this.canvas.width, this.canvas.height],
      [0, this.canvas.height]].map(([x, y]) =>
      fit.worldToMini((x + this.cam.x - 30) / s, (y + this.cam.y - 30) / s));
    MINIMAP_ART.viewport(m, fit, points);
    this._miniLayout = fit;
  }

  minimapToHex(game, x, y) {
    const fit = this._miniLayout || MINIMAP_ART.layout(game.map, this.mini.width, this.mini.height);
    return fit.miniToTile(x, y);
  }
}
