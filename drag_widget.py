from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt


class DragWidget(QtWidgets.QWidget):
    on_drop = QtCore.Signal(dict)
    on_drag_start = QtCore.Signal(dict)
    on_drag_end = QtCore.Signal(dict)

    def __init__(self, parent: QtWidgets.QWidget):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, a0: QtGui.QDragEnterEvent) -> None:
        a0.accept()

    def drag_end_event(self):
        self.on_drag_end.emit({'self': self})

    def dropEvent(self, a0: QtGui.QDropEvent) -> None:
        self.on_drop.emit({'self': self, 'widget': a0.source()})

    def mouseMoveEvent(self, a0: QtGui.QMouseEvent) -> None:
        if a0.buttons() == Qt.MouseButton.LeftButton:
            drag = QtGui.QDrag(self)
            mime = QtCore.QMimeData()
            drag.setMimeData(mime)
            drag.destroyed.connect(self.drag_end_event)
            pixmap = QtGui.QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            self.on_drag_start.emit({'self': self})
            drag.exec(Qt.DropAction.MoveAction)

    def paintEvent(self, a0: QtGui.QPaintEvent) -> None:
        o = QtWidgets.QStyleOption()
        o.initFrom(self)
        p = QtGui.QPainter(self)
        self.style().drawPrimitive(QtWidgets.QStyle.PrimitiveElement.PE_Widget, o, p, self)
