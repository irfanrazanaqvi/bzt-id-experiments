'use strict';
// Local unit test with an in-memory stub (no Fabric network required).
const assert = require('assert');
const BztContract = require('../lib/bzt-contract');

function makeCtx() {
  const state = new Map();
  let n = 0;
  return {
    state,
    stub: {
      getState: async k => state.has(k) ? state.get(k) : Buffer.alloc(0),
      putState: async (k, v) => { state.set(k, v); },
      getTxTimestamp: () => ({ seconds: { low: 1700000000 }, nanos: 5e6 }),
      getTxID: () => 'tx' + (++n),
    },
  };
}

(async () => {
  const c = new BztContract();
  const ctx = makeCtx();
  await c.IssueCredential(ctx, 'c1', 'did:bzt:alice', 'abc123', 'NADRA');
  await assert.rejects(() => c.IssueCredential(ctx, 'c1', 'x', 'y', 'z'), /already exists/);
  assert.deepStrictEqual(JSON.parse(await c.VerifyCredential(ctx, 'c1', 'abc123')), { valid: true });
  assert.strictEqual(JSON.parse(await c.VerifyCredential(ctx, 'c1', 'bad')).reason, 'HASH_MISMATCH');
  assert.strictEqual(JSON.parse(await c.VerifyCredential(ctx, 'nope', 'abc123')).reason, 'NOT_FOUND');
  const k = await c.RecordVerification(ctx, 'c1', 'BANK-1', 'ALLOW');
  assert.ok(k.startsWith('audit:'));
  await assert.rejects(() => c.RecordVerification(ctx, 'nope', 'BANK-1', 'DENY'), /not found/);
  await c.RevokeCredential(ctx, 'c1');
  assert.strictEqual(JSON.parse(await c.VerifyCredential(ctx, 'c1', 'abc123')).reason, 'REVOKED');
  // v2: status list + pairwise pseudonyms
  const d1 = 'a'.repeat(64), d2 = 'b'.repeat(64), ps = 'c'.repeat(64);
  assert.deepStrictEqual(JSON.parse(await c.GetStatusList(ctx, 'L1')), { found: false });
  await c.IssueCredentialS(ctx, 'c2', 'did:bzt:bob', 'h2', 'NADRA', 'L1', '42');
  await assert.rejects(() => c.IssueCredentialS(ctx, 'c3', 'd', 'h', 'NADRA', 'L1', '-1'), /bad statusIndex/);
  await c.UpdateStatusList(ctx, 'L1', '1', d1, 'NADRA');
  await assert.rejects(() => c.UpdateStatusList(ctx, 'L1', '1', d2, 'NADRA'), /stale version/);
  await assert.rejects(() => c.UpdateStatusList(ctx, 'L1', '2', d2, 'OTHER'), /issuer mismatch/);
  await assert.rejects(() => c.UpdateStatusList(ctx, 'L1', '2', 'xyz', 'NADRA'), /64 hex/);
  await c.UpdateStatusList(ctx, 'L1', '2', d2, 'NADRA');
  const g = JSON.parse(await c.GetStatusList(ctx, 'L1'));
  assert.strictEqual(g.version, 2); assert.strictEqual(g.digest, d2);
  const k2 = await c.RecordVerificationP(ctx, 'BANK-1', ps, 'L1', '2', 'STEP_UP', 'OTP_OK');
  assert.ok(k2.startsWith('audit:'));
  assert.ok(!ctx.state.get(k2).toString().includes('c2'));
  await assert.rejects(() => c.RecordVerificationP(ctx, 'BANK-1', ps, 'L1', '2', 'MAYBE', 'x'), /bad decision/);
  console.log('chaincode unit tests passed');
})().catch(e => { console.error(e); process.exit(1); });

// v3: H1 commitment-only issuance and H4 batched audit anchoring
(async () => {
  const crypto = require('crypto');
  const M = require('../lib/merkle');
  const c = new BztContract();
  const ctx = makeCtx();
  const salt = crypto.randomBytes(32).toString('hex');
  const com = crypto.createHash('sha256').update(['c9', 'did:bzt:carol', 'L1', '77', salt].join('|')).digest('hex');
  await c.IssueCredentialH(ctx, com, 'NADRA');
  await assert.rejects(() => c.IssueCredentialH(ctx, com, 'NADRA'), /already exists/);
  await assert.rejects(() => c.IssueCredentialH(ctx, 'xyz', 'NADRA'), /64 hex/);
  const stored = ctx.state.get('cred:' + com).toString();
  for (const leak of ['did:bzt:carol', 'L1', '77', 'c9']) assert.ok(!stored.includes('"' + leak), 'H1 leaks ' + leak);
  assert.strictEqual(JSON.parse(await c.GetCommitment(ctx, com)).found, true);
  // gateway batch of 1000 decisions
  const recs = Array.from({ length: 1000 }, (_, i) => JSON.stringify({ nym: crypto.randomBytes(32).toString('hex'), d: i % 3 ? 'ALLOW' : 'STEP_UP', t: i }));
  const leaves = recs.map(M.leafHash), lv = M.build(leaves), root = M.root(lv);
  await c.AnchorAuditRoot(ctx, 'GW-BANK-1', '2026-11-28T10', root, '1000');
  await assert.rejects(() => c.AnchorAuditRoot(ctx, 'GW-BANK-1', '2026-11-28T10', root, '1000'), /already anchored/);
  for (const i of [0, 1, 499, 998, 999]) {
    const r = JSON.parse(await c.VerifyAuditInclusion(ctx, 'GW-BANK-1', '2026-11-28T10', leaves[i], JSON.stringify(M.proof(lv, i))));
    assert.strictEqual(r.included, true, 'proof ' + i);
  }
  const bad = JSON.parse(await c.VerifyAuditInclusion(ctx, 'GW-BANK-1', '2026-11-28T10', M.leafHash('forged'), JSON.stringify(M.proof(lv, 3))));
  assert.strictEqual(bad.included, false);
  const anchored = [...ctx.state.values()].map(String).join('');
  assert.ok(!recs.some(r => anchored.includes(JSON.parse(r).nym)), 'H4 leaks a pseudonym');
  console.log('H1/H4 unit tests passed');
})().catch(e => { console.error(e); process.exit(1); });
