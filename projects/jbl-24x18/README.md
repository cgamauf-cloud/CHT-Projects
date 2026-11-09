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
  - SDP-58 processor
  - SDA-7120 amplifiers
- JVC NZ8 as the example projector.

Product data, placement windows and absorption coefficients come from secondary sources. AV-601 lists each one that needs verifying. This is a concept design, not for construction.
