// Groth16 (snarkjs) age-range proof benchmark on CPU. usage: node bench_zk.js <wasm> <zkey> <vkey.json> <out.json>
const snarkjs = require("snarkjs"); const { buildPoseidon } = require("circomlibjs"); const fs = require("fs");
const [wasm, zkey, vkeyPath, outPath] = process.argv.slice(2);
const stat = a => { const s = [...a].sort((x, y) => x - y); const m = a.reduce((p, c) => p + c, 0) / a.length; return { n: a.length, mean_ms: +m.toFixed(1), p50_ms: +s[Math.floor(s.length * .5)].toFixed(1), p95_ms: +s[Math.floor(s.length * .95)].toFixed(1), min_ms: +s[0].toFixed(1), max_ms: +s[s.length - 1].toFixed(1) }; };
(async () => {
  const poseidon = await buildPoseidon(); const F = poseidon.F; const vkey = JSON.parse(fs.readFileSync(vkeyPath));
  const prove = [], verify = []; let last;
  for (let i = 0; i < 25; i++) {
    const dob = 25000 + i, salt = 1000003 + i * 7919, today = 46300, minDays = 6575;   // all adults
    const commitment = F.toString(poseidon([dob, salt]));
    const input = { dob, salt, commitment, today, minDays };
    let t = process.hrtime.bigint(); const { proof, publicSignals } = await snarkjs.groth16.fullProve(input, wasm, zkey); prove.push(Number(process.hrtime.bigint() - t) / 1e6);
    t = process.hrtime.bigint(); const ok = await snarkjs.groth16.verify(vkey, publicSignals, proof); verify.push(Number(process.hrtime.bigint() - t) / 1e6);
    if (!ok) throw new Error("verification failed"); last = { proof, publicSignals };
  }
  // soundness check: a minor must not be provable
  let minorRejected = false; try { await snarkjs.groth16.fullProve({ dob: 45000, salt: 5, commitment: F.toString(poseidon([45000, 5])), today: 46300, minDays: 6575 }, wasm, zkey); } catch (e) { minorRejected = true; }
  const proofBytes = Buffer.byteLength(JSON.stringify(last.proof));
  const r = { circuit: "Poseidon commitment + 32-bit age comparison", prove: stat(prove.slice(1)), verify: stat(verify.slice(1)), proof_json_bytes: proofBytes, public_signals: last.publicSignals.length, minor_witness_rejected: minorRejected, note: "first iteration (warm-up) excluded" };
  fs.writeFileSync(outPath, JSON.stringify(r, null, 1)); console.log(JSON.stringify(r, null, 1)); process.exit(0);
})();
