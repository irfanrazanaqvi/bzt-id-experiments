// End-to-end BZT-ID flow v2 (paper, Section 8.11):
//  - W client processes (child processes) x C concurrent flows each, started together;
//  - request contexts mixed 80/10/10: legitimate (ALLOW), new device + unusual network (STEP_UP with a
//    simulated TOTP second factor; user typing time excluded), replay from a remote location (DENY);
//  - revocation through a W3C-style bitstring status list (131,072 entries) held off-chain by the issuer,
//    with only its SHA-256 digest + version on the ledger (UpdateStatusList / GetStatusList);
//  - verification audit written under a pairwise pseudonym HMAC(holderSecret, rpId) (RecordVerificationP).
// usage: node run2.mjs <label> <out.json> <flowsPerWorker> <concPerWorker> <workers>     (DRY=1: no Fabric)
import * as bbs from "@digitalbazaar/bbs-signatures";
import crypto from "node:crypto"; import fs from "node:fs"; import zlib from "node:zlib"; import os from "node:os";
import { fileURLToPath } from "node:url";
import { score, decide, rng, legitContext, stepUpContext, attackContext } from "./engine.mjs";
import { connectGateway, now, stat, runWorkers, merge } from "./fabric.mjs";
const DRY = process.env.DRY === "1"; const LIST_BITS = 131072; const RPS = ["bank-01", "telco-02", "passport-office"];
const enc = new TextEncoder(); const cs = bbs.CIPHERSUITES.BLS12381_SHA256;
const attrs = ["name", "father_name", "cnic_number", "dob", "gender", "address", "province", "issue_date", "expiry_date", "photo_hash"];
const header = enc.encode("bzt-id-cnic-v1");
const sha = b => crypto.createHash("sha256").update(b).digest("hex");
const hmac = (k, m) => crypto.createHmac("sha256", k).update(m).digest("hex");
function totp(secret, t) { const c = Buffer.alloc(8); c.writeBigUInt64BE(BigInt(Math.floor(t / 30000))); const h = crypto.createHmac("sha1", secret).update(c).digest();
  const o = h[19] & 15; return ((h.readUInt32BE(o) & 0x7fffffff) % 1e6).toString().padStart(6, "0"); }
// issuer-side status list
class StatusList { constructor(id) { this.id = id; this.bits = Buffer.alloc(LIST_BITS / 8); this.version = 0; }
  set(i) { this.bits[i >> 3] |= 1 << (i & 7); }
  publish() { this.version++; this.blob = zlib.gzipSync(this.bits); this.digest = sha(this.blob); return this; } }
const bitSet = (bits, i) => (bits[i >> 3] >> (i & 7)) & 1;

async function worker(label, perWorker, C, k) {
  const T = {}; const add = (n, v) => (T[n] ||= []).push(v); const F = {}; const fail = n => { F[n] = (F[n] || 0) + 1; }; const X = {}; const cnt = n => { X[n] = (X[n] || 0) + 1; };
  const run = `${label}-${process.pid}-${Date.now()}`; const r = rng(20261119 + 7919 * k);
  const g = DRY ? null : await connectGateway(); const contract = g?.contract;
  const issuer = await bbs.generateKeyPair({ ciphersuite: cs }); const list = new StatusList(`L-${run}`);
  const cache = new Map(); // verifier cache: listId -> {version, bits}
  const fetchList = () => ({ blob: Buffer.from(list.blob), version: list.version }); // stands in for an HTTPS GET to the issuer
  const pub = async () => { list.publish(); if (!DRY) await contract.submitTransaction("UpdateStatusList", list.id, String(list.version), list.digest, "nadra"); };
  await pub();
  const extra = {};
  async function issue(i) {
    const messages = attrs.map((a, j) => enc.encode(`${a}=v${j}-${run}-${i}`));
    let t = now(); const signature = await bbs.sign({ ...issuer, header, messages, ciphersuite: cs }); add("issue_bbs_sign", now() - t);
    const credId = `c-${run}-${i}`; const commitment = sha(signature);
    if (!DRY) { t = now(); await contract.submitTransaction("IssueCredentialS", credId, `did:bzt:${k}-${i}`, commitment, "nadra", list.id, String(i)); add("issue_ledger_commit", now() - t); }
    return { messages, signature, idx: i, holderSecret: crypto.randomBytes(32), otpSecret: crypto.randomBytes(20) };
  }
  async function statusCheck(idx) { // verifier: ledger digest -> cached or refreshed list -> bit
    let t = now(); const st = DRY ? { version: list.version, digest: list.digest } : JSON.parse(Buffer.from(await contract.evaluateTransaction("GetStatusList", list.id)).toString()); add("verify_status_list_query", now() - t);
    let c = cache.get(list.id);
    if (!c || c.version !== st.version) { t = now(); const f = fetchList(); if (sha(f.blob) !== st.digest) throw new Error("STATUS_DIGEST_MISMATCH");
      c = { version: f.version, bits: zlib.gunzipSync(f.blob) }; cache.set(list.id, c); add("verify_status_list_refresh", now() - t); cnt("list_refresh"); }
    return { revoked: bitSet(c.bits, idx) === 1, version: st.version };
  }
  async function verify(cred, i) {
    const tV = now(); const rp = RPS[i % RPS.length]; const u = r();
    const ctx = u < 0.8 ? legitContext(r) : u < 0.9 ? stepUpContext(r) : attackContext(r);
    const kind = u < 0.8 ? "legit" : u < 0.9 ? "stepup" : "attack";
    const ph = enc.encode(`nonce-${run}-${i}-${rp}`); const idx = [3];
    let t = now(); const proof = await bbs.deriveProof({ publicKey: issuer.publicKey, signature: cred.signature, header, messages: cred.messages, presentationHeader: ph, disclosedMessageIndexes: idx, ciphersuite: cs });
    const pseudonym = hmac(cred.holderSecret, rp); add("verify_wallet_derive_proof", now() - t);
    t = now(); const d = decide(score(ctx)); add("verify_engine", now() - t); cnt(`ctx_${kind}_${d}`);
    const audit = async (dec, outcome) => { if (DRY) return; const t1 = now(); await contract.submitTransaction("RecordVerificationP", rp, pseudonym, list.id, String(list.version), dec, outcome); add(`audit_commit_${dec}`, now() - t1); };
    if (d === "DENY") { await audit("DENY", "REJECTED_CONTEXT"); add("total_DENY", now() - tV); return; }
    if (d === "STEP_UP") { t = now(); const code = totp(cred.otpSecret, Date.now()); const ok = code === totp(cred.otpSecret, Date.now()); add("stepup_totp_check", now() - t); if (!ok) { fail("otp"); return; } }
    t = now(); const ok = await bbs.verifyProof({ publicKey: issuer.publicKey, proof, header, presentationHeader: ph, disclosedMessageIndexes: idx, disclosedMessages: idx.map(j => cred.messages[j]), ciphersuite: cs }); add("verify_bbs_verify_proof", now() - t);
    if (!ok) { fail("proof_invalid"); return; }
    const s = await statusCheck(cred.idx); if (s.revoked) { fail("unexpected_revoked"); return; }
    await audit(d, d === "STEP_UP" ? "VALID_AFTER_OTP" : "VALID"); add(`total_${d}`, now() - tV);
  }
  // functional + cost check of revocation (sequential, before the timed run)
  { const creds = []; for (let i = 0; i < 20; i++) creds.push(await issue(LIST_BITS - 1 - i));
    const before = await statusCheck(creds[0].idx);
    for (let i = 0; i < 10; i++) { list.set(creds[i].idx); const t = now(); await pub(); add("revoke_status_list_update_commit", now() - t); }
    const after = await statusCheck(creds[0].idx); const other = await statusCheck(creds[15].idx);
    extra.revocation_check = { before_revoked: before.revoked, after_revoked: after.revoked, unrevoked_other: other.revoked, list_version: list.version,
      list_bits: LIST_BITS, list_raw_bytes: list.bits.length, list_gzip_bytes: list.blob.length };
    // cost of a realistically filled list: 1% of entries revoked at random positions
    const big = new StatusList("density"); for (let i = 0; i < LIST_BITS / 100; i++) big.set(Math.floor(r() * LIST_BITS)); big.publish();
    const tt = []; for (let i = 0; i < 50; i++) { const t = now(); if (sha(big.blob) !== big.digest) throw new Error("x"); zlib.gunzipSync(big.blob); tt.push(now() - t); }
    extra.revocation_check.list_1pct_gzip_bytes = big.blob.length; extra.revocation_check.list_1pct_hash_gunzip = stat(tt);
    for (let i = 0; i < 3; i++) { const c = await issue(LIST_BITS - 100 - i); await verify(c, i); } }    // warm-up
  for (const n of Object.keys(T)) if (!n.startsWith("revoke")) delete T[n]; for (const n of Object.keys(X)) delete X[n];
  process.send({ ready: true });
  await new Promise(res => process.once("message", res));
  let next = 0; const t0 = now();
  await Promise.all(Array.from({ length: C }, async () => { while (next < perWorker) { const i = next++;
    let cred; try { cred = await issue(i); } catch (e) { fail("issue"); continue; }
    try { await verify(cred, i); cnt("flows_done"); } catch (e) { fail("verify:" + String(e.message).slice(0, 40)); } } }));
  process.send({ samples: T, failures: F, counts: X, extra, worker_wall_s: (now() - t0) / 1000 });
  if (g) { g.gw.close(); g.client.close(); } process.exit(0);
}

const a = process.argv.slice(2);
if (process.send) await worker(a[0], +a[2], +a[3], +a[5]);
else {
  const [label = "dry", out = "e2e2.json", per = "50", C = "4", W = "1"] = a;
  const { wall, results } = await runWorkers(fileURLToPath(import.meta.url), +W, [label, out, per, C, W]);
  const { T, F, X } = merge(results); const done = X.flows_done || 0;
  const res = { label, workers: +W, concurrency_per_worker: +C, flows: +per * +W, wall_s: +wall.toFixed(2), completed_flows_per_s: +(done / wall).toFixed(2),
    host: { cpu_model: os.cpus()[0]?.model, cpus: os.cpus().length, node: process.version },
    decisions: Object.fromEntries(Object.entries(X).filter(([n]) => n.startsWith("ctx_"))), list_refreshes: X.list_refresh || 0,
    revocation_check: results[0].extra.revocation_check, failures: F, steps: Object.fromEntries(Object.entries(T).map(([n, v]) => [n, stat(v)])) };
  fs.writeFileSync(out, JSON.stringify(res, null, 1)); console.log(JSON.stringify(res, null, 1));
}
