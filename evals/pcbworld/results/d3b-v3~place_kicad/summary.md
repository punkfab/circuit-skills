# Unplaced D3 · d3b-v3~place_kicad

10 boards · placer `/usr/bin/python3 ~/sandbox/punkfab/circuit-skills/pcb-layout/scripts/place_kicad.py {in} -o {out}` · routed with `tracemaker,freerouting:2.1.0,srj:all`, 60 s per backend

| placement → router | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias |
|---|---|---|---|---|---|
| designer (d3b-v3, best of its backends) | 1.00 | 1.00 | 0.0 | 519 | 5.5 |
| place_kicad (best of the backends) | 0.10 | 0.94 | 4.0 | 447 | 10.5 |
| place_kicad → tracemaker | 0.10 | 0.85 | 3.6 | 445 | 14.9 |
| designer → tracemaker | 1.00 | 1.00 | 0.0 | 505 | 8.8 |
| place_kicad → freerouting:2.1.0 | 0.10 | 0.29 | 3.0 | 386 | 4.3 |
| designer → freerouting:2.1.0 | 0.80 | 0.99 | 0.0 | 538 | 3.8 |
| place_kicad → srj:all | 0.00 | 0.60 | 64.7 | 422 | 17.0 |
| designer → srj:all | 0.00 | 1.00 | 49.3 | 504 | 11.9 |

Placer failed on 0 boards; 9 placed boards had DRC errors before routing. Mean placement time 1.2 s.

## Boards

| board | designer | place_kicad | placement DRC | place s |
|---|---|---|---|---|
| 0174_sensorboard_DiffIR | ✓ 1.00 · 0 drv (freerouting:2.1.0) | 1.00 · 3 drv (tracemaker) | 3 | 0.7 |
| 0144_ottawa-badges-2016_ottawa-badge-tagger-2016 | ✓ 1.00 · 0 drv (freerouting:2.1.0) | ✓ 1.00 · 0 drv (freerouting:2.1.0) | 0 | 0.7 |
| 0113_maytal_Maytal | ✓ 1.00 · 0 drv (tracemaker) | 0.90 · 8 drv (freerouting:2.1.0) | 8 | 0.8 |
| 0232_ATtiny461Breakout_ATTiny461DevBoard | ✓ 1.00 · 0 drv (freerouting:2.1.0) | 0.84 · 5 drv (tracemaker) | 5 | 0.8 |
| 0288_raspberrypi-3-usb-hub_usb_hub | ✓ 1.00 · 0 drv (tracemaker) | 1.00 · 3 drv (tracemaker) | 3 | 1.0 |
| 0203_MOD-MPU9150_mod-mpu9150 | ✓ 1.00 · 0 drv (tracemaker) | 1.00 · 1 drv (tracemaker) | 1 | 0.8 |
| 0260_NiMH-Charger_NiMH Charger | ✓ 1.00 · 0 drv (tracemaker) | 1.00 · 5 drv (tracemaker) | 5 | 1.6 |
| 0316_kicad-workshop_fancyboard | ✓ 1.00 · 0 drv (freerouting) | 1.00 · 1 drv (freerouting:2.1.0) | 1 | 1.1 |
| 0376_cat-trainer_teensy_base_pcb | ✓ 1.00 · 0 drv (freerouting:2.1.0) | 0.94 · 11 drv (tracemaker) | 11 | 1.9 |
| 0344_mavbridge_mavbridge | ✓ 1.00 · 0 drv (tracemaker) | 0.70 · 3 drv (tracemaker) | 3 | 2.3 |
