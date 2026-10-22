-- scrcpy 5 is SDL3. omarchy-phone sets SDL_APP_ID before SDL starts, so the
-- class is scrcpy, scrcpy-desk, or scrcpy-camera. Size is on that class.
-- Title rules are the backup when the class is only the binary name.
-- Super+Shift+H was free. Super+Shift+P stays Google Photos.

o.window("^(scrcpy|scrcpy-desk|scrcpy-camera)$", { tag = "-default-opacity" })
o.window("^(scrcpy|scrcpy-desk|scrcpy-camera)$", { opacity = "1 override 1 override" })
o.window("^(scrcpy|scrcpy-desk|scrcpy-camera)$", {
  idle_inhibit = "focus",
  no_shortcuts_inhibit = true,
})

o.window("^scrcpy$", {
  float = true,
  center = true,
  size = { 432, 936 },
  -- This Hyprland build rejects rounding above 20.
  rounding = 20,
  keep_aspect_ratio = true,
})

o.window("^scrcpy-desk$", {
  float = true,
  center = true,
  size = { 1280, 800 },
  rounding = 16,
})

o.window("^scrcpy-camera$", {
  float = true,
  center = true,
  size = { 960, 540 },
  rounding = 16,
  keep_aspect_ratio = true,
})

o.window({ title = "^Omarchy Phone$" }, {
  float = true,
  center = true,
  size = { 432, 936 },
  rounding = 20,
  keep_aspect_ratio = true,
})

o.window({ title = "^Omarchy Phone Desk$" }, {
  float = true,
  center = true,
  size = { 1280, 800 },
  rounding = 16,
})

o.window({ title = "^Omarchy Phone Camera$" }, {
  float = true,
  center = true,
  size = { 960, 540 },
  rounding = 16,
  keep_aspect_ratio = true,
})

o.bind("SUPER + SHIFT + H", "Phone", { launch = "omarchy-phone", focus = "scrcpy" })
