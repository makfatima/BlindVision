# Sensor Fusion and Alert Arbitration

Source of truth: `goggles/fusion/fusion_engine.py`, configured from
`config/fusion_config.yaml`. This document mirrors Section IV of the
manuscript.

## Score-level fusion

Each modality first produces an interpreted confidence or proximity
value; the fusion engine combines *those scores*, not raw sensor
features or independent go/no-go decisions:

```
R = w_vc * C + w_vp * P + w_sp * U + w_sc * W
```

| Symbol | Meaning | Weight (tuned) |
|---|---|---|
| C | vision class confidence | w_vc = 0.40 |
| P | vision proximity | w_vp = 0.20 |
| U | stick (ultrasonic) proximity | w_sp = 0.25 |
| W | stick critical/water-flag term | w_sc = 0.15 |

Per-modality breakdown:

```
R_vision = w_vc · c + w_vp · prox(d_vision, D_vmax)      D_vmax = 8 m
R_stick  = w_sp · prox(d_stick, D_smax) + w_sc · flag(d_stick < 0.5 m)   D_smax = 3 m

prox(d, D_max) = clip(1 - d/D_max, 0, 1)
```

The weight **ordering** (`w_vc > w_sp > w_vp > w_sc`) is the design
claim being defended, not the exact decimal values: a confidently
classified vision object should dominate the fused score; ground-level
proximity should outweigh a merely nearby-but-unclassified vision
detection; the binary critical-obstacle flag acts as a floor-raiser,
not a dominant term on its own.

> **Caveat carried over from the manuscript:** the four weights were set
> by manual bench calibration across staged scenarios, not an automated
> search or sensitivity analysis. A ±20% one-parameter-at-a-time sweep
> against the navigation protocol (Section VI.F) has not yet been run.
> Treat the exact decimal values as a starting point for your own
> calibration, not a proven-optimal configuration.

## Algorithm 1 — priority-tier arbitration

Evaluated top-down; the first matching tier wins. Implemented in
`FusionEngine.evaluate()`.

```
1:  if stick.sos_pressed                                  → SOS
2:  if stick.down_distance > 0.5 m                         → CRITICAL_DROPOFF
3:  if nearest_stick_distance < 0.5 m
       or (vision_class in HIGH_RISK and
           nearest_vision_distance <= 2.0 m)               → CRITICAL_OBSTACLE
4:  if stick.water_detected                                → WATER_HAZARD
5:  if stick.fall_detected                                 → FALL_ALERT
6:  R <- 0.40*C + 0.20*P + 0.25*U + 0.15*W
7:  if R >= 0.8                                             → HIGH_RISK_FUSED
8:  if min(nearest_stick_distance, nearest_vision_distance)
       < 1.2 m                                              → MEDIUM
9:  if min(nearest_stick_distance, nearest_vision_distance)
       < 2.0 m                                              → LOW
10: if stick.battery_pct < 20%                               → LOW_BATTERY
11: else                                                     → ROUTINE
```

`HIGH_RISK` vision classes (line 3): `person`, `vehicle`, `bicycle`.

### Distance bands (Table I)

| Distance | Priority |
|---|---|
| 0–0.5 m | Critical |
| 0.5–1.2 m | Medium |
| 1.2–2.0 m | Low |
| >2.0 m | Routine |

### Complexity

O(n) per fusion cycle to build C/P from the currently detected vision
objects (n is small in practice), then O(1) to evaluate the ten tiers.
O(1) memory — only the current frame's readings and the previous tier
decision are retained.

### Degraded-mode behavior

- **Stick disconnected** (no packet > `stick_link_timeout_s`, default 5s):
  tiers 2–6 are simply unavailable — not defaulted to a false-safe
  value. `FusionEngine.evaluate(detections, stick=None)` reflects this.
- **Individual sensor out of calibration**: that term is dropped from
  the weighted sum rather than substituted with an assumed value —
  `prox()` returns 0 for a missing distance rather than guessing.

### Worked example (Section IV)

A person 4 m ahead (`c=0.8`) and a car 10 m ahead (`c=0.9`); the
stick's forward ultrasound reads 0.4 m. Because 0.4 m < 0.5 m, tier 3
fires immediately as `CRITICAL_OBSTACLE`, regardless of the fused
vision-side risk score. This exact scenario is covered by
`goggles/tests/test_fusion_engine.py::test_worked_example_stick_wins_over_fused_vision`.

## Alert output

`goggles/fusion/alert_messages.py` maps each tier to:
- a spoken phrase (e.g. `"Pole left 0.8 meters."`), suppressed with a
  cooldown by `goggles/audio/tts_alert.py` to avoid flicker/duplicates
  on a stationary obstacle;
- a haptic pattern — continuous vibration for `CRITICAL_DROPOFF` /
  `CRITICAL_OBSTACLE`, increasing pulse rate as distance decreases for
  lower tiers, and a reserved three-pulse pattern for `SOS` that never
  overlaps a normal hazard signal.
