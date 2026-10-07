#!/usr/bin/env bash
# Writes caliper/networks/networkConfig.yaml for the fabric-samples test-network.
# usage: make_network_config.sh <path-to-fabric-samples/test-network> <output.yaml>
set -euo pipefail
TN="$(cd "$1" && pwd)"
OUT="$2"
ORG="$TN/organizations/peerOrganizations/org1.example.com"
KEY="$(ls "$ORG"/users/User1@org1.example.com/msp/keystore/*_sk | head -n1)"
CERT="$(ls "$ORG"/users/User1@org1.example.com/msp/signcerts/*.pem | head -n1)"
cat > "$OUT" <<YAML
name: BZT-ID Fabric test-network
version: "2.0.0"
caliper:
  blockchain: fabric
channels:
  - channelName: mychannel
    contracts:
      - id: bzt
organizations:
  - mspid: Org1MSP
    identities:
      certificates:
        - name: User1@org1.example.com
          clientPrivateKey:
            path: $KEY
          clientSignedCert:
            path: $CERT
    connectionProfile:
      path: $ORG/connection-org1.yaml
      discover: true
YAML
echo "wrote $OUT"
