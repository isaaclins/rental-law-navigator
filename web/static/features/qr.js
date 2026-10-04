// A small QR code encoder for the letter and notice (features/paper.js): byte mode, error correction M, versions
// 1-10 (up to 213 bytes, plenty for a link). Follows ISO/IEC 18004 the way Project Nayuki's reference does: data
// and Reed-Solomon blocks, function patterns, the 8 masks scored by the 4 penalty rules. qr(text) -> {size, dark(x, y)}.

const ECC_M = [0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26]; // codewords per block, by version
const BLOCKS_M = [0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5];

const rawModules = (v) => {
  let r = (16 * v + 128) * v + 64;
  if (v >= 2) { const n = Math.floor(v / 7) + 2; r -= (25 * n - 10) * n - 55; if (v >= 7) r -= 36; }
  return r;
};
const dataCodewords = (v) => Math.floor(rawModules(v) / 8) - ECC_M[v] * BLOCKS_M[v];

const gmul = (x, y) => { let z = 0; for (let i = 7; i >= 0; i--) { z = (z << 1) ^ ((z >>> 7) * 0x11d); z ^= ((y >>> i) & 1) * x; } return z; };
function rsDivisor(deg) {
  const r = new Array(deg).fill(0); r[deg - 1] = 1;
  let root = 1;
  for (let i = 0; i < deg; i++) {
    for (let j = 0; j < r.length; j++) { r[j] = gmul(r[j], root); if (j + 1 < r.length) r[j] ^= r[j + 1]; }
    root = gmul(root, 2);
  }
  return r;
}
function rsRemainder(data, div) {
  const r = div.map(() => 0);
  for (const b of data) { const f = b ^ r.shift(); r.push(0); div.forEach((c, i) => (r[i] ^= gmul(c, f))); }
  return r;
}

export function qr(text) {
  const bytes = [...new TextEncoder().encode(text)];
  let v = 1;
  while (v <= 10 && 4 + (v < 10 ? 8 : 16) + bytes.length * 8 > dataCodewords(v) * 8) v++;
  if (v > 10) throw new Error("QR: text too long");
  // the bit stream: mode, length, data, terminator, padding
  const bits = [];
  const put = (val, n) => { for (let i = n - 1; i >= 0; i--) bits.push((val >>> i) & 1); };
  put(4, 4); put(bytes.length, v < 10 ? 8 : 16); bytes.forEach((b) => put(b, 8));
  const cap = dataCodewords(v) * 8;
  put(0, Math.min(4, cap - bits.length));
  put(0, (8 - (bits.length % 8)) % 8);
  for (let p = 0xec; bits.length < cap; p ^= 0xec ^ 0x11) put(p, 8);
  const data = [];
  for (let i = 0; i < bits.length; i += 8) data.push(bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
  // blocks + error correction, interleaved
  const nb = BLOCKS_M[v], ecl = ECC_M[v], raw = Math.floor(rawModules(v) / 8);
  const nShort = nb - (raw % nb), shortLen = Math.floor(raw / nb), div = rsDivisor(ecl);
  const blocks = [];
  for (let i = 0, k = 0; i < nb; i++) {
    const dat = data.slice(k, k + shortLen - ecl + (i < nShort ? 0 : 1));
    k += dat.length;
    const ecc = rsRemainder(dat, div);
    if (i < nShort) dat.push(0);
    blocks.push(dat.concat(ecc));
  }
  const cw = [];
  for (let i = 0; i < blocks[0].length; i++) blocks.forEach((b, j) => { if (i !== shortLen - ecl || j >= nShort) cw.push(b[i]); });

  // the matrix
  const size = v * 4 + 17;
  const M = Array.from({ length: size }, () => new Array(size).fill(false));
  const F = Array.from({ length: size }, () => new Array(size).fill(false));
  const fn = (x, y, d) => { M[y][x] = d; F[y][x] = true; };
  for (let i = 0; i < size; i++) { fn(6, i, i % 2 === 0); fn(i, 6, i % 2 === 0); }
  for (const [cx, cy] of [[3, 3], [size - 4, 3], [3, size - 4]]) {
    for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) {
      const x = cx + dx, y = cy + dy, d = Math.max(Math.abs(dx), Math.abs(dy));
      if (x >= 0 && x < size && y >= 0 && y < size) fn(x, y, d !== 2 && d !== 4);
    }
  }
  if (v > 1) {
    const n = Math.floor(v / 7) + 2, step = Math.ceil((v * 4 + 4) / (n * 2 - 2)) * 2, pos = [6];
    for (let p = size - 7; pos.length < n; p -= step) pos.splice(1, 0, p);
    pos.forEach((ax, i) => pos.forEach((ay, j) => {
      if ((i === 0 && j === 0) || (i === 0 && j === n - 1) || (i === n - 1 && j === 0)) return;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) fn(ax + dx, ay + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }));
  }
  const format = (mask) => {
    const d = mask; // ECC M = 0b00
    let r = d; for (let i = 0; i < 10; i++) r = (r << 1) ^ ((r >>> 9) * 0x537);
    const b = ((d << 10) | r) ^ 0x5412, bit = (i) => ((b >>> i) & 1) === 1;
    for (let i = 0; i <= 5; i++) fn(8, i, bit(i));
    fn(8, 7, bit(6)); fn(8, 8, bit(7)); fn(7, 8, bit(8));
    for (let i = 9; i < 15; i++) fn(14 - i, 8, bit(i));
    for (let i = 0; i < 8; i++) fn(size - 1 - i, 8, bit(i));
    for (let i = 8; i < 15; i++) fn(8, size - 15 + i, bit(i));
    fn(8, size - 8, true);
  };
  format(0); // reserve the format areas before placing data
  if (v >= 7) {
    let r = v; for (let i = 0; i < 12; i++) r = (r << 1) ^ ((r >>> 11) * 0x1f25);
    const b = (v << 12) | r;
    for (let i = 0; i < 18; i++) { const d = ((b >>> i) & 1) === 1, a = size - 11 + (i % 3), c = Math.floor(i / 3); fn(a, c, d); fn(c, a, d); }
  }
  let i = 0;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vert = 0; vert < size; vert++) for (let j = 0; j < 2; j++) {
      const x = right - j, y = ((right + 1) & 2) === 0 ? size - 1 - vert : vert;
      if (!F[y][x] && i < cw.length * 8) { M[y][x] = ((cw[i >>> 3] >>> (7 - (i & 7))) & 1) === 1; i++; }
    }
  }
  const MASKS = [
    (x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
    (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => ((x * y) % 2) + ((x * y) % 3) === 0,
    (x, y) => (((x * y) % 2) + ((x * y) % 3)) % 2 === 0, (x, y) => (((x + y) % 2) + ((x * y) % 3)) % 2 === 0,
  ];
  const apply = (m) => { for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) if (!F[y][x] && MASKS[m](x, y)) M[y][x] = !M[y][x]; };
  const penalty = () => {
    let p = 0, dark = 0;
    const line = (get) => {
      for (let a = 0; a < size; a++) {
        let run = 1;
        for (let b = 1; b <= size; b++) {
          if (b < size && get(a, b) === get(a, b - 1)) run++;
          else { if (run >= 5) p += 3 + run - 5; run = 1; }
        }
        for (let b = 0; b + 10 < size; b++) {
          const s = Array.from({ length: 11 }, (_, k) => (get(a, b + k) ? 1 : 0)).join("");
          if (s === "10111010000" || s === "00001011101") p += 40;
        }
      }
    };
    line((a, b) => M[a][b]); line((a, b) => M[b][a]);
    for (let y = 0; y < size - 1; y++) for (let x = 0; x < size - 1; x++) {
      const c = M[y][x];
      if (c === M[y][x + 1] && c === M[y + 1][x] && c === M[y + 1][x + 1]) p += 3;
    }
    for (const row of M) for (const c of row) if (c) dark++;
    const total = size * size;
    p += (Math.ceil(Math.abs(dark * 20 - total * 10) / total) - 1) * 10;
    return p;
  };
  let best = 0, bestP = Infinity;
  for (let m = 0; m < 8; m++) {
    apply(m); format(m);
    const p = penalty();
    if (p < bestP) { bestP = p; best = m; }
    apply(m); // undo (XOR)
  }
  apply(best); format(best);
  return { size, dark: (x, y) => M[y][x] };
}
