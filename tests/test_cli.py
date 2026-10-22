import io
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from omarchy_phone.cli import main
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
    def __init__(self, devices=USB, wm=WM, mdns=""):
        self.devices = devices
        self.wm = wm
        self.mdns = mdns
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
            self.devices = (
                "List of devices attached\n"
                f"{cmd[2]} device product:e3q model:SM_S928U device:e3q\n"
            )
            return Result(out=f"connected to {cmd[2]}\n")
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

    def test_help_is_the_root_parser(self):
        import contextlib

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("desk", out.getvalue())
        self.assertIn("pair", out.getvalue())


if __name__ == "__main__":
    unittest.main()
