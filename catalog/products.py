"""
CHT equipment catalog: engineering data and Savant store SKUs, with NO prices.

Prices live outside the repo, in a private price list imported by
tools/pricing/import_savant.py into private/pricing/. This module holds only
the published engineering data that the calculation engine needs, and where
each value came from.

Conventions:
  sens     dB SPL @ 2.83 V @ 1 m (radiation space noted in src) unless sens_ref says otherwise
  z        nominal impedance (ohm)
  pmax     power figure used as the output cap, with pmax_kind saying what it is
  grille_wh  (width, height) in metres of the wall/ceiling footprint; dims_status flags assumptions
  lmax_1m  (subs) max SPL at 1 m per enclosure, if published directly
Values marked "verify" come from retailer or secondary sources.
"""

SPEAKERS = {
    "SCL-1": dict(sku="JBLSCL1BLK", desc="JBL Synthesis SCL-1 dual 12in 2-way custom LCR", sens=94, z=4, pmax=600,
                  pmax_kind="CEA-426B rating (JBL page; spec sheet recommends >=500 W amp)", grille_wh=(0.70, 1.30),
                  depth=0.30, dims_status="footprint ASSUMED - verify JBL spec sheet", bracket=None,
                  src="jblsynthesis.com SCL-1 page / SC03996 spec sheet (94 dB on sheet, 95 dB on page)"),
    "SCL-2": dict(sku="JBLSCL-2", desc="JBL Synthesis SCL-2 2.5-way in-wall LCR", sens=92, z=6, pmax=445,
                  pmax_kind="rated RMS (CEA-426B)", grille_wh=(0.326, 1.022), depth=0.147, bracket=None,
                  src="jblsynthesis.com SCL-2 page / owner's manual"),
    "SCL-3": dict(sku="SCL-3", desc="JBL Synthesis SCL-3 dual 5.25in 2-way in-wall", sens=91, z=6, pmax=300,
                  pmax_kind="max recommended amp power (US sheet)", grille_wh=(0.25, 0.42), depth=0.09,
                  dims_status="grille size ASSUMED - verify", bracket="SCL-3PCB",
                  src="Harman SCL-3 spec sheet TR02315 V7"),
    "SCL-5": dict(sku="JBLSCL5", desc="JBL Synthesis SCL-5 7in angled in-ceiling", sens=86, z=6, pmax=125,
                  pmax_kind="max recommended amp power", grille_wh=(0.27, 0.27), depth=0.12, bracket=None,
                  dims_status="footprint ASSUMED", src="JBL SCL-5 quick specs SC03921"),
    "SCL-6": dict(sku="JBLSCL6", desc="JBL Synthesis SCL-6 quad 5.25in in-wall compression driver", sens=91, z=4,
                  pmax=200, pmax_kind="upper recommended amp power", grille_wh=(0.24, 0.80), depth=0.09,
                  dims_status="footprint ASSUMED - verify", bracket="JBLWB54",
                  src="jblsynthesis.com SCL-6 page"),
    "SCL-7": dict(sku="JBLSCL7", desc="JBL Synthesis SCL-7 dual 5.25in angled in-wall", sens=88, z=4, pmax=150,
                  pmax_kind="upper recommended amp power", grille_wh=(0.22, 0.42), depth=0.09,
                  dims_status="footprint ASSUMED - verify", bracket="JBLWB52",
                  src="JBL SCL-7 spec sheet SC03934"),
    "SCL-8": dict(sku="JBLSCL8", desc="JBL Synthesis SCL-8 5.25in angled in-ceiling", sens=85, z=4, pmax=100,
                  pmax_kind="upper recommended amp power", grille_wh=(0.22, 0.22), depth=0.10, bracket=None,
                  dims_status="footprint ASSUMED", src="JBL SCL-8 spec sheet SC03940"),
}

SUBS = {
    "SSW-1": dict(sku="JBLSSW1BLK", desc="JBL Synthesis SSW-1 dual 15in passive subwoofer", woofers=2,
                  sens_1w=90, z_per_woofer=8, pmax_per_woofer=2500, amp_ch=2, grille_wh=(0.55, 1.40), depth=0.30,
                  dims_status="footprint ASSUMED - verify (large; may need a framed soffit/false wall)",
                  src="JBL SCL-1/SSW-1 press release; Len Wallis spec listing"),
    "SSW-3": dict(sku="JBLSSW3BLK", desc="JBL Synthesis SSW-3 dual 10in passive in-wall subwoofer", woofers=2,
                  sens=88, z=4, pmax=600, amp_ch=1, grille_wh=(0.394, 1.676), depth=0.130,
                  src="JBL SSW-3 quick specs SC02547 / owner's manual"),
    "SSW-4": dict(sku="JBLSSW4", desc="JBL Synthesis SSW-4 dual 8in passive in-wall subwoofer", woofers=2,
                  lmax_1m=107, z=8, pmax=350, amp_ch=1, grille_wh=(0.368, 0.597), depth=0.09,
                  lmax_note="107 dB CEA-2010B max SPL used as 1 m figure (conservative; verify reference distance)",
                  src="JBL SSW-4 quick specs; SDA-1700 spec sheet (350 W per SSW-4)"),
}

AMPS = {
    "SMA-4750": dict(sku="JBLSMA4750AM", desc="JBL Synthesis SMA-4750 4-ch Class D amplifier", ch=4, p8=750, p4=1500,
                     src="jblsynthesis.com SMA-4750; 4-ohm figure from Audioholics/ecoustics"),
    "SMA-8300": dict(sku="JBLSMA8300AM", desc="JBL Synthesis SMA-8300 8-ch Class D amplifier", ch=8, p8=300, p4=600,
                     src="jblsynthesis.com SMA series news; 4-ohm figure from Audioholics/ecoustics"),
    "SDA-1700": dict(sku="JBLSDA1700AM", desc="JBL Synthesis SDA-1700 2-ch subwoofer amplifier", ch=2, p8=350, p4=700,
                     src="JBL SDA-1700 spec sheet (700 W into 4 ohm min; 350 W per SSW-4)"),
    "SDR-38 (internal)": dict(sku=None, desc="SDR-38 internal amplification", ch=7, p8=100, p4=180,
                              src="SDR-38 specs, 7 channels driven, 1 kHz"),
}

PROCESSORS = {
    "SDR-38": dict(sku="JBLSDR38AM", desc="JBL Synthesis SDR-38 16-ch AV receiver (7 x 100 W)", outputs=16,
                   internal_amp="SDR-38 (internal)", src="Savant list description; Sound & Vision review"),
    "SDP-60": dict(sku="JBLSDP60AM", desc="JBL Synthesis SDP-60 16-ch AV processor", outputs=16,
                   src="Savant list description (verify spec sheet)"),
    "SDP-80": dict(sku="JBLSDP80AM", desc="JBL Synthesis SDP-80 36-ch preamp/processor", outputs=36,
                   src="Savant list description"),
}

PROJECTORS = {
    "VPL-XW5100ES": dict(sku="VPL-XW5100ES", desc="Sony VPL-XW5100ES 4K SXRD laser projector", lumens=2200,
                         tr_min=1.38, tr_max=2.21, vshift_pct=71, hshift_pct=25, body_depth=0.47,
                         src="ProjectorCentral (shift figures vary by source - verify Sony sheet)"),
    "VPL-XW6100ES": dict(sku="VPL-XW6100ES", desc="Sony VPL-XW6100ES 4K SXRD laser projector", lumens=2700,
                         tr_min=1.35, tr_max=2.84, vshift_pct=85, hshift_pct=36, body_depth=0.52,
                         src="GGVideo / ProjectorCentral"),
    "VPL-XW8100ES": dict(sku="VPL-XW8100ES", desc="Sony VPL-XW8100ES 4K SXRD laser projector", lumens=3400,
                         tr_min=1.34, tr_max=2.87, vshift_pct=85, hshift_pct=36, body_depth=0.52,
                         src="ProjectorCentral (may duplicate XW6100 data - verify Sony sheet)"),
}

# Items with a Savant SKU but no engineering model (sources, control, power, brackets).
ACCESSORIES = {
    "SCL-3PCB": "JBL Synthesis pre-construction bracket for SCL-3",
    "JBLWB54": "JBL Synthesis rough-in bracket for SCL-6",
    "JBLWB52": "JBL Synthesis rough-in bracket for SCL-7",
    "K0217-0000": "Kaleidescape Strato C movie player",
    "K0701-0000": "Kaleidescape Strato V movie player",
    "K0880-0000": "Kaleidescape Strato K movie player",
    "K0110-0030": "Kaleidescape Compact Terra movie server 30 TB",
    "PKG-S2REM-41": "Savant S2 host with Pro Remote X2",
    "ITP-E8000V3B-00": "Savant Touch 8 control screen, black",
    "SX-1120-RT": "SurgeX rack surge eliminator 1RU 20 A",
    "SEQ": "SurgeX sequencing surge eliminator 2RU 20 A",
}

# Things every theater needs that are not on the Savant price list.
NOT_ON_SAVANT_LIST = [
    ("Acoustically transparent screen, 120in 16:9 fixed frame", 1),
    ("Theater recliners", 8),
    ("Speaker cable (12/14/10 AWG per AV-501 schedule)", 1),
    ("Back boxes / brackets where JBL bracket not on Savant list", 1),
    ("Acoustic treatment package (panels, cloud, bass traps, diffusion)", 1),
    ("Equipment rack, ventilation, rack accessories", 1),
    ("Labor: pre-wire, trim-out, calibration", 1),
]
