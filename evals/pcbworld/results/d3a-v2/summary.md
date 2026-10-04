# PCBWorld D3A · d3a-v2

99 boards · backends `freerouting,srj:outer,srj:all` · 60 s per backend · {'circuit_skills': '8c6d487', 'capacity_autorouter': '0.0.958'}

| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |
|---|---|---|---|---|---|---|---|
| reference (designer's routing) | 1.00 | 1.00 | 0.0 | 170 | 1.2 | – | 99/99 |
| freerouting | 0.75 | 0.97 | 0.1 | 149 | 0.8 | 3.3 | 99/99 |
| srj:all | 0.22 | 0.98 | 9.9 | 149 | 3.2 | 1.9 | 98/99 |
| srj:outer | 0.22 | 0.98 | 10.0 | 149 | 3.2 | 1.9 | 98/99 |
| **circuit-skills (best of all backends)** | 0.78 | 1.00 | 3.5 | 153 | 1.5 | 7.0 | 99/99 |

PCBWorld paper, Table 3, D3A (@5: best of five rollouts; Freerouting and PPO are 4-seed means):

| method | CP ↑ | Rout. ↑ | time s |
|---|---|---|---|
| Reference | 1.00 | 1.00 | – |
| Freerouting 2.1.0 | 0.80 | 0.91 | 7.1 |
| KiCadRoutingTools | 0.74 | 0.94 | 0.7 |
| OrthoRoute | 0.02 | 0.53 | 2.2 |
| GPT-5.4 agent | 0.65 | 0.91 | 231.2 |
| GPT-5.4-mini agent | 0.28 | 0.72 | 56.9 |
| PPO | 0.86 | 0.95 | 1.8 |
| PPO (w/o finish) | 0.94 | 0.99 | 3.0 |

Clean boards by the backend that produced the kept candidate: freerouting 67, srj:outer 10

## Does the placement score predict it?

77 boards came back clean and 22 did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):

| placement metric (bare board) | AUC | mean, clean | mean, not clean |
|---|---|---|---|
| congestion_max | 0.56 | 1.29 | 1.20 |
| congestion_p95 | 0.55 | 0.42 | 0.50 |
| over_capacity_pct | 0.57 | 0.92 | 1.63 |
| crossings | 0.66 | 4.74 | 7.18 |
| escape_ratio | 0.49 | 0.00 | 0.00 |
| signal_nets | 0.56 | 6.38 | 6.77 |
| mst_mm | 0.48 | 130.73 | 137.66 |

route_eval diagnosis vs outcome: hand-finish: 0 clean / 22 not, order-ready: 77 clean / 0 not

## Boards

| board | u0 | freerouting | srj:all | srj:outer | circuit-skills |
|---|---|---|---|---|---|
| 0001_rufs__autosave-simple_kicad_schema_and_pcb_v1 | 3 | ✓ 1.00 · 0 drv | 1.00 · 1 drv | 1.00 · 1 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0002_rufs_simple_kicad_schema_and_pcb_v1 | 3 | ✓ 1.00 · 0 drv | 1.00 · 1 drv | 1.00 · 1 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0003_kitspace_grove_adaptor | 4 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0004_S1G-Mod_JST_Adapter | 4 | 0.75 · 0 drv | 1.00 · 1 drv | 1.00 · 2 drv | 1.00 · 1 drv (srj:all) |
| 0006_raspberry_pi_pullup_button_pullup_shutdown_button | 5 | ✓ 1.00 · 0 drv | 1.00 · 3 drv | 1.00 · 3 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0007_raspberry_pi_pullup_button_pullup_shutdown_button(revB) | 5 | ✓ 1.00 · 0 drv | 1.00 · 4 drv | 1.00 · 4 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0005_AVR-Playground_hello_world | 5 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0008_CapPCB_CapPcb | 8 | ✓ 1.00 · 0 drv | 1.00 · 14 drv | 1.00 · 14 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0010_SmartLaserCO2-PCB_OptAdjust | 6 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0012_kitspace_ir_sensor | 7 | ✓ 1.00 · 0 drv | 1.00 · 1 drv | 1.00 · 1 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0009_SmartLaserCO2-PCB_WaterCool | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0011_PixyWirelessShield_Shield PIXY | 5 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0014_hardware-designs_m-trigger | 8 | 0.88 · 0 drv | 1.00 · 4 drv | 1.00 · 4 drv | 1.00 · 4 drv (srj:outer) |
| 0013_crossover-schiit-stack_xover4schiit | 9 | ✓ 1.00 · 0 drv | 1.00 · 63 drv | 1.00 · 64 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0015_kitspace_tt_opt101_module_b1 | 7 | ✓ 1.00 · 0 drv | 1.00 · 4 drv | 1.00 · 4 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0016_breakout-boards_avr-isp-x2 | 6 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0018_Hardware_Playground_hy_adapter | 6 | ✓ 1.00 · 0 drv | 1.00 · 4 drv | 1.00 · 4 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0019_CubeSAT-Reaction-Wheel_Edison_Motor_Servo | 8 | ✓ 1.00 · 0 drv | 1.00 · 9 drv | 1.00 · 9 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0017_Blink-Eras_AVR_ISP_Pogo | 6 | 0.83 · 0 drv | 1.00 · 18 drv | 1.00 · 19 drv | 1.00 · 18 drv (srj:all) |
| 0020_Cherry-Mx-Bitboard_Cherry Mx Bitboard | 11 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0021_RPi-PWM-Fan-interface_RPi PWM Fan interface | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0022_OpenVNAVI_motor unit | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0023_hardware-designs_si7021-board | 10 | ✓ 1.00 · 0 drv | 1.00 · 7 drv | 1.00 · 7 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0024_memsarray_mems_modules | 10 | 0.80 · 0 drv | 1.00 · 5 drv | 1.00 · 5 drv | 1.00 · 5 drv (srj:outer) |
| 0026_PCB_constant_current_ac_hv | 9 | 1.00 · 4 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0025_kitspace_hum_temp_sensor | 10 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0027_ID-FIX_scanConnect | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0028_hardware-designs_c-trigger | 9 | ✓ 1.00 · 0 drv | 1.00 · 2 drv | 1.00 · 2 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0029_espeverywhere__autosave-espeverywhere_breakout | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0030_kitspace_sop8breakout | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0031_kitspace_Potentiometer_mount_4LED | 8 | ✓ 1.00 · 0 drv | 1.00 · 5 drv | 1.00 · 5 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0034_NavigationThing_NavigationThingBacklight | 14 | 0.86 · 0 drv | failed | failed | 0.86 · 0 drv (freerouting) |
| 0032_kitspace_Potentiometer_mount_8LED | 8 | ✓ 1.00 · 0 drv | 1.00 · 1 drv | 1.00 · 1 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0033_breakout-boards_swd-to-wires | 9 | ✓ 1.00 · 0 drv | 1.00 · 11 drv | 1.00 · 11 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0036_nRF24breakoutBoard_nRF24-breakout | 10 | 0.90 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | 1.00 · 6 drv (srj:outer) |
| 0035_KiCad-Like-a-Pro-Tutorial_rf24-breakout-v1 | 10 | ✓ 1.00 · 0 drv | 1.00 · 17 drv | 1.00 · 17 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0037_hardware-designs_spsgrf-board | 10 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0038_PCB_serie_led_strip | 9 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0039_drawduino_drawduino | 14 | ✓ 1.00 · 0 drv | 1.00 · 12 drv | 1.00 · 12 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0040_oshtimer_transponder | 12 | ✓ 1.00 · 0 drv | 1.00 · 2 drv | 1.00 · 2 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0041_FogDrive_attiny45_slim | 12 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0042_starsynctrackers_reset_switch | 12 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0045_retroreflectors_TANGOFLOCK | 14 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0044_blink-errr_blink-errr | 15 | ✓ 1.00 · 0 drv | 1.00 · 13 drv | 1.00 · 13 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0043_breakout-boards_swd-and-uart | 11 | ✓ 1.00 · 0 drv | 1.00 · 5 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0046_mearm-base-pcb_ServoPCB | 14 | 0.93 · 0 drv | 1.00 · 21 drv | 1.00 · 21 drv | 1.00 · 21 drv (srj:outer) |
| 0047_LoLin_Designs_LoLin | 14 | ✓ 1.00 · 0 drv | 1.00 · 11 drv | 1.00 · 12 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0048_MySRaspiGW_MySRaspiGW | 13 | 0.77 · 0 drv | 1.00 · 20 drv | 1.00 · 20 drv | 1.00 · 20 drv (srj:outer) |
| 0049_MySRaspiGW_MySRaspiGW_PA_LNA | 13 | ✓ 1.00 · 0 drv | 1.00 · 9 drv | 1.00 · 9 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0050_MySRaspiGW_MySRaspiGW_PA_LNA_Pimoroni | 13 | 0.92 · 0 drv | 1.00 · 40 drv | 1.00 · 40 drv | 1.00 · 40 drv (srj:outer) |
| 0053_mechkeys_lfk78-jtag | 10 | ✓ 1.00 · 0 drv | 1.00 · 12 drv | 1.00 · 12 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0052_breakout-boards_50-to-100 | 10 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0051_MySRaspiGW_MySRaspiGW_Pimoroni | 13 | 0.85 · 0 drv | 1.00 · 18 drv | 1.00 · 18 drv | 1.00 · 18 drv (srj:outer) |
| 0055_dustbox_Dustbox | 14 | ✓ 1.00 · 0 drv | 1.00 · 11 drv | 1.00 · 11 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0056_nrf2rfm69_nrf2rfm69 | 12 | ✓ 1.00 · 0 drv | 1.00 · 30 drv | 1.00 · 30 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0057_tepmachcha_tepmachcha | 12 | 0.92 · 0 drv | 1.00 · 33 drv | 1.00 · 33 drv | 1.00 · 33 drv (srj:outer) |
| 0059_marlin-neopixel-bridge_ATtiny85_Marneo | 16 | 0.88 · 0 drv | 1.00 · 14 drv | 1.00 · 14 drv | 1.00 · 14 drv (srj:all) |
| 0058_scimpy_powersupply | 17 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0060_Paperino_HW_paperino_breakout | 11 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0054_induction-hob_temperature-sensor | 15 | 0.93 · 0 drv | 1.00 · 10 drv | 1.00 · 10 drv | 1.00 · 10 drv (srj:outer) |
| 0062_I2CTempsensor_sensors | 18 | ✓ 1.00 · 0 drv | 1.00 · 9 drv | 1.00 · 9 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0061_kitspace_temp_breakout | 20 | ✓ 1.00 · 0 drv | 0.95 · 11 drv | 0.95 · 11 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0063_stlinkv2_breakout_stlink_breakout | 17 | ✓ 1.00 · 0 drv | 1.00 · 1 drv | 1.00 · 1 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0064_kicad-guitar-preamp_Preamp-Instructables | 17 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0065_DiscoDanceFloorV1_BusTerminator | 16 | ✓ 1.00 · 0 drv | 1.00 · 13 drv | 1.00 · 13 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0067_radio_saw_dcc6c | 19 | ✓ 1.00 · 0 drv | 0.79 · 4 drv | 0.84 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0068_AVR-ISP_pogo-plug_1.27mm_AVR-ISP_pogo-plug_1.27mm | 6 | ✓ 1.00 · 0 drv | 1.00 · 1 drv | 1.00 · 1 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0066_ESP8266-WS2811-LEDs_ws2811controller_panels | 15 | 1.00 · 3 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0069_C-BISCUIT_crowbar | 18 | ✓ 1.00 · 0 drv | 0.83 · 4 drv | 0.83 · 4 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0070_Raspberry-Pi-Soft-Power-Controller_Switching Supply TPS563208 MCI | 17 | ✓ 1.00 · 0 drv | 1.00 · 3 drv | 1.00 · 3 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0071_hackyflasher_Flasher | 16 | 0.94 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj:outer) |
| 0073_z2amiller_sensorboard_programmer | 15 | ✓ 1.00 · 0 drv | 1.00 · 5 drv | 1.00 · 5 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0072_esp8266_wi07_3_adapter_esp | 15 | 0.93 · 0 drv | 1.00 · 13 drv | 1.00 · 13 drv | 1.00 · 13 drv (srj:outer) |
| 0074_kitspace_12V5A_breakout | 22 | ✓ 1.00 · 0 drv | 1.00 · 7 drv | 1.00 · 7 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0075_RPi-ATtiny85-Programmer_rpi_attiny85_programmer | 13 | ✓ 1.00 · 0 drv | 1.00 · 33 drv | 1.00 · 33 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0076_breakout-boards_usb-5v-3v3 | 22 | ✓ 1.00 · 0 drv | 1.00 · 16 drv | 1.00 · 16 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0077_HaveSome_PCB_HaveSomePCB | 19 | ✓ 1.00 · 0 drv | 0.79 · 4 drv | 0.79 · 4 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0078_Hardware_Playground_buck_led_driver | 15 | 0.67 · 0 drv | 1.00 · 1 drv | 1.00 · 1 drv | 1.00 · 1 drv (srj:outer) |
| 0079_Inkjet_InkjetBreakout | 13 | ✓ 1.00 · 0 drv | 1.00 · 32 drv | 1.00 · 32 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0080_kitspace_RPi_shield | 22 | 0.95 · 0 drv | 1.00 · 7 drv | 1.00 · 7 drv | 1.00 · 7 drv (srj:outer) |
| 0082_firefly-jar_solar_lamp | 20 | 0.95 · 0 drv | 1.00 · 44 drv | 1.00 · 44 drv | 1.00 · 44 drv (srj:outer) |
| 0081_everled_everled | 20 | ✓ 1.00 · 0 drv | 1.00 · 26 drv | 1.00 · 26 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0084_kitspace__autosave-nunchuk_breakout | 21 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0085_mini-whip_mini-whip-power-feed | 23 | 0.87 · 0 drv | 0.74 · 13 drv | 0.74 · 13 drv | 0.87 · 0 drv (freerouting) |
| 0087_solar-lanterns_proto1 | 21 | 0.95 · 0 drv | 1.00 · 13 drv | 1.00 · 13 drv | 1.00 · 13 drv (srj:outer) |
| 0088_DA_Lamp_attiny44a_servo_i2c | 20 | 0.95 · 2 drv | 1.00 · 35 drv | 1.00 · 35 drv | 1.00 · 35 drv (srj:outer) |
| 0086_BB-PWR-8009_BB-PWR-8009_revA | 22 | 0.91 · 0 drv | 1.00 · 29 drv | 1.00 · 28 drv | 1.00 · 28 drv (srj:outer) |
| 0083_DustSensorShield_DustSensorShield | 17 | 0.82 · 0 drv | 1.00 · 11 drv | 1.00 · 11 drv | 1.00 · 11 drv (srj:all) |
| 0090_keyboard_converter_adapter_ibm4704_converter_adapter_ibm4704 | 19 | ✓ 1.00 · 0 drv | 1.00 · 17 drv | 1.00 · 17 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0089_cobwebb-junction-box_CobwebbJunctionBox | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0091_rufs_dra818v_breakout_board | 18 | ✓ 1.00 · 0 drv | 1.00 · 15 drv | 1.00 · 15 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0092_DerKnopf_power-supply | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0093_kitspace_nunchuk_breakout | 21 | ✓ 1.00 · 0 drv | 1.00 · 6 drv | 1.00 · 6 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0095_PsuFanController_FanController | 22 | ✓ 1.00 · 0 drv | 1.00 · 18 drv | 1.00 · 18 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0097_bristle_bot_light_follow_bristle_bot | 21 | ✓ 1.00 · 0 drv | 1.00 · 38 drv | 1.00 · 38 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0098_MSGEQ7-Breakout-Board_MSGEQ7_Breakout_Board | 19 | ✓ 1.00 · 0 drv | 1.00 · 13 drv | 1.00 · 13 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0094_kitspace_gas_sensor | 23 | ✓ 1.00 · 0 drv | 1.00 · 4 drv | 1.00 · 4 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0099_SparkSwitch_SparkProtectionSwitch | 24 | ✓ 1.00 · 0 drv | 1.00 · 18 drv | 1.00 · 18 drv | ✓ 1.00 · 0 drv (freerouting) |
| 0100_smt-zvs-driver_IH10-mc | 14 | ✓ 1.00 · 0 drv | 1.00 · 30 drv | 1.00 · 30 drv | ✓ 1.00 · 0 drv (freerouting) |

Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board's own .kicad_pro, single run per backend (the paper reports @5).
