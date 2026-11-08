"""Fig. 1: layered BZT-ID architecture (academic style: serif, grayscale, no embedded title).
Solid border = implemented in the evaluated prototype (chaincode/ledger, trust-engine model); dashed = specified only."""
import os, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 8})
OUT = os.path.join(os.path.dirname(__file__), "..", "figures", "fig1_architecture.png")
fig = plt.figure(figsize=(7.2, 6.55)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 91); ax.axis("off")
INK = "#111111"
def box(x, y, w, h, text, fill="#ffffff", dashed=False, fs=7.6, bold_first=True):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", fc=fill, ec=INK, lw=0.9, ls=(0, (3, 2)) if dashed else "-"))
    lines = text.split("\n")
    n = len(lines); lh = 2.45
    for i, t in enumerate(lines):
        ax.text(x + w / 2, y + h / 2 + (n / 2 - i - 0.5) * lh, t, ha="center", va="center", fontsize=fs, color=INK,
                fontweight="bold" if (i == 0 and bold_first) else "normal")
def band(y, h, num, name, fill):
    ax.add_patch(Rectangle((0.5, y), 99, h, fc=fill, ec="#777777", lw=0.6))
    ax.add_patch(Rectangle((0.5, y), 6.2, h, fc="#2b2b2b", ec="#2b2b2b"))
    ax.text(3.6, y + h / 2, f"Layer {num}\n{name}", rotation=90, ha="center", va="center", color="white", fontsize=7.2, fontweight="bold", linespacing=1.15)
def arrow(x0, y0, x1, y1, label=None, lx=1.2, ha="left", ls="-", fs=7.2):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=9, lw=1.0, color=INK, ls=ls, shrinkA=0, shrinkB=0))
    if label: ax.text((x0 + x1) / 2 + lx, (y0 + y1) / 2, label, ha=ha, va="center", fontsize=fs, style="italic", color=INK)
# ---- bands
band(71.5, 15, 1, "Subject/device", "#f4f4f4")
band(52.5, 15, 2, "Zero trust", "#e9e9e9")
band(33.5, 15, 3, "DID / VC", "#f4f4f4")
band(12.5, 17.5, 4, "Ledger", "#e1e1e1")
# Layer 1
x0, w, g = 8.6, 21.3, 1.9
for i, t in enumerate(["Citizen / overseas holder\nmobile wallet, local biometric\ncapture, DID keys",
                       "Front-line officer\nNADRA / DGIP terminal",
                       "Relying party\nbank, telecom, airline,\ne-gate",
                       "Capture sensors\nfingerprint, iris, face\n(liveness)"]):
    box(x0 + i * (w + g), 73.2, w, 11.6, t, "#ffffff")
# Layer 2
box(8.6, 54.2, 27, 11.6, "Policy Enforcement Point\nAPI gateway, mutual TLS,\nrequest-context capture", "#ffffff", dashed=True)
box(39.1, 54.2, 28.6, 11.6, "Continuous Trust Engine (PDP)\n$T(x)=\\Sigma_k\\,w_k c_k(x)$, six factors:\nbiometric, device, geo, behaviour,\nnetwork, time", "#ffffff")
box(71.2, 54.2, 28, 11.6, "Policy Administrator\nthresholds, step-up\norchestration (OTP, re-capture)", "#ffffff", dashed=True)
arrow(35.6, 61.2, 39.1, 61.2); arrow(39.1, 58.0, 35.6, 58.0); arrow(71.2, 59.6, 67.7, 59.6)
# Layer 3
for i, t in enumerate(["DID Registry\nW3C DID Core\nDID to public-key document", "VC Issuance Service\nCNIC / NICOP / passport\ncredential templates",
                       "Selective-Disclosure Verifier\nBBS+ / zero-knowledge\npredicate proofs", "Revocation Registry\nbitstring status list\n(target design)"]):
    box(x0 + i * (w + g), 35.2, w, 11.6, t, "#ffffff", dashed=True)
# Layer 4
bw, bg = 17.0, 1.55
for i, (t, d) in enumerate([("NADRA\nregistrar peer\nMSP / CA", False), ("DGIP\npassport peer\nMSP / CA", False), ("Notary peers\nbanks, telecoms\n(KYC)", False),
                            ("Audit peers\nregulators\n(e.g. SBP, PTA)", False), ("Ordering service\nRaft (tested), SmartBFT\n(N ≥ 4)", False)]):
    box(8.6 + i * (bw + bg), 14.2, bw, 14.2, t, "#ffffff")
# ---- inter-layer arrows
arrow(21.0, 73.2, 21.0, 65.8, "requests + biometric capture", lx=1.0)
arrow(54.05, 54.2, 54.05, 46.8, "ALLOW / STEP-UP / DENY gates credential operations", lx=1.0)
arrow(54.05, 35.2, 54.05, 28.4, "issue / verify / revoke transactions", lx=1.0)
# ---- data minimisation row
ax.plot([0.5, 99.5], [10.4, 10.4], color="#555555", lw=0.8, ls=(0, (4, 3)))
ax.text(50, 11.35, "on-chain / off-chain data-minimization boundary", ha="center", va="center", fontsize=7.2, style="italic", color="#333333")
box(0.5, 0.8, 47, 8.2, "Off-chain encrypted vault (HSM-backed)\nraw biometrics and PII; never written on-chain", "#ffffff", dashed=True)
box(52.5, 0.8, 47, 8.2, "On-chain ledger state\nDID pointers, salted claim commitments, lifecycle events", "#ffffff")
arrow(76, 12.5, 76, 9.0)
# legend
ax.add_patch(FancyBboxPatch((8.6, 88.4), 3.2, 1.8, boxstyle="round,pad=0,rounding_size=0.3", fc="white", ec=INK, lw=0.9))
ax.text(12.6, 89.3, "implemented in the evaluated prototype", va="center", fontsize=7.2)
ax.add_patch(FancyBboxPatch((46.5, 88.4), 3.2, 1.8, boxstyle="round,pad=0,rounding_size=0.3", fc="white", ec=INK, lw=0.9, ls=(0, (3, 2))))
ax.text(50.5, 89.3, "specified in the design, not built as an integrated service", va="center", fontsize=7.2)
fig.savefig(OUT, dpi=300, facecolor="white"); print("wrote", OUT)
