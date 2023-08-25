import os
import queue
import sys
import threading
from pathlib import Path

import qdarktheme
from fabric import Connection
from PyQt5 import QtCore, QtWidgets

from config_reader import ConfigReader
from credentials import Credentials
from custom_signal_window import CustomSignalWindow
from docker_container import DockerContainer
from modbus import Modbus
from mqtt_live import MqttLiveWindow
from settings_dialog import SettingsDialog
from slave_mapping import SlaveMapping
from ui.main import Ui_MainWindow
from utils import get_config_local, save_config_local

CONFIG_FILE = Path('config.yaml')


class MainWindow(Ui_MainWindow):
    def __init__(self):
        self.app = QtWidgets.QApplication(sys.argv)
        self.main_window = CustomSignalWindow()
        self.setupUi(self.main_window)

        self.actionconfig.triggered.connect(self.show_settings_dialog)
        self.actionmqtt_live.triggered.connect(self.show_mqtt_live)

        self.queue = queue.Queue()

        self.config: dict = get_config_local(CONFIG_FILE)
        if 'error' in self.config:
            self.config = {
                'host': '127.0.0.1',
                'user': 'pi',
                'password': '123'
            }
            save_config_local(CONFIG_FILE, self.config)

        self.reader_config: dict = {
            'autosize_window': self.autosize_window,
            'c': self.get_connection(),
            'centralwidget': self.centralwidget,
            'gridLayout': self.gridLayout,
            'tableWidget': self.tableWidget,
            'signal': self.main_window.signal,
            'statusBar': self.main_window.statusBar(),
            'queue': self.queue,
            'widget_counter': 0
        }
        self.reader_list: dict[str, ConfigReader] = {
            'credentials': Credentials(self.reader_config),
            'docker': DockerContainer(self.reader_config),
            'slave_mapping': SlaveMapping(self.reader_config),
            'modbus': Modbus(self.reader_config)
        }

        self.init_queue()
        threading.Thread(target=self.worker, daemon=True).start()

    def show(self):
        self.main_window.show()
        sys.exit(self.app.exec_())

    def show_mqtt_live(self):
        store = self.reader_list['credentials'].store
        parameters: dict = SettingsDialog.get_config(MqttLiveWindow.DEFAULT_SETTINGS, MqttLiveWindow.SETTINGS_FILE)
        parameters['host'] = self.config['host']
        parameters['username'] = store['mqtt_user']
        parameters['password'] = store['mqtt_password']
        w = MqttLiveWindow(parameters, as_app=False)
        w.show()

    def get_connection(self):
        return Connection(host=self.config['host'], user=self.config['user'],
                          connect_kwargs={'password': self.config['password']})

    def init_queue(self):
        for key in self.reader_list:
            reader = self.reader_list[key]
            reader.button.setEnabled(False)
            reader.init_queue()
        self.queue.put({'func': self.main_window.statusBar().clearMessage, 'type': 'signal'})

    def show_settings_dialog(self):
        if SettingsDialog(self.config).result == 1:
            save_config_local(CONFIG_FILE, self.config)
            self.reader_config['c'] = self.get_connection()
            for key in self.reader_list:
                self.reader_list[key].set_connection()
            self.init_queue()

    def worker(self):
        while True:
            work = self.queue.get()
            if work['type'] == 'ssh':
                work['func']()
            elif work['type'] == 'signal':
                self.main_window.signal.emit(work)
            self.queue.task_done()

    def autosize_window(self):
        def resize_width():
            size = self.main_window.size()
            size_hint = self.main_window.minimumSizeHint()
            table_size = self.tableWidget.size()
            table_size_hint = self.tableWidget.viewportSizeHint()
            size.setWidth(size.width() + (table_size_hint.width() - table_size.width()) + 25)
            self.main_window.resize(size)
            self.main_window.setMinimumSize(size_hint)

        QtCore.QTimer.singleShot(0, resize_width)


if __name__ == '__main__':
    script_dir = os.path.dirname(os.path.realpath(__file__))

    app = QtWidgets.QApplication(sys.argv)
    qdarktheme.setup_theme("dark")
    main_window = MainWindow()
    main_window.show()
