'use strict';
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');
const crypto = require('crypto');
const sha = x => crypto.createHash('sha256').update(x).digest('hex');

/**
 * One workload module for all BZT-ID operations.
 * roundArguments.op: seed | issue | verify | audit
 * Credential ids are deterministic so that 'verify' and 'audit' rounds can
 * reference credentials created by the earlier 'seed' round.
 */
class BztWorkload extends WorkloadModuleBase {
  constructor() { super(); this.n = 0; }

  async initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext) {
    await super.initializeWorkloadModule(workerIndex, totalWorkers, roundIndex, roundArguments, sutAdapter, sutContext);
    this.op = roundArguments.op; this.roundArguments = roundArguments;
    this.seedCount = roundArguments.seedCount || 500;
    this.contractId = roundArguments.contractId || 'bzt';
    this.uid = `${Date.now().toString(36)}-r${roundIndex}-w${workerIndex}`;
    if (this.op === 'anchorFixed' || this.op === 'inclusion') {
      const M = require('../../chaincode/lib/merkle');
      this.leaves = Array.from({ length: 1000 }, (_, i) => M.leafHash(`audit-record-${i}`));
      this.lv = M.build(this.leaves); this.root = M.root(this.lv); this.M = M;
    }
  }

  static hash(id) { return `h-${id}`; }

  async submitTransaction() {
    const i = this.n++;
    let req;
    switch (this.op) {
      case 'seed': {
        const id = `seed-w${this.workerIndex}-${i}`;
        req = { contractFunction: 'IssueCredential', contractArguments: [id, `did:bzt:${id}`, BztWorkload.hash(id), 'NADRA'], readOnly: false };
        break;
      }
      case 'issue': {
        const id = `iss-${this.uid}-${i}`;
        req = { contractFunction: 'IssueCredential', contractArguments: [id, `did:bzt:${id}`, BztWorkload.hash(id), 'NADRA'], readOnly: false };
        break;
      }
      case 'verify': {
        const id = `seed-w${this.workerIndex}-${i % this.seedCount}`;
        req = { contractFunction: 'VerifyCredential', contractArguments: [id, BztWorkload.hash(id)], readOnly: true };
        break;
      }
      case 'audit': {
        const id = `seed-w${this.workerIndex}-${i % this.seedCount}`;
        req = { contractFunction: 'RecordVerification', contractArguments: [id, 'BANK-1', 'ALLOW'], readOnly: false };
        break;
      }
      // v2 baseline and v3 hardened operations (H1, H4)
      case 'issueS': {
        const id = `isS-${this.uid}-${i}`;
        req = { contractFunction: 'IssueCredentialS', contractArguments: [id, `did:bzt:${id}`, sha(id), 'NADRA', 'L1', String(i)], readOnly: false };
        break;
      }
      case 'issueH': {
        const id = `isH-${this.uid}-${i}`;
        req = { contractFunction: 'IssueCredentialH', contractArguments: [sha([id, `did:bzt:${id}`, 'L1', i, 'salt'].join('|')), 'NADRA'], readOnly: false };
        break;
      }
      case 'auditP': {
        req = { contractFunction: 'RecordVerificationP', contractArguments: ['BANK-1', sha(`nym-${i % 997}`), 'L1', '1', 'ALLOW', 'OK'], readOnly: false };
        break;
      }
      case 'anchor': {
        // one root per batch of (batchSize) decisions; period id unique per tx
        req = { contractFunction: 'AnchorAuditRoot', contractArguments: [`GW-${this.workerIndex}`, `${this.uid}-${i}`, sha(`root-${this.uid}-${i}`), String(this.roundArguments.batchSize || 1000)], readOnly: false };
        break;
      }
      case 'anchorFixed': {
        req = { contractFunction: 'AnchorAuditRoot', contractArguments: ['GW-FIX', `P-${this.uid}`, this.root, '1000'], readOnly: false };
        this.fixedPeriod = `P-${this.uid}`;
        require('fs').writeFileSync('/tmp/bzt_fixed_period', this.fixedPeriod);
        break;
      }
      case 'inclusion': {
        const j = (i * 7919) % 1000;
        const period = require('fs').readFileSync('/tmp/bzt_fixed_period', 'utf8');
        req = { contractFunction: 'VerifyAuditInclusion', contractArguments: ['GW-FIX', period, this.leaves[j], JSON.stringify(this.M.proof(this.lv, j))], readOnly: true };
        break;
      }
      default:
        throw new Error(`unknown op ${this.op}`);
    }
    await this.sutAdapter.sendRequests({ contractId: this.contractId, ...req });
  }
}

module.exports.createWorkloadModule = () => new BztWorkload();
