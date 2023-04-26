import copy
import hashlib
import sys
from pathlib import Path

import yaml
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QComboBox, QDialog, QLabel, QLineEdit, QWidget

from ui.settings import Ui_Dialog
from utils import get_config_local, save_config_local


class SettingsDialog(Ui_Dialog):
    def __init__(self, configuration: dict[str, str], config_file: str = ''):
        self.dialog = QDialog(None, QtCore.Qt.WindowCloseButtonHint)
        self.setupUi(self.dialog)

        self.defaults = configuration
        self.configuration = copy.deepcopy(self.defaults)
        self.save_file = {'last_used': ''}

        if len(config_file) > 0:
            save_file: dict = get_config_local(Path(config_file))
            if 'error' not in save_file and 'last_used' in save_file:
                self.save_file = save_file
                self.configuration = copy.deepcopy(self.save_file[self.save_file['last_used']])

        self.widgets: dict[str, QWidget] = {}

        spacer = self.gridLayout.itemAtPosition(0, 0)
        self.gridLayout.removeItem(spacer)
        self.gridLayout.removeWidget(self.buttonBox)
        if len(config_file) > 0:
            self.combo_box = QComboBox()
            for save in self.save_file:
                if save != 'last_used':
                    self.combo_box.addItem(save)
            self.combo_box.setCurrentText(self.save_file['last_used'])
            self.combo_box.currentTextChanged['QString'].connect(self.combo_box_changed)
            self.gridLayout.addWidget(self.combo_box, 0, 0, 1, 2)
        for i, key in enumerate(self.defaults):
            self.gridLayout.addWidget(QLabel(f'{key}:'), i + 1, 0)
            self.widgets[key] = QLineEdit(str(self.configuration.get(key, self.defaults[key])))
            self.gridLayout.addWidget(self.widgets[key], i + 1, 1)
        self.gridLayout.addItem(spacer, len(self.configuration) + 1, 0, 1, 2)
        self.gridLayout.addWidget(self.buttonBox, len(self.configuration) + 2, 0, 1, 2)

        self.result = self.dialog.exec_()
        if self.result == 1:
            for key in self.widgets:
                widget: QWidget = self.widgets[key]
                if isinstance(widget, QLineEdit):
                    self.configuration[key] = widget.text()
            if len(config_file) > 0:
                h = hashlib.new('sha1')
                h.update(yaml.dump(self.configuration, default_flow_style=False, sort_keys=True).encode())
                config_hash = h.hexdigest()
                if self.save_file['last_used'] == config_hash:
                    return
                if config_hash not in self.save_file:
                    self.save_file[config_hash] = self.configuration
                self.save_file['last_used'] = config_hash
                save_config_local(Path(config_file), self.save_file)

    def combo_box_changed(self, value: str):
        self.configuration = copy.deepcopy(self.save_file[value])
        for key in self.widgets:
            widget: QWidget = self.widgets[key]
            if isinstance(widget, QLineEdit):
                widget.setText(str(self.configuration.get(key, self.defaults[key])))


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    print(SettingsDialog({'Test1': 'lol', 'test2': 123}).result)
