'use strict';
// Off-chain cost of H4 at an RP gateway: build a Merkle tree over n audit records, produce and check a proof.
const crypto = require('crypto');
const M = require('../lib/merkle');
const out = [];
for (const n of [1000, 10000, 100000]) {
  const recs = Array.from({ length: n }, (_, i) => JSON.stringify({ rp: 'BANK-1', nym: crypto.randomBytes(32).toString('hex'), list: 'L1', ver: 7, d: 'ALLOW', t: 1764300000 + i }));
  const reps = 5, tb = [], tv = [];
  let lv;
  for (let r = 0; r < reps; r++) {
    const t0 = process.hrtime.bigint();
    lv = M.build(recs.map(M.leafHash));
    tb.push(Number(process.hrtime.bigint() - t0) / 1e6);
  }
  const root = M.root(lv);
  for (let r = 0; r < 1000; r++) {
    const i = (r * 7919) % n, pf = M.proof(lv, i);
    const t0 = process.hrtime.bigint();
    let h = lv[0][i];
    for (const s of pf) h = crypto.createHash('sha256').update(Buffer.from('01' + (s.left ? s.h + h : h + s.h), 'hex')).digest('hex');
    tv.push(Number(process.hrtime.bigint() - t0) / 1e6);
    if (h !== root) throw new Error('bad proof');
  }
  const med = a => a.sort((x, y) => x - y)[a.length >> 1];
  const pf = M.proof(lv, 0);
  out.push({ n, build_ms_median: +med(tb).toFixed(1), proof_hashes: pf.length, proof_bytes_json: JSON.stringify(pf).length, verify_us_median: +(med(tv) * 1000).toFixed(1) });
}
console.log(JSON.stringify(out, null, 1));
