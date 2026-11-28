B=/home/claude/fabnative; ORG=$B/samples/test-network/organizations
export PATH=$B/bin:$PATH FABRIC_CFG_PATH=$B/config CORE_PEER_TLS_ENABLED=true CORE_PEER_LOCALMSPID=Org1MSP
export CORE_PEER_TLS_ROOTCERT_FILE=$ORG/peerOrganizations/org1.example.com/peers/peer0.org1.example.com/tls/ca.crt
export CORE_PEER_MSPCONFIGPATH=$ORG/peerOrganizations/org1.example.com/users/Admin@org1.example.com/msp
export CORE_PEER_ADDRESS=peer0.org1.example.com:7051
export ORDERER_CA=$ORG/ordererOrganizations/example.com/orderers/orderer.example.com/msp/tlscacerts/tlsca.example.com-cert.pem
export NO_PROXY=$NO_PROXY,localhost,127.0.0.1,.example.com no_proxy=$no_proxy,localhost,127.0.0.1,.example.com GRPC_PROXY= grpc_proxy=; unset HTTPS_PROXY https_proxy
