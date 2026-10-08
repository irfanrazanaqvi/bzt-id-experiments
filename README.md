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

## Additional experiments (all run on free GitHub Actions)

| Experiment | Workflow / script | Output |
|---|---|---|
| **Real biometric scores**: 9,164 public LFW images embedded with open-source FaceNet (VGGFace2 weights); 80,000 genuine/impostor pair scores, identities split into disjoint calibration/test halves | `.github/workflows/biometric-scores.yml`, `biometric/lfw_scores.py` | `data/biometric/` |
| **Exp. 6**: trust engine with the real biometric factor (other five factors synthetic), biometric-only gate, post-hoc hybrid, supervised ML baselines, weight sensitivity | `code/exp6_real_biometric.py` | `data/exp6_*.csv`, `figures/fig9_real_biometric.png` |
| **Fabric 3.0.0, Raft vs SmartBFT** (4 orderers), 2 runs x default/tuned batching | `.github/workflows/fabric-bft.yml` | `data/fabric3/` |
| **Baselines**: centralized SQLite service and ES256 token service, 3 runs each | `.github/workflows/baselines.yml`, `baselines/` | `data/baselines/`, `figures/fig10_baselines_bft.png` |
| **Crash-fault injection** on Fabric 3.0.0 SmartBFT (4 orderers) vs a one-orderer Raft control, 2 runs each | `.github/workflows/fabric-faults.yml`, `faults/inject.sh` | `data/faults/` |
| **ProVerif 2.05** symbolic verification of the credential protocol, with two negative controls | `.github/workflows/proverif.yml`, `proverif/` | `data/proverif/` |
| **BBS+ and Groth16** selective-disclosure benchmarks (4-vCPU runner, Node.js) | `.github/workflows/selective-disclosure.yml`, `zk/` | `data/zk/` |
| **RBA public login data**: non-biometric factors, single rules and supervised baselines (attacker-IP and account-takeover labels) | `.github/workflows/rba-probe.yml`, `rba/rba_eval.py` | `data/rba/` |
| **Emulated WAN**: Fabric 3.0.0 Raft vs SmartBFT with 0/15/40 ms one-way delay (tc netem), 2 runs each | `.github/workflows/fabric-wan.yml` | `data/wan/` |
| **Learned weights and ablation** on the RBA login data (user-split, recalibrated threshold) | `rba/rba_eval.py` (rba2 branch workflow) | `data/rba2/` |
| **CERT Insider Threat r4.2** (simulated, labelled): behavioural/device/time factors, ablation, supervised baselines | `cert/cert_eval.py`, `.github/workflows/cert-probe.yml` | `data/cert/` |

Key results: with real LFW biometric scores the engine reaches ROC-AUC 0.982 (95% CI 0.980-0.984), 84.7% recall at 6.7%
of legitimate sessions flagged; it misses most hardest-10% look-alike impostors (a proxy for spoofing, because LFW has no
spoof samples), which a 1%-FAR biometric gate catches, so a hybrid policy flags 97.6%. SmartBFT write ceiling about 145 tx/s
vs about 205-235 tx/s for Raft on the same Fabric version; minimal centralized/token baselines sustained 1,000 write tx/s.
Only the biometric factor is real; no public dataset contains CNIC/passport transactions. Fabric/baseline numbers come from
shared 4-vCPU runners and vary between runs.

Further results: with one of four SmartBFT orderers crashed the network keeps committing (a leader crash costs about 50 s
of unavailability), with two down it halts without committing; ProVerif proves injective agreement and secrecy with
negative controls (symbolic model only; only crash faults, not Byzantine behaviour, were injected); BBS+ presentation and
Groth16 age-proof costs are about 80-110 ms on a server CPU; on the public RBA login data (synthesized from real logins)
the fixed trust-engine weights do not transfer (attacker-IP AUC at chance), which is reported as a negative result.

Emulated 40 ms one-way delay lowers peak write throughput by about 40% (Raft) and two thirds (SmartBFT, which also fails 28% of
writes); learned weights recover account-takeover detection on the RBA data (19 held-out positives only); on the simulated CERT
benchmark the engine reaches AUC 0.87 but a single removable-media rule reaches 0.86.

## Notes

- Experiments 1-4 above come from a discrete-event simulation. Their absolute latency is lower than what real Fabric shows (see the Fabric benchmark section).
- The attack workload is synthetic and labelled; see the paper for the generation procedure and limitations.

## Citation

If you use this code, please cite the paper (citation details will be added once published).

## License

MIT, see `LICENSE`.
