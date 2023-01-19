import os
import statistics
import sys

import paho.mqtt.client as mqtt
from PyQt5 import QtWidgets, QtCore

from cell import Cell
from custom_signal_window import CustomSignalWindow
from module import Module
from module_widget import ModuleWidget
from settings_dialog import SettingsDialog
from ui.mqtt_live import Ui_MainWindow
from utils_qt import exchange_widget_positions


class MqttLiveWindow(Ui_MainWindow):
    def __init__(self, parameters: dict):
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = CustomSignalWindow()
        self.setupUi(self.main_window)

        self.max_columns: int = int(parameters.get('max_columns', 4))

        self.row = 0
        self.column = 0
        self.modules: dict[str, Module] = {}
        self.spacer: dict = {}

        self.total_system_voltage: float = 0
        self.total_system_current: float = 0
        self.cell_min: float = 0

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.mqtt_on_connect
        self.mqtt_client.on_message = self.mqtt_on_message
        self.mqtt_client.username_pw_set(parameters['username'], parameters['password'])
        self.mqtt_client.connect(host=parameters['host'], port=1883, keepalive=60)

        self.mqtt_client.loop_start()

        QtCore.QTimer.singleShot(100, self.resize_window)

    def show(self):
        self.main_window.show()
        self.app.exec_()

    def resize_window(self):
        self.main_window.resize(0, 0)

    def module_drag_start(self, infos: dict):
        for identifier in self.modules:
            module = self.modules[identifier]
            if module.widget == infos['self']:
                self.mqtt_client.publish(f'esp-module/{module.get_topic()}/blink', 1)
                print(module.get_topic())
                break

    def module_dragged(self, infos: dict):
        exchange_widget_positions(self.gridLayout, infos['self'], infos['widget'])

    def sort_modules(self):
        for identifier in self.modules:
            self.modules[identifier].widget.setParent(None)
        self.row = 0
        self.column = 0
        for identifier in sorted(self.modules):
            if not self.modules[identifier].hidden:
                self.add_widget_to_grid(self.modules[identifier].widget)
        QtCore.QTimer.singleShot(100, self.resize_window)

    @staticmethod
    def mqtt_on_connect(client: mqtt.Client, userdata: any, flags: dict, rc: int):
        client.subscribe('esp-module/#')

    def add_widget(self, identifier: str):
        if identifier not in self.modules:
            module_widget = ModuleWidget(self.centralwidget)
            module_widget.setObjectName("Form")
            module_widget.on_drop.connect(self.module_dragged)
            module_widget.on_drag_start.connect(self.module_drag_start)
            # module_widget.resize(100, 100)
            vertical_layout = QtWidgets.QVBoxLayout(module_widget)
            vertical_layout.setObjectName("verticalLayout")
            label = QtWidgets.QLabel(module_widget)
            label.setObjectName("label")
            label.setText(identifier)
            font = label.font()
            font.setBold(True)
            label.setFont(font)
            vertical_layout.addWidget(label)
            module_temps = QtWidgets.QLabel(module_widget)
            module_temps.setText('-,-')
            vertical_layout.addWidget(module_temps)
            chip_temp = QtWidgets.QLabel(module_widget)
            chip_temp.setText('-')
            vertical_layout.addWidget(chip_temp)
            cells: dict[int, Cell] = {}
            for i in range(1, 13):
                cell_label = QtWidgets.QLabel(module_widget)
                cell_label.setObjectName("label")
                cell_label.setText(f'{i}:')
                vertical_layout.addWidget(cell_label)
                cells[i] = Cell(cell_label)
            self.add_widget_to_grid(module_widget)
            self.modules[identifier] = Module(identifier, module_widget, vertical_layout, label, cells, module_temps,
                                              chip_temp)

    def add_widget_to_grid(self, widget):
        if 'right' not in self.spacer:
            self.spacer['right'] = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding,
                                                         QtWidgets.QSizePolicy.Minimum)
            self.gridLayout.addItem(self.spacer['right'], 0, self.max_columns)
        if 'bottom' in self.spacer:
            self.gridLayout.removeItem(self.spacer['bottom'])
        self.spacer['bottom'] = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Minimum,
                                                      QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(self.spacer['bottom'], self.row + 1, 0)
        self.gridLayout.addWidget(widget, self.row, self.column)
        self.column += 1
        if self.column >= self.max_columns:
            self.row += 1
            self.column = 0

    def set_module_hidden(self, module: Module, value: bool):
        module.hidden = value
        QtCore.QTimer.singleShot(200, self.sort_modules)

    def set_widget(self, data: dict):
        module = self.modules[data['identifier']]
        if 'available' in data:
            self.set_module_hidden(module, module.update_available(data['available']))
        elif 'module_topic' in data:
            identifier = data['module_topic'][data['module_topic'].find('/') + 1:]
            if data['identifier'] != identifier and module.is_available():
                self.add_widget(identifier)
                self.modules[identifier].mac = data['identifier']
                module.number = int(identifier)
                module.header.setText(f"{data['identifier']} [{identifier}]")
                self.set_module_hidden(module, True)
        elif 'total_system_voltage' in data:
            self.total_system_voltage = float(data['total_system_voltage'])
            self.main_window.statusBar().showMessage(f'{self.total_system_voltage} V'
                                                     f', {self.total_system_current} A'
                                                     f', {self.total_system_voltage * self.total_system_current:.2f} W')
        elif 'total_system_current' in data:
            self.total_system_current = float(data['total_system_current'].split(',')[1]) * -1.0
            self.main_window.statusBar().showMessage(f'{self.total_system_voltage} V'
                                                     f', {self.total_system_current} A'
                                                     f', {self.total_system_voltage * self.total_system_current:.2f} W')
        elif 'module_temps' in data:
            module.module_temps.setText(data['module_temps'])
        elif 'chip_temp' in data:
            module.set_chip_temp(data['chip_temp'])
        elif 'voltage' in data:
            module.update_cell_voltage(data['number'], float(data['voltage']))
            module.color_median_voltage(self.cell_min + 0.01)
        elif 'is_balancing' in data:
            cell: Cell = module.cells[data['number']]
            cell.is_balancing = bool(int(data['is_balancing']))
            balancing_text = ' (+)' if cell.is_balancing else ''
            cell.label.setText(f"{data['number']}: {cell.get_voltage():.3f}{balancing_text}")

    def calc_cell_diff(self):
        voltages: list[float] = []
        for ident in self.modules:
            if self.modules[ident].hidden:
                continue
            for cell_number in self.modules[ident].cells:
                cell: Cell = self.modules[ident].cells[cell_number]
                if cell.voltage is not None:
                    voltages.append(cell.voltage)
        cell_max: float = max(voltages)
        self.cell_min: float = min(voltages)
        cell_diff: float = (cell_max - self.cell_min) * 1000
        cell_median: float = statistics.median(voltages)
        cell_mean: float = statistics.mean(voltages)
        self.main_window.setWindowTitle(f'{cell_diff:.0f} mV diff'
                                        f', {cell_median:.3f} V median'
                                        f', {cell_mean:.3f} V mean'
                                        f', {self.cell_min:.3f} V min'
                                        f', {cell_max:.3f} V max')

    def emit_signal_set_widget(self, identifier, topic, msg):
        data = {
            'identifier': identifier,
            topic: msg.payload.decode()
        }
        self.main_window.signal.emit({'func': self.set_widget, 'arg': data})

    def mqtt_on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage):
        topic = msg.topic[msg.topic.find('/') + 1:]
        identifier = topic[:topic.find('/')]
        self.main_window.signal.emit({'func': self.add_widget, 'arg': identifier})
        topic = topic[topic.find('/') + 1:]
        # print(identifier, topic)
        if topic == 'available':
            self.emit_signal_set_widget(identifier, topic, msg)
        elif topic == 'total_system_voltage':
            self.emit_signal_set_widget(identifier, topic, msg)
        elif topic == 'total_system_current':
            self.emit_signal_set_widget(identifier, topic, msg)
        elif topic == 'chip_temp':
            self.emit_signal_set_widget(identifier, topic, msg)
        elif topic == 'module_temps':
            self.emit_signal_set_widget(identifier, topic, msg)
        elif topic == 'module_topic':
            self.emit_signal_set_widget(identifier, topic, msg)
        elif topic == 'uptime' and identifier == '1':
            self.main_window.signal.emit({'func': self.calc_cell_diff})
        elif topic.startswith('cell/'):
            topic = topic[topic.find('/') + 1:]
            number = topic[:topic.find('/')]
            topic = topic[topic.find('/') + 1:]
            number = int(number)
            if topic == 'voltage':
                data = {
                    'identifier': identifier,
                    'number': number,
                    'voltage': msg.payload.decode()
                }
                self.main_window.signal.emit({'func': self.set_widget, 'arg': data})
            elif topic == 'is_balancing':
                data = {
                    'identifier': identifier,
                    'number': number,
                    'is_balancing': msg.payload.decode()
                }
                self.main_window.signal.emit({'func': self.set_widget, 'arg': data})


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))

    app = QtWidgets.QApplication(sys.argv)
    default_params = {
        'host': '',
        'username': '',
        'password': '',
        'max_columns': 4,
    }
    parameters_file: str = 'mqtt_live.yaml'
    settings_dialog = SettingsDialog(default_params, parameters_file)
    if settings_dialog.result == 1:
        main_window = MqttLiveWindow(settings_dialog.configuration)
        main_window.show()
