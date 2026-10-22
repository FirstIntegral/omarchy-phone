import unittest

from omarchy_phone.adb import (
    DeviceChoiceError,
    choose_device,
    connect_candidates,
    fallback_wm,
    parse_devices,
    parse_mdns,
    parse_wm_size,
)


USB = """List of devices attached
R5CW123ABC           device usb:3-2 product:e3q model:SM_S928U device:e3q transport_id:4
"""

BOTH = """List of devices attached
R5CW123ABC           device usb:3-2 product:e3q model:SM_S928U device:e3q transport_id:4
192.168.1.20:34567   device product:e3q model:SM_S928U device:e3q transport_id:5
"""

UNAUTH = """List of devices attached
R5CW123ABC           unauthorized usb:3-2 transport_id:4
"""


class ParseTests(unittest.TestCase):
    def test_usb_device(self):
        devices = parse_devices(USB)
        self.assertEqual(len(devices), 1)
        self.assertEqual(devices[0].serial, "R5CW123ABC")
        self.assertEqual(devices[0].state, "device")
        self.assertEqual(devices[0].transport, "usb")
        self.assertEqual(devices[0].model, "SM_S928U")

    def test_tcp_device(self):
        text = "192.168.1.20:34567 device product:e3q model:SM_S928B device:e3q\n"
        device = parse_devices(text)[0]
        self.assertEqual(device.transport, "tcp")
        self.assertEqual(device.model, "SM_S928B")

    def test_skips_emulator(self):
        text = "emulator-5554 device product:sdk_gphone model:sdk_gphone64_x86_64\n"
        device = parse_devices(text)[0]
        self.assertEqual(device.transport, "emulator")

    def test_wm_size_prefers_physical(self):
        text = "Physical size: 1440x3120\nOverride size: 1080x2340\n"
        self.assertEqual(parse_wm_size(text), (1440, 3120))

    def test_mdns_kinds(self):
        text = (
            "List of discovered mdns services\n"
            "adb-R5\t_adb-tls-connect._tcp\t192.168.1.20:34567\n"
            "adb-R5\t_adb-tls-pairing._tcp\t192.168.1.20:40123\n"
        )
        services = parse_mdns(text)
        self.assertEqual([(s.kind, s.address) for s in services], [
            ("connect", "192.168.1.20:34567"),
            ("pairing", "192.168.1.20:40123"),
        ])

    def test_s24_fallback(self):
        self.assertEqual(fallback_wm("SM_S928U"), (1440, 3120))
        self.assertEqual(fallback_wm("SM-S928B"), (1440, 3120))
        self.assertEqual(fallback_wm("Pixel_8"), (1080, 2400))


class ChooseTests(unittest.TestCase):
    def test_single(self):
        device = choose_device(parse_devices(USB))
        self.assertEqual(device.serial, "R5CW123ABC")

    def test_prefers_usb_when_both(self):
        device = choose_device(parse_devices(BOTH))
        self.assertEqual(device.transport, "usb")

    def test_wifi_flag_prefers_tcp(self):
        device = choose_device(parse_devices(BOTH), prefer_tcp=True)
        self.assertEqual(device.serial, "192.168.1.20:34567")

    def test_unauthorized(self):
        with self.assertRaises(DeviceChoiceError) as caught:
            choose_device(parse_devices(UNAUTH))
        self.assertIn("Allow", str(caught.exception))

    def test_none(self):
        with self.assertRaises(DeviceChoiceError) as caught:
            choose_device(parse_devices("List of devices attached\n"))
        self.assertIn("no phone", str(caught.exception))

    def test_mdns_alias_is_the_same_phone(self):
        text = (
            "192.168.1.46:33745 device product:e3q model:SM_S928B device:e3q\n"
            "adb-RFCX808P0TF-iVjGTR._adb-tls-connect._tcp device product:e3q model:SM_S928B device:e3q\n"
        )
        device = choose_device(parse_devices(text))
        self.assertEqual(device.serial, "192.168.1.46:33745")

    def test_serial_match(self):
        device = choose_device(parse_devices(BOTH), serial="192.168.1.20:34567")
        self.assertEqual(device.transport, "tcp")

    def test_candidates_do_not_guess(self):
        from omarchy_phone.adb import MdnsService

        many = [
            MdnsService("a", "connect", "192.168.1.20:1"),
            MdnsService("b", "connect", "192.168.1.21:2"),
            MdnsService("c", "pairing", "192.168.1.20:9"),
        ]
        self.assertEqual(connect_candidates(None, many), [])
        self.assertEqual(connect_candidates("10.0.0.2:5555", many), ["10.0.0.2:5555"])
        one = [MdnsService("a", "connect", "192.168.1.20:34567")]
        self.assertEqual(
            connect_candidates("10.0.0.2:5555", one),
            ["10.0.0.2:5555", "192.168.1.20:34567"],
        )


if __name__ == "__main__":
    unittest.main()
