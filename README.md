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

## Notes

- This is a simulation, not a production Hyperledger Fabric deployment. Latency and throughput figures come from the discrete-event model described in the paper.
- The attack workload is synthetic and labelled; see the paper for the generation procedure and limitations.

## Citation

If you use this code, please cite the paper (citation details will be added once published).

## License

MIT, see `LICENSE`.
