"""Fig. 2: credential issuance and per-request zero-trust verification (serif, grayscale, no embedded title; text >= 9.5 pt at final width)."""
import os, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
plt.rcParams.update({"font.family": "STIXGeneral", "mathtext.fontset": "stix", "font.size": 10})
OUT = os.path.join(os.path.dirname(__file__), "..", "figures", "fig2_sequence.png")
INK = "#111111"; W_IN, H_IN = 7.2, 9.5; U = 100 / W_IN
fig = plt.figure(figsize=(W_IN, H_IN)); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, H_IN * U); ax.axis("off")
P = {"W": 11, "E": 30, "D": 50, "I": 70, "L": 89}
names = {"W": "Wallet\n(holder)", "E": "PEP\n(gateway)", "D": "Trust engine\n(PDP)", "I": "Issuer /\nverifier", "L": "Consortium\nledger"}
T = H_IN * U; top = T - 7.0; bot = 3.0
for k, x in P.items():
    ax.add_patch(FancyBboxPatch((x - 8.4, top), 16.8, 6.0, boxstyle="round,pad=0,rounding_size=0.6", fc="#ececec", ec=INK, lw=1.0))
    ax.text(x, top + 3.0, names[k], ha="center", va="center", fontsize=9.8, fontweight="bold", linespacing=1.15)
    ax.plot([x, x], [top, bot], color="#666666", lw=0.8, ls=(0, (4, 3)), zorder=0)
y = [top - 1.0]
def msg(a, b, n, text, ret=False, dy=6.0):
    y[0] -= dy; yy = y[0]; xa, xb = P[a], P[b]
    ax.add_patch(FancyArrowPatch((xa, yy), (xb, yy), arrowstyle="-|>", mutation_scale=10, lw=1.1, color=INK, ls=(0, (4, 2)) if ret else "-", shrinkA=0, shrinkB=0, zorder=3))
    ax.text((xa + xb) / 2, yy + 1.0, f"{n}  {text}", ha="center", va="bottom", fontsize=9.6, color=INK, bbox=dict(fc="white", ec="none", pad=0.5), zorder=4)
def frame(y0, y1, label, x0=2, x1=98, lw=1.0, ls="-", lw_label=None):
    ax.add_patch(Rectangle((x0, y1), x1 - x0, y0 - y1, fc="none", ec=INK, lw=lw, ls=ls, zorder=1))
    ax.add_patch(Rectangle((x0, y0 - 3.4), lw_label or 40, 3.4, fc="#d9d9d9", ec=INK, lw=0.8, zorder=2))
    ax.text(x0 + 0.8, y0 - 1.7, label, ha="left", va="center", fontsize=9.6, fontweight="bold", zorder=3)
# Phase A
yA0 = y[0] - 1.0; y[0] -= 3.6
msg("W", "E", "1", "Enrol request, biometric, attestation")
msg("E", "D", "2", "Request context x = (b, d, g, v, n, t)")
msg("D", "E", "3", "Decision: ALLOW / STEP-UP / DENY", ret=True)
yo0 = y[0] - 2.0; y[0] -= 3.8
msg("E", "W", "4a", "Challenge: OTP or re-capture", ret=True)
msg("W", "E", "4b", "Challenge response")
yo1 = y[0] - 2.6
msg("E", "I", "5", "[ALLOW] Issue request (claims, DID)", dy=7.0)
msg("I", "L", "6", "ISSUE: commitment, DID")
msg("L", "I", "7", "Endorse, order, commit; receipt", ret=True)
msg("I", "W", "8", "Signed VC and receipt", ret=True)
yA1 = y[0] - 3.0
frame(yA0, yA1, "A. Enrolment and issuance (steps 1-8)", lw_label=52)
frame(yo0, yo1, "opt  STEP-UP", x0=4, x1=96, lw=0.8, ls=(0, (3, 2)), lw_label=22)
# Phase B
y[0] = yA1 - 3.4; yB0 = y[0] + 1.0; y[0] -= 3.4
msg("W", "E", "9", "Present claim or predicate")
msg("E", "D", "10", "Re-score T(x) for this request")
msg("D", "I", "11", "[not DENY] Forward presentation")
msg("I", "L", "12", "Query status: revocation, commitment")
msg("L", "I", "13", "VALID / REVOKED / EXPIRED", ret=True)
msg("I", "E", "14", "Verification result", ret=True)
msg("E", "W", "15", "Access granted or denied", ret=True)
yB1 = y[0] - 3.0
frame(yB0, yB1, "B. Per-request verification (steps 9-15)", lw_label=52)
yl = yB1 - 4.2
ax.plot([4, 10], [yl, yl], color=INK, lw=1.1); ax.text(11, yl, "request", va="center", fontsize=9.6)
ax.plot([28, 34], [yl, yl], color=INK, lw=1.1, ls=(0, (4, 2))); ax.text(35, yl, "response / return", va="center", fontsize=9.6)
print("legend y", yl, "bot", bot)
fig.savefig(OUT, dpi=600, facecolor="white"); print("wrote", OUT)
