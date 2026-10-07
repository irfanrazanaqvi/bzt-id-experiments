#!/usr/bin/env bash
# usage: bench.sh <mode> <out.csv>   (starts server, drives fixed-rate load with autocannon, records latency/throughput)
set -u
MODE=$1; OUT=$2
rm -f /tmp/central.db*
MODE=$MODE PORT=8080 node baselines/server.js > "$OUT.server.log" 2>&1 &
SP=$!; sleep 2
# seed a verification token / id
if [ "$MODE" = central ]; then
  ID=$(curl -s -XPOST localhost:8080/issue -d '{"id":"seed1","subject":"s"}' | node -pe 'JSON.parse(require("fs").readFileSync(0)).id')
  VURL="http://localhost:8080/verify/$ID"
else
  TOK=$(curl -s -XPOST localhost:8080/issue -d '{"id":"seed1","subject":"s"}' | node -pe 'JSON.parse(require("fs").readFileSync(0)).token')
  VURL="http://localhost:8080/verify/seed1?t=$TOK"
fi
echo "name,offered_tps,avg_latency_ms,p99_latency_ms,achieved_tps,errors" > "$OUT"
run() { # name rate method url body
  J=$(npx -y autocannon -j -d 30 -c 64 -R "$2" -m "$3" ${5:+-b "$5" -H "content-type: application/json"} "$4" 2>/dev/null)
  echo "$J" | node -e 'const j=JSON.parse(require("fs").readFileSync(0));console.log([process.argv[1],process.argv[2],j.latency.average,j.latency.p99,j.requests.average,j.errors+j.non2xx].join(","))' "$1" "$2" >> "$OUT"
}
for r in 10 100 200 300 600 1000; do run "issue" $r POST http://localhost:8080/issue '{"subject":"s","name":"A","dob":"1990-01-01"}'; done
for r in 100 400 600 1000 2000; do run "verify" $r GET "$VURL"; done
for r in 10 100 200; do run "audit" $r POST http://localhost:8080/audit '{"id":"seed1"}'; done
kill $SP; cat "$OUT"
