import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

OUT_FIG = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(OUT_FIG, exist_ok=True)

actors = ["Citizen\n(Wallet)", "PEP\n(Gateway)", "Zero-Trust\nEngine (PDP)", "VC Issuance /\nVerifier Service", "Consortium\nLedger (peers)"]
n = len(actors)
ROW_H = 0.62
N_MSGS_TOTAL = 9 + 7  # message blocks defined below
top = 1.0 + ROW_H * N_MSGS_TOTAL + 1.6
bottom = 0.5
fig, ax = plt.subplots(figsize=(11, top * 0.92), dpi=200)
xs = [1 + i * 2.35 for i in range(n)]

ax.set_xlim(0, xs[-1] + 1.4)
ax.set_ylim(bottom - 0.3, top + 0.6)
ax.axis("off")

for x, name in zip(xs, actors):
    b = FancyBboxPatch((x - 0.95, top - 0.55), 1.9, 0.55, boxstyle="round,pad=0.02",
                        linewidth=1.3, edgecolor="#1f4e79", facecolor="#eaf1fb")
    ax.add_patch(b)
    ax.text(x, top - 0.275, name, ha="center", va="center", fontsize=8.3, weight="bold")
    ax.plot([x, x], [top - 0.55, bottom - 0.2], color="#999999", linewidth=1, linestyle=(0, (4, 3)))

messages = [
    (0, 1, "1. Enrolment request + live biometric capture + device attestation"),
    (1, 2, "2. Forward request context (biometric score, device posture, geo, network)"),
    (2, 1, "3. Trust score T(x); decision {ALLOW / STEP-UP / DENY}"),
    (1, 0, "4a. [STEP-UP] challenge (OTP / secondary biometric)"),
    (0, 1, "4b. Step-up response"),
    (1, 3, "5. [ALLOW] Issue-credential call (claims, biometric hash, DID)"),
    (3, 4, "6. Submit ISSUE transaction (credential-hash commitment)"),
    (4, 3, "7. Byzantine-quorum endorsement + block commit ($\\geq\\lceil2N/3\\rceil$ peers); tx receipt"),
    (3, 0, "8. Signed Verifiable Credential (VC) returned to wallet"),
]

y = top - 1.05
step_h = ROW_H
for (src, dst, text) in messages:
    x1, x2 = xs[src], xs[dst]
    color = "#1e8449" if dst > src else "#943126"
    arr = FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=11,
                           color=color, linewidth=1.15)
    ax.add_patch(arr)
    mx = (x1 + x2) / 2
    ax.text(mx, y + 0.12, text, ha="center", va="bottom", fontsize=7.1)
    y -= step_h

# Post-issuance verification / relying-party flow (second phase)
ax.axhline(y + step_h * 0.35, color="#cccccc", linewidth=0.8, xmin=0.02, xmax=0.98)
ax.text(0.3, y + step_h * 0.55, "Later: relying-party verification (e-gate / KYC lookup)", fontsize=7.6,
         style="italic", color="#555555")

messages2 = [
    (0, 1, "9. Present VC (selective disclosure) for service access"),
    (1, 2, "10. Re-evaluate trust score for THIS request (continuous verification)"),
    (2, 3, "11. If ALLOW/STEP-UP passed: request on-chain status check"),
    (3, 4, "12. Query REVOKE/EXPIRY status + credential-hash match"),
    (4, 3, "13. Status = VALID/REVOKED/EXPIRED"),
    (3, 1, "14. Verification result"),
    (1, 0, "15. Access granted / denied"),
]
y -= step_h * 0.5
step_h2 = ROW_H
for (src, dst, text) in messages2:
    x1, x2 = xs[src], xs[dst]
    color = "#1e8449" if dst > src else "#943126"
    arr = FancyArrowPatch((x1, y), (x2, y), arrowstyle="-|>", mutation_scale=11,
                           color=color, linewidth=1.15)
    ax.add_patch(arr)
    mx = (x1 + x2) / 2
    ax.text(mx, y + 0.12, text, ha="center", va="bottom", fontsize=7.1)
    y -= step_h2

ax.text(xs[-1] / 2 + 0.7, top + 0.25, "Fig. 2. Credential issuance and continuous zero-trust verification protocol",
        ha="center", fontsize=10.5, weight="bold")

fig.tight_layout()
fig.savefig(os.path.join(OUT_FIG, "fig2_sequence.png"), bbox_inches="tight")
print("saved fig2_sequence.png")
