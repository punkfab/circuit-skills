#!/bin/bash
# Diagnose the KiCad IPC path. Everything -> build/diag.log (survives a hard kill).
L=build/diag.log
: > "$L"
echo "[$(date +%T)] start; DISPLAY=$DISPLAY" >>"$L"
echo "kipy version:" >>"$L"; python3 -c "import kipy,inspect,os;print(kipy.__version__ if hasattr(kipy,'__version__') else '?');print('KICAD_API_SOCKET=',os.environ.get('KICAD_API_SOCKET'))" >>"$L" 2>&1

echo "[$(date +%T)] launching pcbnew" >>"$L"
DISPLAY=:0 pcbnew index.circuit.kicad_pcb >build/pcbnew.log 2>&1 &
PID=$!
echo "pcbnew pid=$PID" >>"$L"

for i in $(seq 1 25); do
  python3 - >>"$L" 2>&1 <<'PY'
import time
time.sleep(2)
PY
  alive=$(kill -0 $PID 2>/dev/null && echo yes || echo no)
  echo "[$(date +%T)] t=$((i*2))s pcbnew_alive=$alive" >>"$L"
  # look for api sockets
  ls -1 /tmp/kicad*/*.sock 2>/dev/null >>"$L"
  ls -1 ${XDG_RUNTIME_DIR:-/run/user/$(id -u)}/kicad/*.sock 2>/dev/null >>"$L"
  # try a bare connect
  python3 - >>"$L" 2>&1 <<'PY'
try:
    import kipy
    b = kipy.KiCad().get_board()
    print("CONNECT OK nets=", len(b.get_nets()))
    import sys; sys.exit(42)
except Exception as e:
    print("connect fail:", type(e).__name__, str(e)[:120])
PY
  rc=$?
  if [ $rc -eq 42 ]; then echo "[$(date +%T)] CONNECTED at t=$((i*2))s" >>"$L"; break; fi
  [ "$alive" = "no" ] && { echo "pcbnew died" >>"$L"; break; }
done
kill $PID 2>/dev/null
echo "[$(date +%T)] end" >>"$L"
