#!/usr/bin/env python3
"""
Phase 3 worked-example verification script (NOT application code).

Purpose: reproduce every number quoted in 03-phase3-calculation-catalog.md for
the Phase 9 reference project (20 ft x 30 ft x 8 ft basement, Dolby Atmos 7.2.4,
two rows). It doubles as the first set of golden test vectors for the future
calculation engine (NFR-01). Pure standard library; deterministic.

Coordinate system (right-handed, SI units, metres):
  origin = front-left floor corner (looking at the screen from the seats)
  x = across room width (0 .. W), left -> right
  y = from front (screen) wall toward back wall (0 .. L)
  z = up from finished floor (0 .. H)
Azimuth: 0 deg = straight ahead (toward -y), positive = toward listener's right
         when reported as signed; we report |azimuth| 0..180 for compliance.
Elevation: angle above the horizontal plane through the listener's ears.

Run:  python3 -I reference_calcs.py
"""
import cmath
import math

FT = 0.3048
IN = 0.0254
C_SOUND = 343.0  # m/s at ~20 C

# ---------------------------------------------------------------------------
# 1. Room
# ---------------------------------------------------------------------------
W, L, H = 20 * FT, 30 * FT, 8 * FT
V = W * L * H
S_floor = S_ceil = W * L
S_front = S_back = W * H
S_side = L * H
S_total = 2 * S_floor + 2 * S_front + 2 * S_side

# ---------------------------------------------------------------------------
# 2. Seating & video assumptions (concept-level; every one is an input)
# ---------------------------------------------------------------------------
SCREEN_PLANE_Y = 0.30        # AT screen 300 mm in front of the front wall
ROW1_Y, ROW2_Y = 3.80, 5.60  # ear/eye plane of each row (from front wall)
EYE_SEATED = 1.10            # seated eye height above the seat's floor
EAR_SEATED = 1.05            # seated ear height above the seat's floor
HEAD_CLEAR_C = 0.12          # sightline clearance over eye of person in front
SEAT_PITCH = 0.86            # recliner centre-to-centre width
SEATS_PER_ROW = 4
SCREEN_ASPECT = 16 / 9
TARGET_HVA_DEG = 45.0        # target horizontal viewing angle at RSP row
SCREEN_BOTTOM_Z = 0.61       # bottom of image above finished floor


def seats_x():
    n = SEATS_PER_ROW
    return [W / 2 + (i - (n - 1) / 2) * SEAT_PITCH for i in range(n)]


def riser_height_required(z_eye1, y1, y2, zb, ys, c):
    """Minimum row-2 eye height so that the sightline from row-2 eye to the
    image bottom edge clears the row-1 eye by c. Returns row-2 eye height."""
    k = (y2 - ys) / (y1 - ys)
    return zb + (z_eye1 + c - zb) * k


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def vec(a, b):
    return (b[0] - a[0], b[1] - a[1], b[2] - a[2])


def norm(v):
    return math.sqrt(sum(c * c for c in v))


def az_el(listener, spk):
    """Azimuth (deg, 0 = toward screen, + = right) and elevation (deg)."""
    dx, dy, dz = vec(listener, spk)
    fwd = -dy  # toward screen is -y
    az = math.degrees(math.atan2(dx, fwd))
    el = math.degrees(math.atan2(dz, math.hypot(dx, dy)))
    return az, el, norm((dx, dy, dz))


def db(x):
    return 20 * math.log10(x)


def fmt(x, n=1):
    return f"{x:.{n}f}"


def main():
    out = []
    p = out.append

    p("=== 1. ROOM ===")
    p(f"W x L x H = {fmt(W,3)} x {fmt(L,3)} x {fmt(H,3)} m ; V = {fmt(V,1)} m3 "
      f"({fmt(V/FT**3,0)} ft3) ; S_total = {fmt(S_total,1)} m2")
    p(f"Ratios H:W:L = 1 : {fmt(W/H,2)} : {fmt(L/H,2)}")

    # -----------------------------------------------------------------------
    p("\n=== 2. ROOM MODES (rigid-wall rectangular model) ===")
    modes = []
    for nx in range(0, 12):
        for ny in range(0, 12):
            for nz in range(0, 6):
                if nx == ny == nz == 0:
                    continue
                f = C_SOUND / 2 * math.sqrt((nx / W) ** 2 + (ny / L) ** 2 + (nz / H) ** 2)
                kind = {1: "axial", 2: "tangential", 3: "oblique"}[
                    sum(1 for n in (nx, ny, nz) if n)]
                modes.append((f, (nx, ny, nz), kind))
    modes.sort()
    p("First 15 modes (f Hz, (nx,ny,nz) with x=width, y=length, z=height):")
    for f, n, k in modes[:15]:
        p(f"  {fmt(f,1):>6} Hz  {n}  {k}")
    p("Axial modes < 120 Hz:")
    for axis, dim, name in ((0, W, "width"), (1, L, "length"), (2, H, "height")):
        fs = [fmt(n * C_SOUND / (2 * dim), 1) for n in range(1, 20) if n * C_SOUND / (2 * dim) < 120]
        p(f"  {name:6} ({fmt(dim,3)} m): {', '.join(fs)}")
    n_below_100 = sum(1 for m in modes if m[0] < 100)
    p(f"Mode count below 100 Hz: {n_below_100}")

    # -----------------------------------------------------------------------
    p("\n=== 3. RT60 (Sabine / Eyring), illustrative absorption data ===")
    bands = [125, 250, 500, 1000, 2000, 4000]
    a_gyp = [0.29, 0.10, 0.05, 0.04, 0.07, 0.09]       # 1/2" gypsum on studs
    a_carpet = [0.08, 0.24, 0.57, 0.69, 0.71, 0.73]    # heavy carpet on foam pad
    a_fg2 = [0.17, 0.86, 1.14, 1.07, 1.02, 0.98]       # 2" 6 pcf fibreglass, mount A
    wall_area = 2 * S_front + 2 * S_side

    def rt(surfaces):
        res = []
        for i in range(len(bands)):
            A = sum(area * coeffs[i] for area, coeffs in surfaces)
            abar = min(A / S_total, 0.99)
            sab = 0.161 * V / A
            eyr = 0.161 * V / (-S_total * math.log(1 - abar))
            res.append((sab, eyr, abar))
        return res

    untreated = [(S_floor, a_carpet), (S_ceil, a_gyp), (wall_area, a_gyp)]
    treat_area = S_front + 0.35 * (wall_area - S_front)
    treated = [(S_floor, a_carpet), (S_ceil, a_gyp),
               (wall_area - treat_area, a_gyp), (treat_area, a_fg2)]
    for label, surf in (("Untreated (carpet + drywall)", untreated),
                        (f"Treated (front wall + 35% of other walls = {fmt(treat_area,1)} m2 of 2in panel)", treated)):
        p(label)
        for b, (s, e, a) in zip(bands, rt(surf)):
            p(f"  {b:>5} Hz  abar={fmt(a,2)}  Sabine={fmt(s,2)} s  Eyring={fmt(e,2)} s")
    t_target = 0.25 * (V / 100) ** (1 / 3)
    p(f"EBU Tech 3276-style reference Tm = 0.25*(V/100)^(1/3) = {fmt(t_target,2)} s (comparison only)")
    for t in (0.3, 0.5):
        p(f"Schroeder frequency at T60={t}s: fs = 2000*sqrt(T/V) = {fmt(2000*math.sqrt(t/V),0)} Hz")

    # -----------------------------------------------------------------------
    p("\n=== 4. SCREEN, SIGHTLINES, RISER ===")
    d1 = ROW1_Y - SCREEN_PLANE_Y
    d2 = ROW2_Y - SCREEN_PLANE_Y
    sw = 2 * d1 * math.tan(math.radians(TARGET_HVA_DEG / 2))
    sh = sw / SCREEN_ASPECT
    diag = math.hypot(sw, sh)
    top = SCREEN_BOTTOM_Z + sh
    p(f"Row1 distance to screen = {fmt(d1,2)} m ; row2 = {fmt(d2,2)} m")
    p(f"Screen width for {TARGET_HVA_DEG} deg at row1 = {fmt(sw,3)} m ; height {fmt(sh,3)} m ; "
      f"diag {fmt(diag,3)} m = {fmt(diag/IN,0)} in")
    p(f"Image bottom {fmt(SCREEN_BOTTOM_Z,2)} m, top {fmt(top,3)} m, ceiling {fmt(H,3)} m, "
      f"space above image {fmt(H-top,3)} m")
    eye1 = EYE_SEATED
    eye2 = riser_height_required(eye1, ROW1_Y, ROW2_Y, SCREEN_BOTTOM_Z, SCREEN_PLANE_Y, HEAD_CLEAR_C)
    riser = eye2 - EYE_SEATED
    p(f"Row2 eye height required = {fmt(eye2,3)} m -> riser = {fmt(riser,3)} m ({fmt(riser/IN,1)} in)")
    RISER = math.ceil(riser / IN) * IN  # round up to whole inch
    p(f"Adopted riser (rounded up to whole inch) = {fmt(RISER,3)} m ({fmt(RISER/IN,0)} in)")
    for name, d, eye in (("row1", d1, eye1), ("row2", d2, EYE_SEATED + RISER)):
        hva = 2 * math.degrees(math.atan(sw / 2 / d))
        vt = math.degrees(math.atan((top - eye) / d))
        vb = math.degrees(math.atan((SCREEN_BOTTOM_Z - eye) / d))
        p(f"  {name}: HVA (centre seat) = {fmt(hva)} deg ; vertical to top = {fmt(vt)} deg ; "
          f"to bottom = {fmt(vb)} deg ; distance/width = {fmt(d/sw,2)}")
    for name, d in (("row1", d1), ("row2", d2)):
        for x in seats_x():
            dx_l = (W / 2 - sw / 2) - x
            dx_r = (W / 2 + sw / 2) - x
            ang = math.degrees(math.atan2(dx_r, d) - math.atan2(dx_l, d))
            off = math.degrees(math.atan2(abs(x - W / 2), d))
            p(f"    {name} seat x={fmt(x,2)}: subtended HVA = {fmt(ang)} deg, off-centre angle = {fmt(off)} deg")

    # -----------------------------------------------------------------------
    p("\n=== 5. PROJECTOR THROW, SHIFT, LUMINANCE (JVC DLA-NZ8 example) ===")
    tr_min, tr_max = 1.43, 2.92  # most-cited published range; verify w/ JVC calculator
    th_min, th_max = tr_min * sw, tr_max * sw
    p(f"Throw ratio {tr_min}-{tr_max}:1 -> throw {fmt(th_min,2)}-{fmt(th_max,2)} m "
      f"-> lens plane y = {fmt(SCREEN_PLANE_Y+th_min,2)}-{fmt(SCREEN_PLANE_Y+th_max,2)} m "
      f"(room length {fmt(L,2)} m)")
    lens_y, lens_z = 6.50, H - 0.25
    throw = lens_y - SCREEN_PLANE_Y
    p(f"Chosen lens position y={lens_y} z={fmt(lens_z,3)} -> throw {fmt(throw,2)} m, "
      f"throw ratio needed {fmt(throw/sw,2)} (in range: {tr_min <= throw/sw <= tr_max})")
    centre_z = SCREEN_BOTTOM_Z + sh / 2
    shift_pct = (lens_z - centre_z) / sh * 100
    p(f"Vertical offset lens-to-image-centre = {fmt(lens_z-centre_z,3)} m = {fmt(shift_pct,1)}% of image height "
      f"(NZ8 published +/-80%; confirm JVC's % definition)")
    zb_at_row2 = SCREEN_BOTTOM_Z + (lens_z - SCREEN_BOTTOM_Z) * (ROW2_Y - SCREEN_PLANE_Y) / throw
    head2 = RISER + EYE_SEATED + 0.13
    p(f"Lower beam edge height at row2 = {fmt(zb_at_row2,2)} m ; seated head top row2 = {fmt(head2,2)} m ; "
      f"standing person (1.80 m) on riser = {fmt(RISER+1.80,2)} m -> standing blocks beam: {RISER+1.80 > zb_at_row2}")
    area_m2 = sw * sh
    area_ft2 = area_m2 / FT ** 2
    for lm, k, gain in ((2500, 0.65, 1.0), (2500, 0.65, 0.85), (2500, 0.45, 1.0)):
        fl = lm * k * gain / area_ft2
        p(f"  {lm} lm x {k} (calibration/ageing factor) x gain {gain} on {fmt(area_ft2,1)} ft2 "
          f"-> {fmt(fl,1)} fL = {fmt(fl*3.426,0)} cd/m2")

    # -----------------------------------------------------------------------
    p("\n=== 6. SPEAKER PLACEMENT (7.2.4) ===")
    ear1 = EAR_SEATED
    ear2 = EAR_SEATED + RISER
    RSP = (W / 2, ROW1_Y, ear1)
    lat_lr = 1.65
    z_lcr = 1.17
    y_side_rsp = ROW1_Y + (W / 2) * math.tan(math.radians(10))  # 100 deg at RSP
    y_side_mid = (ROW1_Y + ROW2_Y) / 2
    y_rear_side = ROW1_Y + (W / 2) / math.tan(math.radians(40))  # 140 deg at RSP
    z_surr = 1.83
    top_off = 1.0
    z_ceiling = H
    layouts = {
        "A: RSP-optimised": {
            "L": (W / 2 - lat_lr, 0.0, z_lcr), "C": (W / 2, 0.0, z_lcr), "R": (W / 2 + lat_lr, 0.0, z_lcr),
            "Lss": (0.0, y_side_rsp, z_surr), "Rss": (W, y_side_rsp, z_surr),
            "Lrs": (0.0, y_rear_side, z_surr), "Rrs": (W, y_rear_side, z_surr),
            "Ltf": (W / 2 - lat_lr, ROW1_Y - top_off, z_ceiling), "Rtf": (W / 2 + lat_lr, ROW1_Y - top_off, z_ceiling),
            "Ltr": (W / 2 - lat_lr, ROW1_Y + top_off, z_ceiling), "Rtr": (W / 2 + lat_lr, ROW1_Y + top_off, z_ceiling),
        },
        "B: two-row compromise": {
            "L": (W / 2 - lat_lr, 0.0, z_lcr), "C": (W / 2, 0.0, z_lcr), "R": (W / 2 + lat_lr, 0.0, z_lcr),
            "Lss": (0.0, y_side_mid, z_surr), "Rss": (W, y_side_mid, z_surr),
            "Lrs": (0.0, ROW2_Y + 1.6, z_surr), "Rrs": (W, ROW2_Y + 1.6, z_surr),
            "Ltf": (W / 2 - lat_lr, y_side_mid - 1.6, z_ceiling), "Rtf": (W / 2 + lat_lr, y_side_mid - 1.6, z_ceiling),
            "Ltr": (W / 2 - lat_lr, y_side_mid + 1.6, z_ceiling), "Rtr": (W / 2 + lat_lr, y_side_mid + 1.6, z_ceiling),
        },
    }
    # Dolby home-theater placement windows (as commonly cited; verify vs licensed/current Dolby doc)
    windows = {"L": ("az", 22, 30), "R": ("az", 22, 30), "C": ("az", 0, 0),
               "Lss": ("az", 90, 110), "Rss": ("az", 90, 110),
               "Lrs": ("az", 135, 150), "Rrs": ("az", 135, 150),
               "Ltf": ("el", 30, 55), "Rtf": ("el", 30, 55), "Ltr": ("el", 30, 55), "Rtr": ("el", 30, 55)}
    listeners = {f"r1s{i+1}": (x, ROW1_Y, ear1) for i, x in enumerate(seats_x())}
    listeners.update({f"r2s{i+1}": (x, ROW2_Y, ear2) for i, x in enumerate(seats_x())})
    listeners_ctr = {"RSP(r1 ctr)": RSP, "r2 ctr": (W / 2, ROW2_Y, ear2)}
    for lname, spk in layouts.items():
        p(f"-- Layout {lname} --")
        p(f"{'ch':4} {'x':>6} {'y':>6} {'z':>5} | " + " | ".join(
            f"{k:>11} az/el/dist" for k in listeners_ctr))
        for ch, pos in spk.items():
            row = f"{ch:4} {fmt(pos[0],2):>6} {fmt(pos[1],2):>6} {fmt(pos[2],2):>5} |"
            for k, lis in listeners_ctr.items():
                az, el, d = az_el(lis, pos)
                kind, lo, hi = windows[ch]
                val = abs(az) if kind == "az" else el
                ok = "OK" if (lo - 0.5 <= val <= hi + 0.5) else "--"
                if ch[1:3] in ("tf", "tr"):
                    # top-front must be in front of listener, top-rear behind
                    front = pos[1] < lis[1]
                    if (ch.endswith("tf") and not front) or (ch.endswith("tr") and front):
                        ok = "XX"
                row += f" {fmt(abs(az),0):>4}/{fmt(el,0):>3}/{fmt(d,2):>5} {ok} |"
            p(row)
        # compliance summary across all 8 seats
        tot = passed = 0
        for ch, pos in spk.items():
            for lis in listeners.values():
                az, el, d = az_el(lis, pos)
                kind, lo, hi = windows[ch]
                val = abs(az) if kind == "az" else el
                if ch == "C":
                    continue
                tot += 1
                good = lo - 0.5 <= val <= hi + 0.5
                if ch[1:3] in ("tf", "tr"):
                    front = pos[1] < lis[1]
                    if (ch.endswith("tf") and not front) or (ch.endswith("tr") and front):
                        good = False
                passed += good
        p(f"Seat-channel combinations inside Dolby window: {passed}/{tot} ({fmt(100*passed/tot,0)}%)")

    # -----------------------------------------------------------------------
    p("\n=== 7. SPL / AMPLIFIER POWER (on-axis, distance-only, no room gain) ===")
    # Published data (see catalog doc for sources). sens is dB SPL @ 2.83 V / 1 m unless noted.
    products = {
        "JBL SCL-2 (LCR, in-wall)": dict(sens=92, z=6, pmax=445, pmax_kind="rated RMS (CEA-426B)"),
        "JBL SCL-6 (surround, in-wall)": dict(sens=91, z=4, pmax=200, pmax_kind="upper recommended amp power"),
        "JBL SCL-8 (top, in-ceiling)": dict(sens=85, z=4, pmax=100, pmax_kind="upper recommended amp power"),
        "B&W CWM8.3 D (LCR, in-wall)": dict(sens=89, z=8, pmax=200, pmax_kind="recommended amp power"),
        "B&W CCM8.5 D (top, in-ceiling)": dict(sens=88, z=8, pmax=120, pmax_kind="recommended amp power"),
        "B&W surround (model TBD)": dict(sens=None, z=None, pmax=None, pmax_kind=None),
    }
    TARGET_PEAK = 105.0
    MARGIN = 3.0
    lay = layouts["A: RSP-optimised"]
    dist = {
        "LCR": az_el(RSP, lay["L"])[2],
        "surround": max(az_el(RSP, lay["Lss"])[2], az_el(RSP, lay["Lrs"])[2]),
        "top": az_el(RSP, lay["Ltf"])[2],
    }
    p(f"Worst-case RSP distances: LCR {fmt(dist['LCR'],2)} m, surround {fmt(dist['surround'],2)} m, "
      f"top {fmt(dist['top'],2)} m ; target {TARGET_PEAK} dB peak + {MARGIN} dB margin")
    role = {"LCR": "LCR", "surround": "surround", "top": "top"}
    for name, s in products.items():
        r = "LCR" if "LCR" in name else ("top" if "top" in name else "surround")
        d = dist[r]
        if s["sens"] is None:
            p(f"  {name}: INSUFFICIENT DATA - sensitivity/impedance missing -> no power result; flagged")
            continue
        p_ref = 2.83 ** 2 / s["z"]
        need_db = TARGET_PEAK + MARGIN - s["sens"] + db(d)
        p_need = p_ref * 10 ** (need_db / 10)
        spl_cap = s["sens"] + 10 * math.log10(s["pmax"] / p_ref) - db(d)
        p(f"  {name}: d={fmt(d,2)} m, P_ref(2.83V)={fmt(p_ref,2)} W, required {fmt(p_need,0)} W ; "
          f"est. max at RSP {fmt(spl_cap,1)} dB using {s['pmax']} W ({s['pmax_kind']}) "
          f"-> {'MEETS' if spl_cap >= TARGET_PEAK else 'SHORT by ' + fmt(TARGET_PEAK-spl_cap,1) + ' dB'}")
    # Direct + reverberant (Hopkins-Stryker / statistical room) correction
    abar_1k = rt(treated)[3][2]
    R_room = S_total * abar_1k / (1 - abar_1k)
    p(f"Statistical-room correction (treated room, abar@1k={fmt(abar_1k,2)}, R={fmt(R_room,0)} m2):")
    for Q in (2.0, 5.0, 10.0):
        dc = math.sqrt(Q * R_room / (16 * math.pi))
        gains = []
        for r_name in ("LCR", "surround", "top"):
            d = dist[r_name]
            g = 10 * math.log10((1 / d ** 2 + 16 * math.pi / (Q * R_room)) / (1 / d ** 2))
            gains.append(f"{r_name} +{fmt(g,1)} dB")
        p(f"  Q={Q:>4} (DI {fmt(10*math.log10(Q),1)} dB): critical distance {fmt(dc,2)} m ; " + ", ".join(gains))
    # Per-seat level spread (inverse square only) for layout A
    p("Per-seat level relative to RSP (inverse-square only, layout A), dB:")
    for ch in ("L", "C", "Lss", "Lrs", "Ltf", "Ltr"):
        d_rsp = az_el(RSP, lay[ch])[2]
        rel = [-db(az_el(lis, lay[ch])[2] / d_rsp) for lis in listeners.values()]
        p(f"  {ch:4}: min {fmt(min(rel),1):>5}  max {fmt(max(rel),1):>5}  spread {fmt(max(rel)-min(rel),1)}")
    # SCL-8 coverage: angle between ceiling normal (straight down) and each seat
    p("SCL-8 (top) off-normal angle to seats, layout A (published HF coverage: 120 deg H x 60 deg V about a 45 deg axis):")
    for ch in ("Ltf", "Ltr"):
        angs = []
        for lis in listeners.values():
            v = vec(lay[ch], lis)
            angs.append(math.degrees(math.acos(-v[2] / norm(v))))
        p(f"  {ch}: off-normal {fmt(min(angs),0)}-{fmt(max(angs),0)} deg")

    # -----------------------------------------------------------------------
    p("\n=== 8. SUBWOOFERS ===")
    # JBL SSW-1: 2 x 15", 90 dB / 1 W / 1 m per woofer, 8 ohm per woofer, 2500 W RMS per woofer
    sens_w, n_woofers_per_unit, n_units = 90.0, 2, 2
    lfe_target = 115.0
    d_sub = 4.0
    coherent_gain = 20 * math.log10(n_woofers_per_unit * n_units)
    need_db = lfe_target - (sens_w + coherent_gain) + db(d_sub)
    p_need = 10 ** (need_db / 10)
    p(f"LFE target {lfe_target} dB at RSP; 4 woofers coherent gain +{fmt(coherent_gain,1)} dB; "
      f"d={d_sub} m; no room gain -> {fmt(p_need,0)} W per woofer (rated 2500 W)")
    # Modal-sum seat-to-seat analysis
    T60_LF = 0.40
    delta = 6.91 / T60_LF
    mode_list = []
    for nx in range(0, 8):
        for ny in range(0, 10):
            for nz in range(0, 4):
                f = C_SOUND / 2 * math.sqrt((nx / W) ** 2 + (ny / L) ** 2 + (nz / H) ** 2)
                if f > 250:
                    continue
                lam = (1 if nx == 0 else 0.5) * (1 if ny == 0 else 0.5) * (1 if nz == 0 else 0.5)
                mode_list.append((nx, ny, nz, 2 * math.pi * f, lam))

    def psi(n, r):
        return (math.cos(n[0] * math.pi * r[0] / W) * math.cos(n[1] * math.pi * r[1] / L)
                * math.cos(n[2] * math.pi * r[2] / H))

    def pressure(src_list, rcv, f):
        w = 2 * math.pi * f
        tot = 0j
        for nx, ny, nz, wn, lam in mode_list:
            n = (nx, ny, nz)
            num = sum(psi(n, s) for s in src_list) * psi(n, rcv)
            tot += num / (lam * (wn ** 2 - w ** 2 + 2j * delta * w))
        return abs(tot)

    freqs = [20 * 2 ** (i / 24) for i in range(0, int(24 * math.log2(100 / 20)) + 1)]
    seat_pts = list(listeners.values())
    sub_opts = {
        "S1 front wall 1/4 & 3/4 width": [(W / 4, 0.05, 0.3), (3 * W / 4, 0.05, 0.3)],
        "S2 front & back wall centre": [(W / 2, 0.05, 0.3), (W / 2, L - 0.05, 0.3)],
        "S3 side-wall midpoints": [(0.05, L / 2, 0.3), (W - 0.05, L / 2, 0.3)],
        "S4 front-left & back-right corners": [(0.05, 0.05, 0.3), (W - 0.05, L - 0.05, 0.3)],
        "S0 single sub front-left corner": [(0.05, 0.05, 0.3)],
    }
    p(f"Modal-sum model: rigid walls, uniform damping from T60={T60_LF}s, modes <=250 Hz, "
      f"8 seats, 20-100 Hz in 1/24 oct ({len(freqs)} pts)")
    for name, srcs in sub_opts.items():
        sd_list = []
        for f in freqs:
            lv = [db(pressure(srcs, r, f)) for r in seat_pts]
            m = sum(lv) / len(lv)
            sd_list.append(math.sqrt(sum((x - m) ** 2 for x in lv) / len(lv)))
        rsp_curve = [db(pressure(srcs, RSP, f)) for f in freqs]
        p(f"  {name:36}: mean seat-to-seat SD = {fmt(sum(sd_list)/len(sd_list),2)} dB ; "
          f"max SD = {fmt(max(sd_list),1)} dB ; RSP curve range = {fmt(max(rsp_curve)-min(rsp_curve),1)} dB")

    # -----------------------------------------------------------------------
    p("\n=== 9. FIRST-REFLECTION POINTS (image-source, RSP) ===")
    for ch in ("L", "R", "C"):
        s = lay[ch]
        for wall, axis, plane in (("left wall", 0, 0.0), ("right wall", 0, W), ("ceiling", 2, H)):
            img = list(s)
            img[axis] = 2 * plane - s[axis]
            t = (plane - img[axis]) / (RSP[axis] - img[axis])
            pt = [img[i] + t * (RSP[i] - img[i]) for i in range(3)]
            d_dir = az_el(RSP, s)[2]
            d_ref = norm(vec(img, RSP))
            p(f"  {ch} -> {wall:10}: x={fmt(pt[0],2)} y={fmt(pt[1],2)} z={fmt(pt[2],2)} ; "
              f"path diff {fmt(d_ref-d_dir,2)} m = {fmt((d_ref-d_dir)/C_SOUND*1000,1)} ms ; "
              f"inverse-square level re direct {fmt(-db(d_ref/d_dir),1)} dB")

    # -----------------------------------------------------------------------
    p("\n=== 10. CHANNEL / AMP COUNT ===")
    full_range = 7 + 4
    p(f"Full-range channels {full_range}; sub outputs 2 (each SSW-1 = 2 woofers -> 4 amp channels)")
    p("JBL SDP-58: 16 processed output channels -> 11 + 2 subs = 13 <= 16 OK (4 spare for 9.x.6 growth needs 15+2=17: NOT OK)")
    p("JBL SDA-7120: 7 ch; 100 W/8 ohm, 140 W/4 ohm all-channels-driven -> 2 units = 14 ch for 11 full-range")

    print("\n".join(out))


if __name__ == "__main__":
    main()
