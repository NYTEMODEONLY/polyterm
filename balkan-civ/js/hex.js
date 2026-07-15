// ============================================================
// Hex grid math — pointy-top hexes, odd-r offset coordinates
// ============================================================
"use strict";

const HEX = (() => {
  const DIRS = [
    // even rows
    [[+1, 0], [0, -1], [-1, -1], [-1, 0], [-1, +1], [0, +1]],
    // odd rows
    [[+1, 0], [+1, -1], [0, -1], [-1, 0], [0, +1], [+1, +1]],
  ];

  function neighbors(col, row) {
    const parity = row & 1;
    const out = [];
    for (const [dc, dr] of DIRS[parity]) out.push([col + dc, row + dr]);
    return out;
  }

  function toCube(col, row) {
    const x = col - (row - (row & 1)) / 2;
    const z = row;
    return [x, -x - z, z];
  }

  function distance(c1, r1, c2, r2) {
    const [x1, y1, z1] = toCube(c1, r1);
    const [x2, y2, z2] = toCube(c2, r2);
    return Math.max(Math.abs(x1 - x2), Math.abs(y1 - y2), Math.abs(z1 - z2));
  }

  // Pixel position of hex centre (pointy-top)
  function toPixel(col, row, size) {
    const x = size * Math.sqrt(3) * (col + 0.5 * (row & 1));
    const y = size * 1.5 * row;
    return [x, y];
  }

  // Inverse: pixel -> nearest hex (via cube rounding)
  function fromPixel(px, py, size) {
    const q = (Math.sqrt(3) / 3 * px - 1 / 3 * py) / size;
    const r = (2 / 3 * py) / size;
    // cube round
    let x = q, z = r, y = -x - z;
    let rx = Math.round(x), ry = Math.round(y), rz = Math.round(z);
    const dx = Math.abs(rx - x), dy = Math.abs(ry - y), dz = Math.abs(rz - z);
    if (dx > dy && dx > dz) rx = -ry - rz;
    else if (dy > dz) ry = -rx - rz;
    else rz = -rx - ry;
    const row = rz;
    const col = rx + (rz - (rz & 1)) / 2;
    return [col, row];
  }

  // All hexes within `radius` of (col,row)
  function ring(col, row, radius) {
    const out = [];
    const [cx, , cz] = toCube(col, row);
    for (let dx = -radius; dx <= radius; dx++) {
      for (let dz = Math.max(-radius, -dx - radius); dz <= Math.min(radius, -dx + radius); dz++) {
        const x = cx + dx, z = cz + dz;
        const rrow = z;
        const rcol = x + (z - (z & 1)) / 2;
        out.push([rcol, rrow]);
      }
    }
    return out;
  }

  function corners(cx, cy, size) {
    const pts = [];
    for (let i = 0; i < 6; i++) {
      const angle = Math.PI / 180 * (60 * i - 30);
      pts.push([cx + size * Math.cos(angle), cy + size * Math.sin(angle)]);
    }
    return pts;
  }

  return { neighbors, distance, toPixel, fromPixel, ring, corners, DIRS };
})();
