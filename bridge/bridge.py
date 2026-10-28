"""Forward sanitized Claude/Codex usage cache values to an ESP32 over USB."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import serial
from serial.tools import list_ports

# USB vendor IDs of the USB-to-serial chips used on common ESP32 boards.
ESP32_USB_VENDORS = {
    0x10C4: "Silicon Labs CP210x",
    0x1A86: "WCH CH340/CH9102",
}
RETRY_SECONDS = 2.0


def cache_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise RuntimeError("APPDATA is not set; run this bridge on Windows.")
    return Path(appdata) / "ClaudeCodeUsageMonitor" / "usage-cache.json"


def epoch_seconds(value: object) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, dict):
        seconds = value.get("secs_since_epoch")
        nanos = value.get("nanos_since_epoch", 0)
        if isinstance(seconds, (int, float)) and isinstance(nanos, (int, float)):
            return int(seconds + nanos / 1_000_000_000)
    return None


def window_values(provider: object, key: str, now: int) -> tuple[int, int, bool]:
    if not isinstance(provider, dict):
        return -1, -1, False
    window = provider.get(key)
    if not isinstance(window, dict) or window.get("available") is False:
        return -1, -1, bool(provider.get("stale"))
    percentage = window.get("percentage")
    if not isinstance(percentage, (int, float)):
        return -1, -1, bool(provider.get("stale"))
    remaining = max(0, min(100, round(100 - percentage)))
    reset = epoch_seconds(window.get("resets_at"))
    reset_in = max(0, reset - now) if reset is not None else -1
    return remaining, reset_in, bool(provider.get("stale"))


def read_payload(path: Path, now: int | None = None) -> str:
    now = int(time.time()) if now is None else now
    try:
        cache = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "-2,-2,-2,-2,-2,-2,-2,-2,-2\n"
    if not isinstance(cache, dict) or not isinstance(cache.get("data"), dict):
        return "-2,-2,-2,-2,-2,-2,-2,-2,-2\n"

    data = cache["data"]
    claude = data.get("claude_code")
    codex = data.get("codex")
    c5 = window_values(claude, "session", now)
    cw = window_values(claude, "weekly", now)
    x5 = window_values(codex, "session", now)
    xw = window_values(codex, "weekly", now)
    stale = any(item[2] for item in (c5, cw, x5, xw)) or not cache.get("poll_ok", False)
    values = [c5[0], c5[1], cw[0], cw[1], x5[0], x5[1], xw[0], xw[1], int(stale)]
    return ",".join(str(value) for value in values) + "\n"


def find_esp32_ports() -> list[str]:
    return sorted(p.device for p in list_ports.comports() if p.vid in ESP32_USB_VENDORS)


def port_is_busy(exc: Exception) -> bool:
    message = str(exc)
    return any(text in message for text in ("PermissionError", "Access is denied"))


class Status:
    """Print a status message only when it changes, so retries do not flood the window."""

    def __init__(self) -> None:
        self.last = ""

    def show(self, message: str) -> None:
        if message != self.last:
            print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)
            self.last = message


def pick_port(requested: str | None, status: Status) -> str | None:
    if requested:
        return requested
    ports = find_esp32_ports()
    if len(ports) == 1:
        return ports[0]
    if ports:
        status.show(
            f"Found several possible ESP32 boards: {', '.join(ports)}. "
            f"Unplug the extra ones, or start with: start-bridge.bat {ports[0]}"
        )
    else:
        status.show("Waiting for the ESP32. Plug it into this PC with a USB data cable.")
    return None


def send_forever(port_name: str, path: Path, interval: float, status: Status) -> None:
    with serial.Serial(port_name, 115200, timeout=1, write_timeout=1) as port:
        time.sleep(2.0)  # Allow the ESP32 to reboot after opening its serial port.
        while True:
            if path.exists():
                status.show(f"Connected to the ESP32 on {port_name}. The display is updating.")
            else:
                status.show("Usage cache not found. Is Claude Code Usage Monitor running?")
            port.write(read_payload(path).encode("ascii"))
            port.flush()
            time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Send usage-cache readings to the ESP32 OLED.")
    parser.add_argument(
        "port", nargs="?", help="ESP32 serial port, for example COM5 (found automatically if omitted)"
    )
    parser.add_argument("--port", dest="port_option", metavar="PORT", help="same as the positional port")
    parser.add_argument("--interval", type=float, default=1.0, help="Serial update interval in seconds")
    args = parser.parse_args()
    requested = args.port_option or args.port
    interval = max(0.25, args.interval)
    try:
        path = cache_path()
    except RuntimeError as exc:
        print(f"Bridge error: {exc}", file=sys.stderr)
        return 1

    status = Status()
    print("esp-usage bridge: sends your Claude Code and Codex usage to the ESP32 display.")
    print("Leave this window open. Close it to stop the display updates.\n")
    try:
        while True:
            port_name = pick_port(requested, status)
            if port_name is not None:
                try:
                    send_forever(port_name, path, interval, status)
                except (serial.SerialException, OSError) as exc:
                    if port_is_busy(exc):
                        status.show(
                            f"{port_name} is busy. Close Arduino IDE's Serial Monitor "
                            "or other bridge windows."
                        )
                    elif requested:
                        status.show(f"Cannot use {port_name}. Is the ESP32 plugged in on that port?")
                    else:
                        status.show("Lost the ESP32. Waiting for it to come back...")
            time.sleep(RETRY_SECONDS)
    except KeyboardInterrupt:
        print("\nBridge stopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
