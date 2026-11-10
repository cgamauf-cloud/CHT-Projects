# JBL Synthesis Theater, 24 × 18 (concept)

This is the first end-to-end prototype of the CHT design engine. One set of inputs flows through placement, acoustics, audio, video, cabling and the bill of materials, and comes out as a dimensioned drawing set.

| File | What it is |
|---|---|
| `design.py` | Project inputs plus all calculations: seating and riser, screen, projector, speaker-placement search, subwoofer configuration by modal analysis, RT60, SPL and amplifier sizing, cables, BOM. Writes `out/design.json`. |
| `drawings.py` | Renders `out/drawing-set.html` from `design.json`. Inline SVG sheets are drawn at true scale on 11×17. |
| `out/drawing-set.html` | Drawing set: T-001 cover, A-101 floor plan, A-102 reflected ceiling plan, A-201 screen wall, A-202 side walls, A-301 section, AV-501 schedules, AV-601 calculations and review |
| `out/drawing-set.pdf` | The same set printed to 11×17 (ANSI B). The plan sheets print at 3/8″ = 1′-0″; the elevations and section at 1/2″ = 1′-0″. |
| `out/design_summary.txt` | Console summary and design-review warnings |

Rebuild:

```
python3 -I design.py && python3 -I drawings.py
```

To print the PDF, use any headless Chromium with `printBackground`, 17 × 11 in.

## Key assumptions (change them in `P` at the top of `design.py`)

- 24′ L × 18′ W room. **9′ ceiling (assumed)**. Screen on the 18′ wall.
- Two rows of four recliners. Row 1 ear is 3.75 m from the screen wall; rows are 1.90 m apart. There is a 1 m floor-level rear cross-aisle and a right-side aisle.
- 120″ 16:9 AT screen, with a full-width AT front wall and in-wall L/C/R behind it.
- Door on the back wall (inswing). Equipment rack outside the room.
- JBL Synthesis package:
  - SCL-2 for L/C/R
  - SCL-3 for surrounds and overheads (**JBL approval for ceiling use and the SCL-3 grille size need verifying**)
  - SSW-3 subwoofers
  - Rev A used an SDP-58 processor, SDA-7120 amps and a JVC NZ8. These are not on the Savant store, so Rev B replaces them (see below).

Product data, placement windows and absorption coefficients come from secondary sources. AV-601 lists each one that needs verifying. This is a concept design, not for construction.

## Rev B: Savant-priced packages and the subwoofer planner

- **Packages:** `catalog/packages.py` defines **Good / Better / Best** using products on the Savant store:
  - **Good:** SCL-6/7/8, SSW-4, SDR-38, Sony XW5100.
  - **Better:** SCL-2/3, SSW-3, SDP-60 + SMA amps, Sony XW6100.
  - **Best:** SCL-1/2/3, SSW-1, SDP-80, Sony XW8100.

  Speaker positions are the same for every package. `design.py` evaluates all three. Sheet AV-701 compares them, and `--tier good|better|best` picks which one is drawn.
- **Subwoofer layouts:** `design.py --list-subs` lists the common layouts (front pair, corners, side midpoints, wall midpoints, side ¼/¾, front/back ¼/¾, diagonal, custom). The engine rejects any layout that collides with a speaker or the door. Use `--subs <id>` to force one, or set `P['subs_custom']` for your own positions.
- **Interactive planner:** sheet AV-602 lets you pick a layout or drag the subs along the walls (or move them with the arrow keys). It recomputes the seat-by-seat bass response, the evenness score and the LFE estimate live, using the same modal model as the engine.
- **Pricing:** list prices come from the private Savant import (see `tools/pricing/README.md`). Dealer cost appears only in the private parts catalog workbook.

## Rev C: pricing overlay, budget builder, 3D model (`features.py`)

- **Show prices:** a toolbar button (top of the page) that puts list prices (MSRP) on every selected part: price tags on the floor plan and ceiling plan, price columns in the equipment schedule, the package comparison and the cover. Prices are hidden by default, so the page can be shown to a client without them.
- **Budget ranges:** turns every price into a ±N % range (default 10 %, adjustable).
- **Budget builder (AV-702):**
  - Pick Good, Better or Best and set the ± range.
  - Equipment is grouped into budget categories: Audio, Video, Control, Power, Seating, Acoustic treatment, Infrastructure, Labor.
  - Items that aren't on the Savant list (screen, seats, treatment, infrastructure, labor) are entered as allowances. These are saved per browser.
- **3D model (V-801):**
  - A cutaway render of the room built from the same `design.json` as the drawings: seats, riser, screen, speakers, subs, projector and beam, treatment, door.
  - The screen always shows the **Chicagoland Home Theater** wordmark. "Use our logo file" swaps in your real logo (PNG or SVG), saved per browser.
  - The drawn screen elevation (A-201) carries the wordmark too.
  - With Show prices on, each part gets a model and price label.
  - **Spin** starts a slow turntable (40 s per turn).
  - **Export spin video** (WebM) and **Save still image** (PNG) save through the page's `downloads` capability, after the viewer confirms.
- **Offline client video:** `out/cht-theater-spin.mp4` (1920×1080, 30 s, 30 fps) and `out/cht-theater-hero.png` are rendered headless through the page's own scene (`window.CHT3D.frame(angle)`) and encoded with ffmpeg.
