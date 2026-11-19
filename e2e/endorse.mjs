// Ledger write benchmark for the endorsement-policy experiment (paper, Section 8.12).
// W client processes x C concurrent IssueCredential submissions each (submit = endorse + order + commit).
// usage: node endorse.mjs <label> <out.json> <txPerWorker> <concPerWorker> <workers>
import crypto from "node:crypto"; import fs from "node:fs"; import os from "node:os"; import { fileURLToPath } from "node:url";
import { connectGateway, now, stat, runWorkers, merge } from "./fabric.mjs";
async function worker(label, per, C, k) {
  const g = await connectGateway(); const run = `${label}-${process.pid}-${Date.now()}`; const T = { submit: [] }; const F = {};
  for (let i = 0; i < 5; i++) await g.contract.submitTransaction("IssueCredential", `w-${run}-${i}`, "did:bzt:w", "h", "nadra");
  process.send({ ready: true }); await new Promise(res => process.once("message", res));
  let next = 0;
  await Promise.all(Array.from({ length: C }, async () => { while (next < per) { const i = next++; const t = now();
    try { await g.contract.submitTransaction("IssueCredential", `c-${run}-${i}`, `did:bzt:${k}-${i}`, crypto.randomBytes(32).toString("hex"), "nadra"); T.submit.push(now() - t); }
    catch (e) { const m = String(e.details?.[0]?.message || e.message).slice(0, 60); F[m] = (F[m] || 0) + 1; } } }));
  process.send({ samples: T, failures: F, counts: { ok: T.submit.length } }); g.gw.close(); g.client.close(); process.exit(0);
}
const a = process.argv.slice(2);
if (process.send) await worker(a[0], +a[2], +a[3], +a[5]);
else {
  const [label, out, per, C, W] = a;
  const { wall, results } = await runWorkers(fileURLToPath(import.meta.url), +W, [label, out, per, C, W]);
  const { T, F, X } = merge(results);
  const res = { label, workers: +W, concurrency_per_worker: +C, submitted: +per * +W, committed: X.ok || 0, wall_s: +wall.toFixed(2), tx_per_s: +((X.ok || 0) / wall).toFixed(2),
    host: { cpu_model: os.cpus()[0]?.model, cpus: os.cpus().length }, failures: F, latency: stat(T.submit) };
  fs.writeFileSync(out, JSON.stringify(res, null, 1)); console.log(JSON.stringify(res, null, 1));
}
