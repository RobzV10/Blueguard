# 🐟 BlueGuard v8

> An educational arcade game about overfishing, playable on a tablet with physical smartphone controllers and LED hardware feedback.

Built for **SDG 14 — Life Below Water** awareness.

---

## 📸 Overview

Two players compete as fishermen across multiple rounds:
- **Player 1** controls an **Industrial** boat (large net, high catch, eco-audit fee at the end)
- **Player 2** controls an **Artisanal** boat (small net, slower, biodiversity bonus)

At the end of the season, an ecological audit is revealed — industrial profits are taxed 30%, and the artisanal player earns a bonus for preserved fish populations.

The game runs entirely in a browser on a local WiFi network (hotspot). Each player uses their smartphone as a joystick controller. Two LED strips connected to an ESP32 display the fish population of each player's ocean in real time.

---

## 🗂️ File Structure

```
blueguard/
│
├── README.md                  ← You are here
│
├── web/
│   ├── blueguard_v8.html      ← Main game (run on tablet/screen)
│   ├── controller.html        ← Player controller (run on smartphones)
│   └── server.py              ← Local WebSocket + HTTP server
│
├── hardware/
│   └── esp32_leds.ino         ← Arduino sketch for ESP32 + LED strips
│
└── docs/
    ├── SETUP.md               ← Step-by-step setup guide
    └── HARDWARE.md            ← Wiring and hardware details
```

---

## ⚡ Quick Start

### Requirements

- Python 3.8+ with `websockets` (auto-installed on first run)
- A WiFi hotspot (phone or router — Samsung hotspot tested)
- One tablet or screen for the game
- Two smartphones for controllers
- *(Optional)* ESP32 + 2× WS2812B LED strips (120 LEDs total)

### 1. Start the server

```bash
python web/server.py
```

The terminal will display the URLs for the game and each controller, and QR codes if `qrcode` is installed:

```
====================================================
  BLUEGUARD v8 — SERVEUR LOCAL + LEDs ESP32
====================================================
  IP detectee : 10.75.236.12

  TABLETTE (jeu) :   http://10.75.236.12:8080/blueguard_v8.html
  JOUEUR 1 :         http://10.75.236.12:8080/controller.html?player=1
  JOUEUR 2 :         http://10.75.236.12:8080/controller.html?player=2
====================================================
```

### 2. Open the game

On the tablet, open `blueguard_v8.html` URL in Chrome.

### 3. Connect the controllers

Each player opens their controller URL on their smartphone. The game starts automatically once both players are connected.

---

## 🔧 Hardware Setup (optional — LEDs)

See [`docs/HARDWARE.md`](docs/HARDWARE.md) for full wiring details.

**Short version:**
1. Flash `hardware/esp32_leds.ino` to your ESP32 (edit WiFi name/password first)
2. Connect 2× strips of 60 WS2812B LEDs to pin 4
3. Power the ESP32 — it auto-discovers the server via UDP broadcast
4. The server detects the ESP32 automatically at startup

No IP configuration needed — the ESP32 announces itself on the network.

---

## 🎮 Controls

| Action | Keyboard (debug) | Smartphone controller |
|--------|------------------|-----------------------|
| Move boat | Arrow keys / WASD | Joystick (left thumb) |
| Cast net | Space | Net button (right thumb) |
| Navigate menus | Enter / Escape | Net button / Back button |

---

## 🏗️ Architecture

```
[Tablet — game]  ←──WebSocket──→  [server.py]  ←──TCP──→  [ESP32 + LEDs]
                                       ↑
                          [Smartphone P1 — controller]
                          [Smartphone P2 — controller]
```

- `server.py` runs an HTTP server (port 8080) to serve all HTML files, and a WebSocket server (port 8765) to relay inputs from controllers to the game and fish population data to the ESP32.
- The ESP32 runs a TCP server on port 9000 and receives `fish:P1:P2:MAX` messages every second.

---

## 📦 Dependencies

### Python
```bash
pip install websockets        # required
pip install qrcode            # optional — prints QR codes in terminal
```

### Arduino (ESP32)
- Board: **ESP32 WROOM-32** (via Arduino IDE board manager)
- Library: **FastLED** (install via Arduino Library Manager)

---

## 🌏 Deployment context

This game was designed to run offline via a Samsung mobile hotspot in China, with no internet access. All assets are self-contained. The ESP32 auto-discovery system (UDP broadcast) avoids any manual IP configuration between sessions.

---

## 📄 License

MIT — free to use, modify, and distribute for educational purposes.
