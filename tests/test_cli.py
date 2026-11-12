import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from omarchy_phone.cli import focus_address, main
from omarchy_phone.config import load_last


USB = """List of devices attached
R5CW123ABC           device usb:3-2 product:e3q model:SM_S928U device:e3q transport_id:4
"""

WM = "Physical size: 1440x3120\n"


class Result:
    def __init__(self, code=0, out="", err=""):
        self.returncode = code
        self.stdout = out
        self.stderr = err


class FakeAdb:
    def __init__(self, devices=USB, wm=WM, mdns="", reject_connect=False, settings_fail=False):
        self.devices = devices
        self.wm = wm
        self.mdns = mdns
        self.reject_connect = reject_connect
        self.settings_fail = settings_fail
        self.calls = []

    def __call__(self, cmd):
        self.calls.append(list(cmd))
        if cmd[:2] == ["adb", "start-server"]:
            return Result()
        if cmd[:3] == ["adb", "devices", "-l"]:
            return Result(out=self.devices)
        if cmd[:2] == ["adb", "mdns"]:
            return Result(out=self.mdns)
        if list(cmd[:3]) == ["adb", "-s", "R5CW123ABC"] and "wm" in cmd:
            return Result(out=self.wm)
        if cmd[:2] == ["adb", "connect"]:
            if self.reject_connect:
                return Result(out=f"failed to connect to {cmd[2]}\n")
            self.devices = (
                "List of devices attached\n"
                f"{cmd[2]} device product:e3q model:SM_S928U device:e3q\n"
            )
            return Result(out=f"connected to {cmd[2]}\n")
        if len(cmd) >= 5 and cmd[1] == "-s" and cmd[3:5] == ["shell", "settings"]:
            if self.settings_fail:
                return Result(code=1, err="denied\n")
            if "get" in cmd:
                return Result(out="0\n")
            return Result()
        if cmd[:2] == ["adb", "pair"]:
            return Result(out="Successfully paired\n")
        return Result(code=1, err="unexpected " + " ".join(cmd))


class CliTests(unittest.TestCase):
    def env(self, root: Path) -> dict[str, str]:
        return {
            "HOME": str(root),
            "XDG_CONFIG_HOME": str(root / "cfg"),
            "PATH": "/usr/bin",
            "WAYLAND_DISPLAY": "wayland-1",
            "OMARCHY_PHONE_NO_NOTIFY": "1",
            "OMARCHY_PHONE_ASSUME_SCRCPY": "1",
        }

    def test_dry_run_mirror(self):
        err = io.StringIO()
        with TemporaryDirectory() as tmp:
            code = main(
                ["--dry-run"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(),
                stderr=err,
            )
        self.assertEqual(code, 0)
        text = err.getvalue()
        self.assertIn("SDL_APP_ID=scrcpy", text)
        self.assertIn("SDL_VIDEODRIVER=wayland", text)
        self.assertIn("--window-width=432", text)
        self.assertIn("--window-height=936", text)
        self.assertIn("--keyboard=uhid", text)
        self.assertIn("--shortcut-mod=lalt", text)
        self.assertIn("--serial R5CW123ABC", text)

    def test_dry_run_does_not_save_or_launch(self):
        launched = []
        err = io.StringIO()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = main(
                ["mirror", "--dry-run"],
                environ=self.env(root),
                adb_runner=FakeAdb(),
                scrcpy_exec=lambda cmd, env: launched.append(cmd) or 0,
                stderr=err,
            )
            self.assertIsNone(load_last(self.env(root)))
        self.assertEqual(code, 0)
        self.assertEqual(launched, [])

    def test_no_phone_explains_setup(self):
        err = io.StringIO()
        with TemporaryDirectory() as tmp:
            code = main(
                ["mirror", "--no-reconnect"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(devices="List of devices attached\n"),
                stderr=err,
            )
        self.assertEqual(code, 2)
        self.assertIn("Build number", err.getvalue())
        self.assertIn("pacman", err.getvalue())

    def test_reconnects_single_mdns(self):
        err = io.StringIO()
        mdns = "adb-R5 _adb-tls-connect._tcp 192.168.1.20:34567\n"
        fake = FakeAdb(devices="List of devices attached\n", mdns=mdns)
        launched = []
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = main(
                ["mirror"],
                environ=self.env(root),
                adb_runner=fake,
                scrcpy_exec=lambda cmd, env: launched.append((list(cmd), dict(env))) or 0,
                stderr=err,
            )
            self.assertEqual(load_last(self.env(root)), "192.168.1.20:34567")
        self.assertEqual(code, 0)
        self.assertEqual(launched[0][1]["SDL_APP_ID"], "scrcpy")
        self.assertIn("192.168.1.20:34567", launched[0][0])

    def test_desk_dry_run_app_id(self):
        err = io.StringIO()
        with TemporaryDirectory() as tmp:
            code = main(
                ["desk", "--dry-run"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(),
                stderr=err,
            )
        self.assertEqual(code, 0)
        text = err.getvalue()
        self.assertIn("SDL_APP_ID=scrcpy-desk", text)
        self.assertIn("--new-display=1920x1200/240", text)
        self.assertNotIn("--turn-screen-off", text)

    def test_pair_and_bad_port(self):
        err = io.StringIO()
        with TemporaryDirectory() as tmp:
            code = main(
                ["pair", "192.168.1.20:40123", "123456"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(),
                stderr=err,
                stdout=io.StringIO(),
            )
        self.assertEqual(code, 0)
        self.assertIn("paired", err.getvalue().lower())

        err = io.StringIO()
        with TemporaryDirectory() as tmp:
            code = main(
                ["connect", "not-a-port"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(),
                stderr=err,
            )
        self.assertEqual(code, 2)

    def test_advertised_phone_that_rejects_the_key(self):
        err = io.StringIO()
        mdns = "adb-R5 _adb-tls-connect._tcp 192.168.1.46:35231\n"
        fake = FakeAdb(devices="List of devices attached\n", mdns=mdns, reject_connect=True)
        with TemporaryDirectory() as tmp:
            code = main(
                ["mirror"],
                environ=self.env(Path(tmp)),
                adb_runner=fake,
                stderr=err,
            )
        self.assertEqual(code, 2)
        text = err.getvalue()
        self.assertIn("Phone at 192.168.1.46:35231 refused this computer's key.", text)
        self.assertNotIn("Build number", text)
        self.assertIn(["adb", "connect", "192.168.1.46:35231"], fake.calls)

    def test_launch_disables_auth_timeout(self):
        err = io.StringIO()
        fake = FakeAdb()
        launched = []
        with TemporaryDirectory() as tmp:
            code = main(
                ["mirror"],
                environ=self.env(Path(tmp)),
                adb_runner=fake,
                scrcpy_exec=lambda cmd, env: launched.append(cmd) or 0,
                stderr=err,
            )
        self.assertEqual(code, 0)
        self.assertTrue(launched)
        self.assertIn(
            [
                "adb",
                "-s",
                "R5CW123ABC",
                "shell",
                "settings",
                "put",
                "global",
                "adb_allowed_connection_time",
                "0",
            ],
            fake.calls,
        )
        self.assertNotIn("Could not disable", err.getvalue())

    def test_timeout_write_failure_still_opens(self):
        err = io.StringIO()
        fake = FakeAdb(settings_fail=True)
        launched = []
        with TemporaryDirectory() as tmp:
            code = main(
                ["mirror"],
                environ=self.env(Path(tmp)),
                adb_runner=fake,
                scrcpy_exec=lambda cmd, env: launched.append(cmd) or 0,
                stderr=err,
            )
        self.assertEqual(code, 0)
        self.assertTrue(launched)
        self.assertIn("Could not disable the adb authorization timeout", err.getvalue())

    def test_pair_connects_the_one_advertised_phone(self):
        err = io.StringIO()
        out = io.StringIO()
        mdns = "adb-R5 _adb-tls-connect._tcp 192.168.1.20:34567\n"
        fake = FakeAdb(devices="List of devices attached\n", mdns=mdns)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = main(
                ["pair", "192.168.1.20:40123", "123456"],
                environ=self.env(root),
                adb_runner=fake,
                stderr=err,
                stdout=out,
            )
            self.assertEqual(load_last(self.env(root)), "192.168.1.20:34567")
        self.assertEqual(code, 0)
        self.assertIn("connected to 192.168.1.20:34567", err.getvalue())
        self.assertEqual(json.loads(out.getvalue()), {"ok": True, "connected": True})

    def test_pair_rejects_a_code_that_is_not_six_digits(self):
        err = io.StringIO()
        fake = FakeAdb()
        with TemporaryDirectory() as tmp:
            code = main(
                ["pair", "192.168.1.20:40123", "<img src=x>"],
                environ=self.env(Path(tmp)),
                adb_runner=fake,
                stderr=err,
            )
        self.assertEqual(code, 2)
        self.assertIn("6 digits", err.getvalue())
        self.assertFalse(any(call[:2] == ["adb", "pair"] for call in fake.calls))

    def test_status_ready_pair_and_off(self):
        err = io.StringIO()
        out = io.StringIO()
        with TemporaryDirectory() as tmp:
            code = main(
                ["status"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(),
                stderr=err,
                stdout=out,
            )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())["state"], "ready")

        err = io.StringIO()
        out = io.StringIO()
        mdns = (
            "adb-R5 _adb-tls-connect._tcp 192.168.1.46:35231\n"
            "adb-R5 _adb-tls-pairing._tcp 192.168.1.46:41263\n"
        )
        with TemporaryDirectory() as tmp:
            code = main(
                ["status"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(devices="List of devices attached\n", mdns=mdns, reject_connect=True),
                stderr=err,
                stdout=out,
            )
        self.assertEqual(code, 2)
        self.assertEqual(
            json.loads(out.getvalue()),
            {"state": "pair", "pairing": "192.168.1.46:41263"},
        )

        out = io.StringIO()
        with TemporaryDirectory() as tmp:
            code = main(
                ["status"],
                environ=self.env(Path(tmp)),
                adb_runner=FakeAdb(devices="List of devices attached\n"),
                stderr=io.StringIO(),
                stdout=out,
            )
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())["state"], "off")

    def test_help_is_the_root_parser(self):
        import contextlib

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("desk", out.getvalue())
        self.assertIn("pair", out.getvalue())


class FocusAddressTests(unittest.TestCase):
    def test_a_chat_title_is_not_the_phone(self):
        clients = [
            {"class": "foot", "title": "Restore Omarchy phone wireless", "address": "0xabc"},
            {"class": "foot", "title": "scrcpy tips", "address": "0xdef"},
        ]
        self.assertIsNone(focus_address(clients))

    def test_the_mirror_wins_over_the_desk(self):
        clients = [
            {"class": "scrcpy-desk", "title": "Omarchy Phone Desk", "address": "0x11"},
            {"class": "scrcpy", "title": "Omarchy Phone", "address": "0x22"},
        ]
        self.assertEqual(focus_address(clients), "0x22")

    def test_a_weird_address_is_dropped(self):
        clients = [{"class": "scrcpy", "title": "Omarchy Phone", "address": "0x22;rm"}]
        self.assertIsNone(focus_address(clients))


if __name__ == "__main__":
    unittest.main()
