"""scrcpy command lines. Pure: no adb, no display server."""

from __future__ import annotations

import re
from dataclasses import dataclass

_BIT_RATE = re.compile(r"\d+[KMG]?")
MIRROR_SHORT = 432


@dataclass(frozen=True)
class Stream:
    max_size: int
    max_fps: int
    bit_rate: str
    codec: str


USB_STREAM = Stream(1440, 60, "16M", "h264")
TCP_STREAM = Stream(1080, 60, "8M", "h264")
DESK_BIT_RATE_USB = "16M"
DESK_BIT_RATE_TCP = "8M"


@dataclass(frozen=True)
class Options:
    screen_off: bool = False
    no_audio: bool = False
    audio_dup: bool = False
    fps: int | None = None
    max_size: int | None = None
    bit_rate: str | None = None
    codec: str | None = None
    app: str | None = None
    flex: bool = True
    front: bool = False
    tcpip: str | None = None


@dataclass(frozen=True)
class Launch:
    command: list[str]
    app_id: str


def phone_window(width: int, height: int, short: int = MIRROR_SHORT) -> tuple[int, int]:
    if width <= 0 or height <= 0:
        raise ValueError("display size must be positive")
    if height >= width:
        w, h = short, int(round(short * height / width))
    else:
        h, w = short, int(round(short * width / height))
    return _even(w), _even(h)


def stream_for(transport: str) -> Stream:
    return TCP_STREAM if transport == "tcp" else USB_STREAM


def mirror_command(
    serial: str | None,
    transport: str,
    wm: tuple[int, int],
    options: Options,
) -> Launch:
    _check(options)
    width, height = phone_window(*wm)
    stream = stream_for(transport)
    cmd = _chrome(serial, "Omarchy Phone", width, height, options, stream.max_fps, stream.bit_rate)
    cmd.append(f"--max-size={options.max_size or stream.max_size}")
    if options.screen_off:
        cmd.append("--turn-screen-off")
    _append_tcpip(cmd, options.tcpip)
    return Launch(cmd, "scrcpy")


def desk_command(serial: str | None, transport: str, options: Options) -> Launch:
    _check(options)
    bit_rate = DESK_BIT_RATE_TCP if transport == "tcp" else DESK_BIT_RATE_USB
    cmd = _chrome(serial, "Omarchy Phone Desk", 1280, 800, options, 60, bit_rate)
    cmd.append("--new-display=1920x1200/240")
    if options.flex:
        cmd.append("--flex-display")
    cmd.append("--display-ime-policy=local")
    if options.app:
        cmd.append(f"--start-app={options.app}")
    return Launch(cmd, "scrcpy-desk")


def camera_command(serial: str | None, options: Options) -> Launch:
    _check(options)
    facing = "front" if options.front else "back"
    cmd = _chrome(serial, "Omarchy Phone Camera", 960, 540, options, 60, "8M")
    cmd += [
        "--video-source=camera",
        f"--camera-facing={facing}",
        "--camera-size=1920x1080",
    ]
    if not options.no_audio:
        cmd.append("--audio-source=mic")
    return Launch(cmd, "scrcpy-camera")


def scrcpy_env(base: dict[str, str], app_id: str) -> dict[str, str]:
    env = dict(base)
    env["SDL_APP_ID"] = app_id
    env["SDL_APP_NAME"] = "Omarchy Phone"
    if base.get("WAYLAND_DISPLAY") and not base.get("SDL_VIDEODRIVER"):
        env["SDL_VIDEODRIVER"] = "wayland"
    return env


def _chrome(
    serial: str | None,
    title: str,
    width: int,
    height: int,
    options: Options,
    fps: int,
    bit_rate: str,
) -> list[str]:
    cmd = ["scrcpy"]
    if serial and options.tcpip is None:
        cmd += ["--serial", serial]
    codec = options.codec or "h264"
    rate = options.bit_rate or bit_rate
    cmd += [
        "--window-title",
        title,
        "--window-borderless",
        f"--window-width={width}",
        f"--window-height={height}",
        "--keyboard=uhid",
        "--shortcut-mod=lalt",
        "--keep-active",
        "--stay-awake",
        f"--max-fps={options.fps or fps}",
        f"--video-bit-rate={rate}",
        f"--video-codec={codec}",
    ]
    cmd += _audio(options)
    return cmd


def _audio(options: Options) -> list[str]:
    if options.no_audio:
        return ["--no-audio"]
    if options.audio_dup:
        return ["--audio-dup"]
    return []


def _append_tcpip(cmd: list[str], tcpip: str | None) -> None:
    if tcpip is None:
        return
    if tcpip == "":
        cmd.append("--tcpip")
    else:
        cmd.append(f"--tcpip={tcpip}")


def _check(options: Options) -> None:
    if options.no_audio and options.audio_dup:
        raise ValueError("pass only one of --no-audio and --audio-dup")
    if options.fps is not None and options.fps < 1:
        raise ValueError("--fps must be at least 1")
    if options.max_size is not None and options.max_size < 1:
        raise ValueError("--max-size must be at least 1")
    if options.bit_rate is not None and not _BIT_RATE.fullmatch(options.bit_rate):
        raise ValueError("--bit-rate looks like 8M or 8000000")
    if options.app is not None and not re.fullmatch(r"[A-Za-z0-9_.]+", options.app):
        raise ValueError("--app must be an Android package name")


def _even(value: int) -> int:
    return value if value % 2 == 0 else value + 1


