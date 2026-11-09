#!/usr/bin/env python3
"""
CHT prototype: JBL Synthesis theater in a 24 ft x 18 ft room.

Computes the full design (seating, screen, projector, speaker placement by
search, subwoofer configuration by modal analysis, acoustics, SPL/amplifier,
cabling, BOM) and writes out/design.json, which drawings.py turns into the
drawing set. Pure standard library and deterministic. Formula IDs (A2, B4, C3,
D3...) refer to docs/theater-design-platform/03-phase3-calculation-catalog.md.

Coordinates (m): origin = front-left floor corner seen from the seats;
x across width, y from screen wall to back wall, z up. Azimuth 0 = toward screen.

Run: python3 -I design.py
"""
import json
import math
import os

FT, IN = 0.3048, 0.0254
C = 343.0

# ---------------------------------------------------------------------------
# PROJECT INPUTS (every value here is an input or a labelled assumption)
# ---------------------------------------------------------------------------
P = {
    "project": "CHT Theater Concept: JBL Synthesis 24 x 18",
    "project_no": "CHT-P-0002",
    "revision": "A (concept)",
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
    "projector": {"model": "JVC DLA-NZ8 (example)", "lumens": 2500, "tr_min": 1.43, "tr_max": 2.92,
                  "vshift_pct": 80, "hshift_pct": 34, "k_cal": 0.65, "body_depth": 0.50,
                  "note": "Throw-ratio range differs between published sources; verify with JVC calculator."},
    "c_sound": C,
}

# Product catalog subset (published data; see sources in design.json / docs Phase 3 Sec. 8)
CAT = {
    "SCL-2": {"brand": "JBL Synthesis", "desc": "2.5-way dual 8in in-wall LCR", "sens": 92, "z": 6, "pmax": 445,
              "pmax_kind": "rated RMS (CEA-426B)", "grille_wh": (0.326, 1.022), "depth": 0.147,
              "min_wall": "2x6 (>=152 mm cavity)", "src": "jblsynthesis.com SCL-2 page / owner's manual"},
    "SCL-3": {"brand": "JBL Synthesis", "desc": "2-way dual 5.25in in-wall (surround / Atmos ceiling)", "sens": 91,
              "z": 6, "pmax": 300, "pmax_kind": "max recommended amp power (US sheet; 200 W on some sheets)",
              "grille_wh": (0.25, 0.42), "depth": 0.09, "min_wall": "2x4", "dims_status": "grille size ASSUMED - verify",
              "src": "Harman SCL-3 spec sheet TR02315 V7"},
    "SCL-5": {"brand": "JBL Synthesis", "desc": "2-way 7in in-ceiling (alternate for tops)", "sens": 86, "z": 6,
              "pmax": 125, "pmax_kind": "max recommended amp power", "src": "JBL SCL-5 quick specs SC03921"},
    "SSW-3": {"brand": "JBL Synthesis", "desc": "dual 10in passive in-wall subwoofer", "sens": 88, "z": 4, "pmax": 600,
              "pmax_kind": "system power handling RMS", "grille_wh": (0.394, 1.676), "depth": 0.130,
              "min_wall": "2x6", "fr": "20-150 Hz (-6 dB)", "src": "JBL SSW-3 quick specs SC02547 / owner's manual"},
    "SDP-58": {"brand": "JBL Synthesis", "desc": "16-channel immersive processor", "outputs": 16,
               "src": "JBL SDP-58 spec sheet V2"},
    "SDA-7120": {"brand": "JBL Synthesis", "desc": "7-ch Class G amplifier", "ch": 7, "w8": 100, "w4": 140,
                 "src": "jblsynthesis.com SDA-7120 page (all channels driven)"},
}

# Dolby home placement windows (commonly cited; verify against current Dolby guideline)
WIN = {"L": ("az", 22, 30), "R": ("az", 22, 30), "C": None,
       "Lss": ("az", 90, 110), "Rss": ("az", 90, 110), "Lrs": ("az", 135, 150), "Rrs": ("az", 135, 150),
       "Ltf": ("el", 30, 55), "Rtf": ("el", 30, 55), "Ltm": ("el", 65, 100), "Rtm": ("el", 65, 100),
       "Ltr": ("el", 30, 55), "Rtr": ("el", 30, 55)}

W, L, H = P["room"]["width_ft"] * FT, P["room"]["length_ft"] * FT, P["room"]["height_ft"] * FT


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
    # elevation > 90 deg means "overhead and behind" (used for top-middle window)
    if dy > 0 and abs(el) > 0:
        el_over = 180 - el if el > 0 else el
    else:
        el_over = el
    return az, el, mag((dx, dy, dz)), el_over


def in_window(ch, lis, spk):
    if WIN[ch] is None:
        return True, abs(az_el(lis, spk)[0])
    kind, lo, hi = WIN[ch]
    az, el, d, el_over = az_el(lis, spk)
    if kind == "az":
        v = abs(az)
    elif ch[1:3] == "tm":
        v = el_over
    else:
        v = el
    ok = lo - 0.5 <= v <= hi + 0.5
    if ch[1:3] == "tf" and spk[1] >= lis[1]:
        ok = False
    if ch[1:3] == "tr" and spk[1] <= lis[1]:
        ok = False
    return ok, v


def db(x):
    return 20 * math.log10(x)


def ftin(m, frac=4):
    """metres -> architectural feet-inches string, rounded to 1/frac inch."""
    neg = m < 0
    tot = round(abs(m) / IN * frac) / frac
    ft = int(tot // 12)
    inch = tot - ft * 12
    whole = int(inch)
    f = inch - whole
    fs = ""
    if f > 1e-9:
        n = round(f * frac)
        d = frac
        while n % 2 == 0 and d > 1:
            n //= 2
            d //= 2
        fs = f" {n}/{d}"
    s = f"{ft}'-{whole}{fs}\""
    return ("-" if neg else "") + s


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


def modal_pressure(srcs, rcv, f, mode_list, delta):  # B8
    w = 2 * math.pi * f
    tot = 0j
    for nx, ny, nz, wn, lam in mode_list:
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


# ---------------------------------------------------------------------------
# DESIGN
# ---------------------------------------------------------------------------
def build():
    warn = []
    S = P["seating"]
    sc = P["screen"]
    R = {"inputs": P, "catalog": CAT, "room": {}, "warnings": warn}

    # Room ---------------------------------------------------------------- B1
    V = W * L * H
    Stot = 2 * (W * L + W * H + L * H)
    R["room"] = {"W": W, "L": L, "H": H, "V": V, "S": Stot, "V_ft3": V / FT ** 3,
                 "ratio": [1, round(W / H, 3), round(L / H, 3)]}

    # Screen ------------------------------------------------------------- D1
    diag = sc["diag_in"] * IN
    sw = diag * sc["aspect"] / math.hypot(sc["aspect"], 1)
    sh = sw / sc["aspect"]
    zb = sc["bottom_z"]
    ys = sc["plane_y"]
    scr = {"w": sw, "h": sh, "x0": W / 2 - sw / 2, "x1": W / 2 + sw / 2, "zb": zb, "zt": zb + sh, "y": ys,
           "area_m2": sw * sh, "area_ft2": sw * sh / FT ** 2}
    if H - scr["zt"] < 0.15:
        warn.append("Less than 150 mm above image for masking/border.")
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
    if riser_back < y2 + S["seat_back"] + 0.30:
        warn.append("Less than 300 mm of riser behind row-2 seat backs.")
    if xs[-1] + S["pitch"] / 2 > riser_x1:
        warn.append("Row-2 seats overhang the riser edge at the right aisle.")
    head_std = H - riser
    if head_std < 2.03:
        warn.append(f"Headroom on riser {ftin(head_std)} (< 6'-8\"); check code and soffits.")
    R["seating"] = {"y1": y1, "y2": y2, "riser_req": riser_req, "riser": riser, "riser_front": riser_front,
                    "riser_x1": riser_x1, "riser_back": riser_back, "walkway": walkway, "seats": seats, "rsp": rsp, "xs": xs,
                    "eye2_req": eye2_req}

    # Viewing angles ------------------------------------------------------ D2
    va = []
    for s in seats:
        d = s["y"] - ys
        ex, _, ez = s["eye"]
        hva = math.degrees(math.atan2(scr["x1"] - ex, d) - math.atan2(scr["x0"] - ex, d))
        va.append({"seat": s["id"], "dist": d, "hva": hva,
                   "v_top": math.degrees(math.atan((scr["zt"] - ez) / d)),
                   "v_bot": math.degrees(math.atan((zb - ez) / d)),
                   "off": math.degrees(math.atan(abs(ex - W / 2) / d))})
    R["viewing"] = va
    if max(v["v_top"] for v in va) > 15.5:
        warn.append(f"Front-row vertical angle to image top {max(v['v_top'] for v in va):.1f} deg (>15 deg guidance [verify]).")
    pix = sw / 3840
    R["acuity_4k_m"] = pix / math.tan(math.radians(1 / 60))

    # Projector ---------------------------------------------------------- D5-D8
    pj = P["projector"]
    th_min, th_max = pj["tr_min"] * sw, pj["tr_max"] * sw
    centre_z = zb + sh / 2
    lens_z_max_shift = centre_z + 0.75 * sh  # hold shift at <=75% (margin to the +/-80% limit)
    lens_z = min(H - 0.20, lens_z_max_shift)
    lens_y = min(L - pj["body_depth"] - 0.15, ys + th_max)
    lens_y = max(lens_y, ys + th_min)
    throw = lens_y - ys
    shift = (lens_z - centre_z) / sh * 100
    beam = {}
    for nm, yy, fl in (("row1", y1, 0.0), ("row2", y2, riser)):
        zbeam = zb + (lens_z - zb) * (yy - ys) / throw
        beam[nm] = {"beam_bottom": zbeam, "head_seated": fl + S["eye"] + 0.13, "standing_1800": fl + 1.80,
                    "standing_blocks": fl + 1.80 > zbeam}
    if beam["row2"]["standing_blocks"]:
        warn.append(f"Standing 1.80 m person on riser reaches {beam['row2']['standing_1800']:.2f} m; beam bottom "
                    f"there {beam['row2']['beam_bottom']:.2f} m -> casts shadow when standing.")
    lum = []
    for k_cal, g in ((pj["k_cal"], sc["gain"]), (0.45, sc["gain"]), (pj["k_cal"], 0.85)):
        fl_ = pj["lumens"] * k_cal * g / scr["area_ft2"]
        lum.append({"k": k_cal, "gain": g, "fL": fl_, "nits": fl_ * 3.426})
    R["projector"] = {"lens": (W / 2, lens_y, lens_z), "throw": throw, "tr": throw / sw, "th_range": (th_min, th_max),
                      "shift_pct": shift, "beam": beam, "lum": lum,
                      "tr_ok": pj["tr_min"] <= throw / sw <= pj["tr_max"], "shift_ok": abs(shift) <= pj["vshift_pct"]}

    # Speaker placement search ------------------------------------------- A4/A5
    ears = [s["ear"] for s in seats]
    weights = [1.0 if s["row"] == 1 else 0.9 for s in seats]
    z_lcr = 1.17

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

    door = P["door"]
    CORNER = 0.60  # min distance from a wall-mounted speaker centre to a room corner (traps, boundary)
    NEAR = 0.60    # min horizontal distance from a ceiling speaker to any ear

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

    def best(ch, cands):
        cands = [p_ for p_ in cands if allowed(p_) and allowed(mirror(p_))]
        return max(cands, key=lambda p: score(ch, p))

    spk = {}
    # L/R behind AT front wall (full-width AT fabric wall assumed)
    lat = best("L", [(W / 2 - u / 100, 0.0, z_lcr) for u in range(120, 245, 1)])
    spk["L"] = lat
    spk["R"] = (W - lat[0], 0.0, z_lcr)
    spk["C"] = (W / 2, 0.0, z_lcr)
    z_s = 1.90
    spk["Lss"] = best("Lss", [(0.0, y / 100, z_s) for y in range(int(y1 * 100) - 60, int(y2 * 100) + 60, 2)])
    spk["Rss"] = (W, spk["Lss"][1], z_s)
    rear_c = [(0.0, y / 100, z_s) for y in range(int(y2 * 100), int((L - 0.30) * 100), 2)]
    rear_c += [(x / 100, L, z_s) for x in range(30, int(W / 2 * 100) - 30, 2)]
    spk["Lrs"] = best("Lrs", rear_c)
    spk["Rrs"] = mirror(spk["Lrs"])

    layouts = {}
    for name, tops in (("7.2.4", ["tf", "tr"]), ("7.2.6", ["tf", "tm", "tr"])):
        lay = dict(spk)
        for t in tops:
            ch = "L" + t
            cands = [(W / 2 - u / 100, y / 100, H) for u in range(80, 200, 5)
                     for y in range(40, int((L - 0.4) * 100), 5)]
            p_ = best(ch, cands)
            lay[ch] = p_
            lay["R" + t] = (W - p_[0], p_[1], H)
        tot = sum(1 for ch in lay if ch != "C" for _ in ears)
        hits = sum(in_window(ch, e, p_)[0] for ch, p_ in lay.items() if ch != "C" for e in ears)
        layouts[name] = {"speakers": lay, "hits": hits, "total": tot}
    pick = "7.2.6" if (layouts["7.2.6"]["hits"] / layouts["7.2.6"]["total"]
                       - layouts["7.2.4"]["hits"] / layouts["7.2.4"]["total"]) >= 0.05 else "7.2.4"
    lay = layouts[pick]["speakers"]
    R["layout_compare"] = {k: {"hits": v["hits"], "total": v["total"],
                               "pct": 100 * v["hits"] / v["total"]} for k, v in layouts.items()}
    R["layout"] = pick

    # Per-channel table
    model_of = {"L": "SCL-2", "C": "SCL-2", "R": "SCL-2"}
    for ch in lay:
        model_of.setdefault(ch, "SCL-3")
    mount_of = lambda ch, p_: ("Front wall, behind AT screen/fabric" if p_[1] == 0.0 else
                               "Ceiling" if p_[2] >= H - 1e-6 else
                               "Left wall" if p_[0] == 0.0 else "Right wall" if p_[0] >= W - 1e-6 else "Back wall")
    order = ["L", "C", "R", "Lss", "Rss", "Lrs", "Rrs", "Ltf", "Rtf", "Ltm", "Rtm", "Ltr", "Rtr"]
    chans = []
    for ch in [c for c in order if c in lay]:
        p_ = lay[ch]
        az, el, d, _ = az_el(rsp, p_)
        per = []
        for s in seats:
            ok, v = in_window(ch, s["ear"], p_)
            a2, e2, d2, _ = az_el(s["ear"], p_)
            per.append({"seat": s["id"], "ok": ok, "val": v, "az": a2, "el": e2, "d": d2})
        aim_t = (W / 2, (y1 + y2) / 2, (S["ear"] + riser / 2 + S["ear"]) / 2)
        if p_[2] >= H - 1e-6:
            v_ = sub(aim_t, p_)
            aim = {"yaw": math.degrees(math.atan2(v_[0], -v_[1])), "tilt": math.degrees(math.atan2(-v_[2], math.hypot(v_[0], v_[1])))}
        else:
            aim = None
        chans.append({"ch": ch, "model": model_of[ch], "pos": p_, "mount": mount_of(ch, p_), "az": az, "el": el,
                      "d": d, "window": WIN[ch], "seats": per, "hits": sum(x["ok"] for x in per), "aim": aim})
    R["channels"] = chans
    if pick == "7.2.6":
        warn.append("Placement search: 7.2.6 improves seat compliance by >=5 points over 7.2.4 -> 7.2.6 selected.")

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
                if not (0 < t < 1):
                    continue
                pt = [img[i] + t * (e[i] - img[i]) for i in range(3)]
                zones[wall].append(pt)
    tz = {}
    for wall, pts in zones.items():
        if wall == "ceiling":
            xs_ = [p_[0] for p_ in pts]
            ys_ = [p_[1] for p_ in pts]
            tz[wall] = {"x0": min(xs_) - 0.3, "x1": max(xs_) + 0.3, "y0": min(ys_) - 0.3, "y1": max(ys_) + 0.3}
        else:
            ys_ = [p_[1] for p_ in pts]
            zs_ = [p_[2] for p_ in pts]
            tz[wall] = {"y0": max(0.0, min(ys_) - 0.45), "y1": max(ys_) + 0.45,
                        "z0": max(0.30, min(zs_) - 0.60), "z1": min(H - 0.15, max(zs_) + 0.60)}
    tz["ceiling"]["x0"] = max(tz["ceiling"]["x0"], 0.3)
    tz["ceiling"]["x1"] = min(tz["ceiling"]["x1"], W - 0.3)
    R["reflection_points"] = {k: [[round(c, 3) for c in p_] for p_ in v] for k, v in zones.items()}
    R["treatment_zones"] = tz

    # Subwoofers (B8, C8) --------------------------------------------------
    sub_w, sub_h = CAT["SSW-3"]["grille_wh"]
    occupied = []
    for c_ in chans:
        p_ = c_["pos"]
        gw, gh = CAT[c_["model"]].get("grille_wh", (0.3, 0.4))
        if c_["mount"].startswith("Front"):
            occupied.append(("front", p_[0], p_[2], gw, gh))
        elif c_["mount"] == "Left wall":
            occupied.append(("left", p_[1], p_[2], gw, gh))
        elif c_["mount"] == "Right wall":
            occupied.append(("right", p_[1], p_[2], gw, gh))
        elif c_["mount"] == "Back wall":
            occupied.append(("back", p_[0], p_[2], gw, gh))
    d0 = P["door"]
    occupied.append(("back", d0["x0"] + d0["width"] / 2, 1.05, d0["width"] + 0.15, 2.10))
    zc = 0.15 + sub_h / 2

    def unit(wall, u):
        if wall == "front":
            pos = (u, 0.0, zc)
        elif wall == "back":
            pos = (u, L, zc)
        elif wall == "left":
            pos = (0.0, u, zc)
        else:
            pos = (W, u, zc)
        return {"wall": wall, "u": u, "pos": pos, "rect": (wall, u, zc, sub_w, sub_h)}

    cL = lay["L"][0]
    between = (cL + W / 2) / 2
    cfgs = {
        "2x front wall, between C and L/R": [unit("front", between), unit("front", W - between)],
        "2x side-wall midpoints": [unit("left", L / 2), unit("right", L / 2)],
        "2x front corners": [unit("front", 0.30), unit("front", W - 0.30)],
        "4x front (between C-L/R) + back wall": [unit("front", between), unit("front", W - between),
                                                  unit("back", between), unit("back", W - between)],
        "4x corners": [unit("front", 0.30), unit("front", W - 0.30), unit("back", 0.30), unit("back", W - 0.30)],
        "4x side walls at 1/4 and 3/4 length": [unit("left", L / 4), unit("left", 3 * L / 4),
                                                 unit("right", L / 4), unit("right", 3 * L / 4)],
        "4x wall midpoints (front pair split around C)": [unit("front", between), unit("front", W - between),
                                                           unit("left", L / 2), unit("right", L / 2)],
    }
    T60_LF = 0.40
    delta = 6.91 / T60_LF
    ml = []
    for nx in range(0, 9):
        for ny in range(0, 11):
            for nz in range(0, 5):
                f = C / 2 * math.sqrt((nx / W) ** 2 + (ny / L) ** 2 + (nz / H) ** 2)
                if f <= 250:
                    lam = (1 if nx == 0 else .5) * (1 if ny == 0 else .5) * (1 if nz == 0 else .5)
                    ml.append((nx, ny, nz, 2 * math.pi * f, lam))
    freqs = [20 * 2 ** (i / 24) for i in range(0, int(24 * math.log2(100 / 20)) + 1)]
    sens_u = CAT["SSW-3"]["sens"]
    pref_u = 2.83 ** 2 / CAT["SSW-3"]["z"]
    lmax_1m = sens_u + 10 * math.log10(CAT["SSW-3"]["pmax"] / pref_u)
    sub_res = []
    for name, units in cfgs.items():
        feasible = not any(rect_overlap(u["rect"], o) for u in units for o in occupied)
        srcs = []
        for u in units:
            x_, y_, _ = u["pos"]
            srcs += [(x_, y_, 0.15 + sub_h * 0.25), (x_, y_, 0.15 + sub_h * 0.75)]
        sds, rsp_curve = [], []
        for f in freqs:
            lv = [db(modal_pressure(srcs, e, f, ml, delta)) for e in ears]
            m = sum(lv) / len(lv)
            sds.append(math.sqrt(sum((x - m) ** 2 for x in lv) / len(lv)))
            rsp_curve.append(db(modal_pressure(srcs, rsp, f, ml, delta)))
        amp = sum(10 ** ((lmax_1m - db(max(mag(sub(rsp, u["pos"])), 0.5))) / 20) for u in units)
        spl_ff = db(amp)
        sub_res.append({"name": name, "n": len(units), "feasible": feasible, "mean_sd": sum(sds) / len(sds),
                        "max_sd": max(sds), "rsp_range": max(rsp_curve) - min(rsp_curve),
                        "spl_max_ff": spl_ff, "units": [u["pos"] for u in units], "walls": [u["wall"] for u in units]})
    lfe = P["target"]["lfe"]
    feas = [s_ for s_ in sub_res if s_["feasible"]]
    meeting = [s_ for s_ in feas if s_["spl_max_ff"] >= lfe - 3]  # allow 3 dB modest LF room gain
    pool = meeting or feas
    chosen = min(pool, key=lambda s_: s_["mean_sd"] + 0.4 * s_["n"])
    R["subs"] = {"options": sub_res, "chosen": chosen["name"], "T60_LF": T60_LF, "lmax_1m_unit": lmax_1m,
                 "rule": "Feasible (no wall conflicts) and within 3 dB of LFE target free-field; then lowest "
                         "(mean seat SD + 0.4 dB per enclosure)."}
    if chosen["spl_max_ff"] < lfe:
        warn.append(f"Subwoofers: est. free-field max {chosen['spl_max_ff']:.1f} dB vs LFE target {lfe:.0f} dB; "
                    f"relies on low-frequency room gain (not modelled). Confirm with JBL CTA-2010 data.")

    # Acoustics (B2-B5) ---------------------------------------------------
    md = modes(200)
    coinc = []
    ax = [m_ for m_ in md if m_["type"] == "axial" and m_["f"] < 150]
    for i in range(len(ax)):
        for j in range(i + 1, len(ax)):
            if abs(ax[i]["f"] - ax[j]["f"]) / ax[i]["f"] < 0.02 and ax[i]["n"] != ax[j]["n"]:
                coinc.append((ax[i]["f"], ax[i]["n"], ax[j]["n"]))
    bands = [125, 250, 500, 1000, 2000, 4000]
    A = {"gyp": [0.29, 0.10, 0.05, 0.04, 0.07, 0.09], "carpet": [0.08, 0.24, 0.57, 0.69, 0.71, 0.73],
         "fg2": [0.17, 0.86, 1.14, 1.07, 1.02, 0.98], "fg1": [0.11, 0.28, 0.68, 0.90, 0.93, 0.96], "fg4trap": [0.80, 1.00, 1.00, 1.00, 1.00, 1.00],
         "at_wall": [0.40, 0.90, 1.00, 1.00, 1.00, 1.00], "seat": [0.35, 0.45, 0.57, 0.61, 0.59, 0.55],
         "diffusor": [0.15, 0.22, 0.28, 0.30, 0.30, 0.30]}
    side_panel = sum((tz[w]["y1"] - tz[w]["y0"]) * (tz[w]["z1"] - tz[w]["z0"]) for w in ("left", "right"))
    cloud = (tz["ceiling"]["x1"] - tz["ceiling"]["x0"]) * (tz["ceiling"]["y1"] - tz["ceiling"]["y0"])
    rear_panel = 0.5 * W * H
    traps = 4 * 0.6 * H  # 4 corner traps, 600 mm face
    front = W * H
    walls_total = 2 * W * H + 2 * L * H
    gyp_walls = walls_total - side_panel - rear_panel - traps - front
    seats_n = len(seats)

    def rt(surfs, extra_sabins=None):
        out = []
        for i in range(6):
            Aa = sum(a * A[m_][i] for a, m_ in surfs)
            if extra_sabins:
                Aa += extra_sabins[i]
            abar = min(Aa / Stot, 0.99)
            out.append({"band": bands[i], "abar": abar, "sabine": 0.161 * V / Aa,
                        "eyring": 0.161 * V / (-Stot * math.log(1 - abar))})
        return out
    seat_sab = [seats_n * 0.5 * a for a in A["seat"]]  # ~0.5 m2 face per seat (illustrative)
    untreated = rt([(W * L, "carpet"), (W * L, "gyp"), (walls_total, "gyp")], seat_sab)
    treated = rt([(W * L, "carpet"), (W * L - cloud, "gyp"), (cloud, "fg1"), (gyp_walls, "gyp"),
                  (side_panel, "fg1"), (rear_panel, "diffusor"), (traps, "fg4trap"), (front, "at_wall")], seat_sab)
    tm = 0.25 * (V / 100) ** (1 / 3)
    R["acoustics"] = {"modes": md[:40], "axial": ax, "coincidences": coinc, "n_below_100": sum(1 for m_ in md if m_["f"] < 100),
                      "rt_untreated": untreated, "rt_treated": treated, "tm_ref": tm,
                      "schroeder_0p3": 2000 * math.sqrt(0.3 / V),
                      "areas": {"side_panels": side_panel, "cloud": cloud, "rear": rear_panel, "corner_traps": traps,
                                "front_at_wall": front},
                      "absorption_note": "Coefficients are illustrative typical values; replace with tested ISO 354 / ASTM C423 product data."}
    mid = (treated[2]["eyring"] + treated[3]["eyring"]) / 2
    if mid < 0.75 * tm:
        warn.append(f"Treated mid-band RT60 {mid:.2f} s is well below the ~{tm:.2f} s small-room reference: risk of an "
                    f"over-damped room. Trade some absorption for diffusion (e.g. rear half of side zones).")
    if treated[0]["eyring"] > 1.8 * mid:
        warn.append(f"125 Hz RT60 {treated[0]['eyring']:.2f} s vs mid-band {mid:.2f} s: add low-frequency "
                    f"absorption (membrane/pressure traps) beyond the 4 corner traps.")
    for c_ in coinc:
        warn.append(f"Axial mode coincidence near {c_[0]:.1f} Hz: {c_[1]} and {c_[2]} (L/W ratio).")

    # SPL / power (C1-C5) -------------------------------------------------
    Sa = treated[3]["abar"]
    Rr = Stot * Sa / (1 - Sa)
    Q = P["target"]["Q_assumed"]
    tgt, mar = P["target"]["peak_per_channel"], P["target"]["margin"]
    amp6 = (CAT["SDA-7120"]["w8"] + CAT["SDA-7120"]["w4"]) / 2  # 6-ohm interpolation (assumption)
    spl = []
    for c_ in chans:
        m_ = CAT[c_["model"]]
        pref = 2.83 ** 2 / m_["z"]
        d = c_["d"]
        preq = pref * 10 ** ((tgt + mar - m_["sens"] + db(d)) / 10)
        cap_spk = m_["sens"] + 10 * math.log10(m_["pmax"] / pref) - db(d)
        cap_amp = m_["sens"] + 10 * math.log10(min(m_["pmax"], amp6) / pref) - db(d)
        rg = 10 * math.log10((1 / d ** 2 + 16 * math.pi / (Q * Rr)) / (1 / d ** 2))
        spl.append({"ch": c_["ch"], "model": c_["model"], "d": d, "p_req": preq, "cap_spk_ff": cap_spk,
                    "cap_amp_ff": cap_amp, "room_gain": rg, "cap_spk_room": cap_spk + rg, "cap_amp_room": cap_amp + rg})
    R["spl"] = {"rows": spl, "R_room": Rr, "Q": Q, "amp_6ohm_assumed": amp6, "target": tgt, "margin": mar}
    short = [s_["ch"] for s_ in spl if s_["cap_amp_room"] < tgt]
    worst = min(s_["cap_amp_room"] for s_ in spl)
    R["spl"]["achievable_with_sda7120"] = worst
    R["spl"]["power_for_reference"] = max(s_["p_req"] for s_ in spl)
    if short:
        warn.append(f"Level: SDA-7120 (~{amp6:.0f} W @ 6 ohm, assumed) gives est. {worst:.1f}-"
                    f"{max(s_['cap_amp_room'] for s_ in spl):.1f} dB peaks at the RSP: meets reference -5 dB, not full "
                    f"reference. Full 105 dB + 3 dB margin needs up to {R['spl']['power_for_reference']:.0f} W/ch "
                    f"(free-field basis) on {', '.join(short)}.")

    # Channels / amps / processor (C11) ------------------------------------
    n_full = len(chans)
    n_sub_units = chosen["n"]
    sub_outputs = 2 if n_sub_units >= 2 else 1
    proc_out = n_full + sub_outputs
    R["system"] = {"full_range": n_full, "sub_units": n_sub_units, "sub_outputs": sub_outputs,
                   "proc_outputs_used": proc_out, "proc_capacity": CAT["SDP-58"]["outputs"],
                   "proc_ok": proc_out <= CAT["SDP-58"]["outputs"],
                   "amp_units": math.ceil(n_full / 7), "amp_spare": math.ceil(n_full / 7) * 7 - n_full}
    if not R["system"]["proc_ok"]:
        warn.append("Processor output count exceeded.")
    amap = []
    for i, c_ in enumerate(chans):
        amap.append({"ch": c_["ch"], "amp": f"AMP-{i // 7 + 1} (SDA-7120)", "out": i % 7 + 1})
    for j in range(n_sub_units):
        amap.append({"ch": f"SW{j+1}", "amp": f"AMP-S{j // 2 + 1} (sub amp, model TBD)", "out": j % 2 + 1})
    R["amp_map"] = amap

    # Cables (C12) ------------------------------------------------------
    rack = P["rack"]["entry"]
    awg = [(14, 0.00829), (12, 0.00521), (10, 0.00328)]
    cables = []
    items = [(c_["ch"], c_["pos"], CAT[c_["model"]]["z"]) for c_ in chans]
    items += [(f"SW{j+1}", chosen["units"][j], CAT["SSW-3"]["z"]) for j in range(n_sub_units)]
    for ch, p_, z in items:
        run = (H - p_[2]) + abs(p_[0] - rack[0]) + abs(p_[1] - rack[1]) + 1.5 + 2.0
        zmin = 0.8 * z
        g = next(((a, r) for a, r in awg if 2 * run * r <= 0.05 * zmin), awg[-1])
        loss = db(z / (z + 2 * run * g[1]))
        cables.append({"ch": ch, "run_m": run, "awg": g[0], "loop_ohm": 2 * run * g[1], "loss_db": loss})
    R["cables"] = cables

    # BOM ---------------------------------------------------------------
    from collections import Counter
    cnt = Counter(c_["model"] for c_ in chans)
    bom = [{"qty": cnt["SCL-2"], "item": "JBL Synthesis SCL-2", "desc": CAT["SCL-2"]["desc"], "use": "L / C / R"},
           {"qty": cnt["SCL-3"], "item": "JBL Synthesis SCL-3",
            "desc": CAT["SCL-3"]["desc"], "use": "Surrounds + overhead (verify ceiling-mount approval)"},
           {"qty": n_sub_units, "item": "JBL Synthesis SSW-3", "desc": CAT["SSW-3"]["desc"], "use": "Subwoofers"},
           {"qty": 1, "item": "JBL Synthesis SDP-58", "desc": CAT["SDP-58"]["desc"], "use": "Processor"},
           {"qty": R["system"]["amp_units"], "item": "JBL Synthesis SDA-7120", "desc": CAT["SDA-7120"]["desc"],
            "use": "Full-range amplification (see SPL notes)"},
           {"qty": math.ceil(n_sub_units / 2), "item": "Subwoofer amplifier (TBD)",
            "desc": f">= {CAT['SSW-3']['pmax']} W @ 4 ohm per channel, 2 ch", "use": "SSW-3 x " + str(n_sub_units)},
           {"qty": 1, "item": P["projector"]["model"], "desc": "Laser D-ILA projector", "use": "Video"},
           {"qty": 1, "item": f"{sc['diag_in']}in {sc['aspect_label']} AT screen (model TBD)",
            "desc": f"{ftin(sw)} x {ftin(sh)} image, gain {sc['gain']}", "use": "Video"},
           {"qty": 8, "item": "Theater recliner (model TBD)", "desc": f"{S['pitch']*1000:.0f} mm pitch", "use": "Seating"}]
    R["bom"] = bom
    return R


def main():
    R = build()
    os.makedirs(os.path.join(os.path.dirname(__file__) or ".", "out"), exist_ok=True)
    path = os.path.join(os.path.dirname(__file__) or ".", "out", "design.json")
    with open(path, "w") as f:
        json.dump(R, f, indent=1, default=lambda o: list(o) if isinstance(o, tuple) else str(o))
    s = R["seating"]
    print(f"Layout {R['layout']}  compare {R['layout_compare']}")
    print(f"Screen {R['screen']['w']:.3f} x {R['screen']['h']:.3f}  riser {ftin(s['riser'])} (req {s['riser_req']:.3f})  walkway {s['walkway']:.2f}")
    for c_ in R["channels"]:
        print(f"  {c_['ch']:4} {c_['model']:6} {c_['mount']:34} x={ftin(c_['pos'][0]):>10} y={ftin(c_['pos'][1]):>10} "
              f"z={ftin(c_['pos'][2]):>9}  az {c_['az']:6.1f} el {c_['el']:5.1f} d {c_['d']:.2f}  seats {c_['hits']}/8")
    print("Subs:")
    for o in R["subs"]["options"]:
        print(f"  {o['name']:46} feas={o['feasible']!s:5} meanSD {o['mean_sd']:.2f} maxSD {o['max_sd']:.1f} SPLff {o['spl_max_ff']:.1f}")
    print("  chosen:", R["subs"]["chosen"])
    pj = R["projector"]
    print(f"Projector lens y={pj['lens'][1]:.2f} z={pj['lens'][2]:.2f} TR {pj['tr']:.2f} shift {pj['shift_pct']:.0f}% beam {pj['beam']}")
    for r in R["spl"]["rows"]:
        print(f"  SPL {r['ch']:4} req {r['p_req']:6.0f} W  spk ff {r['cap_spk_ff']:.1f} room {r['cap_spk_room']:.1f}  w/ amp room {r['cap_amp_room']:.1f}")
    print("RT treated:", [round(b["eyring"], 2) for b in R["acoustics"]["rt_treated"]],
          "untreated:", [round(b["eyring"], 2) for b in R["acoustics"]["rt_untreated"]])
    print("Viewing:", [(v["seat"], round(v["hva"], 1), round(v["v_top"], 1)) for v in R["viewing"]])
    print("System:", R["system"])
    print("Cables:", [(c_["ch"], round(c_["run_m"], 1), c_["awg"]) for c_ in R["cables"]])
    print("WARNINGS:")
    for w in R["warnings"]:
        print("  -", w)


if __name__ == "__main__":
    main()
