#include <Arduino.h>
#include <U8g2lib.h>
#include <Wire.h>

// Common 128x64 SSD1306 I2C OLED. ESP32 default I2C pins: SDA=21, SCL=22.
U8G2_SSD1306_128X64_NONAME_F_HW_I2C display(U8G2_R0, U8X8_PIN_NONE);

static const int FIELD_COUNT = 9;
// The bridge sends a line every second; after this long without one, show "connection lost".
static const unsigned long LINK_TIMEOUT_MS = 5000;
int fields[FIELD_COUNT];
char lineBuffer[128];
size_t lineLength = 0;
bool haveData = false;
unsigned long lastDataMillis = 0;

String resetText(int seconds) {
  if (seconds < 0) return "--";
  if (seconds >= 86400) {
    char text[12];
    snprintf(text, sizeof(text), "%dd%02dh", seconds / 86400, (seconds % 86400) / 3600);
    return String(text);
  }
  char text[12];
  snprintf(text, sizeof(text), "%02d:%02d", seconds / 3600, (seconds % 3600) / 60);
  return String(text);
}

String remainingText(int value) {
  return value < 0 ? String("--") : String(value) + "%";
}

void parseLine(char *line) {
  int values[FIELD_COUNT];
  int index = 0;
  char *token = strtok(line, ",");
  while (token != nullptr && index < FIELD_COUNT) {
    values[index++] = atoi(token);
    token = strtok(nullptr, ",");
  }
  if (index != FIELD_COUNT) return;  // Ignore incomplete lines.
  memcpy(fields, values, sizeof(fields));
  haveData = true;
  lastDataMillis = millis();
}

void receiveSerial() {
  while (Serial.available() > 0) {
    char ch = static_cast<char>(Serial.read());
    if (ch == '\n') {
      lineBuffer[lineLength] = '\0';
      parseLine(lineBuffer);
      lineLength = 0;
    } else if (ch != '\r' && lineLength < sizeof(lineBuffer) - 1) {
      lineBuffer[lineLength++] = ch;
    } else if (lineLength >= sizeof(lineBuffer) - 1) {
      lineLength = 0;
    }
  }
}

void drawWindow(int y, const char *provider, const char *window, int remaining, int reset) {
  char row[28];
  String rem = remainingText(remaining);
  String timer = resetText(reset);
  snprintf(row, sizeof(row), "%s %s %s %s", provider, window, rem.c_str(), timer.c_str());
  display.drawStr(0, y, row);
}

void drawScreen() {
  display.clearBuffer();
  display.setFont(u8g2_font_5x7_tf);
  if (!haveData) {
    display.drawStr(0, 14, "AI USAGE MONITOR");
    display.drawStr(0, 31, "Waiting for Windows");
    display.drawStr(0, 45, "Start bridge.py");
  } else if (millis() - lastDataMillis > LINK_TIMEOUT_MS) {
    display.drawStr(0, 14, "CONNECTION LOST");
    display.drawStr(0, 31, "No data from Windows");
    display.drawStr(0, 45, "Start bridge.py");
  } else if (fields[8] == -2) {
    display.drawStr(0, 14, "AI USAGE MONITOR");
    display.drawStr(0, 31, "No usage cache found");
    display.drawStr(0, 45, "Open desktop monitor");
  } else {
    drawWindow(10, "CLAUDE", "5h", fields[0], fields[1]);
    drawWindow(23, "CLAUDE", "wk", fields[2], fields[3]);
    display.drawHLine(0, 29, 128);
    drawWindow(42, "CODEX", "5h", fields[4], fields[5]);
    drawWindow(55, "CODEX", "wk", fields[6], fields[7]);
    if (fields[8] == 1) display.drawStr(121, 8, "*");
  }
  display.sendBuffer();
}

void setup() {
  Serial.begin(115200);
  Wire.begin(21, 22);
  display.setI2CAddress(0x3C * 2);
  display.begin();
  display.setBusClock(400000);
  drawScreen();
}

void loop() {
  receiveSerial();
  static unsigned long lastDraw = 0;
  if (millis() - lastDraw >= 500) {
    drawScreen();
    lastDraw = millis();
  }
}
