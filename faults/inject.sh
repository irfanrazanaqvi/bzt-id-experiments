#!/usr/bin/env bash
# Crash-fault injection on a running Fabric 3.0 test-network while submitting real, committed transactions.
# usage: inject.sh <bft|raft> <out.csv>      (run from the repo root; fabric-samples must be present and network up)
set -u
MODE=$1; OUT=$2
TN="$PWD/fabric-samples/test-network"; export PATH="$TN/../bin:$PATH"
export FABRIC_CFG_PATH="$TN/../config" CORE_PEER_TLS_ENABLED=true CORE_PEER_LOCALMSPID=Org1MSP
O1="$TN/organizations/peerOrganizations/org1.example.com"; O2="$TN/organizations/peerOrganizations/org2.example.com"
export CORE_PEER_TLS_ROOTCERT_FILE="$O1/tlsca/tlsca.org1.example.com-cert.pem" CORE_PEER_MSPCONFIGPATH="$O1/users/Admin@org1.example.com/msp" CORE_PEER_ADDRESS=localhost:7051
OCA="$TN/organizations/ordererOrganizations/example.com/tlsca/tlsca.example.com-cert.pem"
if [ "$MODE" = bft ]; then OADDR=localhost:7052; OHOST=orderer2.example.com; else OADDR=localhost:7050; OHOST=orderer.example.com; fi
echo "scenario,i,rc,latency_ms" > "$OUT"
inv() { # scenario idx timeout
  local id="f-$(date +%s%N)" t0 t1 rc
  t0=$(date +%s%N)
  timeout "$3" peer chaincode invoke -o $OADDR --ordererTLSHostnameOverride $OHOST --tls --cafile "$OCA" -C mychannel -n bzt \
    --peerAddresses localhost:7051 --tlsRootCertFiles "$O1/tlsca/tlsca.org1.example.com-cert.pem" \
    --peerAddresses localhost:9051 --tlsRootCertFiles "$O2/tlsca/tlsca.org2.example.com-cert.pem" \
    -c "{\"function\":\"IssueCredential\",\"Args\":[\"$id\",\"did:bzt:x\",\"h$id\",\"nadra\"]}" --waitForEvent --waitForEventTimeout 25s > /tmp/inv.log 2>&1
  rc=$?; t1=$(date +%s%N)
  echo "$1,$2,$rc,$(( (t1-t0)/1000000 ))" | tee -a "$OUT"
  [ $rc -ne 0 ] && tail -2 /tmp/inv.log | sed 's/^/   err: /'
}
run() { for i in $(seq 1 $2); do inv "$1" $i ${3:-40}; done; }
event() { echo "# $(date +%s) $*" | tee -a "$OUT.events"; }
: > "$OUT.events"
event start; run S0_all_up 15
if [ "$MODE" = bft ]; then
  event "stop orderer1 (initial leader; 3 of 4 up)"; docker stop orderer.example.com >/dev/null; run S1_one_down_leader 15 60
  event "start orderer1, stop orderer4"; docker start orderer.example.com >/dev/null; sleep 20; docker stop orderer4.example.com >/dev/null; run S2_one_down_follower 15 60
  event "stop orderer3 too (2 of 4 up: quorum lost)"; docker stop orderer3.example.com >/dev/null; run S3_two_down 5 35
  event "start orderer3 and orderer4"; docker start orderer3.example.com orderer4.example.com >/dev/null
  T0=$(date +%s); ok=0
  while [ $(( $(date +%s) - T0 )) -lt 180 ]; do
    id="f-$(date +%s%N)"
    if timeout 40 peer chaincode invoke -o $OADDR --ordererTLSHostnameOverride $OHOST --tls --cafile "$OCA" -C mychannel -n bzt --peerAddresses localhost:7051 --tlsRootCertFiles "$O1/tlsca/tlsca.org1.example.com-cert.pem" --peerAddresses localhost:9051 --tlsRootCertFiles "$O2/tlsca/tlsca.org2.example.com-cert.pem" -c "{\"function\":\"IssueCredential\",\"Args\":[\"$id\",\"d\",\"h\",\"n\"]}" --waitForEvent --waitForEventTimeout 25s >/dev/null 2>&1; then ok=1; break; fi
  done
  event "recovered=$ok after $(( $(date +%s) - T0 )) s"; run S4_recovered 15
else
  event "stop the only orderer"; docker stop orderer.example.com >/dev/null; run S1_orderer_down 5 35
  event "start orderer"; docker start orderer.example.com >/dev/null; T0=$(date +%s); ok=0
  while [ $(( $(date +%s) - T0 )) -lt 180 ]; do
    id="f-$(date +%s%N)"
    if timeout 40 peer chaincode invoke -o $OADDR --ordererTLSHostnameOverride $OHOST --tls --cafile "$OCA" -C mychannel -n bzt --peerAddresses localhost:7051 --tlsRootCertFiles "$O1/tlsca/tlsca.org1.example.com-cert.pem" --peerAddresses localhost:9051 --tlsRootCertFiles "$O2/tlsca/tlsca.org2.example.com-cert.pem" -c "{\"function\":\"IssueCredential\",\"Args\":[\"$id\",\"d\",\"h\",\"n\"]}" --waitForEvent --waitForEventTimeout 25s >/dev/null 2>&1; then ok=1; break; fi
  done
  event "recovered=$ok after $(( $(date +%s) - T0 )) s"; run S2_recovered 15
fi
event end
