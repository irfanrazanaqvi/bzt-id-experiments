'use strict';
// Off-chain Merkle helper used by an RP gateway (H4). Leaves are SHA-256(0x00 || record);
// internal nodes SHA-256(0x01 || left || right); an odd node is promoted unchanged.
const crypto = require('crypto');
const H = b => crypto.createHash('sha256').update(b).digest('hex');
const leafHash = rec => H(Buffer.concat([Buffer.from([0]), Buffer.from(rec)]));
const node = (a, b) => H(Buffer.from('01' + a + b, 'hex'));
function build(leaves) {
  const levels = [leaves.slice()];
  while (levels[levels.length - 1].length > 1) {
    const cur = levels[levels.length - 1], nxt = [];
    for (let i = 0; i < cur.length; i += 2) nxt.push(i + 1 < cur.length ? node(cur[i], cur[i + 1]) : cur[i]);
    levels.push(nxt);
  }
  return levels;
}
function proof(levels, idx) {
  const out = [];
  for (let l = 0; l < levels.length - 1; l++) {
    const cur = levels[l], sib = idx ^ 1;
    if (sib < cur.length) out.push({ h: cur[sib], left: sib < idx });
    idx >>= 1;
  }
  return out;
}
module.exports = { leafHash, build, proof, root: lv => lv[lv.length - 1][0] };
