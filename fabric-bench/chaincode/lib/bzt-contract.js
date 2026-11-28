'use strict';
/**
 * BZT-ID chaincode.
 * Only credential-hash commitments and lifecycle-event metadata are written
 * on-chain (paper, Section 4.5). Raw biometrics / PII never reach the ledger.
 */
const crypto = require('crypto');
const { Contract } = require('fabric-contract-api');

const CRED = 'cred:';
const AUDIT = 'audit:';
const SLIST = 'slist:';

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

  // ---------------- v2: status-list revocation and pairwise-pseudonym audit ----------------
  // The issuer keeps a W3C-style bitstring status list off-chain (one bit per credential).
  // Only the list digest and a monotonically increasing version are written on-chain, so a
  // revocation is one small write regardless of how many credentials the list covers.

  /** Issue a credential commitment bound to a slot (listId, statusIndex) of a status list (write). */
  async IssueCredentialS(ctx, credId, subjectDid, commitmentHash, issuerId, listId, statusIndex) {
    const key = CRED + credId;
    const existing = await ctx.stub.getState(key);
    if (existing && existing.length > 0) throw new Error(`credential ${credId} already exists`);
    const idx = parseInt(statusIndex, 10);
    if (!Number.isInteger(idx) || idx < 0) throw new Error('bad statusIndex');
    const rec = { credId, subjectDid, commitmentHash, issuerId, listId, statusIndex: idx, status: 'ACTIVE', issuedAt: this._ts(ctx) };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(rec)));
    return JSON.stringify({ credId, listId, statusIndex: idx });
  }

  /** Publish a new version of a status list: digest = SHA-256 of the (compressed) bitstring (write). */
  async UpdateStatusList(ctx, listId, version, digest, issuerId) {
    const key = SLIST + listId;
    const v = parseInt(version, 10);
    if (!Number.isInteger(v) || v < 1) throw new Error('bad version');
    if (!/^[0-9a-f]{64}$/.test(digest)) throw new Error('digest must be 64 hex chars');
    const cur = await ctx.stub.getState(key);
    if (cur && cur.length > 0) {
      const c = JSON.parse(cur.toString());
      if (c.issuerId !== issuerId) throw new Error('issuer mismatch');
      if (v <= c.version) throw new Error(`stale version ${v} <= ${c.version}`);
    }
    const rec = { listId, version: v, digest, issuerId, updatedAt: this._ts(ctx) };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(rec)));
    return JSON.stringify(rec);
  }

  /** Read the current digest and version of a status list (query / evaluate). */
  async GetStatusList(ctx, listId) {
    const data = await ctx.stub.getState(SLIST + listId);
    if (!data || data.length === 0) return JSON.stringify({ found: false });
    return JSON.stringify({ found: true, ...JSON.parse(data.toString()) });
  }

  /**
   * Audit a verification decision under a pairwise pseudonym (write). The pseudonym is
   * HMAC(holderSecret, rpId), computed by the wallet, so records written by different relying
   * parties for the same holder cannot be linked on-chain. No credential identifier is stored.
   */
  async RecordVerificationP(ctx, rpId, pseudonym, listId, listVersion, decision, outcome) {
    if (!/^[0-9a-f]{64}$/.test(pseudonym)) throw new Error('pseudonym must be 64 hex chars');
    if (!['ALLOW', 'STEP_UP', 'DENY'].includes(decision)) throw new Error('bad decision');
    const key = AUDIT + ctx.stub.getTxID();
    const ev = { rpId, pseudonym, listId, listVersion: parseInt(listVersion, 10), decision, outcome, at: this._ts(ctx) };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(ev)));
    return key;
  }
  // ---------------- v3: hardening H1 (commitment-only issuance) and H4 (batched audit) ----------------
  // H1. The ledger stores only a hiding commitment c = SHA-256(credId || subjectDid || listId ||
  // statusIndex || salt), computed by the issuer; the subject DID and the status-list slot stay
  // off-chain. A reader of world state learns that the issuer issued something at time t, nothing more.

  /** Issue a credential as a hiding commitment only (write). */
  async IssueCredentialH(ctx, commitment, issuerId) {
    if (!/^[0-9a-f]{64}$/.test(commitment)) throw new Error('commitment must be 64 hex chars');
    const key = CRED + commitment;
    const existing = await ctx.stub.getState(key);
    if (existing && existing.length > 0) throw new Error('commitment already exists');
    const rec = { commitment, issuerId, issuedAt: this._ts(ctx) };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(rec)));
    return JSON.stringify({ commitment });
  }

  /** Check that a commitment was issued (query / evaluate). The verifier opens it off-chain. */
  async GetCommitment(ctx, commitment) {
    const data = await ctx.stub.getState(CRED + commitment);
    if (!data || data.length === 0) return JSON.stringify({ found: false });
    return JSON.stringify({ found: true, ...JSON.parse(data.toString()) });
  }

  // H4. A relying-party gateway keeps its per-decision audit records off-chain and anchors one
  // Merkle root per period. One write covers a whole batch, and the ledger holds no per-holder
  // record, so neither the pseudonym nor the decision time of any single presentation is on-chain.

  /** Anchor the Merkle root of a gateway's audit batch for one period (write). */
  async AnchorAuditRoot(ctx, gatewayId, period, root, count) {
    if (!/^[0-9a-f]{64}$/.test(root)) throw new Error('root must be 64 hex chars');
    const n = parseInt(count, 10);
    if (!Number.isInteger(n) || n < 1) throw new Error('bad count');
    const key = ctx.stub.createCompositeKey ? ctx.stub.createCompositeKey('aroot', [gatewayId, period]) : `aroot:${gatewayId}:${period}`;
    const existing = await ctx.stub.getState(key);
    if (existing && existing.length > 0) throw new Error('period already anchored');
    const rec = { gatewayId, period, root, count: n, at: this._ts(ctx) };
    await ctx.stub.putState(key, Buffer.from(JSON.stringify(rec)));
    return JSON.stringify(rec);
  }

  /**
   * Check that an audit record (leaf hash) is in an anchored batch (query / evaluate).
   * proof is a JSON array of {h: hex, left: bool} siblings from leaf to root.
   */
  async VerifyAuditInclusion(ctx, gatewayId, period, leaf, proof) {
    const key = ctx.stub.createCompositeKey ? ctx.stub.createCompositeKey('aroot', [gatewayId, period]) : `aroot:${gatewayId}:${period}`;
    const data = await ctx.stub.getState(key);
    if (!data || data.length === 0) return JSON.stringify({ included: false, reason: 'NO_ROOT' });
    const rec = JSON.parse(data.toString());
    let h = leaf;
    for (const s of JSON.parse(proof)) h = merkleNode(s.left ? s.h : h, s.left ? h : s.h);
    return JSON.stringify({ included: h === rec.root });
  }
}

function merkleNode(a, b) {
  return crypto.createHash('sha256').update(Buffer.from('01' + a + b, 'hex')).digest('hex');
}

module.exports = BztContract;
