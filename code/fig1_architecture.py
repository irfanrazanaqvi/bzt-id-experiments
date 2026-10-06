import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT_FIG = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(OUT_FIG, exist_ok=True)

fig, ax = plt.subplots(figsize=(11, 7.2), dpi=200)
ax.set_xlim(0, 11)
ax.set_ylim(0, 7.2)
ax.axis("off")

def box(x, y, w, h, text, fc="#eaf1fb", ec="#1f4e79", fontsize=8.6, weight="normal"):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                        linewidth=1.3, edgecolor=ec, facecolor=fc)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize,
             weight=weight, wrap=True)
    return (x, y, w, h)

def arrow(p1, p2, text="", color="#333333", style="-|>", curve=0.0):
    a = FancyArrowPatch(p1, p2, arrowstyle=style, mutation_scale=12,
                         color=color, linewidth=1.1,
                         connectionstyle=f"arc3,rad={curve}")
    ax.add_patch(a)
    if text:
        mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
        ax.text(mx, my + 0.10, text, fontsize=6.6, ha="center", color=color)

# ---- Layer 1: Users / Devices ----
ax.text(0.15, 6.95, "Layer 1 — Subject & Device", fontsize=9, weight="bold", color="#1f4e79")
box(0.2, 6.05, 2.1, 0.7, "Citizen /\nOverseas applicant\n(mobile wallet)", fc="#fdf2e3", ec="#b9770e")
box(2.55, 6.05, 2.1, 0.7, "Front-line officer\n(NADRA / DGIP\nterminal)", fc="#fdf2e3", ec="#b9770e")
box(4.9, 6.05, 2.1, 0.7, "Relying-party service\n(bank / airline /\ne-gate)", fc="#fdf2e3", ec="#b9770e")
box(7.25, 6.05, 3.55, 0.7, "IoT/biometric capture: fingerprint,\niris, face liveness sensors", fc="#fdf2e3", ec="#b9770e")

# ---- Layer 2: Zero-Trust Policy Enforcement ----
ax.text(0.15, 5.55, "Layer 2 — Zero-Trust Policy Enforcement (PEP/PDP)", fontsize=9, weight="bold", color="#1f4e79")
box(0.2, 4.55, 3.35, 0.85, "Policy Enforcement Point (PEP)\nAPI gateway · mTLS · request context capture", fc="#eaf1fb")
box(3.75, 4.55, 3.35, 0.85, "Continuous Trust Engine (PDP)\nBiometric, device, geo-velocity,\nbehaviour, network, time-risk fusion", fc="#eaf1fb")
box(7.3, 4.55, 3.5, 0.85, "Policy Administrator\nRBAC/ABAC rules · step-up-auth\norchestration · SIEM feed", fc="#eaf1fb")

# ---- Layer 3: DID / VC identity layer ----
ax.text(0.15, 4.05, "Layer 3 — Decentralized Identity (DID / Verifiable Credential) Layer", fontsize=9, weight="bold", color="#1f4e79")
box(0.2, 3.05, 2.6, 0.85, "DID Registry\n(W3C DID Core)\nsubject ↔ public-key doc", fc="#eafaf1", ec="#1e8449")
box(3.0, 3.05, 2.9, 0.85, "VC Issuance Service\nCNIC / Passport / NICOP\ncredential templates", fc="#eafaf1", ec="#1e8449")
box(6.1, 3.05, 2.4, 0.85, "Selective-Disclosure\nVerifier (ZKP)\nage/citizenship proofs", fc="#eafaf1", ec="#1e8449")
box(8.7, 3.05, 2.1, 0.85, "Revocation\nRegistry\n(status list)", fc="#eafaf1", ec="#1e8449")

# ---- Layer 4: Permissioned blockchain ----
ax.text(0.15, 2.55, "Layer 4 — Permissioned Consortium Blockchain (Hyperledger-Fabric-style, PBFT)", fontsize=9, weight="bold", color="#1f4e79")
box(0.2, 1.15, 2.15, 1.15, "NADRA\nRegistrar peer\n+ CA/MSP", fc="#fdecea", ec="#943126")
box(2.5, 1.15, 2.15, 1.15, "DGIP Passport\nDirectorate peer\n+ CA/MSP", fc="#fdecea", ec="#943126")
box(4.8, 1.15, 2.15, 1.15, "Bank / Telecom\nKYC notary peer", fc="#fdecea", ec="#943126")
box(7.1, 1.15, 2.15, 1.15, "Independent\naudit / regulator\npeer (SBP/PTA)", fc="#fdecea", ec="#943126")
box(9.4, 1.15, 1.4, 1.15, "Ordering\nservice\n(Raft/PBFT)", fc="#fdecea", ec="#943126")

# ---- Off-chain encrypted store ----
box(0.2, 0.1, 4.1, 0.75, "Off-chain encrypted vault (IPFS/HSM)\nraw biometrics & PII — never written on-chain", fc="#f4ecf7", ec="#6c3483")
box(4.5, 0.1, 6.3, 0.75, "On-chain: only DID pointers, credential-hash commitments, issuance/verify/revoke events, audit trail (immutable)", fc="#f4ecf7", ec="#6c3483")

# ---- arrows ----
arrow((1.25, 6.05), (1.9, 5.4), "request + biometric capture")
arrow((3.6, 6.05), (4.5, 5.4))
arrow((6.0, 6.05), (5.4, 5.4))
arrow((5.4, 4.55), (5.4, 3.9), "trust score / decision")
arrow((4.4, 3.05), (2.0, 2.3), "issue tx")
arrow((7.3, 3.05), (7.9, 2.3), "verify tx")
arrow((8.9, 3.05), (8.9, 2.3), "revoke tx")
arrow((1.3, 1.15), (1.6, 0.85), "")
arrow((6.0, 1.15), (6.0, 0.85), "")

ax.text(5.5, 7.08, "Fig. 1. Layered architecture of the proposed BZT-ID system", ha="center",
        fontsize=10.5, weight="bold")

fig.tight_layout()
fig.savefig(os.path.join(OUT_FIG, "fig1_architecture.png"), bbox_inches="tight")
print("saved fig1_architecture.png")
