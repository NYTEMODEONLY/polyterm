// ============================================================
// Shared illustrated map symbols for resources and world sites.
// Kept code-native so both renderers remain crisp and offline.
// ============================================================
"use strict";

const WORLD_ART = (() => {
  function line(ctx, color, width = 6) {
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
  }

  function resource(ctx, type, cx, cy, size) {
    ctx.save();
    ctx.translate(cx - size / 2, cy - size / 2);
    ctx.scale(size / 100, size / 100);

    if (type === "WHEAT") {
      line(ctx, "#6f5522", 5);
      for (const x of [36, 50, 64]) {
        ctx.beginPath(); ctx.moveTo(x, 84); ctx.lineTo(x, 26); ctx.stroke();
        ctx.fillStyle = "#e6b94e";
        for (let y = 29; y < 65; y += 11) {
          ctx.beginPath(); ctx.ellipse(x - 7, y, 8, 4, 0.55, 0, Math.PI * 2); ctx.fill();
          ctx.beginPath(); ctx.ellipse(x + 7, y + 5, 8, 4, -0.55, 0, Math.PI * 2); ctx.fill();
        }
      }
    } else if (type === "SHEEP") {
      ctx.fillStyle = "#f1ead9";
      for (const [x, y, r] of [[42,51,18],[56,48,19],[67,56,16],[49,63,17],[32,60,13]]) {
        ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill();
      }
      ctx.fillStyle = "#353b37";
      ctx.beginPath(); ctx.ellipse(76, 58, 12, 10, 0.2, 0, Math.PI * 2); ctx.fill();
      ctx.fillRect(33, 70, 6, 17); ctx.fillRect(62, 70, 6, 17);
    } else if (type === "HORSES") {
      ctx.fillStyle = "#8b532f";
      ctx.beginPath(); ctx.ellipse(47, 57, 29, 17, -0.08, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.moveTo(67, 51); ctx.lineTo(77, 30); ctx.lineTo(87, 35); ctx.lineTo(76, 62); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.arc(86, 32, 7, 0, Math.PI * 2); ctx.fill();
      line(ctx, "#6b3824", 7);
      for (const x of [31, 48, 65]) { ctx.beginPath(); ctx.moveTo(x, 69); ctx.lineTo(x - 2, 87); ctx.stroke(); }
      line(ctx, "#33251f", 5); ctx.beginPath(); ctx.moveTo(20, 49); ctx.quadraticCurveTo(10, 57, 18, 69); ctx.stroke();
    } else if (type === "IRON") {
      ctx.fillStyle = "#687177";
      for (const [x, y, r] of [[33,65,19],[55,55,25],[74,68,17]]) {
        ctx.beginPath(); ctx.moveTo(x-r,y+r*.6); ctx.lineTo(x-r*.6,y-r*.5); ctx.lineTo(x+r*.15,y-r); ctx.lineTo(x+r,y-r*.1); ctx.lineTo(x+r*.7,y+r*.65); ctx.closePath(); ctx.fill();
      }
      ctx.fillStyle = "#c6d0d1"; ctx.beginPath(); ctx.moveTo(48,41); ctx.lineTo(59,32); ctx.lineTo(67,48); ctx.closePath(); ctx.fill();
    } else if (type === "WINE") {
      ctx.fillStyle = "#6e315f";
      for (const [x,y] of [[44,44],[57,44],[37,56],[50,56],[63,56],[43,68],[57,68],[50,80]]) {
        ctx.beginPath(); ctx.arc(x,y,9,0,Math.PI*2); ctx.fill();
      }
      ctx.fillStyle = "#47713b"; ctx.beginPath(); ctx.ellipse(67,31,18,10,-0.5,0,Math.PI*2); ctx.fill();
      line(ctx,"#5b4a2b",5); ctx.beginPath(); ctx.moveTo(52,37); ctx.lineTo(58,21); ctx.stroke();
    } else if (type === "SILVER") {
      ctx.fillStyle = "#cad5d8";
      for (const [x,y,r] of [[34,67,18],[53,52,24],[73,69,17]]) {
        ctx.beginPath(); ctx.moveTo(x-r,y+r*.5); ctx.lineTo(x-r*.5,y-r*.6); ctx.lineTo(x+r*.25,y-r); ctx.lineTo(x+r,y); ctx.lineTo(x+r*.6,y+r*.65); ctx.closePath(); ctx.fill();
      }
      ctx.strokeStyle = "#f5fbf7"; ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(45,45); ctx.lineTo(57,38); ctx.stroke();
    } else if (type === "OLIVES") {
      line(ctx, "#755a32", 6); ctx.beginPath(); ctx.moveTo(22,78); ctx.quadraticCurveTo(45,54,76,24); ctx.stroke();
      ctx.fillStyle = "#5f813c";
      for (const [x,y,a] of [[35,65,-.6],[46,55,.55],[56,45,-.55],[67,34,.5],[61,60,.5]]) {
        ctx.beginPath(); ctx.ellipse(x,y,13,6,a,0,Math.PI*2); ctx.fill();
      }
      ctx.fillStyle = "#273d25";
      for (const [x,y] of [[40,70],[52,59],[63,48],[72,38]]) { ctx.beginPath(); ctx.ellipse(x,y,6,9,-.4,0,Math.PI*2); ctx.fill(); }
    } else if (type === "SALT") {
      ctx.fillStyle = "#e7f1ed"; ctx.strokeStyle = "#9fc3c8"; ctx.lineWidth = 4;
      for (const [x,y,s] of [[35,61,25],[57,48,29],[70,69,20]]) {
        ctx.beginPath(); ctx.moveTo(x,y-s); ctx.lineTo(x+s*.7,y-s*.15); ctx.lineTo(x+s*.55,y+s*.65); ctx.lineTo(x-s*.55,y+s*.65); ctx.lineTo(x-s*.7,y-s*.15); ctx.closePath(); ctx.fill(); ctx.stroke();
      }
    } else if (type === "FISH") {
      ctx.fillStyle = "#4f90a7";
      ctx.beginPath(); ctx.ellipse(49,54,29,17,0,0,Math.PI*2); ctx.fill();
      ctx.beginPath(); ctx.moveTo(20,54); ctx.lineTo(7,38); ctx.lineTo(7,70); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#e7f3e9"; ctx.beginPath(); ctx.arc(63,49,4,0,Math.PI*2); ctx.fill();
      line(ctx,"#b9d8d6",4); ctx.beginPath(); ctx.arc(42,54,15,-1.1,1.1); ctx.stroke();
    }
    ctx.restore();
  }

  function site(ctx, kind, cx, cy, size) {
    ctx.save();
    ctx.translate(cx - size / 2, cy - size / 2);
    ctx.scale(size / 100, size / 100);
    if (kind === "RUIN") {
      ctx.fillStyle = "#c3b48e";
      ctx.fillRect(21,72,64,10); ctx.fillRect(28,30,12,42); ctx.fillRect(61,24,13,48);
      ctx.beginPath(); ctx.moveTo(22,31); ctx.lineTo(43,20); ctx.lineTo(43,31); ctx.closePath(); ctx.fill();
      ctx.beginPath(); ctx.moveTo(56,25); ctx.lineTo(79,15); ctx.lineTo(79,25); ctx.closePath(); ctx.fill();
    } else if (kind === "CAMP") {
      ctx.fillStyle = "#d6b37a"; ctx.beginPath(); ctx.moveTo(12,79); ctx.lineTo(48,25); ctx.lineTo(84,79); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#552f28"; ctx.beginPath(); ctx.moveTo(43,79); ctx.lineTo(58,54); ctx.lineTo(66,79); ctx.closePath(); ctx.fill();
      line(ctx,"#6d4c2e",5); ctx.beginPath(); ctx.moveTo(83,26); ctx.lineTo(83,82); ctx.stroke();
      ctx.fillStyle="#9b3e2c"; ctx.fillRect(83,28,14,11);
    } else if (kind === "MINE") {
      ctx.fillStyle = "#3a3530"; ctx.beginPath(); ctx.arc(50,78,34,Math.PI,Math.PI*2); ctx.lineTo(84,84); ctx.lineTo(16,84); ctx.closePath(); ctx.fill();
      ctx.fillStyle = "#111716"; ctx.beginPath(); ctx.arc(50,79,18,Math.PI,Math.PI*2); ctx.lineTo(68,84); ctx.lineTo(32,84); ctx.closePath(); ctx.fill();
      line(ctx,"#c7a25e",7); ctx.beginPath(); ctx.moveTo(27,67); ctx.lineTo(72,28); ctx.stroke();
      line(ctx,"#d8c49c",7); ctx.beginPath(); ctx.arc(65,29,18,Math.PI*1.05,Math.PI*1.88); ctx.stroke();
    }
    ctx.restore();
  }

  // Compact food / production / gold markers shared by the strategic lens in
  // both renderers. Shape as well as colour identifies each yield so the lens
  // remains readable with the colourblind palette enabled.
  function yields(ctx, values, cx, cy, size) {
    const tokens = [
      { value: values.food, color: "#6f9f4a", shape: "circle" },
      { value: values.prod, color: "#a56f43", shape: "square" },
      { value: values.gold, color: "#d0a63c", shape: "diamond" },
    ].filter(t => t.value > 0);
    if (!tokens.length) return;

    const gap = size * 0.84;
    const start = cx - (tokens.length - 1) * gap / 2;
    const r = size * 0.38;
    const path = (shape, x, y) => {
      const rr = r;
      ctx.beginPath();
      if (shape === "circle") {
        ctx.arc(x, y, rr, 0, Math.PI * 2);
      } else if (shape === "square") {
        ctx.rect(x - rr, y - rr, rr * 2, rr * 2);
      } else {
        ctx.moveTo(x, y - rr); ctx.lineTo(x + rr, y);
        ctx.lineTo(x, y + rr); ctx.lineTo(x - rr, y); ctx.closePath();
      }
    };

    ctx.save();
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = `800 ${Math.round(size * 0.55)}px 'Segoe UI', sans-serif`;
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i], x = start + i * gap;
      ctx.shadowColor = "rgba(0,0,0,0.72)";
      ctx.shadowBlur = Math.max(2, size * 0.13);
      path(token.shape, x, cy);
      ctx.fillStyle = token.color;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.lineWidth = Math.max(1.5, size * 0.09);
      ctx.strokeStyle = "rgba(245,238,214,0.9)";
      ctx.stroke();
      ctx.fillStyle = "#fff9e8";
      ctx.strokeStyle = "rgba(25,20,14,0.76)";
      ctx.lineWidth = Math.max(1.5, size * 0.1);
      ctx.strokeText(String(token.value), x, cy + size * 0.02);
      ctx.fillText(String(token.value), x, cy + size * 0.02);
    }
    ctx.restore();
  }

  return { resource, site, yields };
})();
