#!/usr/bin/env python3
# BlueGuard v8 — Serveur WebSocket + Support LEDs ESP32
# Usage: python server_leds.py

import asyncio
import json
import socket
import socket as sock_module
import threading
import os

try:
    import websockets
except ImportError:
    print("Installation de websockets...")
    os.system("pip install websockets -q")
    import websockets

PORT_HTTP = 8080
PORT_WS   = 8765

# ╔══════════════════════════════════════════╗
# ║  IP ESP32 — DETECTION AUTOMATIQUE      ║
# ║  Tu n'as plus rien a modifier ici !    ║
# ║  L'ESP32 annonce son IP toute seule.   ║
# ║  Attends juste "ESP32 trouvee !" au    ║
# ║  demarrage du serveur.                 ║
# ╚══════════════════════════════════════════╝
ESP32_IP   = None   # sera rempli automatiquement par discovery UDP
ESP32_PORT = 9000
UDP_DISCOVERY_PORT = 47269
UDP_DISCOVERY_MSG  = "BLUEGUARD_ESP32:"


# ── Detection automatique de l'IP du serveur ──────────────────
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()



def discover_esp32(timeout=60):
    """Ecoute le broadcast UDP de l'ESP32 et retourne son IP."""
    import socket as _sock
    s = _sock.socket(_sock.AF_INET, _sock.SOCK_DGRAM)
    s.setsockopt(_sock.SOL_SOCKET, _sock.SO_REUSEADDR, 1)
    s.setsockopt(_sock.SOL_SOCKET, _sock.SO_BROADCAST, 1)
    try:
        s.bind(("", UDP_DISCOVERY_PORT))
        s.settimeout(1.0)
        print("  [UDP] Ecoute broadcast ESP32 (max " + str(timeout) + "s)...")
        import time
        start = time.time()
        while time.time() - start < timeout:
            try:
                data, addr = s.recvfrom(256)
                msg = data.decode("utf-8", errors="ignore").strip()
                if msg.startswith(UDP_DISCOVERY_MSG):
                    ip = msg[len(UDP_DISCOVERY_MSG):]
                    return ip
            except _sock.timeout:
                elapsed = int(time.time() - start)
                if elapsed % 5 == 0 and elapsed > 0:
                    print("  [UDP] Attente ESP32... (" + str(elapsed) + "s)")
        return None
    finally:
        s.close()


# ── Connexion TCP persistante vers ESP32 ──────────────────────
esp32_socket = None
esp32_lock   = threading.Lock()

def send_to_leds(message):
    """Envoie un message TCP à l'ESP32. Reconnecte si besoin."""
    if not ESP32_IP:
        return  # ESP32 pas encore trouvee
    def _send():
        global esp32_socket
        with esp32_lock:
            # Connexion si absente
            if esp32_socket is None:
                try:
                    s = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_STREAM)
                    s.settimeout(2.0)
                    s.connect((ESP32_IP, ESP32_PORT))
                    s.settimeout(None)
                    esp32_socket = s
                    print("[LED] Connexion TCP ESP32 etablie")
                except Exception as e:
                    print("[LED] Impossible de joindre ESP32 :", e)
                    return
            # Envoi — reconnexion unique si echec
            try:
                esp32_socket.send((message + "\n").encode())
            except Exception:
                print("[LED] Socket morte, reconnexion...")
                try: esp32_socket.close()
                except: pass
                esp32_socket = None
                try:
                    s = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_STREAM)
                    s.settimeout(2.0)
                    s.connect((ESP32_IP, ESP32_PORT))
                    s.settimeout(None)
                    esp32_socket = s
                    esp32_socket.send((message + "\n").encode())
                    print("[LED] Reconnecte et message envoye")
                except Exception as e2:
                    print("[LED] Echec reconnexion :", e2)
                    esp32_socket = None
    threading.Thread(target=_send, daemon=True).start()


def send_fish_level(pop1, pop2, max_fish=100):
    """Envoie pop1 et pop2 separement - un rouleau par bateau."""
    p1 = int(pop1)
    p2 = int(pop2)
    mx = int(max_fish)
    msg = "fish:" + str(p1) + ":" + str(p2) + ":" + str(mx)
    send_to_leds(msg)


# ── WebSocket ──────────────────────────────────────────────────
clients = {"game": None, "p1": None, "p2": None}
lock = asyncio.Lock()


async def handler(websocket):
    role = None
    try:
        async for message in websocket:
            data = json.loads(message)

            if data.get("type") == "register":
                role = data.get("role")
                async with lock:
                    clients[role] = websocket
                print("[+] " + str(role) + " connecte")
                await websocket.send(json.dumps({"type": "registered", "role": role}))
                async with lock:
                    gws = clients.get("game")
                if gws and role != "game":
                    try:
                        await gws.send(json.dumps({"type": "player_connected", "role": role}))
                    except Exception:
                        pass

            elif data.get("type") in ("input", "button"):
                async with lock:
                    gws = clients.get("game")
                if gws:
                    data["from"] = role
                    try:
                        await gws.send(json.dumps(data))
                    except Exception:
                        pass

            # ── Niveau de poissons → LEDs ──────────────────────
            elif data.get("type") == "fish_count":
                pop1 = data.get("pop1", 50)
                pop2 = data.get("pop2", 50)
                max_fish = data.get("max_fish", 100)
                send_fish_level(pop1, pop2, max_fish)

            # ── Resultat audit → LEDs ──────────────────────────
            elif data.get("type") == "audit_result":
                result = data.get("result", "artisanal_wins")
                msg = "reveal_win" if result == "artisanal_wins" else "reveal_red"
                threading.Thread(target=send_to_leds, args=(msg,), daemon=True).start()

    except Exception:
        pass
    finally:
        if role:
            async with lock:
                if clients.get(role) == websocket:
                    clients[role] = None
            print("[-] " + str(role) + " deconnecte")
            async with lock:
                gws = clients.get("game")
            if gws and role != "game":
                try:
                    await gws.send(json.dumps({"type": "player_disconnected", "role": role}))
                except Exception:
                    pass


def start_http(ip):
    import http.server
    import socketserver
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    class SilentHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

    with socketserver.TCPServer(("", PORT_HTTP), SilentHandler) as httpd:
        httpd.serve_forever()


async def main():
    global ESP32_IP
    ip = get_ip()

    print("")
    print("====================================================")
    print("  BLUEGUARD v8 — SERVEUR LOCAL + LEDs ESP32")
    print("====================================================")
    print("  IP detectee : " + ip)
    print("")
    print("  Recherche de l'ESP32 sur le reseau...")
    print("  (allume l'ESP32 maintenant si ce n'est pas fait)")
    found_ip = discover_esp32(timeout=60)
    if found_ip:
        ESP32_IP = found_ip
        print("  ESP32 trouvee !  IP = " + ESP32_IP + "  ✓")
    else:
        print("  ESP32 non trouvee apres 60s.")
        print("  Les LEDs seront desactivees pour cette session.")
        print("  (Verifie que l'ESP32 est allumee et connectee au meme WiFi)")
    print("")
    print("  TABLETTE (jeu) :")
    print("  http://" + ip + ":" + str(PORT_HTTP) + "/blueguard_v8.html")
    print("")
    print("  JOUEUR 1 (manette) :")
    print("  http://" + ip + ":" + str(PORT_HTTP) + "/controller.html?player=1")
    print("")
    print("  JOUEUR 2 (manette) :")
    print("  http://" + ip + ":" + str(PORT_HTTP) + "/controller.html?player=2")
    print("  ESP32 LEDs : " + (ESP32_IP if ESP32_IP else "non connectee") + ":" + str(ESP32_PORT))
    print("====================================================")

    try:
        import qrcode
        urls = [
            ("TABLETTE", "http://" + ip + ":" + str(PORT_HTTP) + "/blueguard_v8.html"),
            ("P1",       "http://" + ip + ":" + str(PORT_HTTP) + "/controller.html?player=1"),
            ("P2",       "http://" + ip + ":" + str(PORT_HTTP) + "/controller.html?player=2"),
        ]
        for label, url in urls:
            qr = qrcode.QRCode(border=1)
            qr.add_data(url)
            qr.make(fit=True)
            print("")
            print("  QR " + label + " :")
            qr.print_ascii(invert=True)
    except ImportError:
        print("  (pip install qrcode pour afficher les QR codes)")

    t = threading.Thread(target=start_http, args=(ip,), daemon=True)
    t.start()

    print("[HTTP] http://" + ip + ":" + str(PORT_HTTP) + "/")

    async with websockets.serve(handler, "", PORT_WS):
        print("[WS]   ws://" + ip + ":" + str(PORT_WS))
        print("")
        print("En attente de connexions... (Ctrl+C pour arreter)")
        print("")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
