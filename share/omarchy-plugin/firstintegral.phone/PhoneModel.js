// Pure checks for the pairing card. Status text is adb output. The code is
// what the user types. Neither one is a shell string.

function validHostPort(value) {
  var match = String(value || "").match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):(\d{1,5})$/)
  if (!match) return false
  for (var i = 1; i <= 4; i++) {
    var octet = Number(match[i])
    if (octet > 255) return false
  }
  var port = Number(match[5])
  return port > 0 && port < 65536
}

function validCode(value) {
  return /^\d{6}$/.test(String(value || ""))
}

function readPair(text) {
  var raw = String(text || "")
  if (raw.length > 500) return { ok: false, connected: false }
  var data
  try {
    data = JSON.parse(raw.trim())
  } catch (e) {
    return { ok: false, connected: false }
  }
  if (!data || typeof data !== "object") return { ok: false, connected: false }
  return { ok: data.ok === true, connected: data.connected === true }
}

function readStatus(text) {
  var raw = String(text || "")
  if (raw.length > 2000) return { state: "error", pairing: "" }
  var data
  try {
    data = JSON.parse(raw.trim())
  } catch (e) {
    return { state: "error", pairing: "" }
  }
  if (!data || typeof data !== "object") return { state: "error", pairing: "" }
  var state = String(data.state || "")
  var allowed = { ready: 1, pair: 1, off: 1, many: 1, unauthorized: 1, error: 1 }
  if (!allowed[state]) state = "error"
  var pairing = validHostPort(data.pairing) ? String(data.pairing) : ""
  return { state: state, pairing: pairing }
}
