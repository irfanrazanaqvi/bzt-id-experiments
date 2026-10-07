'use strict';
/**
 * BZT-ID chaincode.
 * Only credential-hash commitments and lifecycle-event metadata are written
 * on-chain (paper, Section 4.5). Raw biometrics / PII never reach the ledger.
 */
const { Contract } = require('fabric-contract-api');

const CRED = 'cred:';
const AUDIT = 'audit:';

class BztContract extends Contract {
  constructor() { super('BztContract'); }

  _ts(ctx) {
    const t = ctx.stub.getTxTimestamp();
    return new Date(t.seconds.low * 1000 + Math.floor(t.nanos / 1e6)).toISOString();
  }

  /** Issue a credential commitment (write). */
  async IssueCredential(ctx, credId, subjectDid, commitmentHash, issuerId) {
    const key = CRED + credId;
    const existing = await ctx.stub.getState(key);
    if (existing && existing.length > 0) throw new Error(`credential ${credId} already exists`);
    const rec = { credId, subjectDid, commitmentHash, issuerId, status: 'ACTIVE', issuedAt: this._ts(ctx) };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(rec)));
    return JSON.stringify({ credId, status: 'ACTIVE' });
  }

  /** Read-only verification of a presented commitment (query / evaluate). */
  async VerifyCredential(ctx, credId, commitmentHash) {
    const data = await ctx.stub.getState(CRED + credId);
    if (!data || data.length === 0) return JSON.stringify({ valid: false, reason: 'NOT_FOUND' });
    const rec = JSON.parse(data.toString());
    if (rec.status !== 'ACTIVE') return JSON.stringify({ valid: false, reason: rec.status });
    if (rec.commitmentHash !== commitmentHash) return JSON.stringify({ valid: false, reason: 'HASH_MISMATCH' });
    return JSON.stringify({ valid: true });
  }

  /** Verification with an on-chain audit event (write): verifier, credential, outcome. */
  async RecordVerification(ctx, credId, verifierId, outcome) {
    const data = await ctx.stub.getState(CRED + credId);
    if (!data || data.length === 0) throw new Error(`credential ${credId} not found`);
    const key = AUDIT + ctx.stub.getTxID();
    const ev = { credId, verifierId, outcome, at: this._ts(ctx) };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(ev)));
    return key;
  }

  /** Revoke a credential (write). */
  async RevokeCredential(ctx, credId) {
    const key = CRED + credId;
    const data = await ctx.stub.getState(key);
    if (!data || data.length === 0) throw new Error(`credential ${credId} not found`);
    const rec = JSON.parse(data.toString());
    rec.status = 'REVOKED';
    rec.revokedAt = this._ts(ctx);
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(rec)));
    return JSON.stringify({ credId, status: 'REVOKED' });
  }
}

module.exports = BztContract;
