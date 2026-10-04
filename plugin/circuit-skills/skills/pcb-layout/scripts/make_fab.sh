#!/usr/bin/env bash
# make_fab.sh — produce a complete fabrication bundle from a routed KiCad board:
# Gerbers (all copper + mask + silk + paste + edge) + Excellon drill + CPL placement
# + LCSC-mapped BOM, with the Gerbers zipped for upload.
#
# JLCPCB is the target; PCBWay / OSHPark / Aisler accept the SAME Gerber+drill zip
# (only the design-rule limits differ — see rules/). The BOM + CPL are JLCPCB-assembly
# format; other assemblers accept the same CSVs or their own re-mapping.
#
#   bash make_fab.sh <board.kicad_pcb> [name]
#
# Outputs into <board-dir>/fab/ :  <name>-gerbers.zip  <name>-bom.csv  <name>-cpl.csv
set -eu
BOARD="${1:?usage: make_fab.sh <board.kicad_pcb> [name]}"
SELF="$(cd "$(dirname "$0")" && pwd)"
DIR="$(cd "$(dirname "$BOARD")" && pwd)"
B="$(basename "$BOARD")"; STEM="${B%.kicad_pcb}"
NAME="${2:-$STEM}"
FAB="$DIR/fab"; mkdir -p "$FAB"
cd "$DIR"

echo "[0/5] DFM gate (fab minimums KiCad DRC misses: hole spacing, via drill/annular)"
set +e; python3 "$SELF/dfm_check.py" "$B" 2>&1 | sed 's/^/      /'; DFM_RC=${PIPESTATUS[0]}; set -e
[ "$DFM_RC" -ne 0 ] && echo "      ⚠ DFM found ACTIONABLE issues above — bundling anyway, but fix before ordering." >&2 || true

echo "[1/5] Gerbers (all layers + gerber-job)"
kicad-cli pcb export gerbers -o "$FAB/" "$B" >/dev/null
echo "[2/5] Excellon drill"
kicad-cli pcb export drill -o "$FAB/" "$B" >/dev/null
FAB_TGT="${3:-both}"    # jlcpcb | pcbway | both  (Gerbers + CPL are shared across fabs)
echo "[3/5] BOM(s): $FAB_TGT"
case "$FAB_TGT" in jlcpcb|both) python3 "$SELF/gen_bom.py" "$B" --fab jlcpcb -o "$FAB/${NAME}-bom.csv" ;; esac
case "$FAB_TGT" in pcbway|both) python3 "$SELF/gen_bom.py" "$B" --fab pcbway -o "$FAB/${NAME}-bom-pcbway.csv" ;; esac

echo "[4/5] CPL / placement -> JLCPCB columns, filtered to assembled (BOM) parts only"
kicad-cli pcb export pos --format csv --units mm --side both -o "$FAB/${NAME}-cpl-raw.csv" "$B" >/dev/null
python3 - "$FAB/${NAME}-cpl-raw.csv" "$FAB/${NAME}-cpl.csv" "$FAB/${NAME}-bom.csv" "$FAB/${NAME}-bom-pcbway.csv" <<'PYEOF'
import csv, sys
raw, out = sys.argv[1], sys.argv[2]
placed = set()                                        # designators that ARE in the assembly BOM
for bf in sys.argv[3:]:
    try:
        for r in csv.DictReader(open(bf)):
            for x in (r.get("Designator") or "").split(","):
                if x.strip():
                    placed.add(x.strip())
    except FileNotFoundError:
        pass
n = 0
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])   # JLCPCB CPL header
    for r in csv.DictReader(open(raw)):
        ref = (r.get("Ref") or "").strip()
        if not ref or (placed and ref not in placed):  # drop holes + hand-solder (not in the BOM)
            continue
        side = (r.get("Side") or "top").strip().capitalize()   # Top / Bottom
        w.writerow([ref, r.get("PosX", ""), r.get("PosY", ""), side, r.get("Rot", "")]); n += 1
print(f"      CPL: {n} placed parts (matched to BOM designators)")
PYEOF
rm -f "$FAB/${NAME}-cpl-raw.csv"
echo "[5/5] Zip Gerbers + drill -> ${NAME}-gerbers.zip"
cd "$FAB"
rm -f "${NAME}-gerbers.zip"
# standard fab layers: copper (gtl/gbl + g1..g4 inner) / mask / silk / paste / edge / job / drill
FILES=""
for ext in gtl gbl g1 g2 g3 g4 gts gbs gto gbo gtp gbp gm1 gbrjob drl; do
  for f in "$STEM"*."$ext"; do [ -e "$f" ] && FILES="$FILES $f"; done
done
# shellcheck disable=SC2086
zip -jq "${NAME}-gerbers.zip" $FILES
echo "DONE -> $FAB/  (Gerbers + CPL are shared across fabs)"
echo "  JLCPCB:  ${NAME}-gerbers.zip (PCB) + ${NAME}-bom.csv + ${NAME}-cpl.csv"
echo "  PCBWay:  ${NAME}-gerbers.zip (PCB) + ${NAME}-bom-pcbway.csv + ${NAME}-cpl.csv"
echo "  hand-solder (both): ${NAME}-handsolder.csv"
unzip -l "${NAME}-gerbers.zip" | tail -1
