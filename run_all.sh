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
echo "== Done. Datasets in ./data, figures in ./figures =="
