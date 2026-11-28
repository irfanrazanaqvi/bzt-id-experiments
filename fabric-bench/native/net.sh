#!/bin/bash
# Native (no Docker) Fabric 2.5.9 test network: 1 Raft orderer, peer0.org1, peer0.org2, channel "mychannel".
set -e
unset HTTPS_PROXY https_proxy; export NO_PROXY=$NO_PROXY,localhost,127.0.0.1,.example.com no_proxy=$no_proxy,localhost,127.0.0.1,.example.com
B=/home/claude/fabnative; export PATH=$B/bin:$PATH
W=$B/work; rm -rf $W; mkdir -p $W/{orderer,org1,org2,logs}
cd $B/samples/test-network
rm -rf organizations/ordererOrganizations organizations/peerOrganizations
for f in org1 org2 orderer; do cryptogen generate --config=organizations/cryptogen/crypto-config-$f.yaml --output=organizations >/dev/null; done
export FABRIC_CFG_PATH=$B/samples/test-network/configtx
configtxgen -profile ChannelUsingRaft -outputBlock $W/mychannel.block -channelID mychannel 2>/dev/null
ORG=$B/samples/test-network/organizations
O=$ORG/ordererOrganizations/example.com/orderers/orderer.example.com
# orderer
( export FABRIC_CFG_PATH=$B/config ORDERER_GENERAL_LISTENADDRESS=0.0.0.0 ORDERER_GENERAL_LISTENPORT=7050 \
  ORDERER_GENERAL_LOCALMSPID=OrdererMSP ORDERER_GENERAL_LOCALMSPDIR=$O/msp \
  ORDERER_GENERAL_TLS_ENABLED=true ORDERER_GENERAL_TLS_PRIVATEKEY=$O/tls/server.key ORDERER_GENERAL_TLS_CERTIFICATE=$O/tls/server.crt ORDERER_GENERAL_TLS_ROOTCAS=[$O/tls/ca.crt] \
  ORDERER_GENERAL_CLUSTER_CLIENTCERTIFICATE=$O/tls/server.crt ORDERER_GENERAL_CLUSTER_CLIENTPRIVATEKEY=$O/tls/server.key ORDERER_GENERAL_CLUSTER_ROOTCAS=[$O/tls/ca.crt] \
  ORDERER_GENERAL_BOOTSTRAPMETHOD=none ORDERER_CHANNELPARTICIPATION_ENABLED=true \
  ORDERER_ADMIN_LISTENADDRESS=0.0.0.0:7053 ORDERER_ADMIN_TLS_ENABLED=true ORDERER_ADMIN_TLS_PRIVATEKEY=$O/tls/server.key ORDERER_ADMIN_TLS_CERTIFICATE=$O/tls/server.crt ORDERER_ADMIN_TLS_CLIENTROOTCAS=[$O/tls/ca.crt] ORDERER_ADMIN_TLS_ROOTCAS=[$O/tls/ca.crt] \
  ORDERER_OPERATIONS_LISTENADDRESS=127.0.0.1:9443 ORDERER_FILELEDGER_LOCATION=$W/orderer/ledger ORDERER_CONSENSUS_WALDIR=$W/orderer/wal ORDERER_CONSENSUS_SNAPDIR=$W/orderer/snap ;
  nohup orderer > $W/logs/orderer.log 2>&1 & )
EB='[{"name":"ccaas_builder","path":"'$B'/builders/ccaas","propagateEnvironment":["CHAINCODE_AS_A_SERVICE_BUILDER_CONFIG"]}]'
startpeer(){ # org port ccport opsport
  local o=$1 p=$2 cc=$3 ops=$4; local P=$ORG/peerOrganizations/$o.example.com/peers/peer0.$o.example.com
  ( export FABRIC_CFG_PATH=$B/config CORE_PEER_ID=peer0.$o.example.com CORE_PEER_ADDRESS=peer0.$o.example.com:$p CORE_PEER_LISTENADDRESS=0.0.0.0:$p \
    CORE_PEER_CHAINCODEADDRESS=peer0.$o.example.com:$cc CORE_PEER_CHAINCODELISTENADDRESS=0.0.0.0:$cc \
    CORE_PEER_GOSSIP_BOOTSTRAP=peer0.$o.example.com:$p CORE_PEER_GOSSIP_EXTERNALENDPOINT=peer0.$o.example.com:$p \
    CORE_PEER_LOCALMSPID=$( [ $o = org1 ] && echo Org1MSP || echo Org2MSP ) CORE_PEER_MSPCONFIGPATH=$P/msp \
    CORE_PEER_TLS_ENABLED=true CORE_PEER_TLS_CERT_FILE=$P/tls/server.crt CORE_PEER_TLS_KEY_FILE=$P/tls/server.key CORE_PEER_TLS_ROOTCERT_FILE=$P/tls/ca.crt \
    CORE_PEER_FILESYSTEMPATH=$W/$o/production CORE_OPERATIONS_LISTENADDRESS=127.0.0.1:$ops CORE_PEER_PROFILE_ENABLED=false \
    CORE_CHAINCODE_EXTERNALBUILDERS="$EB" CORE_VM_ENDPOINT= CORE_LEDGER_STATE_STATEDATABASE=goleveldb ;
    nohup peer node start > $W/logs/peer-$o.log 2>&1 & )
}
startpeer org1 7051 7052 9444
startpeer org2 9051 9052 9445
sleep 4
osnadmin channel join --channelID mychannel --config-block $W/mychannel.block -o localhost:7053 --ca-file $O/tls/ca.crt --client-cert $O/tls/server.crt --client-key $O/tls/server.key >/dev/null
sleep 2
for o in org1 org2; do source $B/env_$o.sh; peer channel join -b $W/mychannel.block 2>&1 | tail -1; done
