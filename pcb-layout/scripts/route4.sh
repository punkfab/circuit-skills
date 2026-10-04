#!/usr/bin/env bash
# route4.sh — 4-layer route, Freerouting v2.2.4.  SIGNALS route on F.Cu/B.Cu; GND & V3V3
# are NOT routed at all — they're carried by inner-plane ZONES (In1=GND, In2=V3V3) and each
# pad drops a fanout via to its plane.  Mechanical NPTH holes are keepouts so no trace crosses
# a drilled hole.  This is the recipe that eliminates (a) GND/V3V3 traces on signal layers and
# (b) traces routed across keyswitch/USB/screw holes.
#
#   DSN prep : strip tscircuit's (wiring) + mark inner layers (type power)   [dsn_4layer_planes]
#            : DROP GND & V3V3 from the routed netlist (plane-fed)           [dsn_drop_nets]
#            : keepout interior Edge.Cuts cutouts + every NPTH hole          [add_cutout_keepouts + add_npth_keepouts]
#   route    : Freerouting v2.2.4 (JDK25 -> freert224) routes signals + VBUS only
#   KiCad    : pour In1=GND / In2=V3V3, inject signal SES, fanout GND/V3V3 pads to planes,
#              stitch any island, set JLCPCB fab rules, DRC.
#
# Needs: bun/tsci, freert224, kipy, KiCad api server (socket /tmp/kicad/api.sock).
#
# Router: ROUTER=freerouting (default) | fastroute (FASTROUTE_BIN=) | tscircuit | srj (route_srj.mjs, SRJ_LAYERS=outer|all). tscircuit routes the
# design itself (route_tscircuit.mjs; TSCIRCUIT_AUTOROUTER=auto_local, TSCIRCUIT_EFFORT=2x): no DSN/SES,
# the routed export replaces the board, then planes, fab rules and the gates as usual.
set -eu
cd "$(dirname "$0")/.."
export PATH="$HOME/.bun/bin:$PATH"
TSCI=./node_modules/.bin/tsci
SRC=index.circuit.tsx
BOARD=index.circuit.kicad_pcb
PRO=index.circuit.kicad_pro
DSN=build/index.dsn
SES=build/index.ses
DISPLAY=${DISPLAY:-:0}
DROP_NETS="${DROP_NETS:-GND V3V3}"
mkdir -p build

echo "[1/9] export 4-layer board + dsn"
$TSCI export -f kicad_pcb "$SRC" -o "$BOARD" 2>&1 | grep -iE 'exported|error:' || true
$TSCI export -f specctra-dsn "$SRC" -o "$DSN" 2>&1 | grep -iE 'exported|error:' || true

echo "[2/9] placement gate (parts inside outline)"
node scripts/outline-check.mjs "$SRC" || { [ "${FORCE:-}" = 1 ] || { echo "fix placement"; exit 1; }; }

if [ "${ROUTER:-freerouting}" = srj ]; then
  # tscircuit's capacity autorouter on the exported board itself (route_srj.mjs). Signals on the
  # outer layers by default, since the inner planes are poured below; SRJ_LAYERS=all to use all.
  echo "[3-6/9] capacity autorouter on the KiCad board (layers ${SRJ_LAYERS:-outer})"
  CAND="build/srj-${SRJ_LAYERS:-outer}-$(date +%Y%m%d-%H%M%S).kicad_pcb"
  node scripts/route_srj.mjs "$BOARD" -o "$CAND" --layers "${SRJ_LAYERS:-outer}" --board "$BOARD" --time "${MAXT:-300}" --no-refill || exit 1
  cp "$CAND" "$BOARD"
elif [ "${ROUTER:-freerouting}" = tscircuit ]; then
  # tscircuit routes the design itself while it is evaluated: no DSN, no SES. The candidate
  # replaces the plain export; planes, fab rules and the gates below apply as for any backend.
  echo "[3-6/9] tscircuit autorouter (${TSCIRCUIT_AUTOROUTER:-auto_local}${TSCIRCUIT_EFFORT:+, effort $TSCIRCUIT_EFFORT})"
  CAND="build/tscircuit-${TSCIRCUIT_AUTOROUTER:-auto_local}-$(date +%Y%m%d-%H%M%S).kicad_pcb"
  node scripts/route_tscircuit.mjs "$SRC" -o "$CAND" --preset "${TSCIRCUIT_AUTOROUTER:-auto_local}" \
    ${TSCIRCUIT_EFFORT:+--effort "$TSCIRCUIT_EFFORT"} --board "$BOARD" --max-time "${MAXT:-900}" || exit 1
  cp "$CAND" "$BOARD"
else
  echo "[3/9] DSN prep: strip wiring + inner layers -> (type power)"
  python3 scripts/dsn_4layer_planes.py "$DSN" --no-planes --relabel-power
  # tscircuit dedupes DSN images by footprint name -> a top-side part sharing a footprint with a
  # bottom-side one inherits mirrored B.Cu pins. Rebuild those from the (correct) KiCad pads.
  /usr/bin/python3 scripts/dsn_split_sides.py "$BOARD" "$DSN"

  echo "[4/9] DSN: keep GND/V3V3 routed (Freerouting places the QFN dogbones); planes poured in KiCad"
  # NOTE: fully dropping GND/V3V3 (dsn_drop_nets) leaves fine-pitch QFN power pins stranded — they
  # need routed dogbone escapes only the autorouter places well, and Freerouting's (plane) mode won't
  # fan them out (leaves ~48 unrouted). So we let it route them and pour the planes in KiCad.
  # (The "dense LDO corner" shorts that fix_ldo_planes.py used to hand-patch were really the
  # mixed-side image bug that dsn_split_sides.py now fixes above. See the pcb-layout skill.)

  echo "[5/9] DSN: keepout interior cutouts + NPTH mechanical holes"
  python3 scripts/add_cutout_keepouts.py "$BOARD" "$DSN" --margin 0.3 || echo "  (no interior Edge.Cuts cutouts)"
  python3 scripts/add_npth_keepouts.py  "$BOARD" "$DSN" --margin 0.3 --min-hole 0.5

  echo "[6/9] Freerouting v2.2.4 (signals + VBUS; planes & holes avoided)"
  rm -f "$SES"
  FREERT="${FREERT:-$HOME/.local/bin/freert224}" python3 scripts/route_dsn.py "$DSN" -o "$SES" --backend "${ROUTER:-freerouting}" --board "$BOARD" --max-time "${MAXT:-120}" --max-passes "${MP:-12}"
  [ -s "$SES" ] || { echo "no SES written"; exit 1; }
  echo "      SES: $(grep -c '(wire' "$SES") wires, $(grep -c '(via' "$SES") vias"

fi

echo "[7/9] launch pcbnew, wait for IPC socket"
pkill -f 'pcbnew index' 2>/dev/null || true
rm -f /tmp/kicad/api.sock
DISPLAY="$DISPLAY" pcbnew "$BOARD" >build/pcbnew.log 2>&1 &
PCBPID=$!
for i in $(seq 1 40); do
  if [ -S /tmp/kicad/api.sock ] && python3 -c "import kipy; kipy.KiCad().get_board()" >/dev/null 2>&1; then
    echo "      IPC ready at ~${i}s"; break
  fi
  python3 -c "import time; time.sleep(1)"
done

echo "[8/9] pour inner planes (In1=GND, In2=V3V3) + inject routed signals/power"
python3 scripts/add_plane.py GND  In1.Cu --replace              2>&1 | tail -1
python3 scripts/add_plane.py V3V3 In2.Cu --replace --priority 1 2>&1 | tail -1
case "${ROUTER:-freerouting}" in tscircuit|srj) ;; *) python3 scripts/apply_ses_ipc.py "$SES" --save --clear 2>&1 | tail -2 ;; esac

echo "[9/9] fab rules + verify"
python3 scripts/apply_fab_rules.py "$PRO" --fab jlcpcb          2>&1 | tail -1
kill $PCBPID 2>/dev/null || true; pkill -f 'pcbnew index' 2>/dev/null || true
python3 -c "import time; time.sleep(1)"
python3 scripts/check_floating.py "$BOARD" || true
python3 scripts/drc_check.py "$BOARD" 2>&1 | tail -22 || true
echo "DONE — routed $BOARD"
