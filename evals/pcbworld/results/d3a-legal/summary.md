# PCBWorld D3A · d3a-legal

99 boards · backends `srj-legal:all` · 60 s per backend · {'circuit_skills': 'a0cdac3', 'capacity_autorouter': '0.0.958'}

| method | CP ↑ | Rout. ↑ | DRV ↓ | WL mm | vias | time s | ran |
|---|---|---|---|---|---|---|---|
| reference (designer's routing) | 1.00 | 1.00 | 0.0 | 170 | 1.2 | – | 99/99 |
| srj-legal:all | 0.98 | 0.99 | 0.0 | 172 | 3.3 | 6.6 | 98/99 |
| **circuit-skills (best of all backends)** | 0.98 | 0.99 | 0.0 | 172 | 3.3 | 6.6 | 98/99 |

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

Clean boards by the backend that produced the kept candidate: srj-legal:all 97

## Does the placement score predict it?

97 boards came back clean and 1 did not. AUC = the chance a board that failed scores worse than one that passed (0.5 = no signal):

| placement metric (bare board) | AUC | mean, clean | mean, not clean |
|---|---|---|---|
| congestion_max | 0.30 | 1.24 | 0.75 |
| congestion_p95 | 0.15 | 0.43 | 0.13 |
| over_capacity_pct | 0.27 | 0.91 | 0.00 |
| crossings | 0.91 | 5.23 | 14.00 |
| escape_ratio | 0.49 | 0.00 | 0.00 |
| signal_nets | 0.42 | 6.49 | 6.00 |
| mst_mm | 0.97 | 130.77 | 364.60 |

route_eval diagnosis vs outcome: hand-finish: 14 clean / 1 not, order-ready: 83 clean / 0 not

## Boards

| board | u0 | srj-legal:all | circuit-skills |
|---|---|---|---|
| 0001_rufs__autosave-simple_kicad_schema_and_pcb_v1 | 3 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0002_rufs_simple_kicad_schema_and_pcb_v1 | 3 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0003_kitspace_grove_adaptor | 4 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0004_S1G-Mod_JST_Adapter | 4 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0005_AVR-Playground_hello_world | 5 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0006_raspberry_pi_pullup_button_pullup_shutdown_button | 5 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0007_raspberry_pi_pullup_button_pullup_shutdown_button(revB) | 5 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0008_CapPCB_CapPcb | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0009_SmartLaserCO2-PCB_WaterCool | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0010_SmartLaserCO2-PCB_OptAdjust | 6 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0011_PixyWirelessShield_Shield PIXY | 5 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0012_kitspace_ir_sensor | 7 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0013_crossover-schiit-stack_xover4schiit | 9 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0014_hardware-designs_m-trigger | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0015_kitspace_tt_opt101_module_b1 | 7 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0016_breakout-boards_avr-isp-x2 | 6 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0017_Blink-Eras_AVR_ISP_Pogo | 6 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0018_Hardware_Playground_hy_adapter | 6 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0019_CubeSAT-Reaction-Wheel_Edison_Motor_Servo | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0020_Cherry-Mx-Bitboard_Cherry Mx Bitboard | 11 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0021_RPi-PWM-Fan-interface_RPi PWM Fan interface | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0022_OpenVNAVI_motor unit | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0023_hardware-designs_si7021-board | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0024_memsarray_mems_modules | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0025_kitspace_hum_temp_sensor | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0026_PCB_constant_current_ac_hv | 9 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0027_ID-FIX_scanConnect | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0028_hardware-designs_c-trigger | 9 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0029_espeverywhere__autosave-espeverywhere_breakout | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0030_kitspace_sop8breakout | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0031_kitspace_Potentiometer_mount_4LED | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0032_kitspace_Potentiometer_mount_8LED | 8 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0033_breakout-boards_swd-to-wires | 9 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0034_NavigationThing_NavigationThingBacklight | 14 | failed |  |
| 0035_KiCad-Like-a-Pro-Tutorial_rf24-breakout-v1 | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0036_nRF24breakoutBoard_nRF24-breakout | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0037_hardware-designs_spsgrf-board | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0038_PCB_serie_led_strip | 9 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0039_drawduino_drawduino | 14 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0040_oshtimer_transponder | 12 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0041_FogDrive_attiny45_slim | 12 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0042_starsynctrackers_reset_switch | 12 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0043_breakout-boards_swd-and-uart | 11 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0044_blink-errr_blink-errr | 15 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0045_retroreflectors_TANGOFLOCK | 14 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0046_mearm-base-pcb_ServoPCB | 14 | 0.93 · 0 drv | 0.93 · 0 drv (srj-legal:all) |
| 0047_LoLin_Designs_LoLin | 14 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0048_MySRaspiGW_MySRaspiGW | 13 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0049_MySRaspiGW_MySRaspiGW_PA_LNA | 13 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0050_MySRaspiGW_MySRaspiGW_PA_LNA_Pimoroni | 13 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0051_MySRaspiGW_MySRaspiGW_Pimoroni | 13 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0052_breakout-boards_50-to-100 | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0053_mechkeys_lfk78-jtag | 10 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0054_induction-hob_temperature-sensor | 15 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0055_dustbox_Dustbox | 14 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0056_nrf2rfm69_nrf2rfm69 | 12 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0057_tepmachcha_tepmachcha | 12 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0058_scimpy_powersupply | 17 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0059_marlin-neopixel-bridge_ATtiny85_Marneo | 16 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0060_Paperino_HW_paperino_breakout | 11 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0061_kitspace_temp_breakout | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0062_I2CTempsensor_sensors | 18 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0063_stlinkv2_breakout_stlink_breakout | 17 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0064_kicad-guitar-preamp_Preamp-Instructables | 17 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0065_DiscoDanceFloorV1_BusTerminator | 16 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0066_ESP8266-WS2811-LEDs_ws2811controller_panels | 15 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0067_radio_saw_dcc6c | 19 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0068_AVR-ISP_pogo-plug_1.27mm_AVR-ISP_pogo-plug_1.27mm | 6 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0069_C-BISCUIT_crowbar | 18 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0070_Raspberry-Pi-Soft-Power-Controller_Switching Supply TPS563208 MCI | 17 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0071_hackyflasher_Flasher | 16 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0072_esp8266_wi07_3_adapter_esp | 15 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0073_z2amiller_sensorboard_programmer | 15 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0074_kitspace_12V5A_breakout | 22 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0075_RPi-ATtiny85-Programmer_rpi_attiny85_programmer | 13 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0076_breakout-boards_usb-5v-3v3 | 22 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0077_HaveSome_PCB_HaveSomePCB | 19 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0078_Hardware_Playground_buck_led_driver | 15 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0079_Inkjet_InkjetBreakout | 13 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0080_kitspace_RPi_shield | 22 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0081_everled_everled | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0082_firefly-jar_solar_lamp | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0083_DustSensorShield_DustSensorShield | 17 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0084_kitspace__autosave-nunchuk_breakout | 21 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0085_mini-whip_mini-whip-power-feed | 23 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0086_BB-PWR-8009_BB-PWR-8009_revA | 22 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0087_solar-lanterns_proto1 | 21 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0088_DA_Lamp_attiny44a_servo_i2c | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0089_cobwebb-junction-box_CobwebbJunctionBox | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0090_keyboard_converter_adapter_ibm4704_converter_adapter_ibm4704 | 19 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0091_rufs_dra818v_breakout_board | 18 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0092_DerKnopf_power-supply | 20 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0093_kitspace_nunchuk_breakout | 21 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0094_kitspace_gas_sensor | 23 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0095_PsuFanController_FanController | 22 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0097_bristle_bot_light_follow_bristle_bot | 21 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0098_MSGEQ7-Breakout-Board_MSGEQ7_Breakout_Board | 19 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0099_SparkSwitch_SparkProtectionSwitch | 24 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |
| 0100_smt-zvs-driver_IH10-mc | 14 | ✓ 1.00 · 0 drv | ✓ 1.00 · 0 drv (srj-legal:all) |

Cells: ✓ = clean pass · routability · error-level DRC violations. Scored with stock KiCad 9 kicad-cli DRC against each board's own .kicad_pro, single run per backend (the paper reports @5).
