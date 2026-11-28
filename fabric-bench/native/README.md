# Native (no-Docker) Fabric network used for the hardened-chaincode benchmark

Hyperledger Fabric 2.5.9 release binaries and fabric-samples test-network crypto/configtx; one Raft orderer, peer0.org1, peer0.org2, channel `mychannel`, LevelDB, default batching. The chaincode runs as an external service (`npx fabric-chaincode-node server --chaincode-address=0.0.0.0:9999 --chaincode-id=<package id>`).

1. Extract `hyperledger-fabric-linux-amd64-2.5.9.tar.gz` and clone fabric-samples next to these scripts (paths in the scripts assume `/home/claude/fabnative`; edit `B=`).
2. Map `orderer.example.com peer0.org1.example.com peer0.org2.example.com` to 127.0.0.1 in /etc/hosts and exclude them from any HTTP proxy.
3. `./net.sh` (network and channel), `bash anchors.sh` (anchor peers, needed for gateway discovery).
4. Package a `ccaas` chaincode pointing at 127.0.0.1:9999, install, approve and commit it as `bzt`, then start the chaincode server.
5. Caliper: `benchmarks/hardening.yaml` (v2 vs H1 issuance, per-decision audit, H4 anchors; run 3 times by `run_hardening.sh`) and `benchmarks/inclusion.yaml` (`run_inclusion.sh`).

Results: `data/hardening/` (`hardening_summary.csv` from `scripts/parse_hardening.py`; per-repetition Caliper logs and reports in `runs/`). Paper Section 8.8, Table 15.
