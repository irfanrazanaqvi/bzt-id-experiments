# Real Hyperledger Fabric benchmark (Caliper)

Benchmarks the BZT-ID on-chain logic on a **real** Hyperledger Fabric network (fabric-samples
`test-network`) instead of the discrete-event simulator.

- `chaincode/` Node.js chaincode: `IssueCredential`, `VerifyCredential` (read-only),
  `RecordVerification` (audit event write), `RevokeCredential`. Only hash commitments and
  lifecycle metadata are stored. Unit test: `npm test` (in-memory stub, no network needed).
- `caliper/` Hyperledger Caliper 0.7.1 workload and benchmark config (issue / verify / audit
  at fixed send rates).
- `scripts/` network-config generator and Caliper-log parser.
- `../.github/workflows/fabric-benchmark.yml` runs everything on a free GitHub Actions runner.
  Results are committed to the `fabric-results` branch.

## Caveats (state these in the paper)
- The network is the standard 2-organisation `test-network` with a single Raft orderer, all
  containers on one 2-vCPU GitHub runner. Absolute numbers are not representative of a
  geographically distributed national deployment, and Raft is crash-fault tolerant, not Byzantine.
- Caliper load generator and Fabric share the same machine, which lowers peak throughput.
