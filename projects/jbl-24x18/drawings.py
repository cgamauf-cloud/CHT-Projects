#!/usr/bin/env python3
"""
Render the drawing set (HTML with inline SVG sheets) from out/design.json.

Every line on every sheet is drawn from the design.json coordinates - the same
numbers the calculations used - so plan, ceiling plan, elevations, section and
schedules cannot disagree. SVG sheets are 17 x 11 in (viewBox units = 0.01 in)
and drawn at true architectural scale when printed on 11x17 (ANSI B) paper.

Run: python3 -I drawings.py   (after design.py)
"""
import html
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "out", "design.json")))
IN = 0.0254
FT = 0.3048
W, L, H = D["room"]["W"], D["room"]["L"], D["room"]["H"]
WALL = 0.165  # 2x6 stud + 5/8 in drywall, drawn wall thickness (assumed)


def ftin(m, frac=4):
    neg = m < 0
    tot = round(abs(m) / IN * frac) / frac
    ft = int(tot // 12)
    inch = tot - ft * 12
    whole = int(inch)
    f = inch - whole
    fs = ""
    if f > 1e-9:
        n, d = round(f * frac), frac
        while n % 2 == 0 and d > 1:
            n //= 2
            d //= 2
        fs = f" {n}/{d}"
    return ("-" if neg else "") + f"{ft}'-{whole}{fs}\""


def e(s):
    return html.escape(str(s), quote=True)


def scale_units(arch_in_per_ft):
    """paper units (0.01 in) per metre at a given architectural scale (in per ft)."""
    return arch_in_per_ft / FT * 100


class Sheet:
    def __init__(self, number, title, scale_label):
        self.number, self.title, self.scale_label = number, title, scale_label
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    # primitives -------------------------------------------------------
    def line(self, x1, y1, x2, y2, cls="ln"):
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}"/>')

    def rect(self, x, y, w, h, cls="ln"):
        if w < 0:
            x, w = x + w, -w
        if h < 0:
            y, h = y + h, -h
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" class="{cls}"/>')

    def text(self, x, y, s, cls="t", anchor="middle", rot=None, size=None):
        tr = f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ""
        sz = f' style="font-size:{size}px"' if size else ""
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}"{tr}{sz}>{e(s)}</text>')

    def circle(self, x, y, r, cls="ln"):
        self.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" class="{cls}"/>')

    def path(self, d, cls="ln"):
        self.add(f'<path d="{d}" class="{cls}"/>')

    def tag(self, x, y, label, cls="tag"):
        w = 13 + 9 * len(label)
        self.add(f'<rect x="{x - w/2:.1f}" y="{y - 11:.1f}" width="{w:.1f}" height="22" rx="11" class="{cls}"/>')
        self.text(x, y + 5, label, "tagt")

    def dim(self, x1, y1, x2, y2, off, label=None, cls="dim"):
        """Aligned dimension between (x1,y1)-(x2,y2), offset perpendicular by off (paper units)."""
        dx, dy = x2 - x1, y2 - y1
        ln = math.hypot(dx, dy)
        if ln < 1e-6:
            return
        nx, ny = -dy / ln, dx / ln
        a1 = (x1 + nx * off, y1 + ny * off)
        a2 = (x2 + nx * off, y2 + ny * off)
        ext = 6 if off > 0 else -6
        self.line(x1 + nx * (3 if off > 0 else -3), y1 + ny * (3 if off > 0 else -3), a1[0] + nx * ext, a1[1] + ny * ext, "ext")
        self.line(x2 + nx * (3 if off > 0 else -3), y2 + ny * (3 if off > 0 else -3), a2[0] + nx * ext, a2[1] + ny * ext, "ext")
        self.line(a1[0], a1[1], a2[0], a2[1], cls)
        ux, uy = dx / ln, dy / ln
        for (px, py) in (a1, a2):  # architectural slash ticks
            self.line(px - (ux + nx) * 5, py - (uy + ny) * 5, px + (ux + nx) * 5, py + (uy + ny) * 5, "tick")
        mx, my = (a1[0] + a2[0]) / 2, (a1[1] + a2[1]) / 2
        ang = math.degrees(math.atan2(dy, dx))
        if ang >= 90 or ang < -90:
            ang -= 180
        lx = mx + math.sin(math.radians(ang)) * 8
        ly = my - math.cos(math.radians(ang)) * 8
        if label:
            self.text(lx, ly, label, "dimt", rot=ang if abs(ang) > 0.1 else None)

    # sheet wrapper ----------------------------------------------------
    def svg(self):
        p = D["inputs"]
        tb = []
        tb.append('<rect x="25" y="25" width="1650" height="1050" class="frame"/>')
        tb.append('<rect x="35" y="35" width="1630" height="1030" class="frame2"/>')
        x0 = 1400
        tb.append(f'<line x1="{x0}" y1="35" x2="{x0}" y2="1065" class="frame2"/>')
        tb.append(f'<text x="{x0+132}" y="98" class="brand" text-anchor="middle">CHT</text>')
        tb.append(f'<text x="{x0+132}" y="122" class="tbs" text-anchor="middle">CUSTOM HOME THEATER DESIGN</text>')
        rows = [("PROJECT", p["project"].replace("CHT Theater Concept: ", "")), ("PROJECT NO.", p["project_no"]),
                ("ROOM", f"{p['room']['length_ft']}'-0\" L x {p['room']['width_ft']}'-0\" W x {p['room']['height_ft']}'-0\" H"),
                ("FORMAT", f"Dolby Atmos {D['layout']} / {D['system']['sub_units']} subwoofers"),
                ("REVISION", p["revision"]), ("DATE", p["date"]), ("DRAWN", "CHT design engine v0.1"),
                ("SCALE", self.scale_label)]
        y = 160
        for k, v in rows:
            tb.append(f'<line x1="{x0}" y1="{y-22}" x2="1665" y2="{y-22}" class="frame3"/>')
            tb.append(f'<text x="{x0+12}" y="{y-6}" class="tbk">{e(k)}</text>')
            tb.append(f'<text x="{x0+12}" y="{y+14}" class="tbv">{e(v)}</text>')
            y += 52
        tb.append(f'<line x1="{x0}" y1="{y-22}" x2="1665" y2="{y-22}" class="frame3"/>')
        tb.append(f'<rect x="{x0+14}" y="{y}" width="237" height="70" class="stamp"/>')
        tb.append(f'<text x="{x0+132}" y="{y+30}" class="stampt" text-anchor="middle">CONCEPT DESIGN</text>')
        tb.append(f'<text x="{x0+132}" y="{y+54}" class="stampt2" text-anchor="middle">NOT FOR CONSTRUCTION</text>')
        tb.append(f'<line x1="{x0}" y1="900" x2="1665" y2="900" class="frame2"/>')
        tb.append(f'<text x="{x0+12}" y="925" class="tbk">SHEET TITLE</text>')
        words, line_, lines = self.title.split(), "", []
        for w_ in words:
            if len(line_ + " " + w_) > 19:
                lines.append(line_)
                line_ = w_
            else:
                line_ = (line_ + " " + w_).strip()
        lines.append(line_)
        for i, t in enumerate(lines[:2]):
            tb.append(f'<text x="{x0+12}" y="{952 + i*24}" class="tbtitle">{e(t)}</text>')
        tb.append(f'<text x="1652" y="1050" class="sheetno" text-anchor="end">{e(self.number)}</text>')
        body = "\n".join(self.parts)
        return (f'<svg viewBox="0 0 1700 1100" xmlns="http://www.w3.org/2000/svg" role="img" '
                f'aria-label="{e(self.number + " " + self.title)}">'
                f'<defs><pattern id="hatch" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                f'<line x1="0" y1="0" x2="0" y2="10" class="hatchln"/></pattern>'
                f'<pattern id="dots" width="9" height="9" patternUnits="userSpaceOnUse">'
                f'<circle cx="2" cy="2" r="1.1" class="dotfill"/></pattern></defs>'
                f'<rect x="0" y="0" width="1700" height="1100" class="paper"/>'
                f'{"".join(tb)}{body}</svg>')


# ----------------------------------------------------------------------------
CH = {c["ch"]: c for c in D["channels"]}
SE = D["seating"]
SC = D["screen"]
PJ = D["projector"]
SUB = next(o for o in D["subs"]["options"] if o["name"] == D["subs"]["chosen"])
TZ = D["treatment_zones"]
CAT = D["catalog"]
SUBM = D["subs"]["model"]
PKG = D["package"]
OPT = D["options"]
SEAT_W, SEAT_FRONT, SEAT_BACK, FOOT = 0.80, D["inputs"]["seating"]["seat_front"], D["inputs"]["seating"]["seat_back"], D["inputs"]["seating"]["footrest"]


def plan_sheet(number, title, rcp=False):
    s = scale_units(3 / 8)
    ox, oy = 175, 128
    X = lambda x: ox + x * s
    Y = lambda y: oy + y * s
    sh = Sheet(number, title, '3/8" = 1\'-0" (on 11x17)')
    t = WALL * s
    # walls (poche)
    sh.rect(X(0) - t, Y(0) - t, W * s + 2 * t, t, "wall")
    sh.rect(X(0) - t, Y(L), W * s + 2 * t, t, "wall")
    sh.rect(X(0) - t, Y(0), t, L * s, "wall")
    sh.rect(X(W), Y(0), t, L * s, "wall")
    sh.rect(X(0), Y(0), W * s, L * s, "ln")
    door = D["inputs"]["door"]
    dx0, dw = door["x0"], door["width"]
    sh.rect(X(dx0), Y(L) - 1, dw * s, t + 2, "paperfill")
    sh.line(X(dx0), Y(L), X(dx0), Y(L) + t, "ln")
    sh.line(X(dx0 + dw), Y(L), X(dx0 + dw), Y(L) + t, "ln")
    if not rcp:
        sh.line(X(dx0 + dw), Y(L), X(dx0 + dw), Y(L) - dw * s, "ln")
        sh.path(f"M {X(dx0):.1f} {Y(L):.1f} A {dw*s:.1f} {dw*s:.1f} 0 0 1 {X(dx0+dw):.1f} {Y(L)-dw*s:.1f}", "thin")
        sh.text(X(dx0) - 6, Y(L) - 30, "36\" SEALED DOOR", "tiny", anchor="end")
    sh.text(X(W) + t + 10, Y(L) + t - 4, "EQUIPMENT ROOM / RACK BEYOND", "tiny", anchor="start")

    if not rcp:
        # riser
        rf, rx1 = SE["riser_front"], SE["riser_x1"]
        rb = SE["riser_back"]
        sh.rect(X(0), Y(rf), (rx1) * s, (rb - rf) * s, "riser")
        sh.rect(X(0), Y(rf), (rx1) * s, (rb - rf) * s, "ln2")
        sh.text(X(rx1 / 2), Y(rb) - 12, f"RISER +{ftin(SE['riser'])} A.F.F.", "small")
        sh.text(X(0.25), Y(L) - 10, "REAR CROSS-AISLE (FLOOR LEVEL)", "tiny", anchor="start")
        sh.text(X(rx1 + (W - rx1) / 2), Y(rf + 0.9), "AISLE", "small", rot=-90)
        # AT screen and fabric plane
        sh.line(X(0), Y(SC["y"]), X(W), Y(SC["y"]), "hid")
        sh.rect(X(SC["x0"]), Y(SC["y"]) - 4, SC["w"] * s, 8, "screen")
        sh.text(X(W / 2), Y(SC["y"]) + 26,
                f"{D['inputs']['screen']['diag_in']}\" {D['inputs']['screen']['aspect_label']} AT SCREEN - IMAGE {ftin(SC['w'])} W", "small")
        sh.text(X(0.15), Y(SC["y"]) - 8, "AT FABRIC PLANE", "tiny", anchor="start")
        # seats
        for st in SE["seats"]:
            x, y = st["x"], st["y"]
            sh.rect(X(x - SEAT_W / 2), Y(y - SEAT_FRONT), SEAT_W * s, (SEAT_FRONT + SEAT_BACK) * s, "seat")
            sh.rect(X(x - SEAT_W / 2), Y(y - SEAT_FRONT), 0.09 * s, (SEAT_FRONT + SEAT_BACK) * s, "arm")
            sh.rect(X(x + SEAT_W / 2 - 0.09), Y(y - SEAT_FRONT), 0.09 * s, (SEAT_FRONT + SEAT_BACK) * s, "arm")
            sh.rect(X(x - SEAT_W / 2 + 0.12), Y(y - SEAT_FRONT - FOOT), (SEAT_W - 0.24) * s, FOOT * s, "hid")
            sh.circle(X(x), Y(y), 4, "earpt")
            sh.text(X(x), Y(y - 0.32), st["id"], "seatt")
        # RSP
        rx, ry = SE["rsp"][0], SE["rsp"][1]
        sh.circle(X(rx), Y(ry), 11, "rsp")
        sh.line(X(rx) - 17, Y(ry), X(rx) + 17, Y(ry), "rspl")
        sh.line(X(rx), Y(ry) - 17, X(rx), Y(ry) + 17, "rspl")
        sh.text(X(rx) + 2, Y(ry) + 32, "RSP", "rspt")
        # rays to ear-level speakers
        for ch in ("L", "R", "Lss", "Rss", "Lrs", "Rrs"):
            p = CH[ch]["pos"]
            sh.line(X(rx), Y(ry), X(p[0]), Y(p[1]), "ray")
    else:
        for st in SE["seats"]:
            x, y = st["x"], st["y"]
            sh.rect(X(x - SEAT_W / 2), Y(y - SEAT_FRONT), SEAT_W * s, (SEAT_FRONT + SEAT_BACK) * s, "ghost")
        cz = TZ["ceiling"]
        sh.rect(X(cz["x0"]), Y(cz["y0"]), (cz["x1"] - cz["x0"]) * s, (cz["y1"] - cz["y0"]) * s, "zone")
        sh.text(X((cz["x0"] + cz["x1"]) / 2), Y(cz["y0"]) - 8, "ACOUSTIC CLOUD (1\" ABSORBER) AT FIRST-REFLECTION ZONE", "small")
        # projector
        lx, ly, lz = PJ["lens"]
        bw, bd = 0.50, 0.50
        sh.rect(X(lx - bw / 2), Y(ly), bw * s, bd * s, "proj")
        sh.circle(X(lx), Y(ly) + 6, 5, "ln")
        sh.text(X(lx + 1.15), Y(ly + 0.2), "PROJECTOR", "small", anchor="start")
        sh.text(X(lx + 1.15), Y(ly + 0.2) + 16, "CEILING MOUNT", "tiny", anchor="start")
        sh.line(X(lx + bw / 2) + 2, Y(ly + 0.18), X(lx + 1.12), Y(ly + 0.18), "leader")
        sh.line(X(lx), Y(ly), X(SC["x0"]), Y(SC["y"]), "beam")
        sh.line(X(lx), Y(ly), X(SC["x1"]), Y(SC["y"]), "beam")
        sh.rect(X(SC["x0"]), Y(SC["y"]) - 3, SC["w"] * s, 6, "screen")
        # corner traps
        for (cx, cy) in ((0, 0), (W, 0), (0, L), (W, L)):
            sx = 1 if cx == 0 else -1
            sy = 1 if cy == 0 else -1
            sh.path(f"M {X(cx):.1f} {Y(cy):.1f} L {X(cx)+sx*0.42*s:.1f} {Y(cy):.1f} L {X(cx):.1f} {Y(cy)+sy*0.42*s:.1f} Z", "trap")

    # speakers on walls (plan symbols)
    for c in D["channels"]:
        p = c["pos"]
        gw = CAT[c["model"]].get("grille_wh", [0.3, 0.4])[0]
        dep = CAT[c["model"]].get("depth", 0.1)
        if c["mount"].startswith("Front"):
            sh.rect(X(p[0] - gw / 2), Y(0) - dep * s, gw * s, dep * s, "spk" if not rcp else "spkghost")
            if not rcp:
                sh.tag(X(p[0]), Y(0) - t - 22, c["ch"])
        elif c["mount"] == "Left wall":
            sh.rect(X(0) - dep * s, Y(p[1] - gw / 2), dep * s, gw * s, "spk" if not rcp else "spkghost")
            if not rcp:
                sh.tag(X(0) - t - 30, Y(p[1]), c["ch"])
        elif c["mount"] == "Right wall":
            sh.rect(X(W), Y(p[1] - gw / 2), dep * s, gw * s, "spk" if not rcp else "spkghost")
            if not rcp:
                sh.tag(X(W) + t + 30, Y(p[1]), c["ch"])
        elif c["mount"] == "Back wall":
            sh.rect(X(p[0] - gw / 2), Y(L), gw * s, dep * s, "spk" if not rcp else "spkghost")
            if not rcp:
                sh.tag(X(p[0]), Y(L) + t + 22, c["ch"])
        elif c["mount"] == "Ceiling":
            gw2, gh2 = CAT[c["model"]].get("grille_wh", [0.25, 0.42])
            cls = "spk" if rcp else "spkabove"
            sh.rect(X(p[0] - gw2 / 2), Y(p[1] - gh2 / 2), gw2 * s, gh2 * s, cls)
            sh.tag(X(p[0]), Y(p[1] + gh2 / 2) + 20, c["ch"], "tag" if rcp else "tagabove")
    # subwoofers
    sw_w, sw_h = CAT[SUBM]["grille_wh"]
    sw_d = CAT[SUBM]["depth"]
    for i, (pos, wall) in enumerate(zip(SUB["units"], SUB["walls"])):
        lab = f"SW{i+1}"
        if wall == "left":
            sh.rect(X(0) - sw_d * s, Y(pos[1] - sw_w / 2), sw_d * s, sw_w * s, "sub" if not rcp else "spkghost")
            if not rcp:
                sh.tag(X(0) - t - 34, Y(pos[1]), lab, "tagsub")
        elif wall == "right":
            sh.rect(X(W), Y(pos[1] - sw_w / 2), sw_d * s, sw_w * s, "sub" if not rcp else "spkghost")
            if not rcp:
                sh.tag(X(W) + t + 34, Y(pos[1]), lab, "tagsub")
        elif wall == "front":
            sh.rect(X(pos[0] - sw_w / 2), Y(0) - sw_d * s, sw_w * s, sw_d * s, "sub")
            if not rcp:
                sh.tag(X(pos[0]), Y(0) - t - 22, lab, "tagsub")
        else:
            sh.rect(X(pos[0] - sw_w / 2), Y(L), sw_w * s, sw_d * s, "sub")
            if not rcp:
                sh.tag(X(pos[0]), Y(L) + t + 22, lab, "tagsub")

    # dimensions
    sh.dim(X(0), Y(0) - t, X(W), Y(0) - t, -54, ftin(W))
    sh.dim(X(0) - t, Y(0), X(0) - t, Y(L), 92 if not rcp else 60, ftin(L))
    if not rcp:
        xs = sorted([0.0, CH["L"]["pos"][0], W / 2, CH["R"]["pos"][0], W])
        for a, b in zip(xs, xs[1:]):
            sh.dim(X(a), Y(0) - t, X(b), Y(0) - t, -28, ftin(b - a))
        ys = [0.0, SC["y"], SE["y1"], SE["y2"], L]
        for a, b in zip(ys, ys[1:]):
            sh.dim(X(0) - t, Y(a), X(0) - t, Y(b), 62, ftin(b - a))
        sh.text(X(0) + 8, Y(SE["y1"]) - 6, "ROW 1 EAR", "tiny", anchor="start")
        sh.text(X(0) + 8, Y(SE["y2"]) - 6, "ROW 2 EAR", "tiny", anchor="start")
        rs = sorted({0.0, CH["Rss"]["pos"][1], CH["Rrs"]["pos"][1], L} |
                    {u[1] for u, w in zip(SUB["units"], SUB["walls"]) if w == "right"})
        for a, b in zip(rs, rs[1:]):
            sh.dim(X(W) + t, Y(a), X(W) + t, Y(b), -74, ftin(b - a))
    else:
        tops = [c for c in D["channels"] if c["mount"] == "Ceiling"]
        xs = sorted({0.0, W} | {round(c["pos"][0], 4) for c in tops})
        for a, b in zip(xs, xs[1:]):
            sh.dim(X(a), Y(0) - t, X(b), Y(0) - t, -36, ftin(b - a))
        ys = sorted({0.0, L, round(PJ["lens"][1], 4)} | {round(c["pos"][1], 4) for c in tops})
        for a, b in zip(ys, ys[1:]):
            sh.dim(X(W) + t, Y(a), X(W) + t, Y(b), -40, ftin(b - a))
        sh.text(X(W) + t + 50, Y(PJ["lens"][1]) + 4, "LENS", "tiny", anchor="start")
    return sh, X, Y, s


def legend(sh, x, y, items):
    sh.text(x, y, "LEGEND", "h3", anchor="start")
    y += 26
    for cls, lab, kind in items:
        if kind == "rect":
            sh.rect(x, y - 12, 34, 16, cls)
        elif kind == "line":
            sh.line(x, y - 4, x + 34, y - 4, cls)
        elif kind == "tag":
            sh.tag(x + 17, y - 4, "Ls", cls)
        elif kind == "circle":
            sh.circle(x + 17, y - 4, 9, cls)
        sh.text(x + 46, y, lab, "small", anchor="start")
        y += 26
    return y


def notes(sh, x, y, title, lines, width=58):
    sh.text(x, y, title, "h3", anchor="start")
    y += 24
    for i, ln_ in enumerate(lines, 1):
        words, cur, first = ln_.split(), "", True
        out = []
        for w_ in words:
            if len(cur + " " + w_) > width:
                out.append(cur)
                cur = w_
            else:
                cur = (cur + " " + w_).strip()
        out.append(cur)
        for j, o in enumerate(out):
            sh.text(x, y, (f"{i}. " if j == 0 else "    ") + o, "note", anchor="start")
            y += 17
        y += 4
    return y


# ----------------------------------------------------------------------------
def sheet_a101():
    sh, X, Y, s = plan_sheet("A-101", "Floor Plan and Speaker Layout")
    y = legend(sh, 1000, 90, [("spk", f"In-wall loudspeaker (JBL {PKG['lcr']} / {PKG['surround']})", "rect"),
                             ("sub", f"Subwoofer (JBL {SUBM})", "rect"),
                             ("spkabove", "Ceiling loudspeaker (above)", "rect"),
                             ("seat", "Recliner, upright (footrest dashed)", "rect"),
                             ("riser", "Riser platform", "rect"),
                             ("ray", "Reference ray from RSP", "line"),
                             ("rsp", "Reference seating position (RSP)", "circle")])
    sh.text(1000, y + 14, "SPEAKER ANGLES FROM RSP", "h3", anchor="start")
    y += 40
    sh.text(1000, y, "TAG MODEL     AZ    EL      DIST  OK", "mono", anchor="start")
    y += 18
    for c in D["channels"]:
        win = c["window"]
        wtxt = "-" if not win else f"{c['hits']}/8"
        sh.text(1000, y, f"{c['ch']:<4}{c['model']:<6}{abs(c['az']):6.1f}°{c['el']:5.1f}°{ftin(c['d']):>11} {wtxt:>4}",
                "mono", anchor="start")
        y += 17
    notes(sh, 1000, y + 24, "PLAN NOTES", [
        "Dimensions to finished interior faces. Concept dimensions; field-verify before framing.",
        "Front wall is a full-width acoustically transparent (AT) fabric plane; L/C/R are in-wall behind it.",
        f"Check framing depth for in-wall {PKG['lcr']} and {SUBM} (2x6 walls recommended; see manufacturer templates).",
        "Speaker centres are shown; see AV-501 for X/Y/Z coordinates and AV-601 for seat compliance.",
        "Ear points (dots) at 1.05 m above row floor; RSP is row-1 centre between seats 1B/1C.",
        "OK = seats (of 8) inside the Dolby placement window for that channel."], width=52)
    return sh


def sheet_a102():
    sh, X, Y, s = plan_sheet("A-102", "Reflected Ceiling Plan", rcp=True)
    y = legend(sh, 1000, 90, [("spk", f"Ceiling loudspeaker (JBL {PKG['top']})", "rect"),
                             ("proj", "Projector and mount (lens at front edge)", "rect"),
                             ("beam", "Projected image edges", "line"),
                             ("zone", "Acoustic cloud / first-reflection zone", "rect"),
                             ("trap", "Corner bass trap below (full height)", "rect"),
                             ("ghost", "Seats below (reference)", "rect")])
    y += 10
    sh.text(1000, y, "OVERHEAD SPEAKERS", "h3", anchor="start")
    y += 24
    sh.text(1000, y, "TAG  X (L WALL)  Y (SCRN WALL)  EL@RSP", "mono", anchor="start")
    y += 18
    for c in D["channels"]:
        if c["mount"] != "Ceiling":
            continue
        p = c["pos"]
        sh.text(1000, y, f"{c['ch']:<4}{ftin(p[0]):>11}{ftin(p[1]):>15}{c['el']:8.1f}°", "mono", anchor="start")
        y += 17
    lx, ly, lz = PJ["lens"]
    notes(sh, 1000, y + 24, "CEILING NOTES", [
        f"Ceiling height {ftin(H)} (ASSUMED). Confirm joist direction and depth before locating ceiling speakers.",
        f"Projector lens at {ftin(ly - SC['y'])} from screen plane, lens height {ftin(lz)}; throw ratio {PJ['tr']:.2f}:1.",
        f"Vertical lens shift required {PJ['shift_pct']:.0f}% of image height (published limit +/-{PJ['spec']['vshift_pct']}%; verify Sony definition).",
        "Overhead speakers aimed toward midpoint between rows where the model allows rotation.",
        "Provide a dedicated 20 A circuit and conduit (HDMI fibre + control) to the projector location."], width=52)
    return sh


def sheet_a201():
    s = scale_units(1 / 2)
    sh = Sheet("A-201", "Screen Wall Elevation", '1/2" = 1\'-0" (on 11x17)')
    ox, oy = 170, 230
    X = lambda x: ox + x * s
    Z = lambda z: oy + (H - z) * s
    sh.rect(X(0), Z(H), W * s, H * s, "ln")
    sh.rect(X(0) - 12, Z(0), W * s + 24, 12, "wall")
    sh.rect(X(0) - 12, Z(H) - 12, W * s + 24, 12, "wall")
    sh.rect(X(0), Z(H), W * s, H * s, "fabric")
    sh.rect(X(SC["x0"]) - 8, Z(SC["zt"]) - 8, SC["w"] * s + 16, SC["h"] * s + 16, "frameblk")
    sh.rect(X(SC["x0"]), Z(SC["zt"]), SC["w"] * s, SC["h"] * s, "image")
    sh.text(X(W / 2), Z(SC["zt"]) + 36, f"{D['inputs']['screen']['diag_in']}\" DIAG. {D['inputs']['screen']['aspect_label']} AT IMAGE",
            "small")
    for ch in ("L", "C", "R"):
        p = CH[ch]["pos"]
        gw, gh = CAT[CH["L"]["model"]]["grille_wh"]
        sh.rect(X(p[0] - gw / 2), Z(p[2] + gh / 2), gw * s, gh * s, "hidspk")
        sh.circle(X(p[0]), Z(p[2] + 0.12), 7, "hid")
        sh.tag(X(p[0]), Z(p[2] - gh / 2) + 26, ch)
    for x in (0.0, W):
        sx = 1 if x == 0 else -1
        sh.rect(X(x), Z(H), sx * 0.42 * s, H * s, "trapel")
    sh.text(X(0.21), Z(H / 2), "BASS TRAP", "tiny", rot=-90)
    sh.text(X(W - 0.21), Z(H / 2), "BASS TRAP", "tiny", rot=-90)
    ear = D["inputs"]["seating"]["ear"]
    sh.line(X(0), Z(ear), X(W), Z(ear), "ref")
    sh.text(X(0.95), Z(ear) - 6, f"ROW 1 EAR {ftin(ear)}", "tiny", anchor="start")
    eye2 = SE["riser"] + D["inputs"]["seating"]["eye"]
    sh.line(X(0), Z(eye2), X(W), Z(eye2), "ref")
    sh.text(X(0.95), Z(eye2) - 6, f"ROW 2 EYE {ftin(eye2)}", "tiny", anchor="start")
    # dims
    sh.dim(X(0), Z(H) - 12, X(W), Z(H) - 12, -40, ftin(W))
    xs = [0.0, SC["x0"], SC["x1"], W]
    for a, b in zip(xs, xs[1:]):
        sh.dim(X(a), Z(0) + 12, X(b), Z(0) + 12, 40, ftin(b - a))
    xs = [0.0, CH["L"]["pos"][0], W / 2, CH["R"]["pos"][0], W]
    for a, b in zip(xs, xs[1:]):
        sh.dim(X(a), Z(0) + 12, X(b), Z(0) + 12, 80, ftin(b - a))
    zs = [0.0, SC["zb"], SC["zt"], H]
    for a, b in zip(zs, zs[1:]):
        sh.dim(X(W) + 12, Z(a), X(W) + 12, Z(b), 40, ftin(b - a))
    sh.dim(X(0) - 12, Z(0), X(0) - 12, Z(CH["L"]["pos"][2]), -40, ftin(CH["L"]["pos"][2]))
    sh.dim(X(0) - 12, Z(0), X(0) - 12, Z(H), -84, ftin(H))
    notes(sh, 170, 820, "ELEVATION NOTES", [
        f"Image {ftin(SC['w'])} W x {ftin(SC['h'])} H; bottom of image {ftin(SC['zb'])} A.F.F.; top {ftin(SC['zt'])}.",
        f"L/C/R JBL {PKG['lcr']} behind AT fabric, centred at 1.17 m (3'-10\"); verify grille clear of screen frame.",
        "Black, absorptive treatment behind the full AT plane; corner bass traps behind fabric.",
        f"Front-row vertical angle to top of image {max(v['v_top'] for v in D['viewing']):.1f} deg (guidance ~15 deg, verify)."],
        width=110)
    return sh


def sheet_a202():
    s = scale_units(3 / 8)
    sh = Sheet("A-202", "Side Wall Elevations", '3/8" = 1\'-0" (on 11x17)')
    sw_w, sw_h = CAT[SUBM]["grille_wh"]
    for k, (wall, oy, flip) in enumerate((("left", 120, True), ("right", 590, False))):
        ox = 140
        # looking at the wall from inside: left wall -> screen on the right; right wall -> screen on the left
        U = (lambda y: ox + (L - y) * s) if flip else (lambda y: ox + y * s)
        Z = lambda z: oy + (H - z) * s
        sh.text(ox, oy - 40, f"{'LEFT' if flip else 'RIGHT'} WALL - VIEWED FROM INSIDE THE ROOM", "h3", anchor="start")
        sh.rect(min(U(0), U(L)), Z(H), L * s, H * s, "ln")
        sh.rect(min(U(0), U(L)) - 10, Z(0), L * s + 20, 10, "wall")
        sh.rect(min(U(0), U(L)) - 10, Z(H) - 10, L * s + 20, 10, "wall")
        tz = TZ[wall]
        sh.rect(min(U(tz["y0"]), U(tz["y1"])), Z(tz["z1"]), (tz["y1"] - tz["y0"]) * s, (tz["z1"] - tz["z0"]) * s, "zone")
        sh.text((U(tz["y0"]) + U(tz["y1"])) / 2, Z(tz["z1"]) - 8, "FIRST-REFLECTION ABSORPTION ZONE (1\" PANEL)", "tiny")
        # riser profile
        rf, rb = SE["riser_front"], SE["riser_back"]
        sh.rect(min(U(rf), U(rb)), Z(SE["riser"]), (rb - rf) * s, SE["riser"] * s, "riser")
        sh.text((U(rf) + U(rb)) / 2, Z(SE["riser"] / 2) + 4, f"RISER {ftin(SE['riser'])}", "tiny")
        # screen wall marker
        sh.text(U(0) + (-14 if flip else 14), Z(H / 2), "SCREEN WALL", "tiny", rot=-90)
        for c in D["channels"]:
            if c["mount"] != ("Left wall" if flip else "Right wall"):
                continue
            p = c["pos"]
            gw, gh = CAT[c["model"]]["grille_wh"]
            sh.rect(U(p[1]) - gw * s / 2, Z(p[2] + gh / 2), gw * s, gh * s, "spk")
            sh.tag(U(p[1]), Z(p[2] + gh / 2) - 18, c["ch"])
        for i, (pos, w_) in enumerate(zip(SUB["units"], SUB["walls"])):
            if w_ != wall:
                continue
            zc = 0.15 + sw_h / 2
            sh.rect(U(pos[1]) - sw_w * s / 2, Z(zc + sw_h / 2), sw_w * s, sw_h * s, "sub")
            sh.tag(U(pos[1]), Z(zc + sw_h / 2) - 18, f"SW{i+1}", "tagsub")
        # dims along bottom: positions from screen wall
        marks = sorted({0.0, L} | {c["pos"][1] for c in D["channels"] if c["mount"] == ("Left wall" if flip else "Right wall")}
                       | {u[1] for u, w_ in zip(SUB["units"], SUB["walls"]) if w_ == wall})
        for a, b in zip(marks, marks[1:]):
            x1, x2 = sorted((U(a), U(b)))
            sh.dim(x1, Z(0) + 10, x2, Z(0) + 10, 34, ftin(b - a))
        zs = sorted({0.0, H, CH["Lss"]["pos"][2]})
        xe = max(U(0), U(L))
        for a, b in zip(zs, zs[1:]):
            sh.dim(xe, Z(a), xe, Z(b), 40, ftin(b - a))
    notes(sh, 1135, 130, "NOTES", [
        f"Surrounds JBL {PKG['surround']} in-wall at a common centre height to clear row-2 heads on the riser.",
        f"{SUBM} subwoofers vertical, bottom of grille 6\" A.F.F.; locate between studs per JBL template. Layout: {D['subs']['chosen']} (see AV-602).",
        "Absorption zones derived from first-reflection points of L/C/R for all eight seats, plus margin.",
        "Treat the rear half of side walls with diffusion or leave reflective to avoid over-damping (see AV-601 RT60).",
        "Subwoofer grilles may sit behind fabric; keep panels clear of sub cut-outs."], width=33)
    return sh


def sheet_a301():
    s = scale_units(1 / 2)
    sh = Sheet("A-301", "Longitudinal Section", '1/2" = 1\'-0" (on 11x17)')
    ox, oy = 92, 200
    U = lambda y: ox + y * s
    Z = lambda z: oy + (H - z) * s
    sh.rect(U(0) - 12, Z(H), 12, H * s, "wall")
    sh.rect(U(L), Z(H), 12, H * s, "wall")
    sh.rect(U(0) - 12, Z(0), L * s + 24, 12, "wall")
    sh.rect(U(0) - 12, Z(H) - 12, L * s + 24, 12, "wall")
    rf, rz = SE["riser_front"], SE["riser"]
    rb = SE["riser_back"]
    sh.rect(U(rf), Z(rz), (rb - rf) * s, rz * s, "riser")
    # screen + centre speaker
    sh.line(U(SC["y"]), Z(SC["zb"]), U(SC["y"]), Z(SC["zt"]), "screenln")
    gw, gh = CAT[CH["C"]["model"]]["grille_wh"]
    dep = CAT[CH["C"]["model"]]["depth"]
    pc = CH["C"]["pos"]
    sh.rect(U(0) - dep * s, Z(pc[2] + gh / 2), dep * s, gh * s, "spk")
    sh.tag(U(0) + 32, Z(pc[2] + gh / 2) - 16, "C")
    eye = D["inputs"]["seating"]["eye"]
    ear = D["inputs"]["seating"]["ear"]
    # seated figures
    for yy, fl in ((SE["y1"], 0.0), (SE["y2"], rz)):
        sh.path(f"M {U(yy+0.20):.1f} {Z(fl+0.0):.1f} L {U(yy+0.20):.1f} {Z(fl+0.45):.1f} L {U(yy-0.55):.1f} {Z(fl+0.45):.1f} "
                f"L {U(yy-0.55):.1f} {Z(fl+0.0):.1f}", "seat")
        sh.path(f"M {U(yy+0.22):.1f} {Z(fl+0.45):.1f} L {U(yy+0.30):.1f} {Z(fl+1.10):.1f}", "seatback")
        sh.circle(U(yy), Z(fl + eye + 0.02), 0.11 * s, "head")
        sh.circle(U(yy) - 0.06 * s, Z(fl + eye), 3, "eyept")
    # sightline row2 eye -> screen bottom
    y2 = SE["y2"]
    e2 = rz + eye
    sh.line(U(y2) - 0.06 * s, Z(e2), U(SC["y"]), Z(SC["zb"]), "sight")
    zat1 = SC["zb"] + (e2 - SC["zb"]) * (SE["y1"] - SC["y"]) / (y2 - SC["y"])
    sh.line(U(SE["y1"]) - 4, Z(zat1), U(SE["y1"]) - 60, Z(zat1) + 70, "leader")
    sh.text(U(SE["y1"]) - 64, Z(zat1) + 84, f"SIGHTLINE CLEARS ROW-1 EYE BY {ftin(zat1 - eye)}", "tiny", anchor="end")
    # projector & beam
    lx, ly, lz = PJ["lens"]
    sh.rect(U(ly), Z(lz) - 0.10 * s, 0.50 * s, 0.25 * s, "proj")
    sh.line(U(ly + 0.25), Z(lz + 0.15), U(ly + 0.25), Z(H), "ln")
    sh.line(U(ly), Z(lz), U(SC["y"]), Z(SC["zt"]), "beam")
    sh.line(U(ly), Z(lz), U(SC["y"]), Z(SC["zb"]), "beam")
    sh.text(U(ly + 0.25), Z(lz) + 0.15 * s + 16, "PROJECTOR", "tiny")
    bb = PJ["beam"]["row2"]["beam_bottom"]
    sh.line(U(y2) + 26, Z(rz + 1.80), U(y2) + 26, Z(rz), "stand")
    sh.text(U(y2) + 32, Z(rz + 1.0), f"STANDING 1.80 m: {ftin(rz+1.80)}", "tiny", anchor="start")
    sh.text(U(y2) + 32, Z(rz + 1.0) + 14, f"BEAM BOTTOM: {ftin(bb)}", "tiny", anchor="start")
    # overheads: elevation lines to RSP
    for c in D["channels"]:
        if c["mount"] != "Ceiling" or not c["ch"].startswith("L"):
            continue
        p = c["pos"]
        sh.rect(U(p[1]) - 0.21 * s, Z(H), 0.42 * s, 0.09 * s, "spk")
        sh.tag(U(p[1]), Z(H) + 34, c["ch"])
        sh.line(U(p[1]), Z(H), U(SE["y1"]), Z(ear), "ray")
        sh.line(U(p[1]), Z(H), U(y2), Z(rz + ear), "ray2")
        r2 = next(x for x in c["seats"] if x["seat"] == "2B")
        sh.text(U(p[1]), Z(H) + 62, f"EL: RSP {c['el']:.0f}° / ROW 2 {r2['el']:.0f}°", "tiny")
    # dims
    ys = [0.0, SC["y"], SE["y1"], SE["y2"], L]
    for a, b in zip(ys, ys[1:]):
        sh.dim(U(a), Z(0) + 12, U(b), Z(0) + 12, 40, ftin(b - a))
    sh.dim(U(SC["y"]), Z(0) + 12, U(ly), Z(0) + 12, 84, f"THROW {ftin(PJ['throw'])}")
    zs = [0.0, SC["zb"], SC["zt"], H]
    for a, b in zip(zs, zs[1:]):
        sh.dim(U(0) - 12, Z(a), U(0) - 12, Z(b), -34, ftin(b - a))
    sh.dim(U(L) + 12, Z(0), U(L) + 12, Z(rz), 30, ftin(rz))
    sh.dim(U(L) + 12, Z(0), U(L) + 12, Z(H), 64, ftin(H))
    sh.dim(U(L) + 12, Z(rz), U(L) + 12, Z(rz + eye), 30, ftin(eye))
    sh.dim(U(L) + 12, Z(lz), U(L) + 12, Z(H), 30, ftin(H - lz))
    v = D["viewing"]
    notes(sh, 92, 830, "SECTION NOTES", [
        f"Riser {ftin(rz)} computed for a {D['inputs']['seating']['C_clear']*1000:.0f} mm sightline clearance (C-value) over row-1 eye to image bottom.",
        f"Viewing: row 1 {v[1]['hva']:.1f}° horizontal / {v[1]['v_top']:.1f}° to image top; row 2 {v[5]['hva']:.1f}° / {v[5]['v_top']:.1f}°.",
        f"Headroom on riser {ftin(H - rz)}. Overhead angles shown at RSP and row-2 centre (Dolby window 30-55°, verify).",
        "Standing viewers on the riser intersect the lower image beam; consider a higher mount or rear-wall shelf (see AV-601)."],
        width=150)
    return sh


# ----------------------------------------------------------------------------
def table(headers, rows, cls=""):
    th = "".join(f"<th>{e(h)}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def html_sheet(number, title, body):
    p = D["inputs"]
    return (f'<section class="sheet doc" id="{number.lower()}"><header class="dochead"><div class="docbrand">CHT</div>'
            f'<div class="docmeta"><span>{e(p["project"])}</span><span>{e(p["project_no"])} &middot; Rev {e(p["revision"])} &middot; {e(p["date"])}</span></div>'
            f'<div class="docno"><span class="k">SHEET</span><span class="n">{e(number)}</span></div></header>'
            f'<h2 class="doctitle">{e(title)}</h2><div class="docbody">{body}</div>'
            f'<footer class="docfoot">Concept design generated by the CHT design engine v0.1 &middot; not for construction &middot; '
            f'values marked [verify] come from secondary sources</footer></section>')


def sheet_av501():
    ch_rows = []
    for c in D["channels"]:
        p = c["pos"]
        aim = c.get("aim")
        ch_rows.append([e(c["ch"]), e(f"JBL Synthesis {c['model']}"), e(c["mount"]),
                        e(ftin(p[0])), e(ftin(p[1])), e(ftin(p[2])), f"{abs(c['az']):.1f}°", f"{c['el']:.1f}°",
                        e(ftin(c["d"])), e(f"yaw {aim['yaw']:.0f}° / tilt {aim['tilt']:.0f}°" if aim else "flush, on-axis")])
    for i, (pos, w_) in enumerate(zip(SUB["units"], SUB["walls"])):
        ch_rows.append([f"SW{i+1}", f"JBL Synthesis {SUBM}", e(f"{w_.title()} wall, vertical"), e(ftin(pos[0])), e(ftin(pos[1])),
                        e(ftin(pos[2])), "-", "-", "-", "-"])
    t1 = table(["Tag", "Model", "Mounting", "X (from left wall)", "Y (from screen wall)", "Z (A.F.F.)", "Azimuth @RSP",
                "Elevation @RSP", "Distance", "Aim"], ch_rows, "num")
    bom = [[str(b["qty"]), e(b["model"]), e(b["sku"] or "-"), e(b["desc"]), e(b.get("note", "")),
            money(b.get("msrp")), money(b.get("ext_msrp"))] for b in D["bom"]]
    if D.get("msrp_total") is not None:
        bom.append(["", "", "", "<b>Equipment on Savant list</b>", "", "", f"<b>{money(D['msrp_total'])}</b>"])
    t2 = table(["Qty", "Model", "SKU", "Description", "Note", "List (MSRP)", "Ext. list"], bom, "num")
    amap = [[e(a["ch"]), e(a["amp"]), str(a["out"])] for a in D["amp_map"]]
    t3 = table(["Channel", "Amplifier", "Output"], amap, "num")
    cab = [[e(c["ch"]), f"{c['run_m']:.1f} m ({c['run_m']/FT:.0f} ft)", f"{c['awg']} AWG", f"{c['loop_ohm']:.3f} &Omega;",
            f"{c['loss_db']:.2f} dB"] for c in D["cables"]]
    t4 = table(["Run", "Est. length", "Gauge", "Loop R", "Loss"], cab, "num")
    sy = D["system"]
    body = (f'<div class="g2"><div class="cell wide"><h3>Loudspeaker schedule</h3>{t1}'
            f'<p class="fine">Coordinates: origin at front-left floor corner at the finished faces; X across the room, Y from the screen wall, Z above finished floor. '
            f'Azimuth 0° = toward the screen.</p></div>'
            f'<div class="cell wide"><h3>Equipment schedule ({e(PKG["label"])} package)</h3>{t2}'
            f'<p class="fine">Processor outputs used: {sy["proc_outputs_used"]} of {sy["proc_capacity"]} '
            f'({sy["full_range"]} full-range + {sy["sub_outputs"]} sub outputs; {sy["sub_units"]} subwoofers). '
            f'List prices: {e(D.get("price_source") or "not loaded")}. Dealer cost is kept in the private parts catalog only.</p></div>'
            f'<div class="cell"><h3>Amplifier channel map</h3>{t3}</div>'
            f'<div class="cell"><h3>Speaker cable schedule</h3>{t4}'
            f'<p class="fine">Rack outside the back wall. Length = vertical drop + ceiling route (Manhattan) + 1.5 m drop + 2.0 m service loop. '
            f'Gauge chosen so loop resistance &le; 5% of 0.8 &times; nominal impedance (stand-in for minimum impedance).</p></div></div>')
    return html_sheet("AV-501", "Schedules: loudspeakers, equipment, amplification, cabling", body)


def sheet_av601():
    lc = D["layout_compare"]
    seats = [s_["id"] for s_ in SE["seats"]]
    comp = []
    for c in D["channels"]:
        if not c["window"]:
            continue
        cells = []
        for x in c["seats"]:
            cells.append(f'<span class="{"ok" if x["ok"] else "no"}">{x["val"]:.0f}°</span>')
        w = c["window"]
        comp.append([e(c["ch"]), e(f"{w[0]} {w[1]}-{w[2]}°")] + cells)
    t1 = table(["Ch", "Window"] + seats, comp, "num comp")
    spl = [[e(r["ch"]), e(r["model"]), e(r["amp"]), f"{r['p_amp']:.0f}", f"{r['d']:.2f}", f"{r['p_req']:.0f}",
            f"{r['cap_spk_ff']:.1f}", f"{r['cap_amp_room']:.1f}"] for r in D["spl"]["rows"]]
    t2 = table(["Ch", "Model", "Amp", "Amp W @Z", "Dist (m)", "W for 105+3 dB", "Spk max, free-field", "With amp, +room"], spl, "num")
    subs = []
    for o in D["subs"]["options"]:
        mark = "&#9679; " if o["id"] == D["subs"]["chosen_id"] else ""
        feas = "yes" if o["feasible"] else f"<b>no</b> ({e(', '.join(o['conflicts']) or 'span')})"
        subs.append([mark + e(o["name"]), str(o["n"]), feas, f"{o['mean_sd']:.2f}", f"{o['max_sd']:.1f}", f"{o['spl_max_ff']:.1f}"])
    t3 = table(["Subwoofer layout", "Subs", "Feasible", "Mean seat SD (dB)", "Max SD (dB)", "Max LFE @RSP (dB)"], subs, "num")
    ac = D["acoustics"]
    rt = [[str(b["band"]), f"{u['eyring']:.2f}", f"{b['eyring']:.2f}"] for b, u in zip(ac["rt_treated"], ac["rt_untreated"])]
    t4 = table(["Band (Hz)", "RT60 untreated (s)", "RT60 treated (s)"], rt, "num")
    ax = ", ".join(f"{m['f']:.1f}" for m in ac["axial"] if m["f"] < 120)
    v = [[e(x["seat"]), f"{x['dist']:.2f}", f"{x['hva']:.1f}°", f"{x['v_top']:.1f}°", f"{x['v_bot']:.1f}°", f"{x['off']:.1f}°"]
         for x in D["viewing"]]
    t5 = table(["Seat", "To screen (m)", "Horiz. angle", "To top", "To bottom", "Off-centre"], v, "num")
    lum = "; ".join(f"k={x['k']}, gain {x['gain']}: {x['fL']:.1f} fL ({x['nits']:.0f} cd/m²)" for x in PJ["lum"])
    warn = "".join(f"<li>{e(w)}</li>" for w in D["warnings"])
    body = (f'<div class="g2"><div class="cell wide"><h3>Speaker placement compliance per seat</h3>{t1}'
            f'<p class="fine">Placement found by search over wall and ceiling positions (Phase 3, A4). '
            f'7.2.4: {lc["7.2.4"]["hits"]}/{lc["7.2.4"]["total"]} seat-channel pairs in window ({lc["7.2.4"]["pct"]:.0f}%); '
            f'7.2.6: {lc["7.2.6"]["hits"]}/{lc["7.2.6"]["total"]} ({lc["7.2.6"]["pct"]:.0f}%). '
            f'Selected {D["layout"]}. Windows: Dolby home guidelines as commonly cited [verify].</p></div>'
            f'<div class="cell"><h3>Output and amplification (estimate)</h3>{t2}'
            f'<p class="fine">Target 105 dB peaks per channel + 3 dB margin at the RSP. "+room" adds the statistical reverberant field '
            f'(Q = {D["spl"]["Q"]:.0f}, R = {D["spl"]["R_room"]:.0f} m²). Class E estimate, about ±3 dB.</p></div>'
            f'<div class="cell"><h3>Subwoofer configurations (modal model)</h3>{t3}'
            f'<p class="fine">Rigid-wall modal sum, T60 = {D["subs"]["T60_LF"]} s below 250 Hz, 8 seats, 20-100 Hz. Ranks options; '
            f'absolute levels need measurement.</p></div>'
            f'<div class="cell"><h3>Room acoustics</h3>{t4}'
            f'<p class="fine">Axial modes below 120 Hz: {ax} Hz. Modes below 100 Hz: {ac["n_below_100"]}. '
            f'Small-room reference ≈ {ac["tm_ref"]:.2f} s. {e(ac["absorption_note"])}</p></div>'
            f'<div class="cell"><h3>Video</h3>{t5}'
            f'<p class="fine">Image {ftin(SC["w"])} × {ftin(SC["h"])} ({SC["area_ft2"]:.1f} ft²). Projector throw {ftin(PJ["throw"])}, '
            f'ratio {PJ["tr"]:.2f}:1, lens shift {PJ["shift_pct"]:.0f}%. Luminance: {lum}. '
            f'4K pixel structure resolves inside {D["acuity_4k_m"]:.2f} m.</p></div>'
            f'<div class="cell wide"><h3>Design review flags</h3><ul class="flags">{warn}</ul></div></div>')
    return html_sheet("AV-601", "Performance calculations and design review", body)


def cover():
    p = D["inputs"]
    sy = D["system"]
    idx = SHEET_INDEX
    idx_html = "".join(f'<li><a href="#{n.lower()}"><span>{n}</span>{e(t)}</a></li>' for n, t in idx)
    v = D["viewing"]
    facts = [("Room", f"{p['room']['length_ft']}′ × {p['room']['width_ft']}′ × {p['room']['height_ft']}′ ({D['room']['V']:.0f} m³)"),
             ("Package", f"{PKG['label']}: {PKG['lcr']} / {PKG['surround']} / {PKG['top']}"),
             ("Format", f"Dolby Atmos {D['layout']}, {sy['sub_units']} × {SUBM}"),
             ("Seating", f"2 rows × 4, riser {ftin(SE['riser'])}"),
             ("Screen", f"{p['screen']['diag_in']}″ {p['screen']['aspect_label']} AT, {ftin(SC['w'])} wide"),
             ("Row 1 view", f"{v[1]['hva']:.0f}° horizontal"),
             ("Processor", f"{sy['processor']}, {sy['proc_outputs_used']}/{sy['proc_capacity']} outputs"),
             ("Est. level", f"{D['spl']['achievable']:.0f}-{D['spl']['achievable_max']:.0f} dB peaks"),
             ("Bass spread", f"{SUB['mean_sd']:.1f} dB mean seat SD"),
             ("Equipment list", money(D.get("msrp_total")) + " MSRP" if D.get("msrp_total") else "prices not loaded")]
    facts_html = "".join(f'<div class="fact"><span class="k">{e(k)}</span><span class="v">{e(vv)}</span></div>' for k, vv in facts)
    basis = [
        "Clean-room design using published manufacturer data and the CHT calculation catalog (Phase 3). Formula IDs on AV-601.",
        "Room 24′ L × 18′ W; ceiling 9′ is an assumption. Finished-face dimensions to be field-verified.",
        "Screen on the 18′ wall. Full-width acoustically transparent front wall; L/C/R in-wall behind it.",
        "Equipment rack outside the theater beyond the back wall; door on the back wall at the right aisle.",
        "Placement windows from Dolby home-theater guidance as commonly cited; verify against the current Dolby document.",
        "Output figures are estimates (±3 dB). Speaker footprints marked ASSUMED in the catalog must be verified with JBL.",
        f"Products and SKUs from the {D.get('price_source') or 'Savant'}; Good / Better / Best compared on AV-701.",
    ]
    basis_html = "".join(f"<li>{e(b)}</li>" for b in basis)
    return (f'<section class="sheet doc cover" id="t-001"><header class="dochead"><div class="docbrand">CHT</div>'
            f'<div class="docmeta"><span>{e(p["project"])}</span><span>{e(p["project_no"])} &middot; Rev {e(p["revision"])} &middot; {e(p["date"])}</span></div>'
            f'<div class="docno"><span class="k">SHEET</span><span class="n">T-001</span></div></header>'
            f'<div class="coverhero"><div class="eyebrow">Concept drawing set</div><h1>JBL Synthesis Theater, 24 × 18</h1>'
            f'<p class="lede">Dolby Atmos {D["layout"]} dedicated theater with two rows of seating and an acoustically transparent '
            f'120″ screen. Drawn for the <b>{e(PKG["label"])}</b> package ({e(PKG["tagline"])}); all three packages are compared on AV-701.</p>'
            f'<div class="facts">{facts_html}</div></div>'
            f'<div class="g2"><div class="cell"><h3>Sheet index</h3><ol class="index">{idx_html}</ol></div>'
            f'<div class="cell"><h3>Design basis and assumptions</h3><ul class="basis">{basis_html}</ul></div></div>'
            f'<footer class="docfoot">Concept design &middot; not for construction &middot; generated from design.json by the CHT design engine v0.1</footer></section>')


SHEET_INDEX = [("T-001", "Cover, sheet index, design basis"), ("A-101", "Floor plan and speaker layout"),
               ("A-102", "Reflected ceiling plan"), ("A-201", "Screen wall elevation"), ("A-202", "Side wall elevations"),
               ("A-301", "Longitudinal section"), ("AV-501", "Schedules"), ("AV-601", "Performance calculations and review"),
               ("AV-602", "Subwoofer planner (interactive)"), ("AV-701", "Good / Better / Best options")]


def money(v):
    return "-" if v is None else f"${v:,.0f}"


def sheet_av602():
    data = {"W": W, "L": L, "H": H, "c": 343.0, "T60": D["subs"]["T60_LF"],
            "ears": [s_["ear"] for s_ in SE["seats"]], "ids": [s_["id"] for s_ in SE["seats"]], "rsp": SE["rsp"],
            "occupied": D["occupied"], "sub": {"model": SUBM, "w": D["subs"]["grille_wh"][0], "h": D["subs"]["grille_wh"][1],
                                               "zc": D["subs"]["zc"], "lmax": D["subs"]["lmax_1m_unit"]},
            "layouts": [{"id": o["id"], "name": o["name"], "units": o["wall_u"], "mean_sd": o["mean_sd"], "feasible": o["feasible"]}
                        for o in D["subs"]["options"]],
            "chosen": D["subs"]["chosen_id"], "screen": [SC["x0"], SC["x1"], SC["y"]],
            "door": [D["inputs"]["door"]["x0"], D["inputs"]["door"]["width"]]}
    opts = "".join(f'<option value="{e(o["id"])}"{" selected" if o["id"] == D["subs"]["chosen_id"] else ""}>'
                   f'{e(o["name"])} ({o["n"]}){"" if o["feasible"] else " - conflicts"}</option>' for o in D["subs"]["options"])
    body = (f'<div class="planner">'
            f'<div class="pcontrols"><label for="sublayout">Layout</label><select id="sublayout">{opts}'
            f'<option value="custom">Custom (dragged)</option></select>'
            f'<button type="button" id="subreset">Reset to recommended</button>'
            f'<span class="hint">Drag a subwoofer along any wall, or focus one and use the arrow keys (0.1 m steps). '
            f'Results update as you move.</span></div>'
            f'<div class="pgrid"><div class="pcell"><svg id="subplan" viewBox="0 0 100 100" role="img" aria-label="Room plan with subwoofers"></svg></div>'
            f'<div class="pcell"><div class="pmetrics" id="submetrics" aria-live="polite"></div>'
            f'<svg id="subchart" viewBox="0 0 520 300" role="img" aria-label="Predicted bass response at each seat"></svg>'
            f'<p class="fine">Predicted low-frequency response at every seat (thin) and the RSP (bold), 20-120 Hz, '
            f'rigid-wall modal model with T60 = {D["subs"]["T60_LF"]} s. Use it to compare layouts; confirm with measurements. '
            f'Mean seat SD = average across frequency of the level spread between the 8 seats (lower is more even).</p></div></div>'
            f'<script type="application/json" id="subdata">{json.dumps(data)}</script></div>')
    return html_sheet("AV-602", f"Subwoofer planner: {D['subs']['model']} layouts", body)


def sheet_av701():
    tiers = list(OPT.keys())
    rows = [("Positioning", lambda s_: e(s_["tagline"])),
            ("Front L / C / R", lambda s_: e(s_["lcr"])), ("Surrounds", lambda s_: e(s_["surround"])),
            ("Overheads", lambda s_: e(s_["top"])), ("Subwoofers", lambda s_: e(f"{s_['sub']} ({s_['sub_layout']})")),
            ("Processor / outputs used", lambda s_: e(f"{s_['processor']} / {s_['proc']}")),
            ("Amplification", lambda s_: e(s_["amps"])), ("Projector", lambda s_: e(s_["projector"])),
            ("Est. peaks at RSP (+room)", lambda s_: f"{s_['spl_low']:.1f}-{s_['spl_high']:.1f} dB"),
            ("Est. max LFE at RSP", lambda s_: f"{s_['lfe_ff']:.1f} dB"),
            ("Bass evenness (mean seat SD)", lambda s_: f"{s_['sub_sd']:.2f} dB"),
            ("Image brightness (est.)", lambda s_: f"{s_['fL']:.0f} fL"),
            ("Design flags", lambda s_: str(len(s_["warnings"]))),
            ("Equipment at list (MSRP)", lambda s_: f"<b>{money(s_['msrp_total'])}</b>")]
    head = "".join(f'<th class="{"cur" if t == D["tier"] else ""}">{e(OPT[t]["label"])}{" (drawn)" if t == D["tier"] else ""}</th>' for t in tiers)
    trs = "".join(f"<tr><th scope=\"row\">{e(lab)}</th>" + "".join(
        f'<td class="{"cur" if t == D["tier"] else ""}">{fn(OPT[t])}</td>' for t in tiers) + "</tr>" for lab, fn in rows)
    comp = f'<div class="tw"><table class="opt"><thead><tr><th></th>{head}</tr></thead><tbody>{trs}</tbody></table></div>'
    lists = ""
    for t in tiers:
        s_ = OPT[t]
        rr = [[str(b["qty"]), e(b["desc"]), money(b.get("ext_msrp"))] for b in s_["bom"] if b.get("sku")]
        rr.append(["", "<b>Total at list</b>", f"<b>{money(s_['msrp_total'])}</b>"])
        lists += f'<div class="cell"><h3>{e(s_["label"])} equipment</h3>{table(["Qty", "Item", "Ext. list"], rr, "plist")}</div>'
    body = (f'<div class="g2"><div class="cell wide"><h3>Package comparison</h3>{comp}'
            f'<p class="fine">Same room, seating, screen and speaker positions for every package; products, subwoofer count and electronics change. '
            f'Each package uses its own recommended subwoofer layout. List prices (MSRP) from the {e(D.get("price_source") or "Savant price list")}; '
            f'they cover equipment on the Savant list only (screen, seating, wire, treatment and labor are priced separately). '
            f'Dealer cost and margin are in the private CHT Parts Catalog workbook, not on this sheet. '
            f'Regenerate the drawings for another package with: python3 design.py --tier good|better|best.</p></div>'
            f'{lists}</div>')
    return html_sheet("AV-701", "Good / Better / Best options", body)


CSS2 = r"""
.planner{display:flex;flex-direction:column;gap:14px}
.pcontrols{display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center}
.pcontrols label{font-family:var(--f-mono);font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2)}
.pcontrols select,.pcontrols button{font:inherit;font-size:14px;color:var(--ink);background:var(--paper2);border:1px solid var(--ink3);padding:6px 10px;border-radius:2px;max-width:100%}
.pcontrols button{cursor:pointer}
.pcontrols select:focus-visible,.pcontrols button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.pcontrols .hint{font-size:12.5px;color:var(--ink2);flex-basis:100%}
.pgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,380px),1fr));gap:18px}
.pcell{min-width:0;display:flex;flex-direction:column;gap:10px}
#subplan{width:100%;max-width:520px;height:auto;touch-action:none;background:var(--paper2);border:1px solid var(--ink3)}
#subchart{width:100%;height:auto;background:var(--paper2);border:1px solid var(--ink3)}
.pmetrics{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--ink3);border:1px solid var(--ink3)}
.pmetrics div{background:var(--paper);padding:8px 10px;display:flex;flex-direction:column;gap:2px}
.pmetrics .k{font-family:var(--f-mono);font-size:10.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--ink2)}
.pmetrics .v{font-family:var(--f-display);font-size:20px;font-weight:600;font-variant-numeric:tabular-nums}
.pmetrics .bad{color:var(--no)} .pmetrics .good{color:var(--ok)}
#subplan .subrect{fill:var(--sub);stroke:var(--ink);stroke-width:.25;cursor:grab}
#subplan .subrect.bad{fill:var(--no)}
#subplan .subrect:focus{outline:none;stroke:var(--accent);stroke-width:.6}
#subplan .wallln{fill:none;stroke:var(--ink);stroke-width:.5}
#subplan .occ{fill:var(--accent);opacity:.9} #subplan .door{fill:var(--paper2);stroke:var(--ink2);stroke-width:.25}
#subplan .seatpt{fill:var(--accent)} #subplan .scr{stroke:var(--ink);stroke-width:.6}
#subplan text,#subchart text{font-family:var(--f-mono);fill:var(--ink2)}
#subchart .grid{stroke:var(--ink3);stroke-width:.6;opacity:.5} #subchart .seatc{fill:none;stroke:var(--zone);stroke-width:1;opacity:.55}
#subchart .rspc{fill:none;stroke:var(--accent);stroke-width:2.2}
table.opt th[scope=row]{color:var(--ink2);font-family:var(--f-mono);font-size:11px;text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
table.opt td,table.opt th{white-space:normal;min-width:150px}
table.opt .cur{background:rgba(255,209,102,.08)}
table.plist td:first-child,table.plist td:last-child{font-family:var(--f-mono);font-variant-numeric:tabular-nums;white-space:nowrap}
table.plist td:last-child{text-align:right}
@media print{#subplan,#subchart{background:#fff} .pcontrols{display:none}}
"""

PLANNER_JS = r"""
<script>
(function(){
  var el=document.getElementById('subdata'); if(!el) return;
  var D=JSON.parse(el.textContent), W=D.W, L=D.L, H=D.H, c=D.c;
  var svg=document.getElementById('subplan'), chart=document.getElementById('subchart'), met=document.getElementById('submetrics');
  var sel=document.getElementById('sublayout'), reset=document.getElementById('subreset');
  var NS='http://www.w3.org/2000/svg', pad=4, sc=Math.min((100-2*pad)/W,(100-2*pad)/L);
  svg.setAttribute('viewBox','0 0 '+(W*sc+2*pad).toFixed(2)+' '+(L*sc+2*pad).toFixed(2));
  function X(x){return pad+x*sc} function Y(y){return pad+y*sc}
  // modes
  var modes=[], delta=6.91/D.T60;
  for(var nx=0;nx<9;nx++)for(var ny=0;ny<11;ny++)for(var nz=0;nz<5;nz++){
    var f=c/2*Math.sqrt(Math.pow(nx/W,2)+Math.pow(ny/L,2)+Math.pow(nz/H,2)); if(f>250)continue;
    modes.push([nx,ny,nz,2*Math.PI*f,(nx?0.5:1)*(ny?0.5:1)*(nz?0.5:1)]);}
  var freqs=[]; for(var i=0;i<=Math.round(24*Math.log2(120/20));i++)freqs.push(20*Math.pow(2,i/24));
  function psi(m,r){return Math.cos(m[0]*Math.PI*r[0]/W)*Math.cos(m[1]*Math.PI*r[1]/L)*Math.cos(m[2]*Math.PI*r[2]/H)}
  function press(srcs,r,f){var w=2*Math.PI*f,re=0,im=0;
    for(var k=0;k<modes.length;k++){var m=modes[k],s=0;for(var j=0;j<srcs.length;j++)s+=psi(m,srcs[j]);
      var a=s*psi(m,r)/m[4], dr=m[3]*m[3]-w*w, di=2*delta*w, dd=dr*dr+di*di; re+=a*dr/dd; im+=-a*di/dd;}
    return Math.sqrt(re*re+im*im);}
  function db(x){return 20*Math.log10(x)}
  function span(wall){return (wall==='front'||wall==='back')?W:L}
  function pos(u){var z=D.sub.zc; if(u[0]==='front')return[u[1],0,z]; if(u[0]==='back')return[u[1],L,z]; if(u[0]==='left')return[0,u[1],z]; return[W,u[1],z];}
  var units=[];
  function load(id){var lay=D.layouts.filter(function(l){return l.id===id})[0]; if(lay)units=lay.units.map(function(u){return[u[0],u[1]]});}
  function conflicts(){var out=[];units.forEach(function(u,i){var bad=[];
      D.occupied.forEach(function(o){ if(o[0]!==u[0])return;
        if(Math.abs(o[1]-u[1])<(o[3]+D.sub.w)/2+0.05 && Math.abs(o[2]-D.sub.zc)<(o[4]+D.sub.h)/2+0.05) bad.push(o[5]);});
      units.forEach(function(v,j){ if(j!==i&&v[0]===u[0]&&Math.abs(v[1]-u[1])<D.sub.w+0.05) bad.push('SW'+(j+1));});
      out.push(bad);});return out;}
  function draw(){
    while(svg.firstChild)svg.removeChild(svg.firstChild);
    function mk(t,a){var n=document.createElementNS(NS,t);for(var k in a)n.setAttribute(k,a[k]);svg.appendChild(n);return n;}
    mk('rect',{x:X(0),y:Y(0),width:W*sc,height:L*sc,'class':'wallln'});
    mk('line',{x1:X(D.screen[0]),y1:Y(D.screen[2]),x2:X(D.screen[1]),y2:Y(D.screen[2]),'class':'scr'});
    var t=mk('text',{x:X(W/2),y:Y(D.screen[2])+3.2,'text-anchor':'middle','font-size':2.2}); t.textContent='SCREEN';
    mk('rect',{x:X(D.door[0]),y:Y(L)-0.6,width:D.door[1]*sc,height:1.2,'class':'door'});
    D.occupied.forEach(function(o){ if(o[5]==='door')return; var w=o[3]*sc;
      if(o[0]==='front')mk('rect',{x:X(o[1])-w/2,y:Y(0)-0.6,width:w,height:1.2,'class':'occ'});
      if(o[0]==='back')mk('rect',{x:X(o[1])-w/2,y:Y(L)-0.6,width:w,height:1.2,'class':'occ'});
      if(o[0]==='left')mk('rect',{x:X(0)-0.6,y:Y(o[1])-w/2,width:1.2,height:w,'class':'occ'});
      if(o[0]==='right')mk('rect',{x:X(W)-0.6,y:Y(o[1])-w/2,width:1.2,height:w,'class':'occ'});});
    D.ears.forEach(function(e,i){mk('circle',{cx:X(e[0]),cy:Y(e[1]),r:0.9,'class':'seatpt'});});
    var cf=conflicts();
    units.forEach(function(u,i){var w=D.sub.w*sc, d=2.4, r;
      var cls='subrect'+(cf[i].length?' bad':'');
      if(u[0]==='front')r=mk('rect',{x:X(u[1])-w/2,y:Y(0)-d/2,width:w,height:d});
      else if(u[0]==='back')r=mk('rect',{x:X(u[1])-w/2,y:Y(L)-d/2,width:w,height:d});
      else if(u[0]==='left')r=mk('rect',{x:X(0)-d/2,y:Y(u[1])-w/2,width:d,height:w});
      else r=mk('rect',{x:X(W)-d/2,y:Y(u[1])-w/2,width:d,height:w});
      r.setAttribute('class',cls); r.setAttribute('tabindex','0'); r.setAttribute('role','button');
      r.setAttribute('aria-label','Subwoofer '+(i+1)+' on '+u[0]+' wall at '+u[1].toFixed(2)+' m'+(cf[i].length?', conflicts with '+cf[i].join(', '):''));
      r.dataset.i=i;
      var lab=mk('text',{x:(u[0]==='left'?X(0)+3:u[0]==='right'?X(W)-3:X(u[1])),y:(u[0]==='front'?Y(0)+4.5:u[0]==='back'?Y(L)-3:Y(u[1])+0.8),
        'text-anchor':(u[0]==='left'?'start':u[0]==='right'?'end':'middle'),'font-size':2.4}); lab.textContent='SW'+(i+1);});
  }
  function evaluate(){
    var srcs=[]; units.forEach(function(u){var p=pos(u); srcs.push([p[0],p[1],0.15+D.sub.h*0.25],[p[0],p[1],0.15+D.sub.h*0.75]);});
    var curves=D.ears.map(function(){return[]}), rspc=[], sds=[];
    freqs.forEach(function(f){var lv=D.ears.map(function(e){return db(press(srcs,e,f))});
      lv.forEach(function(v,i){curves[i].push(v)}); rspc.push(db(press(srcs,D.rsp,f)));
      if(f<=100){var m=lv.reduce(function(a,b){return a+b},0)/lv.length; sds.push(Math.sqrt(lv.reduce(function(a,b){return a+(b-m)*(b-m)},0)/lv.length));}});
    var amp=0; units.forEach(function(u){var p=pos(u),d=Math.max(Math.hypot(p[0]-D.rsp[0],p[1]-D.rsp[1],p[2]-D.rsp[2]),0.5); amp+=Math.pow(10,(D.sub.lmax-db(d))/20);});
    var mean=sds.reduce(function(a,b){return a+b},0)/sds.length, mx=Math.max.apply(null,sds), cf=conflicts(), nbad=cf.filter(function(x){return x.length}).length;
    met.innerHTML='<div><span class="k">Mean seat SD</span><span class="v '+(mean<3.2?'good':mean>4.5?'bad':'')+'">'+mean.toFixed(2)+' dB</span></div>'+
      '<div><span class="k">Worst-frequency SD</span><span class="v">'+mx.toFixed(1)+' dB</span></div>'+
      '<div><span class="k">Est. max LFE at RSP</span><span class="v">'+(units.length?db(amp).toFixed(1):'-')+' dB</span></div>'+
      '<div><span class="k">'+units.length+' x '+D.sub.model+'</span><span class="v '+(nbad?'bad':'good')+'">'+(nbad?nbad+' conflict'+(nbad>1?'s':''):'Fits')+'</span></div>';
    // chart
    while(chart.firstChild)chart.removeChild(chart.firstChild);
    var x0=46,x1=508,y0=14,y1=268, all=[].concat.apply(rspc,curves), mxl=Math.max.apply(null,all), top=Math.ceil(mxl/5)*5, bot=top-40;
    function cx(f){return x0+(Math.log(f/20)/Math.log(120/20))*(x1-x0)} function cy(v){return y0+(top-Math.max(bot,Math.min(top,v)))/(top-bot)*(y1-y0)}
    function mk(t,a,txt){var n=document.createElementNS(NS,t);for(var k in a)n.setAttribute(k,a[k]);if(txt)n.textContent=txt;chart.appendChild(n);return n;}
    [20,30,40,50,60,80,100,120].forEach(function(f){mk('line',{x1:cx(f),y1:y0,x2:cx(f),y2:y1,'class':'grid'});mk('text',{x:cx(f),y:y1+16,'text-anchor':'middle','font-size':11},f+'');});
    for(var v=bot;v<=top;v+=10){mk('line',{x1:x0,y1:cy(v),x2:x1,y2:cy(v),'class':'grid'});mk('text',{x:x0-6,y:cy(v)+4,'text-anchor':'end','font-size':11},(v-top)+'');}
    mk('text',{x:x1,y:y1+30,'text-anchor':'end','font-size':11},'Hz');
    mk('text',{x:x0+6,y:y0+12,'text-anchor':'start','font-size':11},'dB re max');
    function path(arr){return arr.map(function(v,i){return(i?'L':'M')+cx(freqs[i]).toFixed(1)+' '+cy(v).toFixed(1)}).join(' ')}
    curves.forEach(function(cv){mk('path',{d:path(cv),'class':'seatc'})});
    mk('path',{d:path(rspc),'class':'rspc'});
  }
  var drag=null;
  function toRoom(ev){var pt=svg.createSVGPoint(); pt.x=ev.clientX; pt.y=ev.clientY; var p=pt.matrixTransform(svg.getScreenCTM().inverse()); return[(p.x-pad)/sc,(p.y-pad)/sc];}
  function snap(xy){var x=Math.max(0,Math.min(W,xy[0])), y=Math.max(0,Math.min(L,xy[1]));
    var d={front:y,back:L-y,left:x,right:W-x}, wall=Object.keys(d).sort(function(a,b){return d[a]-d[b]})[0];
    var u=(wall==='front'||wall==='back')?x:y, half=D.sub.w/2; u=Math.max(half,Math.min(span(wall)-half,u)); return[wall,Math.round(u*100)/100];}
  var pending=false; function later(){ if(pending)return; pending=true; requestAnimationFrame(function(){pending=false; evaluate();}); }
  svg.addEventListener('pointerdown',function(ev){var t=ev.target; if(!t.dataset||t.dataset.i===undefined)return; drag=+t.dataset.i; svg.setPointerCapture(ev.pointerId); ev.preventDefault();});
  svg.addEventListener('pointermove',function(ev){ if(drag===null)return; units[drag]=snap(toRoom(ev)); sel.value='custom'; draw(); later();});
  svg.addEventListener('pointerup',function(ev){ if(drag===null)return; var i=drag; drag=null; draw(); evaluate(); var n=svg.querySelector('[data-i="'+i+'"]'); if(n)n.focus();});
  svg.addEventListener('keydown',function(ev){var t=ev.target; if(!t.dataset||t.dataset.i===undefined)return; var i=+t.dataset.i, u=units[i], step=0.1;
    var k=ev.key, dir=0; if(k==='ArrowRight'||k==='ArrowDown')dir=1; else if(k==='ArrowLeft'||k==='ArrowUp')dir=-1; else return;
    ev.preventDefault(); var half=D.sub.w/2; u[1]=Math.round(Math.max(half,Math.min(span(u[0])-half,u[1]+dir*step))*100)/100; sel.value='custom';
    draw(); evaluate(); var n=svg.querySelector('[data-i="'+i+'"]'); if(n)n.focus();});
  sel.addEventListener('change',function(){ if(sel.value==='custom')return; load(sel.value); draw(); evaluate();});
  reset.addEventListener('click',function(){ sel.value=D.chosen; load(D.chosen); draw(); evaluate();});
  load(D.chosen); draw(); evaluate();
})();
</script>
"""


CSS = r"""
:root{
  --paper:#0f3a5f; --paper2:#0c3354; --ink:#e9f2fb; --ink2:#a9c4de; --ink3:#6f93b6;
  --accent:#ffd166; --sub:#ff9f6e; --ok:#9ee6b0; --no:#ff8f8f; --zone:#7fd1ff;
  --f-display:"Barlow Condensed","Arial Narrow","Helvetica Neue",Arial,sans-serif;
  --f-body:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
  --f-mono:"IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace;
  color-scheme: dark;
}
/* Single deliberate look: blueprint on screen, black-on-white in print. */
body{background:var(--paper2);color:var(--ink);font-family:var(--f-body);margin:0;
  padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));padding-block:20px 48px}
.wrap{max-width:1500px;margin:0 auto;display:flex;flex-direction:column;gap:28px}
.topbar{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:baseline;justify-content:space-between}
.topbar h1{font-family:var(--f-display);font-weight:600;letter-spacing:.04em;font-size:clamp(22px,3vw,32px);margin:0;text-wrap:balance}
.topbar nav{display:flex;flex-wrap:wrap;gap:6px}
.topbar nav a{font-family:var(--f-mono);font-size:12px;color:var(--ink);text-decoration:none;border:1px solid var(--ink3);padding:4px 8px;border-radius:2px}
.topbar nav a:hover,.topbar nav a:focus-visible{background:var(--ink);color:var(--paper);outline:none}
.sheet{background:var(--paper);border:1px solid var(--ink3);box-shadow:0 1px 0 rgba(0,0,0,.25)}
.svgwrap{overflow-x:auto}
.svgwrap svg{display:block;width:100%;min-width:900px;height:auto}
svg text{font-family:var(--f-mono);fill:var(--ink)}
.paper{fill:var(--paper)} .paperfill{fill:var(--paper);stroke:none}
.frame{fill:none;stroke:var(--ink);stroke-width:3} .frame2{fill:none;stroke:var(--ink);stroke-width:1.4} .frame3{stroke:var(--ink3);stroke-width:.8}
.brand{font-family:var(--f-display);font-size:58px;font-weight:700;letter-spacing:.12em}
.tbs{font-size:10px;fill:var(--ink2);letter-spacing:.14em}
.tbk{font-size:10px;fill:var(--ink2);letter-spacing:.12em} .tbv{font-size:13px}
.tbtitle{font-family:var(--f-display);font-size:23px;font-weight:600;letter-spacing:.03em}
.sheetno{font-family:var(--f-display);font-size:64px;font-weight:700}
.stamp{fill:none;stroke:var(--accent);stroke-width:2;stroke-dasharray:6 3}
.stampt{font-family:var(--f-display);font-size:22px;font-weight:700;fill:var(--accent);letter-spacing:.08em}
.stampt2{font-size:11px;fill:var(--accent);letter-spacing:.14em}
.ln{fill:none;stroke:var(--ink);stroke-width:2} .ln2{fill:none;stroke:var(--ink);stroke-width:1.6}
.thin{fill:none;stroke:var(--ink2);stroke-width:1}
.wall{fill:url(#hatch);stroke:var(--ink);stroke-width:1.6} .hatchln{stroke:var(--ink2);stroke-width:1.2}
.hid{fill:none;stroke:var(--ink2);stroke-width:1.2;stroke-dasharray:7 5}
.ext{stroke:var(--ink2);stroke-width:.8} .dim{stroke:var(--ink2);stroke-width:.9} .tick{stroke:var(--ink);stroke-width:1.4}
.dimt{font-size:12.5px;fill:var(--ink)} .t{font-size:12px}
.small{font-size:12px;fill:var(--ink)} .tiny{font-size:10.5px;fill:var(--ink2)} .note{font-size:12px;fill:var(--ink)}
.mono{font-size:11.5px;fill:var(--ink);white-space:pre}
.h3{font-family:var(--f-display);font-size:19px;font-weight:600;letter-spacing:.08em}
.screen{fill:var(--ink);stroke:var(--ink)} .screenln{stroke:var(--ink);stroke-width:5}
.seat{fill:none;stroke:var(--ink);stroke-width:1.5} .arm{fill:var(--ink3);stroke:var(--ink);stroke-width:.8}
.seatback{fill:none;stroke:var(--ink);stroke-width:4;stroke-linecap:round}
.seatt{font-size:12px;font-weight:600;fill:var(--ink)}
.ghost{fill:none;stroke:var(--ink3);stroke-width:1;stroke-dasharray:3 3}
.earpt{fill:var(--accent);stroke:none} .eyept{fill:var(--accent)}
.head{fill:none;stroke:var(--ink);stroke-width:1.6}
.riser{fill:url(#dots);stroke:var(--ink2);stroke-width:1} .dotfill{fill:var(--ink3)}
.spk{fill:var(--accent);stroke:var(--ink);stroke-width:1.2} .spkghost{fill:none;stroke:var(--ink3);stroke-width:1}
.spkabove{fill:none;stroke:var(--accent);stroke-width:1.8;stroke-dasharray:5 3}
.hidspk{fill:none;stroke:var(--accent);stroke-width:2;stroke-dasharray:8 4}
.sub{fill:var(--sub);stroke:var(--ink);stroke-width:1.2}
.tag{fill:var(--paper);stroke:var(--accent);stroke-width:1.6} .tagabove{fill:var(--paper);stroke:var(--accent);stroke-width:1.4;stroke-dasharray:4 2}
.tagsub{fill:var(--paper);stroke:var(--sub);stroke-width:1.6}
.tagt{font-size:12px;font-weight:600;fill:var(--ink)}
.rsp{fill:none;stroke:var(--accent);stroke-width:2} .rspl{stroke:var(--accent);stroke-width:1.4} .rspt{font-size:12px;font-weight:700;fill:var(--accent)}
.ray{stroke:var(--accent);stroke-width:.9;stroke-dasharray:2 4;opacity:.85} .ray2{stroke:var(--zone);stroke-width:.9;stroke-dasharray:2 4}
.zone{fill:var(--zone);fill-opacity:.12;stroke:var(--zone);stroke-width:1.4;stroke-dasharray:6 3}
.trap{fill:var(--ink3);fill-opacity:.45;stroke:var(--ink2);stroke-width:1} .trapel{fill:var(--ink3);fill-opacity:.25;stroke:var(--ink2);stroke-width:1;stroke-dasharray:4 3}
.proj{fill:none;stroke:var(--ink);stroke-width:1.8} .beam{stroke:var(--zone);stroke-width:1.2;stroke-dasharray:10 4}
.fabric{fill:var(--ink3);fill-opacity:.10;stroke:none} .frameblk{fill:var(--paper2);stroke:var(--ink);stroke-width:1.4}
.image{fill:var(--ink);fill-opacity:.10;stroke:var(--ink);stroke-width:1.6}
.ref{stroke:var(--ink3);stroke-width:1;stroke-dasharray:12 4 2 4}
.sight{stroke:var(--accent);stroke-width:1.6} .leader{stroke:var(--ink2);stroke-width:.8}
.stand{stroke:var(--no);stroke-width:2;stroke-dasharray:4 3}
/* document sheets */
.doc{padding:22px clamp(16px,2.5vw,32px) 18px;display:flex;flex-direction:column;gap:16px}
.dochead{display:flex;flex-wrap:wrap;align-items:center;gap:12px 20px;border-bottom:2px solid var(--ink);padding-bottom:10px}
.docbrand{font-family:var(--f-display);font-size:34px;font-weight:700;letter-spacing:.12em}
.docmeta{display:flex;flex-direction:column;gap:2px;font-family:var(--f-mono);font-size:12px;color:var(--ink2);flex:1;min-width:0}
.docno{display:flex;flex-direction:column;align-items:flex-end}
.docno .k{font-family:var(--f-mono);font-size:10px;letter-spacing:.14em;color:var(--ink2)}
.docno .n{font-family:var(--f-display);font-size:36px;font-weight:700;line-height:1}
.doctitle{font-family:var(--f-display);font-weight:600;font-size:clamp(20px,2.4vw,28px);letter-spacing:.04em;margin:0;text-wrap:balance}
.g2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,420px),1fr));gap:18px 28px}
.cell{min-width:0;display:flex;flex-direction:column;gap:8px} .cell.wide{grid-column:1/-1}
.cell h3{font-family:var(--f-display);font-weight:600;font-size:18px;letter-spacing:.08em;text-transform:uppercase;margin:0;color:var(--ink)}
.tw{overflow-x:auto;border:1px solid var(--ink3)}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th{font-family:var(--f-mono);font-weight:500;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink2);text-align:left;padding:6px 8px;border-bottom:1px solid var(--ink3);white-space:nowrap}
td{padding:5px 8px;border-bottom:1px solid rgba(169,196,222,.18);vertical-align:top}
table.num td{font-family:var(--f-mono);font-variant-numeric:tabular-nums;white-space:nowrap}
.comp .ok{color:var(--ok)} .comp .no{color:var(--no)}
.fine{font-size:12px;color:var(--ink2);margin:0;line-height:1.5;max-width:110ch}
.flags{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:6px;font-size:13.5px;line-height:1.45}
.flags li::marker{color:var(--accent)}
.docfoot{font-family:var(--f-mono);font-size:11px;color:var(--ink3);border-top:1px solid var(--ink3);padding-top:8px}
.coverhero{display:flex;flex-direction:column;gap:12px;padding-block:12px 6px}
.eyebrow{font-family:var(--f-mono);font-size:12px;letter-spacing:.18em;text-transform:uppercase;color:var(--accent)}
.coverhero h1{font-family:var(--f-display);font-weight:700;font-size:clamp(34px,6vw,64px);letter-spacing:.02em;line-height:1;margin:0;text-wrap:balance}
.lede{font-size:16px;line-height:1.55;color:var(--ink2);max-width:65ch;margin:0}
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--ink3);border:1px solid var(--ink3);margin-top:8px}
.fact{background:var(--paper);padding:10px 12px;display:flex;flex-direction:column;gap:3px}
.fact .k{font-family:var(--f-mono);font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink2)}
.fact .v{font-family:var(--f-display);font-size:20px;font-weight:600;letter-spacing:.02em}
.index{list-style:none;margin:0;padding:0;display:flex;flex-direction:column}
.index a{display:flex;gap:16px;padding:7px 0;border-bottom:1px solid rgba(169,196,222,.2);color:var(--ink);text-decoration:none;font-size:14px}
.index a span{font-family:var(--f-mono);color:var(--accent);min-width:64px}
.index a:hover span,.index a:focus-visible span{text-decoration:underline}
.basis{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:6px;font-size:13.5px;line-height:1.5;color:var(--ink)}
@media (max-width:720px){.facts{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (prefers-reduced-motion: reduce){*{transition:none!important}}
@media print{
  :root{--paper:#fff;--paper2:#fff;--ink:#111;--ink2:#444;--ink3:#888;--accent:#111;--sub:#555;--ok:#111;--no:#b00;--zone:#333;color-scheme:light}
  @page{size:17in 11in;margin:0}
  body{padding:0;background:#fff}
  .wrap{gap:0;max-width:none} .topbar{display:none}
  .sheet{border:none;box-shadow:none;width:17in;height:11in;overflow:hidden;break-after:page;page-break-after:always}
  .sheet.doc{height:auto;min-height:11in;overflow:visible}
  .tw{overflow:visible} .cell{break-inside:avoid}
  .svgwrap{overflow:visible} .svgwrap svg{width:17in;height:11in;min-width:0}
  .doc{padding:.45in .55in;box-sizing:border-box} table{font-size:9.5px} td{padding:2.5px 6px} th{padding:4px 6px;font-size:8.5px}
  .spk{fill:#fff} .sub{fill:#ccc} .fine{font-size:9.5px} .flags{font-size:10.5px}
}
"""


def main():
    sheets = [cover()]
    for fn in (sheet_a101, sheet_a102, sheet_a201, sheet_a202, sheet_a301):
        sh = fn()
        sheets.append(f'<section class="sheet" id="{sh.number.lower()}"><div class="svgwrap">{sh.svg()}</div></section>')
    sheets.append(sheet_av501())
    sheets.append(sheet_av601())
    sheets.append(sheet_av602())
    sheets.append(sheet_av701())
    nav = "".join(f'<a href="#{n.lower()}">{n}</a>' for n, _ in SHEET_INDEX)
    doc = (f'<title>JBL 24x18 Theater Drawings</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n'
           f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
           f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500&display=swap">'
           f'<style>{CSS}{CSS2}</style>\n<div class="wrap"><div class="topbar"><h1>JBL Synthesis Theater, 24 × 18: concept drawing set</h1>'
           f'<nav aria-label="Sheets">{nav}</nav></div>{"".join(sheets)}</div>')
    doc += PLANNER_JS
    out = os.path.join(HERE, "out", "drawing-set.html")
    with open(out, "w") as f:
        f.write(doc)
    print("wrote", out, len(doc), "bytes")


if __name__ == "__main__":
    main()
