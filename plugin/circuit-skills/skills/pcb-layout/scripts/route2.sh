#!/usr/bin/env bash
# route2.sh — the 2-layer (pour) pipeline, headless: no live KiCad, no tscircuit DSN.
#
#   bash scripts/route2.sh                       # export -> gates -> prep -> every backend -> apply the best
#   BACKENDS=freerouting,srj:all MAXT=120 POUR="GND:B.Cu" FAB=jlcpcb bash scripts/route2.sh
#
#   export   : tsci export the placed board (its own routing is discarded)
#   gate     : outline-check (parts inside the outline, clear of cutouts)
#   nets     : merge_nets (reconcile fragmented cross-subcircuit nets)
#   prep     : prep_board (strip routing, pour zone(s), .kicad_pro with the fab's rules, fill)
#   route    : route_eval on the KiCad board itself: Freerouting through KiCad's own Specctra
#              export/import (pours go out as planes, cutouts as keepouts) and the capacity
#              autorouter; every candidate scored, ranked and diagnosed; the best one applied.
#   verify   : drc_check on the result
#
# For 4-layer boards with inner planes use route4.sh. Needs: bun/tsci, system python with pcbnew,
# kicad-cli, and at least one router (freert224 and/or scripts/srj).
set -eu
cd "$(dirname "$0")/.."
export PATH="$HOME/.bun/bin:$PATH"
SRC=index.circuit.tsx
BOARD=index.circuit.kicad_pcb
KPY="${CIRCUIT_SKILLS_KICAD_PYTHON:-/usr/bin/python3}"
mkdir -p build

echo "[1/6] export the placed board"
./node_modules/.bin/tsci export -f kicad_pcb "$SRC" -o "$BOARD" 2>&1 | grep -iE 'exported|error:' || true

echo "[2/6] placement gate (parts inside the outline, clear of cutouts)"
node scripts/outline-check.mjs "$SRC" || { [ "${FORCE:-}" = 1 ] || { echo "fix placement"; exit 1; }; }

echo "[3/6] reconcile cross-subcircuit nets"
python3 scripts/merge_nets.py "$BOARD" --write | tail -1

echo "[4/6] strip routing, pour, fab rules"
POURS=""; for p in ${POUR:-GND:B.Cu}; do POURS="$POURS --pour $p"; done
"$KPY" scripts/prep_board.py "$BOARD" $POURS --fab "${FAB:-jlcpcb}" 2>&1 | grep -E '^(prep_board|apply_fab_rules)' || true
python3 scripts/placement_score.py "$BOARD" --svg build/placement-heat.svg | head -4

echo "[5/6] route with every backend, score, apply the best"
python3 scripts/route_eval.py "$BOARD" --backends "${BACKENDS:-freerouting,srj:all}" --time "${MAXT:-120}" --apply | sed -n '/^|---/,$p'

echo "[6/6] verify"
python3 scripts/drc_check.py "$BOARD" | tail -3
