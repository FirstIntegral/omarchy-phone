#!/usr/bin/env bash
# Symlink the launcher, desktop entries, and Hyprland rules into this user.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/applications"
HYPR="${HOME}/.config/hypr"
LUA="${HYPR}/hyprland.lua"
REQUIRE='require("hypr.phone")'

mkdir -p "$BIN_DIR" "$APP_DIR" "$HYPR"
chmod +x "$ROOT/bin/omarchy-phone"
ln -sfn "$ROOT/bin/omarchy-phone" "$BIN_DIR/omarchy-phone"
ln -sfn "$ROOT/share/applications/omarchy-phone.desktop" "$APP_DIR/omarchy-phone.desktop"
ln -sfn "$ROOT/share/applications/omarchy-phone-desk.desktop" "$APP_DIR/omarchy-phone-desk.desktop"
ln -sfn "$ROOT/share/hypr/phone.lua" "$HYPR/phone.lua"

if [[ ! -f "$LUA" ]]; then
  echo "install: $LUA is missing. Hyprland rules were not wired." >&2
  exit 1
fi

if ! grep -qF "$REQUIRE" "$LUA"; then
  printf '\n-- Omarchy Phone. Super+Shift+H mirrors the phone.\n%s\n' "$REQUIRE" >>"$LUA"
  echo "install: appended $REQUIRE to hyprland.lua"
else
  echo "install: hyprland.lua already loads hypr.phone"
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$APP_DIR" >/dev/null 2>&1 || true
fi

echo "install: $BIN_DIR/omarchy-phone"
echo "install: packages, once: sudo pacman -S --needed scrcpy android-tools android-udev"
