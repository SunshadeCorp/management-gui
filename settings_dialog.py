import sys

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QDialog, QLabel, QLineEdit

from ui.settings import Ui_Dialog


class SettingsDialog(Ui_Dialog):
    def __init__(self, configuration: dict[str, str]):
        self.dialog = QDialog(None, QtCore.Qt.WindowCloseButtonHint)
        self.setupUi(self.dialog)

        line_edits: dict[str, QLineEdit] = {}

        spacer = self.gridLayout.itemAtPosition(0, 0)
        self.gridLayout.removeItem(spacer)
        self.gridLayout.removeWidget(self.buttonBox)
        for i, key in enumerate(configuration):
            self.gridLayout.addWidget(QLabel(f'{key}:'), i, 0)
            line_edits[key] = QLineEdit(str(configuration[key]))
            self.gridLayout.addWidget(line_edits[key], i, 1)
        self.gridLayout.addItem(spacer, len(configuration), 0, 1, 2)
        self.gridLayout.addWidget(self.buttonBox, len(configuration) + 1, 0, 1, 2)

        self.result = self.dialog.exec_()
        if self.result == 1:
            for key in line_edits:
                configuration[key] = line_edits[key].text()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    print(SettingsDialog({'Test1': 'lol', 'test2': 123}).result)
