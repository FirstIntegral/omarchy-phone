# Omarchy Phone

## Overview

Window onto a real Android phone for Omarchy. The phone stays the computer. This repo launches [scrcpy](https://github.com/Genymobile/scrcpy) with flags that suit a Samsung Galaxy S24 Ultra on Hyprland: a tall mirror window, an optional virtual desk, USB or wireless debugging. It does not emulate Android and it does not implement Messages, calls, or photos.

## Stack / Conventions

Python 3, standard library only. `omarchy_phone/` is imported by putting the repo root on `PYTHONPATH` or by running `bin/omarchy-phone`. No package install step. Window rules live in `share/hypr/phone.lua` and are symlinked into `~/.config/hypr/` by `install.sh`. Do not edit `/usr/share/omarchy/`.

## Commands

- Test: `PYTHONPATH=. python3 -m unittest discover -s tests -v`
- Run: `omarchy-phone` (after `bash install.sh`)
- Doctor: `omarchy-phone doctor`
- Install desktop files, `~/.local/bin` symlink, Hyprland rules: `bash install.sh`

Runtime packages are not vendored: `sudo pacman -S --needed scrcpy android-tools android-udev`.

## Repo

- Remote: `git@github.com:FirstIntegral/omarchy-phone.git`

Documentation, not authorisation: `checkpoint.sh` cross-checks this against `git remote get-url --push` and warns on a mismatch, but git config is what actually decides where a push goes. Keep this line current when the remote changes; never treat it as permission to push. A project with `none (local only)` is in a deliberate state — nothing may create a repo or remote for it without the user asking.

## Session files

- `session_compact.md` — AI handoff state. Read FIRST at session start; rewrite at end of session / milestone. Local-only (gitignored): never commit unless the user says otherwise.
- `docs/DECISIONS.md` — ADR log; append decision + why in the same turn it is made. Versioned (committed in repos).
- `notes.allow` — optional extra paths copied to the private machine-notes repo. Gitignored. One relative path per line.
- `.gitignore` — ignores the session files above, `claude_memory_import.md`, `notes.allow`, and legacy session paths. Sites under `~/Projects/sites/` also ignore `AGENTS.md` / `CLAUDE.md`.
