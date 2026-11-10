#!/usr/bin/env python3
"""
Build the CHT Parts Catalog workbook from the private Savant price list.

Output (PRIVATE, git-ignored): private/CHT_Parts_Catalog_<date>.xlsx with
  Settings          - earned discount, client discount, legend (the only cells to edit)
  Theater Parts     - curated list of the parts CHT uses, by system, with live cost/sell/margin formulas
  Package Pricing   - Good / Better / Best bill of materials for the current project, priced by lookup
  Full Price List   - every active and last-time-buy Savant item with the same formulas
  Price Changes     - this month's Savant change notes

Discount and cost reproduce the Savant sheet exactly:
  discount = MIN(max discount, MAX(earned discount, min discount))   (blank bands ignored, as in Excel)
  dealer cost = MSRP x (100 - discount) / 100

Usage: python3 -I tools/pricing/build_parts_catalog.py   (after import_savant.py and projects/jbl-24x18/design.py)
"""
import json
import os
import sys

from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, ROOT)
from catalog.products import SPEAKERS, SUBS, AMPS, PROCESSORS, PROJECTORS  # noqa: E402

PRICES = json.load(open(os.path.join(ROOT, "private", "pricing", "savant_price_list.json")))
OPTIONS = json.load(open(os.path.join(ROOT, "projects", "jbl-24x18", "out", "options.json")))

F = "Arial"
HDR_FILL = PatternFill("solid", fgColor="1F3A5F")
HDR_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
INPUT_FILL = PatternFill("solid", fgColor="FFFF00")
BLUE = Font(name=F, color="0000FF", size=10)
BODY = Font(name=F, size=10)
BOLD = Font(name=F, size=10, bold=True)
GREEN = Font(name=F, color="008000", size=10)
TITLE = Font(name=F, size=14, bold=True)
THIN = Side(style="thin", color="B7C4D1")
MONEY = '$#,##0.00;($#,##0.00);"-"'
MONEY0 = '$#,##0;($#,##0);"-"'
PCT_WHOLE = '0.00"%";-0.00"%";"-"'
PCT = '0.0%;-0.0%;"-"'

# Product lines and categories that belong in a theater / AV integration parts list
THEATER_LINES = {"Harman-JBL", "Harman-Revel", "Harman-Arcam", "Harman-Crown", "AudioControl", "Sony", "Kaleidescape",
                 "Torus Power", "Surgex", "AudioQuest", "Integra", "Pioneer Elite", "MOTU", "Artison", "Devialet"}
SAVANT_CATS = {"Hosts", "Remotes", "Touchpanel", "Controllers", "License", "Subscription"}
SAVANT_SUBCATS = {"IP Audio", "IP Video", "Music Servers", "Cables", "Rack Shelves"}


def cht_category(it):
    cat, subc = it["category"] or "", it["subcategory"] or ""
    desc = (it["desc"] or "").upper()
    if cat == "Speakers" and subc == "Subwoofer":
        return "03 Subwoofers"
    if cat == "Speakers" and (subc == "Accessories" or "BRACKET" in desc or "RIB" in desc):
        return "04 Speaker brackets & accessories"
    if cat == "Speakers" and subc in ("AVR",):
        return "05 Processors & AVRs"
    if cat == "Speakers" and subc == "Soundbars":
        return "02 Soundbars & media room"
    if cat == "Speakers":
        return "01 Loudspeakers"
    if cat == "Audio" and subc == "AVR":
        return "05 Processors & AVRs"
    if cat == "Audio" and subc == "Amplifiers":
        return "06 Amplifiers"
    if cat == "Audio" and subc == "Calibration Services":
        return "12 Services"
    if cat == "Video" and subc == "Projector":
        return "07 Projectors"
    if cat == "Video" and subc in ("Movie Server",):
        return "08 Sources"
    if cat in ("Power Management", "Energy"):
        return "10 Power"
    if cat in SAVANT_CATS or subc in ("Smart", "S2", "EVO"):
        return "09 Control (Savant)"
    if subc in ("IP Audio", "IP Video", "Music Servers"):
        return "09 Control (Savant)"
    if "HDMI" in desc or "OPTICAL" in desc or "SPEAKER CABLE" in desc or subc == "Cables":
        return "11 Cables"
    return "13 Other AV"


def theater_relevant(it):
    if it["line"] in THEATER_LINES:
        return True
    if it["line"] == "Savant" and ((it["category"] in SAVANT_CATS) or (it["subcategory"] in SAVANT_SUBCATS)):
        return True
    return False


ENGINE = {}
for d, kind in ((SPEAKERS, "speaker"), (SUBS, "sub"), (AMPS, "amp"), (PROCESSORS, "processor"), (PROJECTORS, "projector")):
    for model, spec in d.items():
        if spec.get("sku"):
            ENGINE[spec["sku"]] = (model, kind)

PKG_USE = {}
for t, s in OPTIONS["packages"].items():
    for b in s["bom"]:
        if b.get("sku"):
            PKG_USE.setdefault(b["sku"], []).append(s["label"])


def hdr(ws, row, cols, widths=None):
    for i, c in enumerate(cols, 1):
        cell = ws.cell(row, i, c)
        cell.font, cell.fill = HDR_FONT, HDR_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[row].height = 30
    if widths:
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w


def disc_formula(r, earned="Settings!$C$5"):
    # Savant: =MIN(F, MAX($Y$1, G)) with blanks ignored. H = max band, G = min band here.
    return f'=IF(H{r}="",MAX({earned},IF(G{r}="",0,G{r})),MIN(H{r},MAX({earned},IF(G{r}="",0,G{r}))))'


def write_price_rows(ws, items, start, extra_cols):
    """Columns: A Category B SKU C Description D Brand/Line E UOM F MSRP G Min% H Max% I Disc% J Cost K Sell L Margin$ M Margin% ..."""
    r = start
    for it in items:
        ws.cell(r, 1, it["_cat"]).font = BODY
        ws.cell(r, 2, it["sku"]).font = BODY
        ws.cell(r, 3, it["desc"]).font = BODY
        ws.cell(r, 4, f"{it['brand']} / {it['line']}").font = BODY
        ws.cell(r, 5, it["uom"]).font = BODY
        for col, key, fmt in ((6, "msrp", MONEY), (7, "min_disc", PCT_WHOLE), (8, "max_disc", PCT_WHOLE)):
            c = ws.cell(r, col, it[key])
            c.font, c.number_format = BLUE, fmt
        ws.cell(r, 9, disc_formula(r)).number_format = PCT_WHOLE
        ws.cell(r, 10, f"=F{r}*(100-I{r})/100").number_format = MONEY
        ws.cell(r, 11, f"=F{r}*(1-Settings!$C$6)").number_format = MONEY
        ws.cell(r, 12, f"=K{r}-J{r}").number_format = MONEY
        ws.cell(r, 13, f'=IF(K{r}=0,"",L{r}/K{r})').number_format = PCT
        for i in range(9, 14):
            ws.cell(r, i).font = BODY
        for j, v in enumerate(extra_cols(it), 14):
            ws.cell(r, j, v).font = BODY
        r += 1
    return r


def main():
    items = [dict(i) for i in PRICES["items"]]
    for it in items:
        it["_cat"] = cht_category(it)
    wb = Workbook()

    # Settings ------------------------------------------------------------
    s = wb.active
    s.title = "Settings"
    s.column_dimensions["A"].width = 3
    s.column_dimensions["B"].width = 46
    s.column_dimensions["C"].width = 16
    s.column_dimensions["D"].width = 90
    s["B2"] = "CHT Parts Catalog"
    s["B2"].font = TITLE
    s["B3"] = f"Built from: {PRICES['source']} ({PRICES['file']}). CONFIDENTIAL: contains dealer pricing."
    s["B3"].font = Font(name=F, size=10, italic=True, color="C00000")
    s["B5"], s["C5"] = "Earned 2026 Savant discount (whole %, e.g. 40 = 40%)", 0
    s["B6"], s["C6"] = "Client discount off MSRP for sell price (fraction, e.g. 0.10 = 10%)", 0
    for c in ("C5", "C6"):
        s[c].font, s[c].fill = BLUE, INPUT_FILL
    s["C5"].number_format = PCT_WHOLE
    s["C6"].number_format = PCT
    s["D5"] = ("Same as cell Y1 on the Savant sheet. 0 reproduces the Savant file as sent: items with a minimum "
               "discount band get that band; items with no band are priced at MSRP until you enter your earned discount.")
    s["D6"] = "Sell price = MSRP x (1 - client discount). Leave 0 to sell at MSRP."
    s["C5"].comment = Comment("Enter your earned discount from Savant. Source: user / Savant agreement.", "CHT")
    for c in ("B5", "B6", "D5", "D6"):
        s[c].font = BODY
        s[c].alignment = Alignment(wrap_text=True, vertical="top")
    s["B8"] = "How to use"
    s["B8"].font = BOLD
    notes = [
        "Edit only the yellow cells (blue text). Every price, cost and margin recalculates from them.",
        "Discount % = MIN(max discount, MAX(earned discount, min discount)); blank bands are ignored, exactly as on the Savant sheet.",
        "Dealer cost = MSRP x (100 - discount %) / 100.",
        "Theater Parts = the AV / theater lines CHT uses, grouped by system. 'Packages' shows which Good/Better/Best package uses each part.",
        "Package Pricing = the 24x18 JBL project in three packages. Quantities come from the design engine; prices are looked up by SKU.",
        "Rows marked 'Not on Savant list' need your own price in the yellow cells.",
        "Status 'Last time buy' and change notes come from the Savant file's LastTimeBuyPriceList and Changes tabs.",
        "Refresh monthly: run tools/pricing/import_savant.py on the new Savant file, then this builder.",
    ]
    for i, n in enumerate(notes, 9):
        s.cell(i, 2, f"{i-8}. {n}").font = BODY
        s.merge_cells(start_row=i, start_column=2, end_row=i, end_column=4)
    s.cell(18, 2, "Legend").font = BOLD
    s.cell(19, 2, "Blue text = value from the Savant price list or an input").font = BLUE
    s.cell(20, 2, "Black text = formula").font = BODY
    s.cell(21, 2, "Yellow fill = cell to edit").fill = INPUT_FILL
    s.cell(21, 2).font = BODY

    cols = ["System", "SKU", "Description", "Brand / line", "UOM", "MSRP", "Min disc %", "Max disc %", "Disc %",
            "Dealer cost", "Sell price", "Margin $", "Margin %"]
    widths = [26, 20, 60, 24, 6, 12, 10, 10, 9, 12, 12, 11, 9]

    # Theater Parts ----------------------------------------------------------
    tp = wb.create_sheet("Theater Parts")
    tp_items = sorted([i for i in items if theater_relevant(i)], key=lambda i: (i["_cat"], i["line"], i["sku"]))
    hdr(tp, 1, cols + ["Packages", "Engine model", "Status", "Savant change note"], widths + [16, 14, 13, 60])

    def extra(it):
        eng = ENGINE.get(it["sku"])
        return [", ".join(PKG_USE.get(it["sku"], [])), eng[0] if eng else "", it["status"], it["change"] or ""]
    end = write_price_rows(tp, tp_items, 2, extra)
    tp.freeze_panes = "C2"
    tab = Table(displayName="TheaterParts", ref=f"A1:Q{end-1}")
    tab.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    tp.add_table(tab)

    # Package Pricing ----------------------------------------------------------
    pp = wb.create_sheet("Package Pricing")
    pp["A1"] = "24 x 18 JBL Synthesis theater - Good / Better / Best"
    pp["A1"].font = TITLE
    pp["A2"] = ("Quantities from projects/jbl-24x18 design engine (options.json). Unit prices are INDEX/MATCH lookups "
                "into Full Price List by SKU; yellow rows are not on the Savant list - enter your price.")
    pp["A2"].font = Font(name=F, size=9, italic=True)
    tiers = list(OPTIONS["packages"].keys())
    labels = [OPTIONS["packages"][t]["label"] for t in tiers]
    ph = ["Group", "SKU", "Description"] + [f"{l} qty" for l in labels] + ["Unit MSRP", "Unit cost", "Unit sell"] + \
         [f"{l} sell" for l in labels] + [f"{l} cost" for l in labels]
    hdr(pp, 4, ph, [22, 18, 52, 9, 9, 9, 12, 12, 12, 13, 13, 13, 13, 13, 13])
    # union of BOM lines in order
    lines = []
    seen = {}
    for t in tiers:
        for b in OPTIONS["packages"][t]["bom"]:
            key = (b["role"], b["sku"] or b["desc"])
            if key not in seen:
                seen[key] = {"role": b["role"], "sku": b["sku"], "desc": b["desc"], "qty": {}}
                lines.append(seen[key])
            seen[key]["qty"][t] = b["qty"]
    order = ["Loudspeakers", "Brackets", "Subwoofers", "Processing", "Amplification", "Video",
             "Sources / control / power", "Not on Savant list"]
    lines.sort(key=lambda x: order.index(x["role"]))
    r = 5
    nq = len(tiers)
    q0 = 4  # first qty column (D)
    um, uc, us = q0 + nq, q0 + nq + 1, q0 + nq + 2
    s0 = us + 1
    c0 = s0 + nq
    for ln in lines:
        pp.cell(r, 1, ln["role"]).font = BODY
        pp.cell(r, 2, ln["sku"] or "").font = BODY
        pp.cell(r, 3, ln["desc"]).font = BODY
        for j, t in enumerate(tiers):
            c = pp.cell(r, q0 + j, ln["qty"].get(t, 0))
            c.font = BLUE
        if ln["sku"]:
            look = lambda col: (f'=IFERROR(INDEX(\'Full Price List\'!${col}:${col},MATCH($B{r},\'Full Price List\'!$B:$B,0)),"not found")')
            pp.cell(r, um, look("F")).font = GREEN
            pp.cell(r, uc, look("J")).font = GREEN
            pp.cell(r, us, look("K")).font = GREEN
        else:
            for col in (um, uc, us):
                cc = pp.cell(r, col, None)
                cc.fill, cc.font = INPUT_FILL, BLUE
            pp.cell(r, us, f"={get_column_letter(um)}{r}*(1-Settings!$C$6)").font = BODY
            pp.cell(r, us).fill = PatternFill()
        for col in (um, uc, us):
            pp.cell(r, col).number_format = MONEY
        for j in range(nq):
            qc = get_column_letter(q0 + j)
            pp.cell(r, s0 + j, f'=IFERROR({qc}{r}*{get_column_letter(us)}{r},0)').number_format = MONEY0
            pp.cell(r, c0 + j, f'=IFERROR({qc}{r}*{get_column_letter(uc)}{r},0)').number_format = MONEY0
        r += 1
    last = r - 1
    r += 1
    pp.cell(r, 3, "Equipment total").font = BOLD
    for j in range(nq):
        for base in (s0, c0):
            col = get_column_letter(base + j)
            c = pp.cell(r, base + j, f"=SUM({col}5:{col}{last})")
            c.font, c.number_format = BOLD, MONEY0
    pp.cell(r + 1, 3, "Equipment margin $ (sell - cost)").font = BOLD
    pp.cell(r + 2, 3, "Equipment margin %").font = BOLD
    for j in range(nq):
        sc, cc = get_column_letter(s0 + j), get_column_letter(c0 + j)
        pp.cell(r + 1, s0 + j, f"={sc}{r}-{cc}{r}").number_format = MONEY0
        pp.cell(r + 2, s0 + j, f'=IF({sc}{r}=0,"",({sc}{r}-{cc}{r})/{sc}{r})').number_format = PCT
    pp.cell(r + 4, 1, "Engineering summary (from the design engine)").font = BOLD
    summ = [("Front LCR / surrounds / overheads", lambda s_: f"{s_['lcr']} / {s_['surround']} / {s_['top']}"),
            ("Subwoofers", lambda s_: f"{s_['sub']} ({s_['sub_layout']})"),
            ("Processor / amplification", lambda s_: f"{s_['processor']} / {s_['amps']}"),
            ("Est. peak level at RSP (dB, +room)", lambda s_: f"{s_['spl_low']:.1f} - {s_['spl_high']:.1f}"),
            ("Est. max LFE at RSP, free-field (dB)", lambda s_: f"{s_['lfe_ff']:.1f}"),
            ("Bass seat-to-seat spread (mean SD, dB)", lambda s_: f"{s_['sub_sd']:.2f}"),
            ("Projector / est. luminance", lambda s_: f"{s_['projector']} / {s_['fL']:.0f} fL")]
    for i, (lab, fn) in enumerate(summ, r + 5):
        pp.cell(i, 3, lab).font = BODY
        for j, t in enumerate(tiers):
            pp.cell(i, s0 + j, fn(OPTIONS["packages"][t])).font = BODY
    for j, l in enumerate(labels):
        pp.cell(r + 4, s0 + j, l).font = BOLD
    pp.freeze_panes = "D5"

    # Full Price List ----------------------------------------------------------
    fp = wb.create_sheet("Full Price List")
    all_items = sorted(items, key=lambda i: (i["line"], i["sku"]))
    hdr(fp, 1, cols + ["Status", "Category / subcategory", "Ship estimate", "Savant change note"], widths + [13, 30, 18, 60])

    def extra2(it):
        return [it["status"], f"{it['category']} / {it['subcategory']}", str(it["ship_days"] or ""), it["change"] or ""]
    end = write_price_rows(fp, all_items, 2, extra2)
    fp.freeze_panes = "C2"
    fp.auto_filter.ref = f"A1:Q{end-1}"

    # Price Changes --------------------------------------------------------------
    pc = wb.create_sheet("Price Changes")
    hdr(pc, 1, ["SKU", "Change"], [24, 140])
    for i, (k, v) in enumerate(PRICES["changes"].items(), 2):
        pc.cell(i, 1, k).font = BODY
        pc.cell(i, 2, v).font = BODY

    for ws in (tp, fp):
        for row in ws.iter_rows(min_row=2, max_row=min(ws.max_row, 6000)):
            for c in row:
                c.border = Border(bottom=THIN)
    out = os.path.join(ROOT, "private", f"CHT_Parts_Catalog_{PRICES['file'][-13:-5]}.xlsx")
    wb.save(out)
    print(out, "theater parts:", len(tp_items), "all:", len(all_items), "package lines:", len(lines))


if __name__ == "__main__":
    main()
