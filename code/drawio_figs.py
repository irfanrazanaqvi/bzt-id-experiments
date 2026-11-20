"""Generate draw.io sources for Fig. 1 (architecture) and Fig. 2 (sequence) at journal width.
Canvas width 1000 units = 7 in printed, so fontSize 20 = 10 pt, 17 = 8.6 pt."""
import html, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "drawio")
FONT = "fontFamily=Helvetica;"
class G:
    def __init__(s): s.c = []; s.n = 2
    def id(s): s.n += 1; return f"c{s.n}"
    def box(s, x, y, w, h, title, body="", dashed=False, fill="#FFFFFF", fs=20, bs=17, align="center", stroke=2):
        v = f'<b style="font-size:{fs}px">{html.escape(title)}</b>' + (f'<br><span style="font-size:{bs}px">{body}</span>' if body else "")
        st = f"rounded=1;arcSize=6;whiteSpace=wrap;html=1;{FONT}strokeColor=#000000;strokeWidth={stroke};fillColor={fill};align={align};verticalAlign=middle;spacing=4;" + ("dashed=1;dashPattern=6 4;" if dashed else "")
        i = s.id(); s.c.append(f'<mxCell id="{i}" value="{html.escape(v)}" style="{st}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'); return i
    def rect(s, x, y, w, h, fill, stroke="#000000", sw=1.5, dashed=False):
        st = f"rounded=0;html=1;strokeColor={stroke};strokeWidth={sw};fillColor={fill};" + ("dashed=1;" if dashed else "")
        i = s.id(); s.c.append(f'<mxCell id="{i}" value="" style="{st}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'); return i
    def text(s, x, y, w, h, t, fs=17, bold=False, italic=False, align="center", color="#000000", rot=0, fill="none"):
        fsty = (1 if bold else 0) + (2 if italic else 0)
        st = f"text;html=1;{FONT}fontSize={fs};fontStyle={fsty};align={align};verticalAlign=middle;fontColor={color};whiteSpace=wrap;fillColor={fill};" + (f"rotation={rot};" if rot else "")
        i = s.id(); s.c.append(f'<mxCell id="{i}" value="{html.escape(t)}" style="{st}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'); return i
    def line(s, x1, y1, x2, y2, dashed=False, arrow=True, sw=2, label="", fs=17, lab_dx=0, lab_dy=-14, italic=False, color="#000000"):
        st = f"endArrow={'block' if arrow else 'none'};endFill=1;endSize=7;html=1;strokeColor={color};strokeWidth={sw};" + ("dashed=1;dashPattern=7 4;" if dashed else "")
        i = s.id(); s.c.append(f'<mxCell id="{i}" value="" style="{st}" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/><mxPoint x="{x2}" y="{y2}" as="targetPoint"/></mxGeometry></mxCell>')
        if label:
            w = 460; s.text((x1 + x2) / 2 - w / 2 + lab_dx, min(y1, y2) + lab_dy - 11, w, 22, label, fs=fs, italic=italic)
    def save(s, name, W, H):
        xml = f'<mxfile><diagram name="{name}"><mxGraphModel dx="{W}" dy="{H}" grid="0" page="1" pageWidth="{W}" pageHeight="{H}" background="#FFFFFF"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{"".join(s.c)}</root></mxGraphModel></diagram></mxfile>'
        open(os.path.join(OUT, name + ".drawio"), "w").write(xml)

# ---------------------------------------------------------------- Fig. 1 architecture
g = G(); W = 1000; LX = 0; LW = 92; BX = 100; BW = W - BX
def band(y, h, label):
    g.rect(LX, y, W, h, "#F2F2F2"); g.rect(LX, y, LW, h, "#262626", stroke="#262626")
    g.text(LX, y, LW, h, label, fs=17, bold=True, color="#FFFFFF")
def row(y, h, items, x0=BX + 8, x1=W - 8, gap=10):
    n = len(items); w = (x1 - x0 - gap * (n - 1)) / n
    return [g.box(x0 + k * (w + gap), y, w, h, t, b, dashed=d) for k, (t, b, d) in enumerate(items)]
# legend
g.rect(560, 4, 34, 18, "#FFFFFF", sw=2); g.text(600, 0, 160, 26, "implemented", fs=16, align="left")
g.rect(735, 4, 34, 18, "#FFFFFF", sw=2, dashed=True); g.text(775, 0, 225, 26, "specified, not built", fs=16, align="left")
y = 32; H1 = 82
band(y, H1, "Layer 1<br>Devices"); row(y + 8, H1 - 16, [("Citizen / holder", "wallet, DID keys", True), ("Front-line officer", "NADRA / DGIP terminal", False), ("Relying party", "bank, telecom, e-gate", False), ("Capture sensors", "fingerprint, iris, face", False)])
g.line(500, y + H1, 500, y + H1 + 34, label="requests + biometric capture", italic=True, lab_dx=250, lab_dy=17)
y += H1 + 34; H2 = 104
band(y, H2, "Layer 2<br>Zero trust")
x0 = BX + 8; ws = [250, 320, 250]; gap = (W - 8 - x0 - sum(ws)) / 2; xs = [x0, x0 + ws[0] + gap, x0 + ws[0] + ws[1] + 2 * gap]
g.box(xs[0], y + 8, ws[0], H2 - 16, "Policy Enforcement Point", "API gateway, mutual TLS", dashed=True, fs=19, bs=16)
g.box(xs[1], y + 8, ws[1], H2 - 16, "Continuous Trust Engine (PDP)", "T(x) = Σ<sub>k</sub> w<sub>k</sub>c<sub>k</sub>(x)<br>biometric, device, geo,<br>behaviour, network, time", fs=19, bs=16)
g.box(xs[2], y + 8, ws[2], H2 - 16, "Policy Administrator", "thresholds, step-up<br>(OTP, re-capture)", dashed=True, fs=19, bs=16)
g.line(xs[0] + ws[0], y + 42, xs[1], y + 42); g.line(xs[1], y + 62, xs[0] + ws[0], y + 62); g.line(xs[2], y + 52, xs[1] + ws[1], y + 52)
g.line(500, y + H2, 500, y + H2 + 34, label="ALLOW / STEP-UP / DENY gates credential operations", italic=True, lab_dx=250, lab_dy=17)
y += H2 + 34
band(y, H1, "Layer 3<br>DID / VC"); row(y + 8, H1 - 16, [("DID Registry", "W3C DID Core", True), ("VC Issuance", "BBS+ credentials", False), ("Selective disclosure", "BBS+ and ZK proofs", False), ("Revocation registry", "bitstring status list", False)])
g.line(500, y + H1, 500, y + H1 + 34, label="issue / verify / revoke transactions", italic=True, lab_dx=250, lab_dy=17)
y += H1 + 34
band(y, H1, "Layer 4<br>Ledger"); row(y + 8, H1 - 16, [("NADRA", "registrar peer", False), ("DGIP", "passport peer", True), ("Notary peers", "banks, telecoms", True), ("Audit peers", "regulators", True), ("Ordering", "Raft / SmartBFT", False)], gap=8)
y += H1
g.line(0, y + 22, W, y + 22, arrow=False, dashed=True, sw=1.5); g.text(270, y + 12, 460, 20, "on-chain / off-chain data-minimization boundary", fs=16, italic=True, fill="#FFFFFF")
y += 34
g.box(0, y, 480, 58, "Off-chain encrypted vault (HSM-backed)", "raw biometrics and PII; never on-chain", dashed=True)
g.box(520, y, 480, 58, "On-chain ledger state", "DID pointers, claim commitments, lifecycle events")
g.save("fig1_architecture", W, y + 60)
print("fig1 height", y + 60)

# ---------------------------------------------------------------- Fig. 2 sequence
g = G(); W = 1000
lanes = ["Wallet (holder)", "PEP (gateway)", "Trust engine (PDP)", "Issuer / verifier", "Consortium ledger"]
LXs = [100, 300, 500, 700, 900]
for x, n in zip(LXs, lanes): g.box(x - 95, 0, 190, 44, n, fill="#E6E6E6", fs=18)
RH = 32; y0 = 56
msgs = [("A", "A. Enrolment and issuance (steps 1-8)"), (0, 1, "1  Enrol request, biometric, attestation", False), (1, 2, "2  Request context x = (b, d, g, v, n, t)", False),
        (2, 1, "3  ALLOW / STEP-UP / DENY", True), ("O", "opt  STEP-UP"), (1, 0, "4a  Challenge: OTP or re-capture", True), (0, 1, "4b  Challenge response", False), ("/O", ""),
        (1, 3, "5  [ALLOW] Issue request (claims, DID)", False), (3, 4, "6  ISSUE: commitment, DID", False), (4, 3, "7  Endorse, order, commit; receipt", True),
        (3, 0, "8  Signed VC and receipt", True), ("/A", ""), ("B", "B. Per-request verification (steps 9-15)"), (0, 1, "9  Present claim or predicate", False),
        (1, 2, "10  Re-score T(x) for this request", False), (2, 3, "11  [not DENY] Forward presentation", False), (3, 4, "12  Query status list, commitment", False),
        (4, 3, "13  VALID / REVOKED / EXPIRED", True), (3, 1, "14  Verification result", True), (1, 0, "15  Access granted or denied", True), ("/B", "")]
y = y0; stack = {}
for m in msgs:
    if m[0] in ("A", "B"):
        stack[m[0]] = y; y += 34; continue
    if m[0] == "O": y += 12; stack["O"] = y; y += 26; continue
    if m[0] == "/O":
        top = stack["O"]; g.rect(30, top, 610, y - top + 4, "none", dashed=True, sw=1.5); g.rect(30, top, 130, 24, "#E6E6E6", sw=1.5); g.text(30, top, 130, 24, "opt  STEP-UP", fs=16, bold=True); y += 10; continue
    if m[0] in ("/A", "/B"):
        k = m[0][1]; top = stack[k]; g.rect(8, top, W - 16, y - top + 6, "none", sw=1.5)
        lab = "A. Enrolment and issuance (steps 1-8)" if k == "A" else "B. Per-request verification (steps 9-15)"
        g.rect(8, top, 400, 26, "#D9D9D9", sw=1.5); g.text(14, top, 400, 26, lab, fs=17, bold=True, align="left"); y += 22; continue
    a, b, t, ret = m; y += RH
    g.line(LXs[a], y, LXs[b], y, dashed=ret)
    tw = len(t) * 9.6 + 16; g.text((LXs[a] + LXs[b]) / 2 - tw / 2, y - 26, tw, 20, t, fs=17, fill="#FFFFFF")
H = y + 30
for x in LXs: g.line(x, 44, x, H - 26, arrow=False, dashed=True, sw=1, color="#808080")
g.line(20, H - 10, 80, H - 10, arrow=True); g.text(88, H - 21, 120, 22, "request", fs=16, align="left")
g.line(240, H - 10, 300, H - 10, arrow=True, dashed=True); g.text(308, H - 21, 200, 22, "response / return", fs=16, align="left")
# send lifelines to back: move the last 5 lifeline cells before others
cells = g.c; life = [c for c in cells if 'strokeColor=#808080' in c]; rest = [c for c in cells if c not in life]; g.c = life + rest
g.save("fig2_sequence", W, H + 2)
print("fig2 height", H)
