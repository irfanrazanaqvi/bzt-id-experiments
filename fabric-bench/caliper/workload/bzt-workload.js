'use strict';
const { WorkloadModuleBase } = require('@hyperledger/caliper-core');

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
    this.op = roundArguments.op;
    this.seedCount = roundArguments.seedCount || 500;
    this.contractId = roundArguments.contractId || 'bzt';
    this.uid = `${Date.now().toString(36)}-r${roundIndex}-w${workerIndex}`;
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
      default:
        throw new Error(`unknown op ${this.op}`);
    }
    await this.sutAdapter.sendRequests({ contractId: this.contractId, ...req });
  }
}

module.exports.createWorkloadModule = () => new BztWorkload();
