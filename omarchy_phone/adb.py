"""Parse adb output and pick a phone. No subprocesses here."""

from __future__ import annotations

from dataclasses import dataclass


class DeviceChoiceError(Exception):
    """The phone list cannot be turned into one scrcpy target."""


@dataclass(frozen=True)
class Device:
    serial: str
    state: str
    model: str
    transport: str
    raw: str


@dataclass(frozen=True)
class MdnsService:
    name: str
    kind: str
    address: str


def parse_devices(text: str) -> list[Device]:
    devices: list[Device] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("List of") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        serial, state = parts[0], parts[1]
        model = ""
        transport = "unknown"
        for part in parts[2:]:
            if part.startswith("model:"):
                model = part.split(":", 1)[1]
            elif part.startswith("usb:"):
                transport = "usb"
        if transport == "unknown":
            if serial.startswith("emulator-"):
                transport = "emulator"
            elif _is_hostport(serial):
                transport = "tcp"
        devices.append(Device(serial, state, model, transport, line))
    return devices


def parse_wm_size(text: str) -> tuple[int, int] | None:
    physical = _size_after(text, "Physical size:")
    if physical:
        return physical
    return _size_after(text, "Override size:")


def parse_mdns(text: str) -> list[MdnsService]:
    services: list[MdnsService] = []
    for raw_line in text.splitlines():
        parts = raw_line.split()
        if len(parts) < 3:
            continue
        type_field = parts[1]
        if "_adb-tls-connect._tcp" in type_field:
            kind = "connect"
        elif "_adb-tls-pairing._tcp" in type_field:
            kind = "pairing"
        else:
            continue
        if not _is_hostport(parts[2]):
            continue
        services.append(MdnsService(parts[0], kind, parts[2]))
    return services


def ready_devices(devices: list[Device]) -> list[Device]:
    return [d for d in devices if d.state == "device" and d.transport != "emulator"]


def choose_device(
    devices: list[Device],
    *,
    serial: str | None = None,
    prefer_tcp: bool = False,
) -> Device:
    if serial:
        for device in devices:
            if device.serial == serial:
                if device.state != "device":
                    raise DeviceChoiceError(
                        f"{serial} is {device.state}. Unlock the phone and accept the USB debugging prompt."
                    )
                return device
        raise DeviceChoiceError(f"no device with serial {serial}")

    ok = ready_devices(devices)
    if not ok:
        if any(d.state == "unauthorized" for d in devices):
            raise DeviceChoiceError(
                "phone is plugged in but USB debugging is not allowed yet. "
                "Unlock the S24, tap Allow, and check Always allow from this computer."
            )
        if any("permission" in d.state for d in devices):
            raise DeviceChoiceError(
                "adb sees the phone and cannot open it. Install android-udev, replug, "
                "and if it still says no permissions, log out and back in."
            )
        raise DeviceChoiceError("no phone connected")

    if len(ok) == 1:
        return ok[0]

    # adb often lists one phone twice: the ip:port and the mDNS service name.
    concrete = [d for d in ok if not _is_mdns_serial(d.serial)]
    pool = concrete or ok
    if len(pool) == 1:
        return pool[0]

    usb = [d for d in pool if d.transport == "usb"]
    tcp = [d for d in pool if d.transport == "tcp"]
    if not prefer_tcp and len(usb) == 1:
        return usb[0]
    if prefer_tcp and len(tcp) == 1:
        return tcp[0]

    lines = "\n".join(f"  {d.serial}  {d.transport}  {d.model}" for d in pool)
    raise DeviceChoiceError(f"more than one phone. Pass --serial.\n{lines}")


def connect_candidates(last: str | None, services: list[MdnsService]) -> list[str]:
    """Addresses worth an `adb connect`, in order. Never guess among several mDNS hits."""
    out: list[str] = []
    if last and _is_hostport(last):
        out.append(last)
    connects = [s.address for s in services if s.kind == "connect"]
    if len(connects) == 1 and connects[0] not in out:
        out.append(connects[0])
    return out


def fallback_wm(model: str) -> tuple[int, int]:
    folded = model.upper().replace("-", "_")
    if folded.startswith("SM_S928"):
        return (1440, 3120)
    return (1080, 2400)


def _size_after(text: str, label: str) -> tuple[int, int] | None:
    for line in text.splitlines():
        if label not in line:
            continue
        tail = line.split(label, 1)[1].strip()
        if "x" not in tail:
            continue
        width_s, _, height_s = tail.partition("x")
        if width_s.isdigit() and height_s.isdigit():
            return int(width_s), int(height_s)
    return None


def _is_mdns_serial(serial: str) -> bool:
    return "_adb-tls-connect._tcp" in serial or "_adb-tls-pairing._tcp" in serial


def _is_hostport(value: str) -> bool:
    host, sep, port = value.rpartition(":")
    if not sep or not host or not port.isdigit():
        return False
    number = int(port)
    return 0 < number < 65536
