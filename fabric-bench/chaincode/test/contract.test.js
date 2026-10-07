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
  console.log('chaincode unit tests passed');
})().catch(e => { console.error(e); process.exit(1); });
