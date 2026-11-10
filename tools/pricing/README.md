# Pricing tools (private data)

Savant price lists and dealer costs are confidential. They are kept in `private/`, which git ignores and which is never committed.

| Step | Command | Output |
|---|---|---|
| 1. Import the monthly Savant file | `python3 -I tools/pricing/import_savant.py ~/Downloads/Price_List_Integrator_YYYYMMDD.xlsx` | `private/pricing/savant_price_list.json` |
| 2. Run the design engine (attaches MSRP to the package BOMs) | `cd projects/jbl-24x18 && python3 -I design.py` | `out/design.json`, `out/options.json` (MSRP only) |
| 3. Build the parts catalog workbook | `python3 -I tools/pricing/build_parts_catalog.py` | `private/CHT_Parts_Catalog_YYYYMMDD.xlsx` |

The workbook has these sheets:
- **Settings:** your earned Savant discount and the client discount. These are the only cells to edit.
- **Theater Parts:** about 500 AV and theater parts grouped by system.
- **Package Pricing:** Good/Better/Best for the current project, with sell, cost and margin.
- **Full Price List:** every Savant item, using the same formulas.
- **Price Changes:** this month's change notes from Savant.

The cost formula reproduces Savant's sheet: discount = `MIN(max, MAX(earned, min))`, and cost = `MSRP × (100 − discount)/100`.

Drawings and other committed outputs show **list price (MSRP) only**.
