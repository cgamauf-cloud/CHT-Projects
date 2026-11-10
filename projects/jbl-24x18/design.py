#!/usr/bin/env python3
"""
CHT prototype: JBL Synthesis theater in a 24 ft x 18 ft room.

Computes the full concept design for each Good / Better / Best package
(catalog/packages.py): seating and riser, screen, projector, speaker placement
by search, subwoofer layout from a library of common configurations (or one you
choose), acoustics, SPL and amplifier sizing, cabling and the bill of
materials. Writes out/design.json (the package to draw) and out/options.json
(all packages side by side). Pure standard library, deterministic. Formula IDs
(A2, B4, C3, D3...) refer to docs/theater-design-platform/03-phase3-calculation-catalog.md.

Usage:
  python3 -I design.py                       # draw "better", auto subwoofer layout
  python3 -I design.py --tier best           # draw another package
  python3 -I design.py --subs side-quarters  # force a subwoofer layout (see --list-subs)
  python3 -I design.py --list-subs

List prices (MSRP) are attached when private/pricing/savant_price_list.json exists
(created by tools/pricing/import_savant.py). Dealer cost never enters these outputs.

Coordinates (m): origin = front-left floor corner seen from the seats;
x across width, y from screen wall to back wall, z up. Azimuth 0 = toward screen.
"""
import argparse
import json
import math
import os
import sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, ROOT)
from catalog.products import SPEAKERS, SUBS, AMPS, PROCESSORS, PROJECTORS, ACCESSORIES, NOT_ON_SAVANT_LIST  # noqa: E402
from catalog.packages import PACKAGES  # noqa: E402

FT, IN = 0.3048, 0.0254
C = 343.0

# ---------------------------------------------------------------------------
# PROJECT INPUTS (every value here is an input or a labelled assumption)
# ---------------------------------------------------------------------------
P = {
    "project": "CHT Theater Concept: JBL Synthesis 24 x 18",
    "project_no": "CHT-P-0002",
    "revision": "B (concept, Savant-priced packages)",
    "date": "2026-11-09",
    "room": {"length_ft": 24, "width_ft": 18, "height_ft": 9,
             "status": "Concept dimensions (finished interior faces assumed). Ceiling height 9 ft ASSUMED."},
    "screen": {"diag_in": 120, "aspect": 16 / 9, "aspect_label": "16:9", "type": "Fixed-frame acoustically transparent (AT)",
               "gain": 1.0, "plane_y": 0.305, "bottom_z": 0.610},
    "seating": {"rows": 2, "seats_per_row": 4, "pitch": 0.864, "row1_y": 3.75, "row_spacing": 1.90,
                "eye": 1.10, "ear": 1.05, "C_clear": 0.12, "seat_front": 0.75, "seat_back": 0.20,
                "footrest": 0.55, "riser_aisle_right": 0.85, "rear_aisle": 1.00},
    "door": {"wall": "back", "x0": 4.45, "width": 0.914, "swing": "in (into rear cross-aisle)"},
    "rack": {"location": "Equipment room outside back wall (right)", "entry": (6.10, 7.80)},
    "target": {"peak_per_channel": 105.0, "margin": 3.0, "lfe": 115.0, "Q_assumed": 5.0},
    "projector_k_cal": 0.65,
    "subs_custom": None,  # e.g. [("left", 2.0), ("right", 5.3)] -> use with --subs custom
    "c_sound": C,
}

# Dolby home placement windows (commonly cited; verify against current Dolby guideline)
WIN = {"L": ("az", 22, 30), "R": ("az", 22, 30), "C": None,
       "Lss": ("az", 90, 110), "Rss": ("az", 90, 110), "Lrs": ("az", 135, 150), "Rrs": ("az", 135, 150),
       "Ltf": ("el", 30, 55), "Rtf": ("el", 30, 55), "Ltm": ("el", 65, 100), "Rtm": ("el", 65, 100),
       "Ltr": ("el", 30, 55), "Rtr": ("el", 30, 55)}

W, L, H = P["room"]["width_ft"] * FT, P["room"]["length_ft"] * FT, P["room"]["height_ft"] * FT
ORDER = ["L", "C", "R", "Lss", "Rss", "Lrs", "Rrs", "Ltf", "Rtf", "Ltm", "Rtm", "Ltr", "Rtr"]


# ---------------------------------------------------------------------------
# GEOMETRY / CALC HELPERS
# ---------------------------------------------------------------------------
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mag(v):
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def az_el(lis, spk):  # A2
    dx, dy, dz = sub(spk, lis)
    az = math.degrees(math.atan2(dx, -dy))
    el = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    el_over = 180 - el if (dy > 0 and el > 0) else el  # >90 = overhead and behind
    return az, el, mag((dx, dy, dz)), el_over


def in_window(ch, lis, spk):
    if WIN[ch] is None:
        return True, abs(az_el(lis, spk)[0])
    kind, lo, hi = WIN[ch]
    az, el, d, el_over = az_el(lis, spk)
    v = abs(az) if kind == "az" else (el_over if ch[1:3] == "tm" else el)
    ok = lo - 0.5 <= v <= hi + 0.5
    if ch[1:3] == "tf" and spk[1] >= lis[1]:
        ok = False
    if ch[1:3] == "tr" and spk[1] <= lis[1]:
        ok = False
    return ok, v


def db(x):
    return 20 * math.log10(x)


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


def modes(limit=200):  # B2
    out = []
    for nx in range(0, 15):
        for ny in range(0, 15):
            for nz in range(0, 8):
                if nx == ny == nz == 0:
                    continue
                f = C / 2 * math.sqrt((nx / W) ** 2 + (ny / L) ** 2 + (nz / H) ** 2)
                if f <= limit:
                    k = sum(1 for n in (nx, ny, nz) if n)
                    out.append({"f": round(f, 2), "n": [nx, ny, nz], "type": ["", "axial", "tangential", "oblique"][k]})
    return sorted(out, key=lambda m: m["f"])


def mode_list(fmax=250):
    ml = []
    for nx in range(0, 9):
        for ny in range(0, 11):
            for nz in range(0, 5):
                f = C / 2 * math.sqrt((nx / W) ** 2 + (ny / L) ** 2 + (nz / H) ** 2)
                if f <= fmax:
                    lam = (1 if nx == 0 else .5) * (1 if ny == 0 else .5) * (1 if nz == 0 else .5)
                    ml.append((nx, ny, nz, 2 * math.pi * f, lam))
    return ml


def modal_pressure(srcs, rcv, f, ml, delta):  # B8
    w = 2 * math.pi * f
    tot = 0j
    for nx, ny, nz, wn, lam in ml:
        def psi(r):
            return (math.cos(nx * math.pi * r[0] / W) * math.cos(ny * math.pi * r[1] / L)
                    * math.cos(nz * math.pi * r[2] / H))
        tot += sum(psi(s) for s in srcs) * psi(rcv) / (lam * (wn ** 2 - w ** 2 + 2j * delta * w))
    return abs(tot)


def rect_overlap(a, b, gap=0.05):
    """a,b = (wall, u_center, z_center, w, h); u is the in-plane horizontal coordinate."""
    if a[0] != b[0]:
        return False
    return (abs(a[1] - b[1]) < (a[3] + b[3]) / 2 + gap) and (abs(a[2] - b[2]) < (a[4] + b[4]) / 2 + gap)


def amp_power(amp, z):
    """Per-channel power into nominal z, from 8- and 4-ohm ratings (capped at the 4-ohm figure)."""
    a = AMPS[amp]
    return min(a["p4"], a["p8"] * 8 / z)


def load_prices():
    path = os.path.join(ROOT, "private", "pricing", "savant_price_list.json")
    if not os.path.exists(path):
        return None, None
    data = json.load(open(path))
    return {r["sku"]: r for r in data["items"]}, data.get("source")


# ---------------------------------------------------------------------------
# SUBWOOFER LAYOUT LIBRARY
# ---------------------------------------------------------------------------
SUB_LAYOUTS = OrderedDict([
    ("front-pair", "Front wall pair, between C and L/R"),
    ("front-corners", "Front corners"),
    ("rear-corners", "Rear corners"),
    ("side-mid", "Side-wall midpoints"),
    ("front-back-mid", "Front and back wall centres"),
    ("diagonal", "Diagonal corners (front-left + rear-right)"),
    ("diagonal-alt", "Diagonal corners (front-right + rear-left)"),
    ("four-corners", "Four corners"),
    ("four-midwalls", "Four wall midpoints"),
    ("side-quarters", "Side walls at 1/4 and 3/4 length"),
    ("front-back-quarters", "Front and back walls at 1/4 and 3/4 width"),
    ("front-pair-back-pair", "Front pair (between C and L/R) + back wall pair"),
    ("custom", "Custom positions (P['subs_custom'] or the planner)"),
])


def layout_units(lid, lcr_x, sub_w):
    """Return [(wall, u)] for a layout id. u = position along the wall from the front (side walls) or left (front/back)."""
    cu = sub_w / 2 + 0.10  # corner offset
    between = (lcr_x + W / 2) / 2
    lib = {
        "front-pair": [("front", between), ("front", W - between)],
        "front-corners": [("front", cu), ("front", W - cu)],
        "rear-corners": [("back", cu), ("back", W - cu)],
        "side-mid": [("left", L / 2), ("right", L / 2)],
        "front-back-mid": [("front", W / 2), ("back", W / 2)],
        "diagonal": [("front", cu), ("back", W - cu)],
        "diagonal-alt": [("front", W - cu), ("back", cu)],
        "four-corners": [("front", cu), ("front", W - cu), ("back", cu), ("back", W - cu)],
        "four-midwalls": [("front", W / 2), ("back", W / 2), ("left", L / 2), ("right", L / 2)],
        "side-quarters": [("left", L / 4), ("left", 3 * L / 4), ("right", L / 4), ("right", 3 * L / 4)],
        "front-back-quarters": [("front", W / 4), ("front", 3 * W / 4), ("back", W / 4), ("back", 3 * W / 4)],
        "front-pair-back-pair": [("front", between), ("front", W - between), ("back", between), ("back", W - between)],
        "custom": list(P["subs_custom"] or []),
    }
    return lib[lid]


def unit_pos(wall, u, zc):
    return {"front": (u, 0.0, zc), "back": (u, L, zc), "left": (0.0, u, zc), "right": (W, u, zc)}[wall]


# ---------------------------------------------------------------------------
# DESIGN
# ---------------------------------------------------------------------------
def build(tier="better", sub_choice="auto", prices=None):
    warn = []
    pk = PACKAGES[tier]
    S = P["seating"]
    sc = P["screen"]
    R = {"inputs": P, "tier": tier, "package": pk, "room": {}, "warnings": warn}
    models = {"lcr": SPEAKERS[pk["lcr"]], "surround": SPEAKERS[pk["surround"]], "top": SPEAKERS[pk["top"]]}
    R["catalog"] = {pk["lcr"]: models["lcr"], pk["surround"]: models["surround"], pk["top"]: models["top"],
                    pk["sub"]: SUBS[pk["sub"]]}

    # Room ---------------------------------------------------------------- B1
    V = W * L * H
    Stot = 2 * (W * L + W * H + L * H)
    R["room"] = {"W": W, "L": L, "H": H, "V": V, "S": Stot, "V_ft3": V / FT ** 3,
                 "ratio": [1, round(W / H, 3), round(L / H, 3)]}

    # Screen ------------------------------------------------------------- D1
    diag = sc["diag_in"] * IN
    sw = diag * sc["aspect"] / math.hypot(sc["aspect"], 1)
    sh = sw / sc["aspect"]
    zb, ys = sc["bottom_z"], sc["plane_y"]
    scr = {"w": sw, "h": sh, "x0": W / 2 - sw / 2, "x1": W / 2 + sw / 2, "zb": zb, "zt": zb + sh, "y": ys,
           "area_m2": sw * sh, "area_ft2": sw * sh / FT ** 2}
    R["screen"] = scr

    # Seating & riser ---------------------------------------------------- A1/D3
    y1 = S["row1_y"]
    y2 = y1 + S["row_spacing"]
    k = (y2 - ys) / (y1 - ys)
    eye2_req = zb + (S["eye"] + S["C_clear"] - zb) * k
    riser_req = eye2_req - S["eye"]
    riser = math.ceil(riser_req / IN) * IN
    xs = [W / 2 + (i - (S["seats_per_row"] - 1) / 2) * S["pitch"] for i in range(S["seats_per_row"])]
    seats = []
    for r, (yy, fl) in enumerate(((y1, 0.0), (y2, riser))):
        for i, x in enumerate(xs):
            seats.append({"id": f"{r+1}{chr(65+i)}", "row": r + 1, "x": x, "y": yy, "floor": fl,
                          "ear": (x, yy, fl + S["ear"]), "eye": (x, yy, fl + S["eye"])})
    rsp = (W / 2, y1, S["ear"])
    riser_front = y2 - S["seat_front"] - S["footrest"] - 0.05
    walkway = riser_front - (y1 + S["seat_back"])
    if walkway < 0.30:
        warn.append(f"Cross-aisle between row 1 seat backs and riser nosing is {walkway:.2f} m (<0.30 m).")
    riser_x1 = W - S["riser_aisle_right"]
    riser_back = L - S["rear_aisle"]
    R["seating"] = {"y1": y1, "y2": y2, "riser_req": riser_req, "riser": riser, "riser_front": riser_front,
                    "riser_x1": riser_x1, "riser_back": riser_back, "walkway": walkway, "seats": seats, "rsp": rsp,
                    "xs": xs, "eye2_req": eye2_req}

    # Viewing angles ------------------------------------------------------ D2
    va = []
    for s in seats:
        d = s["y"] - ys
        ex, _, ez = s["eye"]
        hva = math.degrees(math.atan2(scr["x1"] - ex, d) - math.atan2(scr["x0"] - ex, d))
        va.append({"seat": s["id"], "dist": d, "hva": hva, "v_top": math.degrees(math.atan((scr["zt"] - ez) / d)),
                   "v_bot": math.degrees(math.atan((zb - ez) / d)), "off": math.degrees(math.atan(abs(ex - W / 2) / d))})
    R["viewing"] = va
    if max(v["v_top"] for v in va) > 15.5:
        warn.append(f"Front-row vertical angle to image top {max(v['v_top'] for v in va):.1f} deg (>15 deg guidance [verify]).")
    R["acuity_4k_m"] = (sw / 3840) / math.tan(math.radians(1 / 60))

    # Projector ---------------------------------------------------------- D5-D8
    pj = PROJECTORS[pk["projector"]]
    th_min, th_max = pj["tr_min"] * sw, pj["tr_max"] * sw
    centre_z = zb + sh / 2
    lens_z = min(H - 0.20, centre_z + (pj["vshift_pct"] - 5) / 100 * sh)
    lens_y = max(min(L - pj["body_depth"] - 0.15, ys + th_max), ys + th_min)
    throw = lens_y - ys
    shift = (lens_z - centre_z) / sh * 100
    beam = {}
    for nm, yy, fl in (("row1", y1, 0.0), ("row2", y2, riser)):
        zbeam = zb + (lens_z - zb) * (yy - ys) / throw
        beam[nm] = {"beam_bottom": zbeam, "head_seated": fl + S["eye"] + 0.13, "standing_1800": fl + 1.80,
                    "standing_blocks": fl + 1.80 > zbeam}
    if lens_y < y2 + 0.4:
        warn.append(f"{pk['projector']}: maximum throw puts the lens at y={lens_y:.2f} m, over/near row 2 "
                    f"(row 2 ear at {y2:.2f} m): check fan noise and head clearance.")
    if beam["row2"]["standing_blocks"]:
        warn.append(f"Standing 1.80 m person on riser reaches {beam['row2']['standing_1800']:.2f} m; beam bottom "
                    f"there {beam['row2']['beam_bottom']:.2f} m -> casts shadow when standing.")
    k_cal = P["projector_k_cal"]
    lum = []
    for kk, g in ((k_cal, sc["gain"]), (0.45, sc["gain"]), (k_cal, 0.85)):
        fl_ = pj["lumens"] * kk * g / scr["area_ft2"]
        lum.append({"k": kk, "gain": g, "fL": fl_, "nits": fl_ * 3.426})
    R["projector"] = {"model": pk["projector"], "spec": pj, "lens": (W / 2, lens_y, lens_z), "throw": throw,
                      "tr": throw / sw, "th_range": (th_min, th_max), "shift_pct": shift, "beam": beam, "lum": lum,
                      "tr_ok": pj["tr_min"] <= throw / sw <= pj["tr_max"] + 1e-9,
                      "shift_ok": abs(shift) <= pj["vshift_pct"]}

    # Speaker placement search ------------------------------------------- A4/A5
    ears = [s["ear"] for s in seats]
    weights = [1.0 if s["row"] == 1 else 0.9 for s in seats]
    z_lcr = 1.17
    door = P["door"]
    CORNER, NEAR = 0.60, 0.60

    def allowed(p_):
        x_, y_, z_ = p_
        if z_ >= H - 1e-6:
            return all(math.hypot(x_ - e[0], y_ - e[1]) >= NEAR for e in ears)
        if y_ in (0.0, L):
            if x_ < CORNER or x_ > W - CORNER:
                return False
            if y_ == L and door["x0"] - 0.25 < x_ < door["x0"] + door["width"] + 0.25:
                return False
            return True
        return CORNER <= y_ <= L - CORNER

    def mirror(p_):
        return (W - p_[0], p_[1], p_[2])

    def score(ch, pos):
        hits, sc_, dev = 0, 0.0, 0.0
        kind, lo, hi = WIN[ch] or ("az", 0, 0)
        mid = (lo + hi) / 2
        for e, w in zip(ears, weights):
            ok, v = in_window(ch, e, pos)
            hits += ok
            sc_ += w * ok
            dev += abs(v - mid) * (1.0 if e[1] == y1 else 0.6)
        return sc_, -dev, hits

    def best(ch, cands):
        cands = [p_ for p_ in cands if allowed(p_) and allowed(mirror(p_))]
        return max(cands, key=lambda p: score(ch, p))

    spk = {}
    lat = best("L", [(W / 2 - u / 100, 0.0, z_lcr) for u in range(120, 245, 1)])
    spk["L"], spk["R"], spk["C"] = lat, mirror(lat), (W / 2, 0.0, z_lcr)
    z_s = 1.90
    spk["Lss"] = best("Lss", [(0.0, y / 100, z_s) for y in range(int(y1 * 100) - 60, int(y2 * 100) + 60, 2)])
    spk["Rss"] = (W, spk["Lss"][1], z_s)
    rear_c = [(0.0, y / 100, z_s) for y in range(int(y2 * 100), int((L - 0.30) * 100), 2)]
    rear_c += [(x / 100, L, z_s) for x in range(30, int(W / 2 * 100) - 30, 2)]
    spk["Lrs"] = best("Lrs", rear_c)
    spk["Rrs"] = mirror(spk["Lrs"]) if spk["Lrs"][1] == L else (W, spk["Lrs"][1], z_s)

    layouts = {}
    for name, tops in (("7.2.4", ["tf", "tr"]), ("7.2.6", ["tf", "tm", "tr"])):
        lay = dict(spk)
        for t in tops:
            ch = "L" + t
            cands = [(W / 2 - u / 100, y / 100, H) for u in range(80, 200, 5) for y in range(40, int((L - 0.4) * 100), 5)]
            p_ = best(ch, cands)
            lay[ch], lay["R" + t] = p_, mirror(p_)
        tot = sum(1 for ch in lay if ch != "C" for _ in ears)
        hits = sum(in_window(ch, e, p_)[0] for ch, p_ in lay.items() if ch != "C" for e in ears)
        layouts[name] = {"speakers": lay, "hits": hits, "total": tot}
    pick = "7.2.6" if (layouts["7.2.6"]["hits"] / layouts["7.2.6"]["total"]
                       - layouts["7.2.4"]["hits"] / layouts["7.2.4"]["total"]) >= 0.05 else "7.2.4"
    lay = layouts[pick]["speakers"]
    R["layout_compare"] = {k_: {"hits": v["hits"], "total": v["total"], "pct": 100 * v["hits"] / v["total"]}
                           for k_, v in layouts.items()}
    R["layout"] = pick

    role_of = lambda ch: "lcr" if ch in ("L", "C", "R") else ("top" if ch[1] == "t" else "surround")
    mount_of = lambda p_: ("Front wall, behind AT screen/fabric" if p_[1] == 0.0 else "Ceiling" if p_[2] >= H - 1e-6
                           else "Left wall" if p_[0] == 0.0 else "Right wall" if p_[0] >= W - 1e-6 else "Back wall")
    chans = []
    aim_t = (W / 2, (y1 + y2) / 2, S["ear"] + riser / 2)
    for ch in [c for c in ORDER if c in lay]:
        p_ = lay[ch]
        az, el, d, _ = az_el(rsp, p_)
        per = []
        for s in seats:
            ok, v = in_window(ch, s["ear"], p_)
            a2, e2, d2, _ = az_el(s["ear"], p_)
            per.append({"seat": s["id"], "ok": ok, "val": v, "az": a2, "el": e2, "d": d2})
        aim = None
        if p_[2] >= H - 1e-6:
            v_ = sub(aim_t, p_)
            aim = {"yaw": math.degrees(math.atan2(v_[0], -v_[1])), "tilt": math.degrees(math.atan2(-v_[2], math.hypot(v_[0], v_[1])))}
        role = role_of(ch)
        chans.append({"ch": ch, "role": role, "model": pk[role], "pos": p_, "mount": mount_of(p_), "az": az, "el": el,
                      "d": d, "window": WIN[ch], "seats": per, "hits": sum(x["ok"] for x in per), "aim": aim})
    R["channels"] = chans

    # Treatment: first reflection zones (B6) ------------------------------
    zones = {"left": [], "right": [], "ceiling": []}
    for ch in ("L", "C", "R"):
        s_ = lay[ch]
        for st in seats:
            e = st["ear"]
            for wall, axis, plane in (("left", 0, 0.0), ("right", 0, W), ("ceiling", 2, H)):
                img = list(s_)
                img[axis] = 2 * plane - s_[axis]
                t = (plane - img[axis]) / (e[axis] - img[axis])
                if 0 < t < 1:
                    zones[wall].append([img[i] + t * (e[i] - img[i]) for i in range(3)])
    tz = {}
    for wall, pts in zones.items():
        if wall == "ceiling":
            tz[wall] = {"x0": max(min(p[0] for p in pts) - 0.3, 0.3), "x1": min(max(p[0] for p in pts) + 0.3, W - 0.3),
                        "y0": min(p[1] for p in pts) - 0.3, "y1": max(p[1] for p in pts) + 0.3}
        else:
            tz[wall] = {"y0": max(0.0, min(p[1] for p in pts) - 0.45), "y1": max(p[1] for p in pts) + 0.45,
                        "z0": max(0.30, min(p[2] for p in pts) - 0.60), "z1": min(H - 0.15, max(p[2] for p in pts) + 0.60)}
    R["reflection_points"] = {k_: [[round(c, 3) for c in p_] for p_ in v] for k_, v in zones.items()}
    R["treatment_zones"] = tz

    # Subwoofers (B8, C8) --------------------------------------------------
    sm = SUBS[pk["sub"]]
    sub_w, sub_h = sm["grille_wh"]
    zc = 0.15 + sub_h / 2
    occupied = []
    for c_ in chans:
        p_ = c_["pos"]
        gw, gh = SPEAKERS[c_["model"]]["grille_wh"]
        wall = {"Front wall, behind AT screen/fabric": "front", "Left wall": "left", "Right wall": "right",
                "Back wall": "back"}.get(c_["mount"])
        if wall:
            u = p_[0] if wall in ("front", "back") else p_[1]
            occupied.append((wall, u, p_[2], gw, gh, c_["ch"]))
    occupied.append(("back", door["x0"] + door["width"] / 2, 1.05, door["width"] + 0.15, 2.10, "door"))
    R["occupied"] = occupied

    # per-enclosure max output at 1 m (C8)
    if "lmax_1m" in sm:
        lmax_1m = sm["lmax_1m"]
        sub_basis = sm["lmax_note"]
    elif "sens_1w" in sm:  # per-woofer data (SSW-1)
        pw = min(sm["pmax_per_woofer"], amp_power(pk["amp_sub"], sm["z_per_woofer"]))
        lmax_1m = sm["sens_1w"] + 10 * math.log10(pw) + db(sm["woofers"])
        sub_basis = f"{sm['sens_1w']} dB/1W/1m per woofer, {pw:.0f} W per woofer ({pk['amp_sub']}), {sm['woofers']} woofers coherent"
    else:
        pw = min(sm["pmax"], amp_power(pk["amp_sub"], sm["z"]))
        lmax_1m = sm["sens"] + 10 * math.log10(pw / (2.83 ** 2 / sm["z"]))
        sub_basis = f"{sm['sens']} dB @2.83 V, {pw:.0f} W ({pk['amp_sub']})"

    ml = mode_list()
    T60_LF = 0.40
    delta = 6.91 / T60_LF
    freqs = [20 * 2 ** (i / 24) for i in range(0, int(24 * math.log2(100 / 20)) + 1)]
    sub_res = []
    for lid, lname in SUB_LAYOUTS.items():
        units = layout_units(lid, lay["L"][0], sub_w)
        if not units:
            continue
        rects = [(w_, u, zc, sub_w, sub_h) for w_, u in units]
        conflicts = sorted({o[5] for r_ in rects for o in occupied if rect_overlap(r_, o[:5])})
        span_ok = all(sub_w / 2 <= u <= (W if w_ in ("front", "back") else L) - sub_w / 2 for w_, u in units)
        feasible = not conflicts and span_ok
        pos = [unit_pos(w_, u, zc) for w_, u in units]
        srcs = []
        for x_, y_, _ in pos:
            srcs += [(x_, y_, 0.15 + sub_h * 0.25), (x_, y_, 0.15 + sub_h * 0.75)]
        sds, rsp_curve = [], []
        for f in freqs:
            lv = [db(modal_pressure(srcs, e, f, ml, delta)) for e in ears]
            m = sum(lv) / len(lv)
            sds.append(math.sqrt(sum((x - m) ** 2 for x in lv) / len(lv)))
            rsp_curve.append(db(modal_pressure(srcs, rsp, f, ml, delta)))
        amp = sum(10 ** ((lmax_1m - db(max(mag(sub(rsp, p_)), 0.5))) / 20) for p_ in pos)
        sub_res.append({"id": lid, "name": lname, "n": len(units), "feasible": feasible, "conflicts": conflicts,
                        "mean_sd": sum(sds) / len(sds), "max_sd": max(sds), "rsp_range": max(rsp_curve) - min(rsp_curve),
                        "spl_max_ff": db(amp), "units": pos, "walls": [w_ for w_, _ in units],
                        "wall_u": [[w_, u] for w_, u in units]})
    lfe = P["target"]["lfe"]
    if sub_choice != "auto":
        chosen = next((o for o in sub_res if o["id"] == sub_choice), None)
        if chosen is None:
            raise SystemExit(f"Unknown or empty subwoofer layout '{sub_choice}'. Use --list-subs.")
        if not chosen["feasible"]:
            warn.append(f"Subwoofer layout '{chosen['name']}' was forced but conflicts with: {', '.join(chosen['conflicts']) or 'wall span'}.")
    else:
        pool = [o for o in sub_res if o["feasible"] and o["n"] == pk["sub_count"]] or [o for o in sub_res if o["feasible"]]
        chosen = min(pool, key=lambda o: o["mean_sd"] + 0.02 * o["max_sd"])
    R["subs"] = {"options": sub_res, "chosen": chosen["name"], "chosen_id": chosen["id"], "T60_LF": T60_LF,
                 "lmax_1m_unit": lmax_1m, "basis": sub_basis, "model": pk["sub"], "grille_wh": [sub_w, sub_h], "zc": zc,
                 "mode": "forced" if sub_choice != "auto" else "auto",
                 "rule": f"Auto: feasible layouts with {pk['sub_count']} enclosures (package default), lowest mean seat-to-seat SD."}
    if chosen["spl_max_ff"] < lfe:
        warn.append(f"Subwoofers ({chosen['n']} x {pk['sub']}): est. free-field max {chosen['spl_max_ff']:.1f} dB vs LFE "
                    f"target {lfe:.0f} dB; relies on low-frequency room gain (not modelled).")

    # Acoustics (B2-B5) ---------------------------------------------------
    md = modes(200)
    ax = [m_ for m_ in md if m_["type"] == "axial" and m_["f"] < 150]
    coinc = [(ax[i]["f"], ax[i]["n"], ax[j]["n"]) for i in range(len(ax)) for j in range(i + 1, len(ax))
             if abs(ax[i]["f"] - ax[j]["f"]) / ax[i]["f"] < 0.02]
    bands = [125, 250, 500, 1000, 2000, 4000]
    A = {"gyp": [0.29, 0.10, 0.05, 0.04, 0.07, 0.09], "carpet": [0.08, 0.24, 0.57, 0.69, 0.71, 0.73],
         "fg1": [0.11, 0.28, 0.68, 0.90, 0.93, 0.96], "fg4trap": [0.80, 1.00, 1.00, 1.00, 1.00, 1.00],
         "at_wall": [0.40, 0.90, 1.00, 1.00, 1.00, 1.00], "seat": [0.35, 0.45, 0.57, 0.61, 0.59, 0.55],
         "diffusor": [0.15, 0.22, 0.28, 0.30, 0.30, 0.30]}
    side_panel = sum((tz[w]["y1"] - tz[w]["y0"]) * (tz[w]["z1"] - tz[w]["z0"]) for w in ("left", "right"))
    cloud = (tz["ceiling"]["x1"] - tz["ceiling"]["x0"]) * (tz["ceiling"]["y1"] - tz["ceiling"]["y0"])
    rear_panel, traps, front = 0.5 * W * H, 4 * 0.6 * H, W * H
    walls_total = 2 * W * H + 2 * L * H
    gyp_walls = walls_total - side_panel - rear_panel - traps - front
    seat_sab = [len(seats) * 0.5 * a for a in A["seat"]]

    def rt(surfs):
        out = []
        for i in range(6):
            Aa = sum(a * A[m_][i] for a, m_ in surfs) + seat_sab[i]
            abar = min(Aa / Stot, 0.99)
            out.append({"band": bands[i], "abar": abar, "sabine": 0.161 * V / Aa,
                        "eyring": 0.161 * V / (-Stot * math.log(1 - abar))})
        return out
    untreated = rt([(W * L, "carpet"), (W * L, "gyp"), (walls_total, "gyp")])
    treated = rt([(W * L, "carpet"), (W * L - cloud, "gyp"), (cloud, "fg1"), (gyp_walls, "gyp"),
                  (side_panel, "fg1"), (rear_panel, "diffusor"), (traps, "fg4trap"), (front, "at_wall")])
    tm = 0.25 * (V / 100) ** (1 / 3)
    R["acoustics"] = {"modes": md[:40], "axial": ax, "coincidences": coinc, "n_below_100": sum(1 for m_ in md if m_["f"] < 100),
                      "rt_untreated": untreated, "rt_treated": treated, "tm_ref": tm, "schroeder_0p3": 2000 * math.sqrt(0.3 / V),
                      "areas": {"side_panels": side_panel, "cloud": cloud, "rear": rear_panel, "corner_traps": traps,
                                "front_at_wall": front},
                      "absorption_note": "Coefficients are illustrative typical values; replace with tested ISO 354 / ASTM C423 product data."}
    mid = (treated[2]["eyring"] + treated[3]["eyring"]) / 2
    if mid < 0.75 * tm:
        warn.append(f"Treated mid-band RT60 {mid:.2f} s is well below the ~{tm:.2f} s small-room reference: risk of an "
                    f"over-damped room. Trade some absorption for diffusion (e.g. rear half of side zones).")
    if treated[0]["eyring"] > 1.8 * mid:
        warn.append(f"125 Hz RT60 {treated[0]['eyring']:.2f} s vs mid-band {mid:.2f} s: add low-frequency absorption.")
    for c_ in coinc:
        warn.append(f"Axial mode coincidence near {c_[0]:.1f} Hz: {c_[1]} and {c_[2]} (room ratios).")

    # SPL / power (C1-C5) -------------------------------------------------
    Sa = treated[3]["abar"]
    Rr = Stot * Sa / (1 - Sa)
    Q = P["target"]["Q_assumed"]
    tgt, mar = P["target"]["peak_per_channel"], P["target"]["margin"]
    spl = []
    for c_ in chans:
        m_ = SPEAKERS[c_["model"]]
        amp = pk["amp_" + c_["role"]]
        pref = 2.83 ** 2 / m_["z"]
        d = c_["d"]
        p_amp = amp_power(amp, m_["z"])
        preq = pref * 10 ** ((tgt + mar - m_["sens"] + db(d)) / 10)
        cap_spk = m_["sens"] + 10 * math.log10(m_["pmax"] / pref) - db(d)
        cap_amp = m_["sens"] + 10 * math.log10(min(m_["pmax"], p_amp) / pref) - db(d)
        rg = 10 * math.log10((1 / d ** 2 + 16 * math.pi / (Q * Rr)) / (1 / d ** 2))
        spl.append({"ch": c_["ch"], "model": c_["model"], "amp": amp, "p_amp": p_amp, "d": d, "p_req": preq,
                    "cap_spk_ff": cap_spk, "cap_amp_ff": cap_amp, "room_gain": rg,
                    "cap_spk_room": cap_spk + rg, "cap_amp_room": cap_amp + rg})
    worst = min(s_["cap_amp_room"] for s_ in spl)
    R["spl"] = {"rows": spl, "R_room": Rr, "Q": Q, "target": tgt, "margin": mar, "achievable": worst,
                "achievable_max": max(s_["cap_amp_room"] for s_ in spl), "power_for_reference": max(s_["p_req"] for s_ in spl)}
    short = [s_["ch"] for s_ in spl if s_["cap_amp_room"] < tgt]
    if short:
        warn.append(f"Level: est. {worst:.1f}-{R['spl']['achievable_max']:.1f} dB peaks at the RSP with this package; "
                    f"below 105 dB reference on {', '.join(short)}.")

    # Channels / amps / processor (C11) ------------------------------------
    n_full = len(chans)
    sub_units = chosen["n"]
    sub_outputs = 2 if sub_units >= 2 else 1
    proc = PROCESSORS[pk["processor"]]
    proc_out = n_full + sub_outputs
    amp_ch = Counter()
    for c_ in chans:
        amp_ch[pk["amp_" + c_["role"]]] += 1
    sub_amp_ch = sub_units * sm["amp_ch"]
    amp_ch[pk["amp_sub"]] += sub_amp_ch
    amp_units = {a: math.ceil(n / AMPS[a]["ch"]) for a, n in amp_ch.items() if "internal" not in a}
    if "SDR-38 (internal)" in amp_ch and amp_ch["SDR-38 (internal)"] > AMPS["SDR-38 (internal)"]["ch"]:
        warn.append("More channels assigned to SDR-38 internal amplification than it has.")
    R["system"] = {"full_range": n_full, "sub_units": sub_units, "sub_outputs": sub_outputs, "processor": pk["processor"],
                   "proc_outputs_used": proc_out, "proc_capacity": proc["outputs"], "proc_ok": proc_out <= proc["outputs"],
                   "amp_channels": dict(amp_ch), "amp_units": amp_units}
    if not R["system"]["proc_ok"]:
        warn.append(f"{pk['processor']}: {proc_out} outputs needed, {proc['outputs']} available.")
    amap, used = [], Counter()
    for c_ in chans:
        a = pk["amp_" + c_["role"]]
        i = used[a]
        used[a] += 1
        amap.append({"ch": c_["ch"], "amp": f"{a} #{i // AMPS[a]['ch'] + 1}", "out": i % AMPS[a]["ch"] + 1})
    for j in range(sub_units):
        a = pk["amp_sub"]
        for w_ in range(sm["amp_ch"]):
            i = used[a]
            used[a] += 1
            lab = f"SW{j+1}" + (f" woofer {w_+1}" if sm["amp_ch"] > 1 else "")
            amap.append({"ch": lab, "amp": f"{a} #{i // AMPS[a]['ch'] + 1}", "out": i % AMPS[a]["ch"] + 1})
    R["amp_map"] = amap

    # Cables (C12) ------------------------------------------------------
    rack = P["rack"]["entry"]
    awg = [(14, 0.00829), (12, 0.00521), (10, 0.00328)]
    cables = []
    items = [(c_["ch"], c_["pos"], SPEAKERS[c_["model"]]["z"]) for c_ in chans]
    zsub = sm.get("z", sm.get("z_per_woofer", 8))
    items += [(f"SW{j+1}", chosen["units"][j], zsub) for j in range(sub_units)]
    for ch, p_, z in items:
        run = (H - p_[2]) + abs(p_[0] - rack[0]) + abs(p_[1] - rack[1]) + 1.5 + 2.0
        g = next(((a, r) for a, r in awg if 2 * run * r <= 0.05 * 0.8 * z), awg[-1])
        cables.append({"ch": ch, "run_m": run, "awg": g[0], "loop_ohm": 2 * run * g[1],
                       "loss_db": db(z / (z + 2 * run * g[1]))})
    R["cables"] = cables

    # BOM -----------------------------------------------------------------
    bom = []

    def add(role, model, sku, desc, qty, note=""):
        if qty:
            bom.append({"role": role, "model": model, "sku": sku, "desc": desc, "qty": qty, "note": note})
    cnt = Counter(c_["model"] for c_ in chans)
    for model, q in cnt.items():
        m_ = SPEAKERS[model]
        roles = sorted({c_["role"] for c_ in chans if c_["model"] == model}, key=["lcr", "surround", "top"].index)
        add("Loudspeakers", model, m_["sku"], m_["desc"], q, " + ".join(r.upper() if r == "lcr" else r for r in roles))
        if m_.get("bracket"):
            add("Brackets", m_["bracket"], m_["bracket"], ACCESSORIES[m_["bracket"]], q)
    add("Subwoofers", pk["sub"], sm["sku"], sm["desc"], sub_units, chosen["name"])
    add("Processing", pk["processor"], proc["sku"], proc["desc"], 1)
    for a, n in amp_units.items():
        add("Amplification", a, AMPS[a]["sku"], AMPS[a]["desc"], n, f"{amp_ch[a]} channels used of {n * AMPS[a]['ch']}")
    add("Video", pk["projector"], pj["sku"], pj["desc"], 1)
    for sku, q in pk["extras"]:
        add("Sources / control / power", sku, sku, ACCESSORIES[sku], q)
    for desc, q in NOT_ON_SAVANT_LIST:
        add("Not on Savant list", "-", None, desc, q, "price separately")
    msrp_total = 0.0
    missing = []
    for b in bom:
        if prices is not None and b["sku"]:
            it = prices.get(b["sku"])
            if it:
                b["msrp"] = it["msrp"]
                b["ext_msrp"] = it["msrp"] * b["qty"]
                b["status"] = it.get("status", "Active")
                msrp_total += b["ext_msrp"]
            else:
                missing.append(b["sku"])
    R["bom"] = bom
    R["msrp_total"] = msrp_total if prices is not None else None
    if missing:
        warn.append(f"SKUs not found on the Savant price list: {', '.join(missing)}.")
    for b in bom:
        if b.get("status") and b["status"] != "Active":
            warn.append(f"{b['sku']}: {b['status']} on the Savant list.")
    return R


def summary(R):
    pk = R["package"]
    ch_sub = next(o for o in R["subs"]["options"] if o["id"] == R["subs"]["chosen_id"])
    return {"tier": R["tier"], "label": pk["label"], "tagline": pk["tagline"],
            "lcr": pk["lcr"], "surround": pk["surround"], "top": pk["top"],
            "sub": f"{ch_sub['n']} x {pk['sub']}", "sub_layout": ch_sub["name"], "processor": pk["processor"],
            "amps": ", ".join(f"{n} x {a}" for a, n in R["system"]["amp_units"].items()),
            "projector": pk["projector"], "spl_low": R["spl"]["achievable"], "spl_high": R["spl"]["achievable_max"],
            "lfe_ff": ch_sub["spl_max_ff"], "sub_sd": ch_sub["mean_sd"], "fL": R["projector"]["lum"][0]["fL"],
            "throw_ok": R["projector"]["tr_ok"], "shift": R["projector"]["shift_pct"],
            "proc": f"{R['system']['proc_outputs_used']}/{R['system']['proc_capacity']}",
            "msrp_total": R["msrp_total"], "bom": R["bom"], "warnings": R["warnings"]}


def jdump(obj, path):
    with open(path, "w") as f:
        json.dump(obj, f, indent=1, default=lambda o: list(o) if isinstance(o, tuple) else str(o))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tier", default="better", choices=list(PACKAGES))
    ap.add_argument("--subs", default="auto", help="subwoofer layout id, 'auto', or 'custom'")
    ap.add_argument("--list-subs", action="store_true")
    a = ap.parse_args()
    if a.list_subs:
        for k_, v in SUB_LAYOUTS.items():
            print(f"  {k_:22} {v}")
        return
    prices, src = load_prices()
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    results = {t: build(t, a.subs if t == a.tier else "auto", prices) for t in PACKAGES}
    R = results[a.tier]
    R["options"] = {t: summary(r) for t, r in results.items()}
    R["price_source"] = src
    jdump(R, os.path.join(HERE, "out", "design.json"))
    jdump({"price_source": src, "packages": R["options"]}, os.path.join(HERE, "out", "options.json"))
    print(f"Drawn package: {a.tier}   layout {R['layout']}   subs: {R['subs']['chosen']} ({R['subs']['mode']})")
    print(f"Prices: {'MSRP from ' + src if src else 'no private price list found (run tools/pricing/import_savant.py)'}")
    for t, s in R["options"].items():
        tot = f"${s['msrp_total']:,.0f}" if s["msrp_total"] is not None else "n/a"
        print(f"  {s['label']:6} {s['lcr']}/{s['surround']}/{s['top']}  {s['sub']:12} {s['processor']:7} {s['amps']:32} "
              f"{s['projector']:13} peaks {s['spl_low']:.1f}-{s['spl_high']:.1f} dB  LFE {s['lfe_ff']:.1f}  "
              f"subSD {s['sub_sd']:.2f}  {s['fL']:.0f} fL  proc {s['proc']}  MSRP {tot}")
    print("Subwoofer layouts for the drawn package:")
    for o in R["subs"]["options"]:
        flag = "*" if o["id"] == R["subs"]["chosen_id"] else " "
        print(f"  {flag} {o['id']:22} n={o['n']} feas={o['feasible']!s:5} meanSD {o['mean_sd']:.2f}  LFE {o['spl_max_ff']:.1f}"
              + (f"  conflicts: {', '.join(o['conflicts'])}" if o["conflicts"] else ""))
    print("WARNINGS (drawn package):")
    for w in R["warnings"]:
        print("  -", w)


if __name__ == "__main__":
    main()
