# Unplaced D3 · d3b-v3~tracemaker-place

10 boards · placer `tracemaker-place {in} -o {out} --mode full --threads 8` · routed with `tracemaker,freerouting:2.1.0,srj:all`, 60 s per backend

| placement → router | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias |
|---|---|---|---|---|---|
| designer (d3b-v3, best of its backends) | 1.00 | 1.00 | 0.0 | 519 | 5.5 |
| tracemaker-place (best of the backends) | 0.50 | 0.85 | 15.8 | 322 | 6.9 |
| tracemaker-place → tracemaker | 0.50 | 0.85 | 15.8 | 320 | 7.0 |
| designer → tracemaker | 1.00 | 1.00 | 0.0 | 505 | 8.8 |
| tracemaker-place → freerouting:2.1.0 | 0.10 | 0.58 | 3.0 | 404 | 2.0 |
| designer → freerouting:2.1.0 | 0.80 | 0.99 | 0.0 | 538 | 3.8 |
| tracemaker-place → srj:all | 0.00 | 0.60 | 50.7 | 392 | 9.8 |
| designer → srj:all | 0.00 | 1.00 | 49.3 | 504 | 11.9 |

Placer failed on 0 boards; 5 placed boards had DRC errors before routing. Mean placement time 2.5 s.

## Boards

| board | designer | tracemaker-place | placement DRC | place s |
|---|---|---|---|---|
| 0174_sensorboard_DiffIR | ✓ 1.00 · 0 drv (freerouting:2.1.0) | 1.00 · 1 drv (freerouting:2.1.0) | 1 | 1.9 |
| 0144_ottawa-badges-2016_ottawa-badge-tagger-2016 | ✓ 1.00 · 0 drv (freerouting:2.1.0) | 0.77 · 50 drv (tracemaker) | 50 | 7.9 |
| 0113_maytal_Maytal | ✓ 1.00 · 0 drv (tracemaker) | ✓ 1.00 · 0 drv (tracemaker) | 0 | 1.4 |
| 0232_ATtiny461Breakout_ATTiny461DevBoard | ✓ 1.00 · 0 drv (freerouting:2.1.0) | 0.37 · 20 drv (tracemaker) | 20 | 1.1 |
| 0288_raspberrypi-3-usb-hub_usb_hub | ✓ 1.00 · 0 drv (tracemaker) | ✓ 1.00 · 0 drv (tracemaker) | 0 | 1.3 |
| 0203_MOD-MPU9150_mod-mpu9150 | ✓ 1.00 · 0 drv (tracemaker) | ✓ 1.00 · 0 drv (tracemaker) | 0 | 0.4 |
| 0260_NiMH-Charger_NiMH Charger | ✓ 1.00 · 0 drv (tracemaker) | ✓ 1.00 · 0 drv (tracemaker) | 0 | 1.3 |
| 0316_kicad-workshop_fancyboard | ✓ 1.00 · 0 drv (freerouting) | 0.69 · 8 drv (tracemaker) | 8 | 0.7 |
| 0376_cat-trainer_teensy_base_pcb | ✓ 1.00 · 0 drv (freerouting:2.1.0) | ✓ 1.00 · 0 drv (tracemaker) | 0 | 2.5 |
| 0344_mavbridge_mavbridge | ✓ 1.00 · 0 drv (tracemaker) | 0.66 · 79 drv (tracemaker) | 79 | 6.6 |
