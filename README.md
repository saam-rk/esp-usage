# esp-usage

Show your remaining **Claude Code** and **Codex** usage on a tiny OLED screen next to your PC.

An ESP32 with a 0.96-inch 128×64 I²C OLED displays the remaining percentage and the time until reset for the five-hour and weekly limits of both tools. A small Python bridge on Windows reads the local cache written by [Claude Code Usage Monitor](https://github.com/CodeZeno/Claude-Code-Usage-Monitor) and sends only those values to the ESP32 over the USB cable. No Wi-Fi is needed.

## What you need

- ESP32 dev board (DevKit V1 / 38-pin NodeMCU ESP-32S style) and a USB data cable
- 0.96-inch 128×64 I²C OLED (SSD1306, 4 pins: GND, VDD, SCK/SCL, SDA)
- Breadboard and four male-to-female Dupont jumper wires
- Windows with [Claude Code Usage Monitor](https://github.com/CodeZeno/Claude-Code-Usage-Monitor) running, Claude Code and Codex enabled
- [Arduino IDE 2](https://www.arduino.cc/en/software) and [Python 3](https://www.python.org/downloads/)

## Wiring

Push the OLED's four pins into four separate breadboard rows. Then use one male-to-female jumper per pin: the female end goes onto the ESP32 pin, the male end goes into the same breadboard row as the OLED pin.

| OLED pin | ESP32 pin |
| --- | --- |
| GND | GND |
| VDD | 3V3 |
| SDA | GPIO 21 (labeled `D21` or `P21`) |
| SCK / SCL | GPIO 22 (labeled `D22` or `P22`) |

Use **3V3**, not VIN/5V. The USB cable powers both boards.

On the 38-pin NodeMCU ESP-32S board the labels are printed on the underside. With the labels facing you and the USB port at the bottom: `3V3` is the top pin of the right column; `GND`, `P22` and `P21` are the 1st, 3rd and 6th pins from the top of the left column.

## Upload the firmware

1. Open Arduino IDE.
2. Install the ESP32 boards if needed: **Tools → Board → Boards Manager**, search `esp32` by Espressif Systems, install.
3. Install the display library: **Tools → Manage Libraries**, search `U8g2` by oliver, install.
4. Open `firmware/UsageDisplay/UsageDisplay.ino`.
5. Plug in the ESP32. Select **Tools → Board → esp32 → ESP32 Dev Module** and the ESP32's COM port under **Tools → Port**.
6. Click **Upload** (the right-arrow button). If the upload hangs at `Connecting...`, hold the ESP32's **BOOT** button until it starts writing.

The screen should show `Waiting for Windows`.

## Find the COM port

Open **Device Manager** (right-click the Start button) and expand **Ports (COM & LPT)**. The ESP32 usually appears as `Silicon Labs CP210x ... (COM5)` or `USB-SERIAL CH340 (COM5)`. Unplug and replug it to see which entry disappears and returns. If nothing appears, install the CP210x or CH340 driver, or try another USB cable (some cables only charge).

## Run the bridge

In PowerShell, from this project folder (replace `COM5` with your port):

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r bridge\requirements.txt
.\.venv\Scripts\python bridge\bridge.py --port COM5
```

The first two commands are only needed once. Close Arduino IDE's Serial Monitor first; only one program can use the COM port at a time. Press `Ctrl+C` to stop the bridge.

## Reading the screen

```text
CLAUDE 5h 82% 03:12
CLAUDE wk 64% 4d07h
--------------------
CODEX 5h -- --
CODEX wk 91% 6d02h
```

- The percentage is what **remains** of each limit.
- The timer is the time until that limit resets: `hh:mm`, or days and hours.
- `--` means the monitor has no reading for that window. Nothing is estimated.
- `*` in the top-right corner means the monitor's last refresh failed, so values may be old.
- `No usage cache found` means the monitor's cache file is missing or unreadable.

## Privacy

The bridge reads `%APPDATA%\ClaudeCodeUsageMonitor\usage-cache.json` and uses only the Claude Code and Codex five-hour and weekly usage entries. It never reads login files, and it never sends account names, IDs, tokens or credentials. Data travels only over the local USB cable.

## Troubleshooting

- **Blank screen:** check that VDD is on 3V3 and GND on GND, and that SDA/SCL are not swapped. The sketch expects I²C address `0x3C`.
- **Bridge cannot open the port:** close the Serial Monitor and check the port number in Device Manager.

## Credits

Usage data comes from [Claude Code Usage Monitor](https://github.com/CodeZeno/Claude-Code-Usage-Monitor) by Code Zeno (MIT License). This project does not include its code. The display uses the [U8g2](https://github.com/olikraus/u8g2) library.
