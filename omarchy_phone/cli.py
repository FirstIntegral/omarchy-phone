"""Command line for omarchy-phone."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence

from omarchy_phone import __version__
from omarchy_phone.adb import (
    Device,
    DeviceChoiceError,
    choose_device,
    connect_candidates,
    fallback_wm,
    parse_devices,
    parse_mdns,
    parse_wm_size,
    ready_devices,
)
from omarchy_phone.config import load_last, save_last
from omarchy_phone.launch import Options, desk_command, camera_command, mirror_command, scrcpy_env

Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
Exec = Callable[[Sequence[str], Mapping[str, str]], int]

PACMAN = "sudo pacman -S --needed scrcpy android-tools android-udev"

SETUP = f"""
No phone ready.

On the Galaxy S24 Ultra:
  1. Settings → About phone → Software information. Tap Build number 7 times.
  2. Settings → Developer options. Turn on USB debugging.
  3. Plug in. Unlock the phone. Tap Allow, and check Always allow from this computer.

Wireless, same Wi-Fi, cable unplugged:
  Developer options → Wireless debugging → Pair device with pairing code.
  The pairing port and the connect port are different.
    omarchy-phone pair IP:PAIRPORT CODE
    omarchy-phone connect IP:CONNECTPORT
  omarchy-phone mdns lists both. After one successful connect, plain
  omarchy-phone tries that address again, then a single mDNS hit.

This computer needs the Arch packages (once):
  {PACMAN}
Then unplug and replug. Banking apps and Secure Folder stay black. That is Android,
not this program.
""".strip()


def main(
    argv: Sequence[str] | None = None,
    *,
    environ: dict[str, str] | None = None,
    adb_runner: Runner | None = None,
    scrcpy_exec: Exec | None = None,
    stderr: object | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or (args[0].startswith("-") and args[0] not in {"-h", "--help", "--version"}):
        args = ["mirror", *args]
    parser = _parser()
    try:
        ns = parser.parse_args(args)
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else 2

    env = dict(os.environ if environ is None else environ)
    err = sys.stderr if stderr is None else stderr
    adb = adb_runner or _subprocess_runner()
    launch = scrcpy_exec or _exec

    try:
        if ns.cmd == "doctor":
            return _doctor(adb, env, err)
        if ns.cmd == "devices":
            return _devices(adb, err)
        if ns.cmd == "mdns":
            return _mdns(adb, err)
        if ns.cmd == "pair":
            return _adb_passthrough(adb, ["adb", "pair", ns.hostport, ns.code], err)
        if ns.cmd == "connect":
            code = _adb_passthrough(adb, ["adb", "connect", ns.hostport], err)
            if code == 0:
                save_last(env, ns.hostport)
            return code
        if ns.cmd == "disconnect":
            cmd = ["adb", "disconnect"] if not ns.hostport else ["adb", "disconnect", ns.hostport]
            return _adb_passthrough(adb, cmd, err)
        if ns.cmd == "apps":
            return _apps(ns, adb, env, launch, err)
        return _open(ns, adb, env, launch, err)
    except DeviceChoiceError as exc:
        _fail(str(exc) + "\n\n" + SETUP, env, err)
        return 2
    except ValueError as exc:
        _fail(str(exc), env, err)
        return 2
    except MissingTool as exc:
        _fail(f"{exc}\n\n{PACMAN}", env, err)
        return 127


class MissingTool(Exception):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="omarchy-phone",
        description="Show a real Android phone in an Omarchy window and use it.",
    )
    parser.add_argument("--version", action="version", version=f"omarchy-phone {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    mirror = sub.add_parser("mirror", help="mirror the phone panel (default)")
    _add_common(mirror)
    mirror.add_argument("--screen-off", action="store_true", help="turn the phone panel off while the window is open")

    desk = sub.add_parser("desk", help="second Android screen, physical panel stays as it is")
    _add_common(desk)
    desk.add_argument("--app", help="Android package to open on the virtual display")
    desk.add_argument("--fixed", action="store_true", help="do not resize Android when the window is resized")

    camera = sub.add_parser("camera", help="use the phone camera in a window")
    _add_common(camera)
    camera.add_argument("--front", action="store_true")

    tcpip = sub.add_parser("tcpip", help="switch a USB phone to wireless adb and mirror it")
    _add_common(tcpip)
    tcpip.add_argument("address", nargs="?", help="optional ip or ip:port, default port 5555")
    tcpip.add_argument("--screen-off", action="store_true")

    sub.add_parser("devices", help="list adb devices")
    sub.add_parser("mdns", help="list wireless debugging services")
    sub.add_parser("doctor", help="check adb, scrcpy, and whether a phone is ready")

    pair = sub.add_parser("pair", help="pair wireless debugging")
    pair.add_argument("hostport")
    pair.add_argument("code")

    connect = sub.add_parser("connect", help="adb connect to a wireless debugging port")
    connect.add_argument("hostport")

    disconnect = sub.add_parser("disconnect", help="adb disconnect")
    disconnect.add_argument("hostport", nargs="?")

    apps = sub.add_parser("apps", help="list packages scrcpy can start")
    apps.add_argument("--serial")
    apps.add_argument("--wifi", action="store_true")
    apps.add_argument("--no-reconnect", action="store_true")
    return parser


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--serial")
    parser.add_argument("--wifi", action="store_true", help="prefer Wi-Fi when USB is also connected")
    parser.add_argument("--no-audio", action="store_true")
    parser.add_argument("--audio-dup", action="store_true", help="keep audio playing on the phone too")
    parser.add_argument("--fps", type=int)
    parser.add_argument("--max-size", type=int)
    parser.add_argument("--bit-rate")
    parser.add_argument("--codec", choices=("h264", "h265", "av1"))
    parser.add_argument("--dry-run", action="store_true", help="print the scrcpy command and exit")
    parser.add_argument("--no-reconnect", action="store_true", help="do not try a saved address or mDNS")


def _open(ns: argparse.Namespace, adb: Runner, env: dict[str, str], launch: Exec, err: object) -> int:
    _require("adb", adb_injected=_injected(adb))
    options = _options(ns)
    serial, transport, wm = _target(ns, adb, env)
    if ns.cmd == "tcpip":
        options = _with_tcpip(options, ns.address or "")
        # scrcpy --tcpip picks the USB device itself. Do not also pass --serial.
        serial = None
        transport = "tcp"
    if ns.cmd == "desk":
        built = desk_command(serial, transport, options)
    elif ns.cmd == "camera":
        built = camera_command(serial, options)
    else:
        built = mirror_command(serial, transport, wm, options)

    child_env = scrcpy_env(env, built.app_id)
    if ns.dry_run:
        _write(err, _format_launch(built.command, child_env, env) + "\n")
        return 0
    if serial and transport == "tcp":
        save_last(env, serial)
    _require_scrcpy(env)
    return launch(built.command, child_env)


def _target(
    ns: argparse.Namespace,
    adb: Runner,
    env: dict[str, str],
) -> tuple[str | None, str, tuple[int, int]]:
    if ns.cmd == "tcpip" and ns.address:
        return None, "tcp", _wm_if_listed(adb)
    device = _select(ns, adb, env)
    if ns.cmd == "tcpip" and device.transport != "usb":
        raise DeviceChoiceError(
            "switching to wireless needs the USB cable. Or pass an address: omarchy-phone tcpip IP"
        )
    if device.transport == "tcp" and ns.cmd != "tcpip" and not ns.dry_run:
        save_last(env, device.serial)
    return device.serial, device.transport, _wm(adb, device)


def _wm_if_listed(adb: Runner) -> tuple[int, int]:
    devices = ready_devices(_device_list(adb))
    if len(devices) == 1:
        return _wm(adb, devices[0])
    return fallback_wm("")


def _with_tcpip(options: Options, tcpip: str) -> Options:
    return Options(
        screen_off=options.screen_off,
        no_audio=options.no_audio,
        audio_dup=options.audio_dup,
        fps=options.fps,
        max_size=options.max_size,
        bit_rate=options.bit_rate,
        codec=options.codec,
        app=options.app,
        flex=options.flex,
        front=options.front,
        tcpip=tcpip,
    )


def _apps(ns: argparse.Namespace, adb: Runner, env: dict[str, str], launch: Exec, err: object) -> int:
    del err
    _require("adb", adb_injected=_injected(adb))
    device = _select(ns, adb, env)
    _require_scrcpy(env)
    return launch(["scrcpy", "--serial", device.serial, "--list-apps"], env)


def _require_scrcpy(env: Mapping[str, str]) -> None:
    if env.get("OMARCHY_PHONE_ASSUME_SCRCPY") == "1":
        return
    if shutil.which("scrcpy") is None:
        raise MissingTool("scrcpy is not installed")


def _select(ns: argparse.Namespace, adb: Runner, env: dict[str, str]) -> Device:
    devices = _device_list(adb)
    if not ready_devices(devices) and not getattr(ns, "no_reconnect", False):
        for address in connect_candidates(load_last(env), _mdns_services(adb)):
            adb(["adb", "connect", address])
        devices = _device_list(adb)
    return choose_device(devices, serial=ns.serial, prefer_tcp=bool(ns.wifi))


def _device_list(adb: Runner) -> list[Device]:
    adb(["adb", "start-server"])
    result = adb(["adb", "devices", "-l"])
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "adb devices failed").strip()
        raise DeviceChoiceError(detail)
    return parse_devices(result.stdout)


def _mdns_services(adb: Runner):
    result = adb(["adb", "mdns", "services"])
    if result.returncode != 0:
        return []
    return parse_mdns(result.stdout)


def _wm(adb: Runner, device: Device | None) -> tuple[int, int]:
    if device is None:
        return fallback_wm("")
    result = adb(["adb", "-s", device.serial, "shell", "wm", "size"])
    if result.returncode == 0:
        parsed = parse_wm_size(result.stdout)
        if parsed:
            return parsed
    return fallback_wm(device.model)


def _options(ns: argparse.Namespace) -> Options:
    return Options(
        screen_off=bool(getattr(ns, "screen_off", False)),
        no_audio=bool(ns.no_audio),
        audio_dup=bool(ns.audio_dup),
        fps=ns.fps,
        max_size=ns.max_size,
        bit_rate=ns.bit_rate,
        codec=ns.codec,
        app=getattr(ns, "app", None),
        flex=not bool(getattr(ns, "fixed", False)),
        front=bool(getattr(ns, "front", False)),
    )


def _doctor(adb: Runner, env: dict[str, str], err: object) -> int:
    missing = [name for name in ("adb", "scrcpy") if shutil.which(name) is None]
    for name in ("adb", "scrcpy"):
        path = shutil.which(name)
        _write(err, f"{name}: {path or 'missing'}\n")
    if not missing and shutil.which("adb"):
        result = adb(["adb", "version"])
        _write(err, (result.stdout or result.stderr or "").strip() + "\n")
        try:
            devices = _device_list(adb)
        except DeviceChoiceError as exc:
            _write(err, str(exc) + "\n")
        else:
            if devices:
                for device in devices:
                    _write(err, f"{device.serial}  {device.state}  {device.transport}  {device.model}\n")
            else:
                _write(err, "no phone listed\n")
            services = _mdns_services(adb)
            for service in services:
                _write(err, f"mdns {service.kind}  {service.address}\n")
    session = env.get("XDG_SESSION_TYPE") or env.get("WAYLAND_DISPLAY") or "unknown"
    _write(err, f"session: {session}\n")
    if missing:
        _write(err, PACMAN + "\n")
        return 127
    return 0


def _devices(adb: Runner, err: object) -> int:
    _require("adb", adb_injected=_injected(adb))
    for device in _device_list(adb):
        _write(err, f"{device.serial}\t{device.state}\t{device.transport}\t{device.model}\n")
    return 0


def _mdns(adb: Runner, err: object) -> int:
    _require("adb", adb_injected=_injected(adb))
    result = adb(["adb", "mdns", "services"])
    _write(err, result.stdout or "")
    if result.stderr:
        _write(err, result.stderr)
    return result.returncode


def _adb_passthrough(adb: Runner, cmd: list[str], err: object) -> int:
    _require("adb", adb_injected=_injected(adb))
    if cmd[1] in {"pair", "connect"} and not _hostport_ok(cmd[2]):
        raise ValueError(f"{cmd[2]} is not host:port")
    result = adb(cmd)
    if result.stdout:
        _write(err, result.stdout if result.stdout.endswith("\n") else result.stdout + "\n")
    if result.stderr:
        _write(err, result.stderr if result.stderr.endswith("\n") else result.stderr + "\n")
    if cmd[1] == "connect" and _connect_succeeded(result.stdout or ""):
        return 0
    if cmd[1] == "connect" and result.returncode == 0 and not _connect_succeeded(result.stdout or ""):
        return result.returncode or 1
    return result.returncode


def _hostport_ok(value: str) -> bool:
    host, sep, port = value.rpartition(":")
    return bool(sep and host and port.isdigit() and 0 < int(port) < 65536)


def _connect_succeeded(text: str) -> bool:
    lowered = text.lower()
    return "connected to" in lowered and "failed" not in lowered and "cannot" not in lowered


def _require(name: str, *, adb_injected: bool) -> None:
    if adb_injected:
        return
    if shutil.which(name) is None:
        raise MissingTool(f"{name} is not installed")


def _injected(adb: Runner) -> bool:
    return not isinstance(adb, _DefaultRunner)


class _DefaultRunner:
    def __call__(self, cmd: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(list(cmd), text=True, capture_output=True)


def _subprocess_runner() -> Runner:
    return _DefaultRunner()


def _exec(cmd: Sequence[str], env: Mapping[str, str]) -> int:
    os.execvpe(cmd[0], list(cmd), dict(env))
    return 127


def _format_launch(cmd: Sequence[str], env: Mapping[str, str], base: Mapping[str, str]) -> str:
    lines = []
    for key in ("SDL_APP_ID", "SDL_APP_NAME", "SDL_VIDEODRIVER"):
        if env.get(key) and env.get(key) != base.get(key):
            lines.append(f"{key}={env[key]}")
    lines.append(shlex.join(cmd))
    return "\n".join(lines)


def _fail(message: str, env: Mapping[str, str], err: object) -> None:
    _write(err, message.rstrip() + "\n")
    if env.get("OMARCHY_PHONE_NO_NOTIFY") == "1":
        return
    if _isatty(err):
        return
    headline = message.strip().splitlines()[0]
    _notify(headline)


def _notify(headline: str) -> None:
    if shutil.which("omarchy-notification-send"):
        subprocess.run(
            [
                "omarchy-notification-send",
                "--app-name",
                "Omarchy Phone",
                "-u",
                "normal",
                "Omarchy Phone",
                headline,
            ],
            check=False,
        )
        return
    if shutil.which("notify-send"):
        subprocess.run(["notify-send", "-a", "Omarchy Phone", "Omarchy Phone", headline], check=False)


def _isatty(err: object) -> bool:
    isatty = getattr(err, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except (OSError, ValueError):
        return False


def _write(err: object, text: str) -> None:
    write = getattr(err, "write", None)
    if not callable(write):
        return
    write(text)
