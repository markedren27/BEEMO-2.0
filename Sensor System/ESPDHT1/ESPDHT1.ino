#define BLYNK_TEMPLATE_ID "TMPL6o3zcPNQF"
#define BLYNK_TEMPLATE_NAME "Beemo"
#define BLYNK_AUTH_TOKEN "Lq0F3W3ovPyeXuqvtFInHhMrgUIzzs6K"
#define BLYNK_PRINT Serial

#include <WiFi.h>
#include <BlynkSimpleEsp32.h>
#include <DFRobot_DHT11.h>
#include <DHT.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// WiFi & Blynk credentials
char auth[] = BLYNK_AUTH_TOKEN;
// char ssid[] = "2.4G-LErj";
// char pass[] = "YgosDfVs";
char ssid[] = "PLDT_Home_92C29";
char pass[] = "Beemo_69";

// DHT Sensor setup
#define DHTPIN 4
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);
DFRobot_DHT11 DFRobotDHT;

// Blynk Timer
BlynkTimer timer;

// Google Sheets setup
const String SHEET_NAME = "DHT11_DataSheet"; // Sheet name
const String host = "script.google.com";
const int httpsPort = 443;
unsigned long lastSheetUpdate = 0;
const unsigned long sheetInterval = 600000; // 10 minutes in milliseconds

// Thresholds
#define TEMP_MIN 32
#define TEMP_MAX 37
#define HUMIDITY_MIN 55
#define HUMIDITY_MAX 65

// Notification timers
unsigned long lastHighTempNotification = 0;
unsigned long lastLowTempNotification = 0;
unsigned long lastHighHumidNotification = 0;
unsigned long lastLowHumidNotification = 0;
unsigned long lastIdealConditionNotification = 0;
#define NOTIFICATION_INTERVAL 32000

void sendSensorData() {
  float h = dht.readHumidity();
  float t = dht.readTemperature();

  // Fallback to DFRobot library
  if (isnan(h) || isnan(t)) {
    DFRobotDHT.read(DHTPIN);
    h = DFRobotDHT.humidity;
    t = DFRobotDHT.temperature;
  }

  if (isnan(h) || isnan(t)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }

  Serial.print("Temperature: ");
  Serial.print(t);
  Serial.print(" °C | Humidity: ");
  Serial.print(h);
  Serial.println(" %");

  Blynk.virtualWrite(V0, t);
  Blynk.virtualWrite(V1, h);

  unsigned long now = millis();
  
  // Temperature Alerts with interval
  if (t > TEMP_MAX && (now - lastHighTempNotification >= NOTIFICATION_INTERVAL)) {
    Blynk.logEvent("high_temp", "[Hive 1] The beehive temperature is too high, which may stress the bees. Ensure the hive is shaded and well-ventilated. Consider relocating it or adding a cooling mechanism to maintain an optimal environment.");
    Serial.println("High Hive Temperature Alert: Notification Sent");
    lastHighTempNotification = now;
  } else if (t < TEMP_MIN && (now - lastLowTempNotification >= NOTIFICATION_INTERVAL)) {
    Blynk.logEvent("low_temp", "[Hive 1] The beehive temperature has dropped below the ideal range. Insulate the hive or provide external heating to protect the colony, especially during colder seasons.");
    Serial.println("Low Hive Temperature Warning: Notification Sent");
    lastLowTempNotification = now;
  }
  
  // Humidity Alerts with interval
  if (h > HUMIDITY_MAX && (now - lastHighHumidNotification >= NOTIFICATION_INTERVAL)) {
    Blynk.logEvent("high_humid", "[Hive 1] High humidity levels detected, which could encourage mold growth and harm the colony. Improve ventilation and check for water pooling near the hive.");
    Serial.println("Excessive Humidity in Beehive: Notification Sent");
    lastHighHumidNotification = now;
  } else if (h < HUMIDITY_MIN && (now - lastLowHumidNotification >= NOTIFICATION_INTERVAL)) {
    Blynk.logEvent("low_humid", "[Hive 1] Humidity levels are too low, potentially leading to dehydration of bees or poor brood development. Consider placing a water source near the hive or adjusting hive insulation.");
    Serial.println("Low Humidity in Beehive: Notification Sent");
    lastLowHumidNotification = now;
  }
  
  // Ideal Condition Alert
  if (t >= TEMP_MIN && t <= TEMP_MAX && h >= HUMIDITY_MIN && h <= HUMIDITY_MAX && (now - lastIdealConditionNotification >= NOTIFICATION_INTERVAL)) {
    Blynk.logEvent("good_temphum", "[Hive 1] Good news! The hive's temperature is within the ideal range of 32–37°C, and humidity is stable between 55–65%. No action needed!");
    Serial.println("Nice! Temperature and Humidity Are Just Right!: Notification Sent");
    lastIdealConditionNotification = now;
  }

  // Every 10 minutes: send to Google Sheets
  if (millis() - lastSheetUpdate >= sheetInterval) {
    sendToGoogleSheets(t, h);
    lastSheetUpdate = millis();
  }
}

void sendToGoogleSheets(float temperature, float humidity) {
  if ((WiFi.status() == WL_CONNECTED)) {
    HTTPClient http;
    String url = "https://script.google.com/macros/s/AKfycbypLna26jSbvZVKJs7DtzEe3IdpI7IPVq1AG227ZFYKGuMUDunQ-jBcIopD2h5R0obbxg/exec";

    // Get date and time
    time_t now;
    struct tm timeinfo;
    if (!getLocalTime(&timeinfo)) {
      Serial.println("Failed to get time");
      return;
    }

    char dateStr[11];
    char timeStr[9];
    strftime(dateStr, sizeof(dateStr), "%Y-%m-%d", &timeinfo);
    strftime(timeStr, sizeof(timeStr), "%H:%M:%S", &timeinfo);

    // Prepare JSON payload
    StaticJsonDocument<200> doc;
    JsonArray values = doc.createNestedArray("values");
    values.add(dateStr);                   // Column A - Date
    values.add(timeStr);                   // Column B - Time
    values.add(String(temperature, 1));    // Column C - Temperature
    values.add(String(humidity, 1));       // Column D - Humidity
    doc["deviceId"] = "ESP32_1";

    String jsonPayload;
    serializeJson(doc, jsonPayload);

    // Make POST request
    http.begin(url);
    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(jsonPayload);

    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.print("Google Sheets Response: ");
      Serial.println(response);
    } else {
      Serial.print("Error sending to Google Sheets. HTTP response code: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi not connected. Skipping Google Sheets update.");
  }
}

void setup() {
  Serial.begin(115200);

  Blynk.begin(auth, ssid, pass);

  // Wait for WiFi
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("WiFi connected!");

  dht.begin();

  // Set timezone to Philippine Standard Time (UTC+8)
  configTzTime("GMT-8", "pool.ntp.org", "time.nist.gov");

  timer.setInterval(2500L, sendSensorData); // Real-time updates
}

void loop() {
  Blynk.run();
  timer.run();
}