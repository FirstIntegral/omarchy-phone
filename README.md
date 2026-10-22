# Omarchy Phone

A window onto your real phone. Built for a Samsung Galaxy S24 Ultra on Omarchy (Hyprland). The phone is the computer. This is not an emulator and not Waydroid.

[scrcpy](https://github.com/Genymobile/scrcpy) 5 does the video, the audio, the touch, and the keyboard. This repo picks the flags, shapes the window, and remembers a wireless address.

## Once on the phone

1. Settings → About phone → Software information. Tap **Build number** seven times.
2. Settings → Developer options. Turn on **USB debugging**.
3. Plug in. Unlock. Tap **Allow**, and check **Always allow from this computer**.

Wireless, same Wi-Fi:

1. Developer options → **Wireless debugging** → **Pair device with pairing code**.
2. The pairing port and the connect port are different numbers.

```bash
omarchy-phone pair 192.168.1.20:37123 123456
omarchy-phone connect 192.168.1.20:41234
```

`omarchy-phone mdns` lists both. After one good connect, plain `omarchy-phone` tries that address again.

## Once on the computer

```bash
sudo pacman -S --needed scrcpy android-tools android-udev
bash install.sh
```

Unplug and replug after `android-udev`. Then **Super+Shift+H**, or run `omarchy-phone`.

`Super+Shift+P` is still Google Photos. Nothing was unbound to make room.

## Use

| Command | What you get |
|---|---|
| `omarchy-phone` | The phone panel, in a tall window. Click is touch. |
| `omarchy-phone --screen-off` | Same mirror, panel off, so the OLED stays dark. |
| `omarchy-phone desk` | A second Android screen. The physical panel is left alone. |
| `omarchy-phone desk --app com.android.settings` | Desk, and open that package. |
| `omarchy-phone camera` | Back camera. `--front` for the other one. |
| `omarchy-phone tcpip` | Cable plugged in: switch the phone to wireless, then mirror. |
| `omarchy-phone --wifi` | Prefer the Wi-Fi device when the cable is also connected. |
| `omarchy-phone --codec h265` | Sharper stream. h264 is the default because it fails less often. |
| `omarchy-phone doctor` | Say what is missing. |

Left **Alt** is the shortcut key inside the window. Super stays Hyprland.

- Right-click: Back. Middle-click: Home.
- Alt+o turns the phone panel off. Alt+Shift+o turns it on.
- Alt+k opens the Android keyboard layout. Do that once. UHID is a real keyboard, and One UI needs the layout.
- Alt+f fullscreen. Alt+h Home. Alt+b Back. Alt+n notifications.
- Drag a file onto the window to copy it to the phone. An APK installs.

The first launch asks the phone to trust this computer's adb key. That tap is yours.

Audio from the phone plays here and is muted on the phone. `--audio-dup` keeps both. `--no-audio` keeps it on the phone only.

Banking apps and Secure Folder draw a black rectangle. Android marks those surfaces as secure. scrcpy cannot see them.

## Desk mode

`--new-display` asks Android for another screen. On some Samsung builds that screen is blank until an app is started. If the desk window stays black:

```bash
omarchy-phone desk --app com.android.settings
```

Resizing the desk window resizes that Android screen (`--flex-display`). `--fixed` turns that off.

## Develop

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Python 3 standard library only. `bash install.sh` symlinks `bin/omarchy-phone` into `~/.local/bin`, the desktop files into `~/.local/share/applications`, and `share/hypr/phone.lua` into `~/.config/hypr/phone.lua`. It appends `require("hypr.phone")` to `~/.config/hypr/hyprland.lua` once.

Remove that line, and the three symlinks, to uninstall the desktop wiring. The repo can stay.
