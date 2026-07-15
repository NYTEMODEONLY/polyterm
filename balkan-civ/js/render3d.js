// ============================================================
// Three.js renderer: extruded hex terrain, sprite units, fog
// Implements the same interface as the 2D Renderer so ui.js
// can drive either one: cam {x,y,zoom}, size, selected,
// selectedCity, reachable, attackable, hoverTile, previewPath,
// dirty, centerOn(), screenToHex(), draw().
// ============================================================
"use strict";

// terrain surface heights in world units (1 hex = 34 units wide-ish)
const ELEV3D = { OCEAN: -7, COAST: -3, GRASSLAND: 2.4, PLAINS: 2.4, HILLS: 7, MOUNTAIN: 5 };
const SEA_Y = 0.5;          // translucent water surface
const WALL_BOTTOM = -9;     // hex prisms extend down to here
const SHROUD_Y = 29;        // fog canopy sits above terrain silhouettes

function isWater3D(t) { return t.terrain === "OCEAN" || t.terrain === "COAST"; }
function surfY3D(t) { return isWater3D(t) ? SEA_Y : ELEV3D[t.terrain]; }

class Renderer3D {
  static supported() {
    if (typeof THREE === "undefined") return false;
    try {
      const cv = document.createElement("canvas");
      return !!(cv.getContext("webgl2") || cv.getContext("webgl"));
    } catch (e) { return false; }
  }

  constructor(canvas, minimap) {
    this.canvas = canvas;
    this.mini = minimap;
    this.mctx = minimap.getContext("2d");
    this.cam = { x: 0, y: 0, zoom: 1.28, rot: 0 };
    this.hexSize = 34;
    this.selected = null;
    this.selectedCity = null;
    this.reachable = [];
    this.attackable = [];
    this.settlementSites = [];
    this.hoverTile = null;
    this.previewPath = null;
    this.showYields = false;
    this.dirty = true;

    this.three = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
    this.three.setClearColor(0x0a3442);
    this.three.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    // Three r147 ships in legacy colour mode; linear output avoids double-brightening
    // CSS-style colours while keeping the deliberately painted palette intact.
    this.three.outputEncoding = THREE.LinearEncoding;
    this.three.toneMapping = THREE.NoToneMapping;
    this.three.shadowMap.enabled = true;
    this.three.shadowMap.type = THREE.PCFSoftShadowMap;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0a3442);
    this.scene.fog = new THREE.Fog(0x17363d, 1100, 3000);
    this.camera = new THREE.PerspectiveCamera(45, 1, 5, 8000);
    this.pitch = 0.94; // radians above the horizon
    this.scene.add(new THREE.HemisphereLight(0xddebf0, 0x514734, 0.56));
    this.scene.add(new THREE.AmbientLight(0xffefd0, 0.24));
    this.sun = new THREE.DirectionalLight(0xffe6bc, 0.72);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(1024, 1024);
    this.sun.shadow.camera.near = 20;
    this.sun.shadow.camera.far = 4200;
    this.sun.shadow.camera.left = -1200;
    this.sun.shadow.camera.right = 1200;
    this.sun.shadow.camera.top = 1200;
    this.sun.shadow.camera.bottom = -1200;
    this.sun.shadow.bias = -0.0007;
    this.sun.position.set(900, 1500, 850);
    this.scene.add(this.sun);
    this.scene.add(this.sun.target);

    // static per-map groups (rebuilt when the map object changes)
    this.gTerrain = new THREE.Group();
    // per-state groups (rebuilt when fog / owners / improvements change)
    this.gShroud = new THREE.Group();
    this.gBorders = new THREE.Group();
    this.gImprov = new THREE.Group();
    this.gYields = new THREE.Group();
    // per-frame pooled objects
    this.gDyn = new THREE.Group();
    for (const g of [this.gTerrain, this.gShroud, this.gBorders, this.gImprov, this.gYields, this.gDyn]) this.scene.add(g);

    this._texCache = new Map();
    this._matFill = {
      move: new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.22, depthWrite: false }),
      atk: new THREE.MeshBasicMaterial({ color: 0xe74c3c, transparent: true, opacity: 0.4, depthWrite: false }),
    };
    this._matSite = {};
    for (const [tier, color] of Object.entries({ excellent: 0x8fd18a, good: 0xe0c77d, marginal: 0xa8b1ad })) {
      this._matSite[tier] = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.72,
        side: THREE.DoubleSide, depthWrite: false });
      this._matSite[`${tier}-wait`] = new THREE.MeshBasicMaterial({ color, transparent: true, opacity: 0.3,
        side: THREE.DoubleSide, depthWrite: false });
    }
    this._matWorked = new THREE.MeshBasicMaterial({ color: 0xf0d890, transparent: true, opacity: 0.62,
      side: THREE.DoubleSide, depthWrite: false });
    this._hexFillGeo = null;   // shared flat hexagon, built with map
    this._pool = { move: [], atk: [], site: [], worked: [], decor: [], fx: [], routes: [], flash: [], rings: [] };
    this._units = new Map();   // unit id -> sprite
    this._cities = new Map();  // city object -> group
    this._builtFor = null;     // map object the static geometry was built for
    this._visSnap = null;
    this._ownSnap = null;
    this._impHash = null;
    this._yieldShown = null;
    this._yieldHash = null;
    this._vw = 0; this._vh = 0;

    this._hover = null; this._selRing = null; this._citySel = null; this._preview = null;
  }

  get size() { return this.hexSize * this.cam.zoom; }

  centerOn(game, c, r) {
    const [x, y] = HEX.toPixel(c, r, this.size);
    this.cam.x = x - this.canvas.width / 2;
    this.cam.y = y - this.canvas.height / 2;
    this.dirty = true;
  }

  rotate(dir) {
    this.cam.rot = (this.cam.rot || 0) + dir * Math.PI / 16;
    this.dirty = true;
  }

  // camera target in world units, derived from the 2D camera model
  _target() {
    const z = this.cam.zoom;
    return [
      (this.cam.x + this.canvas.width / 2 - 30) / z,
      (this.cam.y + this.canvas.height / 2 - 30) / z,
    ];
  }

  _placeCamera() {
    const [tx, tz] = this._target();
    const dist = (this.canvas.height / this.cam.zoom) * 0.98 + 60;
    const rot = this.cam.rot || 0, p = this.pitch;
    this.camera.position.set(
      tx + Math.sin(rot) * Math.cos(p) * dist,
      Math.sin(p) * dist,
      tz + Math.cos(rot) * Math.cos(p) * dist);
    this.camera.lookAt(tx, 0, tz);
  }

  _rayAt(sx, sy) {
    this._placeCamera();
    const ndc = new THREE.Vector2(
      (sx / this.canvas.width) * 2 - 1,
      -(sy / this.canvas.height) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.setFromCamera(ndc, this.camera);
    return ray;
  }

  // Ray → ground point on the plane at height y (null if parallel).
  _groundPoint(ray, y) {
    const hit = new THREE.Vector3();
    return ray.ray.intersectPlane(new THREE.Plane(new THREE.Vector3(0, 1, 0), -y), hit) ? hit : null;
  }

  // Pick by testing elevation planes from highest to lowest and accepting
  // the first hex whose real surface matches that height — parallax-exact
  // for tile tops without raycasting the full terrain mesh.
  screenToHex(sx, sy) {
    const ray = this._rayAt(sx, sy);
    const game = this._game;
    if (game) {
      const vis = game.players[game.viewer].visible;
      const levels = [
        [SHROUD_Y, (t, v) => v === 0],                             // shroud canopy
        [ELEV3D.HILLS, (t, v) => v > 0 && t.terrain === "HILLS"],
        [ELEV3D.MOUNTAIN, (t, v) => v > 0 && t.terrain === "MOUNTAIN"],
        [2.4, (t, v) => v > 0 && !isWater3D(t) && t.terrain !== "HILLS" && t.terrain !== "MOUNTAIN"],
        [SEA_Y, (t, v) => v > 0 && isWater3D(t)],
      ];
      for (const [y, match] of levels) {
        const hit = this._groundPoint(ray, y);
        if (!hit) continue;
        const [c, r] = HEX.fromPixel(hit.x, hit.z, this.hexSize);
        const t = game.tile(c, r);
        if (t && match(t, vis[game.map.idx(c, r)])) return [c, r];
      }
    }
    const hit = this._groundPoint(ray, 2.4);
    if (!hit) return [-999, -999];
    return HEX.fromPixel(hit.x, hit.z, this.hexSize);
  }

  // ---------------- canvas-texture helpers ----------------
  _tex(key, w, h, drawFn) {
    let t = this._texCache.get(key);
    if (t) return t;
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    drawFn(cv.getContext("2d"), w, h);
    t = new THREE.CanvasTexture(cv);
    this._texCache.set(key, t);
    return t;
  }

  _waterTex() {
    return this._tex("water|painted-v2", 512, 512, (ctx, w, h) => {
      const grad = ctx.createLinearGradient(0, 0, w, h);
      grad.addColorStop(0, "#236f91");
      grad.addColorStop(0.55, "#185b7c");
      grad.addColorStop(1, "#0f4969");
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
      ctx.lineCap = "round";
      for (let y = 18; y < h; y += 29) {
        const offset = ((y * 17) % 37) - 18;
        for (let x = -50 + offset; x < w + 50; x += 92) {
          ctx.strokeStyle = y % 58 ? "rgba(222,246,242,0.13)" : "rgba(8,49,70,0.15)";
          ctx.lineWidth = y % 58 ? 2 : 3;
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.bezierCurveTo(x + 15, y - 5, x + 31, y + 5, x + 47, y);
          ctx.stroke();
        }
      }
      for (let i = 0; i < 180; i++) {
        const x = (i * 83) % w, y = (i * 149) % h;
        ctx.fillStyle = i % 3 ? "rgba(255,255,255,0.035)" : "rgba(0,28,48,0.045)";
        ctx.fillRect(x, y, 2, 2);
      }
    });
  }

  _worldTex(kind, key) {
    return this._tex(`world|${kind}|${key}`, 112, 112, (ctx) => {
      if (kind === "resource") WORLD_ART.resource(ctx, key, 56, 56, 94);
      else WORLD_ART.site(ctx, key, 56, 56, 96);
    });
  }

  _yieldTex(values) {
    const count = [values.food, values.prod, values.gold].filter(v => v > 0).length;
    const w = 16 + count * 58, h = 70;
    return this._tex(`yield|${values.food}|${values.prod}|${values.gold}`, w, h, (ctx) => {
      WORLD_ART.yields(ctx, values, w / 2, h / 2, 52);
    });
  }

  _textTex(text, color) {
    return this._tex(`t|${text}|${color}`, 256, 96, (ctx) => {
      ctx.font = "bold 56px sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.lineWidth = 9;
      ctx.strokeStyle = "rgba(0,0,0,0.85)";
      ctx.strokeText(text, 128, 50);
      ctx.fillStyle = color;
      ctx.fillText(text, 128, 50);
    });
  }

  _unitTex(u, game) {
    const civ = CIVS[game.players[u.owner].civId];
    const outline = u.owner === game.viewer ? "#ffffff" : civ.color2;
    const hpB = u.hp >= 100 ? 100 : Math.ceil(u.hp / 5) * 5;
    const spent = u.owner === game.viewer && u.moves <= 0;
    const emb = game.isEmbarked(u);
    const art = UNIT_ART.kind(u.def);
    const supply = u.owner === game.viewer && u.def.naval ? game.navalSupply(u) : null;
    const supplyStatus = !supply || supply.supplied ? 0 : supply.attritionActive ? 2 : 1;
    const key = `u|${art}|${civ.color}|${outline}|${hpB}|${u.level}|${u.fortified ? 1 : 0}|${emb ? 1 : 0}|${spent ? 1 : 0}|${supplyStatus}`;
    return this._tex(key, 128, 152, (ctx) => {
      if (spent) ctx.globalAlpha = 0.58;
      // Civ-style strategic badge: shadow, civ rim, parchment field.
      ctx.fillStyle = "rgba(0,0,0,0.42)";
      ctx.beginPath();
      ctx.ellipse(64, 90, 49, 42, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(64, 80, 47, 0, Math.PI * 2);
      ctx.fillStyle = "#171d1b";
      ctx.fill();
      ctx.beginPath();
      ctx.arc(64, 80, 43, 0, Math.PI * 2);
      ctx.fillStyle = civ.color;
      ctx.fill();
      ctx.lineWidth = 5;
      ctx.strokeStyle = outline;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(64, 80, 34, 0, Math.PI * 2);
      ctx.fillStyle = "#e8dfc9";
      ctx.fill();
      UNIT_ART.draw(ctx, u.def, 64, 81, 57, "#202724");
      // HP bar
      if (hpB < 100) {
        ctx.fillStyle = "#222";
        ctx.fillRect(20, 16, 88, 11);
        ctx.fillStyle = hpB > 60 ? "#2ecc71" : hpB > 30 ? "#f39c12" : "#e74c3c";
        ctx.fillRect(20, 16, 88 * hpB / 100, 11);
      }
      if (supplyStatus) {
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(11, 37); ctx.lineTo(42, 37); ctx.lineTo(11, 68); ctx.closePath();
        ctx.fillStyle = supplyStatus === 2 ? "#d94f3d" : "#e7a447";
        ctx.fill();
        ctx.fillStyle = "#17120c";
        ctx.font = "bold 22px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("!", 22, 48);
        ctx.restore();
      }
      // badges
      ctx.font = "30px serif";
      if (u.fortified) ctx.fillText("🛡", 110, 40);
      if (emb) ctx.fillText("⛵", 18, 40);
      // veteran pips
      ctx.fillStyle = "#f1c40f";
      for (let i = 0; i < u.level; i++) {
        ctx.beginPath();
        ctx.arc(46 + i * 18, 140, 7, 0, Math.PI * 2);
        ctx.fill();
      }
    });
  }

  _bannerTex(city, game) {
    const civ = CIVS[game.players[city.owner].civId];
    const rel = city.religion !== null && game.religions[city.religion];
    const seenNow = game.players[game.viewer].visible[game.map.idx(city.c, city.r)] === 2;
    const blockaded = (city.owner === game.viewer || seenNow) && game.cityBlockade(city).active;
    const label = `${blockaded ? "⚓ " : ""}${rel ? rel.icon + " " : ""}${city.name}${city.isCapital ? " ★" : ""}`;
    const hpB = city.hp >= city.maxHp ? 100 : Math.ceil(city.hp / city.maxHp * 20) * 5;
    const key = `b|${label}|${city.pop}|${civ.color}|${hpB}|${blockaded ? 1 : 0}`;
    let t = this._texCache.get(key);
    if (t) return t;
    const meas = document.createElement("canvas").getContext("2d");
    meas.font = "bold 30px 'Segoe UI', sans-serif";
    const tw = Math.ceil(meas.measureText(label).width);
    const w = tw + 82, h = 70;
    t = this._tex(key, w, h, (ctx) => {
      ctx.fillStyle = "rgba(5,10,11,0.93)";
      ctx.beginPath();
      ctx.roundRect(5, 5, w - 10, 49, 5);
      ctx.fill();
      ctx.lineWidth = 3;
      ctx.strokeStyle = blockaded ? "#de684b" : "#d5ba73";
      ctx.stroke();
      ctx.fillStyle = civ.color;
      ctx.fillRect(10, 10, w - 20, 5);
      ctx.beginPath();
      ctx.arc(25, 31, 17, 0, Math.PI * 2);
      ctx.fill();
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#f3e8c7";
      ctx.stroke();
      ctx.fillStyle = "#fff9e8";
      ctx.font = "bold 24px 'Segoe UI', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(String(city.pop), 25, 32);
      ctx.fillStyle = "#fff6df";
      ctx.font = "bold 30px 'Segoe UI', sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(label, w / 2 + 17, 34);
      if (hpB < 100) {
        ctx.fillStyle = "#222";
        ctx.fillRect(10, 59, w - 20, 8);
        ctx.fillStyle = "#e74c3c";
        ctx.fillRect(10, 59, (w - 20) * hpB / 100, 8);
      }
    });
    t.userData = { w, h };
    return t;
  }

  // ---------------- static geometry ----------------
  _corners(wx, wz, r) {
    const pts = [];
    for (let i = 0; i < 6; i++) {
      const a = Math.PI / 180 * (60 * i - 30);
      pts.push([wx + r * Math.cos(a), wz + r * Math.sin(a)]);
    }
    return pts;
  }

  _pushTri(pos, col, a, b, c, color) {
    pos.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]);
    col.push(color.r, color.g, color.b, color.r, color.g, color.b, color.r, color.g, color.b);
  }

  // fan a flat hexagon at height y
  _pushHexTop(pos, col, wx, wz, y, r, color) {
    const pts = this._corners(wx, wz, r);
    for (let i = 0; i < 6; i++) {
      const p1 = pts[i], p2 = pts[(i + 1) % 6];
      this._pushTri(pos, col, [wx, y, wz], [p2[0], y, p2[1]], [p1[0], y, p1[1]], color);
    }
  }

  _pushHexTopVaried(pos, col, wx, wz, y, r, color, seed) {
    const pts = this._corners(wx, wz, r);
    for (let i = 0; i < 6; i++) {
      const p1 = pts[i], p2 = pts[(i + 1) % 6];
      const f = 0.988 + (((seed * 19 + i * 23) % 7) / 500);
      this._pushTri(pos, col, [wx, y, wz], [p2[0], y, p2[1]], [p1[0], y, p1[1]], color.clone().multiplyScalar(f));
    }
  }

  _pushWall(pos, col, p1, p2, topY, botY, color) {
    const a = [p1[0], topY, p1[1]], b = [p2[0], topY, p2[1]];
    const c = [p2[0], botY, p2[1]], d = [p1[0], botY, p1[1]];
    this._pushTri(pos, col, a, b, c, color);
    this._pushTri(pos, col, a, c, d, color);
  }

  _pushCone(pos, col, wx, wz, baseY, topY, r, color, segs = 7) {
    const apex = [wx, topY, wz];
    for (let i = 0; i < segs; i++) {
      const a1 = Math.PI * 2 * i / segs, a2 = Math.PI * 2 * (i + 1) / segs;
      const p1 = [wx + r * Math.cos(a1), baseY, wz + r * Math.sin(a1)];
      const p2 = [wx + r * Math.cos(a2), baseY, wz + r * Math.sin(a2)];
      this._pushTri(pos, col, p1, p2, apex, color);
    }
  }

  _buildStatic(game) {
    // wipe everything tied to the previous map
    for (const g of [this.gTerrain, this.gShroud, this.gBorders, this.gImprov, this.gYields, this.gDyn]) {
      for (const ch of [...g.children]) {
        g.remove(ch);
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material && g === this.gYields) ch.material.dispose();
      }
    }
    this._units.clear(); this._cities.clear();
    this._pool = { move: [], atk: [], site: [], worked: [], decor: [], fx: [], routes: [], flash: [], rings: [] };
    this._hover = this._selRing = this._citySel = this._preview = null;
    this._visSnap = this._ownSnap = null;
    this._impHash = null;
    this._yieldShown = null;
    this._yieldHash = null;

    const S = this.hexSize, map = game.map;
    const jitterOf = (c, r) => {
      let h2 = (c * 73856093) ^ (r * 19349663);
      h2 = (h2 ^ (h2 >> 13)) >>> 0;
      return ((h2 % 100) / 100 - 0.5) * 0.14;
    };
    const pos = [], col = [];
    const waterPos = [], waterCol = [], shorePos = [], shoreCol = [];
    this._tileRange = new Array(map.tiles.length);
    const tmp = new THREE.Color();

    for (const t of map.tiles) {
      const start = pos.length / 3;
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const top = ELEV3D[t.terrain];
      const j = isWater3D(t) ? jitterOf(t.c, t.r) * 0.5 : jitterOf(t.c, t.r);
      tmp.set(TERRAIN[t.terrain].color).multiplyScalar(1 + j);
      const base = tmp.clone();
      if (!isWater3D(t)) base.multiplyScalar(0.72);
      const wall = base.clone().multiplyScalar(0.66);
      const pts = this._corners(wx, wz, S);

      this._pushHexTopVaried(pos, col, wx, wz, top, S, base, map.idx(t.c, t.r));
      // cliff walls only where the neighbour surface is lower (or off-map)
      HEX.neighbors(t.c, t.r).forEach(([nc, nr], dir) => {
        const n = game.tile(nc, nr);
        const nTop = n ? ELEV3D[n.terrain] : WALL_BOTTOM;
        if (nTop >= top) return;
        const E = [[5, 0], [4, 5], [3, 4], [2, 3], [1, 2], [0, 1]][dir];
        this._pushWall(pos, col, pts[E[0]], pts[E[1]], top, Math.max(nTop - 1, WALL_BOTTOM), wall);
      });

      if (t.terrain === "MOUNTAIN") {
        const rock = new THREE.Color("#8b8c87").multiplyScalar(1 + j);
        const snow = new THREE.Color("#f1f0e7");
        this._pushCone(pos, col, wx - S * 0.18, wz + S * 0.1, top, top + 21, S * 0.67, rock, 8);
        this._pushCone(pos, col, wx + S * 0.32, wz - S * 0.03, top, top + 13, S * 0.46, rock.clone().multiplyScalar(1.11), 7);
        this._pushCone(pos, col, wx - S * 0.18, wz + S * 0.1, top + 12.5, top + 21.2, S * 0.27, snow, 8);
      } else if (t.terrain === "HILLS") {
        // a stepped bump on top of the raised hex
        const bump = base.clone().multiplyScalar(0.92);
        const bpts = this._corners(wx + S * 0.08, wz + S * 0.05, S * 0.55);
        this._pushHexTop(pos, col, wx + S * 0.08, wz + S * 0.05, top + 3, S * 0.55, bump);
        for (let i = 0; i < 6; i++) this._pushWall(pos, col, bpts[i], bpts[(i + 1) % 6], top + 3, top, bump.clone().multiplyScalar(0.8));
      }
      if (t.feature === "FOREST") {
        const green = new THREE.Color(FEATURE.FOREST.color).multiplyScalar(1.55 + j * 0.7);
        for (const [dx, dz, sc, tone] of [[-0.34, 0.12, 0.92, 0.88], [0.06, -0.2, 1.22, 1.08], [0.34, 0.2, 0.82, 0.96], [0.02, 0.3, 0.74, 1.18]]) {
          this._pushCone(pos, col, wx + dx * S, wz + dz * S, top, top + S * 0.64 * sc, S * 0.25 * sc, green.clone().multiplyScalar(tone), 7);
        }
      }

      // Civ-style shallow water and a narrow sand ribbon at the land edge.
      if (t.terrain === "COAST") {
        const shallow = new THREE.Color("#4ca2b2").multiplyScalar(1 + j * 0.4);
        this._pushHexTopVaried(waterPos, waterCol, wx, wz, SEA_Y + 0.12, S, shallow, map.idx(t.c, t.r));
      }
      if (!isWater3D(t)) {
        const sand = new THREE.Color(t.terrain === "PLAINS" ? "#d1b874" : "#c9bb82");
        HEX.neighbors(t.c, t.r).forEach(([nc, nr], dir) => {
          const n = game.tile(nc, nr);
          if (!n || !isWater3D(n)) return;
          const E = [[5, 0], [4, 5], [3, 4], [2, 3], [1, 2], [0, 1]][dir];
          const p1 = pts[E[0]], p2 = pts[E[1]];
          const mx = (p1[0] + p2[0]) / 2, mz = (p1[1] + p2[1]) / 2;
          let ix = wx - mx, iz = wz - mz;
          const il = Math.hypot(ix, iz) || 1;
          ix = ix / il * S * 0.10; iz = iz / il * S * 0.10;
          const y = SEA_Y + 0.18;
          this._pushTri(shorePos, shoreCol, [p1[0], y, p1[1]], [p2[0], y, p2[1]], [p2[0] + ix, y, p2[1] + iz], sand);
          this._pushTri(shorePos, shoreCol, [p1[0], y, p1[1]], [p2[0] + ix, y, p2[1] + iz], [p1[0] + ix, y, p1[1] + iz], sand);
        });
      }
      this._tileRange[map.idx(t.c, t.r)] = [start, pos.length / 3 - start];
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    geo.computeVertexNormals();
    this._baseCol = Float32Array.from(col);
    this._terrainMesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.92, metalness: 0 }));
    this._terrainMesh.receiveShadow = true;
    this.gTerrain.add(this._terrainMesh);

    if (waterPos.length) {
      const waterGeo = new THREE.BufferGeometry();
      waterGeo.setAttribute("position", new THREE.Float32BufferAttribute(waterPos, 3));
      waterGeo.setAttribute("color", new THREE.Float32BufferAttribute(waterCol, 3));
      const shallows = new THREE.Mesh(waterGeo, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.55, depthWrite: false }));
      shallows.renderOrder = 1;
      this.gTerrain.add(shallows);
    }
    if (shorePos.length) {
      const shoreGeo = new THREE.BufferGeometry();
      shoreGeo.setAttribute("position", new THREE.Float32BufferAttribute(shorePos, 3));
      shoreGeo.setAttribute("color", new THREE.Float32BufferAttribute(shoreCol, 3));
      const shores = new THREE.Mesh(shoreGeo, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.88, depthWrite: false, side: THREE.DoubleSide }));
      shores.renderOrder = 2;
      this.gTerrain.add(shores);
    }

    // translucent sea surface over the whole map, gently wave-animated
    const [maxX] = HEX.toPixel(map.w, 0, S), [, maxZ] = HEX.toPixel(0, map.h, S);
    const waterTex = this._waterTex();
    waterTex.wrapS = waterTex.wrapT = THREE.RepeatWrapping;
    waterTex.repeat.set(Math.max(4, map.w / 5), Math.max(3, map.h / 5));
    const sea = new THREE.Mesh(
      new THREE.PlaneGeometry(maxX + S * 14, maxZ + S * 14, 48, 36),
      new THREE.MeshStandardMaterial({ map: waterTex, color: 0x4f92a4, roughness: 0.4, metalness: 0.02, transparent: true, opacity: 0.62, depthWrite: false }));
    sea.rotation.x = -Math.PI / 2;
    sea.position.set(maxX / 2 - S, SEA_Y, maxZ / 2 - S * 0.75);
    this.gTerrain.add(sea);
    this._sea = sea;
    this._center = new THREE.Vector3(maxX / 2, 0, maxZ / 2);

    // shared flat hexagon used by highlights / hover / shroud template
    const hpos = [], hcol = [];
    this._pushHexTop(hpos, hcol, 0, 0, 0, S * 0.92, new THREE.Color(0xffffff));
    this._hexFillGeo = new THREE.BufferGeometry();
    this._hexFillGeo.setAttribute("position", new THREE.Float32BufferAttribute(hpos, 3));

    this.sun.target.position.copy(this._center);
    this._builtFor = map;
  }

  // darken explored-but-fogged tiles, tint owned land toward the civ colour
  _recolor(game) {
    const vis = game.players[game.viewer].visible;
    const col = this._terrainMesh.geometry.getAttribute("color");
    const arr = col.array, base = this._baseCol;
    const tmp = new THREE.Color();
    for (let i = 0; i < game.map.tiles.length; i++) {
      const [start, count] = this._tileRange[i];
      const v = vis[i];
      const t = game.map.tiles[i];
      let f = v === 2 ? 1 : v === 1 ? 0.48 : 0.14;
      let tint = null;
      if (t.owner !== -1 && v > 0) tint = tmp.set(CIVS[game.players[t.owner].civId].color);
      for (let k = start * 3; k < (start + count) * 3; k += 3) {
        let r = base[k] * f, g = base[k + 1] * f, b = base[k + 2] * f;
        if (tint) { r += (tint.r - r) * 0.13; g += (tint.g - g) * 0.13; b += (tint.b - b) * 0.13; }
        arr[k] = r; arr[k + 1] = g; arr[k + 2] = b;
      }
    }
    col.needsUpdate = true;
  }

  // opaque dark prisms over unexplored tiles
  _rebuildShroud(game) {
    for (const ch of [...this.gShroud.children]) { this.gShroud.remove(ch); ch.geometry.dispose(); }
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    const pos = [], col = [];
    const dark = new THREE.Color(0x263b40);
    for (const t of game.map.tiles) {
      if (vis[game.map.idx(t.c, t.r)] !== 0) continue;
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const h = SHROUD_Y;
      const c = dark.clone().multiplyScalar(1 + (((t.c * 7 + t.r * 11) % 10) / 10 - 0.5) * 0.045);
      this._pushHexTop(pos, col, wx, wz, h, S * 1.002, c);
    }
    if (!pos.length) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    geo.computeVertexNormals();
    const shroud = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.97 }));
    this.gShroud.add(shroud);
  }

  _rebuildBorders(game) {
    for (const ch of [...this.gBorders.children]) { this.gBorders.remove(ch); ch.geometry.dispose(); }
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    const pos = [], col = [];
    const tmp = new THREE.Color();
    for (const t of game.map.tiles) {
      if (t.owner === -1) continue;
      const v = vis[game.map.idx(t.c, t.r)];
      if (v === 0) continue;
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const y = surfY3D(t) + 0.45;
      tmp.set(CIVS[game.players[t.owner].civId].color);
      if (v === 1) tmp.multiplyScalar(0.55);
      const pts = this._corners(wx, wz, S * 0.97);
      HEX.neighbors(t.c, t.r).forEach(([nc, nr], dir) => {
        const n = game.tile(nc, nr);
        if (n && n.owner === t.owner) return;
        const E = [[5, 0], [4, 5], [3, 4], [2, 3], [1, 2], [0, 1]][dir];
        const p1 = pts[E[0]], p2 = pts[E[1]];
        const mx = (p1[0] + p2[0]) / 2, mz = (p1[1] + p2[1]) / 2;
        let ix = wx - mx, iz = wz - mz;
        const il = Math.hypot(ix, iz) || 1;
        ix = ix / il * S * 0.22; iz = iz / il * S * 0.22;
        this._pushTri(pos, col, [p1[0], y, p1[1]], [p2[0], y, p2[1]], [p2[0] + ix, y, p2[1] + iz], tmp);
        this._pushTri(pos, col, [p1[0], y, p1[1]], [p2[0] + ix, y, p2[1] + iz], [p1[0] + ix, y, p1[1] + iz], tmp);
      });
    }
    if (!pos.length) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    this.gBorders.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })));
  }

  _rebuildImprovements(game) {
    for (const ch of [...this.gImprov.children]) { this.gImprov.remove(ch); ch.geometry.dispose(); }
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    const pos = [], col = [];
    const road = new THREE.Color("#5a3c1e"), farm = new THREE.Color("#f0dc78");
    const quad = (x1, z1, x2, z2, w, y, c) => {
      // strip of width w from (x1,z1) to (x2,z2) at height y
      let px = -(z2 - z1), pz = x2 - x1;
      const l = Math.hypot(px, pz) || 1;
      px = px / l * w / 2; pz = pz / l * w / 2;
      this._pushTri(pos, col, [x1 - px, y, z1 - pz], [x2 - px, y, z2 - pz], [x2 + px, y, z2 + pz], c);
      this._pushTri(pos, col, [x1 - px, y, z1 - pz], [x2 + px, y, z2 + pz], [x1 + px, y, z1 + pz], c);
    };
    for (const t of game.map.tiles) {
      if (!t.improvement) continue;
      const v = vis[game.map.idx(t.c, t.r)];
      if (v === 0) continue;
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const y = ELEV3D[t.terrain] + 0.3;
      if (t.improvement === "ROAD") {
        const c = v === 1 ? road.clone().multiplyScalar(0.6) : road;
        let any = false;
        for (const [nc, nr] of HEX.neighbors(t.c, t.r)) {
          const n = game.tile(nc, nr);
          if (!n || (n.improvement !== "ROAD" && !n.city)) continue;
          const [nx, nz] = HEX.toPixel(nc, nr, S);
          quad(wx, wz, (wx + nx) / 2, (wz + nz) / 2, S * 0.18, y, c);
          any = true;
        }
        if (!any) quad(wx - S * 0.15, wz, wx + S * 0.15, wz, S * 0.18, y, c);
      } else if (t.improvement === "FARM") {
        const c = v === 1 ? farm.clone().multiplyScalar(0.6) : farm;
        for (const dz of [-0.2, 0, 0.2]) {
          quad(wx - S * 0.34, wz + (dz + 0.26) * S, wx + S * 0.34, wz + (dz + 0.26) * S, S * 0.07, y, c);
        }
      }
    }
    if (!pos.length) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    this.gImprov.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide })));
  }

  _rebuildYields(game) {
    for (const ch of [...this.gYields.children]) {
      this.gYields.remove(ch);
      ch.material.dispose();
    }
    if (!this.showYields) return;
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    for (const t of game.map.tiles) {
      if (vis[game.map.idx(t.c, t.r)] !== 2) continue;
      const values = game.tileYield(t);
      const count = [values.food, values.prod, values.gold].filter(v => v > 0).length;
      if (!count) continue;
      const tex = this._yieldTex(values);
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const h = S * 0.48;
      const sp = new THREE.Sprite(new THREE.SpriteMaterial({
        map: tex, transparent: true, depthTest: false, depthWrite: false,
      }));
      sp.position.set(wx, surfY3D(t) + S * 0.48, wz + S * 0.36);
      sp.scale.set(h * (16 + count * 58) / 70, h, 1);
      sp.renderOrder = 3;
      this.gYields.add(sp);
    }
  }

  // ---------------- pooled dynamic objects ----------------
  _getPooled(pool, make) {
    for (const o of pool) if (!o.visible) { o.visible = true; return o; }
    const o = make();
    pool.push(o);
    this.gDyn.add(o);
    return o;
  }

  _hidePool(pool) { for (const o of pool) o.visible = false; }

  _spriteAt(pool, tex, wx, y, wz, w, h, opacity = 1) {
    const s = this._getPooled(pool, () => new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false })));
    s.material.map = tex;
    s.material.opacity = opacity;
    s.position.set(wx, y, wz);
    s.scale.set(w, h, 1);
    return s;
  }

  _syncCities(game) {
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    for (const [c, gr] of this._cities) {
      if (!game.cities.includes(c)) { this.gDyn.remove(gr); this._cities.delete(c); }
    }
    for (const city of game.cities) {
      const v = vis[game.map.idx(city.c, city.r)];
      let gr = this._cities.get(city);
      if (v === 0) { if (gr) gr.visible = false; continue; }
      if (!gr) {
        gr = new THREE.Group();
        // A compact walled settlement with a central keep and roofscape.
        const wallMat = new THREE.MeshStandardMaterial({ color: 0xd2c3a2, roughness: 0.95 });
        const stoneMat = new THREE.MeshStandardMaterial({ color: 0xa89a7d, roughness: 1 });
        const roofMat = new THREE.MeshStandardMaterial({ color: 0x87382b, roughness: 0.88 });
        const foundation = new THREE.Mesh(new THREE.CylinderGeometry(S * 0.57, S * 0.62, S * 0.13, 6), stoneMat);
        foundation.position.y = S * 0.065;
        foundation.receiveShadow = true;
        gr.add(foundation);
        const wallRing = new THREE.Mesh(new THREE.TorusGeometry(S * 0.47, S * 0.045, 4, 6), stoneMat);
        wallRing.rotation.x = Math.PI / 2;
        wallRing.position.y = S * 0.22;
        wallRing.castShadow = wallRing.receiveShadow = true;
        gr.add(wallRing);
        for (const [dx, dz, w, hgt] of [[-0.3, 0.05, 0.28, 0.4], [0.08, -0.2, 0.34, 0.66], [0.32, 0.2, 0.25, 0.35], [-0.05, 0.3, 0.23, 0.31]]) {
          const bw = w * S, bh = hgt * S;
          const box = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, bw), wallMat);
          box.position.set(dx * S, bh / 2, dz * S);
          box.castShadow = box.receiveShadow = true;
          gr.add(box);
          const roof = new THREE.Mesh(new THREE.ConeGeometry(bw * 0.78, bw * 0.55, 4), roofMat);
          roof.position.set(dx * S, bh + bw * 0.27, dz * S);
          roof.rotation.y = Math.PI / 4;
          roof.castShadow = true;
          gr.add(roof);
        }
        const keep = new THREE.Mesh(new THREE.CylinderGeometry(S * 0.13, S * 0.15, S * 0.82, 8), stoneMat);
        keep.position.set(S * 0.07, S * 0.41, -S * 0.02);
        keep.castShadow = keep.receiveShadow = true;
        gr.add(keep);
        const keepRoof = new THREE.Mesh(new THREE.ConeGeometry(S * 0.19, S * 0.22, 8), roofMat);
        keepRoof.position.set(S * 0.07, S * 0.93, -S * 0.02);
        keepRoof.castShadow = true;
        gr.add(keepRoof);
        const banner = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false }));
        banner.name = "banner";
        gr.add(banner);
        this._cities.set(city, gr);
        this.gDyn.add(gr);
      }
      gr.visible = true;
      const [wx, wz] = HEX.toPixel(city.c, city.r, S);
      const top = ELEV3D[game.tile(city.c, city.r).terrain];
      gr.position.set(wx, top, wz);
      const banner = gr.getObjectByName("banner");
      const tex = this._bannerTex(city, game);
      banner.material.map = tex;
      banner.material.opacity = v === 1 ? 0.6 : 1;
      const bh = S * 0.9, bw = bh * tex.userData.w / tex.userData.h;
      banner.scale.set(bw, bh, 1);
      banner.position.set(0, S * 1.72, 0);
      banner.renderOrder = 6;
      gr.traverse(o => { if (o.isMesh) { o.material.opacity = 1; } });
    }
  }

  _syncUnits(game, nowMs) {
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    const ANIM_HOP = 110;
    game.anims = game.anims.filter(a => nowMs - a.ts < (a.hops.length - 1) * ANIM_HOP + 80);
    const seen = new Set();
    for (const u of game.units) {
      const i = game.map.idx(u.c, u.r);
      if (u.owner !== game.viewer && vis[i] !== 2) continue;
      if (u.owner === game.viewer && vis[i] === 0) continue;
      seen.add(u.id);
      let sp = this._units.get(u.id);
      if (!sp) {
        sp = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false }));
        sp.center.set(0.5, 0.32);
        this._units.set(u.id, sp);
        this.gDyn.add(sp);
      }
      sp.visible = true;
      sp.material.map = this._unitTex(u, game);
      sp.material.opacity = 1;
      let [wx, wz] = HEX.toPixel(u.c, u.r, S);
      let y = surfY3D(game.tile(u.c, u.r));
      const anim = game.anims.find(a => a.id === u.id);
      if (anim) {
        const prog = (nowMs - anim.ts) / ANIM_HOP;
        const total = anim.hops.length - 1;
        if (prog < total) {
          const seg = Math.floor(prog), f = prog - seg;
          const [c1, r1] = anim.hops[seg], [c2, r2] = anim.hops[seg + 1];
          const [x1, z1] = HEX.toPixel(c1, r1, S), [x2, z2] = HEX.toPixel(c2, r2, S);
          const y1 = surfY3D(game.tile(c1, r1)), y2 = surfY3D(game.tile(c2, r2));
          wx = x1 + (x2 - x1) * f; wz = z1 + (z2 - z1) * f; y = y1 + (y2 - y1) * f;
        }
      }
      const strike = !this.reduceMotion && (game.strikes || []).find(s => s.id === u.id);
      if (strike) {
        const f = Math.min(1, (nowMs - strike.ts) / 300);
        const k = Math.sin(f * Math.PI) * (strike.ranged ? 0.16 : 0.4);
        const [tx, tz] = HEX.toPixel(strike.tc, strike.tr, S);
        wx += (tx - wx) * k; wz += (tz - wz) * k;
      }
      sp.position.set(wx, y + 1.2, wz);
      sp.scale.set(S * 1.35, S * 1.6, 1);
      sp.renderOrder = 5;
    }
    for (const [id, sp] of this._units) {
      if (!seen.has(id)) sp.visible = false;
    }
  }

  _syncDecor(game) {
    this._hidePool(this._pool.decor);
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    for (const t of game.map.tiles) {
      const v = vis[game.map.idx(t.c, t.r)];
      if (v === 0) continue;
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const y = surfY3D(t);
      const op = v === 1 ? 0.45 : 1;
      if (t.resource) this._spriteAt(this._pool.decor, this._worldTex("resource", t.resource), wx - S * 0.48, y + S * 0.34, wz - S * 0.34, S * 0.54, S * 0.54, op);
      if (t.ruin) this._spriteAt(this._pool.decor, this._worldTex("site", "RUIN"), wx, y + S * 0.34, wz, S * 0.66, S * 0.66, op);
      if (game.campAt && game.campAt(t.c, t.r)) this._spriteAt(this._pool.decor, this._worldTex("site", "CAMP"), wx, y + S * 0.39, wz, S * 0.78, S * 0.78, op);
      if (t.improvement === "MINE") this._spriteAt(this._pool.decor, this._worldTex("site", "MINE"), wx + S * 0.38, y + S * 0.28, wz + S * 0.3, S * 0.48, S * 0.48, op);
    }
  }

  _lineOf(points, color, dashed) {
    const geo = new THREE.BufferGeometry().setFromPoints(points.map(p => new THREE.Vector3(p[0], p[1], p[2])));
    const mat = dashed
      ? new THREE.LineDashedMaterial({ color, dashSize: this.hexSize * 0.28, gapSize: this.hexSize * 0.22, transparent: true, opacity: 0.85 })
      : new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.85 });
    const line = new THREE.Line(geo, mat);
    if (dashed) line.computeLineDistances();
    line.renderOrder = 4;
    return line;
  }

  _syncOverlays(game) {
    const S = this.hexSize;
    const vis = game.players[game.viewer].visible;
    // move / attack highlights
    this._hidePool(this._pool.move);
    this._hidePool(this._pool.atk);
    this._hidePool(this._pool.site);
    this._hidePool(this._pool.worked);
    if (this.selected) {
      for (const [c, r] of this.reachable) {
        const m = this._getPooled(this._pool.move, () => {
          const mesh = new THREE.Mesh(this._hexFillGeo, this._matFill.move);
          mesh.renderOrder = 2;
          return mesh;
        });
        const [wx, wz] = HEX.toPixel(c, r, S);
        m.position.set(wx, surfY3D(game.tile(c, r)) + 0.5, wz);
      }
      for (const [c, r] of this.attackable) {
        const m = this._getPooled(this._pool.atk, () => {
          const mesh = new THREE.Mesh(this._hexFillGeo, this._matFill.atk);
          mesh.renderOrder = 2;
          return mesh;
        });
        const [wx, wz] = HEX.toPixel(c, r, S);
        m.position.set(wx, surfY3D(game.tile(c, r)) + 0.5, wz);
      }
    }
    for (const site of this.settlementSites) {
      const m = this._getPooled(this._pool.site, () => {
        const mesh = new THREE.Mesh(new THREE.RingGeometry(S * 0.62, S * 0.76, 6, 1, Math.PI / 6),
          this._matSite.excellent);
        mesh.rotation.x = -Math.PI / 2;
        mesh.renderOrder = 3;
        return mesh;
      });
      m.material = this._matSite[site.canFoundThisTurn ? site.tier : `${site.tier}-wait`];
      const [wx, wz] = HEX.toPixel(site.c, site.r, S);
      m.position.set(wx, surfY3D(game.tile(site.c, site.r)) + 0.72, wz);
    }
    if (this.selectedCity && this.selectedCity.owner === game.viewer) {
      for (const t of game.workedTiles(this.selectedCity)) {
        if (!vis[game.map.idx(t.c, t.r)]) continue;
        const m = this._getPooled(this._pool.worked, () => {
          const mesh = new THREE.Mesh(new THREE.RingGeometry(S * 0.69, S * 0.78, 6, 1, Math.PI / 6),
            this._matWorked);
          mesh.rotation.x = -Math.PI / 2;
          mesh.renderOrder = 3;
          return mesh;
        });
        const [wx, wz] = HEX.toPixel(t.c, t.r, S);
        m.position.set(wx, surfY3D(t) + 0.74, wz);
      }
    }

    // trade routes + path preview are rebuilt every frame (cheap lines)
    for (const l of this._pool.routes) { this.gDyn.remove(l); l.geometry.dispose(); l.material.dispose(); }
    this._pool.routes = [];
    for (const route of game.routes || []) {
      if (route.owner !== game.viewer) continue;
      const suspended = !game.tradeRouteStatus(route).active;
      const pts = route.path.map(([pc, pr]) => {
        const [wx, wz] = HEX.toPixel(pc, pr, S);
        return [wx, surfY3D(game.tile(pc, pr)) + 1.4, wz];
      });
      const l = this._lineOf(pts, suspended ? 0xde684b : 0xf1c40f, true);
      if (suspended) l.material.opacity = 0.62;
      this.gDyn.add(l);
      this._pool.routes.push(l);
    }
    if (this.previewPath && this.previewPath.length && this.selected) {
      const start = [this.selected.c, this.selected.r];
      const pts = [start, ...this.previewPath].map(([pc, pr]) => {
        const [wx, wz] = HEX.toPixel(pc, pr, S);
        return [wx, surfY3D(game.tile(pc, pr)) + 1.6, wz];
      });
      const l = this._lineOf(pts, 0xffffff, true);
      this.gDyn.add(l);
      this._pool.routes.push(l);
      const turns = Math.max(1, Math.ceil(this.previewPath.length / Math.max(1, this.selected.maxMoves)));
      if (turns > 1) {
        const last = pts[pts.length - 1];
        this._spriteAt(this._pool.fx, this._textTex(String(turns), "#ffffff"), last[0], last[1] + S * 0.55, last[2], S * 0.9, S * 0.34);
      }
    }

    // hover outline
    if (!this._hover) {
      const pts = this._corners(0, 0, S * 0.96).map(p => new THREE.Vector3(p[0], 0, p[1]));
      this._hover = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.6 }));
      this._hover.renderOrder = 3;
      this.gDyn.add(this._hover);
    }
    this._hover.visible = false;
    if (this.hoverTile) {
      const [hc, hr] = this.hoverTile;
      const t = game.tile(hc, hr);
      if (t && vis[game.map.idx(hc, hr)]) {
        const [wx, wz] = HEX.toPixel(hc, hr, S);
        this._hover.position.set(wx, surfY3D(t) + 0.6, wz);
        this._hover.visible = true;
      }
    }

    // selection ring / selected city outline
    if (!this._selRing) {
      this._selRing = new THREE.Mesh(
        new THREE.RingGeometry(S * 0.5, S * 0.6, 24),
        new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.9, side: THREE.DoubleSide, depthWrite: false }));
      this._selRing.rotation.x = -Math.PI / 2;
      this._selRing.renderOrder = 3;
      this.gDyn.add(this._selRing);
      const pts = this._corners(0, 0, S * 0.95).map(p => new THREE.Vector3(p[0], 0, p[1]));
      this._citySel = new THREE.LineLoop(
        new THREE.BufferGeometry().setFromPoints(pts),
        new THREE.LineBasicMaterial({ color: 0xffffff }));
      this._citySel.renderOrder = 3;
      this.gDyn.add(this._citySel);
    }
    this._selRing.visible = this._citySel.visible = false;
    if (this.selected && game.units.includes(this.selected)) {
      const [wx, wz] = HEX.toPixel(this.selected.c, this.selected.r, S);
      this._selRing.position.set(wx, surfY3D(game.tile(this.selected.c, this.selected.r)) + 0.7, wz);
      this._selRing.visible = true;
    }
    if (this.selectedCity) {
      const [wx, wz] = HEX.toPixel(this.selectedCity.c, this.selectedCity.r, S);
      this._citySel.position.set(wx, surfY3D(game.tile(this.selectedCity.c, this.selectedCity.r)) + 0.7, wz);
      this._citySel.visible = true;
    }
  }

  _syncStrikes(game, now) {
    game.strikes = (game.strikes || []).filter(s => now - s.ts < 450);
    this._hidePool(this._pool.flash);
    const vis = game.players[game.viewer].visible;
    for (const s of game.strikes) {
      if (!vis[game.map.idx(s.tc, s.tr)]) continue;
      const age = (now - s.ts) / 450;
      const m = this._getPooled(this._pool.flash, () => {
        const mesh = new THREE.Mesh(this._hexFillGeo,
          new THREE.MeshBasicMaterial({ color: 0xff4433, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
        mesh.renderOrder = 3;
        return mesh;
      });
      m.material.opacity = (1 - age) * 0.5;
      const [wx, wz] = HEX.toPixel(s.tc, s.tr, this.hexSize);
      m.position.set(wx, surfY3D(game.tile(s.tc, s.tr)) + 0.55, wz);
    }
  }

  _syncEffects(game, now) {
    game.effects = game.effects.filter(e => now - e.ts < 1300);
    const S = this.hexSize;
    const vis = game.players[game.viewer].visible;
    this._hidePool(this._pool.rings);
    for (const e of game.effects) {
      if (!vis[game.map.idx(e.c, e.r)]) continue; // don't reveal events in the unexplored world
      const age = (now - e.ts) / 1300;
      const [wx, wz] = HEX.toPixel(e.c, e.r, S);
      const t = game.tile(e.c, e.r);
      if (e.ring) {
        if (this.reduceMotion) continue;
        const m = this._getPooled(this._pool.rings, () => {
          const mesh = new THREE.Mesh(
            new THREE.RingGeometry(0.82, 1.0, 32),
            new THREE.MeshBasicMaterial({ transparent: true, side: THREE.DoubleSide, depthWrite: false }));
          mesh.rotation.x = -Math.PI / 2;
          mesh.renderOrder = 4;
          return mesh;
        });
        m.material.color.set(e.color);
        m.material.opacity = (1 - age) * 0.85;
        const rad = S * (0.3 + age * 1.3);
        m.scale.set(rad, rad, rad);
        m.position.set(wx, surfY3D(t) + 0.8, wz);
        continue;
      }
      const y = surfY3D(t) + S * 0.7 + age * S * 0.9;
      this._spriteAt(this._pool.fx, this._textTex(e.text, e.color), wx, y, wz, S * 1.9, S * 0.72, 1 - age);
    }
  }

  // ---------------- main draw ----------------
  draw(game) {
    this._game = game;
    const W = this.canvas.width, H = this.canvas.height;
    if (this._vw !== W || this._vh !== H) {
      this.three.setSize(W, H, false);
      this.camera.aspect = W / H;
      this.camera.updateProjectionMatrix();
      this._vw = W; this._vh = H;
    }
    if (this._builtFor !== game.map) this._buildStatic(game);

    // fog / ownership / improvements diffing
    const vis = game.players[game.viewer].visible;
    let visChanged = !this._visSnap;
    if (this._visSnap) {
      for (let i = 0; i < vis.length; i++) if (vis[i] !== this._visSnap[i]) { visChanged = true; break; }
    }
    let ownChanged = !this._ownSnap;
    if (this._ownSnap) {
      for (let i = 0; i < game.map.tiles.length; i++) if (game.map.tiles[i].owner !== this._ownSnap[i]) { ownChanged = true; break; }
    }
    let impHash = 0;
    for (let i = 0; i < game.map.tiles.length; i++) {
      const t = game.map.tiles[i];
      if (t.improvement) impHash = (impHash * 31 + i * 3 + (t.improvement === "ROAD" ? 1 : t.improvement === "FARM" ? 2 : 3)) >>> 0;
    }
    if (visChanged || ownChanged) {
      this._recolor(game);
      this._visSnap = Uint8Array.from(vis);
      this._ownSnap = Int16Array.from(game.map.tiles, t => t.owner);
    }
    if (visChanged) this._rebuildShroud(game);
    if (visChanged || ownChanged) this._rebuildBorders(game);
    if (visChanged || impHash !== this._impHash) {
      this._rebuildImprovements(game);
      this._impHash = impHash;
    }
    const yieldChanged = this._yieldShown !== this.showYields;
    if (visChanged || impHash !== this._yieldHash || yieldChanged) {
      this._rebuildYields(game);
      this._yieldHash = impHash;
      this._yieldShown = this.showYields;
    }

    const now = Date.now();
    this._hidePool(this._pool.fx);
    this._syncCities(game);
    this._syncUnits(game, now);
    this._syncDecor(game);
    this._syncOverlays(game);
    this._syncStrikes(game, now);
    this._syncEffects(game, now);
    this._animateWater(now);
    this._sunCycle(game);

    this._placeCamera();
    this.three.render(this.scene, this.camera);
    this.drawMinimap(game);
    this._lastDraw = now;
    this.dirty = false;
  }

  // gentle rolling swell on the sea plane
  _animateWater(now) {
    if (!this._sea || this.reduceMotion) return;
    const t = now * 0.0012;
    const posAttr = this._sea.geometry.getAttribute("position");
    for (let i = 0; i < posAttr.count; i++) {
      const x = posAttr.getX(i), y = posAttr.getY(i);
      posAttr.setZ(i, Math.sin(x * 0.016 + t * 1.4) * 0.34 + Math.cos(y * 0.021 + t) * 0.22);
    }
    posAttr.needsUpdate = true;
    this._sea.geometry.computeVertexNormals();
  }

  // the sun drifts slowly around the map as turns pass
  _sunCycle(game) {
    if (!this._center || this.reduceMotion) return;
    const az = ((game.turn % 80) / 80) * Math.PI * 2 + 0.6;
    this.sun.position.copy(this._center)
      .add(new THREE.Vector3(Math.cos(az) * 1300, 1500, Math.sin(az) * 1300));
    const warm = (Math.sin(az * 2) + 1) / 2; // subtle temperature swing
    this.sun.color.setRGB(1, 0.95 - warm * 0.06, 0.85 - warm * 0.12);
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
    // viewport outline: unproject the screen corners onto the ground so the
    // shape stays correct when the camera is rotated
    const hexW = this.hexSize * Math.sqrt(3), hexH = this.hexSize * 1.5;
    const cw = this.canvas.width, ch = this.canvas.height;
    const pts = [[0, 0], [cw, 0], [cw, ch], [0, ch]].map(([px, py]) => {
      const hit = this._groundPoint(this._rayAt(px, py), 2.4);
      return hit ? [(hit.x / hexW) * sx, (hit.z / hexH) * sy] : null;
    });
    if (pts.every(p => p)) {
      m.save();
      m.beginPath(); m.rect(0, 0, W, H); m.clip();
      m.strokeStyle = "rgba(255,255,255,0.8)";
      m.lineWidth = 1;
      m.beginPath();
      pts.forEach(([px, py], i) => i === 0 ? m.moveTo(px, py) : m.lineTo(px, py));
      m.closePath();
      m.stroke();
      m.restore();
    }
  }
}
