#include <WiFi.h>
#include <ArduinoJson.h>
#include <WiFiClientSecure.h>
#include <MQTTClient.h>
#include <time.h>

const char* ssid = <wifi ssid>;
const char* password = <wifi password>;

// Azure IoT Hub settings
const char* host = <host>;
const char* deviceId = <device id>;
const char* sasToken = <sasToken>;
const int mqttPort = 8883;

WiFiClientSecure net;
MQTTClient mqttClient(256);
WiFiServer server(1234);

const int pumpPin = 16;
const int solenoidPins[] = {4, 5, 13, 14, 17, 21}; // could vary
const int numSolenoids = sizeof(solenoidPins) / sizeof(solenoidPins[0]);

void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, password);
    Serial.print("Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.print(".");
    }
    Serial.println("\nWiFi connected.");

    pinMode(pumpPin, OUTPUT);
    digitalWrite(pumpPin, LOW);

    for (int i = 0; i < numSolenoids; i++) {
        pinMode(solenoidPins[i], OUTPUT);
        digitalWrite(solenoidPins[i], LOW);
    }

    server.begin();
    net.setInsecure();
    mqttClient.begin(host, mqttPort, net);
    mqttClient.onMessage(messageHandler);

    syncTime();
    connectToAzure();
}

void connectToAzure() {
    String username = String(host) + "/" + deviceId + "/?api-version=2021-04-12";
    String clientId = deviceId;

    while (!mqttClient.connect(clientId.c_str(), username.c_str(), sasToken)) {
        Serial.print(".");
        delay(1000);
    }
    Serial.println("\nConnected to Azure IoT Hub");
    mqttClient.subscribe("devices/" + String(deviceId) + "/messages/devicebound/#");
}

void loop() {
    mqttClient.loop();

    if (!mqttClient.connected()) {
        connectToAzure();
    }

    WiFiClient client = server.available();
    if (client) {
        while (client.connected()) {
            if (client.available()) {
                String jsonString = client.readStringUntil('\n');
                Serial.println("Signal received : " + jsonString);
                bool ok = processJson(jsonString);
                if (ok) {
                    client.print("Now spraying!\n");
                } else {
                    client.print("JSON error\n");
                }
            }
        }
        client.stop();
        return;
    }

    Serial.println("Listening...");
    delay(10000);
}

bool processJson(String jsonString) {
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, jsonString);

    if (error) {
        Serial.print("JSON parse error: ");
        Serial.println(error.c_str());
        return false;
    }

    JsonArray solenoids = doc["solenoids"];
    int duration = doc["duration"] | 18000;

    if (solenoids.size() == 0) {
        Serial.println("No solenoid data found!");
        shutdown();
        return false;
    }

    bool anyActive = false;
    for (int i = 0; i < numSolenoids && i < solenoids.size(); i++) {
        if (solenoids[i] == 1) {
            anyActive = true;
            break;
        }
    }

    if (!anyActive) {
        Serial.println("No solenoids requested!");
        shutdown();
        return true;
    }

    digitalWrite(pumpPin, HIGH);
    Serial.println("Turning pump and solenoids ON...");

    for (int i = 0; i < numSolenoids && i < solenoids.size(); i++) {
        digitalWrite(solenoidPins[i], solenoids[i] == 1 ? HIGH : LOW);
    }

    Serial.print("Activation for 18 seconds... \n");
    delay(duration);
    shutdown();
    return true;
}

void shutdown() {
    Serial.println("Shutting down...");
    digitalWrite(pumpPin, LOW);

    for (int i = 0; i < numSolenoids; i++) {
        digitalWrite(solenoidPins[i], LOW);
    }

    Serial.println("Pumps and solenoids are now OFF...");
    Serial.println("==================================");
}

void syncTime() {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    time_t now = time(nullptr);

    while (now < 100000) {
        delay(500);
        now = time(nullptr);
    }
}

void messageHandler(String &topic, String &payload) {
    Serial.println("Payload: " + payload);
    bool ok = processJson(payload);
}
