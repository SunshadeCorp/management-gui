import os
import statistics
import sys

import paho.mqtt.client as mqtt
from PyQt5 import QtWidgets

from custom_signal_window import CustomSignalWindow
from ui.mqtt_live import Ui_MainWindow

CONFIG_MAX_COLUMNS = 4


class MqttLiveWindow(Ui_MainWindow):
    def __init__(self, host: str, username: str, password: str):
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = CustomSignalWindow()
        self.setupUi(self.main_window)

        self.row = 0
        self.column = 0
        self.modules: dict = {}

        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.mqtt_on_connect
        self.mqtt_client.on_message = self.mqtt_on_message
        self.mqtt_client.username_pw_set(username, password)
        self.mqtt_client.connect(host=host, port=1883, keepalive=60)

        self.mqtt_client.loop_start()

    def show(self):
        self.main_window.show()
        self.app.exec_()

    @staticmethod
    def mqtt_on_connect(client: mqtt.Client, userdata: any, flags: dict, rc: int):
        client.subscribe('esp-module/#')

    def add_widget(self, identifier: str):
        if identifier not in self.modules:
            module = QtWidgets.QWidget(self.centralwidget)
            module.setObjectName("Form")
            # module.resize(100, 100)
            vertical_layout = QtWidgets.QVBoxLayout(module)
            vertical_layout.setObjectName("verticalLayout")
            label = QtWidgets.QLabel(module)
            label.setObjectName("label")
            label.setText(identifier)
            vertical_layout.addWidget(label)
            cells = {}
            for i in range(1, 13):
                cell = QtWidgets.QLabel(module)
                cell.setObjectName("label")
                cell.setText(f'{i}:')
                vertical_layout.addWidget(cell)
                cells[i] = {
                    'widget': cell,
                }
            self.gridLayout.addWidget(module, self.row, self.column)
            self.column += 1
            if self.column >= CONFIG_MAX_COLUMNS:
                self.row += 1
                self.column = 0
            self.modules[identifier] = {
                'widget': module,
                'layout': vertical_layout,
                'header': label,
                'cells': cells,
            }

    def set_widget(self, data: dict):
        module = self.modules[data['identifier']]
        if 'available' in data:
            if data['available'] == 'offline':
                widget: QtWidgets.QWidget = module['widget']
                widget.setStyleSheet('background-color: grey;')
            return
        voltage: float = float(data['value'])
        cell: QtWidgets.QLabel = module['cells'][data['number']]['widget']
        module['cells'][data['number']]['voltage'] = voltage
        cell.setText(f"{data['number']}: {data['value']}")
        voltages: list[float] = []
        for cell_number in module['cells']:
            if 'voltage' in module['cells'][cell_number]:
                voltages.append(module['cells'][cell_number]['voltage'])
        median_voltage: float = statistics.median(voltages)
        module['header'].setText(f"{data['identifier']}: {median_voltage:.3f}")
        for cell_number in module['cells']:
            if 'voltage' in module['cells'][cell_number]:
                if abs(module['cells'][cell_number]['voltage'] - median_voltage) >= 0.01:
                    module['cells'][cell_number]['widget'].setStyleSheet('background-color: red;')
                else:
                    module['cells'][cell_number]['widget'].setStyleSheet('')

    def mqtt_on_message(self, client: mqtt.Client, userdata: any, msg: mqtt.MQTTMessage):
        topic = msg.topic[msg.topic.find('/') + 1:]
        identifier = topic[:topic.find('/')]
        self.main_window.signal.emit({'func': self.add_widget, 'arg': identifier})
        topic = topic[topic.find('/') + 1:]
        print(identifier, topic)
        if topic == 'available':
            data = {
                'identifier': identifier,
                'available': msg.payload.decode()
            }
            self.main_window.signal.emit({'func': self.set_widget, 'arg': data})
        elif topic == 'module_topic':
            pass
        elif topic.startswith('cell/'):
            topic = topic[topic.find('/') + 1:]
            number = topic[:topic.find('/')]
            topic = topic[topic.find('/') + 1:]
            number = int(number)
            if topic == 'voltage':
                data = {
                    'identifier': identifier,
                    'number': number,
                    'value': msg.payload.decode()
                }
                self.main_window.signal.emit({'func': self.set_widget, 'arg': data})


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))

    main_window = MqttLiveWindow('host', 'username', 'password')
    main_window.show()
