// ============================================================
// Shared code-native unit silhouettes for both map renderers.
// Coordinates are normalized to a 100x100 badge so the same art
// stays crisp in the 2D canvas and Three.js canvas textures.
// ============================================================
"use strict";

const UNIT_ART = (() => {
  function kind(def) {
    const n = def.name.toLowerCase();
    if (def.naval) return n.includes("ironclad") ? "steamship" : "ship";
    if (def.siege) return n.includes("cannon") ? "cannon" : "siege";
    if (def.caravan) return "caravan";
    if (def.missionary) return "missionary";
    if (def.great === "sci") return "scientist";
    if (def.great === "eng") return "engineer";
    if (def.great === "gen") return "general";
    if (n.includes("settler")) return "settler";
    if (def.worker) return "worker";
    if (n.includes("scout")) return "scout";
    if (n.includes("horse") || n.includes("knight") || n.includes("cavalry") ||
        n.includes("gusar") || n.includes("konnik") || n.includes("cataphract") ||
        n.includes("stradiot") || n.includes("călărași")) return "mounted";
    if (def.rs) return n.includes("crossbow") ? "crossbow" : n.includes("archer") || n.includes("bow") ? "archer" : "crossbow";
    if (n.includes("musket") || n.includes("rifle") || n.includes("janissary")) return "gunner";
    if (n.includes("spear") || n.includes("pike") || n.includes("guard")) return "spearman";
    return "infantry";
  }

  function person(ctx, x, y, scale = 1) {
    ctx.beginPath(); ctx.arc(x, y - 17 * scale, 7 * scale, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath();
    ctx.moveTo(x - 9 * scale, y - 8 * scale);
    ctx.lineTo(x + 9 * scale, y - 8 * scale);
    ctx.lineTo(x + 6 * scale, y + 15 * scale);
    ctx.lineTo(x - 6 * scale, y + 15 * scale);
    ctx.closePath(); ctx.fill();
  }

  function wheel(ctx, x, y, r) {
    ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath(); ctx.arc(x, y, r * 0.22, 0, Math.PI * 2); ctx.fill();
    for (let i = 0; i < 6; i++) {
      const a = i * Math.PI / 3;
      ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + Math.cos(a) * r, y + Math.sin(a) * r); ctx.stroke();
    }
  }

  function draw(ctx, def, cx, cy, size, color = "#f7edd8") {
    const k = kind(def);
    ctx.save();
    ctx.translate(cx - size / 2, cy - size / 2);
    ctx.scale(size / 100, size / 100);
    ctx.fillStyle = color;
    ctx.strokeStyle = color;
    ctx.lineWidth = 6;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    if (k === "settler") {
      ctx.beginPath(); ctx.moveTo(16, 76); ctx.lineTo(45, 28); ctx.lineTo(74, 76); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "rgba(20,20,20,0.55)";
      ctx.beginPath(); ctx.moveTo(41, 76); ctx.lineTo(54, 51); ctx.lineTo(61, 76); ctx.closePath(); ctx.fill();
      ctx.fillStyle = color; ctx.fillRect(72, 21, 5, 56);
      ctx.beginPath(); ctx.moveTo(77, 22); ctx.lineTo(94, 29); ctx.lineTo(77, 38); ctx.closePath(); ctx.fill();
    } else if (k === "worker") {
      person(ctx, 43, 55, 1.05);
      ctx.beginPath(); ctx.moveTo(57, 30); ctx.lineTo(83, 73); ctx.stroke();
      ctx.lineWidth = 8; ctx.beginPath(); ctx.arc(65, 29, 18, Math.PI * 1.05, Math.PI * 1.88); ctx.stroke();
    } else if (k === "scout") {
      ctx.beginPath(); ctx.arc(43, 32, 11, Math.PI, Math.PI * 2); ctx.lineTo(55, 46); ctx.lineTo(31, 46); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(32, 47); ctx.lineTo(55, 47); ctx.lineTo(62, 78); ctx.lineTo(25, 78); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(69, 23); ctx.lineTo(76, 80); ctx.stroke();
      ctx.beginPath(); ctx.arc(73, 20, 7, 0, Math.PI * 2); ctx.stroke();
    } else if (k === "archer") {
      person(ctx, 38, 55, 0.9);
      ctx.lineWidth = 5;
      ctx.beginPath(); ctx.arc(66, 51, 27, -Math.PI / 2, Math.PI / 2); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(66, 24); ctx.lineTo(66, 78); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(34, 50); ctx.lineTo(88, 50); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(88, 50); ctx.lineTo(78, 44); ctx.lineTo(78, 56); ctx.closePath(); ctx.fill();
    } else if (k === "crossbow") {
      person(ctx, 37, 57, 0.9);
      ctx.beginPath(); ctx.moveTo(39, 48); ctx.lineTo(88, 48); ctx.stroke();
      ctx.lineWidth = 5; ctx.beginPath(); ctx.arc(65, 48, 24, Math.PI * 1.12, Math.PI * 1.88); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(62, 48); ctx.lineTo(48, 68); ctx.stroke();
    } else if (k === "spearman") {
      person(ctx, 39, 57, 0.95);
      ctx.beginPath(); ctx.ellipse(56, 58, 15, 22, 0, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "rgba(20,20,20,0.5)"; ctx.beginPath(); ctx.arc(56, 58, 5, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(75, 15); ctx.lineTo(84, 31); ctx.lineTo(73, 29); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(77, 27); ctx.lineTo(70, 82); ctx.stroke();
    } else if (k === "mounted") {
      ctx.beginPath();
      ctx.ellipse(48, 61, 29, 17, -0.08, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.moveTo(68, 52); ctx.lineTo(78, 33); ctx.lineTo(87, 38); ctx.lineTo(78, 62); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.arc(86, 35, 7, 0, Math.PI * 2); ctx.fill();
      ctx.lineWidth = 7;
      for (const x of [31, 48, 65]) { ctx.beginPath(); ctx.moveTo(x, 72); ctx.lineTo(x - 3, 87); ctx.stroke(); }
      person(ctx, 48, 35, 0.72);
      ctx.beginPath(); ctx.moveTo(56, 28); ctx.lineTo(76, 17); ctx.stroke();
    } else if (k === "gunner") {
      person(ctx, 37, 56, 1);
      ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(42, 48); ctx.lineTo(82, 35); ctx.stroke();
      ctx.lineWidth = 4; ctx.beginPath(); ctx.moveTo(73, 38); ctx.lineTo(82, 57); ctx.stroke();
    } else if (k === "infantry") {
      person(ctx, 42, 57, 1);
      ctx.beginPath(); ctx.moveTo(61, 27); ctx.lineTo(79, 18); ctx.lineTo(68, 37); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(69, 29); ctx.lineTo(58, 77); ctx.stroke();
      ctx.beginPath(); ctx.ellipse(37, 59, 13, 19, 0, 0, Math.PI * 2); ctx.stroke();
    } else if (k === "siege") {
      wheel(ctx, 31, 70, 13); wheel(ctx, 68, 70, 13);
      ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(29, 62); ctx.lineTo(71, 62); ctx.stroke();
      ctx.lineWidth = 7; ctx.beginPath(); ctx.moveTo(51, 58); ctx.lineTo(70, 20); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(62, 22); ctx.lineTo(79, 17); ctx.lineTo(72, 34); ctx.closePath(); ctx.fill();
    } else if (k === "cannon") {
      wheel(ctx, 34, 70, 14); wheel(ctx, 66, 70, 14);
      ctx.lineWidth = 14; ctx.beginPath(); ctx.moveTo(25, 52); ctx.lineTo(72, 48); ctx.stroke();
      ctx.lineWidth = 9; ctx.beginPath(); ctx.moveTo(68, 48); ctx.lineTo(87, 38); ctx.stroke();
      ctx.beginPath(); ctx.arc(23, 52, 8, 0, Math.PI * 2); ctx.fill();
    } else if (k === "ship" || k === "steamship") {
      ctx.beginPath(); ctx.moveTo(12, 64); ctx.lineTo(88, 64); ctx.lineTo(75, 80); ctx.lineTo(29, 80); ctx.closePath(); ctx.fill();
      ctx.fillRect(48, 19, 5, 48);
      if (k === "ship") {
        ctx.beginPath(); ctx.moveTo(47, 23); ctx.lineTo(20, 58); ctx.lineTo(47, 58); ctx.closePath(); ctx.fill();
        ctx.beginPath(); ctx.moveTo(55, 29); ctx.lineTo(78, 58); ctx.lineTo(55, 58); ctx.closePath(); ctx.fill();
      } else {
        ctx.fillRect(29, 48, 43, 17); ctx.fillRect(39, 31, 12, 18); ctx.fillRect(58, 25, 10, 24);
        ctx.beginPath(); ctx.moveTo(62, 19); ctx.bezierCurveTo(74, 12, 77, 28, 84, 18); ctx.stroke();
      }
      ctx.beginPath(); ctx.moveTo(16, 86); ctx.bezierCurveTo(30, 78, 40, 92, 52, 85); ctx.bezierCurveTo(66, 77, 77, 91, 88, 84); ctx.stroke();
    } else if (k === "caravan") {
      ctx.beginPath(); ctx.ellipse(45, 59, 25, 14, 0, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.moveTo(62, 54); ctx.lineTo(72, 32); ctx.lineTo(81, 38); ctx.lineTo(72, 61); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.arc(81, 34, 7, 0, Math.PI * 2); ctx.fill();
      ctx.lineWidth = 7; for (const x of [30, 55, 69]) { ctx.beginPath(); ctx.moveTo(x, 67); ctx.lineTo(x - 2, 84); ctx.stroke(); }
      ctx.fillStyle = "rgba(20,20,20,0.48)"; ctx.fillRect(32, 47, 25, 14);
    } else if (k === "missionary") {
      ctx.beginPath(); ctx.arc(50, 27, 9, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.moveTo(40, 38); ctx.lineTo(60, 38); ctx.lineTo(74, 82); ctx.lineTo(26, 82); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "rgba(20,20,20,0.5)"; ctx.fillRect(47, 46, 6, 25); ctx.fillRect(39, 53, 22, 6);
    } else {
      person(ctx, 47, 57, 1.05);
      ctx.beginPath(); ctx.arc(47, 55, 27, 0, Math.PI * 2); ctx.stroke();
      if (k === "scientist") { ctx.beginPath(); ctx.arc(72, 31, 9, 0, Math.PI * 2); ctx.stroke(); ctx.beginPath(); ctx.moveTo(66, 38); ctx.lineTo(56, 52); ctx.stroke(); }
      if (k === "engineer") { wheel(ctx, 72, 33, 11); }
      if (k === "general") { ctx.beginPath(); ctx.moveTo(72, 19); ctx.lineTo(76, 31); ctx.lineTo(89, 31); ctx.lineTo(79, 39); ctx.lineTo(83, 52); ctx.lineTo(72, 44); ctx.lineTo(61, 52); ctx.lineTo(65, 39); ctx.lineTo(55, 31); ctx.lineTo(68, 31); ctx.closePath(); ctx.fill(); }
    }
    ctx.restore();
  }

  return { draw, kind };
})();
