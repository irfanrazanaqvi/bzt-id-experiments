#!/usr/bin/env bash
# Reproduces every experiment, dataset and figure from a clean checkout.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
echo "== 1. Installing Python dependencies =="
pip install --quiet -r requirements.txt
echo "== 2. Running experiments and generating figures =="
cd code
python3 fig1_architecture.py
python3 fig2_sequence.py
python3 exp1_scalability.py
python3 exp3_zero_trust_detection.py
python3 exp4_tamper_evidence.py
python3 exp5_sensitivity.py
python3 plot_fabric_results.py
python3 exp6_real_biometric.py ../data/biometric/lfw_pair_scores.csv
python3 fig10_baselines_bft.py
echo "== Fabric faults, ProVerif, BBS+/Groth16 and RBA runs are GitHub Actions workflows (see .github/workflows); their outputs are in data/faults, data/proverif, data/zk, data/rba =="
echo "== Done. Datasets in ./data, figures in ./figures =="
