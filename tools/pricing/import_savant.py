#!/usr/bin/env python3
"""
Import a Savant integrator price list (.xlsx) into private/pricing/savant_price_list.json.

The output is PRIVATE (git-ignored): it carries MSRP and the discount bands that
determine dealer cost. Dealer cost = MSRP x (1 - discount/100), where
discount = MIN(max discount, MAX(your earned discount, min discount)) - the
same formula the Savant sheet uses (blank bands are ignored, as in Excel).

Usage: python3 -I tools/pricing/import_savant.py <Price_List_Integrator_YYYYMMDD.xlsx>
"""
import json
import os
import re
import sys

import openpyxl

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def rows(ws, header_row=2):
    it = ws.iter_rows(values_only=True)
    for _ in range(header_row - 1):
        next(it)
    hdr = next(it)
    for r in it:
        if r and r[0]:
            yield dict(zip(hdr, r))


def main(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    m = re.search(r"(\d{8})", os.path.basename(path))
    source = f"Savant integrator price list {m.group(1) if m else ''}".strip()
    changes = {}
    for r in rows(wb["Changes"], 1):
        changes[r["ProductName"]] = f"{r['ChangeSummary']}: {str(r['ChangeDetails'] or '').strip()}"
    items = []
    for sheet, status in (("ActivePriceList", "Active"), ("LastTimeBuyPriceList", "Last time buy")):
        for r in rows(wb[sheet], 2):
            items.append({"sku": str(r["ProductName"]).strip(), "desc": r["Description"], "brand": r["Brand"],
                          "line": r["ProductLine"], "msrp": r["MSRP"], "max_disc": r["MaximumDiscount"],
                          "min_disc": r["MinimumDiscount"], "category": r["ProductCategory"],
                          "subcategory": r["ProductSubCategory"], "uom": r["UnitofMeasure"],
                          "ship_days": r["In-Stock Shipping Estimate (Business Days)"], "status": status,
                          "change": changes.get(r["ProductName"])})
    out_dir = os.path.join(ROOT, "private", "pricing")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "savant_price_list.json")
    with open(out, "w") as f:
        json.dump({"source": source, "file": os.path.basename(path), "items": items,
                   "changes": changes}, f, indent=0)
    print(f"{len(items)} items ({sum(i['status'] == 'Active' for i in items)} active) -> {out}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
