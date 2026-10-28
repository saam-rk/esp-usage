# AGENTS.md

Rules for anyone (human or AI agent) working on this project. Follow them.

## Goal

Show the remaining usage and the time until reset for the **five-hour** and **weekly** limits of **Claude Code** and **Codex** on a 0.96-inch 128×64 I²C OLED driven by an ESP32 dev board.

This is a small, personal project maintained by one person. Keep it simple, readable and easy to change. It is public open source under the MIT License, so everything must be in English and safe to publish.

## Folder structure

```text
AGENTS.md                 Project rules (this file)
README.md                 What the project is and how to build and run it
LICENSE                   MIT License, copyright saam-rk
PROGRESS.md               Local session notes (ignored by Git)
start-bridge.bat          Double-click launcher: sets up .venv and runs the bridge
bridge/bridge.py          Windows bridge: reads the monitor cache, sends values over USB serial
bridge/requirements.txt   Python dependencies for the bridge
firmware/UsageDisplay/    Arduino sketch for the ESP32 and OLED
```

## Communication

- The maintainer is a beginner. Use clear, simple English and explain unfamiliar terms.
- Explain each step. Keep technical instructions short and concrete.
- Before asking the maintainer to connect or power anything, give precise physical wiring instructions: which pin, which wire, which breadboard row.
- When wiring changes, ask for a photo and check it before the board is connected to USB. If pins or rows are unclear, ask for a closer photo.

## Hardware and wiring

- ESP32 dev board, 38-pin NodeMCU ESP-32S style (sold as "DevKit V1"), CP2102 USB chip, USB-C. Pin labels (`3V3`, `GND`, `P21`, `P22`, ...) are printed only on the underside. Arduino board: "ESP32 Dev Module".
- Blue 0.96-inch 128×64 I²C OLED, pin order `GND VDD SCK SDA` (SSD1306-compatible, address `0x3C`), MB-102 breadboard, Dupont jumpers.
- The OLED sits in four separate breadboard rows. One male-to-female jumper per connection: female end on the ESP32 pin, male end in the OLED pin's row.

| OLED pin | ESP32 pin |
| --- | --- |
| GND | GND |
| VDD | 3V3 (never 5V/VIN) |
| SDA | GPIO 21 (`P21`) |
| SCK / SCL | GPIO 22 (`P22`) |

No sensors or buttons are used.

## Architecture

- [Claude Code Usage Monitor](https://github.com/CodeZeno/Claude-Code-Usage-Monitor) runs on Windows and writes `%APPDATA%\ClaudeCodeUsageMonitor\usage-cache.json`.
- `bridge/bridge.py` reads that cache, extracts only the needed usage values and sends one short text line per second to the ESP32 over USB serial (115200 baud). No Wi-Fi. It auto-detects the port by USB vendor ID (CP210x, CH340) and reconnects after unplugging.
- The firmware shows "connection lost" after 5 seconds without a valid line.
- Serial line format: `c5_left,c5_reset_s,cw_left,cw_reset_s,x5_left,x5_reset_s,xw_left,xw_reset_s,stale`. `-1` means "not available" (shown as `--`); all `-2` means "cache missing or invalid".
- In the cache, `percentage` is the **used** percentage; remaining = 100 − used. `percentage: null` or `available: false` means the window has no reading.

## Privacy and data honesty (must never be broken)

- The bridge may access only `poll_ok`, `data.claude_code.session`, `data.claude_code.weekly`, `data.codex.session` and `data.codex.weekly`.
- Never read, log or transmit credentials, tokens, account IDs, profile names, credential paths or account records (for example `data.accounts` in the cache, or any provider login file).
- Never invent, estimate or hard-code limits or readings. If the source does not report a value, show `--`.
- Never commit `.env` files, secrets or real cache files.

## Git workflow

- Remote: public GitHub repository `saam-rk/esp-usage`. Everything pushed is visible to anyone.
- Commit as `saam-rk <191466689+saam-rk@users.noreply.github.com>` (set in this repo's local Git config). Never commit with a personal email address.
- Routine work goes on the current branch (normally `main`) in small, frequent commits. Push after each commit.
- Commit messages: English, imperative, with a prefix: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`. No AI attribution.
- Use a separate branch and a pull request only when the maintainer asks or when a large or risky change clearly benefits from review. Give the maintainer the PR link. Never merge a PR unless asked.
- Never force-push, rewrite history or delete branches without explicit permission.

## Dependencies, docs and verification

- Add dependencies only when needed, and pin a compatible range (see `bridge/requirements.txt`). Firmware uses the Arduino ESP32 core and the U8g2 library.
- Keep `README.md` up to date when setup, wiring or behavior changes. Preserve license and attribution notices for any reused code.
- Keep `.gitignore` covering secrets, `.env` files, virtual environments, Python caches, build output and `PROGRESS.md`. `AGENTS.md` stays tracked.
- Verify changes in proportion to their risk: compile the sketch after firmware changes, run the bridge's parsing against a sample or the real cache after bridge changes, and check the physical screen for display changes. Never claim something was tested when it was not.

## Session notes

- Read `PROGRESS.md` at the start of every session.
- Update it as work progresses: what is done, what is next, decisions and open problems. Keep it short.
- `PROGRESS.md` is ignored by Git and must never be committed.
