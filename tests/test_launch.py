import unittest

from omarchy_phone.launch import Options, camera_command, desk_command, mirror_command, phone_window, scrcpy_env


S24 = (1440, 3120)


class WindowTests(unittest.TestCase):
    def test_s24_ultra_shape(self):
        self.assertEqual(phone_window(*S24), (432, 936))

    def test_landscape(self):
        self.assertEqual(phone_window(1920, 1080), (768, 432))

    def test_generic_phone_shape(self):
        self.assertEqual(phone_window(1080, 2400), (432, 960))


class CaptureTests(unittest.TestCase):
    def test_capture_matches_window(self):
        launch = mirror_command("R5", "tcp", (1080, 2400), Options())
        self.assertIn("--window-width=432", launch.command)
        self.assertIn("--window-height=960", launch.command)
        self.assertIn("--max-size=960", launch.command)
        self.assertIn("--video-bit-rate=8M", launch.command)


class CommandTests(unittest.TestCase):
    def test_usb_mirror(self):
        launch = mirror_command("R5", "usb", S24, Options())
        self.assertEqual(
            launch.command,
            [
                "scrcpy",
                "--serial",
                "R5",
                "--window-title",
                "Omarchy Phone",
                "--window-width=432",
                "--window-height=936",
                "--keyboard=uhid",
                "--shortcut-mod=lalt",
                "--keep-active",
                "--stay-awake",
                "--video-buffer=0",
                "--audio-buffer=30",
                "--no-clipboard-autosync",
                "--max-fps=120",
                "--video-bit-rate=12M",
                "--video-codec=h264",
                "--max-size=936",
            ],
        )
        self.assertEqual(launch.app_id, "scrcpy")
        self.assertNotIn("--turn-screen-off", launch.command)
        self.assertNotIn("--mouse=uhid", launch.command)

    def test_wifi_mirror_is_lighter(self):
        launch = mirror_command("192.168.1.20:34567", "tcp", S24, Options(screen_off=True))
        self.assertIn("--max-size=936", launch.command)
        self.assertIn("--max-fps=120", launch.command)
        self.assertIn("--video-buffer=0", launch.command)
        self.assertIn("--no-clipboard-autosync", launch.command)
        self.assertIn("--video-bit-rate=8M", launch.command)
        self.assertIn("--turn-screen-off", launch.command)
        self.assertIn("--serial", launch.command)

    def test_codec_override(self):
        launch = mirror_command("R5", "usb", S24, Options(codec="h265", fps=90, bit_rate="20M"))
        self.assertIn("--video-codec=h265", launch.command)
        self.assertIn("--max-fps=90", launch.command)
        self.assertIn("--video-bit-rate=20M", launch.command)

    def test_desk_is_a_virtual_display(self):
        launch = desk_command("R5", "usb", Options(app="com.android.settings"))
        self.assertEqual(launch.app_id, "scrcpy-desk")
        self.assertIn("--new-display=1920x1200/240", launch.command)
        self.assertIn("--flex-display", launch.command)
        self.assertIn("--display-ime-policy=local", launch.command)
        self.assertIn("--start-app=com.android.settings", launch.command)
        self.assertNotIn("--turn-screen-off", launch.command)
        self.assertNotIn("--max-size=1440", launch.command)

    def test_desk_fixed(self):
        launch = desk_command("R5", "tcp", Options(flex=False))
        self.assertNotIn("--flex-display", launch.command)
        self.assertIn("--video-bit-rate=8M", launch.command)

    def test_camera(self):
        launch = camera_command("R5", Options(front=True))
        self.assertEqual(launch.app_id, "scrcpy-camera")
        self.assertIn("--video-source=camera", launch.command)
        self.assertIn("--camera-facing=front", launch.command)
        self.assertIn("--audio-source=mic", launch.command)
        self.assertNotIn("--max-size=1440", launch.command)

    def test_camera_no_audio_skips_mic(self):
        launch = camera_command("R5", Options(no_audio=True))
        self.assertIn("--no-audio", launch.command)
        self.assertNotIn("--audio-source=mic", launch.command)

    def test_tcpip_omits_serial(self):
        launch = mirror_command("R5", "tcp", S24, Options(tcpip=""))
        self.assertNotIn("--serial", launch.command)
        self.assertIn("--tcpip", launch.command)
        self.assertIn("--max-size=936", launch.command)

    def test_rejects_bad_package(self):
        with self.assertRaises(ValueError):
            desk_command("R5", "usb", Options(app="not a package"))

    def test_rejects_both_audio_flags(self):
        with self.assertRaises(ValueError):
            mirror_command("R5", "usb", S24, Options(no_audio=True, audio_dup=True))

    def test_wayland_env(self):
        env = scrcpy_env({"WAYLAND_DISPLAY": "wayland-1", "PATH": "/usr/bin"}, "scrcpy")
        self.assertEqual(env["SDL_APP_ID"], "scrcpy")
        self.assertEqual(env["SDL_VIDEODRIVER"], "wayland")
        self.assertEqual(env["PATH"], "/usr/bin")

    def test_does_not_override_explicit_video_driver(self):
        env = scrcpy_env({"WAYLAND_DISPLAY": "wayland-1", "SDL_VIDEODRIVER": "x11"}, "scrcpy-desk")
        self.assertEqual(env["SDL_VIDEODRIVER"], "x11")
        self.assertEqual(env["SDL_APP_ID"], "scrcpy-desk")


if __name__ == "__main__":
    unittest.main()
