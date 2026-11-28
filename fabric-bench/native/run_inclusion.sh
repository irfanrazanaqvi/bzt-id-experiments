#!/bin/bash
cd /home/claude/bzt-id-experiments/fabric-bench/caliper
while [ ! -f /home/claude/fabnative/results/DONE ]; do sleep 20; done
unset HTTPS_PROXY https_proxy; export NO_PROXY=$NO_PROXY,.example.com,localhost no_proxy=$no_proxy,.example.com,localhost
for rep in 1 2 3; do
  npx caliper launch manager --caliper-workspace . --caliper-networkconfig networks/native.yaml --caliper-benchconfig benchmarks/inclusion.yaml --caliper-flow-only-test > /home/claude/fabnative/results/incl_rep$rep.log 2>&1
done
echo DONE > /home/claude/fabnative/results/DONE_INCL
