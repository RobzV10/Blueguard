# 🔌 Hardware Guide

## Components

| Component | Quantity | Notes |
|-----------|----------|-------|
| ESP32 WROOM-32 | 1 | Any ESP32 dev board works |
| WS2812B LED strip | 2 × 60 LEDs | 5V, 60 LEDs/m recommended |
| 5V power supply | 1 | Min 2A (3A recommended for full brightness) |
| 470Ω resistor | 1 | On the data line (protects ESP32) |
| 1000µF capacitor | 1 | Between 5V and GND (protects LEDs) |
| Jumper wires | — | |

---

## Wiring

```
Power supply 5V ──────────────────────────── LED strip VCC (both)
Power supply GND ─────┬────────────────────── LED strip GND (both)
                      │
                    [1000µF cap between 5V and GND]
                      │
ESP32 GND ────────────┘
ESP32 GPIO 4 ──[470Ω]──────────────────────── LED strip DATA (strip 1, LEDs 0-59)
                                               Strip 1 output → Strip 2 input (LEDs 60-119)
```

**Important:** Do not power the LED strips from the ESP32's 3.3V or 5V pins — they cannot supply enough current. Use a dedicated 5V power supply.

---

## LED layout

```
[ Strip 1 — LEDs 0 to 59  ]  →  Industrial boat (left side of game)
[ Strip 2 — LEDs 60 to 119]  →  Artisanal boat (right side of game)
```

The two strips are chained (data-out of strip 1 → data-in of strip 2) and share the same data pin (GPIO 4).

---

## LED color meaning

| Color | Meaning |
|-------|---------|
| 🔵 Bright blue with waves | Fish population > 50% — ocean healthy |
| 🟠 Orange | Fish population 15–50% — getting scarce |
| 🔴 Red pulsing | Fish population < 15% — critical |
| ⚪ White blinking | Ocean empty (< 2% fish) |
| 🟢 Green flashing | ESP32 connected to WiFi successfully |
| 🔴 Red flashing | WiFi connection failed |
| 🟢 Alternating green at audit | Artisanal player wins |
| 🔴 Alternating red at audit | Industrial player wins |

---

## Arduino pin config

Defined at the top of `esp32_leds.ino`:

```cpp
#define LED_PIN       4       // GPIO pin connected to LED data line
#define NUM_LEDS      120     // Total LEDs (2 × 60)
#define LEDS_PER_SIDE 60      // LEDs per player
#define BRIGHTNESS    80      // 0-255 (80 ≈ 30% — safe for battery)
```

Reduce `BRIGHTNESS` if running on a small power bank.
