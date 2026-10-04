# Critical routing gate

Native KiCad DRC, DFM, and floating-pad checks remain mandatory. They do not imply
controlled impedance, coupled routing, continuous return paths, or crystal suitability.

Run `python3 scripts/check_critical_routing.py board.kicad_pcb --json`.
The policy is `board.routing-policy.json`, or specify `--policy path`.
Requires the KiCad `pcbnew` Python bindings; no board edits, subprocesses, or zone refill.
Exit 0 means screening and declared review evidence pass; 1 means findings; 2 means
missing/invalid policy or unavailable geometry. Missing input is never a clean result.
The viewer runs this gate when the sidecar exists. Without it the summary explicitly
states critical routing is NOT ASSESSED. Editing the policy invalidates the viewer revision.

## Policy (version 1)

```json
{
  "version": 1,
  "reference_layers": {"F.Cu": {"layer": "In1.Cu", "net": "GND"}},
  "groups": [{
    "name": "USB",
    "differential_pair": true,
    "legs": [["USB_DP", "USB_DP_MCU"], ["USB_DM", "USB_DM_MCU"]],
    "allowed_layers": ["F.Cu"],
    "max_vias": 0,
    "max_copper_mm": 50,
    "max_copper_mismatch_mm": 1,
    "required_reviews": ["fabricator-stackup-impedance", "pair-coupling-and-return-path"]
  }],
  "reviews": {}
}
```

These numbers are example project screening budgets, **not USB compliance limits**.
Limits apply per net, except mismatch, which aggregates each explicitly declared leg.
For crystal nets use separate legs and omit `differential_pair`. Require a placement review.
Net lists include series-resistor-separated sections explicitly; there is no guessing
from names, protocol, or pin numbers. Missing nets, absent tracks, excessive vias,
disallowed layers, excessive copper length/mismatch, and missing reference samples fail.
Unsupported geometry (including arcs) is unresolved rather than omitted from a pass.

Each straight track is sampled at endpoints and at intervals no greater than 0.25 mm.
Samples require actual filled-zone copper of the declared net on the reference layer.
A missing layer mapping or unfilled zone fails. Refill zones and run native DRC first.
The checker reads persisted fill; it cannot establish that a fill cache is current.

## What this does not compute

Length is **total track copper**, including branches/stubs. It excludes pad delay and
via-barrel length, and is not point-to-point propagation delay. Paired copper totals
can mask unequal individual series sections. Centerline samples can miss narrow slots;
coverage does not establish a connected reference island, return-path continuity,
transition stitching, field containment, coupling, or impedance. This is screening.

Stackup dielectric thickness/material, copper thickness, width/gap, target impedance,
and fabrication tolerance need a fabricator-backed stackup and impedance calculation.
KiCad custom rules can then enforce width, gap, uncoupled length, and skew. Explicit
net matching is needed where existing names are not KiCad differential-pair suffixes.
Do not invent a width/gap and claim controlled impedance from the layer count alone.

Every group must declare engineering reviews. A review entry has `reviewer`, `evidence`
and `board_sha256` (SHA-256 of the exact `.kicad_pcb`). These are human/solver signoffs,
not calculations made by this checker. Re-routing invalidates old signoffs. Evidence
should identify the stackup revision and calculation or reviewed paths, not just "OK".
The gate cannot verify the truth of a signoff. Power/thermal/current-limit qualification
is still separate; this gate does not establish fabrication readiness by itself.

Sources: [KiCad 9 custom rules](https://docs.kicad.org/9.0/en/pcbnew/pcbnew.html#custom-design-rules)
and [WIZnet hardware guide](https://docs.wiznet.io/Design-Guide/hardware_design_guide).
WIZnet specifies equal-length differential routing with 100-ohm differential impedance.

The viewer uses `/usr/bin/python3` on Linux for the native gate, independently of the
standard-library helpers. Set `CIRCUIT_SKILLS_KICAD_PYTHON` to the KiCad-compatible
interpreter on other installs. Do not add another Python version's binary bindings
to `sys.path`; incompatible bindings can crash. Missing bindings produce an unresolved
exit status, not a successful check.
