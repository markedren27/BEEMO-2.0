#include "src/OV2640.h"
#include <WiFi.h>
#include <WebServer.h>
#include <WiFiClient.h>

// Select camera model
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

// WiFi credentials
// #define SSID1 "2.4G-LErj"
// #define PWD1 "YgosDfVs"
#define SSID1 "Carl Joseph's S24 FE"
#define PWD1 "12345678910"

OV2640 cam;
WebServer server(80);

const char HEADER[] = "HTTP/1.1 200 OK\r\n"
                      "Access-Control-Allow-Origin: *\r\n"
                      "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";

void handle_jpg_stream() {
  WiFiClient client = server.client();
  if (!client.connected()) return;

  client.print(HEADER);
  
  while (client.connected()) {
    cam.run();

    client.print("--frame\r\n");
    client.print("Content-Type: image/jpeg\r\n");
    client.print("Content-Length: ");
    client.print(cam.getSize());
    client.print("\r\n\r\n");

    client.write((char *)cam.getfb(), cam.getSize());
    client.print("\r\n");

    yield();  // Allow WiFi handling, prevents lag
  }
}

void handle_jpg() {
  WiFiClient client = server.client();
  if (!client.connected()) return;

  cam.run();
  
  client.print("HTTP/1.1 200 OK\r\nContent-Type: image/jpeg\r\n\r\n");
  client.write((char *)cam.getfb(), cam.getSize());
}

void handleNotFound() {
  server.send(200, "text/plain", "ESP32-CAM Server is running.");
}

void setup() {
  Serial.begin(115200);
  setCpuFrequencyMhz(240);  // Boost CPU speed for smoother video

  // **WiFi Optimization**
  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID1, PWD1);
  WiFi.setSleep(false);  // Disable WiFi power saving (lowers latency)
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println(F("\nWiFi connected"));
  Serial.print("Stream Link: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");

  // **Camera Configuration for Better Quality**
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 25000000;  // Pushes camera sensor to best performance
  config.pixel_format = PIXFORMAT_JPEG;

  // **Frame parameters (Larger Frame + Better Compression)**
  config.frame_size = FRAMESIZE_CIF;  // 800x600 resolution //SVGA
  config.jpeg_quality = 20;  // Balances image quality & network speed /12
  config.fb_count = 2;  // Triple buffering for a smoother stream /3

  cam.init(config);

  // **Network Optimizations**
  server.on("/mjpeg/1", HTTP_GET, handle_jpg_stream);
  server.on("/stream", HTTP_GET, handle_jpg_stream);  // Alternative path for Blynk
  server.on("/jpg", HTTP_GET, handle_jpg);
  server.onNotFound(handleNotFound);
  server.begin();
}

void loop() {
  server.handleClient();
}