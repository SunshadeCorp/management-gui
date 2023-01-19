import statistics

from PyQt5 import QtWidgets

from cell import Cell


class Module:
    def __init__(self, identifier, widget, layout, header, cells, module_temps, chip_temp):
        self.identifier = identifier
        self.widget: QtWidgets.QWidget = widget
        self.layout = layout
        self.header: QtWidgets.QLabel = header
        self.cells: dict[int, Cell] = cells
        self.module_temps: QtWidgets.QLabel = module_temps
        self.chip_temp: QtWidgets.QLabel = chip_temp
        self.mac = None
        self.hidden = False
        self.number = None
        self.available = None
        self.median_voltage: float = 0.0

    def get_topic(self):
        if self.mac is not None:
            return self.mac
        else:
            return self.identifier

    def get_title(self):
        return self.identifier if self.number is None else f'{self.identifier} [{self.number}]'

    def get_median_voltage(self) -> float:
        voltages: list[float] = []
        for cell_number in self.cells:
            if self.cells[cell_number].voltage is not None:
                voltages.append(self.cells[cell_number].voltage)
        return statistics.median(voltages)

    def is_available(self) -> bool:
        if self.available is None:
            return True
        elif self.available == 'online':
            return True
        elif self.available == 'undefined':
            return True
        return False

    def update_available(self, value: str) -> bool:
        self.available = value
        if value == 'online':
            self.widget.setStyleSheet('')
            return False
        elif value == 'offline':
            self.widget.setStyleSheet('background-color: grey;')
        elif value == 'undefined':
            self.widget.setStyleSheet('background-color: #cccccc;')
        return True

    def update_cell_voltage(self, number: int, voltage: float):
        cell: Cell = self.cells[number]
        cell.voltage = voltage
        balancing_text = ' (+)' if cell.is_balancing else ''
        cell.label.setText(f"{number}: {voltage}{balancing_text}")
        self.median_voltage: float = self.get_median_voltage()
        self.header.setText(f'{self.get_title()}: {self.median_voltage:.3f}')
        for cell_number in self.cells:
            current_cell = self.cells[cell_number]
            if current_cell.voltage is not None:
                if current_cell.voltage - self.median_voltage >= 0.01:
                    current_cell.label.setStyleSheet('background-color: #ff5c33;')
                elif current_cell.voltage - self.median_voltage <= -0.01:
                    current_cell.label.setStyleSheet('background-color: #3399ff;')
                else:
                    current_cell.label.setStyleSheet('')

    def color_median_voltage(self, min_voltage: float):
        if self.median_voltage > min_voltage:
            self.header.setStyleSheet('background-color: #ff5c33;')
        else:
            self.header.setStyleSheet('')

    def set_chip_temp(self, value: str):
        chip_temp: float = float(value)
        self.chip_temp.setText(f'{chip_temp:.2f} °C')
        if chip_temp >= 50.0:
            self.chip_temp.setStyleSheet('background-color: #ffff80;')
        elif chip_temp >= 60.0:
            self.chip_temp.setStyleSheet('background-color: #ffb366;')
        else:
            self.chip_temp.setStyleSheet('')
