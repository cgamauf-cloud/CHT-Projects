# Phase 1 — Competitive Application Analysis: The Cinema Designer (TCD)

**Project:** CHT Theater Design Platform: technical discovery
**Document:** Phase 1 functional decomposition and initial requirements matrix
**Status:** Draft v0.1 for internal review
**Date:** 2026-11-08
**Method:** Clean-room functional analysis from public sources only. No access to TCD's source code, private APIs or paid accounts. Nothing was reverse-engineered from binaries or network traffic.

---

## 0. How to read this document

### 0.1 Evidence labels

Every claim about TCD has one of these labels:

| Label | Meaning |
|---|---|
| **[V]** Vendor-confirmed | Stated on thecinemadesigner.com, its shop, its blog, or a vendor press release. |
| **[P]** Press or partner-reported | Stated by trade press (CE Pro, Residential Systems, audioXpress, etc.) or a partner (Trinnov, D-Tools, manufacturers). Usually based on vendor press material. |
| **[U]** User-reported | Forum posts (AVS Forum). Anecdotal and may be out of date. |
| **[I]** Inferred | Our engineering inference about how a function *must* work to produce the documented output. **This is not a claim about TCD's implementation.** |
| **[G]** Gap | Unknown. Needs authorized hands-on access or vendor clarification. |

### 0.2 Research limitations (important)

1. **Direct page fetching was blocked in this research environment.** thecinemadesigner.com, cepro.com, avsforum.com, residentialsystems.com and the other trade sites could not be loaded directly. Evidence was gathered through search-engine indexing of those pages: titles, snippets and summarized excerpts. Confidence is therefore lower than for a direct read. Each [V]/[P] item should be re-verified against the live page before it is quoted externally. Section 9 lists what to verify.
2. **No sample TCD report was available.** Report contents are reconstructed from the vendor's features page and user descriptions.
3. **Much of the trade coverage dates from 2016–2019.** The newest dated vendor material found is the **TCD 2.5** update (features going live **June 2024**). No evidence of a "TCD 3.0" was found as of this date.
4. **Pricing differs between storefronts and over time.** All prices must be re-checked.

---

## 1. Executive summary of TCD (functional level)

**What it is.** The Cinema Designer is a cloud-based, browser-delivered tool for designing dedicated home cinemas and media rooms "in minutes" [V][S1][S2]. The integrator enters room dimensions, seating, screen and projector choices, and selects loudspeakers, subwoofers and electronics from a manufacturer database. TCD then computes speaker positions, screen size and height, sightlines and riser heights, projector throw, amplifier power, predicted SPL per seat, room modes and RT60. It produces a branded PDF or Word design report with CAD drawings and 3D renders [V][P][S1][S5][S8].

**Lineage.**

| Date | Event | Source |
|---|---|---|
| Feb 2016 | Launched at ISE 2016 by UK developer Guy Singleton | [P][S9] |
| 2017 | D-Tools SI 2017 CSV export integration | [V][P][S12][S13] |
| 2017–2019 | Manufacturers join the database: Steinway Lyngdorf (Dec 2017), PMC (Jul 2018), AudioControl, James Loudspeaker, Legacy Audio, Acurus, Paradigm/Anthem, Origin Acoustics (Jan 2019) | [P][S16–S20] |
| Aug 2018 | **CEDIA acquires TCD** and renames it *The CEDIA Designer*. CEDIA members get the base tier free. | [P][S10][S11] |
| ~2019 | Spanish documentation, soundbar products, "Project Progress", immersive VR renders (Cinema Room Pro tier) | [P][S14] |
| 2022 | CEDIA transfers ownership back to Guy Singleton. The name reverts to *The Cinema Designer*. | [P][S11][S15] |
| 17 Mar 2023 | **TCD 2.0**: 3D room model, bass and room-mode waveforms showing nulls, interactive speaker layouts that update with the listening position. Acoustic treatment zones were slated for April 2023. | [P][S6][S7] |
| Jun 2024 | **TCD 2.5**: Trinnov WaveForming, heat maps and polar plots (selected manufacturers), additional surrounds, loudspeaker position adjustments, acoustic-treatment placement (selected manufacturers), channel updates | [V][P][S3][S4][S21] |

**Design basis claimed.** Output is designed to follow **CTA/CEDIA CEB-22** (Home Theater Audio) and **CEB-23** (Home Theater Video) recommended practices "as well as several ITU documents" [P][S5][S8]. CEB-22 has since been superseded in practice by **CEDIA/CTA-RP22 (Immersive Audio Design RP)**, currently **v1.2, September 2023** [S30]. **[G]** We found no public evidence that TCD has re-based on RP22 levels.

**Scale claimed.** Up to **32 channels** of Dolby Atmos / DTS:X design [V][P][S1][S22].

**Commercial model.** Per-seat subscriptions in two main tiers. **Media Room** is the base tier and **Cinema Room Pro** is the full tier. A "Media Room Pro" tier appeared on the CEDIA-era pricing page [V][S23–S26]. Subscriptions now include "unlimited designs, edits and renders" [V][S2].

| Tier | Current shop (GBP, re-verify) | CEDIA-era page (USD, historical) |
|---|---|---|
| Media Room | £45/month; £425/year | $150/use · $55/month · $625/year (non-member) |
| Cinema Room Pro | £75/month (3-month minimum); £175 for a single month; £630/year | $300/use · $100/month · $850/year (non-member); member $145 / $65 / $500 |

Older reports quote £60/month for 30 uses and £710/year [U][P].

**Difficulty of building a competitor (preliminary).** TCD's *visible* math is mostly well-documented, closed-form engineering:

- geometric speaker placement against published angle windows
- inverse-square SPL
- rectangular-room mode equations
- Sabine/Eyring RT60
- throw-ratio and screen-geometry trigonometry

That math is **not** the hard part. The hard and defensible parts are:

1. **The manufacturer data asset.** Licensed, normalized, verified specs, and, for heat maps and polar plots, measured directivity data. Building this took TCD years of manufacturer sign-ups.
2. **A rules engine** that encodes RP22/RP23/Dolby/DTS/Auro placement rules, conflict resolution and constraint relaxation in a maintainable, testable way.
3. **Geometry and documentation:** one engineering model that drives the 2D CAD, 3D, DXF and a 35-page branded report consistently.
4. **Trust:** defensible, validated predictions, and honesty about what a simplified model cannot predict, especially below the Schroeder frequency.

**Preliminary feasibility verdict.** A CHT-internal tool matching TCD's Media Room scope is a realistic small-team build. Phase 8 will provide estimates. Matching Cinema Room Pro *and* exceeding it on rigor (RP22-level classification, multi-seat coverage from measured directivity, non-rectangular rooms) is a multi-year effort. Its pacing item is data licensing, not code.

---

## 2. TCD workflow as publicly described

Reconstructed from [S5][S8][S27][U]. Ordering is **[I]**.

```
Project / client  ──►  Room shell (W × L × H, units)  ──►  Room type (Media Room | Cinema)
       │
       ▼
Seating: rows, seats per row, seat model (manufacturer), arm width, seat depth, gap,
         riser height & step rise (tiered, Pro)  ──►  RSP / MLP defined
       │
       ▼
Screen: fixed, AT or non-AT, custom size or calculated  ──►  height adjust, sightlines, viewing angles
       │
       ▼
Projector: model + lens  ──►  throw calc  ──►  mount (ceiling | pole | motorized in-ceiling)
       │
       ▼
Audio format / channel layout (up to 32 ch)  ──►  "Calculate speaker placement"  (re-run on change [V/U])
       │
       ▼
Speaker & sub selection from manufacturer DB  ──►  per-seat SPL table, max variance, amp power + headroom
       │
       ▼
Acoustics: room modes, bass/mode waveforms, RT60, treatment zones (absorb / diffuse / reflect / bass)
           Trinnov WaveForming option; heat maps / polar plots (selected brands)
       │
       ▼
Outputs: 3D viewport, true-to-room renders, VR renders, 3D CAD DXF, PDF/Word report (~35 pp),
         D-Tools SI CSV (pricing, tax, labor)
```

User-reported behavior worth noting:

- A change to projector, seating or seat distance requires pressing **"calculate speaker placement"** again [V-FAQ/U]. This suggests a **batch, not reactive**, dependency model. That is an opportunity for CHT (see Phase 5).
- There are constraints on how far ceiling and surround speakers can be moved [U].
- Speaker dispersion was **not modeled** at the time of the forum post. It later arrived partially, via manufacturer-supplied heat maps and polar plots, for selected brands only [U][P].
- The tool has "internal rules that you might not agree with" [U].

---

## 3. Subsystem decomposition (the 16 subsystems)

Complexity scale: **L** = days to 2 weeks · **M** = 2–6 weeks · **H** = 1–3 months · **VH** = more than 3 months or needs specialist validation. Each estimate covers one subsystem built to production quality by an experienced engineer. Phase 8 refines them.

### 3.1 Project creation and management

| Aspect | Detail |
|---|---|
| Purpose | Container for client, site, room, revisions and outputs. Multi-design accounts. |
| TCD evidence | Account holds multiple designs, each with an export button [V][S13]. "Project Progress" feature [P][S14]. Unlimited designs and edits per subscription [V][S2]. Spanish-language documentation [P]. |
| User inputs | Client and site info, project name, designer, units, language, branding. |
| Data required | Company profile and logo for branding. |
| Calculations | None. |
| Standards | None. |
| Outputs / deps | Feeds report headers and BOM export. Every other subsystem hangs off the project. |
| Complexity | **L–M** (M with revisions, audit trail and multi-user). |
| Confirmed vs inferred | Multi-design and export confirmed. Revision history, collaboration, roles **[G]**. |

### 3.2 Room dimensions and geometry

| Aspect | Detail |
|---|---|
| Purpose | Define the acoustic and visual shell. |
| TCD evidence | Room dimensions are entered [V][S27]. 3D room model since 2.0 [P][S6]. 3D CAD DXF of the room is a feature [V][S2]. |
| User inputs | Width, length, height, units (metric and imperial; report shows mm and inches [V]). Probably doors, soffits, columns **[G]**. |
| Data required | None beyond user inputs. |
| Calculations | Volume, surface areas, ratios. Feeds modes and RT60. |
| Standards | Room-ratio literature (Bolt, Louden, Sepmeyer; EBU Tech 3276 for listening rooms) as reference; no compliance claim. |
| Outputs / deps | Drives everything downstream. |
| Complexity | **M** for rectangular; **H–VH** for arbitrary polygons, sloped or coffered ceilings, and openings. |
| Confirmed vs inferred | **Rectangular shoebox is the evident model [I]**; we found no evidence of non-rectangular support. Doors, windows, soffits **[G]**. |

### 3.3 Seating and riser configuration

| Aspect | Detail |
|---|---|
| Purpose | Place rows and seats, set the RSP/MLP, ensure sightlines. |
| TCD evidence | User adjusts distance, arm width, seat depth, riser height and seat gap "until sightlines work" [P][S5][U]. Tiered seating with user-set riser height and step rise is a Pro feature [V][S2]. Manufacturer seating appears in renders [P][S5]. |
| User inputs | Rows, seats per row, seat model or dimensions, gaps, aisle, riser heights, step rise, eye/ear height. |
| Data required | Seat catalog: width, arm width, depth reclined and upright, seated eye/ear height. |
| Calculations | Seat coordinates; per-row eye and ear height; sightline clearance over the head in front to the screen bottom edge; riser height needed for a target clearance. |
| Standards | CEB-23-B / RP23 (seating relative to screen), RP22 (RSP definition via CEB-23-B [S30]), THX/SMPTE sightline guidance. |
| Outputs / deps | RSP drives speaker angles, SPL per seat, viewing angles and screen height. |
| Complexity | **M**. |
| Confirmed vs inferred | Inputs confirmed. The sightline algorithm **[I]** is standard: it compares the line from the eye to the screen bottom against the top of the head of the row in front. |

### 3.4 Speaker configuration and placement

| Aspect | Detail |
|---|---|
| Purpose | Choose a layout (e.g. 7.2.4) and compute recommended positions. |
| TCD evidence | Automatic placement via "calculate speaker placement" [V-FAQ]. Up to 32 channels for Atmos/DTS:X [V][S1]. "High render channel count" update [P][S22]. A table of speaker positions with distances from the seating position (mm and inches) [V][S2]. In-room floor-standing speakers are an option [V][S2]. Layouts update with the listening position (2.0) [P][S6]. Position adjustments and additional surrounds (2.5) [P][S3]. |
| User inputs | Format and channel layout, mounting type per channel (in-wall, on-wall, in-ceiling, floor-standing, behind an AT screen). |
| Data required | Placement rules: Dolby (Atmos home guidelines, e.g. overhead elevation window commonly cited as 30°–55° [S32]), DTS:X, Auro-3D, RP22 layouts [S30]. Speaker physical dimensions. |
| Calculations | Azimuth and elevation from RSP to each speaker; snap to wall and ceiling surfaces; conflict checks (screen, doors, rows); distance per speaker; angle-to-seat for all seats. |
| Standards | Dolby Atmos Home Theater Installation Guidelines (2014 and Dec 2018 editions found [S32]), ITU-R BS.775 / BS.2051, RP22 v1.2. |
| Outputs / deps | Positions feed SPL, coverage, amplifier channel count, cable schedule, drawings. |
| Complexity | **H** (rules engine + constraint solving + many layouts). |
| Confirmed vs inferred | Output tables confirmed. The algorithm (rule-based angle windows plus surface projection) is **[I]**. Movement constraints exist [U]. |

### 3.5 Speaker manufacturer and model selection

| Aspect | Detail |
|---|---|
| Purpose | Select real products per channel role. |
| TCD evidence | Manufacturer database; brands join by agreement [P][S16–S20]. Soundbars added [P]. Loewe displays added [V][S28]. |
| User inputs | Brand and model per channel or group. |
| Data required | Sensitivity, impedance, max SPL, power handling, dimensions, mounting type, dispersion; polar data for heat maps (selected brands) [P]. |
| Calculations | Filtering by mounting type and room role; compatibility checks. |
| Standards | None directly. Spec measurement conventions (e.g. sensitivity at 2.83 V / 1 m) matter for comparability. |
| Outputs / deps | Feeds SPL, amplifier sizing, BOM, renders. |
| Complexity | UI **M**; data acquisition **VH** (ongoing). |
| Confirmed vs inferred | Database confirmed. Exact fields **[G]**; Phase 2 will specify ours. |

### 3.6 Subwoofer placement and system design

| Aspect | Detail |
|---|---|
| Purpose | Choose sub count and positions for even bass across seats. |
| TCD evidence | Multiple subwoofers [V][S2]. Bass and mode waveforms show nulls (2.0) [P][S6]. Trinnov WaveForming placement built in (2.5) [P][S3][S21]. M&K X+/V+ subs added [V]. |
| User inputs | Sub count, model, candidate positions. |
| Data required | Sub max output (e.g. CEA-2010 style), dimensions, frequency extension. |
| Calculations | **[I]** Likely modal pressure at seats for candidate positions (e.g. midpoints of walls, quarter positions) using the analytic rectangular-room modal sum. WaveForming uses Trinnov's documented placement rules. |
| Standards | RP22 bass parameters [S30]. Welti / Harman multi-sub research (Todd Welti, AES papers) as the reference basis. |
| Outputs / deps | Sub positions, predicted seat-to-seat bass variation. Depends on room geometry and seating. |
| Complexity | **H** (simple modal model); **VH** with optimization and boundary-element accuracy. |
| Confirmed vs inferred | Feature confirmed. Algorithm **[I]**/**[G]**. |

### 3.7 Acoustic modeling and treatment

| Aspect | Detail |
|---|---|
| Purpose | Predict modes and RT60; recommend treatment. |
| TCD evidence | Room-mode calculations [V][S2]. RT60 calculation [P][S7]. Treatment within predefined zones for absorption, diffusion, reflection and bass management [P][S6]. Treatment placement for selected manufacturers (2.5) [P][S3]. Documentation says "what kind of acoustical materials to use" [P][S8]. |
| User inputs | Surface finishes and materials, treatment products, target RT60. |
| Data required | Absorption coefficients per octave band (125 Hz–4 kHz) for materials and panels; diffuser data. |
| Calculations | Axial, tangential and oblique modes (f = c/2 · √((nx/Lx)² + (ny/Ly)² + (nz/Lz)²)); Sabine and Eyring RT60; first-reflection points (image source); treatment coverage percentage. |
| Standards | ISO 354 (absorption coefficient measurement), ISO 3382 (RT measurement), RP22 references AES75-2023 and ANSI/ASA S12.2-2008 (room noise) [S30]. |
| Outputs / deps | Mode table and plots, RT60 estimate, treatment layout. Depends on room geometry and speaker positions (reflection points). |
| Complexity | **M** (modes and Sabine) to **VH** (credible predictions plus treatment optimization). |
| Confirmed vs inferred | Outputs confirmed. Models **[I]**: the shoebox modal and Sabine approach is almost certain given rectangular inputs. |

### 3.8 Screen sizing and placement

| Aspect | Detail |
|---|---|
| Purpose | Size the screen for the seats and set its height. |
| TCD evidence | Calculated or custom screen size; AT and non-AT fixed screens; fixed-screen vertical height adjustment; sightlines and viewing angles [V][S2]. |
| User inputs | Aspect ratio (16:9, 2.35/2.40:1), AT or not, masking **[G]**, custom size. |
| Data required | Screen catalog: sizes, aspect ratio, gain, AT, frame border, depth. |
| Calculations | Width from target horizontal viewing angle at RSP: W = 2·d·tan(θ/2). Vertical angle to the top of the image. Bottom-edge height vs front-row sightline. AT speaker cavity depth. |
| Standards | CEB-23-B (2019) / RP23 (in progress) [S31]; SMPTE EG-18 / RP 166; THX. Cited angle targets range from about 30° to 62°, and **sources disagree** [S31]. |
| Outputs / deps | Screen width and height, bottom-edge height, viewing angles per seat. Feeds projector throw, luminance and LCR placement. |
| Complexity | **M**. |
| Confirmed vs inferred | Features confirmed. The target-angle rules TCD uses **[G]**. |

### 3.9 Projector selection and throw calculation

| Aspect | Detail |
|---|---|
| Purpose | Verify that the projector and lens can fill the screen from feasible positions. |
| TCD evidence | Projector and lens info entered; lens throw calculation; placement options on-ceiling, pole-mounted or motorized in-ceiling [V][S2][U]. |
| User inputs | Projector model and lens, mount type, ceiling constraints. |
| Data required | Throw-ratio range (min/max), lens shift (vertical and horizontal %), lumens (ISO 21118 / ANSI), body dimensions, lens offset from the body center. |
| Calculations | Throw distance D = TR × image width (at min and max zoom); lens-shift feasibility for lens height vs screen center; anamorphic options; clearance to the rear wall and rows. |
| Standards | ISO 21118 (data projector specs); manufacturer calculators. |
| Outputs / deps | Projector position. Feeds luminance (3.11), rack and cable, drawings. |
| Complexity | **M**. |
| Confirmed vs inferred | Throw confirmed. Lens-shift checks and **luminance (fL / nits) calculation [G]**: no public mention found. |

### 3.10 Amplifier and processor selection

| Aspect | Detail |
|---|---|
| Purpose | Select an AVR or processor and amplifiers with enough channels and power. |
| TCD evidence | In-tool amplifier power calculation for required SPL and headroom [V][S2][S5]. Specifies amplification and processor requirements [P][S7]. Partners include processor and amplifier brands (Anthem, Acurus, AudioControl, Trinnov/JBL Synthesis WaveForming context) [P]. |
| User inputs | Target reference level, headroom, preferred brands. |
| Data required | Processor: decoded and processed channel count, formats, bass management, room correction, outputs. Amplifier: channels, power at 8 Ω/4 Ω, bridging. |
| Calculations | Required power per channel: P = 10^((SPL_target + headroom − sens + 20·log10(d/1 m)) / 10) W (with corrections for sensitivity reference and array gain). Channel-count matching; impedance compatibility. |
| Standards | RP22 SPL-capability parameters per level [S30]; Dolby reference level (85 dB SPL at −20 dBFS per channel, i.e. 105 dB peaks; subs +10 dB LFE). |
| Outputs / deps | Electronics BOM, rack load, power and heat. Depends on speakers, distances and target. |
| Complexity | **M** (power math); **H** with full compatibility rules. |
| Confirmed vs inferred | Power calculation confirmed. Processor channel-count validation **[G]**. Thermal and electrical load **[G]**. |

### 3.11 System performance validation

| Aspect | Detail |
|---|---|
| Purpose | Prove the design meets targets. |
| TCD evidence | Table of SPL and **maximum variance per channel and seat** (passive speakers) [V][S2]. Heat maps and polar plots on the 3D viewport vs MLP and other seats (selected brands) [P][S3][S21]. |
| User inputs | Target level or class. |
| Data required | Directivity data (spinorama or polar) for off-axis per-seat SPL. |
| Calculations | Per-seat SPL = on-axis SPL − 20·log10(d/d_ref) − off-axis loss(θ, φ, f). Seat-to-seat variance. |
| Standards | RP22 v1.2: 21 parameters and 4 levels [S30]. **TCD's public material cites CEB-22, not RP22 levels [G].** |
| Outputs / deps | Pass/fail or class per parameter. |
| Complexity | **H**; **VH** for a defensible RP22 level-classification claim (needs the licensed document and validation). |
| Confirmed vs inferred | SPL table and variance confirmed. Level classification **not evidenced**. |

### 3.12 Automated equipment recommendations

| Aspect | Detail |
|---|---|
| Purpose | Suggest products that meet constraints. |
| TCD evidence | "TCD does the rest, configuring a room that makes sense for the stated characteristics" [P][S8]. Explicit auto-recommendation of *models* **[G]**: evidence suggests the user selects products and TCD computes. |
| Data required | Full catalog with normalized specs; budget data. |
| Calculations | Constraint filtering + scoring (SPL capability vs target, size fit, budget). |
| Complexity | **H**. |
| Confirmed vs inferred | Mostly **[G]**. This is a likely **CHT differentiation opportunity**. |

### 3.13 CAD drawings and dimensioned layouts

| Aspect | Detail |
|---|---|
| Purpose | Installer-grade plans and elevations. |
| TCD evidence | CAD drawings in the report [P][U]. **3D CAD DXF of the room** [V][S2]. D-Tools later "extends AV system design and CAD drawing services" with TCD [P][S29]. |
| Outputs | Plan view, elevations (screen wall), sections (risers), dimensioned speaker positions. |
| Complexity | **H** (dimensioning and annotation is labor-intensive); DXF export **M**. |
| Confirmed vs inferred | DXF confirmed. Sheet set, layering and title blocks **[G]**. |

### 3.14 Interactive 3D visualization

| Aspect | Detail |
|---|---|
| Purpose | Client communication and design checking. |
| TCD evidence | 3D wireframe renders in reports [V][S1]. 3D room model and viewport (2.0) [P]. "True-to-room" renders including the manufacturer's seating [P][V][S5]. Immersive VR renders (Cinema Room Pro) [P][S14]. Heat-map overlay on the viewport [P]. |
| Complexity | **M** (viewer) to **H** (photoreal and VR renders with a product model library). |
| Confirmed vs inferred | Confirmed. Rendering technology **[G]**. |

### 3.15 Proposal and engineering report generation

| Aspect | Detail |
|---|---|
| Purpose | Client-ready and installer-ready documentation. |
| TCD evidence | PDF or Word download with 3D wireframes and drawings [V][S1]. ~35-page report with CAD drawings and 3D renders [U]. Content: speaker positions, seating, acoustic materials, mounting [P][S8]. |
| Complexity | **M–H**. |
| Confirmed vs inferred | Formats confirmed. Templates, branding and revision tracking **[G]**. |

### 3.16 Equipment lists, BOM and estimating integration

| Aspect | Detail |
|---|---|
| Purpose | Bridge from design to sales. |
| TCD evidence | Per-design CSV export formatted for **D-Tools System Integrator 2017** import. It enables local-area pricing, tax, labor and costs **in D-Tools** [V][P][S12][S13]. |
| Complexity | **L–M** per target system (D-Tools SI / Cloud, Portal.io, SimPRO, etc.). |
| Confirmed vs inferred | Confirmed for SI 2017. Current D-Tools Cloud compatibility **[G]**. |

---

## 4. Functional feature matrix: TCD vs proposed CHT platform

Tier key for CHT: **T1** = MVP · **T2** = Professional Integrator · **T3** = Reference-grade / SaaS (see Phase 8).

| # | Capability | TCD | Evidence | CHT target | CHT design intent / differentiation |
|---|---|---|---|---|---|
| 1 | Cloud, browser-based | Yes | V | T1 | Same |
| 2 | Multi-project account | Yes | V | T1 | Plus client/site records |
| 3 | Revision history and audit trail | ? | G | T1 | Immutable design versions; diff between revisions |
| 4 | Multi-user, roles, firm accounts | ? | G | T2 | Role-based (designer, sales, installer, reviewer) |
| 5 | Rectangular room | Yes | V/I | T1 | Same |
| 6 | Non-rectangular rooms, soffits, sloped ceilings | Not evidenced | G | T3 | Polygon plan plus ceiling planes; modal model flagged as approximate |
| 7 | Doors, windows, columns, obstructions | ? | G | T1 | Required for credible placement and collision checks |
| 8 | Metric and imperial | Yes | V | T1 | Internal SI (mm); display in either |
| 9 | Multi-row seating | Yes | V | T1 | Same |
| 10 | Tiered risers with sightline solving | Yes (Pro) | V | T1 | Auto-solve riser height for target clearance |
| 11 | Manufacturer seating catalog | Yes | P | T2 | — |
| 12 | Auto speaker placement | Yes, batch recalc | V/U | T1 | **Reactive dependency graph** (no manual recalc) |
| 13 | Layouts to 32 channels | Yes | V | T1 up to 9.x.6; T3 beyond | — |
| 14 | Dolby / DTS:X / Auro-3D rules | Atmos and DTS:X claimed; Auro **[G]** | V/G | T1 Atmos; T2 DTS:X/Auro; T3 IMAX Enhanced | Rules versioned with source citations |
| 15 | Placement tolerance display (preferred vs acceptable) | ? | G | T1 | Show angle-window compliance per speaker per seat |
| 16 | Speaker database | Yes, manufacturer-joined | P | T2 | Plus provenance and confidence per field |
| 17 | Directivity-based coverage and heat maps | Partial (selected brands) | P | T2 basic / T3 measured | Generic-pattern fallback clearly labeled |
| 18 | Per-seat SPL table and variance | Yes (passive) | V | T1 (on-axis) / T2 (off-axis) | — |
| 19 | Amplifier power for SPL plus headroom | Yes | V | T1 | Show the formula and assumptions in the report |
| 20 | Processor channel and format validation | ? | G | T2 | Decoded vs processed vs output channel checks |
| 21 | Impedance and load compatibility | ? | G | T2 | — |
| 22 | Multi-subwoofer design | Yes | V | T2 | Modal seat-variance optimizer |
| 23 | Trinnov WaveForming | Yes (2.5) | P | T3 (partner-dependent) | Requires a Trinnov relationship |
| 24 | Room modes | Yes | V | T1 | — |
| 25 | RT60 | Yes | P | T2 | Sabine plus Eyring, octave bands |
| 26 | First-reflection points | ? | G | T2 | Image-source per speaker per seat |
| 27 | Treatment zones and product placement | Yes (selected brands) | P | T2 | — |
| 28 | Screen size, AT/non-AT, height, viewing angles | Yes | V | T1 | Show multiple standards' targets side by side |
| 29 | Projector throw and mount options | Yes | V | T1 (throw) / T2 (shift, clearance) | — |
| 30 | Screen luminance (fL / nits), gain, HDR | Not evidenced | G | T2 | **Likely differentiator** |
| 31 | Displays (TVs) for media rooms | Yes (e.g. Loewe) | V | T2 | — |
| 32 | Soundbars | Yes | P | T3 | Low priority for CHT |
| 33 | Automated product recommendations | Limited / unclear | G | T2 | Rules plus scoring; explainable |
| 34 | RP22 level classification | Not evidenced (cites CEB-22) | G | T3 | Only after licensing and validation |
| 35 | 3D viewport | Yes | P | T2 | — |
| 36 | Photoreal / "true-to-room" renders | Yes | P/V | T3 | — |
| 37 | VR renders | Yes (Pro) | P | T3 / optional | — |
| 38 | 2D dimensioned CAD sheets | Yes | U/P | T1 (basic plan) / T2 (full set) | — |
| 39 | DXF export | Yes (3D room) | V | T2 | 2D sheets plus 3D |
| 40 | PDF report | Yes | V | T1 | — |
| 41 | Word report | Yes | V | T2 | — |
| 42 | Custom branding and templates | Probable | G | T1 (CHT brand) / T3 (per-tenant) | — |
| 43 | Cable and infrastructure schedule | Not evidenced | G | T2 | Speaker wire gauge vs run length, HDMI/fiber, conduit |
| 44 | Rack, power and thermal planning | Not evidenced | G | T2 | — |
| 45 | Installation and calibration checklists | Not evidenced | G | T2 | — |
| 46 | D-Tools CSV export | Yes (SI 2017) | V | T2 | Plus D-Tools Cloud and other estimating tools |
| 47 | Pricing (MSRP/dealer) in the tool | Via D-Tools | V | T2 | Price lists per tenant, never shared |
| 48 | Localization | Spanish docs | P | T3 | — |
| 49 | API / integrations | ? | G | T3 | Public API |
| 50 | AI assistance | Not evidenced | — | T2/T3 | Spec extraction, narrative drafting only; **never** a source of engineering numbers |

---

## 5. Cross-subsystem dependency map (preliminary; detailed in Phase 5)

```
Room geometry ─┬─► Room modes ─► Sub placement ─► Bass seat variance
               ├─► RT60 ◄── Surface materials / treatment
               ├─► Reflection points ◄── Speaker positions
               └─► Seating/risers ─► RSP ─┬─► Screen size/height ─┬─► Projector throw/shift ─► Luminance
                                          │                       └─► LCR positions (AT cavity)
                                          └─► Speaker positions ─┬─► Per-seat SPL/coverage ◄── Speaker data
                                                                 ├─► Amp power/channels ─► Processor/amp selection ─► Rack/power/heat
                                                                 └─► Cable schedule ─► BOM ─► Report/estimate export
```

Requirement: any upstream change must invalidate and recompute downstream nodes automatically. The UI must show which results are stale or failed (contrast with TCD's manual recalc [V/U]).

---

## 6. Initial requirements matrix (CHT platform)

Priority: **M** = must, **S** = should, **C** = could. Tier = first tier it ships in.

### 6.1 Project and data

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| FR-PRJ-01 | Create, edit and archive projects with client, site, designer and status | M | T1 |
| FR-PRJ-02 | Every saved change creates an immutable revision; revisions can be compared and restored | M | T1 |
| FR-PRJ-03 | Store all geometry internally in SI (mm, m, degrees); display in metric or imperial per user | M | T1 |
| FR-PRJ-04 | Each design records the catalog version and rules version it used, so results are reproducible | M | T1 |
| FR-PRJ-05 | Multi-user firm accounts with roles | S | T2 |
| FR-PRJ-06 | Multi-tenant isolation (data, price lists, branding) | M | T3 |

### 6.2 Room

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| FR-ROOM-01 | Rectangular room by W × L × H | M | T1 |
| FR-ROOM-02 | Doors, windows, columns, soffits and HVAC as keep-out volumes | M | T1 |
| FR-ROOM-03 | Mark dimensions as *concept*, *measured* or *verified* | M | T1 |
| FR-ROOM-04 | Surface material assignment per wall, ceiling and floor | S | T2 |
| FR-ROOM-05 | Polygon floor plans and sloped or stepped ceilings | C | T3 |

### 6.3 Seating and video

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| FR-SEAT-01 | Rows, seats per row, seat dimensions, gaps and aisles; RSP selection | M | T1 |
| FR-SEAT-02 | Compute sightline clearance per row; solve minimum riser height for a target clearance | M | T1 |
| FR-SEAT-03 | Seated eye and ear heights configurable with defaults labeled as assumptions | M | T1 |
| FR-VID-01 | Screen sizing from target viewing angle at the RSP, with selectable guidance source | M | T1 |
| FR-VID-02 | Report horizontal and vertical viewing angles for every seat | M | T1 |
| FR-VID-03 | Screen bottom-edge height from front-row sightline and center-channel clearance | M | T1 |
| FR-VID-04 | Projector throw from throw-ratio range; mount feasibility | M | T1 |
| FR-VID-05 | Lens-shift feasibility check | S | T2 |
| FR-VID-06 | Screen luminance estimate (fL / nits) from lumens, gain, area and lamp/laser aging assumption | S | T2 |

### 6.4 Audio

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| FR-AUD-01 | Layouts 5.1 → 9.1.6 (Dolby Atmos) with preferred and acceptable angle windows, cited per rule | M | T1 |
| FR-AUD-02 | Auto-place speakers onto valid surfaces honoring keep-outs; manual override with live compliance feedback | M | T1 |
| FR-AUD-03 | Per-speaker coordinates, azimuth, elevation, distance to the RSP and to every seat | M | T1 |
| FR-AUD-04 | On-axis per-seat SPL and required amplifier power for a target level plus headroom | M | T1 |
| FR-AUD-05 | Off-axis per-seat SPL from directivity data, with a labeled generic fallback | S | T2 |
| FR-AUD-06 | Processor and amplifier channel, format and impedance compatibility | M | T2 |
| FR-AUD-07 | Multi-sub placement analysis with seat-to-seat modal variance | S | T2 |
| FR-AUD-08 | DTS:X, Auro-3D and >9.x.6 layouts | S | T3 |

### 6.5 Acoustics

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| FR-ACO-01 | Axial, tangential and oblique modes to a user-set frequency limit; Schroeder frequency displayed | M | T1 |
| FR-ACO-02 | RT60 (Sabine and Eyring) per octave band from material coefficients | S | T2 |
| FR-ACO-03 | First-reflection points per speaker and seat | S | T2 |
| FR-ACO-04 | Treatment placement and coverage reporting | S | T2 |
| FR-ACO-05 | Every acoustic output marked as a *model estimate requiring on-site measurement* | M | T1 |

### 6.6 Catalog

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| FR-CAT-01 | Versioned equipment catalog with per-attribute source, date and confidence | M | T2 (manual entry in T1) |
| FR-CAT-02 | Calculations degrade gracefully, with explicit warnings, when attributes are missing | M | T1 |
| FR-CAT-03 | Licensed data only; tenant-private pricing | M | T2 |

### 6.7 Outputs

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| FR-OUT-01 | Branded PDF report: summary, BOM, plan, speaker table, seating, video calcs, modes, assumptions | M | T1 |
| FR-OUT-02 | Dimensioned 2D plan and screen-wall elevation (SVG/PDF) | M | T1 |
| FR-OUT-03 | Interactive 3D view from the same model as 2D | S | T2 |
| FR-OUT-04 | DXF export | S | T2 |
| FR-OUT-05 | Word export; reusable report templates | S | T2 |
| FR-OUT-06 | Estimating export (D-Tools CSV first) | S | T2 |
| FR-OUT-07 | Installation and calibration checklists | S | T2 |

### 6.8 Non-functional

| ID | Requirement | Pri | Tier |
|---|---|---|---|
| NFR-01 | Calculation engine is a pure, deterministic, separately versioned library with unit tests against hand-worked examples | M | T1 |
| NFR-02 | No engineering number is produced by an AI model; AI output is advisory text or data-entry assistance with human approval | M | T1 |
| NFR-03 | Each reported value traces to its formula, inputs and source rule (report "assumptions and basis" appendix) | M | T1 |
| NFR-04 | Standards compliance claims require a licensed copy of the standard and a documented validation | M | T1 |
| NFR-05 | Recalculation of a typical 2-row 7.2.4 design in under 500 ms in the browser | S | T1 |

---

## 7. Standards and documents to acquire or license

| Document | Version found | Access | Needed for | Notes |
|---|---|---|---|---|
| CEDIA/CTA-RP22 Immersive Audio Design RP | v1.2, Sept 2023 [S30] | Public PDF at cedia.org (verify terms) | Placement, SPL, bass, levels | 21 parameters, 4 levels. Get legal review before making "RP22 Level N" claims. |
| CTA/CEDIA-CEB23-B Home Theater Video Design | 2019 [S31] | CTA (verify purchase/licensing) | Screen, seating, viewing | RP23 (video) in development; only Level 1 reportedly finished [S31] |
| CTA/CEDIA-CEB22 Home Theater Audio | (superseded by RP22) | CTA | Legacy comparison | TCD's cited basis |
| RP32 (RP22 measurement companion) | Status unconfirmed [U][S30] | — | Verification checklists | Track |
| Dolby Atmos Home Theater Installation Guidelines | Dec 2018 (and 2014) [S32] | Dolby (public PDF) | Layouts, angles | Confirm the latest edition with Dolby |
| DTS:X and Auro-3D speaker layout guides | — | Vendor | Layouts | Acquire |
| ITU-R BS.775-4, BS.2051-3 | — | ITU (free) | Reference layouts | — |
| AES75-2023 | 2023 | AES (purchase) | Max SPL measurement | Referenced by RP22 |
| ANSI/ASA S12.2-2008 | 2008 | ASA (purchase) | Room noise criteria | Referenced by RP22 |
| ISO 354, ISO 3382-1/-2 | — | ISO (purchase) | Absorption data, RT | Data provenance |
| ISO 21118 | — | ISO (purchase) | Projector lumens spec | Spec normalization |
| SMPTE ST 431-1 / RP 431-2, EG-18 / RP 166 | — | SMPTE (purchase) | Luminance and viewing references | Cinema reference only |
| ANSI/CTA-2010 | — | CTA | Subwoofer output | Spec normalization |
| THX certification criteria | — | THX (proprietary) | Optional | Cannot claim THX without a program |

---

## 8. Competitive takeaways for CHT

1. **Do not compete on the 32-channel headline first.** Compete on **traceability**: every number shows its formula, inputs, source and confidence. TCD's public material does not show this. Users report "internal rules you might not agree with" [U].
2. **Reactive recomputation** instead of a "calculate" button.
3. **Measured vs estimated** labeling everywhere, and an on-site verification checklist that closes the loop (design → install → measure → as-built).
4. **Video luminance and HDR**, **cable, rack, power and thermal**, and **calibration checklists** are not evidenced in TCD. They are concrete gaps that matter to an integrator.
5. **Data strategy is the moat.** Start with the brands CHT actually sells. Capture provenance per field. Get written permission before using manufacturer data or 3D models.
6. **RP22 level classification** is a possible flagship differentiator, but **only after** licensing review and validation against measurements.

---

## 9. Knowledge gaps and how to close them

| # | Gap | Method to close (authorized only) |
|---|---|---|
| G1 | Exact current feature-by-tier matrix and prices | Read the live features and pricing pages from an unrestricted network; request a sales demo |
| G2 | A real sample report (structure, tables, drawing set) | Request a sample from TCD sales or an existing TCD-using integrator (with permission); buy one month of Cinema Room Pro (£175) for evaluation, within the ToS |
| G3 | Room-shape support (non-rectangular, soffits, doors) | Trial or demo |
| G4 | Placement rules and tolerances, and whether RP22 is used | Demo questions; compare outputs against Dolby/RP22 for test rooms |
| G5 | Off-axis / coverage modeling depth | Demo with heat-map brands vs non-heat-map brands |
| G6 | Luminance, lens shift, HDR handling | Trial |
| G7 | Processor/amp channel validation, impedance checks | Trial |
| G8 | DXF content (2D sheets vs 3D only), layering | Trial export |
| G9 | Current D-Tools (Cloud) compatibility | D-Tools docs / support |
| G10 | Revision, collaboration and multi-user features | Demo |
| G11 | Data licensing terms between TCD and manufacturers | Not knowable publicly; inform our own manufacturer agreements |
| G12 | Current ownership, roadmap, any v3 | Vendor contact; live news page |

**Terms-of-service caution:** before any trial, review TCD's Terms and Conditions [S33]. Do not copy report templates, wording, graphics or database contents into CHT's product. Record only functional observations, consistent with clean-room practice. Keep the people who view TCD outputs separate from those who write CHT's report templates, or document what they saw.

---

## 10. Next steps (proposed)

1. **Close G1–G4** (1–2 weeks): live-site verification, demo request, decision on a one-month evaluation subscription.
2. **Phase 2 — Equipment database specification**: schema, attribute provenance and confidence model, sample records for CHT's top brands.
3. **Phase 3 — Calculation catalog**: formulas, worked examples, validation rules and test vectors. This becomes the test suite for NFR-01.
4. **Phase 9 reference project (20′ × 30′ × 8′, 7.2.4)**: run it early as the end-to-end acceptance case that every later phase must satisfy.
5. Then Phases 4–8 (UI and geometry, workflow, reports, architecture, roadmap).

---

## 11. Sources

All accessed 2026-11-08 through search indexing; direct fetch was blocked (see §0.2). Dates are publication dates where known.

| ID | Source | Date |
|---|---|---|
| S1 | The Cinema Designer, home page — https://thecinemadesigner.com/ | current |
| S2 | TCD Features and Pricing — https://thecinemadesigner.com/tcd-features-and-pricing/ | current |
| S3 | CE Pro, "Cinema Designer Updates Brings Several New Features" (TCD 2.5) — https://www.cepro.com/briefs/cinema-designer-updates-brings-several-new-features/138311/ | ~2024 |
| S4 | TCD blog, TCD News category — https://thecinemadesigner.com/blog/categories/tcd-news/ | various |
| S5 | CE Pro, "TCD Software Primer: Doing the Home-Theater Math" — https://www.cepro.com/news/home_theater_design_software_a_primer_on_the_cedia_designer/6947/ | ~2019 |
| S6 | audioXpress, "The Cinema Designer (TCD) 2.0 Updates…" — https://audioxpress.com/news/the-cinema-designer-tcd-2-0-updates-expands-original-vision-features-and-functionality | Mar 2023 |
| S7 | Residential Systems, "The Cinema Designer Launches TCD 2.0" — https://www.residentialsystems.com/news/the-cinema-designer-launches-tcd-2-0 | Mar 2023 |
| S8 | CE Pro, "Revolutionary TCD Software Takes Custom Home Theater Design from Weeks to Minutes" — https://www.cepro.com/news/tcd_software_custom_home_theater_design/2212/ | ~2016 |
| S9 | CE Pro, "ISE 2016: New Cinema Design Software…" — https://www.cepro.com/news/cinema_designer_launches_cinema_design_software_tool/696/ | Feb 2016 |
| S10 | Residential Systems, "CEDIA Acquires The Cinema Designer" — https://www.residentialsystems.com/news/cedia-acquires-the-cinema-designer | Aug 2018 |
| S11 | CE Pro, "CEDIA Transfers Ownership of TCD Software Back to Original Creator" — https://www.cepro.com/audio-video/home-theater/cedia-transfers-ownership-tcd-software-back-to-original-creator/ | 2022 |
| S12 | D-Tools, "D-Tools and The CEDIA Designer (TCD) Announce Integration Partnership" — https://www.d-tools.com/resource-center/news-events/d-tools-the-cedia-designer-tcd-announce-intergration-partnership | 2017–18 |
| S13 | TCD blog, "The Cinema Designer releases D-Tools integration" — https://thecinemadesigner.com/blog/posts/the-cinema-designer-releases-d-tools-integration/ | 2017 |
| S14 | Residential Systems, "The CEDIA Designer Adds New Features" — https://www.residentialsystems.com/features/from-the-field/the-cedia-designer-adds-new-features | ~2019 |
| S15 | Monitor Audio, "The CEDIA Designer reverts back to The Cinema Designer" — https://www.monitoraudio.com/pl/blog/the-cedia-designer-reverts-back-to-the-cinema-designer | 2022 |
| S16 | audioXpress, "PMC Joins The Cinema Designer Database…" — https://audioxpress.com/news/pmc-joins-the-cinema-designer-database-for-home-theater-and-media-room-projects | Jul 2018 |
| S17 | Steinway Lyngdorf, "Steinway Lyngdorf joins The Cinema Designer platform" — https://steinwaylyngdorf.com/2017/12/ | Dec 2017 |
| S18 | Legacy Audio, "Legacy Audio joins The Cinema Designer database" — https://legacyaudio.com/news/legacy-audio-joins-the-cinema-designer-database | ~2018 |
| S19 | rAVe, "Origin Acoustics Joins The CEDIA Designer Software and Database" — https://www.ravepubs.com/origin-acoustics-joins-cedia-designer-software-database-2 | Jan 2019 |
| S20 | Home Theater HiFi, "Paradigm, Anthem join The Cinema Designer…" — https://hometheaterhifi.com/press-releases/paradigm-anthem-join-cinema-designer-facilitating-accurate-high-render-channel-count-immersive-audio-home-theatre-designs-minutes/ | ~2018 |
| S21 | Trinnov, "WaveForming to be integrated in The Cinema Designer" — https://www.trinnov.com/en/blog/posts/waveforming-to-be-integrated-in-the-cinema-designer/ | ~2024 |
| S22 | Sound & Vision, "Cinema Designer Tool Updated for 32-Channel Super Theaters" — https://www.soundandvision.com/content/cinema-designer-tool-updated-32-channel-home-theaters | ~2018 |
| S23 | TCD shop, "Cinema Room Pro Monthly Subscription" — https://shopify.thecinemadesigner.com/collections/frontpage/products/cinema-room-pro-monthly-subscription | current |
| S24 | TCD shop, "Media Room Monthly Subscription" — https://shopify.thecinemadesigner.com/products/media-room-monthly-subscription | current |
| S25 | TCD shop, "Cinema Room Pro Annual Subscription" — https://shopify.thecinemadesigner.com/collections/frontpage/products/cinema-room-pro-annual-subscription | current |
| S26 | CEDIA-era pricing page — https://thecediadesigner.org/pricing/ | historical |
| S27 | AVS Forum, "The Official 'The Cinema Designer' (TCD) Thread" — https://www.avsforum.com/threads/the-official-the-cinema-designer-tcd-thread-an-ht-design-tool.3240182/ | ~2022 |
| S28 | TCD blog, "Loewe TV displays join The Cinema Designer database" — https://thecinemadesigner.com/blog/posts/loewe-tv-displays-join-the-cinema-designer-database-opening-high-end-loewe-media-room-designs-up-to-global-integrator-database/ | — |
| S29 | D-Tools, "D-Tools Extends AV System Design and CAD Drawing Services with The CEDIA Designer" — https://www.d-tools.com/resource-center/news-events/d-tools-extends-av-system-design-and-cad-drawing-services-with-the-cedia-designer | ~2019 |
| S30 | CEDIA/CTA-RP22 Immersive Audio Design Recommended Practice v1.2 — https://cedia.org/site/assets/files/6057/cedia-cta_rp22_v1_2_sept_2023.pdf | Sep 2023 |
| S31 | Connected Magazine, "Lifting the lid on RP23 for video design" — https://connectedmag.com.au/lifting-the-lid-on-rp23-for-video-design/ ; AVS Forum CEB23-B explainer — https://www.avsforum.com/threads/designing-the-video-experience-getting-the-right-screen-size-and-type-explicating-the-home-theater-video-design-bulletin-cta-cedia-ceb23-b.2944566/ | various |
| S32 | Dolby Atmos Home Theater Installation Guidelines (Dec 2018 copy) — https://displaydaily.com/wp-content/uploads/2014/10/dolby-atmos-home-theater-installation-guidelines.pdf | Dec 2018 |
| S33 | TCD Terms and Conditions — https://thecinemadesigner.com/terms-and-conditions/ ; TCD FAQ — https://thecinemadesigner.com/about-tcd/faq/ | current |
