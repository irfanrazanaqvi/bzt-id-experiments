#!/bin/bash
unset HTTPS_PROXY https_proxy; export NO_PROXY=$NO_PROXY,.example.com,localhost no_proxy=$no_proxy,.example.com,localhost
mkdir -p /home/claude/fabnative/results
for rep in 1 2 3; do
  npx caliper launch manager --caliper-workspace . --caliper-networkconfig networks/native.yaml --caliper-benchconfig benchmarks/hardening.yaml --caliper-flow-only-test > /home/claude/fabnative/results/rep$rep.log 2>&1
  cp report.html /home/claude/fabnative/results/report_rep$rep.html 2>/dev/null
done
echo DONE > /home/claude/fabnative/results/DONE
