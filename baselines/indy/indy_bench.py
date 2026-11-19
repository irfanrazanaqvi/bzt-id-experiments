"""
Hyperledger Indy baseline (paper, Section 8.3): write and read throughput of a 4-node Indy (Plenum/RBFT)
ledger run by von-network on one host, driven with indy-vdr.
Write = NYM transaction (create a DID with its verkey), signed by the network's trustee; the call returns
after the transaction is ordered and written (f+1 matching replies). Read = GET_NYM on one node (state proof).
usage: python indy_bench.py <genesis.txn> <out.json>
"""
import asyncio, json, os, sys, time, statistics as st
import base58, nacl.signing
from indy_vdr import ledger, open_pool, set_protocol_version
set_protocol_version(2)
TRUSTEE = nacl.signing.SigningKey(b"000000000000000000000000Trustee1")
DID = base58.b58encode(bytes(TRUSTEE.verify_key)[:16]).decode()
def new_did():
    k = nacl.signing.SigningKey.generate(); vk = bytes(k.verify_key)
    return base58.b58encode(vk[:16]).decode(), base58.b58encode(vk).decode()
def pct(a, p): s = sorted(a); return s[min(len(s) - 1, int(len(s) * p))]
def summ(lat): return {"n": len(lat), "mean_ms": round(st.mean(lat), 1), "p50_ms": round(pct(lat, .5), 1), "p95_ms": round(pct(lat, .95), 1), "max_ms": round(max(lat), 1)} if lat else None
async def write(pool):
    d, vk = new_did(); req = ledger.build_nym_request(DID, d, vk, None, None)
    req.set_signature(TRUSTEE.sign(req.signature_input).signature)
    r = await pool.submit_request(req); return d
async def read(pool, d):
    r = await pool.submit_request(ledger.build_get_nym_request(None, d)); assert r["data"], "nym not found"
async def phase(pool, fn, total, conc):
    lat, fails, it = [], {}, iter(range(total))
    async def w():
        for i in it:
            t = time.perf_counter()
            try: await fn(i); lat.append((time.perf_counter() - t) * 1000)
            except Exception as e: k = type(e).__name__ + ":" + str(e)[:60]; fails[k] = fails.get(k, 0) + 1
    t0 = time.perf_counter(); await asyncio.gather(*[w() for _ in range(conc)]); wall = time.perf_counter() - t0
    return {"submitted": total, "concurrency": conc, "ok": len(lat), "wall_s": round(wall, 2), "tx_per_s": round(len(lat) / wall, 2), "latency": summ(lat), "failures": fails}
async def main(gen, out):
    pool = await open_pool(transactions_path=gen); res = {"ledger": "Hyperledger Indy (von-network, 4 nodes, one host)", "writes": [], "reads": []}
    for _ in range(5): await write(pool)  # warm-up
    dids = []
    async def wfn(i): dids.append(await write(pool))
    for total, conc in [(100, 1), (400, 16), (800, 64)]:
        res["writes"].append(await phase(pool, wfn, total, conc)); print(res["writes"][-1], flush=True)
    async def rfn(i): await read(pool, dids[i % len(dids)])
    for total, conc in [(300, 1), (2000, 16), (4000, 64)]:
        res["reads"].append(await phase(pool, rfn, total, conc)); print(res["reads"][-1], flush=True)
    json.dump(res, open(out, "w"), indent=1)
asyncio.run(main(sys.argv[1], sys.argv[2]))
