// BBS+ selective disclosure (IETF BBS draft, via @digitalbazaar/bbs-signatures). usage: node bench_bbs.mjs <out.json>
import * as bbs from "@digitalbazaar/bbs-signatures"; import fs from "fs";
console.log("exports:", Object.keys(bbs).join(","));
const enc = new TextEncoder(); const out = process.argv[2];
const stat = a => { const s = [...a].sort((x, y) => x - y); const m = a.reduce((p, c) => p + c, 0) / a.length; return { n: a.length, mean_ms: +m.toFixed(1), p50_ms: +s[Math.floor(s.length * .5)].toFixed(1), p95_ms: +s[Math.floor(s.length * .95)].toFixed(1) }; };
const ciphersuite = bbs.CIPHERSUITES.BLS12381_SHA256;
const keyPair = await bbs.generateKeyPair({ ciphersuite });
const attrs = ["name", "father_name", "cnic_number", "dob", "gender", "address", "province", "issue_date", "expiry_date", "photo_hash"];
const messages = attrs.map((a, i) => enc.encode(`${a}=value-${i}`));
const header = enc.encode("bzt-id-cnic-v1"), presentationHeader = enc.encode("verifier-nonce");
const T = async (f, n = 20) => { const a = []; for (let i = 0; i < n + 1; i++) { const t = process.hrtime.bigint(); await f(); a.push(Number(process.hrtime.bigint() - t) / 1e6); } return a.slice(1); };
const res = { library: "@digitalbazaar/bbs-signatures", ciphersuite: "BLS12-381-SHA-256", total_messages: messages.length };
let signature; res.sign = stat(await T(async () => { signature = await bbs.sign({ ...keyPair, header, messages, ciphersuite }); }));
res.signature_bytes = signature.length;
res.verify_signature = stat(await T(async () => { const ok = await bbs.verifySignature({ publicKey: keyPair.publicKey, signature, header, messages, ciphersuite }); if (!ok) throw new Error("sig"); }));
res.disclosure = [];
for (const k of [1, 2, 5, 10]) {
  const idx = Array.from({ length: k }, (_, i) => i); let proof;
  const d = stat(await T(async () => { proof = await bbs.deriveProof({ publicKey: keyPair.publicKey, signature, header, messages, presentationHeader, disclosedMessageIndexes: idx, ciphersuite }); }));
  const disclosedMessages = idx.map(i => messages[i]);
  const v = stat(await T(async () => { const ok = await bbs.verifyProof({ publicKey: keyPair.publicKey, proof, header, presentationHeader, disclosedMessageIndexes: idx, disclosedMessages, ciphersuite }); if (!ok) throw new Error("proof"); }));
  res.disclosure.push({ disclosed: k, of: messages.length, derive_proof: d, verify_proof: v, proof_bytes: proof.length });
}
fs.writeFileSync(out, JSON.stringify(res, null, 1)); console.log(JSON.stringify(res, null, 1));
