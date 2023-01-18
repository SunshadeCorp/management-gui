import os
import statistics
import sys

import paho.mqtt.client as mqtt
from PyQt5 import QtWidgets, QtCore, QtGui

from custom_signal_window import CustomSignalWindow
from drag_widget import DragWidget
from settings_dialog import SettingsDialog
from ui.mqtt_live import Ui_MainWindow
from utils_qt import exchange_widget_positions


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


class MqttLiveWindow(Ui_MainWindow):
    def __init__(self, parameters: dict):
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = CustomSignalWindow()
        self.setupUi(self.main_window)

        self.max_columns: int = int(parameters.get('max_columns', 4))

        self.row = 0
        self.column = 0
        self.modules: dict = {}
        self.spacer: dict = {}

        self.total_system_voltage: float = 0
        self.total_system_current: float = 0

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.mqtt_on_connect
        self.mqtt_client.on_message = self.mqtt_on_message
        self.mqtt_client.username_pw_set(parameters['username'], parameters['password'])
        self.mqtt_client.connect(host=parameters['host'], port=1883, keepalive=60)

        self.mqtt_client.loop_start()

        QtCore.QTimer.singleShot(100, self.resize_window)
        # QtCore.QTimer.singleShot(1000, self.sort_modules)

    def show(self):
        self.main_window.show()
        self.app.exec_()

    def resize_window(self):
        self.main_window.resize(0, 0)

    def module_drag_start(self, infos: dict):
        for identifier in self.modules:
            if self.modules[identifier]['widget'] == infos['self']:
                self.mqtt_client.publish(f'esp-module/{identifier}/blink', 1)
                break

    def module_dragged(self, infos: dict):
        exchange_widget_positions(self.gridLayout, infos['self'], infos['widget'])

    def sort_modules(self):
        for i in enumerate(list(self.modules.keys())):
            print(i)
        for identifier1 in self.modules:
            for identifier2 in reversed(self.modules):
                if identifier2 > identifier1:
                    exchange_widget_positions(self.gridLayout,
                                              self.modules[identifier1]['widget'],
                                              self.modules[identifier2]['widget'])
        for identifier1 in self.modules:
            for identifier2 in reversed(self.modules):
                if identifier2 > identifier1:
                    exchange_widget_positions(self.gridLayout,
                                              self.modules[identifier1]['widget'],
                                              self.modules[identifier2]['widget'])

    @staticmethod
    def mqtt_on_connect(client: mqtt.Client, userdata: any, flags: dict, rc: int):
        client.subscribe('esp-module/#')

    def add_widget(self, identifier: str):
        if identifier not in self.modules:
            module = ModuleWidget(self.centralwidget)
            module.setObjectName("Form")
            module.on_drop.connect(self.module_dragged)
            module.on_drag_start.connect(self.module_drag_start)
            # module.resize(100, 100)
            vertical_layout = QtWidgets.QVBoxLayout(module)
            vertical_layout.setObjectName("verticalLayout")
            label = QtWidgets.QLabel(module)
            label.setObjectName("label")
            label.setText(identifier)
            font = label.font()
            font.setBold(True)
            label.setFont(font)
            vertical_layout.addWidget(label)
            module_temps = QtWidgets.QLabel(module)
            module_temps.setText('-,-')
            vertical_layout.addWidget(module_temps)
            chip_temp = QtWidgets.QLabel(module)
            chip_temp.setText('-')
            vertical_layout.addWidget(chip_temp)
            cells: dict = {}
            for i in range(1, 13):
                cell = QtWidgets.QLabel(module)
                cell.setObjectName("label")
                cell.setText(f'{i}:')
                vertical_layout.addWidget(cell)
                cells[i] = {
                    'widget': cell,
                }
            self.gridLayout.addWidget(module, self.row, self.column)
            if 'right' not in self.spacer:
                self.spacer['right'] = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding,
                                                             QtWidgets.QSizePolicy.Minimum)
                self.gridLayout.addItem(self.spacer['right'], 0, self.max_columns)
            if 'bottom' in self.spacer:
                self.gridLayout.removeItem(self.spacer['bottom'])
            self.spacer['bottom'] = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Minimum,
                                                          QtWidgets.QSizePolicy.Expanding)
            self.gridLayout.addItem(self.spacer['bottom'], self.row + 1, 0)
            self.column += 1
            if self.column >= self.max_columns:
                self.row += 1
                self.column = 0
            self.modules[identifier] = {
                'widget': module,
                'layout': vertical_layout,
                'header': label,
                'cells': cells,
                'module_temps': module_temps,
                'chip_temp': chip_temp
            }

    def set_widget(self, data: dict):
        module = self.modules[data['identifier']]
        if 'available' in data:
            if data['available'] == 'offline':
                widget: QtWidgets.QWidget = module['widget']
                widget.setStyleSheet('background-color: grey;')
            if data['available'] == 'online':
                widget: QtWidgets.QWidget = module['widget']
                widget.setStyleSheet('')
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
            module['module_temps'].setText(data['module_temps'])
        elif 'chip_temp' in data:
            module['chip_temp'].setText(data['chip_temp'])
        elif 'voltage' in data:
            voltage: float = float(data['voltage'])
            module['cells'][data['number']]['voltage'] = voltage
            cell: QtWidgets.QLabel = module['cells'][data['number']]['widget']
            balancing_text = ' (+)' if module['cells'][data['number']].get('is_balancing', False) else ''
            cell.setText(f"{data['number']}: {data['voltage']}{balancing_text}")
            voltages: list[float] = []
            for cell_number in module['cells']:
                module['cells'][cell_number]['widget'].setStyleSheet('')
                if 'voltage' in module['cells'][cell_number]:
                    voltages.append(module['cells'][cell_number]['voltage'])
            cell.setStyleSheet('background-color: green;')
            median_voltage: float = statistics.median(voltages)
            module['header'].setText(f"{data['identifier']}: {median_voltage:.3f}")
            for cell_number in module['cells']:
                if 'voltage' in module['cells'][cell_number]:
                    if module['cells'][cell_number]['voltage'] - median_voltage >= 0.01:
                        module['cells'][cell_number]['widget'].setStyleSheet('background-color: #ff5c33;')
                    elif module['cells'][cell_number]['voltage'] - median_voltage <= -0.01:
                        module['cells'][cell_number]['widget'].setStyleSheet('background-color: #3399ff;')
                    else:
                        module['cells'][cell_number]['widget'].setStyleSheet('')
        elif 'is_balancing' in data:
            is_balancing: bool = bool(int(data['is_balancing']))
            cell: dict = module['cells'][data['number']]
            cell['is_balancing'] = is_balancing
            balancing_text = ' (+)' if is_balancing else ''
            cell['widget'].setText(f"{data['number']}: {cell.get('voltage', -1):.3f}{balancing_text}")

    def calc_cell_diff(self):
        voltages: list[float] = []
        for ident in self.modules:
            if len(ident) > 2:
                continue
            for cell_number in self.modules[ident]['cells']:
                cell: dict = self.modules[ident]['cells'][cell_number]
                if 'voltage' in cell:
                    voltages.append(cell['voltage'])
        cell_max: float = max(voltages)
        cell_min: float = min(voltages)
        cell_diff: float = (cell_max - cell_min) * 1000
        cell_median: float = statistics.median(voltages)
        cell_mean: float = statistics.mean(voltages)
        self.main_window.setWindowTitle(f'{cell_diff:.0f} mV diff'
                                        f', {cell_median:.3f} V median'
                                        f', {cell_mean:.3f} V mean'
                                        f', {cell_min:.3f} V min'
                                        f', {cell_max:.3f} V max')

    def mqtt_on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage):
        topic = msg.topic[msg.topic.find('/') + 1:]
        identifier = topic[:topic.find('/')]
        if len(identifier) > 2:
            return
        self.main_window.signal.emit({'func': self.add_widget, 'arg': identifier})
        topic = topic[topic.find('/') + 1:]
        # print(identifier, topic)
        if topic == 'available':
            data = {
                'identifier': identifier,
                'available': msg.payload.decode()
            }
            self.main_window.signal.emit({'func': self.set_widget, 'arg': data})
        elif topic == 'total_system_voltage':
            data = {
                'identifier': identifier,
                'total_system_voltage': msg.payload.decode()
            }
            self.main_window.signal.emit({'func': self.set_widget, 'arg': data})
        elif topic == 'total_system_current':
            data = {
                'identifier': identifier,
                'total_system_current': msg.payload.decode()
            }
            self.main_window.signal.emit({'func': self.set_widget, 'arg': data})
        elif topic == 'chip_temp':
            data = {
                'identifier': identifier,
                'chip_temp': msg.payload.decode()
            }
            self.main_window.signal.emit({'func': self.set_widget, 'arg': data})
        elif topic == 'module_temps':
            data = {
                'identifier': identifier,
                'module_temps': msg.payload.decode()
            }
            self.main_window.signal.emit({'func': self.set_widget, 'arg': data})
        elif topic == 'module_topic':
            pass
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
