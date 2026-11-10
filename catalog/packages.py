"""
Good / Better / Best theater packages (JBL Synthesis + partners on the Savant store).

A package names a model for each role. The design engine sizes amplification,
checks output, and the pricing tools price it from the private price list.
Geometry (speaker positions) is the same for every package so the comparison
is like-for-like; only products, subwoofer count and electronics change.
"""

PACKAGES = {
    "good": dict(
        label="Good",
        tagline="Value JBL Synthesis in-wall system, AVR-based",
        lcr="SCL-6", surround="SCL-7", top="SCL-8",
        sub="SSW-4", sub_count=4,
        processor="SDR-38",
        amp_lcr="SDR-38 (internal)", amp_surround="SDR-38 (internal)", amp_top="SMA-4750", amp_sub="SDA-1700",
        projector="VPL-XW5100ES",
        extras=[("K0217-0000", 1), ("PKG-S2REM-41", 1), ("SX-1120-RT", 1)],
    ),
    "better": dict(
        label="Better",
        tagline="Reference in-wall LCR, separates, four in-wall subs",
        lcr="SCL-2", surround="SCL-3", top="SCL-3",
        sub="SSW-3", sub_count=4,
        processor="SDP-60",
        amp_lcr="SMA-4750", amp_surround="SMA-8300", amp_top="SMA-8300", amp_sub="SMA-4750",
        projector="VPL-XW6100ES",
        extras=[("K0701-0000", 1), ("PKG-S2REM-41", 1), ("ITP-E8000V3B-00", 1), ("SEQ", 1)],
    ),
    "best": dict(
        label="Best",
        tagline="SCL-1 compression-driver LCR, SSW-1 dual-15 subs, 36-ch processing",
        lcr="SCL-1", surround="SCL-2", top="SCL-3",
        sub="SSW-1", sub_count=4,
        processor="SDP-80",
        amp_lcr="SMA-4750", amp_surround="SMA-8300", amp_top="SMA-8300", amp_sub="SMA-4750",
        projector="VPL-XW8100ES",
        extras=[("K0880-0000", 1), ("K0110-0030", 1), ("PKG-S2REM-41", 1), ("ITP-E8000V3B-00", 1), ("SEQ", 1)],
    ),
}
