# 🛠️ Setup Guide

## First-time setup

### Step 1 — Flash the ESP32 (once only)

1. Open `hardware/esp32_leds.ino` in Arduino IDE
2. Edit the WiFi credentials at the top of the file:
   ```cpp
   const char* ssid     = "YOUR_HOTSPOT_NAME";
   const char* password = "YOUR_HOTSPOT_PASSWORD";
   ```
3. Select board: **ESP32 WROOM-32** (install via Boards Manager if missing)
4. Install the **FastLED** library via Library Manager
5. Upload the sketch
6. Done — you never need to plug the ESP32 into a PC again

### Step 2 — Install Python dependencies

```bash
pip install websockets
pip install qrcode        # optional
```

---

## Every session

1. **Turn on the hotspot** on your phone
2. **Plug in the ESP32** (USB battery or power bank) — LEDs flash blue while connecting, then green when ready
3. **Launch the server** on your PC:
   ```bash
   python web/server.py
   ```
   The server will print:
   ```
   Recherche de l'ESP32 sur le reseau...
   ESP32 trouvee ! IP = 10.75.x.x ✓
   ```
4. **Open the game** on the tablet — use the URL shown in the terminal
5. **Each player scans their QR code** or opens their controller URL

That's it — the game starts once both players are connected.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| ESP32 not found | Make sure it's connected to the same hotspot. Wait up to 60s for auto-discovery. |
| Controller not connecting | Check that the phone is on the same WiFi as the PC |
| Game page not loading | Make sure `server.py` is running and use the exact URL shown in terminal |
| LEDs not responding | Check power supply (ESP32 + 120 LEDs needs ~2A). Restart ESP32. |
| WiFi name changed | Re-flash the ESP32 once with the new credentials |
