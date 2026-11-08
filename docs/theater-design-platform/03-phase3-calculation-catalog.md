# Phase 3 — Engineering Calculation Catalog

**Project:** CHT Theater Design Platform: technical discovery
**Document:** Phase 3 calculation engine specification, with the Phase 9 reference project as the running example
**Status:** Draft v0.1 for internal review
**Date:** 2026-11-08
**Companion files:**
- [`phase3-worked-examples/reference_calcs.py`](phase3-worked-examples/reference_calcs.py) is a standard-library verification script. It computes every number in this document.
- [`phase3-worked-examples/reference_calcs_output.txt`](phase3-worked-examples/reference_calcs_output.txt) is its output.

These are the **first golden test vectors** for the future engine (requirement NFR-01 in Phase 1). They are not application code.

**Preferred brands (CHT input):** JBL Synthesis (available through the Savant store) and Bowers & Wilkins. The worked examples use their published custom-install specifications.

---

## 0. Conventions

### 0.1 Units and coordinates

| Item | Convention |
|---|---|
| Internal units | SI. The engine stores **millimetres** as integers for geometry and uses SI floats for derived quantities. Display is metric or imperial. This document uses metres. |
| Origin | Front-left floor corner, seen from the seats looking at the screen |
| Axes | **x** across the width (left → right), **y** from the screen wall toward the back wall, **z** up from the finished floor |
| Azimuth | 0° is toward the screen; positive is to the listener's right. Compliance uses \|az\| from 0° to 180°. |
| Elevation | Angle above the horizontal plane through the listener's ears |
| Speed of sound | c = 343 m/s at 20 °C. Engine form: c = 331.3·√(1 + T/273.15) |
| Levels | dB SPL re 20 µPa. Sensitivity is normalized to **dB SPL @ 2.83 V @ 1 m**, with the radiation space (2π or 4π) recorded. |

### 0.2 Result classes (shown on every reported value)

| Class | Meaning | Examples |
|---|---|---|
| **G**: Geometry | Exact, given the inputs. Error comes only from input error. | Angles, distances, throw distance, riser height |
| **E**: Engineering estimate | A simplified model with known bias. Reported with an uncertainty band. | SPL at seat, required power, RT60, modal response, luminance |
| **M**: Measurement required | Cannot be validated without on-site measurement. The design value is a *target*. | In-room frequency response, actual RT60, seat-to-seat bass variance, noise floor, calibrated luminance |

### 0.3 Rule provenance

Every placement window and target lives in a **versioned rule set**. Each rule stores the document, its edition, the clause or page, and whether we hold a licensed or authoritative copy. Values marked **[verify]** come from secondary sources. They must be checked against the primary document before the rule set is approved. The direct-fetch limitation from Phase 1 §0.2 still applies.

---

## 1. Engine design principles

1. **Pure functions.** `f(inputs, catalogVersion, ruleSetVersion) → results + warnings + provenance`. No I/O and no randomness, so the same inputs always produce identical output.
2. **Typed quantities.** Unit-aware types (length, angle, SPL, power) prevent dB/W and ft/m mix-ups at compile time.
3. **Every result carries a trace:** the formula ID (e.g. `C3`), its inputs, the data sources and the result class.
4. **Missing data degrades explicitly.** A calculation returns `INSUFFICIENT_DATA` with the list of missing fields. It never substitutes a silent default. Defaults are allowed only when they are labelled assumptions (e.g. seated ear height 1.05 m) that the user can see and override.
5. **Criteria are data, not code.** Dolby, DTS, RP22 and RP23 thresholds are loaded as criteria sets. This lets RP22 level thresholds be added once the licensed text is in hand, without code changes.
6. **AI never computes engineering numbers.** This is NFR-02 from Phase 1.

---

## 2. Reference project: inputs and assumptions

| Input | Value used | Status | Needed before construction |
|---|---|---|---|
| Room | 20′ × 30′ × 8′ = 6.096 × 9.144 × 2.438 m | Concept (client brief) | Finished-surface dimensions after framing, drywall, AT wall and soffits |
| Volume | 135.9 m³ (4,800 ft³) | Derived | — |
| Screen | 16:9, acoustically transparent (AT), plane 0.30 m in front of the front wall | **Assumption** | Screen type and aspect ratio decision (2.40:1 constant height is a common alternative) |
| Front speakers | In-wall LCR behind the AT screen, acoustic centre 1.17 m | Assumption | Wall cavity depth (SCL-2 needs ≥152 mm stud depth) |
| Rows | Row 1 ear/eye plane at y = 3.80 m; row 2 at y = 5.60 m; 4 recliners per row at 0.86 m pitch | Assumption | Seat model (reclined depth, eye/ear height) |
| Seated eye / ear height | 1.10 m / 1.05 m above the row floor | Default assumption | Seat manufacturer data |
| RSP | Centre of row 1 (between seats 2 and 3) | Design decision | Confirm the primary row with the client |
| Sightline clearance C | 120 mm | Typical design value [verify against CEB23-B and cinema practice] | — |
| Format | Dolby Atmos 7.2.4 | Client brief | — |
| Target level | 105 dB SPL peak per channel at the RSP (Dolby reference: 85 dB at −20 dBFS) + 3 dB design margin; LFE 115 dB | Design target | Client performance goal (reference vs. "reference −5 dB") |
| Rack | Outside the theater; speaker runs assumed 15 m | Assumption | Actual rack location and cable paths |
| Projector example | JVC DLA-NZ8 (2,500 lm; throw ratio 1.43–2.92:1; shift ±80% V / ±34% H) | Example only | Selected model and lens |

---

## 3. Calculation catalog

Each entry gives the formula, variables and units, required inputs, the reference-project example, validation rules, tolerance, references, limitations and result class.

### Group A: Speaker placement

#### A1. Listener model

- **Definition.** Each seat *s* has an ear point E_s = (x_s, y_s, h_floor,s + h_ear) and an eye point with h_eye. The RSP is a designated point, usually the centre of the primary row. That point may fall between seats when a row has an even number of seats, as in this project.
- **Inputs.** Seat layout, riser heights, seat model ear and eye heights.
- **Validation.** Ear height between 0.85 and 1.30 m above the seat floor. Seats must be inside the room and must not overlap each other or keep-out zones.
- **Class.** G.

#### A2. Azimuth, elevation and distance

```
d   = (dx, dy, dz) = P_spk − E_listener
az  = atan2(dx, −dy)                      [deg; 0 = toward screen]
el  = atan2(dz, √(dx² + dy²))             [deg]
r   = |d|                                  [m]
```

- **Example.** Front-left L at (1.398, 0, 1.17) seen from the RSP (3.048, 3.80, 1.05): az = 23.5°, el = 1.7°, r = 4.14 m.
- **Tolerance.** Exact (G). Real-world error comes from mounting tolerance (±25 mm gives about ±0.4° at 4 m).

#### A3. Layout rule windows (rule set: Dolby home guidelines)

Values are as commonly cited from the Dolby Atmos Home Theater Installation Guidelines (editions 2014, Apr 2015 and Dec 2018 indexed) and the Dolby 7.1.4 setup guides. **[verify all against the current Dolby document before encoding]**

| Channel | Window | Applies to |
|---|---|---|
| L / R | \|az\| 22°–30° | All layouts |
| C | 0° | All layouts |
| Ls / Rs (5.1.x) | \|az\| 110°–120° | 5.x layouts |
| Lss / Rss (7.1.x) | \|az\| 90°–110° | 7.x and 9.x layouts |
| Lrs / Rrs | \|az\| 135°–150° | 7.x and 9.x layouts |
| Lw / Rw (wides) | Window per Dolby [verify] | 9.x layouts |
| Top Front / Top Rear (x.x.4, x.x.6) | elevation 30°–55°; Top Front must be in front of the listener and Top Rear behind | .4 and .6 |
| Top Middle (x.x.2, x.x.6) | elevation 65°–100° [verify] | .2 and .6 |
| Vertical, ear-level channels | Near ear height; surrounds raised to clear the heads of rows behind [verify the Dolby height guidance] | — |

Reference alternatives stored as separate rule sets: ITU-R BS.775 (L/R ±30°, surrounds 100°–120°) and ITU-R BS.2051 (higher channel counts), DTS:X, Auro-3D, and CEDIA/CTA-RP22 v1.2 (Sept 2023, 21 parameters, 4 levels; licensed or official text required).

#### A4. Placement solver (algorithm)

1. **Ideal directions.** For each channel, take the ideal direction (window centre or rule-preferred value) relative to the *design reference point*. This is the RSP, or a row-weighted point in multi-row mode.
2. **Ray-cast.** Cast a ray from the reference ear point along the ideal direction. Intersect it with the allowed mounting surfaces for that channel's mounting type: front wall, side walls, ceiling, or behind the AT screen.
3. **Constraints.**
   - Hard: keep-outs (doors, screen frame, soffits, HVAC, projector beam, beams and joists if known), minimum distance from corners, product cut-out size.
   - Soft: symmetry, alignment with L/R for the tops, and stud and joist grid snapping.
4. **Violations.** If a constraint is violated, search along the surface within the window for the feasible point that minimizes a weighted cost:

   ```
   J = Σ_seats w_s · Σ_ch [ angular deviation outside window ]² + λ · asymmetry
   ```

5. **Report** per channel: position, the window, pass or fail per seat, and the binding constraint.

- **Class.** G for geometry. The window choice is a rule-set decision.

#### A5. Multi-row compliance score

```
Compliance = (# seat–channel pairs inside window) / (# seat–channel pairs)
```

The centre channel is excluded. Per-seat and per-channel breakdowns are also reported.

**Reference project result.** This is a key finding.

| Layout | Strategy | RSP | Row-2 centre | All 8 seats |
|---|---|---|---|---|
| A | RSP-optimised (Lss at 100°, Lrs at 140°, tops ±1.0 m from row 1) | 10/10 pass | Lss 67°, Lrs 121°, **Top Rear lands in front of row 2** (el 27°), Top Front el 16° | **30/80 (38%)** |
| B | Two-row compromise (sides at row midpoint, tops ±1.6 m from midpoint) | Top Rear el 25° (fail) | Better side angles, still out of window | 20/80 (25%) |

**Interpretation.** With an 8′ ceiling and two rows 1.8 m apart, one set of four top speakers cannot meet the 30°–55° window for both rows. The row-2 ear sits on an 18″ riser, leaving only 0.93 m to the ceiling. One pair of side surrounds cannot be 90°–110° for both rows either. The engine must surface this conflict *as a design decision*, not hide it. Candidate resolutions to model in Phase 5:

- 7.2.6: add Top Middle. The JBL SDP-58 has 16 outputs; 13 + 2 subs = 15 is OK.
- 9.2.6: needs 17 outputs, which **exceeds the SDP-58**. It would need a higher-count processor.
- Surround arrays or additional surround pairs, depending on the processor.
- Reducing row spacing or riser height, which trades against sightlines (D3).

#### A6. Aiming

For pivoting tweeters or angled baffles, the aim vector points from the speaker to a target point. The target is the RSP or the centroid of the seats.

```
yaw  = atan2(t_x − p_x, −(t_y − p_y))
tilt = atan2(t_z − p_z, √((t_x − p_x)² + (t_y − p_y)²))
```

Off-axis angle per seat: θ_s = arccos( â · ŝ ), where â is the unit aim vector and ŝ is the unit vector from the speaker to the seat. Example: an SCL-8 top speaker (non-pivoting; its 45° angled axis is set by its rotation) sees seats at **37°–77° from its ceiling normal** in layout A.

#### A7. Distance and delay table (for processor setup)

```
Δt_i = (r_max − r_i) / c
```

The engine exports each speaker's distance to the RSP in the processor's units. Example: Ltf 2.38 m vs Lrs 4.81 m gives Δ = 7.1 ms. The processor does the delay alignment; the design only supplies the starting values. **Class M:** final values come from calibration.

---

### Group B: Room and acoustic analysis

#### B1. Volume, areas, ratios

V = W·L·H; S = 2(WL + WH + LH). Example: V = 135.9 m³, S = 185.8 m², H:W:L = 1 : 2.50 : 3.75. Ratio charts (Bolt, Louden) may be shown for reference only, never as pass/fail.

#### B2. Room modes (rigid rectangular room)

```
f(nx,ny,nz) = (c/2) · √( (nx/W)² + (ny/L)² + (nz/H)² ),   n ∈ {0,1,2,…}
```

The mode type depends on how many indices are non-zero: one means axial, two tangential, three oblique.

**Example.** The first length mode is 343 / (2·9.144) = **18.8 Hz**.

| Axis | Axial modes < 120 Hz |
|---|---|
| Width 6.096 m | 28.1, 56.3, 84.4, 112.5 Hz |
| Length 9.144 m | 18.8, 37.5, 56.3, 75.0, 93.8, 112.5 Hz |
| Height 2.438 m | 70.3 Hz |

- **Coincidences.** At **56.3 Hz** (0,3,0) and (2,0,0) coincide exactly. At **112.5 Hz** (0,6,0) and (4,0,0) coincide. Both happen because L/W = 1.5 exactly. Flag coincidences within 5% or one critical bandwidth.
- **Mode count.** 30 modes below 100 Hz.
- **Validation.** Dimensions > 0, and f_max ≤ about 2× the Schroeder frequency.
- **Limitations.** This model assumes rigid, parallel and rectangular boundaries. Real basements have concrete and framed walls with different impedance, soffits and openings, so actual frequencies shift and damping varies. **Class E for frequencies, M for amplitudes.**

#### B3. Schroeder frequency

f_s ≈ 2000·√(T60/V). Example: 94 Hz at T60 = 0.3 s and 121 Hz at 0.5 s. Below f_s, use modal methods (B8). Above it, use statistical methods (B4, B5).

#### B4. Reverberation time

```
Sabine:  T60 = 0.161·V / A,       A = Σ S_i·α_i  (+ 4mV air term above 2 kHz)
Eyring:  T60 = 0.161·V / (−S·ln(1 − ᾱ)),   ᾱ = A/S  (clamp ᾱ ≤ 0.99)
```

Eyring is preferred when ᾱ > about 0.2, which applies to treated theaters. Fitzroy or Arau-Puchades can be offered for non-uniform absorption distributions.

**Example** (*illustrative* absorption coefficients; the production catalog must use tested ISO 354 / ASTM C423 data):

| Band (Hz) | 125 | 250 | 500 | 1k | 2k | 4k |
|---|---|---|---|---|---|---|
| Untreated, Eyring (s) | 0.46 | 0.77 | 0.51 | 0.44 | 0.39 | 0.36 |
| Treated, Eyring (s): front wall plus 35% of other walls, 35.7 m² of 2″ panel | 0.52 | 0.35 | 0.22 | 0.21 | 0.20 | 0.20 |

A small-room reference time for comparison is EBU Tech 3276 style T_m = 0.25·(V/100 m³)^⅓ = **0.28 s**. This is a comparison only. RP22 may define its own criterion [verify].

**Finding.** The 2″ panels control 500 Hz–4 kHz but leave **125 Hz at about 0.5 s**. The design needs low-frequency treatment such as bass traps or membrane absorbers, which must be modelled with real product data.

**Limitations.** Statistical theory assumes a diffuse field, which small rooms do not have. Expect ±20–30% error versus measurement. **Class E; verify by ISO 3382-2 measurement after treatment.**

#### B5. Room constant and critical distance

```
R   = S·ᾱ / (1 − ᾱ)
D_c = √(Q·R / (16π))
```

Example: in the treated room at 1 kHz, ᾱ = 0.43, so R = 142 m². That gives D_c = 2.4 m for Q = 2, 3.8 m for Q = 5, and 5.3 m for Q = 10. **Every row-1 seat sits near or beyond D_c for most speakers**, so free-field 1/r² understates the SPL there (see C5).

#### B6. First-reflection points (image-source method)

Mirror the source across the wall plane, then intersect the image→listener segment with that plane.

```
P_img[axis] = 2·plane − P_src[axis]
t = (plane − P_img[axis]) / (E[axis] − P_img[axis])
Q = P_img + t·(E − P_img)
```

Report the point, the extra path length Δr, the delay Δr/c, and the inverse-square level relative to the direct sound.

**Example at the RSP.**

| Source → surface | Reflection point (x, y, z) | Δt | Level re direct |
|---|---|---|---|
| L → left wall | (0.00, 1.19, 1.13) | 5.0 ms | −3.0 dB |
| C → side walls | (0 or 6.10, 1.90, 1.11) | 9.9 ms | −5.5 dB |
| L → ceiling | (2.19, 1.81, 2.44) | 2.3 ms | −1.5 dB |

The engine creates a treatment target zone around each point, sized from the Fresnel zone or a fixed ±0.6 m, and unions the zones across all seats and speakers.

Limitations: specular reflection only, before the panel's own absorption. **Class G for the points, E for the level.**

#### B7. Treatment coverage

Coverage % = treated area ÷ surface area, per surface and per zone. Absorption, diffusion and bass-trap products come from the catalog (Phase 2), each with tested coefficients. Output: the rule check "every first-reflection zone covered: Y/N", plus RT60 re-computed with B4.

#### B8. Low-frequency seat response and multi-sub placement (modal sum)

```
p(r, ω) ∝ Σ_n  [ Σ_src ψ_n(r_src) ] · ψ_n(r) / ( Λ_n · (ω_n² − ω² + 2jδω) )
ψ_n(r) = cos(nx·π·x/W) · cos(ny·π·y/L) · cos(nz·π·z/H)
Λ_n = Π ε_i,  ε = 1 if n_i = 0 else ½
δ = 6.91 / T60_LF
```

Metric: the seat-to-seat standard deviation (SD) of level across all seats, per frequency (20–100 Hz in 1/24-octave steps), then its mean and maximum. This is Welti's mean-spatial-variance family of metrics.

**Example** (T60_LF = 0.4 s, modes ≤ 250 Hz, 8 seats):

| Option | Mean seat SD | Max SD |
|---|---|---|
| S0: single sub, front-left corner | 4.36 dB | 9.6 dB |
| S1: two subs at front wall ¼ and ¾ width | 3.35 dB | 6.5 dB |
| S2: front and back wall centres | 2.83 dB | 11.1 dB |
| S3: side-wall midpoints | 2.80 dB | 8.4 dB |
| S4: opposite corners (front-left and back-right) | 2.83 dB | 7.3 dB |

**Reading.** Any two-sub option beats one sub. Opposing-boundary options (S2–S4) beat the common "both subs on the front wall" option on mean SD, but S2 has a worse peak SD. Because of its size and depth, the JBL SSW-1 in-wall sub constrains which walls are possible.

**Limitations.** Real walls are not rigid. Framed walls absorb bass, which lowers Q and shifts frequencies. No processor EQ, delay or gain optimization is included, and no Trinnov WaveForming. **Class E for the ranking only. Absolute values are class M.** A Tier 3 upgrade path is the boundary element or finite-difference method, or optimization of per-sub gain and delay (as in Welti and in MSO-style tools).

---

### Group C: Audio performance

#### C1. Sensitivity normalization

Normalize every sensitivity to **dB @ 2.83 V @ 1 m**.

- A spec given at 1 W/1 m into a nominal Z converts as S_2.83V = S_1W + 10·log10(8/Z).
- Store the radiation condition: 2π (half-space, typical for in-wall and in-ceiling spec sheets, e.g. the JBL SCL-8 "2π anechoic") or 4π.
- Do **not** add +3 dB boundary gain to a spec that is already 2π.

The reference power at 2.83 V is P_ref = 2.83²/Z_nom: 1 W at 8 Ω, 1.33 W at 6 Ω, 2 W at 4 Ω.

#### C2. On-axis SPL at distance (free-field)

```
SPL(r, P) = S_2.83V + 10·log10(P / P_ref) − 20·log10(r / 1 m)
```

#### C3. Required amplifier power

```
P_req = P_ref · 10^((SPL_target + margin − S_2.83V + 20·log10(r)) / 10)
```

#### C4. Maximum output capability

Use, in order of preference:

1. the manufacturer's rated max SPL, with its standard (e.g. AES75 / CTA-2034 for full range, CTA-2010 for subs)
2. rated long-term power (e.g. CEA-426B), via C2
3. the upper recommended amplifier power, labelled as a *lower-confidence proxy*

Power compression is not modelled. Apply a 2–3 dB penalty at rated power, or use measured data.

**Example** (free-field, RSP, target 105 + 3 dB margin; result for 105 dB without the margin):

| Product (published data) | Role | r (m) | P_req | Est. max at RSP | vs 105 dB |
|---|---|---|---|---|---|
| JBL Synthesis SCL-2: 92 dB/2.83 V, 6 Ω, 445 W RMS (CEA-426B) | LCR | 4.14 | 913 W | 104.9 dB | −0.1 dB |
| JBL SCL-6: 91 dB, 4 Ω, 25–200 W recommended | Surround | 4.81 | 2,317 W | 97.4 dB (proxy) | −7.6 dB |
| JBL SCL-8: 85 dB, 4 Ω, 25–100 W recommended | Top | 2.38 | 2,257 W | 94.5 dB (proxy) | −10.5 dB |
| B&W CWM8.3 D: 89 dB, 8 Ω (min 5 Ω), 200 W recommended | LCR | 4.14 | 1,366 W | 99.7 dB (proxy) | −5.3 dB |
| B&W CCM8.5 D: 88 dB, 8 Ω (min 3.3 Ω), 120 W recommended | Top | 2.38 | 566 W | 101.3 dB (proxy) | −3.7 dB |
| B&W surround: model not yet selected | Surround | — | **INSUFFICIENT_DATA** | — | flagged |

#### C5. Direct + reverberant correction (statistical room)

```
ΔL = 10·log10( (1/r² + 16π/(Q·R)) / (1/r²) )
```

**Example** (R = 142 m²):

| Q (DI) | LCR | Surround | Top |
|---|---|---|---|
| 2 (3 dB) | +6.1 dB | +7.1 dB | +3.0 dB |
| 5 (7 dB) | +3.5 dB | +4.2 dB | +1.5 dB |
| 10 (10 dB) | +2.1 dB | +2.6 dB | +0.8 dB |

**Key finding.** The free-field method (C2–C4) is conservative by roughly 1–7 dB in this room. The size of the error depends on directivity data we usually do not have. With a moderate Q = 5:

- SCL-2 LCR reaches about **108 dB**, which meets reference.
- B&W CWM8.3 D LCR reaches about 103 dB.
- The ceiling models remain 2–9 dB short of 105 dB peaks.

Therefore the engine must:

1. show **both** the free-field and the room-corrected estimate, as a range
2. ask for the client's target level explicitly (reference vs. reference −5 dB, a common "near-reference" home target)
3. flag ceiling and surround channels for a larger model or more units when the range straddles the target
4. flag that a max-SPL spec is missing for JBL SCL-6/8 and B&W models (a Phase 2 data request)

**Class E: ±3 dB band at best.**

#### C6. Seat-to-seat level spread (inverse-square)

Spread = max − min across seats of 20·log10(r_RSP / r_seat).

| Channel | L | C | Lss | Lrs | Ltf | Ltr |
|---|---|---|---|---|---|---|
| Spread (dB) | 4.4 | 3.5 | 7.1 | 7.0 | 7.5 | 8.5 |

Nearby surround and top speakers dominate the spread. This is the case for more, lower-level surround and top sources in multi-row rooms. The RP22 seat-to-seat criteria will be applied once the thresholds are loaded from the official document.

#### C7. Off-axis level (directivity)

```
SPL_seat = SPL_on(r) + H(θ, φ, f)
```

- **Best data:** measured polar or spinorama data (CTA-2034; GLL or CLF files).
- **Fallback:** a coverage-angle model, labelled "approximate":

  ```
  H(θ) = 20·log10(cosⁿ θ),   n = ln(0.5) / ln(cos(θ_c/2))
  ```

  where θ_c is the published −6 dB coverage angle. Example, SCL-8: horizontal 120° gives n = 1.0, so a seat 60° off axis is −6 dB; vertical 60° gives n = 4.8.

- **Class E.** No data at all → `INSUFFICIENT_DATA` for the coverage map.

#### C8. Subwoofer requirement

Coherent summation of N identical sources at low frequency adds +20·log10(N) dB. That is ideal and an upper bound; boundaries and phase reduce it.

**Example:** 2 × JBL SSW-1 (2 woofers each, 90 dB/1 W/1 m per woofer), target LFE 115 dB at 4 m with no room gain → **316 W per woofer** (rated 2,500 W). This leaves about 9 dB of headroom before rated power, before room gain. Room gain in a sealed basement below about 19 Hz (c/2L) adds more.

Max-output data should be CTA-2010 style (dB at 20/25/31.5/40/50/63 Hz). If absent, flag it. **Class E.**

#### C9. Target levels and headroom

Dolby reference is 85 dB SPL (C-weighted, slow) at −20 dBFS per screen channel, giving 105 dB peaks; LFE is +10 dB in-band. The design target is stored per project as one of:

- Reference
- Reference −3 dB
- Reference −5 dB
- RP22 level *N* (when licensed and loaded)

#### C10. Load and impedance

- Parallel load: Z = 1 / Σ(1/Z_i).
- Check: amplifier rating at that load exists, and Z_min (when published, e.g. CCM8.5 D 3.3 Ω) ≥ the amplifier's minimum stable load.
- Example: JBL SDA-7120 is 140 W/4 Ω all channels driven. That is below the ≥566 W per channel C3 asks for at full reference with margin on the B&W tops. This is a power gap to resolve: lower the target, add amplification per channel, or choose a higher-sensitivity speaker.

#### C11. Channel count validation

```
outputs_needed = full-range channels + sub outputs
amp channels needed = Σ (amp channels per speaker)
```

The SSW-1 uses 2 amplifier channels per enclosure. Example:
- 7.2.4 = 11 + 2 = 13 outputs ≤ 16 on the SDP-58. OK.
- 7.2.6 = 15. OK.
- 9.2.6 = 17. Fails.
- Amplification: 11 full-range channels + 4 woofer channels → two SDA-7120 (14 ch) for the full-range channels, plus separate sub amplification (JBL recommends one bridged MA4-D per SSW-1 [verify]).

#### C12. Speaker cable loss

```
R_loop = 2·ℓ·ρ_AWG
Loss   = 20·log10( Z / (Z + R_loop) )
```

Use Z_min for the worst case. Design rule: R_loop ≤ 5% of Z_min.

| Run | Gauge | R_loop | Loss into 4 Ω | % of 3.3 Ω |
|---|---|---|---|---|
| 15 m | 12 AWG (5.21 mΩ/m) | 0.156 Ω | −0.33 dB | 4.7% |
| 15 m | 14 AWG (8.29 mΩ/m) | 0.249 Ω | −0.52 dB | 7.5% (fails the rule) |

**Class G/E.** The rack outside the room makes this a real constraint.

#### C13. Performance classification

A per-parameter pass/fail against a loaded criteria set. **Do not claim "RP22 Level N" until:**

1. the official RP22 v1.2 text is in hand and its use is cleared
2. each of the 21 parameters is mapped to a calculation, or marked "measurement-only"
3. validation against measured rooms is complete

Most RP22 parameters are measurement-verified; the design tool can only *predict* them.

---

### Group D: Video engineering

#### D1. Screen width from target viewing angle

```
W_img = 2·d·tan(θ_H/2)
H_img = W_img / AR
```

**Example:** d = 3.50 m, θ_H = 45° → W = 2.899 m, H = 1.631 m, diagonal **131″** (16:9).

Guidance as cited by secondary sources (**[verify]**: sources disagree; store as selectable criteria):

| Source | Horizontal viewing angle |
|---|---|
| SMPTE EG-18 | ≥ 30° |
| THX | 36°–40° |
| ITU (UHD) | about 58°–61° |
| CEB23-B | Treats viewing angle as a function of distance and size, not a single number |

#### D2. Per-seat viewing angles

- Horizontal angle subtended: atan2(x_R − x_s, d) − atan2(x_L − x_s, d).
- Vertical angle to the image top: atan((z_top − z_eye)/d).
- Off-centre angle: atan(|x_s − x_c| / d).

| Seat | HVA | To top | To bottom | Off-centre |
|---|---|---|---|---|
| Row 1, centre seats | 44.5° | 18.1° | −8.0° | 7.0° |
| Row 1, outer seats | 40.7° | — | — | 20.2° |
| Row 2, centre seats | 30.4° | 7.4° | −10.1° | 4.6° |
| Row 2, outer seats | 29.1° | — | — | 13.7° |

**Finding.** Row 1 looks **18° up to the image top**, more than the commonly cited ~15° comfort guidance [verify source]. Options:
- move row 1 back (this conflicts with row 2 and the back wall)
- reduce the screen to about 40° HVA
- lower the image bottom (this conflicts with the centre channel and the sightline)
- go 2.40:1 constant-height, which reduces image height for the same width

The engine should present these as a trade-off table.

#### D3. Sightline and riser height

```
z_eye2,min = z_b + (z_eye1 + C − z_b) · (y2 − y_s)/(y1 − y_s)
riser = z_eye2,min − h_eye
```

where z_b is the image bottom and y_s is the screen plane.

**Example:** z_b = 0.61, z_eye1 = 1.10, C = 0.12, y1 − y_s = 3.50, y2 − y_s = 5.30 → z_eye2 = 1.534 m → riser 0.434 m (17.1″). Adopt **18″ (0.457 m)**, rounded up to construction increments.

- **Validation:** riser < ceiling clearance. Row-2 standing headroom here: 2.438 − 0.457 = 1.98 m. Check against code and comfort: flag < 2.0 m.
- Stagger option: offsetting row-2 seats by half a seat lets C be reduced. Model as a per-seat check.
- **Class G.**

#### D4. Image placement constraints

- Image top ≤ ceiling − masking/border. Here 0.197 m above the image is free.
- Image bottom ≥ the front-row sightline and ≥ the clearance needed over the centre channel or stage.
- For AT screens, the speaker cavity behind needs a minimum depth (product + gap). The 0.30 m assumed must hold SCL-2 grille depth plus spacing [verify the manufacturer's recommended gap].

#### D5. Projector throw

```
D_throw = TR × W_img        for TR ∈ [TR_min, TR_max]
```

**Example (JVC DLA-NZ8):** 1.43–2.92 → 4.15–8.47 m, so the lens plane can sit anywhere from y = 4.45 m to 8.77 m. The chosen lens at y = 6.50 m gives a throw ratio of 2.14. In range.

The published throw range varies between sources (1.35–2.75 vs 1.43–2.92). **The engine must use the manufacturer's own calculator data and record the lens-centre reference point.**

#### D6. Lens shift

```
Vertical offset % = (z_lens − z_img,centre) / H_img × 100
```

Must be within the published range. **Example:** (2.188 − 1.426)/1.631 = **46.8%**, within ±80%. Shift-percentage definitions differ by manufacturer (relative to image height vs half-height). Store the definition with the spec. Combined H+V shift is often limited to an ellipse or diamond [verify per model].

#### D7. Beam clearance

```
z_beam_bottom(y) = z_b + (z_lens − z_b) · (y − y_s)/(D_throw)
```

**Example:** at row 2, the lower beam edge is 1.96 m. Seated heads (1.69 m) clear it. **A standing person (1.80 m) on the 18″ riser, 2.26 m total, blocks the image.** Flag it. Options: raise the lens (limited by the 8′ ceiling), move the projector behind row 2, or accept it.

#### D8. Screen luminance

```
L_fL   = Φ_lm × k × G / A_ft²
L_cd/m² = L_fL × 3.426
```

Here k is the calibrated-to-rated light factor: calibration loss (D65), lens zoom position and laser ageing. It is typically 0.45–0.75 and **an explicit assumption**. G is the screen gain (AT screens are often below 1).

| Scenario | Result |
|---|---|
| 2,500 lm, k = 0.65, G = 1.0, A = 50.9 ft² | **31.9 fL (109 cd/m²)** |
| G = 0.85 | 27.1 fL (93 cd/m²) |
| k = 0.45 | 22.1 fL (76 cd/m²) |

Compare against the SDR cinema reference of 14 fL / 48 cd/m² (SMPTE ST 431-1/RP 431-2 [verify]) and project-chosen HDR targets. RP23 luminance levels are reportedly not yet published [verify].

Limitations: a uniform Lambertian-gain approximation. No hotspotting and no angular gain falloff for off-axis seats. **Class E. Class M after calibration with a luminance meter.**

#### D9. Ambient light and contrast (Tier 2)

```
Contrast_eff ≈ (L_white + L_amb) / (L_black + L_amb)
L_amb = E_amb × G × ρ / π
```

Requires the room's light reflectance (dark finishes). Class E.

#### D10. Resolution and visual acuity

```
d_max,resolve = (W_img / N_px) / tan(1′)
```

**Example:** 4K (3,840 px) on 2.899 m → pixel 0.755 mm → 2.6 m. Both rows (3.5 and 5.3 m) sit beyond the distance where individual 4K pixels resolve. This is useful in client conversations about "4K vs 8K e-shift". Class G with a model assumption (20/20 vision).

#### D11. Acoustically transparent screen effects

- Insertion-loss data (dB vs frequency) and comb-filter risk from the speaker-to-screen gap go in the catalog per screen material.
- SPL calculations subtract the insertion loss for channels behind the screen.
- If the data is missing, flag it. Typical values above 10 kHz are 1–3 dB [verify per material].

---

## 4. Calculation dependency summary

```
Room (B1) ─► Modes (B2), Schroeder (B3), RT60 (B4) ─► Room constant (B5) ─► SPL correction (C5)
Seats (A1) ─► Sightline/riser (D3) ─► ear heights ─► A2/A4/A5 placement ─► C2–C7 audio ─► C10–C12 amps/cables
Screen (D1) ─► D2 angles, D4 placement ─► D5 throw ─► D6 shift ─► D7 beam ─► D8 luminance
Speakers placed (A4) ─► reflections (B6) ─► treatment (B7) ─► RT60 (B4)
Sub positions ─► modal seat response (B8) ─► C8 sub output
```

Any upstream edit invalidates and recomputes downstream nodes. The full graph comes in Phase 5.

---

## 5. Validation and testing strategy

| Layer | Method |
|---|---|
| Unit tests | Every formula has hand-worked vectors (this document plus `reference_calcs.py`), tolerance 1e-6 for G-class |
| Cross-check | Independent tools: projector-manufacturer throw calculators, a room-mode calculator, REW room simulation for B8, a second engineer's spreadsheet |
| Property tests | Symmetry (mirrored room gives mirrored results), unit invariance (ft vs m inputs give identical SI results), monotonicity (bigger screen gives bigger angles) |
| Regression | Golden-project snapshots, including this reference project, per catalog and rule-set version |
| Field validation (Tier 2+) | Compare predicted vs measured for at least 5 completed CHT rooms: SPL at RSP, seat spread, RT60, bass SD. Publish error bands, then tighten the class-E uncertainty bands |

---

## 6. Reference project: issues the engine surfaced

| # | Finding | Impact | Decision needed |
|---|---|---|---|
| 1 | 4 tops can't serve both rows under an 8′ ceiling (A5: 38% seat-channel compliance) | Immersive effect degraded for row 2 | 7.2.6 (fits the SDP-58) vs accepting the compromise vs other processors |
| 2 | One surround pair can't serve both rows | Row 2 side surrounds at 67°–74° | Extra surround pair or arrays (processor-dependent) |
| 3 | Ceiling and surround speakers may not reach 105 dB peaks (C4/C5, ±3 dB) | Reference level not guaranteed | Target level; larger models or more units; need max-SPL data |
| 4 | Row 1 vertical angle 18° to the image top | Neck comfort | Screen size or aspect ratio, row-1 position |
| 5 | Standing person on row 2 blocks the projector beam | Usability | Projector location |
| 6 | 2″ panels leave 125 Hz RT60 at about 0.5 s | Bass decay, clarity | Low-frequency treatment budget |
| 7 | 56.3 Hz and 112.5 Hz mode coincidences (L/W = 1.5) | Strong resonances | Multi-sub placement (S3/S4 better than S1), EQ, possibly a different final room width |
| 8 | 9.2.6 exceeds the SDP-58's 16 outputs | Upgrade path | Processor choice if future growth is wanted |
| 9 | 15 m runs need 12 AWG or heavier to meet the 5% rule | Cable spec | Rack location |

---

## 7. Data still required before a construction-ready design

1. Finished dimensions, the construction section, and wall and ceiling build-ups (framing depth, concrete vs stud, joist direction and spacing, soffits and ductwork, doors, egress).
2. Seat model data: eye and ear heights, reclined depth, width.
3. The client's performance target (reference vs −5 dB) and budget band.
4. Screen and projector decisions: aspect ratio, AT material with insertion-loss data, gain, projector model and lens, mount constraints.
5. Product max-SPL and directivity data: JBL SCL-6/SCL-8, the B&W models (and choice of B&W surround), and CTA-2010 sub output data.
6. Tested absorption data for chosen finishes and treatment products.
7. Rack location, cable path lengths, HVAC and electrical capacity for amplification.
8. After construction: measured noise floor, RT60, and frequency response at each seat. These are class M items that close the loop.

---

## 8. Product data sources used in this document

Published specifications, accessed 2026-11-08 via search indexing. They must be verified against manufacturer PDFs before entering the production catalog (Phase 2).

| Product | Key data used | Source |
|---|---|---|
| JBL Synthesis SCL-2 | 92 dB (2.83 V/1 m), 6 Ω, 445 W RMS (CEA-426B), 57 Hz–25 kHz (−6 dB), 147 mm deep, ≥152 mm wall | https://www.jblsynthesis.com/products/loudspeakers/SCL-2-.html ; owner's manual https://www.jblsynthesis.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dwc6c70f95/pdfs/JBL%20SCL-2%20Owners%20Manual%20%2006-Sep-2017%20(1).pdf ; retailer: https://www.audioadvice.com/products/jbl-synthesis-scl-2-2-5-way-in-wall-speaker |
| JBL Synthesis SCL-6 | 91 dB, 4 Ω, 25–200 W recommended, 80° × 80° coverage (2–17 kHz) | https://www.jblsynthesis.com/products/loudspeakers/SCL-6.html |
| JBL Synthesis SCL-7 | 88 dB, 4 Ω, 25–150 W, 90° H × 60° V | https://www.jblsynthesis.com/products/loudspeakers/SCL-7.html ; independent measurements https://www.spinorama.org/speakers/JBL%20Synthesis%20SCL-7/ASR/index_asr.html |
| JBL Synthesis SCL-8 | 85 dB (2.83 V/1 m, 2π), 4 Ω, 25–100 W, 55 Hz–30 kHz, 120° H × 60° V about a 45° axis | https://www.jblsynthesis.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw95c2cca2/pdfs/SC03940_JBL%20Synthesis%20SCL-8%20Spec%20Sheet%20(Update).pdf |
| JBL Synthesis SSW-1 | 2 × 15″, 90 dB/1 W/1 m and 8 Ω per woofer, 2,500 W RMS per woofer, ports tuned 18 Hz | https://www.jblsynthesis.com/on/demandware.static/-/Sites-SYN-US-NCOM-Library/default/dw8988341b/content/news/harman-explore/JBL-SCL-1&-SSW-1-Press-Release.pdf ; https://lenwallisaudio.com/products/cinema/av-speakers/tailored-speakers/in-wall-subwoofers/jbl-synthesis-ssw-1-passive-in-wall-subwoofer/ |
| JBL Synthesis SDA-7120 | 7 ch; 100 W/8 Ω, 140 W/4 Ω all channels driven | https://www.jblsynthesis.com/products/electronics/SDA-7120-.html |
| JBL Synthesis SDP-58 | 16 processed output channels | https://support.jbl.com/on/demandware.static/-/Sites-masterCatalog_Harman/default/dw2906dd8e/pdfs/JBL_Synthesis_SDP-58_Spec_Sheet_V2_072122.pdf |
| B&W CWM8.3 D | 89 dB (reference condition not stated by retailers [verify]), 8 Ω (min 5 Ω), 30 Hz–35 kHz (−6 dB), 200 W recommended | https://www.weybridge-audio.co.uk/products/bowers-and-wilkins-cwm8-3d-in-wall-speaker-each ; https://www.audioadvice.com/bowers-wilkins-cwm8-3-d |
| B&W CCM8.5 D | 88 dB, 8 Ω (min 3.3 Ω), 120 W recommended, 35 Hz–35 kHz (−6 dB), 331 mm cut-out | https://www.bowerswilkins.com/on/demandware.static/-/Library-Sites-bowers_apac_shared/ja_JP/v1727868770909/PDPDocumentation/CCM8-5-D-Information-Sheet.pdf |
| JVC DLA-NZ8 | 2,500 lm; throw ratio 1.43–2.92 (sources differ); lens shift ±80% V / ±34% H | https://www.projectorcentral.com/jvc-dla-nz8.htm |

## 9. Standards and guidance referenced

| Document | Use | Status |
|---|---|---|
| CEDIA/CTA-RP22 v1.2 (Sept 2023) — https://cedia.org/site/assets/files/6057/cedia-cta_rp22_v1_2_sept_2023.pdf | Criteria set (C13), placement rules (A3) | Obtain and read the official text; legal check before compliance claims |
| CTA/CEDIA-CEB23-B (2019); RP23 (in development) | D1–D4 | Acquire |
| Dolby Atmos Home Theater Installation Guidelines; Dolby 7.1.4 setup guides — https://www.dolby.com/siteassets/about/support/guide/setup-guides/7.1.4-in-wall-dolby-atmos-enabled-speaker-placement/7_1_4_in_wall_speaker_setup.pdf | A3 windows, C9 levels | Obtain the current edition; verify all [verify] values |
| ITU-R BS.775, BS.2051 | Alternate rule sets | Free from ITU |
| ISO 354 / ASTM C423; ISO 3382-2 | B4 data and verification | Purchase |
| AES75-2023, CTA-2034, CTA-2010, CEA-426B | C4, C7, C8 data normalization | Purchase or obtain |
| SMPTE ST 431-1 / RP 431-2, EG-18 | D1, D8 references | Purchase |
| EBU Tech 3276 | B4 comparison | Free |
| Gjestland / UNIC, "How to design a cinema auditorium" — https://unic-cinemas.org/fileadmin/CinemaAuditoriumDesign_v1.0.pdf | D3 sightline practice | Free |
| T. Welti, AES papers on multiple-subwoofer optimization | B8 metric | Purchase |
