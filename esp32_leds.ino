// ============================================================
// BlueGuard v8 — Code Arduino ESP32 WROOM 32
// Rouleau 1 (LEDs 0-59)  = Bateau P1 (cote gauche)
// Rouleau 2 (LEDs 60-119) = Bateau P2 (cote droit)
//
// Librairie requise : FastLED
// ============================================================

#include <WiFi.h>
#include <WiFiUdp.h>
#include <FastLED.h>

// ── CONFIG LEDs ──────────────────────────────────────────────
#define LED_PIN      4
#define NUM_LEDS     120     // 2 rouleaux de 60
#define LEDS_PER_SIDE 60     // 60 LEDs par bateau
#define BRIGHTNESS   80
#define LED_TYPE     WS2812B
#define COLOR_ORDER  GRB

CRGB leds[NUM_LEDS];

// ── CONFIG WIFI ──────────────────────────────────────────────
const char* ssid     = "NOM_DU_HOTSPOT";
const char* password = "MOT_DE_PASSE";

// ── SERVEUR TCP ──────────────────────────────────────────────
WiFiServer server(9000);
WiFiClient client;

// ── UDP AUTODISCOVERY ────────────────────────────────────────
// L'ESP32 annonce son IP au serveur Python par broadcast UDP
// Le serveur la detecte automatiquement — plus besoin de la noter !
WiFiUDP udp;
#define UDP_BROADCAST_PORT 47269
#define UDP_BROADCAST_MSG  "BLUEGUARD_ESP32:"
unsigned long lastBroadcast   = 0;
unsigned long broadcastStop   = 0;   // timestamp auquel on arrete les broadcasts
bool          broadcasting    = false;

// ── ETAT ────────────────────────────────────────────────────
float fishP1    = 1.0;   // 0.0 = vide, 1.0 = plein — cote P1
float fishP2    = 1.0;   // cote P2
float maxFish   = 100.0;
String ledMode  = "normal";
float wave      = 0;
unsigned long lastLedUpdate = 0;
unsigned long lastBlink     = 0;
bool  blinkState = false;

// ── Seuils couleur ───────────────────────────────────────────
// > 50 poissons : bleu clair
// 15-50         : assombrissement progressif
// < 15          : rouge
// 0             : blanc clignotant

// ============================================================
void setup() {
  Serial.begin(115200);
  delay(300);

  FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
  FastLED.setBrightness(BRIGHTNESS);
  fill_solid(leds, NUM_LEDS, CRGB(0, 80, 200)); // bleu clair au demarrage
  FastLED.show();

  Serial.print("Connexion WiFi : ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);

  int tries = 0;
  while (WiFi.status() != WL_CONNECTED && tries < 30) {
    delay(500);
    Serial.print(".");
    tries++;
    // Animation rotation pendant connexion
    for (int i = 0; i < NUM_LEDS; i++) {
      leds[i] = (i % 6 == tries % 6) ? CRGB(0,120,255) : CRGB(0,20,60);
    }
    FastLED.show();
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi OK ! IP ESP32 : " + WiFi.localIP().toString());
    Serial.println(">>> Le serveur Python va detecter l'IP automatiquement !");
    // Demarrer UDP broadcast
    udp.begin(UDP_BROADCAST_PORT);
    broadcastStop = millis() + 60000; // broadcast pendant 60 secondes
    broadcasting  = true;
    // Flash vert = connecte
    fill_solid(leds, NUM_LEDS, CRGB(0, 200, 50));
    FastLED.show();
    delay(800);
  } else {
    Serial.println("\nECHEC WiFi — verifie ssid/password");
    fill_solid(leds, NUM_LEDS, CRGB(200, 0, 0));
    FastLED.show();
  }

  server.begin();
  Serial.println("Serveur TCP pret port 9000");
}

// ============================================================
void loop() {
  // UDP broadcast : annonce l'IP toutes les 2s pendant 60s au demarrage
  if (broadcasting && millis() < broadcastStop) {
    if (millis() - lastBroadcast > 2000) {
      lastBroadcast = millis();
      String msg = String(UDP_BROADCAST_MSG) + WiFi.localIP().toString();
      udp.beginPacket(IPAddress(255,255,255,255), UDP_BROADCAST_PORT);
      udp.print(msg);
      udp.endPacket();
      Serial.println("[UDP] Broadcast : " + msg);
    }
  } else if (broadcasting && millis() >= broadcastStop) {
    broadcasting = false;
    Serial.println("[UDP] Broadcast termine. ESP32 prete.");
  }

  // Accepter connexion
  if (!client || !client.connected()) {
    client = server.available();
    if (client) Serial.println("server_leds.py connecte");
  }

  // Lire message
  if (client && client.connected() && client.available()) {
    String msg = client.readStringUntil('\n');
    msg.trim();
    Serial.println("Recu: " + msg);

    if (msg.startsWith("fish:")) {
      // Format "fish:P1:P2:MAX" ex: "fish:72:45:100"
      // ou ancien format "fish:0.75" (compatibilite)
      String data = msg.substring(5);
      int sep1 = data.indexOf(':');
      if (sep1 != -1) {
        int sep2 = data.indexOf(':', sep1 + 1);
        float p1 = data.substring(0, sep1).toFloat();
        float p2 = data.substring(sep1 + 1, sep2 != -1 ? sep2 : data.length()).toFloat();
        float mx = sep2 != -1 ? data.substring(sep2 + 1).toFloat() : 100.0;
        if (mx > 0) { fishP1 = p1 / mx; fishP2 = p2 / mx; }
      } else {
        // Ancien format ratio 0.0-1.0
        float ratio = data.toFloat();
        fishP1 = ratio; fishP2 = ratio;
      }
      fishP1 = constrain(fishP1, 0.0, 1.0);
      fishP2 = constrain(fishP2, 0.0, 1.0);
      ledMode = "normal";

    } else if (msg == "reveal_win") {
      ledMode = "reveal_win";
    } else if (msg == "reveal_red") {
      ledMode = "reveal_red";
    } else if (msg == "reset") {
      ledMode = "normal"; fishP1 = 1.0; fishP2 = 1.0;
    }
  }

  // Update LEDs 50ms
  if (millis() - lastLedUpdate > 50) {
    lastLedUpdate = millis();
    wave += 0.10;

    // Blink toutes les 300ms pour le blanc
    if (millis() - lastBlink > 300) {
      lastBlink = millis();
      blinkState = !blinkState;
    }

    updateSide(0,             LEDS_PER_SIDE, fishP1);
    updateSide(LEDS_PER_SIDE, LEDS_PER_SIDE, fishP2);
    FastLED.show();
  }
}

// ── updateSide : colorie un rouleau selon le niveau de poissons ──────────────
void updateSide(int startLed, int count, float fishLevel) {

  // ── Flash reveal audit ──
  if (ledMode == "reveal_win") {
    bool on = blinkState;
    for (int i = startLed; i < startLed + count; i++)
      leds[i] = on ? CRGB(0, 255, 80) : CRGB(0, 40, 15);
    return;
  }
  if (ledMode == "reveal_red") {
    bool on = blinkState;
    for (int i = startLed; i < startLed + count; i++)
      leds[i] = on ? CRGB(255, 30, 0) : CRGB(50, 8, 0);
    return;
  }

  // ── Blanc clignotant : ocean vide (< 2%) ──
  if (fishLevel < 0.02) {
    for (int i = startLed; i < startLed + count; i++)
      leds[i] = blinkState ? CRGB(255, 255, 255) : CRGB(0, 0, 0);
    return;
  }

  // ── Mode normal : gradient bleu clair → sombre → rouge ──
  for (int i = startLed; i < startLed + count; i++) {
    float w = (sin(wave + (i - startLed) * 0.20) + 1.0) / 2.0; // vague 0-1

    if (fishLevel > 0.50) {
      // > 50% : bleu clair vif avec légères vagues cyan
      // fishLevel 0.5→1.0 : bleu plein
      uint8_t r = 0;
      uint8_t g = (uint8_t)(50 + w * 40);
      uint8_t b = (uint8_t)(180 + w * 60);
      leds[i] = CRGB(r, g, b);

    } else if (fishLevel > 0.15) {
      // 15%-50% : transition bleu sombre → orange
      // t = 0 quand fishLevel=0.50, t = 1 quand fishLevel=0.15
      float t = 1.0 - (fishLevel - 0.15) / 0.35;
      // Bleu(0,60,180) → Orange(200,80,0)
      uint8_t r = (uint8_t)(t * 200 + w * 20);
      uint8_t g = (uint8_t)(60 - t * 20 + w * 20);
      uint8_t b = (uint8_t)((1.0 - t) * 180);
      leds[i] = CRGB(r, g, b);

    } else {
      // < 15% : rouge pulsant
      float pulse = (sin(wave * 3.0 + (i - startLed) * 0.15) + 1.0) / 2.0;
      uint8_t r = (uint8_t)(150 + pulse * 90);
      uint8_t g = (uint8_t)(pulse * 15);
      leds[i] = CRGB(r, g, 0);
    }
  }
}
