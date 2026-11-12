# Decisions & Rationale (ADRs)

Append an entry (date + decision + why + rejected alternatives) in the same turn a meaningful choice is made.

## 2026-11-12 The bar card takes the pairing code

- **Decision:** A click on `firstintegral.phone` opens a `KeyboardPanel`. `omarchy-phone status` prints one JSON line. `ready` launches the mirror and closes the card. `pair` keeps the card up, with the phone steps and a 6-digit box. The port comes from `_adb-tls-pairing`. The code is checked as six digits, then passed as one argv element to `omarchy-phone pair`. Pair prints `{"ok","connected"}` on stdout. The card does not show adb text. Strings live in `i18n/en.json`.
- **Why:** The key refusal was a chat message and a notification. The code only exists on the phone screen. The next time has to be solvable from the icon.
- **Rejected:** typing the port as well as the code; a shell string that includes the code; leaving the one-tap launch in place when the key is refused, which exits with no window.
- **Follow-up:** `omarchy-launch-or-focus 'Omarchy Phone'` is a case-insensitive substring match. On 2026-11-12 it matched the grok window title that contains `Omarchy phone`, focused that window, switched to its workspace, and warped the cursor to the window center. The card click must not call that helper. A `PopupCard` draws, and it does not take keys. `KeyboardPanel` does. While that card is open the launcher sets `cursor:no_warps` true and restores false on close, so the pointer stays put. The user confirmed the code box accepts typing. The shell hot reload kept the original click handler until `omarchy-restart-shell`. `share/hypr/phone.lua` now focuses class `scrcpy`. Hyprland has not reloaded that file.

## 2026-11-12 Keep the wireless key, and say when the phone rejects it

- **Decision:** A bar click that finds one advertising phone and gets `failed to connect` (not `Connection refused`) exits with `NeedsPairError`. The notification's first line is `Phone at <ip:port> refused this computer's key.` No USB setup essay on that path. `omarchy-phone pair` then `adb connect`s when exactly one `_adb-tls-connect` service is up, and saves that address. After any real open, the launcher runs `settings put global adb_allowed_connection_time 0` on that phone. A failed write still opens the mirror and prints one line.
- **Why:** On 2026-11-12 the S24 Ultra (SM-S928B, `192.168.1.46`) advertised `_adb-tls-connect` on port 35231. TCP was open. The adb server log was `SSLV3_ALERT_CERTIFICATE_UNKNOWN` for `~/.android/adbkey` (key file dated 2026-10-22). The bar launched `omarchy-phone` and the process exited with no window. Android's default authorization lifetime is about seven days unless that developer switch is on. The saved port in `last.json` was already stale (`35095`, connection refused). Port rediscovery was already implemented. Key rejection was not.
- **Rejected:** a QR pairing window (the popup code is the one step the phone must show); turning Wireless debugging on from here (the switch is off after reboot until the phone is already reachable); failing the mirror when the settings write is denied.

## 2026-10-22 Drop Super while the phone window is focused

- **Decision:** `share/hypr/phone.lua` binds Left Super and Right Super with `auto_consuming`. The bind returns `{ ok = true }` only when the focused window is `scrcpy`, `scrcpy-desk`, `scrcpy-camera`, or one of the three Omarchy Phone titles. Otherwise it returns `{ ok = false }` and the key is passed on. `--shortcut-mod` stays `lalt`.
- **Why:** The mirror uses a UHID keyboard. Super is not an scrcpy shortcut, so scrcpy forwards it as `KEYCODE_META_LEFT` (117). On this S24 Ultra, `dumpsys input` records that key from the scrcpy device as `KEY_GESTURE_TYPE_ALL_APPS`, action `COMPLETE`. The gesture runs on release, so a Super+drag of the window and a bare Super tap both step the phone back. Hyprland tracks the modifier in xkb before it decides whether to forward the key, so swallowing the event leaves Super+drag and Super+key binds intact. The release is withheld because the press was not sent.
- **Rejected:** adding `lsuper` to `--shortcut-mod`. That also swallows Super, but every Super chord that reaches the window becomes an scrcpy shortcut. `Super+q` would quit the mirror. `Super+r` would rotate the phone. Those chords belong to Hyprland.

## 2026-10-22 The phone edge is the screen, on any Android shape

- **Decision:** The mirror encodes at the window's long side (`--max-size` equals that side). Hyprland draws no border on the scrcpy windows. The mirror window rule does not force 432×936. scrcpy asks for the size computed from `wm size`.
- **Why:** A 960 cap on a 1440×3120 panel encodes 443×960. Fitted into a 432×936 window, one column is left empty and shows up as a gray line on the right. The theme border is a gold-to-blue gradient, so the four edges of the phone were four different colors. A fixed 432×936 rule would letterbox every phone that is not 19.5:9. Bitrate stays 8M on Wi-Fi and 12M on USB. The window is still only a few hundred pixels wide, so matching it costs less than the old cap, not more.
- **Rejected:** leaving the gradient border and calling it chrome; a second border drawn by us; forcing every phone into the S24 frame.

## 2026-10-22 Low latency without opening the lock screen

- **Decision:** The mirror runs at 120 fps, H.264, video buffer 0, audio buffer 30 ms. Clipboard autosync is off. The window opens on the right, with a libdecor title bar, and is not centered. A bar widget `firstintegral.phone` runs the same launch as Super+Shift+H. Capture size is no longer a fixed 960 or 1200. That lives in "The phone edge is the screen".
- **Why:** A plain drag on the picture is a swipe on the phone, and a center rule put that picture in the middle of the monitor. H.264 with no video buffer is scrcpy's low-latency path. A frame the size of the window spends less time on the encoder and on Wi-Fi than a full-panel encode. Autosync would copy whatever is on the phone clipboard, including passwords, onto the Linux clipboard whenever it changes. The PIN pad stays black. That surface is marked non-recordable on purpose.
- **Rejected:** H.265 for the default (more compression delay), a 1440p stream over Wi-Fi, turning off Android's secure-display flag, and a new network service for the bar icon.

## 2026-10-22 scrcpy front end, not a second phone stack

- **Decision:** `omarchy-phone` is a Python launcher around scrcpy 5 plus Hyprland window rules. Mirror shows the S24 Ultra panel in a phone-shaped floating window and injects a UHID keyboard. Desk mode uses scrcpy's virtual display (`--new-display` and `--flex-display`) so the glass can stay in a pocket while a second Android screen is on the monitor. Mouse stays scrcpy's default touch mapping. The shortcut modifier is Left Alt only.
- **Why:** scrcpy already does the hard part: encode on the phone, decode on the PC (hardware decode in 5.0), audio, clipboard, drag-and-drop, USB, and wireless adb. The S24 is the device the user asked to use. Waydroid would boot a different Android image and would not show this phone. A from-scratch client of the scrcpy protocol would reimplement a maintained program. SMS, calls, photos, and notification sync need a companion app with extra permissions and are a different product.
- **Rejected:** a custom Wayland video client; Waydroid or an emulator image; a Phone Link clone of messages and calls in this release; UHID mouse (relative pointer, wrong for a touch UI); leaving Super as a scrcpy shortcut modifier (it belongs to Hyprland). `--shortcut-mod=lalt` is the split.
- **Key:** `Super+Shift+H` launches or focuses the window. `Super+Shift+P` stays Google Photos. Nothing was unbound.
