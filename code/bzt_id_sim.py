"""
bzt_id_sim.py
--------------------------------------------------------------------
Reference implementation and experimental testbed for:

  "A Blockchain-Enabled Zero-Trust Digital Identity Architecture for
   Secure CNIC and Passport Services" (BZT-ID)

This module implements, in software simulation, the three core
components of the proposed architecture so that the performance and
security claims made in the paper can be reproduced end-to-end:

  1. PermissionedLedger   - a Practical-Byzantine-Fault-Tolerant (PBFT)
                             style permissioned blockchain that stores
                             identity-lifecycle events (Issue, Verify,
                             Update, Revoke) as hash-chained blocks
                             endorsed by a quorum of Registrar Authority
                             (NADRA / DGIP) peer nodes.
  2. DID / VC layer        - W3C Decentralized Identifier (DID) and
                             Verifiable Credential (VC) issuance,
                             signing (ECDSA/SECP256k1 via a light
                             HMAC-based surrogate signature for the
                             simulation), and selective-disclosure
                             verification.
  3. ZeroTrustEngine        - a continuous, attribute-based trust-scoring
                             engine that fuses biometric-match
                             confidence, device posture, network/
                             geo-velocity, and behavioural signals into
                             a per-request trust score, and enforces a
                             "never trust, always verify" policy
                             independent of the blockchain layer.

The module is intentionally dependency-light (Python standard library
+ numpy/pandas for analysis) so referees / readers can run it without
a real Hyperledger Fabric or Ethereum deployment. It is a discrete-event
*performance and security simulation*, not a production system: places
where a production deployment would use real cryptography (ECDSA
signatures, zk-SNARK selective disclosure, TLS-mutual-auth channels)
are clearly marked.

Author: (for anonymisation during review)
License: MIT (for reproducibility artifact)
--------------------------------------------------------------------
"""

from __future__ import annotations
import hashlib
import hmac
import json
import math
import random
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple


# =====================================================================
# 1. CRYPTOGRAPHIC PRIMITIVES (simulation surrogates)
# =====================================================================

SECRET_NETWORK_KEY = b"BZT-ID-SIMULATED-NETWORK-ROOT-KEY"  # simulation only


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hmac_sign(payload: str, key: bytes = SECRET_NETWORK_KEY) -> str:
    """Surrogate for an ECDSA/EdDSA digital signature over `payload`.
    Provides the same experimental properties (fixed-cost sign/verify,
    tamper-evidence) without requiring an elliptic-curve library."""
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def hmac_verify(payload: str, signature: str, key: bytes = SECRET_NETWORK_KEY) -> bool:
    return hmac.compare_digest(hmac_sign(payload, key), signature)


def gen_did(prefix: str = "did:bzt") -> str:
    """W3C DID-style identifier: did:bzt:<method-specific-id>."""
    return f"{prefix}:{uuid.uuid4().hex}"


# =====================================================================
# 2. VERIFIABLE CREDENTIAL (VC) DATA MODEL
# =====================================================================

@dataclass
class VerifiableCredential:
    vc_id: str
    subject_did: str
    issuer_did: str
    credential_type: str  # "CNIC" | "Passport"
    claims: Dict[str, Any]
    biometric_hash: str
    issued_at: float
    expiry: float
    signature: str = ""
    revoked: bool = False

    def canonical(self) -> str:
        payload = {
            "vc_id": self.vc_id,
            "subject_did": self.subject_did,
            "issuer_did": self.issuer_did,
            "type": self.credential_type,
            "claims": self.claims,
            "biometric_hash": self.biometric_hash,
            "issued_at": self.issued_at,
            "expiry": self.expiry,
        }
        return json.dumps(payload, sort_keys=True)

    def sign(self):
        self.signature = hmac_sign(self.canonical())

    def verify_signature(self) -> bool:
        return hmac_verify(self.canonical(), self.signature)


# =====================================================================
# 3. PERMISSIONED BLOCKCHAIN LEDGER (PBFT-style, Hyperledger-Fabric-like)
# =====================================================================

@dataclass
class Transaction:
    tx_id: str
    tx_type: str  # ISSUE | VERIFY | UPDATE | REVOKE
    subject_did: str
    payload_hash: str
    timestamp: float
    endorsements: List[str] = field(default_factory=list)


@dataclass
class Block:
    index: int
    timestamp: float
    transactions: List[Transaction]
    prev_hash: str
    hash: str = ""

    def compute_hash(self) -> str:
        tx_repr = json.dumps(
            [asdict(t) for t in self.transactions], sort_keys=True, default=str
        )
        block_repr = f"{self.index}|{self.timestamp}|{tx_repr}|{self.prev_hash}"
        return sha256_hex(block_repr)


class PermissionedLedger:
    """
    Simulates a permissioned, PBFT-style consortium blockchain
    (e.g., Hyperledger Fabric with Raft/PBFT ordering) operated jointly
    by the Registrar Authority (NADRA), the Passport Directorate (DGIP),
    and independently-audited notary peers (banks, telecom KYC agents).

    Consensus model: a transaction is committed to a block once it
    receives endorsement signatures from >= ceil(2N/3) of the N peer
    nodes (Byzantine quorum), matching PBFT's fault-tolerance bound of
    f = floor((N-1)/3) faulty nodes.
    """

    def __init__(self, num_peers: int = 4, block_size: int = 10,
                 endorsement_latency_ms: Tuple[float, float] = (8, 25),
                 ordering_latency_ms: Tuple[float, float] = (5, 15),
                 seed: Optional[int] = None):
        self.num_peers = num_peers
        self.block_size = block_size
        self.endorsement_latency_ms = endorsement_latency_ms
        self.ordering_latency_ms = ordering_latency_ms
        self.rng = random.Random(seed)
        genesis = Block(0, time.time(), [], "0" * 64)
        genesis.hash = genesis.compute_hash()
        self.chain: List[Block] = [genesis]
        self.mempool: List[Transaction] = []
        self.credential_index: Dict[str, VerifiableCredential] = {}
        self.audit_log: List[Dict[str, Any]] = []

    # ---- quorum / BFT fault bound -----------------------------------
    def byzantine_quorum(self) -> int:
        return math.ceil((2 * self.num_peers) / 3)

    def max_faulty_tolerated(self) -> int:
        return max(0, (self.num_peers - 1) // 3)

    # ---- endorsement simulation ---------------------------------------
    def _simulate_endorsement_round(self, tx: Transaction) -> float:
        """Returns total wall-clock latency (ms) for a transaction to
        collect a Byzantine quorum of endorsement signatures plus
        ordering-service sequencing."""
        quorum = self.byzantine_quorum()
        peer_latencies = sorted(
            self.rng.uniform(*self.endorsement_latency_ms) for _ in range(self.num_peers)
        )
        # Endorsement completes once the quorum-th fastest peer responds
        endorsement_time = peer_latencies[quorum - 1]
        ordering_time = self.rng.uniform(*self.ordering_latency_ms)
        tx.endorsements = [f"peer-{i}" for i in range(quorum)]
        return endorsement_time + ordering_time

    def submit_transaction(self, tx_type: str, subject_did: str,
                            payload: Dict[str, Any]) -> Tuple[Transaction, float]:
        payload_hash = sha256_hex(json.dumps(payload, sort_keys=True, default=str))
        tx = Transaction(
            tx_id=uuid.uuid4().hex,
            tx_type=tx_type,
            subject_did=subject_did,
            payload_hash=payload_hash,
            timestamp=time.time(),
        )
        latency_ms = self._simulate_endorsement_round(tx)
        self.mempool.append(tx)
        self.audit_log.append({
            "tx_id": tx.tx_id, "type": tx_type, "subject": subject_did,
            "latency_ms": latency_ms, "ts": tx.timestamp
        })
        if len(self.mempool) >= self.block_size:
            self._seal_block()
        return tx, latency_ms

    def _seal_block(self):
        prev_hash = self.chain[-1].hash
        block = Block(len(self.chain), time.time(), self.mempool[:self.block_size], prev_hash)
        block.hash = block.compute_hash()
        self.chain.append(block)
        self.mempool = self.mempool[self.block_size:]

    def flush(self):
        while self.mempool:
            self._seal_block()

    # ---- credential lifecycle -----------------------------------------
    def issue_credential(self, vc: VerifiableCredential) -> float:
        vc.sign()
        self.credential_index[vc.vc_id] = vc
        _, latency = self.submit_transaction(
            "ISSUE", vc.subject_did,
            {"vc_id": vc.vc_id, "hash": sha256_hex(vc.canonical())}
        )
        return latency

    def revoke_credential(self, vc_id: str) -> Optional[float]:
        vc = self.credential_index.get(vc_id)
        if not vc:
            return None
        vc.revoked = True
        _, latency = self.submit_transaction("REVOKE", vc.subject_did, {"vc_id": vc_id})
        return latency

    def verify_credential(self, vc_id: str) -> Tuple[bool, float, str]:
        vc = self.credential_index.get(vc_id)
        if vc is None:
            return False, 0.0, "NOT_FOUND"
        _, latency = self.submit_transaction("VERIFY", vc.subject_did, {"vc_id": vc_id})
        if vc.revoked:
            return False, latency, "REVOKED"
        if not vc.verify_signature():
            return False, latency, "SIGNATURE_INVALID"
        if time.time() > vc.expiry:
            return False, latency, "EXPIRED"
        return True, latency, "VALID"

    def integrity_check(self) -> bool:
        """Re-walks the chain re-computing hashes to confirm
        tamper-evidence (used in the security-analysis experiment)."""
        for i in range(1, len(self.chain)):
            block = self.chain[i]
            if block.prev_hash != self.chain[i - 1].hash:
                return False
            if block.compute_hash() != block.hash:
                return False
        return True


# =====================================================================
# 4. ZERO-TRUST CONTINUOUS VERIFICATION ENGINE
# =====================================================================

@dataclass
class RequestContext:
    """Attributes collected by the Policy Enforcement Point (PEP) for
    every access/verification request, per NIST SP 800-207 zero-trust
    tenets (policy decisions are per-request, based on dynamic signals,
    not a one-time login)."""
    biometric_match_score: float   # 0-1, from live liveness+match
    device_posture_score: float    # 0-1, patch level / attestation
    geo_velocity_anomaly: float    # 0-1, 0 = normal, 1 = impossible travel
    behavioural_anomaly: float     # 0-1, 0 = normal typing/usage pattern
    network_reputation: float      # 0-1, 1 = clean IP/ASN reputation
    time_of_day_risk: float        # 0-1, off-hours risk


class ZeroTrustEngine:
    """
    Implements a lightweight, explainable multi-factor trust-scoring
    function T(x) in [0,1] and a policy-decision-point (PDP) that maps
    T(x) to {ALLOW, STEP_UP_AUTH, DENY}, independent of and in addition
    to the blockchain-anchored credential check. This operationalises
    the "never trust, always verify" principle for every CNIC/passport
    service transaction (renewal, e-gate boarding, KYC lookup, etc.).
    """

    # Convex combination of six normalised risk signals (weights sum to
    # 1.0), calibrated by grid-search against a labelled synthetic risk
    # dataset (see experiments/train_weights.py in the code appendix)
    # to maximise separation between the legitimate-user and attack
    # score distributions reported in Section 7 (Fig. 6).
    WEIGHTS = {
        "biometric_match_score": 0.30,   # positively-oriented signal
        "device_posture_score": 0.15,    # positively-oriented signal
        "network_reputation": 0.15,      # positively-oriented signal
        "geo_velocity_anomaly": 0.20,    # anomaly signal -> inverted
        "behavioural_anomaly": 0.15,     # anomaly signal -> inverted
        "time_of_day_risk": 0.05,        # anomaly signal -> inverted
    }
    ANOMALY_FEATURES = {"geo_velocity_anomaly", "behavioural_anomaly", "time_of_day_risk"}

    ALLOW_THRESHOLD = 0.75
    STEP_UP_THRESHOLD = 0.50

    def score(self, ctx: RequestContext) -> float:
        x = asdict(ctx)
        t = 0.0
        for k, w in self.WEIGHTS.items():
            v = x[k]
            contrib = (1.0 - v) if k in self.ANOMALY_FEATURES else v
            t += w * contrib
        return max(0.0, min(1.0, t))

    def decide(self, ctx: RequestContext) -> Tuple[str, float]:
        t = self.score(ctx)
        if t >= self.ALLOW_THRESHOLD:
            return "ALLOW", t
        if t >= self.STEP_UP_THRESHOLD:
            return "STEP_UP_AUTH", t
        return "DENY", t


# =====================================================================
# 5. SYNTHETIC WORKLOAD GENERATORS
# =====================================================================

def synthetic_legit_context(rng: random.Random) -> RequestContext:
    """90% typical sessions; 10% 'degraded-but-legitimate' sessions
    (e.g. genuine overseas Pakistani applicant on unfamiliar public
    Wi-Fi, older handset, red-eye application) so the legitimate-class
    score distribution has a realistic lower tail rather than a hard
    floor, matching field-reported false-positive rates in continuous
    authentication studies."""
    if rng.random() < 0.10:
        return RequestContext(
            biometric_match_score=rng.uniform(0.55, 0.85),
            device_posture_score=rng.uniform(0.35, 0.75),
            geo_velocity_anomaly=rng.uniform(0.1, 0.55),
            behavioural_anomaly=rng.uniform(0.1, 0.5),
            network_reputation=rng.uniform(0.3, 0.75),
            time_of_day_risk=rng.uniform(0.2, 0.8),
        )
    return RequestContext(
        biometric_match_score=rng.uniform(0.85, 0.995),
        device_posture_score=rng.uniform(0.7, 1.0),
        geo_velocity_anomaly=rng.uniform(0.0, 0.15),
        behavioural_anomaly=rng.uniform(0.0, 0.2),
        network_reputation=rng.uniform(0.7, 1.0),
        time_of_day_risk=rng.uniform(0.0, 0.4),
    )


def synthetic_attack_context(rng: random.Random, kind: str) -> RequestContext:
    """kind in {spoof, credential_stuffing, impossible_travel, insider_replay}"""
    if kind == "spoof":  # deepfake / presentation attack on biometrics
        return RequestContext(
            biometric_match_score=rng.uniform(0.3, 0.7),
            device_posture_score=rng.uniform(0.4, 0.9),
            geo_velocity_anomaly=rng.uniform(0.0, 0.3),
            behavioural_anomaly=rng.uniform(0.2, 0.6),
            network_reputation=rng.uniform(0.3, 0.8),
            time_of_day_risk=rng.uniform(0.0, 0.6),
        )
    if kind == "credential_stuffing":
        return RequestContext(
            biometric_match_score=rng.uniform(0.0, 0.3),
            device_posture_score=rng.uniform(0.1, 0.5),
            geo_velocity_anomaly=rng.uniform(0.2, 0.6),
            behavioural_anomaly=rng.uniform(0.5, 0.95),
            network_reputation=rng.uniform(0.0, 0.4),
            time_of_day_risk=rng.uniform(0.3, 1.0),
        )
    if kind == "impossible_travel":
        return RequestContext(
            biometric_match_score=rng.uniform(0.6, 0.95),
            device_posture_score=rng.uniform(0.5, 0.9),
            geo_velocity_anomaly=rng.uniform(0.75, 1.0),
            behavioural_anomaly=rng.uniform(0.2, 0.5),
            network_reputation=rng.uniform(0.2, 0.7),
            time_of_day_risk=rng.uniform(0.2, 0.8),
        )
    # insider_replay: stolen/replayed credential from a legitimate device
    return RequestContext(
        biometric_match_score=rng.uniform(0.0, 0.4),
        device_posture_score=rng.uniform(0.6, 1.0),
        geo_velocity_anomaly=rng.uniform(0.4, 0.9),
        behavioural_anomaly=rng.uniform(0.4, 0.85),
        network_reputation=rng.uniform(0.5, 0.9),
        time_of_day_risk=rng.uniform(0.1, 0.7),
    )


if __name__ == "__main__":
    # smoke test
    ledger = PermissionedLedger(num_peers=4, seed=42)
    zte = ZeroTrustEngine()
    rng = random.Random(1)

    vc = VerifiableCredential(
        vc_id=uuid.uuid4().hex, subject_did=gen_did(), issuer_did="did:bzt:nadra-root",
        credential_type="CNIC", claims={"name": "A. Citizen", "dob": "1998-04-11"},
        biometric_hash=sha256_hex("fingerprint-template-demo"),
        issued_at=time.time(), expiry=time.time() + 3600 * 24 * 3650,
    )
    lat = ledger.issue_credential(vc)
    ok, vlat, reason = ledger.verify_credential(vc.vc_id)
    ledger.flush()
    print("issue_latency_ms=", round(lat, 2), "verify:", ok, reason, "verify_latency_ms=", round(vlat, 2))
    print("chain length:", len(ledger.chain), "integrity_ok:", ledger.integrity_check())

    ctx = synthetic_legit_context(rng)
    print("legit decision:", zte.decide(ctx))
    ctx2 = synthetic_attack_context(rng, "spoof")
    print("attack decision:", zte.decide(ctx2))
