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

void drawRightAligned(int right, int y, const char *text) {
  display.drawStr(right - display.getStrWidth(text), y, text);
}

// One row in fixed columns (6 px wide font): provider, window, remaining %, reset timer.
void drawWindow(int y, const char *provider, const char *window, int remaining, int reset) {
  display.drawStr(0, y, provider);
  display.drawStr(42, y, window);
  drawRightAligned(84, y, remainingText(remaining).c_str());
  drawRightAligned(121, y, resetText(reset).c_str());
}

void drawMessage(const char *title, const char *line1, const char *line2) {
  display.setFont(u8g2_font_6x13B_tf);
  display.drawStr(0, 12, title);
  display.drawHLine(0, 16, 128);
  display.setFont(u8g2_font_6x13_tf);
  display.drawStr(0, 36, line1);
  display.drawStr(0, 54, line2);
}

void drawScreen() {
  display.clearBuffer();
  if (!haveData) {
    drawMessage("AI USAGE MONITOR", "Waiting for Windows", "Run start-bridge");
  } else if (millis() - lastDataMillis > LINK_TIMEOUT_MS) {
    drawMessage("CONNECTION LOST", "No data from Windows", "Run start-bridge");
  } else if (fields[8] == -2) {
    drawMessage("AI USAGE MONITOR", "No usage cache found", "Open desktop monitor");
  } else {
    display.setFont(u8g2_font_6x13B_tf);
    drawWindow(12, "Claude", "5h", fields[0], fields[1]);
    drawWindow(27, "Claude", "wk", fields[2], fields[3]);
    display.drawHLine(0, 32, 128);
    drawWindow(47, "Codex", "5h", fields[4], fields[5]);
    drawWindow(62, "Codex", "wk", fields[6], fields[7]);
    if (fields[8] == 1) {
      display.setFont(u8g2_font_5x7_tf);
      display.drawStr(123, 7, "*");
    }
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
