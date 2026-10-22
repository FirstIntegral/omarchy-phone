# Decisions & Rationale (ADRs)

Append an entry (date + decision + why + rejected alternatives) in the same turn a meaningful choice is made.

## 2026-10-22 scrcpy front end, not a second phone stack

- **Decision:** `omarchy-phone` is a Python launcher around scrcpy 5 plus Hyprland window rules. Mirror shows the S24 Ultra panel in a phone-shaped floating window and injects a UHID keyboard. Desk mode uses scrcpy's virtual display (`--new-display` and `--flex-display`) so the glass can stay in a pocket while a second Android screen is on the monitor. Mouse stays scrcpy's default touch mapping. The shortcut modifier is Left Alt only.
- **Why:** scrcpy already does the hard part: encode on the phone, decode on the PC (hardware decode in 5.0), audio, clipboard, drag-and-drop, USB, and wireless adb. The S24 is the device the user asked to use. Waydroid would boot a different Android image and would not show this phone. A from-scratch client of the scrcpy protocol would reimplement a maintained program. SMS, calls, photos, and notification sync need a companion app with extra permissions and are a different product.
- **Rejected:** a custom Wayland video client; Waydroid or an emulator image; a Phone Link clone of messages and calls in this release; UHID mouse (relative pointer, wrong for a touch UI); leaving Super as a scrcpy shortcut modifier (it belongs to Hyprland). `--shortcut-mod=lalt` is the split.
- **Key:** `Super+Shift+H` launches or focuses the window. `Super+Shift+P` stays Google Photos. Nothing was unbound.
