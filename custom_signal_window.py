from PyQt6 import QtCore
from PyQt6.QtWidgets import QMainWindow


class CustomSignalWindow(QMainWindow):
    signal = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.signal.connect(self.signaling)

    def event(self, event: QtCore.QEvent) -> bool:
        if event.type() == event.Type.StatusTip:
            return True
        return super().event(event)

    @staticmethod
    def signaling(work: dict):
        if 'arg' in work:
            work['func'](work['arg'])
        else:
            work['func']()
