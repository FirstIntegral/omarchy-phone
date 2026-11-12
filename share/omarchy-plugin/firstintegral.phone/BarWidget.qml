import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// One tap opens the card. A trusted phone opens the mirror. A refused key
// stays on the card so the code is typed there.
// The mark is drawn here. The plugin directory must be a real directory.
// A symlink out of ~/.config/omarchy hides the other QML files.
BarWidget {
  id: root
  moduleName: "firstintegral.phone"

  readonly property bool opened: panel.opened

  function close() { panel.close() }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

  PhonePanel {
    id: panel
    width: 0
    height: 0
    bar: root.bar
    anchorItem: button
    hostWidget: root
  }

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    // Empty text hides the button. The space is not drawn.
    text: " "
    labelVisible: false
    keepSpace: true
    fixedWidth: bar ? bar.barSize : 28
    tooltipText: strings.t("phone.tooltip")
    onPressed: function(mouseButton) {
      if (!root.bar || mouseButton !== Qt.LeftButton) return
      console.log("phone: tap")
      panel.toggle()
    }

    Item {
      anchors.centerIn: parent
      width: 11
      height: 17

      Rectangle {
        anchors.fill: parent
        radius: 3
        color: "transparent"
        border.width: 1.25
        border.color: button.foreground
        antialiasing: true
      }

      Rectangle {
        width: 4
        height: 1.25
        radius: 1
        color: button.foreground
        antialiasing: true
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 2.25
      }
    }
  }
}
