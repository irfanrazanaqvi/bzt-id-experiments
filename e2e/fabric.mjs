// Fabric Gateway connection to peer0.org1 of the fabric-samples test-network ($TN).
import crypto from "node:crypto"; import fs from "node:fs"; import path from "node:path";
export async function connectGateway() {
  const grpc = await import("@grpc/grpc-js"); const { connect, signers } = await import("@hyperledger/fabric-gateway");
  const TN = process.env.TN; const O1 = path.join(TN, "organizations/peerOrganizations/org1.example.com");
  const tls = fs.readFileSync(path.join(O1, "peers/peer0.org1.example.com/tls/ca.crt"));
  const client = new grpc.Client("localhost:7051", grpc.credentials.createSsl(tls), { "grpc.ssl_target_name_override": "peer0.org1.example.com" });
  const mspDir = path.join(O1, "users/User1@org1.example.com/msp");
  const certFile = fs.readdirSync(path.join(mspDir, "signcerts"))[0]; const keyFile = fs.readdirSync(path.join(mspDir, "keystore"))[0];
  const identity = { mspId: "Org1MSP", credentials: fs.readFileSync(path.join(mspDir, "signcerts", certFile)) };
  const signer = signers.newPrivateKeySigner(crypto.createPrivateKey(fs.readFileSync(path.join(mspDir, "keystore", keyFile))));
  const gw = connect({ client, identity, signer, evaluateOptions: () => ({ deadline: Date.now() + 30000 }), submitOptions: () => ({ deadline: Date.now() + 60000 }), commitStatusOptions: () => ({ deadline: Date.now() + 120000 }) });
  return { gw, client, contract: gw.getNetwork("mychannel").getContract("bzt") };
}
export const now = () => Number(process.hrtime.bigint()) / 1e6;
export function stat(a) { if (!a || !a.length) return null; const s = [...a].sort((x, y) => x - y); const m = a.reduce((p, c) => p + c, 0) / a.length;
  const q = p => s[Math.min(s.length - 1, Math.floor(s.length * p))]; return { n: a.length, mean_ms: +m.toFixed(2), p50_ms: +q(.5).toFixed(2), p95_ms: +q(.95).toFixed(2), p99_ms: +q(.99).toFixed(2), max_ms: +s[s.length - 1].toFixed(2) }; }
// Run `nWorkers` copies of `script` (child processes), start them together, merge their raw samples.
export async function runWorkers(script, nWorkers, args) {
  const { fork } = await import("node:child_process");
  const kids = Array.from({ length: nWorkers }, (_, k) => fork(script, [...args, String(k)], { stdio: ["inherit", "inherit", "inherit", "ipc"] }));
  await Promise.all(kids.map(c => new Promise((res, rej) => { c.once("message", m => m.ready ? res() : rej(new Error("worker failed: " + JSON.stringify(m)))); c.once("exit", code => rej(new Error("worker exited " + code))); })));
  const t0 = now(); kids.forEach(c => c.send({ go: true }));
  const results = await Promise.all(kids.map(c => new Promise(res => c.once("message", m => res({ ...m, t_end: now() })))));
  const wall = (Math.max(...results.map(r => r.t_end)) - t0) / 1000;
  return { wall, results };
}
export function merge(results) { const T = {}, F = {}, X = {};
  for (const r of results) { for (const [k, v] of Object.entries(r.samples || {})) (T[k] ||= []).push(...v);
    for (const [k, v] of Object.entries(r.failures || {})) F[k] = (F[k] || 0) + v;
    for (const [k, v] of Object.entries(r.counts || {})) X[k] = (X[k] || 0) + v; }
  return { T, F, X }; }
