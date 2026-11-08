"""Fig. 2: credential issuance and per-request zero-trust verification (academic style: serif, grayscale, no embedded title)."""
import os, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 8})
OUT = os.path.join(os.path.dirname(__file__), "..", "figures", "fig2_sequence.png")
INK = "#111111"
fig = plt.figure(figsize=(7.2, 8.3)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(-4, 111); ax.axis("off")
P = {"W": 11, "E": 30, "D": 50, "I": 70, "L": 90}
names = {"W": "Wallet\n(holder)", "E": "PEP\n(gateway)", "D": "Trust engine\n(PDP)", "I": "Issuer /\nverifier service", "L": "Consortium\nledger"}
top, bot = 105.5, -2.0
for k, x in P.items():
    ax.add_patch(FancyBboxPatch((x - 8.2, top - 0.2), 16.4, 5.4, boxstyle="round,pad=0,rounding_size=0.6", fc="#ececec", ec=INK, lw=0.9))
    ax.text(x, top + 2.5, names[k], ha="center", va="center", fontsize=8.2, fontweight="bold", linespacing=1.15)
    ax.plot([x, x], [top - 0.2, bot], color="#666666", lw=0.8, ls=(0, (4, 3)), zorder=0)
y = [top - 3.5]
def msg(a, b, n, text, ret=False, dy=5.1):
    y[0] -= dy
    yy = y[0]
    xa, xb = P[a], P[b]
    ax.add_patch(FancyArrowPatch((xa, yy), (xb, yy), arrowstyle="-|>", mutation_scale=8.5, lw=1.0, color=INK, ls=(0, (4, 2)) if ret else "-", shrinkA=0, shrinkB=0, zorder=3))
    mx = (xa + xb) / 2
    ax.text(mx, yy + 1.15, f"{n}  {text}", ha="center", va="bottom", fontsize=7.7, color=INK, bbox=dict(fc="white", ec="none", pad=0.6), zorder=4)
def frame(y0, y1, label, x0=2, x1=98, fill="none", lw=0.9, ls="-"):
    ax.add_patch(Rectangle((x0, y1), x1 - x0, y0 - y1, fc=fill, ec=INK, lw=lw, ls=ls, zorder=1))
    ax.add_patch(Rectangle((x0, y0 - 2.9), 15.5 if len(label) < 12 else 36, 2.9, fc="#d9d9d9", ec=INK, lw=0.8, zorder=2))
    ax.text(x0 + 0.8, y0 - 1.45, label, ha="left", va="center", fontsize=7.7, fontweight="bold", zorder=3)
# ---------------- Phase A
yA0 = y[0] - 1.6
y[0] -= 3.0
msg("W", "E", "1", "Enrolment request, biometric capture, attestation")
msg("E", "D", "2", "Request context x = (b, d, g, v, n, t)")
msg("D", "E", "3", "T(x) and decision: ALLOW / STEP-UP / DENY", ret=True)
yo0 = y[0] - 1.8
y[0] -= 3.2
msg("E", "W", "4a", "Challenge (OTP or supervised re-capture)", ret=True)
msg("W", "E", "4b", "Challenge response")
yo1 = y[0] - 2.2
msg("E", "I", "5", "[ALLOW] Issue request: claims, record ref., DID", dy=6.2)
msg("I", "L", "6", "ISSUE: hash commitment, DID pointer")
msg("L", "I", "7", "Endorsement, ordering, block commit; receipt", ret=True)
msg("I", "W", "8", "Signed verifiable credential (VC) and receipt", ret=True)
yA1 = y[0] - 2.4
frame(yA0, yA1, "A. Enrolment and issuance (steps 1-8)")
frame(yo0, yo1, "opt  STEP-UP", x0=4, x1=96, fill="none", lw=0.7, ls=(0, (3, 2)))
# ---------------- Phase B
y[0] = yA1 - 3.2
yB0 = y[0] + 1.0
y[0] -= 2.2
msg("W", "E", "9", "Present claim or predicate (selective disclosure)")
msg("E", "D", "10", "Re-capture context; re-score T(x) for this request")
msg("D", "I", "11", "[not DENY] Forward presentation for verification")
msg("I", "L", "12", "Query status: revocation, commitment match")
msg("L", "I", "13", "VALID / REVOKED / EXPIRED", ret=True)
msg("I", "E", "14", "Verification result", ret=True)
msg("E", "W", "15", "Access granted or denied", ret=True)
yB1 = y[0] - 2.4
frame(yB0, yB1, "B. Per-request verification (steps 9-15)")
# legend
ax.add_patch(Rectangle((0,-4),100,5.2,fc="white",ec="none",zorder=5))
ax.plot([4, 9], [yB1 - 3.4, yB1 - 3.4], color=INK, lw=1.0,zorder=6); ax.text(10, yB1 - 3.4, "request", va="center", fontsize=7.4, zorder=6)
ax.plot([24, 29], [yB1 - 3.4, yB1 - 3.4], color=INK, lw=1.0, ls=(0, (4, 2)), zorder=6); ax.text(30, yB1 - 3.4, "response / return", va="center", fontsize=7.4, zorder=6)
print("last y", yB1 - 3.4)
fig.savefig(OUT, dpi=300, facecolor="white"); print("wrote", OUT)
