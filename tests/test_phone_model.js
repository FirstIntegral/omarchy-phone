const assert = require("assert")
const fs = require("fs")
const vm = require("vm")
const path = require("path")

const file = path.join(
  __dirname,
  "../share/omarchy-plugin/firstintegral.phone/PhoneModel.js",
)
const sandbox = {}
vm.runInNewContext(fs.readFileSync(file, "utf8"), sandbox)

assert.strictEqual(sandbox.validCode("123456"), true)
assert.strictEqual(sandbox.validCode("12345"), false)
assert.strictEqual(sandbox.validCode("<img src=x>"), false)
assert.strictEqual(sandbox.validCode("1234567"), false)

assert.strictEqual(sandbox.validHostPort("192.168.1.46:41263"), true)
assert.strictEqual(sandbox.validHostPort("192.168.1.46"), false)
assert.strictEqual(sandbox.validHostPort("<img src=https://example.invalid/x>"), false)
assert.strictEqual(sandbox.validHostPort("999.1.1.1:1"), false)

const marked = sandbox.readStatus(
  '{"state":"pair","pairing":"<img src=\\"https://example.invalid/x\\">"}',
)
assert.strictEqual(marked.state, "pair")
assert.strictEqual(marked.pairing, "")

const badState = sandbox.readStatus('{"state":"<b>no</b>","pairing":"192.168.1.46:41263"}')
assert.strictEqual(badState.state, "error")
assert.strictEqual(badState.pairing, "192.168.1.46:41263")

const huge = sandbox.readStatus("x".repeat(2001))
assert.strictEqual(huge.state, "error")

const good = sandbox.readStatus('{"state":"pair","pairing":"192.168.1.46:41263"}')
assert.strictEqual(good.state, "pair")
assert.strictEqual(good.pairing, "192.168.1.46:41263")

const paired = sandbox.readPair('{"ok":true,"connected":true}\n')
assert.strictEqual(paired.ok, true)
assert.strictEqual(paired.connected, true)
const markedPair = sandbox.readPair('{"ok":"<img>","connected":"yes"}')
assert.strictEqual(markedPair.ok, false)
assert.strictEqual(markedPair.connected, false)
const junk = sandbox.readPair("not json")
assert.strictEqual(junk.ok, false)
assert.strictEqual(junk.connected, false)

console.log("phone model ok")
