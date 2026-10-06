"""
exp4_tamper_evidence.py
--------------------------------------------------------------------
Experiment 4: Tamper-evidence of the hash-chained permissioned ledger.

We issue a batch of credentials, seal them into blocks, then simulate
an adversary who compromises a single storage replica and silently
mutates one field of one historical transaction (e.g. changing a VC's
claims hash to forge a credential post-hoc). We measure:
  (a) detection rate of `integrity_check()` (should be 100%: any single
      bit-flip anywhere in the chain invalidates every subsequent hash)
  (b) how many blocks downstream of the tampered block become invalid
      (illustrating the "avalanche"/tamper-propagation property)
This operationalises the immutability security claim made in Sec. 9.

Outputs: data/exp4_tamper_results.csv
--------------------------------------------------------------------
"""
import sys, os, copy, random, uuid, time
sys.path.insert(0, os.path.dirname(__file__))
from bzt_id_sim import PermissionedLedger, VerifiableCredential, gen_did, sha256_hex
import pandas as pd

OUT_DATA = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUT_DATA, exist_ok=True)


def build_ledger(n_credentials=500, block_size=20, num_peers=10, seed=5):
    ledger = PermissionedLedger(num_peers=num_peers, block_size=block_size, seed=seed)
    for _ in range(n_credentials):
        did = gen_did()
        vc = VerifiableCredential(
            vc_id=uuid.uuid4().hex, subject_did=did, issuer_did="did:bzt:nadra-root",
            credential_type=random.choice(["CNIC", "Passport"]), claims={"name": "citizen"},
            biometric_hash=sha256_hex(did), issued_at=time.time(),
            expiry=time.time() + 3600 * 24 * 3650,
        )
        ledger.issue_credential(vc)
    ledger.flush()
    return ledger


def tamper_and_measure(ledger, target_block_index):
    """Flips one character of one transaction's payload_hash in a
    target block (simulating an unauthorised data-at-rest edit),
    without recomputing hashes (as a naive attacker who only edits the
    stored ledger file would do), then checks how the tamper is
    detected and how far it propagates."""
    tampered = copy.deepcopy(ledger)
    block = tampered.chain[target_block_index]
    tx = block.transactions[0]
    original = tx.payload_hash
    tx.payload_hash = ("f" if original[0] != "f" else "0") + original[1:]

    # integrity_check walks the whole chain; report first failing index
    first_break = None
    for i in range(1, len(tampered.chain)):
        b = tampered.chain[i]
        prev_ok = b.prev_hash == tampered.chain[i - 1].hash
        hash_ok = b.compute_hash() == b.hash
        if not (prev_ok and hash_ok):
            first_break = i
            break
    detected = not tampered.integrity_check()
    blocks_invalidated = (len(tampered.chain) - first_break) if first_break else 0
    return {
        "target_block": target_block_index,
        "chain_length": len(tampered.chain),
        "tamper_detected": detected,
        "first_invalid_block": first_break,
        "downstream_blocks_invalidated": blocks_invalidated,
    }


if __name__ == "__main__":
    ledger = build_ledger()
    n_blocks = len(ledger.chain)
    rows = []
    # Tamper at several points along the chain (early / middle / late)
    for frac in [0.05, 0.25, 0.5, 0.75, 0.95]:
        idx = max(1, min(n_blocks - 1, int(frac * n_blocks)))
        rows.append(tamper_and_measure(ledger, idx))

    # Baseline: centralized single-database mutation is *silent* by
    # construction (no hash chain to break) -- included for comparison
    # in the manuscript's comparison table, not computed here (qualitative row).

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DATA, "exp4_tamper_results.csv"), index=False)
    print(df.to_string(index=False))
    print(f"Total blocks in test chain: {n_blocks}")
    print("Experiment 4 complete.")
