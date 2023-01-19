from PyQt5 import QtWidgets


class Cell:
    def __init__(self, label):
        self.label: QtWidgets.QLabel = label
        self.voltage = None
        self.is_balancing = False

    def get_voltage(self):
        return -1 if self.voltage is None else self.voltage
