import sys
t=open('proverif/bztid.pv.tmpl').read()
V={'full':('Full protocol: fresh verifier nonce, holder signature bound to nonce and verifier, issuer signature, ledger check.',
           'sign((n, vid, c1, c2), skH)','let (=n, =vid, =d1, =d2) = checksign(sg, pkh) in'),
   'no_nonce':('NEGATIVE CONTROL: holder signature does not cover the verifier nonce (replay possible).',
           'sign((vid, c1, c2), skH)','let (=vid, =d1, =d2) = checksign(sg, pkh) in'),
   'no_holder_binding':('NEGATIVE CONTROL: verifier does not check the holder signature (bearer credential).',
           'sign((n, vid, c1, c2), skH)','')}
for k,(d,hs,vs) in V.items():
    open(f'proverif/bztid_{k}.pv','w').write(t.replace('@@VARIANT@@',d).replace('@@HOLDERSIG@@',hs).replace('@@VERIFYSIG@@',vs))
