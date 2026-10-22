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

-- No center rule. center is applied at open and, with a borderless scrcpy
-- window, a plain drag is a swipe on the phone, so the window looked glued
-- to the middle. It opens on the right. Super+left-drag moves it after that.
-- Rounding above 20 is rejected by this Hyprland build.
-- No size here. scrcpy asks for the size that matches `wm size`, so a phone
-- that is not 19.5:9 is not forced into the S24 frame.
-- border_size 0: the theme border is a gold-to-blue gradient, so each edge
-- of the phone was a different color, plus a 1px gap on the right.

o.window("^scrcpy$", {
  float = true,
  move = { "(monitor_w - window_w - 24)", "40" },
  rounding = 20,
  border_size = 0,
  keep_aspect_ratio = true,
})

o.window("^scrcpy-desk$", {
  float = true,
  size = { 1280, 800 },
  move = { "80", "80" },
  rounding = 16,
  border_size = 0,
})

o.window("^scrcpy-camera$", {
  float = true,
  size = { 960, 540 },
  move = { "80", "80" },
  rounding = 16,
  border_size = 0,
  keep_aspect_ratio = true,
})

o.window({ title = "^Omarchy Phone$" }, {
  float = true,
  move = { "(monitor_w - window_w - 24)", "40" },
  rounding = 20,
  border_size = 0,
  keep_aspect_ratio = true,
})

o.window({ title = "^Omarchy Phone Desk$" }, {
  float = true,
  size = { 1280, 800 },
  move = { "80", "80" },
  rounding = 16,
  border_size = 0,
})

o.window({ title = "^Omarchy Phone Camera$" }, {
  float = true,
  size = { 960, 540 },
  move = { "80", "80" },
  rounding = 16,
  border_size = 0,
  keep_aspect_ratio = true,
})

-- Focus the phone window by its title. A pattern of "scrcpy" also matches
-- any chat or terminal whose title merely mentions scrcpy, and the key
-- then looks like it did nothing.
o.bind("SUPER + SHIFT + H", "Phone", { launch = "omarchy-phone", focus = "Omarchy Phone" })
