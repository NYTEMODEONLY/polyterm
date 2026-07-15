// ============================================================
// Shared river topology for the Canvas and Three.js renderers
// ============================================================
"use strict";

const RIVER_ART = (() => {
  const isWater = (t) => !!t && (t.terrain === "OCEAN" || t.terrain === "COAST");

  function hash(c, r, salt = 0) {
    let h = Math.imul(c + 31 + salt * 17, 374761393) ^ Math.imul(r + 47, 668265263);
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return (h ^ (h >>> 16)) >>> 0;
  }

  function branches(game, tile) {
    if (!tile || !tile.river) return [];
    const visible = game.players[game.viewer].visible;
    return HEX.neighbors(tile.c, tile.r).map(([c, r], dir) => {
      const neighbor = game.tile(c, r);
      if (!neighbor || !visible[game.map.idx(c, r)] || (!neighbor.river && !isWater(neighbor))) return null;
      const sign = hash(tile.c, tile.r, dir) & 1 ? 1 : -1;
      return { tile: neighbor, dir, mouth: isWater(neighbor), bend: sign * (0.045 + (hash(tile.c, tile.r, dir + 9) % 4) * 0.012) };
    }).filter(Boolean);
  }

  function stubVector(tile) {
    const angle = ((hash(tile.c, tile.r) % 6) * Math.PI) / 3;
    return [Math.cos(angle), Math.sin(angle)];
  }

  return { branches, stubVector, isWater };
})();
