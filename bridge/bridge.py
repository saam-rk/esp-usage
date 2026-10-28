"""Forward sanitized Claude/Codex usage cache values to an ESP32 over USB."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import serial


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Send usage-cache readings to the ESP32 OLED.")
    parser.add_argument("--port", required=True, help="ESP32 serial port, for example COM5")
    parser.add_argument("--interval", type=float, default=1.0, help="Serial update interval in seconds")
    args = parser.parse_args()
    path = cache_path()
    try:
        with serial.Serial(args.port, 115200, timeout=1, write_timeout=1) as port:
            print(f"Reading {path} and sending display data to {args.port}. Press Ctrl+C to stop.")
            time.sleep(2.0)  # Allow the ESP32 to reboot after opening its serial port.
            while True:
                port.write(read_payload(path).encode("ascii"))
                port.flush()
                time.sleep(max(0.25, args.interval))
    except KeyboardInterrupt:
        return 0
    except (OSError, serial.SerialException, RuntimeError) as exc:
        print(f"Bridge error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
