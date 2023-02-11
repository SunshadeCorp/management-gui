import statistics
import time

import paho.mqtt.client as mqtt
from PyQt5 import QtWidgets

from cell import Cell
from module_widget import ModuleWidget
from utils_qt import exchange_widget_positions


class Module:
    TOPICS: list = [
        'available',
        'build_timestamp',
        'chip_temp',
        'module_temps',
        'module_topic',
        'module_voltage',
        'pec15_error_count',
        'total_system_current',
        'total_system_voltage',
        'uptime'
    ]

    def __init__(self, identifier: str, parent: QtWidgets.QWidget, grid_layout: QtWidgets.QGridLayout,
                 mqtt_client: mqtt.Client):
        self.identifier = identifier
        self.grid_layout = grid_layout
        self.mqtt_client = mqtt_client
        self.mac = None
        self.hidden = False
        self.number = None
        self.available = None
        self.module_voltage: float = 0.0
        self.cell_median_voltage: float = 0.0
        self.cell_sum_voltage: float = 0.0
        self.uptime: int = 0
        self.last_uptime: float = time.time()

        self.widget: ModuleWidget = ModuleWidget(parent)
        self.widget.on_drop.connect(self.module_dragged)
        self.widget.on_drag_start.connect(self.drag_start)
        self.layout = QtWidgets.QVBoxLayout(self.widget)
        self.header: QtWidgets.QLabel = QtWidgets.QLabel(identifier, self.widget)
        font = self.header.font()
        font.setBold(True)
        self.header.setFont(font)
        self.layout.addWidget(self.header)
        self.module_temps: QtWidgets.QLabel = self.add_label('-,-')
        self.chip_temp = self.add_label('-')
        self.cells: dict[int, Cell] = {}
        for i in range(1, 13):
            self.cells[i] = Cell(self.add_label(f'{i}:'))
        self.module_voltage_label = self.add_label('-')
        self.uptime_label = self.add_label('-')
        self.pec15_label = self.add_label('-')
        self.build_timestamp_label = self.add_label('-')

    def add_label(self, text: str) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(text, self.widget)
        self.layout.addWidget(label)
        return label

    def is_mac(self) -> bool:
        return len(self.identifier) == 12

    def restart(self):
        self.mqtt_client.publish(f'esp-module/{self.identifier}/restart', 1)

    def drag_start(self, infos: dict):
        self.mqtt_client.publish(f'esp-module/{self.get_topic()}/blink', 1)
        print(self.get_topic())

    def module_dragged(self, infos: dict):
        exchange_widget_positions(self.grid_layout, self.widget, infos['widget'])

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

    def calc_voltage(self) -> float:
        return sum(self.cells[cell_number].voltage for cell_number in self.cells if
                   self.cells[cell_number].voltage is not None)

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
            self.widget.setStyleSheet('background-color: #cccccc; color: #404040;')
        return True

    def refresh_cell_text(self, number: int):
        cell: Cell = self.cells[number]
        balancing_text = ' (+)' if cell.is_balancing else ''
        accurate_text = f' [{cell.accurate_voltage:.3f}]' if cell.accurate_voltage is not None else ''
        cell.label.setText(f"{number}: {cell.voltage:.3f}{accurate_text}{balancing_text}")

    def update_cell_voltage(self, number: int, voltage: float):
        self.cells[number].voltage = voltage
        self.refresh_cell_text(number)
        self.cell_median_voltage: float = self.get_median_voltage()
        self.header.setText(f'{self.get_title()}: {self.cell_median_voltage:.3f}')
        for cell_number in self.cells:
            current_cell = self.cells[cell_number]
            if current_cell.voltage is not None:
                if current_cell.voltage - self.cell_median_voltage >= 0.01:
                    current_cell.label.setStyleSheet('background-color: #ff5c33;')
                elif current_cell.voltage - self.cell_median_voltage <= -0.01:
                    current_cell.label.setStyleSheet('background-color: #3399ff;')
                else:
                    current_cell.label.setStyleSheet('')

    def color_median_voltage(self, min_voltage: float):
        if self.cell_median_voltage > min_voltage:
            self.header.setStyleSheet('background-color: #ff5c33;')
        else:
            self.header.setStyleSheet('')

    def update_chip_temp(self, value: str):
        chip_temp: float = float(value)
        self.chip_temp.setText(f'{chip_temp:.2f} °C')
        if chip_temp >= 60.0:
            self.chip_temp.setStyleSheet('background-color: #ffb366;')
        elif chip_temp >= 50.0:
            self.chip_temp.setStyleSheet('background-color: #ffff80; color: #404040;')
        else:
            self.chip_temp.setStyleSheet('')

    def update_voltage(self, value: str):
        self.module_voltage: float = float(value)
        self.cell_sum_voltage: float = self.calc_voltage()
        diff: float = abs(self.module_voltage - self.cell_sum_voltage)
        if diff > 0.1:
            self.module_voltage_label.setStyleSheet('background-color: #ff3300;')
        elif diff > 0.05:
            self.module_voltage_label.setStyleSheet('background-color: #ff8566;')
        elif diff > 0.02:
            self.module_voltage_label.setStyleSheet('background-color: #ffb366;')
        elif diff > 0.01:
            self.module_voltage_label.setStyleSheet('background-color: #ffff80; color: #404040;')
        else:
            self.module_voltage_label.setStyleSheet('')
        self.module_voltage_label.setText(f"{self.module_voltage:.2f}, {self.cell_sum_voltage:.3f}, {diff:.3f}")

    def update_uptime(self, uptime: int):
        self.uptime = uptime
        self.last_uptime = time.time()
        self.uptime_label.setText(f'{self.uptime}')
        if self.available == 'online':
            self.widget.setStyleSheet('')

    def update_pec15(self, pec15: int):
        self.pec15_label.setText(f'pec15: {pec15}')

    def check_uptime(self):
        if self.available == 'online':
            if time.time() - self.last_uptime > 3:
                self.widget.setStyleSheet('background-color: #ff8c1a;')
