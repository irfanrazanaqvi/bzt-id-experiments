"""Graphical abstract (Elsevier: landscape, at least 1328 x 531 px; readable at 5 x 13 cm)."""
import os, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix"})
OUT = os.path.join(os.path.dirname(__file__), "..", "figures", "graphical_abstract")
fig = plt.figure(figsize=(13.28, 5.31)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 132.8); ax.set_ylim(0, 53.1); ax.axis("off")
INK, BLUE, LB, GR = "#111111", "#0b4f8a", "#e6eef7", "#f2f2f2"
def box(x, y, w, h, fc, ec=INK, lw=1.4, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=ec, lw=lw, ls=ls))
def arrow(x0, x1, y):
    ax.add_patch(FancyArrowPatch((x0, y), (x1, y), arrowstyle="-|>", mutation_scale=28, lw=2.2, color=BLUE))
# panel titles
for x, t in [(2, "Problem"), (42, "BZT-ID architecture"), (88, "Evidence (measured)")]:
    ax.text(x, 49.5, t, fontsize=19, fontweight="bold", color=BLUE, va="center")
# problem panel
box(2, 7, 32, 38, GR)
ax.text(18, 38.5, "Centralized CNIC /\npassport database", ha="center", va="center", fontsize=17, fontweight="bold", linespacing=1.2)
for i, t in enumerate(["single point of compromise", "no external audit trail", "trust ends at login", "full record shared with\nbanks, telecoms, airlines"]):
    ax.text(4.5, 31 - i * 5.3, "• " + t, fontsize=14.5, va="top", linespacing=1.15)
arrow(34.5, 40.5, 26)
# architecture panel: four layers
layers = [("Wallet and relying parties", "selective disclosure (BBS+)"), ("Zero-trust policy engine", "re-scores every request"),
          ("DID / verifiable credentials", "commitments only, no biometrics"), ("Permissioned Fabric ledger", "Raft or SmartBFT ordering")]
for i, (a, b) in enumerate(layers):
    y = 37 - i * 9.6
    box(41, y, 40, 8.2, LB if i % 2 == 0 else "white", ec=BLUE, lw=1.6)
    ax.text(61, y + 5.4, a, ha="center", va="center", fontsize=15.5, fontweight="bold")
    ax.text(61, y + 2.3, b, ha="center", va="center", fontsize=13.5, style="italic")
arrow(81.5, 87.5, 26)
# evidence panel
box(88, 7, 43, 38, "white", ec=INK)
items = [("~238 tx/s", "peak writes, Raft and tuned SmartBFT (one host)"), ("0.10 s / 0.17-0.21 s", "end-to-end issuance / verification"),
         ("1 of 4 down: OK", "2 of 4 down: halts safely (crash faults)"), ("AUC 0.98, but", "biometric floor + learned weights needed")]
for i, (a, b) in enumerate(items):
    y = 40.5 - i * 8.6
    ax.text(90.5, y, a, fontsize=16.5, fontweight="bold", color=BLUE, va="top")
    ax.text(90.5, y - 3.6, b, fontsize=13.5, va="top")
fig.savefig(OUT + ".png", dpi=300, facecolor="white"); fig.savefig(OUT + ".pdf", facecolor="white"); print("ok")
