// ============================================================
// Canvas renderer: map, fog of war, borders, units, cities
// ============================================================
"use strict";

// which two neighbour directions flank each hex corner
const CORNER_DIRS = [[0, 5], [4, 5], [3, 4], [2, 3], [1, 2], [0, 1]];

// deterministic per-tile brightness variation
function tileJitter(c, r) {
  let h = (c * 73856093) ^ (r * 19349663);
  h = (h ^ (h >> 13)) >>> 0;
  return ((h % 100) / 100 - 0.5) * 0.14; // -7%..+7%
}

const _shadeCache = {};
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
    this.attackable = [];        // [[c,r],...] attack highlights
    this.hoverTile = null;   // [c, r] under the cursor
    this.previewPath = null; // path preview for the selected unit
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

  centerOn(game, c, r) {
    const [x, y] = HEX.toPixel(c, r, this.size);
    this.cam.x = x - this.canvas.width / 2;
    this.cam.y = y - this.canvas.height / 2;
    this.dirty = true;
  }

  draw(game) {
    const ctx = this.ctx;
    const W = this.canvas.width, H = this.canvas.height;
    ctx.fillStyle = "#0d1b2a";
    ctx.fillRect(0, 0, W, H);
    const vis = game.players[game.viewer].visible;
    const s = this.size;

    // visible tile range
    for (let r = 0; r < game.map.h; r++) {
      for (let c = 0; c < game.map.w; c++) {
        const [sx, sy] = this.worldToScreen(c, r);
        if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
        const v = vis[game.map.idx(c, r)];
        if (v === 0) continue; // unseen
        const t = game.map.tiles[game.map.idx(c, r)];
        this.drawTile(ctx, game, t, sx, sy, s, v);
      }
    }

    // borders (drawn over tiles)
    for (let r = 0; r < game.map.h; r++) {
      for (let c = 0; c < game.map.w; c++) {
        const i = game.map.idx(c, r);
        if (vis[i] === 0) continue;
        const t = game.map.tiles[i];
        if (t.owner === -1) continue;
        const [sx, sy] = this.worldToScreen(c, r);
        if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
        this.drawBorder(ctx, game, t, sx, sy, s);
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

    // cities
    for (const city of game.cities) {
      const i = game.map.idx(city.c, city.r);
      if (vis[i] === 0) continue;
      const [sx, sy] = this.worldToScreen(city.c, city.r);
      if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
      this.drawCity(ctx, game, city, sx, sy, s);
    }

    // units (only on currently-visible tiles), with movement animation
    const nowMs = Date.now();
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
      if (sx < -2 * s || sy < -2 * s || sx > W + 2 * s || sy > H + 2 * s) continue;
      this.drawUnit(ctx, game, u, sx, sy, s);
    }

    // trade routes of the viewing player (dashed gold roads)
    for (const route of game.routes || []) {
      if (route.owner !== game.viewer) continue;
      ctx.save();
      ctx.strokeStyle = "rgba(241,196,15,0.5)";
      ctx.lineWidth = Math.max(1.5, s * 0.07);
      ctx.setLineDash([s * 0.2, s * 0.25]);
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
      const turns = Math.max(1, Math.ceil(this.previewPath.length / Math.max(1, this.selected.def.moves)));
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
      const age = (now - e.ts) / 1300;
      const [ex, ey] = this.worldToScreen(e.c, e.r);
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
      ctx.beginPath();
      ctx.arc(sx, sy, s * 0.62, 0, Math.PI * 2);
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 3;
      ctx.setLineDash([6, 4]);
      ctx.stroke();
      ctx.setLineDash([]);
    }
    if (this.selectedCity) {
      const [sx, sy] = this.worldToScreen(this.selectedCity.c, this.selectedCity.r);
      this.hexPath(ctx, sx, sy, s * 0.95);
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 3;
      ctx.stroke();
    }

    this.drawMinimap(game);
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

  drawTile(ctx, game, t, sx, sy, s, v) {
    const water = t.terrain === "OCEAN" || t.terrain === "COAST";
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
    ctx.fillStyle = shade(TERRAIN[t.terrain].color, water ? tileJitter(t.c, t.r) * 0.5 : tileJitter(t.c, t.r));
    ctx.fill();
    ctx.strokeStyle = water ? "rgba(0,0,0,0.08)" : "rgba(0,0,0,0.15)";
    ctx.lineWidth = 0.7;
    ctx.stroke();
    // gentle waves on some water tiles
    if (water && s > 12) {
      const h = ((t.c * 7 + t.r * 13) % 7);
      if (h < 2) {
        ctx.strokeStyle = "rgba(255,255,255,0.10)";
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
    }

    // feature / terrain decorations
    if (t.terrain === "MOUNTAIN") {
      ctx.fillStyle = "#8d8d93";
      ctx.beginPath();
      ctx.moveTo(sx - s * 0.5, sy + s * 0.4);
      ctx.lineTo(sx - s * 0.1, sy - s * 0.45);
      ctx.lineTo(sx + s * 0.25, sy + s * 0.4);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#b9b9c0";
      ctx.beginPath();
      ctx.moveTo(sx - s * 0.02, sy + s * 0.4);
      ctx.lineTo(sx + s * 0.3, sy - s * 0.3);
      ctx.lineTo(sx + s * 0.58, sy + s * 0.4);
      ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#f0f0f5";
      ctx.beginPath();
      ctx.moveTo(sx - s * 0.18, sy - s * 0.25);
      ctx.lineTo(sx - s * 0.1, sy - s * 0.45);
      ctx.lineTo(sx - s * 0.02, sy - s * 0.25);
      ctx.closePath(); ctx.fill();
    } else if (t.terrain === "HILLS") {
      ctx.strokeStyle = "rgba(60,50,30,0.5)";
      ctx.lineWidth = Math.max(1.5, s * 0.06);
      for (const dx of [-0.3, 0.15]) {
        ctx.beginPath();
        ctx.arc(sx + dx * s, sy + s * 0.15, s * 0.28, Math.PI, 0);
        ctx.stroke();
      }
    }
    if (t.feature === "FOREST") {
      ctx.fillStyle = FEATURE.FOREST.color;
      for (const [dx, dy] of [[-0.3, 0.1], [0.1, -0.15], [0.35, 0.2]]) {
        ctx.beginPath();
        ctx.moveTo(sx + dx * s - s * 0.2, sy + dy * s + s * 0.25);
        ctx.lineTo(sx + dx * s, sy + dy * s - s * 0.3);
        ctx.lineTo(sx + dx * s + s * 0.2, sy + dy * s + s * 0.25);
        ctx.closePath(); ctx.fill();
      }
    }
    if (t.improvement === "ROAD") {
      // connect toward neighbouring roads/cities
      ctx.strokeStyle = "rgba(90,60,30,0.85)";
      ctx.lineWidth = Math.max(2, s * 0.12);
      ctx.lineCap = "round";
      let drewAny = false;
      for (const [nc, nr] of HEX.neighbors(t.c, t.r)) {
        const n = game.tile(nc, nr);
        if (!n || (n.improvement !== "ROAD" && !n.city)) continue;
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
    } else if (t.improvement === "FARM") {
      ctx.strokeStyle = "rgba(240,220,120,0.75)";
      ctx.lineWidth = Math.max(1, s * 0.05);
      for (const dy of [-0.18, 0, 0.18]) {
        ctx.beginPath();
        ctx.moveTo(sx - s * 0.34, sy + dy * s + s * 0.28);
        ctx.lineTo(sx + s * 0.34, sy + dy * s + s * 0.28);
        ctx.stroke();
      }
    } else if (t.improvement === "MINE" && s > 14) {
      ctx.font = `${Math.floor(s * 0.45)}px serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("⛏️", sx + s * 0.45, sy + s * 0.4);
    }
    if (t.ruin && s > 12) {
      ctx.font = `${Math.floor(s * 0.6)}px serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("🏺", sx, sy + s * 0.05);
    }
    if (game.campAt && game.campAt(t.c, t.r) && s > 12) {
      ctx.font = `${Math.floor(s * 0.7)}px serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("🏕️", sx, sy + s * 0.05);
    }
    if (t.resource && s > 14) {
      ctx.font = `${Math.floor(s * 0.55)}px serif`;
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(RESOURCE[t.resource].icon, sx - s * 0.75, sy - s * 0.45);
    }

    // fog: explored but not visible
    if (v === 1) {
      this.hexPath(ctx, sx, sy, s + 0.5);
      ctx.fillStyle = "rgba(10,15,30,0.55)";
      ctx.fill();
    }
  }

  drawBorder(ctx, game, t, sx, sy, s) {
    const color = CIVS[game.players[t.owner].civId].color;
    const pts = HEX.corners(sx, sy, s * 0.96);
    ctx.strokeStyle = color;
    ctx.lineWidth = Math.max(2, s * 0.09);
    ctx.lineCap = "round";
    // draw only edges facing tiles NOT owned by same player
    HEX.neighbors(t.c, t.r).forEach(([nc, nr], dir) => {
      const n = game.tile ? game.tile(nc, nr) : null;
      if (n && n.owner === t.owner) return;
      // edge between corner dir and dir+1 (aligned with DIRS ordering below)
      const EDGE = [[5, 0], [4, 5], [3, 4], [2, 3], [1, 2], [0, 1]][dir];
      ctx.beginPath();
      ctx.moveTo(pts[EDGE[0]][0], pts[EDGE[0]][1]);
      ctx.lineTo(pts[EDGE[1]][0], pts[EDGE[1]][1]);
      ctx.stroke();
    });
    // faint fill
    this.hexPath(ctx, sx, sy, s);
    ctx.fillStyle = color + "18";
    ctx.fill();
  }

  drawCity(ctx, game, city, sx, sy, s) {
    const civ = CIVS[game.players[city.owner].civId];
    // city hex base
    this.hexPath(ctx, sx, sy, s * 0.8);
    ctx.fillStyle = "#3a3530";
    ctx.fill();
    // buildings silhouette
    ctx.fillStyle = "#d8cbb0";
    const bw = s * 0.22;
    for (const [dx, hMul] of [[-1.3, 0.5], [-0.4, 0.85], [0.5, 0.6]]) {
      ctx.fillRect(sx + dx * bw, sy - s * 0.35 * hMul, bw * 0.8, s * 0.35 * hMul + s * 0.25);
    }
    ctx.fillStyle = "#8a2f20";
    for (const [dx, hMul] of [[-1.3, 0.5], [-0.4, 0.85], [0.5, 0.6]]) {
      ctx.beginPath();
      ctx.moveTo(sx + dx * bw - bw * 0.15, sy - s * 0.35 * hMul);
      ctx.lineTo(sx + dx * bw + bw * 0.4, sy - s * 0.35 * hMul - s * 0.18);
      ctx.lineTo(sx + dx * bw + bw * 0.95, sy - s * 0.35 * hMul);
      ctx.closePath(); ctx.fill();
    }

    // banner
    const rel = city.religion !== null && game.religions[city.religion];
    const label = `${city.pop}  ${rel ? rel.icon + " " : ""}${city.name}${city.isCapital ? " ★" : ""}`;
    ctx.font = `bold ${Math.max(11, Math.floor(s * 0.34))}px 'Segoe UI', sans-serif`;
    const tw = ctx.measureText(label).width;
    const bx = sx - tw / 2 - 8, by = sy - s * 1.05, bh = Math.max(16, s * 0.46);
    ctx.fillStyle = "rgba(15,15,20,0.82)";
    ctx.beginPath();
    ctx.roundRect(bx, by - bh / 2, tw + 16, bh, 4);
    ctx.fill();
    ctx.strokeStyle = civ.color;
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = civ.color;
    ctx.fillRect(bx + 3, by - bh / 2 + 3, 5, bh - 6);
    ctx.fillStyle = "#fff";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(label, sx + 2, by + 1);

    // HP bar when damaged
    if (city.hp < city.maxHp) {
      const w = s * 1.4;
      ctx.fillStyle = "#222";
      ctx.fillRect(sx - w / 2, by + bh / 2 + 2, w, 4);
      ctx.fillStyle = "#e74c3c";
      ctx.fillRect(sx - w / 2, by + bh / 2 + 2, w * (city.hp / city.maxHp), 4);
    }
  }

  drawUnit(ctx, game, u, sx, sy, s) {
    const civ = CIVS[game.players[u.owner].civId];
    const rad = s * 0.42;
    const spent = u.owner === game.viewer && u.moves <= 0;
    if (spent) ctx.globalAlpha = 0.6;
    // shadow + disc
    ctx.beginPath();
    ctx.arc(sx, sy + 2, rad, 0, Math.PI * 2);
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    ctx.fill();
    ctx.beginPath();
    ctx.arc(sx, sy, rad, 0, Math.PI * 2);
    ctx.fillStyle = civ.color;
    ctx.fill();
    ctx.strokeStyle = u.owner === game.viewer ? "#fff" : civ.color2;
    ctx.lineWidth = 2;
    ctx.stroke();
    // icon
    ctx.font = `${Math.floor(rad * 1.1)}px serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(u.def.icon, sx, sy + 1);
    // HP bar
    if (u.hp < 100) {
      const w = rad * 2;
      ctx.fillStyle = "#222";
      ctx.fillRect(sx - rad, sy - rad - 7, w, 4);
      ctx.fillStyle = u.hp > 60 ? "#2ecc71" : u.hp > 30 ? "#f39c12" : "#e74c3c";
      ctx.fillRect(sx - rad, sy - rad - 7, w * (u.hp / 100), 4);
    }
    // fortified marker
    if (u.fortified) {
      ctx.font = `${Math.floor(rad * 0.8)}px serif`;
      ctx.fillText("🛡", sx + rad * 0.9, sy - rad * 0.9);
    }
    // embarked land unit rides a little boat
    if (game.isEmbarked(u)) {
      ctx.font = `${Math.floor(rad * 0.9)}px serif`;
      ctx.fillText("⛵", sx - rad * 0.9, sy - rad * 0.9);
    }
    // veteran pips
    if (u.level > 0) {
      ctx.fillStyle = "#f1c40f";
      for (let i = 0; i < u.level; i++) {
        ctx.beginPath();
        ctx.arc(sx - rad * 0.5 + i * rad * 0.5, sy + rad + 5, Math.max(1.6, rad * 0.12), 0, Math.PI * 2);
        ctx.fill();
      }
    }
    if (spent) ctx.globalAlpha = 1;
  }

  drawMinimap(game) {
    const m = this.mctx;
    const W = this.mini.width, H = this.mini.height;
    m.fillStyle = "#0d1b2a";
    m.fillRect(0, 0, W, H);
    const sx = W / game.map.w, sy = H / game.map.h;
    const vis = game.players[game.viewer].visible;
    for (const t of game.map.tiles) {
      const v = vis[game.map.idx(t.c, t.r)];
      if (!v) continue;
      let color = TERRAIN[t.terrain].color;
      if (t.owner !== -1) color = CIVS[game.players[t.owner].civId].color;
      m.fillStyle = color;
      m.globalAlpha = v === 1 ? 0.5 : 1;
      m.fillRect(t.c * sx, t.r * sy, Math.ceil(sx), Math.ceil(sy));
    }
    m.globalAlpha = 1;
    for (const c of game.cities) {
      if (!vis[game.map.idx(c.c, c.r)]) continue;
      m.fillStyle = "#fff";
      m.fillRect(c.c * sx - 1, c.r * sy - 1, 3, 3);
    }
    // camera viewport box
    const s = this.size;
    const hexW = s * Math.sqrt(3), hexH = s * 1.5;
    m.strokeStyle = "rgba(255,255,255,0.8)";
    m.lineWidth = 1;
    m.strokeRect(
      (this.cam.x / hexW) * sx, (this.cam.y / hexH) * sy,
      (this.canvas.width / hexW) * sx, (this.canvas.height / hexH) * sy);
  }
}
