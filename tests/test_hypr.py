import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HyprRuleTests(unittest.TestCase):
    def test_super_is_dropped_only_on_the_phone_window(self):
        text = (ROOT / "share/hypr/phone.lua").read_text()
        self.assertIn('hl.bind("Super_L"', text)
        self.assertIn('hl.bind("Super_R"', text)
        self.assertIn("auto_consuming = true", text)
        self.assertIn("ignore_mods = true", text)
        self.assertIn("return { ok = false }", text)
        self.assertIn('class == "scrcpy"', text)
        self.assertIn('title == "Omarchy Phone"', text)
