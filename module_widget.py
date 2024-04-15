from PyQt6 import QtGui, QtWidgets

from drag_widget import DragWidget


class ModuleWidget(DragWidget):
    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.last_style_sheet: str = ''

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent) -> None:
        if a0.source() is self:
            return
        self.last_style_sheet = self.styleSheet()
        self.setStyleSheet('background-color: brown;')
        a0.accept()

    def dragLeaveEvent(self, a0: QtGui.QDragLeaveEvent) -> None:
        self.setStyleSheet(self.last_style_sheet)

    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        super(ModuleWidget, self).dropEvent(a0)
        self.setStyleSheet(self.last_style_sheet)
