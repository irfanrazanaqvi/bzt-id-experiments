"""Fig. 2 (flow-lane version): issuance and per-request verification as two left-to-right lanes.
Step badges 1-15 match the protocol text of Section 5. Canvas width 1000 units = 7 in printed."""
import html, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "figures", "drawio")
FONT = "fontFamily=Helvetica;"
cells = []; n = [2]
def nid(): n[0] += 1; return f"c{n[0]}"
def vertex(x, y, w, h, value, style):
    i = nid(); cells.append(f'<mxCell id="{i}" value="{html.escape(value)}" style="{style}" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry"/></mxCell>'); return i
def node(cx, cy, w, h, actor, body, dashed=False, fill="#FFFFFF"):
    v = f'<span style="font-size:13px;letter-spacing:1px">{actor}</span><br><b style="font-size:16px">{body}</b>'
    st = f"rounded=1;arcSize=10;whiteSpace=wrap;html=1;{FONT}strokeWidth=2;strokeColor=#000000;fillColor={fill};verticalAlign=middle;spacing=3;" + ("dashed=1;dashPattern=6 4;" if dashed else "")
    return vertex(cx - w / 2, cy - h / 2, w, h, v, st)
def diamond(cx, cy, w, h, text):
    return vertex(cx - w / 2, cy - h / 2, w, h, f'<b style="font-size:16px">{text}</b>', f"rhombus;whiteSpace=wrap;html=1;{FONT}strokeWidth=2.5;strokeColor=#000000;fillColor=#D9D9D9;")
def text(x, y, w, h, t, fs=15, bold=False, italic=False, color="#000000", align="center", fill="none", rot=0):
    st = f"text;html=1;{FONT}fontSize={fs};fontStyle={(1 if bold else 0) + (2 if italic else 0)};fontColor={color};align={align};verticalAlign=middle;whiteSpace=wrap;fillColor={fill};" + (f"rotation={rot};" if rot else "")
    return vertex(x, y, w, h, t, st)
def badge(cx, cy, label):
    w = 22 if len(label) <= 2 else 34
    return vertex(cx - w / 2, cy - 11, w, 22, label, f"rounded=1;arcSize=50;html=1;{FONT}fontSize=14;fontStyle=1;fontColor=#FFFFFF;fillColor=#000000;strokeColor=#000000;align=center;verticalAlign=middle;")
def edge(pts, dashed=False, sw=2):
    st = f"endArrow=block;endFill=1;endSize=7;html=1;strokeWidth={sw};strokeColor=#000000;rounded=0;" + ("dashed=1;dashPattern=7 4;" if dashed else "")
    (x1, y1), (x2, y2) = pts[0], pts[-1]; mids = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in pts[1:-1])
    arr = f'<Array as="points">{mids}</Array>' if mids else ""
    i = nid(); cells.append(f'<mxCell id="{i}" value="" style="{st}" edge="1" parent="1"><mxGeometry relative="1" as="geometry"><mxPoint x="{x1}" y="{y1}" as="sourcePoint"/><mxPoint x="{x2}" y="{y2}" as="targetPoint"/>{arr}</mxGeometry></mxCell>')
W = 1000; SX = 0; SW = 54; BW, BH = 136, 86; DW, DH = 130, 100
CX = [148, 330, 508, 712, 900]
def lane(y0, title, steps):
    H = 272
    vertex(0, y0, W, H, "", "rounded=0;html=1;strokeColor=#000000;strokeWidth=1.5;fillColor=#F4F4F4;")
    vertex(0, y0, SW, H, "", "rounded=0;html=1;strokeColor=#1F1F1F;fillColor=#1F1F1F;")
    text(SW / 2 - H / 2, y0 + H / 2 - 18, H, 36, title, fs=17, bold=True, color="#FFFFFF", rot=-90)
    cy = y0 + 112; ret_y = y0 + 34; low_y = cy + 112
    a, b, c, d, e = steps["nodes"]
    node(CX[0], cy, BW, BH, *a); node(CX[1], cy, BW, BH, *b); diamond(CX[2], cy, DW, DH, c); node(CX[3], cy, BW, BH, *d); node(CX[4], cy, BW + 44, BH, *e)
    # forward arrows
    xs = [(CX[0] + BW / 2, CX[1] - BW / 2), (CX[1] + BW / 2, CX[2] - DW / 2), (CX[2] + DW / 2, CX[3] - BW / 2), (CX[3] + BW / 2, CX[4] - (BW + 44) / 2)]
    for (x1, x2), lab in zip(xs, steps["fwd"]):
        yy = cy - 12 if lab and lab[0] in "6" or (lab and lab.startswith("12")) else cy
        edge([(x1, yy), (x2, yy)])
        if lab: badge((x1 + x2) / 2, yy + (17 if x1 == CX[2] + DW / 2 else -15), lab)
    # ledger -> issuer/verifier return (lower parallel arrow)
    edge([(CX[4] - (BW + 44) / 2, cy + 14), (CX[3] + BW / 2, cy + 14)], dashed=True); badge((CX[3] + BW / 2 + CX[4] - (BW + 44) / 2) / 2, cy + 30, steps["ret_ledger"])
    # long returns above the lane boxes
    for (src, dst, lab, off) in steps["returns"]:
        yy = ret_y + off
        edge([(CX[src], cy - BH / 2), (CX[src], yy), (CX[dst] + 18 * (1 if dst < src else -1), yy), (CX[dst] + 18 * (1 if dst < src else -1), cy - BH / 2)], dashed=True)
        badge((CX[src] + CX[dst]) / 2, yy, lab)
    # decision branches below the diamond
    sx, dx = CX[2] - 130, CX[2] + 130
    node(sx, low_y, 232, 52, "STEP-UP", steps["stepup"], dashed=False, fill="#FFFFFF")
    node(dx, low_y, 232, 52, "DENY", steps["deny"], fill="#FFFFFF")
    edge([(CX[2] - 30, cy + DH / 2 - 15), (CX[2] - 30, low_y - 40), (sx + 30, low_y - 40), (sx + 30, low_y - 26)])
    edge([(sx - 30, low_y - 26), (sx - 30, low_y - 58), (CX[2] - 60, low_y - 58), (CX[2] - 60, cy + 12)], dashed=True) if False else None
    edge([(CX[2] + 30, cy + DH / 2 - 15), (CX[2] + 30, low_y - 40), (dx - 30, low_y - 40), (dx - 30, low_y - 26)])
    if steps["stepup_badge"]: badge(CX[2] - 30, low_y - 58, steps["stepup_badge"])
    text(CX[2] + DW / 2, cy - 30, CX[3] - BW / 2 - CX[2] - DW / 2, 20, "ALLOW", fs=13, bold=True)
    return y0 + H
y = lane(0, "A. Enrolment and issuance", {
    "nodes": [("WALLET", "Enrol: live capture, device attestation"), ("PEP", "Build request context x"), "Trust<br>engine T(x)", ("ISSUER", "Sign VC (BBS+), salted commitments"), ("LEDGER", "Endorse, order, commit ISSUE tx")],
    "fwd": ["1", "2", "3, 5", "6"], "ret_ledger": "7", "returns": [(3, 0, "8", 0)],
    "stepup": "OTP or re-capture", "stepup_badge": "4a-b", "deny": "Reject and log"})
y = lane(y + 14, "B. Per-request verification", {
    "nodes": [("WALLET", "Present claim or predicate (BBS+ proof)"), ("PEP", "Fresh context for this request"), "Re-score<br>T(x)", ("VERIFIER", "Check proof and status list bit"), ("LEDGER", "Status-list digest; pseudonymous audit")],
    "fwd": ["9", "10", "11", "12"], "ret_ledger": "13", "returns": [(3, 1, "14", 0), (1, 0, "15", 0)],
    "stepup": "OTP or re-capture", "stepup_badge": "", "deny": "Reject; pseudonymous log"})
# legend
ly = y + 12
edge([(10, ly + 10), (60, ly + 10)]); text(66, ly, 90, 20, "request", fs=14, align="left")
edge([(170, ly + 10), (220, ly + 10)], dashed=True); text(226, ly, 150, 20, "response / return", fs=14, align="left")
badge(400, ly + 10, "1"); text(416, ly, 330, 20, "protocol step (Section 5)", fs=14, align="left")
H = ly + 26
xml = f'<mxfile><diagram name="fig2"><mxGraphModel grid="0" page="1" pageWidth="{W}" pageHeight="{H}" background="#FFFFFF"><root><mxCell id="0"/><mxCell id="1" parent="0"/>{"".join(cells)}</root></mxGraphModel></diagram></mxfile>'
open(os.path.join(OUT, "fig2_flow.drawio"), "w").write(xml); print("height", H)
