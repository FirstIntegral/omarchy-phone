import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui
import "PhoneModel.js" as PhoneModel

// Card under the phone icon. A trusted phone opens the mirror. A refused
// key stays on this card: the steps are here, and the 6-digit code is typed
// here. The code is checked, then passed as one argv element.
// Popup under the icon. It is a direct child of the bar button. A hidden
// loader leaves this window unmapped, and the focus grab then lands on the
// fullscreen bar surface. Hyprland warps the cursor to the middle of that.
Item {
  id: root

  property var bar: null
  property var anchorItem: null
  property var hostWidget: null
  property bool opened: false
  readonly property var barIdentity: hostWidget || root
  readonly property string launcher: Quickshell.env("HOME") + "/.local/bin/omarchy-phone"
  property bool busy: false
  property string phase: "looking"
  property string pairing: ""
  property string noteKey: ""
  property bool statusHandled: false
  property bool pairHandled: false

  signal codeAccepted()
  signal focusCode()

  onOpenedChanged: if (root.opened) root.look()

  function open() {
    if (root.opened || noWarpProc.running) return
    // The card is a fullscreen layer for one moment so the text box can take
    // keys. Hyprland would otherwise warp the pointer to the middle of it.
    noWarpProc.running = true
  }
  function close() {
    root.opened = false
    if (!restoreWarpProc.running) restoreWarpProc.running = true
  }
  function toggle() {
    if (root.opened) root.close()
    else root.open()
  }

  function look() {
    console.log("phone: card", root.phase)
    if (root.busy) return
    root.busy = true
    root.statusHandled = false
    root.phase = "looking"
    root.noteKey = ""
    statusProc.running = true
  }

  function applyStatus(text) {
    if (root.statusHandled) return
    root.statusHandled = true
    root.busy = false
    var status = PhoneModel.readStatus(text)
    root.pairing = status.pairing
    root.phase = status.state
    console.log("phone: status", status.state, status.pairing)
    if (status.state === "pair" && status.pairing !== "") focusCodeTimer.restart()
    if (status.state === "ready") {
      root.openMirror()
      root.close()
    }
  }

  function submit(code) {
    if (root.busy) return
    if (!PhoneModel.validCode(code)) {
      root.noteKey = "phone.badCode"
      return
    }
    if (!PhoneModel.validHostPort(root.pairing)) {
      root.noteKey = "phone.noPopup"
      return
    }
    root.busy = true
    root.pairHandled = false
    root.noteKey = ""
    pairProc.command = [root.launcher, "pair", root.pairing, code]
    pairProc.running = true
  }

  function finishPair(body) {
    if (root.pairHandled) return
    root.pairHandled = true
    root.busy = false
    var result = PhoneModel.readPair(body)
    if (result.connected) {
      root.phase = "paired"
      root.codeAccepted()
      root.openMirror()
      root.close()
      return
    }
    if (result.ok) {
      root.noteKey = "phone.pairedWait"
      root.phase = "pair"
      return
    }
    root.noteKey = "phone.failed"
    root.phase = "pair"
  }

  function openMirror() {
    if (!root.bar) return
    // Do not use omarchy-launch-or-focus. Its match is case-insensitive, so
    // a window whose title merely contains "Omarchy phone" takes the focus,
    // the workspace jumps, and the cursor warps to that window's center.
    root.bar.run("uwsm-app -- omarchy-phone")
  }

  // Wait until the panel has taken focus, then move it into the code box.
  Timer {
    id: focusCodeTimer
    interval: 80
    onTriggered: root.focusCode()
  }

  Process {
    id: statusProc
    command: [root.launcher, "status"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.applyStatus(text)
    }
    onExited: function() {
      Qt.callLater(function() {
        if (!root.statusHandled) root.applyStatus("")
      })
    }
  }

  Process {
    id: pairProc
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.finishPair(text)
    }
    onExited: function() {
      Qt.callLater(function() {
        if (!root.pairHandled) root.finishPair("")
      })
    }
  }

  Process {
    id: noWarpProc
    command: ["hyprctl", "keyword", "cursor:no_warps", "true"]
    onExited: root.opened = true
  }

  Process {
    id: restoreWarpProc
    command: ["hyprctl", "keyword", "cursor:no_warps", "false"]
  }

  KeyboardPanel {
    id: panel
    anchorItem: root.anchorItem
    owner: root.barIdentity
    bar: root.bar
    open: root.opened
    centerOnBar: false
    focusTarget: codeField
    contentWidth: panel.fittedContentWidth(Style.space(360))
    contentHeight: panel.cappedContentHeight(Style.space(340))

    Column {
      id: column
      anchors.fill: parent
      spacing: Style.space(8)

        Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

        Text {
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          text: strings.t("phone.pairLead")
          visible: root.phase === "pair" || root.phase === "paired"
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.subtitle
          font.bold: true
        }

        Text {
          id: lead
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.body
          text: {
            if (root.phase === "looking") return strings.t("phone.looking")
            if (root.phase === "ready" || root.phase === "paired") return strings.t("phone.paired")
            if (root.phase === "off") return strings.t("phone.offLead")
            if (root.phase === "many") return strings.t("phone.many")
            if (root.phase === "unauthorized") return strings.t("phone.unauthorized")
            if (root.phase === "error") return strings.t("phone.error")
            return ""
          }
          visible: text !== ""
        }

        Text {
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          visible: root.phase === "pair"
          text: strings.t("phone.steps")
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
        }

        Text {
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          visible: root.phase === "off"
          text: strings.t("phone.offSteps")
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
        }

        Text {
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          visible: root.phase === "pair" && root.pairing !== ""
          text: strings.t("phone.port").arg(root.pairing)
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
        }

        Text {
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          visible: root.phase === "pair" && root.pairing === ""
          text: strings.t("phone.noPopup")
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
        }

        Text {
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          visible: root.phase === "pair" && root.pairing !== ""
          text: strings.t("phone.codeLabel")
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.body
        }

        TextField {
          id: codeField
          width: parent.width
          visible: root.phase === "pair" && root.pairing !== ""
          enabled: !root.busy
          placeholderText: strings.t("phone.placeholder")
          maximumLength: 6
          inputMethodHints: Qt.ImhDigitsOnly
          focus: true
          foreground: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          Connections {
            target: root
            function onCodeAccepted() { codeField.text = "" }
            function onFocusCode() { codeField.forceActiveFocus() }
          }
          Keys.onPressed: function(event) {
            if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {
              root.submit(codeField.text)
              event.accepted = true
            } else if (event.key === Qt.Key_Escape) {
              root.close()
              event.accepted = true
            }
          }
        }

        Text {
          width: parent.width
          textFormat: Text.PlainText
          wrapMode: Text.WordWrap
          visible: root.noteKey !== ""
          text: root.noteKey !== "" ? strings.t(root.noteKey) : ""
          color: root.bar ? root.bar.foreground : Commons.Color.foreground
          font.family: root.bar ? root.bar.fontFamily : Style.font.family
          font.pixelSize: Style.font.bodySmall
        }

        Button {
          width: parent.width
          visible: root.phase === "pair" && root.pairing !== ""
          enabled: !root.busy
          text: strings.t("phone.pairButton")
          foreground: root.bar ? root.bar.foreground : Commons.Color.foreground
          onClicked: root.submit(codeField.text)
        }

        Button {
          width: parent.width
          visible: root.phase !== "looking" && root.phase !== "ready" && root.phase !== "paired"
          enabled: !root.busy
          text: strings.t("phone.lookButton")
          foreground: root.bar ? root.bar.foreground : Commons.Color.foreground
          onClicked: root.look()
        }
    }
  }
}
