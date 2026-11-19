# Direct-Drive CPG Degree Mapping Design

## Intent

Make a direct-drive robot joint follow the main CPG command in physical degrees: CPG 90° is the calibrated Center, and a CPG delta of +10° commands a joint delta of +10° in the configured physical direction.

## Selected approach

Use the SCS15 conversion `180° / 1024 raw` at scale `1.0`, because the project hardware record and Feetech's SCS15 product sheet both specify that resolution, and the user confirmed all four joints are directly driven with no gearing or linkage ratio. Keep the existing measured Center raw values, directions, EEPROM safe limits, Speed 20, serial safety runtime, and Emergency Torque Off behavior.

Alternatives considered:

- Measure raw-per-degree with a protractor for each joint: more accurate, but deferred until physical calibration data is collected.
- Expand in ±10° stages: safer during commissioning, but rejected because the requested behavior is full degree-following now.

## Mapping

`target_raw = center_raw + direction × round((q_deg - 90°) / nominal_degrees_per_count)`

The main CPG clamps all joints to `60–120°`. The hardware mapper retains an independent `±171 raw` envelope and the existing per-ID EEPROM limits.

| ID | Center | Direction | Raw at 60° | Raw at 120° | Configured safe range |
|---:|---:|---:|---:|---:|---:|
| 0 | 410 | -1 | 581 | 239 | 0–870 |
| 1 | 566 | -1 | 737 | 395 | 120–940 |
| 2 | 593 | +1 | 422 | 764 | 165–1023 |
| 3 | 176 | +1 | 5 | 347 | 0–720 |

Nominal raw quantization limits the command/feedback estimate to ±0.087890625° (half a count). Physical accuracy still requires later protractor calibration.

## Motion safety

- Arming continues to synchronize present raw positions before enabling torque.
- `START CPG` is rejected after arming until `GO CENTER` reaches Center and settles successfully.
- CPG retains its 20°/s software rate limit; SCS15 Speed remains 20.
- All target writes remain clamped to the ±171 raw envelope and each Servo's configured safe limits.
- Stop returns to Center under feedback monitoring; Emergency only cuts Torque and never commands Center.

## Display

- Change Servo graph/table from relative angle (`Center = 0°`) to absolute joint angle (`Center = 90°`).
- Use the same `60–120°` y-axis as the CPG graph so commanded CPG and measured Servo feedback can be compared visually.
- Continue showing raw feedback and raw target as the authoritative diagnostic values.

## Tests

- Verify exact 1:1 nominal targets at 60°, 80°, 90°, 100°, and 120° for all directions.
- Verify safe-limit and ±171-raw clamping.
- Verify absolute feedback conversion and quantization tolerance.
- Verify CPG cannot start before a successful Center operation after arming.
- Preserve emergency, serial-fault, shutdown, camera, and existing main CPG regression suites.

