"""Fig. 1: layered BZT-ID architecture (serif, grayscale, no embedded title; body text >= 9.5 pt at final width).
Solid border = implemented in the evaluated prototype; dashed = specified only."""
import os, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 10})
OUT = os.path.join(os.path.dirname(__file__), "..", "figures", "fig1_architecture.png")
W_IN, H_IN = 7.2, 9.7; U = 100 / W_IN
fig = plt.figure(figsize=(W_IN, H_IN)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, H_IN * U); ax.axis("off")
INK = "#111111"; FS = 10; LH = 3.0
def box(x, y, w, h, text, dashed=False, fs=FS):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.8", fc="#ffffff", ec=INK, lw=1.1, ls=(0, (3, 2)) if dashed else "-"))
    lines = text.split("\n"); n = len(lines)
    for i, t in enumerate(lines):
        ax.text(x + w / 2, y + h / 2 + (n / 2 - i - 0.5) * LH, t, ha="center", va="center", fontsize=fs, color=INK, fontweight="bold" if i == 0 else "normal")
def band(y, h, num, name, fill):
    ax.add_patch(Rectangle((0.5, y), 99, h, fc=fill, ec="#777777", lw=0.7))
    ax.add_patch(Rectangle((0.5, y), 6.4, h, fc="#2b2b2b", ec="#2b2b2b"))
    ax.text(3.7, y + h / 2, f"Layer {num}\n{name}", rotation=90, ha="center", va="center", color="white", fontsize=9.5, fontweight="bold", linespacing=1.15)
def arrow(x0, y0, x1, y1, label=None, lx=1.4):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=11, lw=1.2, color=INK, shrinkA=0, shrinkB=0))
    if label: ax.text((x0 + x1) / 2 + lx, (y0 + y1) / 2, label, ha="left", va="center", fontsize=9.5, style="italic", color=INK)
T = H_IN * U  # 125
# legend
ax.add_patch(FancyBboxPatch((8.6, T - 5.2), 3.6, 2.4, boxstyle="round,pad=0,rounding_size=0.3", fc="white", ec=INK, lw=1.1)); ax.text(13.2, T - 4.0, "implemented in the evaluated prototype", va="center", fontsize=9.5)
ax.add_patch(FancyBboxPatch((8.6, T - 9.2), 3.6, 2.4, boxstyle="round,pad=0,rounding_size=0.3", fc="white", ec=INK, lw=1.1, ls=(0, (3, 2)))); ax.text(13.2, T - 8.0, "specified in the design, not built as an integrated service", va="center", fontsize=9.5)
x0, w, g = 8.6, 21.0, 1.9
# Layer 1
y1b, h1 = T - 28.2, 17.0
band(y1b, h1, 1, "Devices", "#f4f4f4")
for i, t in enumerate(["Citizen / holder\nwallet, local biometric\ncapture, DID keys", "Front-line officer\nNADRA / DGIP\nterminal", "Relying party\nbank, telecom,\nairline, e-gate", "Capture sensors\nfingerprint, iris,\nface (liveness)"]):
    box(x0 + i * (w + g), y1b + 1.6, w, h1 - 3.2, t)
# Layer 2
h2 = 23.0; y2b = y1b - 8.5 - h2
band(y2b, h2, 2, "Zero trust", "#e9e9e9")
by, bh = y2b + 1.6, h2 - 3.2
box(8.6, by, 26.6, bh, "Policy Enforcement\nPoint (PEP)\nAPI gateway,\nmutual TLS", dashed=True)
box(38.8, by, 29.2, bh, "Continuous Trust Engine\n(PDP)\n$T(x)=\\Sigma_k\\,w_k c_k(x)$\nbiometric, device, geo,\nbehaviour, network, time")
box(71.6, by, 27.6, bh, "Policy Administrator\nthresholds, step-up\n(OTP, re-capture)", dashed=True)
ym = by + bh / 2
arrow(35.2, ym + 2.5, 38.8, ym + 2.5); arrow(38.8, ym - 2.5, 35.2, ym - 2.5); arrow(71.6, ym, 68.0, ym)
# Layer 3
h3 = 17.0; y3b = y2b - 9.5 - h3
band(y3b, h3, 3, "DID / VC", "#f4f4f4")
for i, t in enumerate(["DID Registry\nW3C DID Core\nDID to key document", "VC Issuance\nCNIC / NICOP /\npassport templates", "Selective-disclosure\nverifier\nBBS+, ZK proofs", "Revocation registry\nstatus list\n(target design)"]):
    box(x0 + i * (w + g), y3b + 1.6, w, h3 - 3.2, t, dashed=True)
# Layer 4
h4 = 19.0; y4b = y3b - 9.5 - h4
band(y4b, h4, 4, "Ledger", "#e1e1e1")
bw, bg = 16.8, 1.5
for i, t in enumerate(["NADRA\nregistrar peer\nMSP / CA", "DGIP\npassport peer\nMSP / CA", "Notary peers\nbanks, telecoms\n(KYC)", "Audit peers\nregulators\n(SBP, PTA)", "Ordering service\nRaft (tested),\nSmartBFT (N ≥ 4)"]):
    box(8.6 + i * (bw + bg), y4b + 1.6, bw, h4 - 3.2, t, fs=9.6)
# inter-layer arrows
arrow(21.0, y1b + 1.6, 21.0, y2b + h2, "requests + biometric capture")
arrow(53.4, y2b, 53.4, y3b + h3, "ALLOW / STEP-UP / DENY gates credential operations")
arrow(53.4, y3b, 53.4, y4b + h4, "issue / verify / revoke transactions")
# data-minimisation row
yl = y4b - 4.2
ax.plot([0.5, 99.5], [yl, yl], color="#555555", lw=0.9, ls=(0, (4, 3)))
ax.text(50, yl + 2.0, "on-chain / off-chain data-minimization boundary", ha="center", va="center", fontsize=9.5, style="italic", color="#333333", bbox=dict(fc="white", ec="none", pad=0.5))
bh2 = 11.0; by2 = yl - 2.6 - bh2
box(0.5, by2, 47, bh2, "Off-chain encrypted vault (HSM-backed)\nraw biometrics and PII; never on-chain", dashed=True, fs=9.8)
box(52.5, by2, 47, bh2, "On-chain ledger state\nDID pointers, claim commitments, lifecycle events", fs=9.8)
arrow(88, y4b, 88, by2 + bh2)
print("bottom box y", by2, "band4 bottom", y4b)
fig.savefig(OUT, dpi=600, facecolor="white"); print("wrote", OUT)
