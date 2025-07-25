import os
import statistics
import sys
import threading
from pathlib import Path

import paho.mqtt.client as mqtt
import qdarktheme
import yaml
from fabric import Connection
from PyQt6 import QtCore, QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QCloseEvent
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout, QWidgetItem

from cell import Cell
from custom_signal_window import CustomSignalWindow
from module import Module
from module_widget import ModuleWidget
from settings_dialog import SettingsDialog
from ui.mqtt_live import Ui_MainWindow
from utils import get_config_local, get_yaml_file, put_file_sudo


class MqttLiveWindow(Ui_MainWindow):
    SETTINGS_FILE: str = 'mqtt_live.yaml'
    DEFAULT_SETTINGS: dict = {
        'host': '127.0.0.1',
        'username': '',
        'password': '',
        'max_columns': 6,
        'show_hidden': 0,
        'hide_modules': 'none',
        'auto_resize': 1,
        'mqtt_prefix': '',
        'ota_file': 'firmware.bin'
    }
    CELL_TOPICS: list = [
        'voltage',
        'is_balancing'
    ]

    def __init__(self, parameters: dict, as_app=True):
        self.as_app = as_app
        if self.as_app:
            self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = CustomSignalWindow()
        self.main_window.closeEvent = self.close_event
        self.setupUi(self.main_window)

        self.actionread_accurate_all.triggered.connect(self.read_accurate_all)
        self.actionbalancing_enabled.triggered.connect(self.switch_balancing_enabled)
        self.actionrestart_all.triggered.connect(self.restart_all)
        self.actiondelete_offline.triggered.connect(self.delete_offline)
        self.actiondelete_no_slave_mapping.triggered.connect(self.delete_no_slave_mapping)
        self.actionota_update_all.triggered.connect(self.ota_update_all)
        self.actionreset_can_limits.triggered.connect(self.reset_can_limits)
        self.actiongenerate_slave_mapping.triggered.connect(self.generate_slave_mapping)

        self.actionhidden.triggered.connect(self.show_hidden_clicked)
        self.actionuptime.triggered.connect(self.update_modules)
        self.actionbuild_timestamp.triggered.connect(self.update_modules)
        self.actionauto_resize.triggered.connect(self.auto_resize_clicked)
        self.actiondark_mode.triggered.connect(self.switch_dark_mode)

        self.max_columns: int = int(parameters.get('max_columns', 4))
        self.show_hidden: bool = bool(int(parameters.get('show_hidden', 0)) == 1)
        self.auto_resize: bool = bool(int(parameters.get('auto_resize', 0)) == 1)
        self.actionhidden.setChecked(self.show_hidden)
        self.actionauto_resize.setChecked(self.auto_resize)

        self.canBox.hide()

        self.hide_modules: set[str] = set()
        hide_modules = parameters.get('hide_modules', self.DEFAULT_SETTINGS['hide_modules'])
        if hide_modules != '' and hide_modules.lower() != 'none':
            modules: list[str] = hide_modules.split(',')
            self.hide_modules: set[str] = set(modules)

        self.row = 0
        self.column = 0
        self.modules: dict[str, Module] = {}
        self.spacer: dict = {}

        self.total_system_voltage: float = 0
        self.total_system_current: float = 0
        self.cell_min: float = 0

        self.mqtt_prefix: str = parameters.get('mqtt_prefix', '')
        if len(self.mqtt_prefix) > 0 and not self.mqtt_prefix.endswith('/'):
            self.mqtt_prefix = f'{self.mqtt_prefix}/'
        self.mqtt_host = parameters['host']
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.mqtt_on_connect
        self.mqtt_client.on_message = self.mqtt_on_message
        self.mqtt_client.username_pw_set(parameters['username'], parameters['password'])
        self.mqtt_client.connect_async(host=self.mqtt_host, port=1883, keepalive=60)

        self.mqtt_client.loop_start()

        self.ota_file = parameters.get('ota_file', self.DEFAULT_SETTINGS['ota_file'])

        timer = QtCore.QTimer(self.main_window)
        timer.timeout.connect(self.timer_work)
        timer.start(1000)

    def show(self):
        self.main_window.show()
        if self.as_app:
            sys.exit(self.app.exec())

    def close_event(self, a0: QCloseEvent) -> None:
        self.mqtt_client.loop_stop()
        a0.accept()

    def read_accurate_all(self):
        for identifier in self.modules:
            self.mqtt_client.publish(f'esp-module/{identifier}/read_accurate', payload='1')

    def switch_balancing_enabled(self):
        value: str = str(self.actionbalancing_enabled.isChecked()).lower()
        self.mqtt_client.publish('master/core/config/balancing_enabled/set', payload=value, retain=True)

    def delete_module(self, identifier: str):
        topics = [
            'accurate/module_voltage',
            'accurate/module_temps',
            'accurate/chip_temp',
            'auto_detect_battery_type',
            'available',
            'battery_type',
            'bms_mode',
            'build_timestamp',
            'chip_temp',
            'cpu',
            'esp_sdk',
            'flash',
            'ip',
            'module_temps',
            'module_topic',
            'module_voltage',
            'ota_start',
            'ota_url',
            'pec15_error_count',
            'total_system_voltage',
            'uptime',
            'version',
            'wifi',
        ]
        for i in range(1, 13):
            for cell_topic in self.CELL_TOPICS:
                topics.append(f'accurate/cell/{i}/{cell_topic}')
                topics.append(f'cell/{i}/{cell_topic}')
        for topic in topics:
            self.mqtt_client.publish(f'esp-module/{identifier}/{topic}', retain=True)

    def delete_offline(self):
        for identifier in self.modules:
            if self.modules[identifier].available == 'offline':
                self.delete_module(identifier)

    def delete_no_slave_mapping(self):
        config: dict = get_config_local(Path('config.yaml'))
        if 'error' in config:
            print(config)
            return
        c = Connection(host=config['host'], user=config['user'], connect_kwargs={'password': config['password']})
        file = get_yaml_file(c, '/docker/easybms-master/slave_mapping.yaml')
        for identifier in self.modules:
            if len(identifier) != 12:
                continue
            if identifier not in file['slaves']:
                self.delete_module(identifier)

    def find_module_by_item(self, item: QWidgetItem):
        if not item:
            return None
        module_widget = item.widget()
        if not module_widget:
            return None
        if not isinstance(module_widget, ModuleWidget):
            return None
        for identifier in self.modules:
            widget = self.modules[identifier].widget
            if widget == module_widget:
                return self.modules[identifier]
        return None

    def generate_slave_mapping(self):
        comments: str = ''
        mapping: dict = {'slaves': {}}
        counter: int = 1
        for row in range(self.moduleBoxLayout.rowCount()):
            for col in range(self.moduleBoxLayout.columnCount()):
                item = self.moduleBoxLayout.itemAtPosition(row, col)
                module = self.find_module_by_item(item)
                if module:
                    if module.is_mac() or module.mac is not None:
                        mapping['slaves'][module.get_topic()] = {'number': counter}
                    else:
                        comments += f'# {module.identifier} not found!\n'
                    counter += 1
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        dialog.resize(600, 450)
        dialog.setWindowTitle("slave_mapping.yaml")
        layout = QVBoxLayout(dialog)
        textbox = QTextEdit(dialog)
        textbox.setText(comments + yaml.dump(mapping, default_flow_style=False, sort_keys=False))
        layout.addWidget(textbox)
        button_layout = QHBoxLayout()
        button_yaml = QPushButton("Set yaml", dialog)
        button_layout.addWidget(button_yaml)

        button_restart = QPushButton("Restart master", dialog)
        button_layout.addWidget(button_restart)
        layout.addLayout(button_layout)

        def set_slave_mapping(content: str):
            config = get_config_local(Path('config.yaml'))
            with Connection(host=config['host'], user=config['user'],
                            connect_kwargs={'password': config['password']}) as c:
                put_file_sudo(c, content, '/docker/easybms-master/slave_mapping.yaml')
            self.main_window.signal.emit({'func': button_yaml.setEnabled, 'arg': True})
            self.main_window.signal.emit({'func': button_yaml.setText, 'arg': 'Done.'})

        def set_yaml_button():
            button_yaml.setEnabled(False)
            button_yaml.setText('...')
            threading.Thread(target=set_slave_mapping, args=(textbox.toPlainText(),), daemon=True).start()

        button_yaml.clicked.connect(set_yaml_button)

        def restart_master():
            config = get_config_local(Path('config.yaml'))
            with Connection(host=config['host'], user=config['user'],
                            connect_kwargs={'password': config['password']}) as c:
                c.sudo('docker-compose -f /docker/docker-compose.yml restart easybms-master')
            self.main_window.signal.emit({'func': button_restart.setEnabled, 'arg': True})
            self.main_window.signal.emit({'func': button_restart.setText, 'arg': 'Done.'})

        def restart_button():
            button_restart.setEnabled(False)
            button_restart.setText('...')
            threading.Thread(target=restart_master, daemon=True).start()

        button_restart.clicked.connect(restart_button)

        dialog.exec()

    def ota_update_all(self):
        for identifier in self.modules:
            if len(identifier) != 12:
                continue
            self.mqtt_client.publish(f'esp-module/{identifier}/ota', payload=self.ota_file)

    def reset_can_limits(self):
        self.mqtt_client.publish('master/can/limits/max_charge_current/reset', payload='1')
        self.mqtt_client.publish('master/can/limits/max_discharge_current/reset', payload='1')
        self.mqtt_client.publish('master/can/limits/max_voltage/reset', payload='1')
        self.mqtt_client.publish('master/can/limits/min_voltage/reset', payload='1')

    def show_hidden_clicked(self):
        self.show_hidden = not self.show_hidden
        self.sort_modules()

    def auto_resize_clicked(self):
        self.auto_resize = not self.auto_resize
        self.sort_modules()

    def switch_dark_mode(self):
        qdarktheme.setup_theme("dark" if self.actiondark_mode.isChecked() else "light")

    def update_modules(self):
        for identifier in self.modules:
            module = self.modules[identifier]
            if module.mac is not None and len(module.build_timestamp_label.text()) <= 1:
                module.build_timestamp_label.setText(self.modules[module.mac].build_timestamp_label.text())
            self.update_all_labels(module)
        if self.auto_resize:
            QtCore.QTimer.singleShot(100, self.resize_window)

    def resize_window(self):
        self.main_window.resize(0, 0)

    def restart_all(self):
        for identifier in self.modules:
            if self.modules[identifier].is_mac():
                self.modules[identifier].restart()

    def sort_modules(self):
        for identifier in self.modules:
            self.modules[identifier].widget.hide()
            self.modules[identifier].widget.setParent(None)
        self.row = 0
        self.column = 0
        for identifier in sorted(self.modules, key=lambda x: self.modules[x].get_order()):
            if self.modules[identifier].hidden and not self.show_hidden:
                continue
            self.add_widget_to_grid(self.modules[identifier].widget)
            self.modules[identifier].widget.show()
        if self.auto_resize:
            self.resize_window()

    def mqtt_on_connect(self, client: mqtt.Client, userdata: any, flags: dict, rc: int):
        client.subscribe(f'{self.mqtt_prefix}esp-module/#')
        client.subscribe(f'{self.mqtt_prefix}esp-total/#')
        client.subscribe(f'{self.mqtt_prefix}master/core/config/balancing_enabled')

    @staticmethod
    def update_label_visibility(action: QAction, label: QtWidgets.QLabel):
        if action.isChecked():
            label.show()
        else:
            label.hide()

    def update_all_labels(self, module: Module):
        self.update_label_visibility(self.actionuptime, module.uptime_label)
        self.update_label_visibility(self.actionbuild_timestamp, module.build_timestamp_label)

    def add_widget(self, identifier: str):
        if identifier not in self.modules:
            module = Module(identifier, self.moduleBox, self.moduleBoxLayout, self.mqtt_client)
            self.update_all_labels(module)
            self.add_widget_to_grid(module.widget)
            self.modules[identifier] = module

    def add_widget_to_grid(self, widget):
        self.moduleBoxLayout.addWidget(widget, self.row, self.column)
        self.column += 1
        if self.column >= self.max_columns:
            self.row += 1
            self.column = 0

    def set_module_hidden(self, module: Module, value: bool):
        module.hidden = True if module.identifier in self.hide_modules else value
        self.sort_modules()

    def print_status_bar(self):
        mod_sum_voltage: float = sum(self.modules[identifier].module_voltage for identifier in self.modules
                                     if not self.modules[identifier].hidden)
        cell_sum_voltage: float = sum(self.modules[identifier].cell_sum_voltage for identifier in self.modules
                                      if not self.modules[identifier].hidden)
        self.main_window.statusBar().showMessage(f'{self.total_system_voltage:.2f} V'
                                                 f', {self.total_system_current:.2f} A'
                                                 f', {self.total_system_voltage * self.total_system_current:.2f} W'
                                                 f', {mod_sum_voltage:.2f} V'
                                                 f', {cell_sum_voltage:.2f} V')

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
            self.print_status_bar()
        elif 'total_system_current' in data:
            self.total_system_current = float(data['total_system_current'].split(',')[1]) * -1.0
            self.print_status_bar()
        elif 'chip_temp' in data:
            module.update_chip_temp(data['chip_temp'])
        elif 'module_temps' in data:
            module.module_temps.setText(data['module_temps'])
        elif 'module_voltage' in data:
            module.update_voltage(data['module_voltage'])
        elif 'voltage' in data:
            try:
                module.update_cell_voltage(data['number'], float(data['voltage']))
            except ValueError:
                print(data['identifier'], data['voltage'], 'bad data!')
            module.color_median_voltage(self.cell_min + 0.01)
        elif 'accurate_voltage' in data:
            module.cells[data['number']].accurate_voltage = float(data['accurate_voltage'])
            module.refresh_cell_text(data['number'])
        elif 'is_balancing' in data:
            cell: Cell = module.cells[data['number']]
            cell.is_balancing = bool(int(data['is_balancing']))
            module.refresh_cell_text(data['number'])
        elif 'uptime' in data:
            module.update_uptime(int(data['uptime']))
        elif 'pec15_error_count' in data:
            module.update_pec15(int(data['pec15_error_count']))
        elif 'build_timestamp' in data:
            module.build_timestamp_label.setText(data['build_timestamp'])

    def set_total(self, data: dict):
        if 'total_voltage' in data:
            self.total_system_voltage = float(data['total_voltage'])
            self.print_status_bar()
        elif 'total_current' in data:
            self.total_system_current = float(data['total_current']) * -1.0
            self.print_status_bar()

    def timer_work(self):
        for identifier in self.modules:
            self.modules[identifier].check_uptime()
        if not self.mqtt_client.is_connected():
            self.main_window.setWindowTitle("DISCONNECTED!")
            self.mqtt_client.connect_async(host=self.mqtt_host, port=1883, keepalive=60)
            return
        self.calc_cell_diff()

    def calc_cell_diff(self):
        voltages: list[float] = []
        accurate_voltages: list[float] = []
        socs: list[float] = []
        for ident in self.modules:
            if self.modules[ident].hidden:
                continue
            for cell_number in self.modules[ident].cells:
                cell: Cell = self.modules[ident].cells[cell_number]
                if cell.voltage is not None:
                    voltages.append(cell.voltage)
                    socs.append(cell.get_soc())
                if cell.accurate_voltage is not None:
                    accurate_voltages.append(cell.accurate_voltage)
        if len(voltages) < 1:
            return
        accurate_cell_diff_text = ''
        if len(accurate_voltages) > 0:
            accurate_cell_diff = (max(accurate_voltages) - min(accurate_voltages)) * 1000
            accurate_cell_diff_text = f' [{accurate_cell_diff:.0f}]'
        self.cell_min: float = min(voltages)
        cell_max: float = max(voltages)
        cell_diff: float = (cell_max - self.cell_min) * 1000
        cell_median: float = statistics.median(voltages)
        cell_mean: float = statistics.mean(voltages)
        soc_min: float = min(socs)
        soc_max: float = max(socs)
        soc_median: float = statistics.median(socs)
        soc_mean: float = statistics.mean(socs)
        self.main_window.setWindowTitle(f'{cell_diff:.0f}{accurate_cell_diff_text} mV diff'
                                        f', {cell_median:.3f} V median'
                                        f', {cell_mean:.3f} V mean'
                                        f', {self.cell_min:.3f} V min'
                                        f', {cell_max:.3f} V max'
                                        f', {soc_median:.1f} % median'
                                        f', {soc_mean:.1f} % mean'
                                        f', {soc_min:.1f} % min'
                                        f', {soc_max:.1f} % max')

    def emit_signal_set_module(self, identifier: str, topic: str, msg):
        data = {
            'identifier': identifier,
            topic: msg.payload.decode()
        }
        self.main_window.signal.emit({'func': self.set_widget, 'arg': data})

    def emit_signal_set_cell(self, identifier: str, number: int, topic: str, msg):
        data = {
            'identifier': identifier,
            'number': number,
            topic: msg.payload.decode()
        }
        self.main_window.signal.emit({'func': self.set_widget, 'arg': data})

    def mqtt_on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage):
        if len(msg.payload) < 1:
            return
        if len(self.mqtt_prefix) > 0 and msg.topic.startswith(self.mqtt_prefix):
            msg.topic = msg.topic[len(self.mqtt_prefix):].encode('utf-8')
        if msg.topic.startswith('esp-module'):
            topic: str = msg.topic[msg.topic.find('/') + 1:]
            identifier: str = topic[:topic.find('/')]
            self.main_window.signal.emit({'func': self.add_widget, 'arg': identifier})
            topic = topic[topic.find('/') + 1:]
            # print(identifier, topic)
            if topic in Module.TOPICS:
                self.emit_signal_set_module(identifier, topic, msg)
            elif topic.startswith('cell/'):
                topic = topic[topic.find('/') + 1:]
                number = topic[:topic.find('/')]
                topic = topic[topic.find('/') + 1:]
                number = int(number)
                if topic in self.CELL_TOPICS:
                    self.emit_signal_set_cell(identifier, number, topic, msg)
            elif topic.startswith('accurate/cell/'):
                topic = topic[topic.find('/') + 1:]
                topic = topic[topic.find('/') + 1:]
                number = topic[:topic.find('/')]
                topic = topic[topic.find('/') + 1:]
                number = int(number)
                if topic in self.CELL_TOPICS:
                    self.emit_signal_set_cell(identifier, number, f'accurate_{topic}', msg)
        elif msg.topic == 'esp-total/total_voltage':
            self.main_window.signal.emit({'func': self.set_total, 'arg': {
                'total_voltage': msg.payload.decode()
            }})
        elif msg.topic == 'esp-total/total_current':
            self.main_window.signal.emit({'func': self.set_total, 'arg': {
                'total_current': msg.payload.decode()
            }})
        elif msg.topic == 'master/core/config/balancing_enabled':
            self.main_window.signal.emit({'func': self.actionbalancing_enabled.setChecked,
                                          'arg': msg.payload.decode().lower() == 'true'})


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme("dark")
    settings_dialog = SettingsDialog(MqttLiveWindow.DEFAULT_SETTINGS, MqttLiveWindow.SETTINGS_FILE)
    if settings_dialog.result == 1:
        main_window = MqttLiveWindow(settings_dialog.configuration)
        main_window.show()
