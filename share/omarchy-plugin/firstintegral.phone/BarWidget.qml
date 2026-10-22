import QtQuick
import qs.Ui

// One tap does what Super+Shift+H does: focus the phone window, or open it.
// The mark is drawn here. A second QML file is invisible to the shell when
// the plugin directory is a symlink out of ~/.config/omarchy.
BarWidget {
  id: root
  moduleName: "firstintegral.phone"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    // Empty text hides the button. The space is not drawn.
    text: " "
    labelVisible: false
    keepSpace: true
    fixedWidth: bar ? bar.barSize : 28
    tooltipText: "Phone. Super+drag moves the window."
    onPressed: function(mouseButton) {
      if (!root.bar || mouseButton !== Qt.LeftButton) return
      root.bar.run("omarchy-launch-or-focus 'Omarchy Phone' 'uwsm-app -- omarchy-phone'")
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
