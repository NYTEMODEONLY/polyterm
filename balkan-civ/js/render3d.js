// ============================================================
// Three.js renderer: extruded hex terrain, sprite units, fog
// Implements the same interface as the 2D Renderer so ui.js
// can drive either one: cam {x,y,zoom}, size, selected,
// selectedCity, reachable, controlled, attackable, hoverTile, previewPath,
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
    this.controlled = [];
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
    this.hemi = new THREE.HemisphereLight(0xe5f0f2, 0x5c523e, 0.68);
    this.ambient = new THREE.AmbientLight(0xfff1d7, 0.32);
    this.scene.add(this.hemi);
    this.scene.add(this.ambient);
    this.sun = new THREE.DirectionalLight(0xffe6bc, 0.78);
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
    this._matZoc = new THREE.MeshBasicMaterial({ color: 0xf1c40f, transparent: true, opacity: 0.82,
      side: THREE.DoubleSide, depthWrite: false });
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
    this._pool = { move: [], zoc: [], atk: [], site: [], worked: [], decor: [], fx: [], routes: [], flash: [], rings: [] };
    this._units = new Map();   // unit id -> grounded piece group
    this._cities = new Map();  // city object -> group
    this._builtFor = null;     // map object the static geometry was built for
    this._visSnap = null;
    this._ownSnap = null;
    this._impHash = null;
    this._yieldShown = null;
    this._yieldHash = null;
    this._vw = 0; this._vh = 0;

    this._hover = null; this._selRing = null; this._citySel = null; this._preview = null;

    const S = this.hexSize;
    this._unitGeo = {
      outer: new THREE.CylinderGeometry(S * 0.39, S * 0.41, S * 0.10, 28),
      inner: new THREE.CylinderGeometry(S * 0.33, S * 0.35, S * 0.12, 28),
      center: new THREE.CylinderGeometry(S * 0.22, S * 0.24, S * 0.14, 28),
    };
  }

  get size() { return this.hexSize * this.cam.zoom; }

  centerOn(game, c, r, screenPoint = null) {
    const [x, z] = HEX.toPixel(c, r, this.hexSize);
    const targetX = screenPoint?.x ?? this.canvas.width / 2;
    const targetY = screenPoint?.y ?? this.canvas.height / 2;
    this.cam.x = x * this.cam.zoom - this.canvas.width / 2 + 30;
    this.cam.y = z * this.cam.zoom - this.canvas.height / 2 + 30;

    // Perspective needs a ground-plane projection to place a tile at a
    // viewport point that is not the geometric center.
    if (targetX !== this.canvas.width / 2 || targetY !== this.canvas.height / 2) {
      this.camera.aspect = this.canvas.width / Math.max(1, this.canvas.height);
      this.camera.updateProjectionMatrix();
      const hit = this._groundPoint(this._rayAt(targetX, targetY), 0);
      if (hit) {
        this.cam.x += (x - hit.x) * this.cam.zoom;
        this.cam.y += (z - hit.z) * this.cam.zoom;
      }
    }
    this.dirty = true;
  }

  worldToScreen(c, r, height = 0) {
    this.camera.aspect = this.canvas.width / Math.max(1, this.canvas.height);
    this.camera.updateProjectionMatrix();
    this._placeCamera();
    const [x, z] = HEX.toPixel(c, r, this.hexSize);
    const point = new THREE.Vector3(x, height, z).project(this.camera);
    return [(point.x + 1) * this.canvas.width / 2, (1 - point.y) * this.canvas.height / 2];
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
    this.camera.updateMatrixWorld(true);
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
    const hpB = u.hp >= 100 ? 100 : Math.ceil(u.hp / 5) * 5;
    const emb = game.isEmbarked(u);
    const art = UNIT_ART.kind(u.def);
    const supply = u.owner === game.viewer && u.def.naval ? game.navalSupply(u) : null;
    const supplyStatus = !supply || supply.supplied ? 0 : supply.attritionActive ? 2 : 1;
    const key = `u-grounded-v2|${art}|${hpB}|${u.level}|${u.fortified ? 1 : 0}|${emb ? 1 : 0}|${supplyStatus}`;
    return this._tex(key, 128, 156, (ctx) => {
      const star = (x, y, radius) => {
        ctx.beginPath();
        for (let i = 0; i < 10; i++) {
          const a = -Math.PI / 2 + i * Math.PI / 5;
          const r = i % 2 ? radius * 0.43 : radius;
          const px = x + Math.cos(a) * r, py = y + Math.sin(a) * r;
          if (i === 0) ctx.moveTo(px, py); else ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fillStyle = "#f4cf55";
        ctx.fill();
        ctx.strokeStyle = "#211b10";
        ctx.lineWidth = 2;
        ctx.stroke();
      };
      const shield = (x, y, size) => {
        ctx.beginPath();
        ctx.moveTo(x, y - size * 0.55);
        ctx.lineTo(x + size * 0.46, y - size * 0.34);
        ctx.lineTo(x + size * 0.34, y + size * 0.24);
        ctx.quadraticCurveTo(x, y + size * 0.62, x - size * 0.34, y + size * 0.24);
        ctx.lineTo(x - size * 0.46, y - size * 0.34);
        ctx.closePath();
        ctx.fillStyle = "#f0e6ce";
        ctx.fill();
        ctx.strokeStyle = "#202724";
        ctx.lineWidth = 3;
        ctx.stroke();
      };
      const boat = (x, y, size) => {
        ctx.fillStyle = "#f0e6ce";
        ctx.strokeStyle = "#202724";
        ctx.lineWidth = 3;
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
      };

      UNIT_ART.draw(ctx, u.def, 67, 84, 83, "rgba(8,14,13,0.9)");
      UNIT_ART.draw(ctx, u.def, 64, 81, 83, "#f2e7cf");
      // HP bar
      if (hpB < 100) {
        ctx.fillStyle = "rgba(18,22,21,0.96)";
        ctx.fillRect(12, 7, 104, 13);
        ctx.fillStyle = hpB > 60 ? "#2ecc71" : hpB > 30 ? "#f39c12" : "#e74c3c";
        ctx.fillRect(14, 9, 100 * hpB / 100, 9);
      }
      if (supplyStatus) {
        ctx.beginPath();
        ctx.moveTo(4, 29); ctx.lineTo(36, 29); ctx.lineTo(4, 61); ctx.closePath();
        ctx.fillStyle = supplyStatus === 2 ? "#d94f3d" : "#e7a447";
        ctx.fill();
        ctx.fillStyle = "#17120c";
        ctx.font = "bold 22px sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("!", 15, 40);
      }
      if (u.fortified) shield(109, 40, 26);
      if (emb) boat(19, 40, 25);
      const level = Math.min(3, u.level);
      for (let i = 0; i < level; i++) star(64 + (i - (level - 1) / 2) * 22, 145, 9);
    });
  }

  _bannerTex(city, game) {
    const civ = CIVS[game.players[city.owner].civId];
    const seenNow = game.players[game.viewer].visible[game.map.idx(city.c, city.r)] === 2;
    const reportDetails = city.owner === game.viewer || seenNow;
    const rel = reportDetails && city.religion !== null && game.religions[city.religion];
    const blockaded = (city.owner === game.viewer || seenNow) && game.cityBlockade(city).active;
    const label = `${blockaded ? "⚓ " : ""}${rel ? rel.icon + " " : ""}${city.name}${city.isCapital ? " ★" : ""}`;
    const population = reportDetails ? city.pop : "?";
    const hpB = reportDetails ? (city.hp >= city.maxHp ? 100 : Math.ceil(city.hp / city.maxHp * 20) * 5) : 100;
    const key = `b|${label}|${population}|${civ.color}|${hpB}|${blockaded ? 1 : 0}`;
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
      ctx.fillText(String(population), 25, 32);
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

  _pushMound(pos, col, wx, wz, baseY, topY, r, color, segs = 10) {
    const outer = [], inner = [];
    for (let i = 0; i < segs; i++) {
      const a = Math.PI * 2 * i / segs;
      const wobble = 0.94 + ((i * 17 + Math.round(wx + wz)) % 5) * 0.025;
      outer.push([wx + Math.cos(a) * r * wobble, baseY, wz + Math.sin(a) * r * wobble]);
      inner.push([wx + Math.cos(a) * r * 0.43, topY, wz + Math.sin(a) * r * 0.43]);
    }
    for (let i = 0; i < segs; i++) {
      const n = (i + 1) % segs;
      const side = color.clone().multiplyScalar(0.91 + (i % 3) * 0.035);
      this._pushTri(pos, col, outer[i], outer[n], inner[n], side);
      this._pushTri(pos, col, outer[i], inner[n], inner[i], side);
      this._pushTri(pos, col, [wx, topY + 0.16, wz], inner[n], inner[i],
        color.clone().multiplyScalar(1.04 + (i % 2) * 0.025));
    }
  }

  _pushColumn(pos, col, wx, wz, baseY, topY, r, color, segs = 6) {
    for (let i = 0; i < segs; i++) {
      const a1 = Math.PI * 2 * i / segs, a2 = Math.PI * 2 * (i + 1) / segs;
      const p1 = [wx + r * Math.cos(a1), baseY, wz + r * Math.sin(a1)];
      const p2 = [wx + r * Math.cos(a2), baseY, wz + r * Math.sin(a2)];
      const p3 = [p2[0], topY, p2[2]], p4 = [p1[0], topY, p1[2]];
      this._pushTri(pos, col, p1, p2, p3, color);
      this._pushTri(pos, col, p1, p3, p4, color);
    }
  }

  _buildStatic(game) {
    // wipe everything tied to the previous map
    for (const group of this._cities.values()) this._disposeCityGroup(group);
    for (const g of [this.gTerrain, this.gShroud, this.gBorders, this.gImprov, this.gYields, this.gDyn]) {
      for (const ch of [...g.children]) {
        g.remove(ch);
        if (ch.geometry) ch.geometry.dispose();
        if (ch.material && g !== this.gDyn) {
          for (const material of Array.isArray(ch.material) ? ch.material : [ch.material]) material.dispose();
        }
      }
    }
    this._units.clear(); this._cities.clear();
    this._pool = { move: [], zoc: [], atk: [], site: [], worked: [], decor: [], fx: [], routes: [], flash: [], rings: [] };
    this._hover = this._selRing = this._citySel = this._preview = null;
    this._sea = this._foam = null;
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
    const waterPos = [], waterCol = [], shorePos = [], shoreCol = [], foamPos = [], foamCol = [];
    this._tileRange = new Array(map.tiles.length);
    const tmp = new THREE.Color();

    for (const t of map.tiles) {
      const start = pos.length / 3;
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const top = ELEV3D[t.terrain];
      const j = isWater3D(t) ? jitterOf(t.c, t.r) * 0.5 : jitterOf(t.c, t.r);
      tmp.set(TERRAIN[t.terrain].color).multiplyScalar(1 + j);
      const base = tmp.clone();
      if (!isWater3D(t)) base.multiplyScalar(0.86);
      const wall = base.clone().multiplyScalar(0.72);
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
        const bump = base.clone().multiplyScalar(0.95);
        this._pushMound(pos, col, wx - S * 0.18, wz + S * 0.08, top, top + 3.6,
          S * 0.56, bump, 11);
        this._pushMound(pos, col, wx + S * 0.30, wz - S * 0.06, top, top + 2.7,
          S * 0.39, bump.clone().multiplyScalar(1.06), 10);
      }
      if (t.feature === "FOREST") {
        const green = new THREE.Color(FEATURE.FOREST.color).multiplyScalar(1.38 + j * 0.45);
        const trunk = new THREE.Color("#6f4d2f");
        for (const [dx, dz, sc, tone] of [[-0.31, 0.13, 0.88, 0.90], [0.04, -0.17, 1.12, 1.08], [0.34, 0.19, 0.78, 1.0]]) {
          const x = wx + dx * S, z = wz + dz * S;
          const trunkTop = top + S * 0.16 * sc;
          this._pushColumn(pos, col, x, z, top, trunkTop, S * 0.045 * sc, trunk, 6);
          this._pushCone(pos, col, x, z, trunkTop - S * 0.025, top + S * 0.48 * sc,
            S * 0.32 * sc, green.clone().multiplyScalar(tone * 0.82), 8);
          this._pushCone(pos, col, x, z, top + S * 0.24 * sc, top + S * 0.72 * sc,
            S * 0.22 * sc, green.clone().multiplyScalar(tone * 1.08), 8);
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
          const foam = new THREE.Color("#e3f6ed");
          const fx = ix * 0.18, fz = iz * 0.18, fy = SEA_Y + 0.235;
          this._pushTri(foamPos, foamCol, [p1[0], fy, p1[1]], [p2[0], fy, p2[1]],
            [p2[0] + fx, fy, p2[1] + fz], foam);
          this._pushTri(foamPos, foamCol, [p1[0], fy, p1[1]], [p2[0] + fx, fy, p2[1] + fz],
            [p1[0] + fx, fy, p1[1] + fz], foam);
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
    if (foamPos.length) {
      const foamGeo = new THREE.BufferGeometry();
      foamGeo.setAttribute("position", new THREE.Float32BufferAttribute(foamPos, 3));
      foamGeo.setAttribute("color", new THREE.Float32BufferAttribute(foamCol, 3));
      const foam = new THREE.Mesh(foamGeo, new THREE.MeshBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.55, depthWrite: false,
        side: THREE.DoubleSide,
      }));
      foam.renderOrder = 3;
      this.gTerrain.add(foam);
      this._foam = foam;
    }

    // translucent sea surface over the whole map, gently wave-animated
    const [maxX] = HEX.toPixel(map.w, 0, S), [, maxZ] = HEX.toPixel(0, map.h, S);
    const waterTex = this._waterTex();
    waterTex.wrapS = waterTex.wrapT = THREE.RepeatWrapping;
    waterTex.repeat.set(Math.max(4, map.w / 5), Math.max(3, map.h / 5));
    const sea = new THREE.Mesh(
      new THREE.PlaneGeometry(maxX + S * 14, maxZ + S * 14, 48, 36),
      new THREE.MeshStandardMaterial({ map: waterTex, color: 0x4d9cb0, roughness: 0.4, metalness: 0.02, transparent: true, opacity: 0.66, depthWrite: false }));
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
      let tint = null;
      if (t.owner !== -1 && v > 0) tint = tmp.set(CIVS[game.players[t.owner].civId].color);
      for (let k = start * 3; k < (start + count) * 3; k += 3) {
        const lum = base[k] * 0.299 + base[k + 1] * 0.587 + base[k + 2] * 0.114;
        let r, g, b;
        if (v === 2) {
          r = base[k]; g = base[k + 1]; b = base[k + 2];
        } else if (v === 1) {
          const saturation = 0.46, brightness = 0.72;
          r = (lum + (base[k] - lum) * saturation) * brightness;
          g = (lum + (base[k + 1] - lum) * saturation) * brightness;
          b = (lum + (base[k + 2] - lum) * saturation) * brightness;
        } else {
          r = g = b = lum * 0.30;
        }
        if (tint) { r += (tint.r - r) * 0.08; g += (tint.g - g) * 0.08; b += (tint.b - b) * 0.08; }
        arr[k] = r; arr[k + 1] = g; arr[k + 2] = b;
      }
    }
    col.needsUpdate = true;
  }

  // opaque dark prisms over unexplored tiles
  _rebuildShroud(game) {
    for (const ch of [...this.gShroud.children]) {
      this.gShroud.remove(ch); ch.geometry.dispose(); ch.material.dispose();
    }
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    const pos = [], col = [];
    const dark = new THREE.Color(0x2b4145);
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
    const shroud = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, opacity: 0.94 }));
    this.gShroud.add(shroud);
  }

  _rebuildBorders(game) {
    for (const ch of [...this.gBorders.children]) {
      this.gBorders.remove(ch); ch.geometry.dispose(); ch.material.dispose();
    }
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
        ix = ix / il * S * 0.075; iz = iz / il * S * 0.075;
        this._pushTri(pos, col, [p1[0], y, p1[1]], [p2[0], y, p2[1]], [p2[0] + ix, y, p2[1] + iz], tmp);
        this._pushTri(pos, col, [p1[0], y, p1[1]], [p2[0] + ix, y, p2[1] + iz], [p1[0] + ix, y, p1[1] + iz], tmp);
      });
    }
    if (!pos.length) return;
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.Float32BufferAttribute(col, 3));
    this.gBorders.add(new THREE.Mesh(geo, new THREE.MeshBasicMaterial({
      vertexColors: true, transparent: true, opacity: 0.94, side: THREE.DoubleSide,
    })));
  }

  _rebuildImprovements(game) {
    for (const ch of [...this.gImprov.children]) {
      this.gImprov.remove(ch); ch.geometry.dispose(); ch.material.dispose();
    }
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    const pos = [], col = [];
    const road = new THREE.Color("#5a3c1e"), connectedRoad = new THREE.Color("#b57d37");
    const farm = new THREE.Color("#f0dc78");
    const riverBank = new THREE.Color("#173d48"), riverWater = new THREE.Color("#4aaec9");
    const connected = game.roadNetwork ? game.roadNetwork(game.viewer).tiles : new Set();
    const quad = (x1, z1, x2, z2, w, y1, c, y2 = y1) => {
      // strip of width w from (x1,z1) to (x2,z2), optionally sloped
      let px = -(z2 - z1), pz = x2 - x1;
      const l = Math.hypot(px, pz) || 1;
      px = px / l * w / 2; pz = pz / l * w / 2;
      this._pushTri(pos, col, [x1 - px, y1, z1 - pz], [x2 - px, y2, z2 - pz], [x2 + px, y2, z2 + pz], c);
      this._pushTri(pos, col, [x1 - px, y1, z1 - pz], [x2 + px, y2, z2 + pz], [x1 + px, y1, z1 + pz], c);
    };
    const riverStrip = (x1, z1, y1, x2, z2, y2, bend, bank, water) => {
      const dx = x2 - x1, dz = z2 - z1, len = Math.hypot(dx, dz) || 1;
      const mx = (x1 + x2) / 2 - dz / len * bend * S;
      const mz = (z1 + z2) / 2 + dx / len * bend * S;
      const my = (y1 + y2) / 2;
      quad(x1, z1, mx, mz, S * 0.23, y1 + 0.008, bank, my + 0.008);
      quad(mx, mz, x2, z2, S * 0.23, my + 0.008, bank, y2 + 0.008);
      quad(x1, z1, mx, mz, S * 0.13, y1 + 0.022, water, my + 0.022);
      quad(mx, mz, x2, z2, S * 0.13, my + 0.022, water, y2 + 0.022);
    };
    for (const t of game.map.tiles) {
      if (!t.improvement && !t.road && !t.river) continue;
      const v = vis[game.map.idx(t.c, t.r)];
      if (v === 0) continue;
      const [wx, wz] = HEX.toPixel(t.c, t.r, S);
      const y = ELEV3D[t.terrain] + 0.3;
      if (t.river) {
        const bank = v === 1 ? riverBank.clone().multiplyScalar(0.58) : riverBank;
        const water = v === 1 ? riverWater.clone().multiplyScalar(0.58) : riverWater;
        const branches = RIVER_ART.branches(game, t);
        if (branches.length) {
          for (const branch of branches) {
            const n = branch.tile;
            const [nx, nz] = HEX.toPixel(n.c, n.r, S);
            const ny = surfY3D(n) + 0.3;
            riverStrip(wx, wz, y, (wx + nx) / 2, (wz + nz) / 2,
              (y + ny) / 2, branch.bend, bank, water);
          }
        } else {
          const [dx, dz] = RIVER_ART.stubVector(t);
          riverStrip(wx - dx * S * 0.24, wz - dz * S * 0.24, y,
            wx + dx * S * 0.24, wz + dz * S * 0.24, y, 0.05, bank, water);
        }
      }
      if (t.road) {
        const base = connected.has(game.map.idx(t.c, t.r)) ? connectedRoad : road;
        const c = v === 1 ? base.clone().multiplyScalar(0.6) : base;
        const roadY = y + 0.06;
        let any = false;
        for (const [nc, nr] of HEX.neighbors(t.c, t.r)) {
          const n = game.tile(nc, nr);
          if (!n || !vis[game.map.idx(nc, nr)] || (!n.road && !n.city)) continue;
          const [nx, nz] = HEX.toPixel(nc, nr, S);
          quad(wx, wz, (wx + nx) / 2, (wz + nz) / 2, S * 0.18, roadY, c);
          any = true;
        }
        if (!any) quad(wx - S * 0.15, wz, wx + S * 0.15, wz, S * 0.18, roadY, c);
      }
      if (t.improvement === "FARM") {
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

  _spriteAt(pool, tex, wx, y, wz, w, h, opacity = 1, tint = 0xffffff) {
    const s = this._getPooled(pool, () => new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false })));
    s.material.map = tex;
    s.material.opacity = opacity;
    s.material.color.set(tint);
    s.position.set(wx, y, wz);
    s.scale.set(w, h, 1);
    return s;
  }

  _disposeCityModel(model) {
    if (!model) return;
    const materials = new Set();
    model.traverse(object => {
      if (object.geometry) object.geometry.dispose();
      if (Array.isArray(object.material)) object.material.forEach(material => materials.add(material));
      else if (object.material) materials.add(object.material);
    });
    materials.forEach(material => material.dispose());
  }

  _disposeCityGroup(group) {
    if (!group) return;
    this._disposeCityModel(group.getObjectByName("model"));
    const banner = group.getObjectByName("banner");
    if (banner && banner.material) banner.material.dispose();
  }

  _buildCityModel(appearance, S) {
    const model = new THREE.Group();
    model.name = "model";
    const p = appearance.palette;
    const material = (color, roughness = 0.92, metalness = 0) =>
      new THREE.MeshStandardMaterial({ color, roughness, metalness, transparent: true });
    const groundMat = material(p.ground, 1);
    const facadeMat = material(p.facade);
    const stoneMat = material(p.stone, 1);
    const roofMat = material(p.roof, 0.86);
    const accentMat = material(p.accent, 0.7, appearance.era >= 4 ? 0.18 : 0);
    const civMat = material(appearance.capital ? p.accent : appearance.civColor, 0.72);
    const addMesh = (geometry, mat, x, y, z, receive = true) => {
      const mesh = new THREE.Mesh(geometry, mat);
      mesh.position.set(x, y, z);
      mesh.castShadow = true;
      mesh.receiveShadow = receive;
      model.add(mesh);
      return mesh;
    };

    addMesh(new THREE.CylinderGeometry(S * 0.57, S * 0.62, S * 0.13, 6),
      groundMat, 0, S * 0.065, 0);

    if (appearance.fortified) {
      const wall = addMesh(new THREE.TorusGeometry(S * 0.48, S * 0.047, 4, 6),
        stoneMat, 0, S * 0.22, 0);
      wall.rotation.x = Math.PI / 2;
      for (const [x, z] of [[-0.39, -0.18], [0.39, -0.18], [-0.27, 0.34], [0.27, 0.34]])
        addMesh(new THREE.CylinderGeometry(S * 0.075, S * 0.085, S * 0.28, 6),
          stoneMat, x * S, S * 0.18, z * S);
    }

    const layout = [
      [-0.30, 0.10, 0.21, 0.35], [0.03, -0.16, 0.25, 0.48], [0.31, 0.12, 0.18, 0.31],
      [-0.06, 0.27, 0.20, 0.29], [-0.34, -0.20, 0.17, 0.28], [0.34, -0.18, 0.16, 0.25],
    ];
    for (let i = 0; i < appearance.density; i++) {
      const [x, z, width, height] = layout[i];
      const bw = width * S;
      const bh = height * S * (1 + appearance.era * 0.035);
      const body = addMesh(new THREE.BoxGeometry(bw, bh, bw), i % 3 === 0 ? stoneMat : facadeMat,
        x * S, bh / 2 + S * 0.12, z * S);
      body.rotation.y = (i % 2 ? 0.09 : -0.08);
      if (appearance.era >= 4 && i % 2 === 0) {
        addMesh(new THREE.BoxGeometry(bw * 1.10, bw * 0.12, bw * 1.10), roofMat,
          x * S, bh + S * 0.12, z * S);
      } else {
        const roof = addMesh(new THREE.ConeGeometry(bw * 0.78, bw * 0.55, 4), roofMat,
          x * S, bh + S * 0.12 + bw * 0.27, z * S, false);
        roof.rotation.y = Math.PI / 4 + body.rotation.y;
      }
    }

    if (appearance.industry) {
      addMesh(new THREE.BoxGeometry(S * 0.36, S * 0.34, S * 0.31), facadeMat,
        0, S * 0.29, -S * 0.02);
      addMesh(new THREE.BoxGeometry(S * 0.42, S * 0.07, S * 0.35), roofMat,
        0, S * 0.495, -S * 0.02);
      for (const x of [-0.10, 0.11]) {
        addMesh(new THREE.CylinderGeometry(S * 0.036, S * 0.048, S * 0.48, 8),
          material("#6a5140", 1), x * S, S * 0.62, -S * 0.03);
      }
      if (appearance.faith) {
        addMesh(new THREE.CylinderGeometry(S * 0.085, S * 0.10, S * 0.27, 9),
          stoneMat, -S * 0.29, S * 0.255, S * 0.10);
        addMesh(new THREE.SphereGeometry(S * 0.105, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2),
          roofMat, -S * 0.29, S * 0.40, S * 0.10, false);
      }
    } else if (appearance.era === 3 || appearance.faith) {
      addMesh(new THREE.CylinderGeometry(S * 0.14, S * 0.16, S * 0.43, 10),
        stoneMat, 0, S * 0.335, -S * 0.02);
      addMesh(new THREE.SphereGeometry(S * 0.17, 12, 7, 0, Math.PI * 2, 0, Math.PI / 2),
        roofMat, 0, S * 0.56, -S * 0.02, false);
      addMesh(new THREE.CylinderGeometry(S * 0.018, S * 0.018, S * 0.17, 6),
        accentMat, 0, S * 0.76, -S * 0.02, false);
    } else if (appearance.era >= 2) {
      addMesh(new THREE.CylinderGeometry(S * 0.13, S * 0.15, S * 0.82, 8),
        stoneMat, S * 0.04, S * 0.53, -S * 0.02);
      addMesh(new THREE.ConeGeometry(S * 0.19, S * 0.22, 8), roofMat,
        S * 0.04, S * 1.05, -S * 0.02, false);
    } else if (appearance.era === 1) {
      addMesh(new THREE.BoxGeometry(S * 0.39, S * 0.12, S * 0.28), facadeMat,
        0, S * 0.41, -S * 0.02);
      for (const x of [-0.14, -0.047, 0.047, 0.14])
        addMesh(new THREE.CylinderGeometry(S * 0.022, S * 0.025, S * 0.35, 7),
          stoneMat, x * S, S * 0.245, S * 0.11);
      const hallRoof = addMesh(new THREE.ConeGeometry(S * 0.30, S * 0.16, 4), roofMat,
        0, S * 0.55, -S * 0.02, false);
      hallRoof.rotation.y = Math.PI / 4;
    }

    if (appearance.wonder) {
      addMesh(new THREE.ConeGeometry(S * 0.055, S * 0.40, 7), accentMat,
        -S * 0.22, S * 0.62, -S * 0.14, false);
      const halo = addMesh(new THREE.TorusGeometry(S * 0.12, S * 0.018, 5, 18), accentMat,
        -S * 0.22, S * 0.92, -S * 0.14, false);
      halo.rotation.x = Math.PI / 2;
    }

    addMesh(new THREE.CylinderGeometry(S * 0.013, S * 0.013, S * 0.43, 6),
      accentMat, S * 0.29, S * 0.78, S * 0.03, false);
    addMesh(new THREE.BoxGeometry(S * 0.20, S * 0.11, S * 0.018),
      civMat, S * 0.39, S * 0.90, S * 0.03, false);
    return model;
  }

  _syncCities(game) {
    const vis = game.players[game.viewer].visible;
    const S = this.hexSize;
    for (const [c, gr] of this._cities) {
      if (!game.cities.includes(c)) {
        this._disposeCityGroup(gr);
        this.gDyn.remove(gr);
        this._cities.delete(c);
      }
    }
    for (const city of game.cities) {
      const v = vis[game.map.idx(city.c, city.r)];
      let gr = this._cities.get(city);
      if (v === 0) { if (gr) gr.visible = false; continue; }
      if (!gr) {
        gr = new THREE.Group();
        const banner = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false }));
        banner.name = "banner";
        gr.add(banner);
        this._cities.set(city, gr);
        this.gDyn.add(gr);
      }
      const player = game.players[city.owner];
      const obscured = v !== 2 && city.owner !== game.viewer;
      const appearance = CITY_ART.profile(city, player, obscured);
      if (gr.userData.appearance !== appearance.signature) {
        const prior = gr.getObjectByName("model");
        if (prior) { gr.remove(prior); this._disposeCityModel(prior); }
        gr.add(this._buildCityModel(appearance, S));
        gr.userData.appearance = appearance.signature;
      }
      gr.visible = true;
      const [wx, wz] = HEX.toPixel(city.c, city.r, S);
      const top = ELEV3D[game.tile(city.c, city.r).terrain];
      gr.position.set(wx, top, wz);
      const model = gr.getObjectByName("model");
      const opacity = v === 1 ? 0.52 : 1;
      if (model) model.traverse(object => {
        if (!object.isMesh) return;
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        for (const material of materials) {
          material.opacity = opacity;
          material.depthWrite = opacity === 1;
        }
      });
      const banner = gr.getObjectByName("banner");
      const tex = this._bannerTex(city, game);
      banner.material.map = tex;
      banner.material.opacity = v === 1 ? 0.6 : 1;
      const bh = S * 0.9, bw = bh * tex.userData.w / tex.userData.h;
      banner.scale.set(bw, bh, 1);
      banner.position.set(0, S * 1.72, 0);
      banner.renderOrder = 6;
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
      let piece = this._units.get(u.id);
      if (!piece) {
        piece = new THREE.Group();
        const outer = new THREE.Mesh(this._unitGeo.outer,
          new THREE.MeshStandardMaterial({ roughness: 0.76, metalness: 0.05, transparent: true }));
        outer.name = "base-outer";
        outer.position.y = S * 0.05;
        outer.castShadow = true;
        const inner = new THREE.Mesh(this._unitGeo.inner,
          new THREE.MeshStandardMaterial({ roughness: 0.72, metalness: 0.04, transparent: true }));
        inner.name = "base-inner";
        inner.position.y = S * 0.09;
        inner.castShadow = true;
        const center = new THREE.Mesh(this._unitGeo.center,
          new THREE.MeshStandardMaterial({ color: 0x202724, roughness: 0.9, transparent: true }));
        center.name = "base-center";
        center.position.y = S * 0.13;
        const art = new THREE.Sprite(new THREE.SpriteMaterial({ transparent: true, depthWrite: false }));
        art.name = "art";
        art.center.set(0.5, 0.12);
        art.position.set(0, S * 0.25, 0);
        art.scale.set(S * 0.82, S, 1);
        art.renderOrder = 5;
        piece.add(outer, inner, center, art);
        this._units.set(u.id, piece);
        this.gDyn.add(piece);
      }
      piece.visible = true;
      const civ = CIVS[game.players[u.owner].civId];
      const spent = u.owner === game.viewer && u.moves <= 0;
      const opacity = spent ? 0.58 : 1;
      const outer = piece.getObjectByName("base-outer");
      const inner = piece.getObjectByName("base-inner");
      const center = piece.getObjectByName("base-center");
      const art = piece.getObjectByName("art");
      outer.material.color.set(u.owner === game.viewer ? "#f7f0dc" : civ.color2);
      inner.material.color.set(civ.color);
      for (const mesh of [outer, inner, center]) {
        mesh.material.opacity = opacity;
        mesh.material.depthWrite = opacity === 1;
      }
      art.material.map = this._unitTex(u, game);
      art.material.opacity = opacity;
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
      piece.position.set(wx, y + 0.35, wz);
    }
    for (const [id, piece] of this._units) {
      if (!seen.has(id)) piece.visible = false;
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
      const op = v === 1 ? 0.62 : 1;
      const tint = v === 1 ? 0x9ba9a4 : 0xffffff;
      if (t.resource) this._spriteAt(this._pool.decor, this._worldTex("resource", t.resource), wx - S * 0.48, y + S * 0.34, wz - S * 0.34, S * 0.54, S * 0.54, op, tint);
      if (t.ruin) this._spriteAt(this._pool.decor, this._worldTex("site", "RUIN"), wx, y + S * 0.34, wz, S * 0.66, S * 0.66, op, tint);
      if (game.campAt && game.campAt(t.c, t.r)) this._spriteAt(this._pool.decor, this._worldTex("site", "CAMP"), wx, y + S * 0.39, wz, S * 0.78, S * 0.78, op, tint);
      if (t.improvement === "MINE") this._spriteAt(this._pool.decor, this._worldTex("site", "MINE"), wx + S * 0.38, y + S * 0.28, wz + S * 0.3, S * 0.48, S * 0.48, op, tint);
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
    this._hidePool(this._pool.zoc);
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
      for (const [c, r] of this.controlled) {
        const m = this._getPooled(this._pool.zoc, () => {
          const mesh = new THREE.Mesh(new THREE.RingGeometry(S * 0.66, S * 0.78, 6, 1, Math.PI / 6),
            this._matZoc);
          mesh.rotation.x = -Math.PI / 2;
          mesh.renderOrder = 3;
          return mesh;
        });
        const [wx, wz] = HEX.toPixel(c, r, S);
        m.position.set(wx, surfY3D(game.tile(c, r)) + 0.72, wz);
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
        new THREE.RingGeometry(S * 0.47, S * 0.58, 32),
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
      const pulse = this.reduceMotion ? 0 : (Math.sin(Date.now() * 0.007) + 1) / 2;
      const scale = 1 + pulse * 0.075;
      this._selRing.scale.set(scale, scale, scale);
      this._selRing.material.opacity = this.reduceMotion ? 1 : 0.68 + pulse * 0.32;
      this._selRing.position.set(wx, surfY3D(game.tile(this.selected.c, this.selected.r)) + 0.62, wz);
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
      impHash = (impHash * 31 + (t.road ? 1 : 0) + (t.river ? 8 : 0) +
        (t.improvement === "FARM" ? 2 : t.improvement === "MINE" ? 4 : 0)) >>> 0;
    }
    if (visChanged || ownChanged) {
      this._recolor(game);
      this._visSnap = Uint8Array.from(vis);
      this._ownSnap = Int16Array.from(game.map.tiles, t => t.owner);
    }
    if (visChanged) this._rebuildShroud(game);
    if (visChanged || ownChanged) this._rebuildBorders(game);
    if (visChanged || ownChanged || impHash !== this._impHash) {
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
    if (this._foam) this._foam.visible = !this.reduceMotion;
    if (!this._sea || this.reduceMotion) return;
    const t = now * 0.0012;
    const posAttr = this._sea.geometry.getAttribute("position");
    for (let i = 0; i < posAttr.count; i++) {
      const x = posAttr.getX(i), y = posAttr.getY(i);
      posAttr.setZ(i, Math.sin(x * 0.016 + t * 1.4) * 0.34 + Math.cos(y * 0.021 + t) * 0.22);
    }
    posAttr.needsUpdate = true;
    this._sea.geometry.computeVertexNormals();
    if (this._foam) this._foam.material.opacity = 0.40 + (Math.sin(t * 2.2) + 1) * 0.12;
  }

  // the sun drifts slowly around the map as turns pass
  _sunCycle(game) {
    if (!this._center || this.reduceMotion) return;
    const az = ((game.turn % 80) / 80) * Math.PI * 2 + 0.6;
    this.sun.position.copy(this._center)
      .add(new THREE.Vector3(Math.cos(az) * 1300, 1500, Math.sin(az) * 1300));
    const warm = (Math.sin(az * 2) + 1) / 2;
    // The cycle may change temperature and direction, never strategic legibility.
    this.sun.intensity = 0.74 + (1 - warm) * 0.10;
    this.sun.color.setRGB(1, 0.97 - warm * 0.04, 0.91 - warm * 0.08);
  }

  drawMinimap(game) {
    const m = this.mctx;
    const fit = MINIMAP_ART.draw(m, this.mini, game);
    // Unproject the screen corners so rotation and perspective are reflected.
    const cw = this.canvas.width, ch = this.canvas.height;
    const pts = [[0, 0], [cw, 0], [cw, ch], [0, ch]].map(([px, py]) => {
      const hit = this._groundPoint(this._rayAt(px, py), 2.4);
      return hit ? fit.worldToMini(hit.x / this.hexSize, hit.z / this.hexSize) : null;
    });
    MINIMAP_ART.viewport(m, fit, pts);
    this._miniLayout = fit;
  }

  minimapToHex(game, x, y) {
    const fit = this._miniLayout || MINIMAP_ART.layout(game.map, this.mini.width, this.mini.height);
    return fit.miniToTile(x, y);
  }
}
