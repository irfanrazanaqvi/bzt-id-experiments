# BZT-ID — Experiment Code and Data

Reproducibility package for the paper **"A Blockchain-Enabled Zero-Trust Digital Identity Architecture for Secure CNIC and Passport Services"** (BZT-ID).

It contains the discrete-event simulation testbed (permissioned PBFT-style consortium ledger, DID/VC credential lifecycle, six-factor continuous Zero-Trust scoring engine), the four experiments reported in the paper, the generated datasets, and the figures. Every run uses fixed random seeds, so re-running reproduces the published numbers exactly.

## Repository layout

```
code/
  bzt_id_sim.py                  Core library: ledger, DID/VC, Zero-Trust engine
  exp1_scalability.py            Exp. 1 (latency vs. consortium size) + Exp. 2 (throughput vs. load)
  exp3_zero_trust_detection.py   Exp. 3 (attack detection, ROC/AUC, 20,000 sessions)
  exp4_tamper_evidence.py        Exp. 4 (ledger tamper-evidence)
  fig1_architecture.py           Fig. 1 (architecture diagram)
  fig2_sequence.py               Fig. 2 (protocol sequence diagram)
data/                            CSV outputs of all experiments
figures/                         Figures 1-6 as used in the paper
requirements.txt                 Python dependencies (numpy, pandas, matplotlib)
run_all.sh                       One command to reproduce everything
```

## Quick start

Requires Python 3.9+.

```bash
git clone https://github.com/irfanrazanaqvi/bzt-id-experiments.git
cd bzt-id-experiments
bash run_all.sh
```

This installs the dependencies, runs all experiments (about 12 seconds) and regenerates `data/*.csv` and `figures/*.png`. No external services, accounts, GPUs or paid APIs are needed.

## Headline results

| Experiment | Result |
|---|---|
| Commit latency vs. consortium size (N = 4-25) | 28.0-29.1 ms mean, near-flat scaling |
| Throughput saturation (N = 4 / 10 / 22) | 71 / 174 / 380 committed tx/s |
| Attack detection (20,000 sessions, 4 attack classes) | BZT-ID: 99.8% recall, AUC 0.987; static biometric-only MFA baseline: 89.8% recall, AUC 0.960 |
| Ledger tamper-evidence (5 tamper points) | 100% detection, full downstream block invalidation |

## Real Hyperledger Fabric benchmark (Caliper)

`fabric-bench/` runs the BZT-ID chaincode (issue / verify / audit / revoke commitments) on a **real**
Hyperledger Fabric 2.5.9 network and measures it with Hyperledger Caliper 0.7.1. It executes on a free GitHub
Actions runner (`.github/workflows/fabric-benchmark.yml`, push to the `fabric-bench` branch or run it manually);
raw logs and results are kept on the `fabric-results` branch. Selected results are in `data/fabric/`, plotted
by `code/plot_fabric_results.py` as `figures/fig7_fabric_real_benchmark.png`.

Mean over n = 4 independent runs (min-max in brackets); per-run raw results are in `data/fabric/repeats_run6/` and
`data/fabric/fabric_*_summary_n4.csv`. 0 failed transactions in every round of every run.

| Operation (4-vCPU runner, 30 s rounds) | Default batching (2 s, 10 tx/block) | Tuned batching (200 ms, 100 tx/block) |
|---|---|---|
| `IssueCredential` mean latency at 100 tx/s offered | 72 ms (70-80) | 138 ms (120-150) |
| `IssueCredential` mean latency at 10 tx/s offered | 490 ms (480-520) | 130 ms |
| `IssueCredential` committed throughput at 300 tx/s offered | 227 tx/s (187-266) | 226 tx/s (195-299) |
| `VerifyCredential` (read-only) at 600 tx/s offered | 586 tx/s (570-600) | 572 tx/s (536-600) |

The write ceiling is **unstable between runs** (about 190-300 tx/s); do not quote a single run.

**Caveats.** Standard 2-organisation `test-network`, single Raft orderer (crash-fault tolerant, not Byzantine),
all containers plus the Caliper load generator on one machine, four runs per configuration. The N = 4-25
consortium-size experiment of the simulator is **not** reproduced here. Treat these as order-of-magnitude
validation, not as a model of a distributed national deployment.

## Notes

- Experiments 1-4 above come from a discrete-event simulation. Their absolute latency is lower than what real Fabric shows (see the Fabric benchmark section).
- The attack workload is synthetic and labelled; see the paper for the generation procedure and limitations.

## Citation

If you use this code, please cite the paper (citation details will be added once published).

## License

MIT, see `LICENSE`.
