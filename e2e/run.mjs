// End-to-end BZT-ID flow on a running Fabric test-network (paper, Fig. 2):
//   issuance:     issuer BBS+ signs 10 attributes -> PEP scores context -> IssueCredential (submit + commit)
//   verification: wallet derives BBS+ proof (1 of 10 disclosed) -> PEP re-scores context -> verifier checks proof
//                 -> VerifyCredential (evaluate on a peer) -> RecordVerification (submit + commit, audited path)
// usage: node run.mjs <label> <out.json> [nFlows=200] [concurrency=1]      (DRY=1 skips Fabric)
import * as bbs from "@digitalbazaar/bbs-signatures";
import crypto from "node:crypto"; import fs from "node:fs"; import path from "node:path";
import { score, decide, rng, legitContext } from "./engine.mjs";
const [label = "dry", out = "e2e.json", nArg = "200", cArg = "1"] = process.argv.slice(2);
const N = +nArg, C = +cArg, DRY = process.env.DRY === "1";
const enc = new TextEncoder(); const cs = bbs.CIPHERSUITES.BLS12381_SHA256;
const now = () => Number(process.hrtime.bigint()) / 1e6;
const stat = a => { if (!a.length) return null; const s = [...a].sort((x, y) => x - y); const m = a.reduce((p, c) => p + c, 0) / a.length;
  const q = p => s[Math.min(s.length - 1, Math.floor(s.length * p))]; return { n: a.length, mean_ms: +m.toFixed(2), p50_ms: +q(.5).toFixed(2), p95_ms: +q(.95).toFixed(2), max_ms: +s[s.length - 1].toFixed(2) }; };

let contract, gw, client;
async function connect() {
  if (DRY) return;
  const grpc = await import("@grpc/grpc-js"); const { connect, signers } = await import("@hyperledger/fabric-gateway");
  const TN = process.env.TN; const O1 = path.join(TN, "organizations/peerOrganizations/org1.example.com");
  const tls = fs.readFileSync(path.join(O1, "peers/peer0.org1.example.com/tls/ca.crt"));
  client = new grpc.Client("localhost:7051", grpc.credentials.createSsl(tls), { "grpc.ssl_target_name_override": "peer0.org1.example.com" });
  const mspDir = path.join(O1, "users/User1@org1.example.com/msp");
  const certFile = fs.readdirSync(path.join(mspDir, "signcerts"))[0]; const keyFile = fs.readdirSync(path.join(mspDir, "keystore"))[0];
  const identity = { mspId: "Org1MSP", credentials: fs.readFileSync(path.join(mspDir, "signcerts", certFile)) };
  const signer = signers.newPrivateKeySigner(crypto.createPrivateKey(fs.readFileSync(path.join(mspDir, "keystore", keyFile))));
  gw = connect({ client, identity, signer, evaluateOptions: () => ({ deadline: Date.now() + 30000 }), submitOptions: () => ({ deadline: Date.now() + 60000 }), commitStatusOptions: () => ({ deadline: Date.now() + 120000 }) });
  contract = gw.getNetwork("mychannel").getContract("bzt");
}
const attrs = ["name", "father_name", "cnic_number", "dob", "gender", "address", "province", "issue_date", "expiry_date", "photo_hash"];
const header = enc.encode("bzt-id-cnic-v1");
const T = {}; const add = (k, v) => (T[k] ||= []).push(v);
const fails = {}; const fail = k => { fails[k] = (fails[k] || 0) + 1; };
const issuer = await bbs.generateKeyPair({ ciphersuite: cs });
const r = rng(20261119); const run = `${label}-${Date.now()}`;

async function flow(i) {
  const tAll = now();
  // ---- issuance
  const messages = attrs.map((a, j) => enc.encode(`${a}=v${j}-${run}-${i}`));
  let t = now(); const ctxI = legitContext(r); const dI = decide(score(ctxI)); add("issue_engine", now() - t);
  if (dI === "DENY") { fail("issue_denied"); return; }
  t = now(); const signature = await bbs.sign({ ...issuer, header, messages, ciphersuite: cs }); add("issue_bbs_sign", now() - t);
  const credId = `c-${run}-${i}`; const commitment = crypto.createHash("sha256").update(signature).digest("hex");
  if (!DRY) { t = now(); try { await contract.submitTransaction("IssueCredential", credId, `did:bzt:${i}`, commitment, "nadra"); add("issue_ledger_commit", now() - t); } catch (e) { fail("issue_ledger"); return; } }
  add("issue_total", now() - tAll);
  // ---- verification (presentation of 1 of 10 attributes, e.g. citizenship/age predicate)
  const tV = now(); const ph = enc.encode(`nonce-${run}-${i}`); const idx = [3];
  t = now(); const proof = await bbs.deriveProof({ publicKey: issuer.publicKey, signature, header, messages, presentationHeader: ph, disclosedMessageIndexes: idx, ciphersuite: cs }); add("verify_wallet_derive_proof", now() - t);
  t = now(); const ctxV = legitContext(r); const dV = decide(score(ctxV)); add("verify_engine", now() - t);
  if (dV === "DENY") { fail("verify_denied"); return; }
  t = now(); const ok = await bbs.verifyProof({ publicKey: issuer.publicKey, proof, header, presentationHeader: ph, disclosedMessageIndexes: idx, disclosedMessages: idx.map(k => messages[k]), ciphersuite: cs }); add("verify_bbs_verify_proof", now() - t);
  if (!ok) { fail("proof_invalid"); return; }
  if (!DRY) {
    t = now(); let st; try { st = JSON.parse(Buffer.from(await contract.evaluateTransaction("VerifyCredential", credId, commitment)).toString()); } catch (e) { fail("status_query"); return; }
    add("verify_ledger_status_query", now() - t); if (!st.valid) { fail("status_invalid"); return; }
  }
  add("verify_total_readonly", now() - tV);
  if (!DRY) { t = now(); try { await contract.submitTransaction("RecordVerification", credId, "bank-01", "VALID"); add("verify_audit_commit", now() - t); } catch (e) { fail("audit_commit"); return; } }
  add("verify_total_audited", now() - tV);
}
await connect();
// functional check of revocation before the timed runs
const check = {};
if (!DRY) {
  const id = `rev-${run}`; await contract.submitTransaction("IssueCredential", id, "did:bzt:r", "h", "nadra");
  check.before = JSON.parse(Buffer.from(await contract.evaluateTransaction("VerifyCredential", id, "h")).toString());
  await contract.submitTransaction("RevokeCredential", id);
  check.after_revoke = JSON.parse(Buffer.from(await contract.evaluateTransaction("VerifyCredential", id, "h")).toString());
}
for (let i = 0; i < 5; i++) await flow(-1 - i);           // warm-up, discarded
for (const k of Object.keys(T)) delete T[k]; for (const k of Object.keys(fails)) delete fails[k];
const t0 = now(); let next = 0;
await Promise.all(Array.from({ length: C }, async () => { while (next < N) { const i = next++; await flow(i); } }));
const wall = (now() - t0) / 1000;
const res = { label, flows: N, concurrency: C, wall_s: +wall.toFixed(2), completed_flows_per_s: +((T.verify_total_audited || T.verify_total_readonly || []).length / wall).toFixed(2), revocation_check: check, failures: fails, steps: Object.fromEntries(Object.entries(T).map(([k, v]) => [k, stat(v)])) };
fs.writeFileSync(out, JSON.stringify(res, null, 1)); console.log(JSON.stringify(res, null, 1));
if (gw) gw.close(); if (client) client.close();
