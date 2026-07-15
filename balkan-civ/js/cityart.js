"use strict";

// Shared city appearance rules keep the strategic information identical in
// both renderers. The canvas painter is also used by Classic 2D directly.
const CITY_ART = (() => {
  const STAGES = [
    { name: "Ancient", ground: "#3b3326", facade: "#b79b69", stone: "#7c6748", roof: "#7f5b32", accent: "#d0b36b" },
    { name: "Classical", ground: "#393531", facade: "#d3c6a8", stone: "#9d9079", roof: "#a34d35", accent: "#d8b56a" },
    { name: "Medieval", ground: "#323335", facade: "#c8c1b2", stone: "#817f79", roof: "#783a31", accent: "#d8b66a" },
    { name: "Renaissance", ground: "#30383a", facade: "#d8d0bd", stone: "#8f9a97", roof: "#356b69", accent: "#d7b65f" },
    { name: "Industrial", ground: "#2d3030", facade: "#ad8f74", stone: "#6e7370", roof: "#3d4647", accent: "#c79b45" },
  ];
  const FORTIFICATIONS = new Set(["WALLS", "CASTLE", "ARSENAL", "BRAN_CASTLE", "KALEMEGDAN"]);
  const FAITH_BUILDINGS = new Set(["SHRINE", "TEMPLE", "MOUNT_ATHOS", "HAGIA_SOPHIA", "STUDENICA", "RILA"]);
  const INDUSTRY_BUILDINGS = new Set(["WORKSHOP", "FACTORY", "ARSENAL", "IRON_GATES", "ORIENT_EXPRESS"]);
  const LAYOUT = [
    [-0.30, 0.10, 0.21, 0.35], [0.03, -0.16, 0.25, 0.48], [0.31, 0.12, 0.18, 0.31],
    [-0.06, 0.27, 0.20, 0.29], [-0.34, -0.20, 0.17, 0.28], [0.34, -0.18, 0.16, 0.25],
  ];

  function contains(buildings, key) {
    return buildings instanceof Set ? buildings.has(key) : buildings.includes(key);
  }

  function hasAny(buildings, keys) {
    for (const key of keys) if (contains(buildings, key)) return true;
    return false;
  }

  function hasWonder(buildings) {
    for (const key of buildings) if (BUILDINGS[key] && BUILDINGS[key].wonder) return true;
    return false;
  }

  function profile(city, player, obscured = false) {
    const buildings = city && city.buildings ? city.buildings : [];
    const era = obscured ? 0 : Math.max(0, Math.min(STAGES.length - 1,
      player && typeof player.era === "function" ? player.era() : 0));
    const pop = Math.max(1, Number(city && city.pop) || 1);
    const density = obscured ? 2 : Math.max(2, Math.min(LAYOUT.length, 2 + Math.floor((pop - 1) / 2)));
    const fortified = !obscured && hasAny(buildings, FORTIFICATIONS);
    const faith = !obscured && hasAny(buildings, FAITH_BUILDINGS);
    const industry = !obscured && (era >= 4 || hasAny(buildings, INDUSTRY_BUILDINGS));
    const wonder = !obscured && hasWonder(buildings);
    const capital = !!(city && city.isCapital);
    const civColor = player && player.civId && CIVS[player.civId] ? CIVS[player.civId].color : "#a33d32";
    return {
      era, stage: STAGES[era].name, density, fortified, faith, industry, wonder,
      capital, obscured, civColor, palette: STAGES[era],
      signature: [era, density, fortified ? 1 : 0, faith ? 1 : 0, industry ? 1 : 0,
        wonder ? 1 : 0, capital ? 1 : 0, obscured ? 1 : 0, civColor].join(":"),
    };
  }

  function roof(ctx, x, y, width, height, color, flat = false) {
    ctx.fillStyle = color;
    if (flat) {
      ctx.fillRect(x - width * 0.56, y - height * 0.08, width * 1.12, height * 0.13);
      return;
    }
    ctx.beginPath();
    ctx.moveTo(x - width * 0.62, y);
    ctx.lineTo(x, y - height * 0.42);
    ctx.lineTo(x + width * 0.62, y);
    ctx.closePath();
    ctx.fill();
  }

  function building(ctx, profile, x, baseline, width, height, index) {
    const p = profile.palette;
    const flat = profile.era >= 4 && index % 2 === 0;
    ctx.fillStyle = index % 3 === 0 ? p.stone : p.facade;
    ctx.fillRect(x - width / 2, baseline - height, width, height);
    roof(ctx, x, baseline - height, width, height, p.roof, flat);
    if (profile.era >= 1 && width > 5) {
      ctx.fillStyle = profile.era >= 4 ? "#d8b66a" : "rgba(35,32,28,0.55)";
      const windowY = baseline - height * 0.58;
      ctx.fillRect(x - width * 0.24, windowY, Math.max(1, width * 0.13), Math.max(1, height * 0.15));
      if (width > 9) ctx.fillRect(x + width * 0.11, windowY, Math.max(1, width * 0.13), Math.max(1, height * 0.15));
    }
  }

  function landmark(ctx, profile, sx, sy, s) {
    const p = profile.palette;
    const dome = (x, y, scale) => {
      ctx.fillStyle = p.stone;
      ctx.fillRect(x - s * 0.13 * scale, y - s * 0.33 * scale,
        s * 0.26 * scale, s * 0.34 * scale);
      ctx.fillStyle = p.roof;
      ctx.beginPath();
      ctx.arc(x, y - s * 0.34 * scale, s * 0.16 * scale, Math.PI, 0);
      ctx.fill();
      ctx.fillRect(x - s * 0.018 * scale, y - s * 0.58 * scale,
        s * 0.036 * scale, s * 0.12 * scale);
    };
    if (profile.industry) {
      ctx.fillStyle = p.facade;
      ctx.fillRect(sx - s * 0.15, sy - s * 0.31, s * 0.34, s * 0.34);
      ctx.fillStyle = p.roof;
      ctx.fillRect(sx - s * 0.18, sy - s * 0.34, s * 0.40, s * 0.07);
      for (const dx of [-0.09, 0.10]) {
        ctx.fillStyle = "#6a5140";
        ctx.fillRect(sx + dx * s, sy - s * 0.59, s * 0.065, s * 0.30);
        ctx.fillStyle = "#292d2d";
        ctx.fillRect(sx + dx * s - s * 0.012, sy - s * 0.61, s * 0.089, s * 0.035);
      }
      if (profile.faith) dome(sx - s * 0.29, sy + s * 0.09, 0.62);
    } else if (profile.era === 3 || profile.faith) {
      dome(sx, sy, 1);
    } else if (profile.era >= 2) {
      ctx.fillStyle = p.stone;
      ctx.fillRect(sx - s * 0.13, sy - s * 0.55, s * 0.26, s * 0.56);
      roof(ctx, sx, sy - s * 0.55, s * 0.29, s * 0.44, p.roof);
    } else if (profile.era === 1) {
      ctx.fillStyle = p.facade;
      ctx.fillRect(sx - s * 0.18, sy - s * 0.27, s * 0.36, s * 0.28);
      ctx.fillStyle = p.stone;
      for (const dx of [-0.12, -0.04, 0.04, 0.12]) ctx.fillRect(sx + dx * s, sy - s * 0.32, s * 0.035, s * 0.31);
      roof(ctx, sx, sy - s * 0.32, s * 0.43, s * 0.28, p.roof);
    }
  }

  function draw(ctx, profile, sx, sy, s) {
    const p = profile.palette;
    ctx.save();
    if (profile.obscured) ctx.globalAlpha *= 0.58;
    if (profile.fortified) {
      ctx.strokeStyle = p.stone;
      ctx.lineWidth = Math.max(2, s * 0.10);
      ctx.beginPath();
      ctx.ellipse(sx, sy + s * 0.13, s * 0.50, s * 0.30, 0, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = p.stone;
      for (const [dx, dy] of [[-0.43, 0.04], [0.43, 0.04], [-0.28, 0.33], [0.28, 0.33]])
        ctx.fillRect(sx + dx * s - s * 0.055, sy + dy * s - s * 0.12, s * 0.11, s * 0.19);
    }
    for (let i = profile.density - 1; i >= 0; i--) {
      const [dx, dy, width, height] = LAYOUT[i];
      building(ctx, profile, sx + dx * s, sy + (dy + 0.20) * s,
        width * s, height * s * (1 + profile.era * 0.035), i);
    }
    landmark(ctx, profile, sx, sy, s);
    if (profile.wonder) {
      ctx.strokeStyle = p.accent;
      ctx.lineWidth = Math.max(1.5, s * 0.045);
      ctx.beginPath();
      ctx.arc(sx, sy - s * 0.25, s * 0.40, Math.PI * 1.08, Math.PI * 1.92);
      ctx.stroke();
    }
    ctx.strokeStyle = p.accent;
    ctx.lineWidth = Math.max(1, s * 0.035);
    ctx.beginPath();
    ctx.moveTo(sx + s * 0.28, sy - s * 0.52);
    ctx.lineTo(sx + s * 0.28, sy - s * 0.82);
    ctx.stroke();
    ctx.fillStyle = profile.capital ? p.accent : profile.civColor;
    ctx.beginPath();
    ctx.moveTo(sx + s * 0.29, sy - s * 0.81);
    ctx.lineTo(sx + s * 0.50, sy - s * 0.73);
    ctx.lineTo(sx + s * 0.29, sy - s * 0.65);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  return { STAGES, profile, draw };
})();
