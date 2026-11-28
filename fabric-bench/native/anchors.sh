set -e
B=/home/claude/fabnative; W=$B/work/anchor; mkdir -p $W; cd $W
for o in 1 2; do
  source $B/env_org$o.sh; P=$([ $o = 1 ] && echo 7051 || echo 9051)
  peer channel fetch config cfg.pb -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com -c mychannel --tls --cafile $ORDERER_CA 2>/dev/null
  configtxlator proto_decode --input cfg.pb --type common.Block --output cfg.json
  jq .data.data[0].payload.data.config cfg.json > c.json
  jq '.channel_group.groups.Application.groups.Org'$o'MSP.values += {"AnchorPeers":{"mod_policy":"Admins","value":{"anchor_peers":[{"host":"peer0.org'$o'.example.com","port":'$P'}]},"version":"0"}}' c.json > m.json
  configtxlator proto_encode --input c.json --type common.Config --output c.pb
  configtxlator proto_encode --input m.json --type common.Config --output m.pb
  configtxlator compute_update --channel_id mychannel --original c.pb --updated m.pb --output u.pb
  configtxlator proto_decode --input u.pb --type common.ConfigUpdate --output u.json
  echo '{"payload":{"header":{"channel_header":{"channel_id":"mychannel","type":2}},"data":{"config_update":'$(cat u.json)'}}}' | jq . > e.json
  configtxlator proto_encode --input e.json --type common.Envelope --output e.pb
  peer channel update -f e.pb -c mychannel -o localhost:7050 --ordererTLSHostnameOverride orderer.example.com --tls --cafile $ORDERER_CA 2>&1 | tail -1
done
