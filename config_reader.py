from queue import Empty, Queue
from typing import Callable

from fabric import Connection
from paramiko.ssh_exception import NoValidConnectionsError
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGridLayout, QPushButton, QStatusBar, QTableWidget

from utils import get_config_file, get_yaml_file


class ConfigReader:
    store: dict
    config: dict
    c: Connection
    button: QPushButton
    table_widget: QTableWidget
    signal: Signal
    queue: Queue
    name: str
    autosize_window: Callable
    status_bar: QStatusBar

    def __init__(self, config: dict, name: str):
        self.config = config
        self.autosize_window = config['autosize_window']
        self.set_connection()
        self.table_widget = config['tableWidget']
        self.signal = config['signal']
        self.status_bar = config['statusBar']
        self.queue = config['queue']
        self.name = name

        self.button = QPushButton(config['centralwidget'])
        self.button.setEnabled(False)
        self.button.setObjectName(self.name)
        self.button.setText(self.name.replace('_', ' '))
        self.button.clicked.connect(self.button_pressed)

        column = config['widget_counter']
        config['widget_counter'] += 1
        grid_layout: QGridLayout = config['gridLayout']
        spacer = grid_layout.itemAtPosition(0, column).spacerItem()
        grid_layout.removeItem(spacer)
        grid_layout.addWidget(self.button, 0, column, 1, 1)
        grid_layout.addItem(spacer, 0, column + 1, 1, 1)
        grid_layout.removeWidget(self.table_widget)
        grid_layout.addWidget(self.table_widget, 1, 0, 1, column + 2)

    def set_connection(self):
        self.c = self.config['c']

    def init_queue(self):
        self.queue.put({'func': self.status_bar.showMessage, 'type': 'signal', 'arg': f'{self.name}..'})
        self.queue.put({'func': self.get_info, 'type': 'ssh'})
        self.queue.put({'func': self.button.setEnabled, 'type': 'signal', 'arg': True})

    def get_info(self):
        pass

    def button_pressed(self):
        self.button.setEnabled(False)
        if self.config.get('last_clicked', '') == self.name:
            self.queue.put({'func': self.get_info, 'type': 'ssh'})
        self.queue.put({'func': self.show_info, 'type': 'signal'})
        self.queue.put({'func': self.button.setEnabled, 'type': 'signal', 'arg': True})
        self.config['last_clicked'] = self.name

    def show_info(self):
        pass

    def clear_queue(self):
        while not self.queue.empty():
            try:
                self.queue.get(block=False)
            except Empty:
                continue
            self.queue.task_done()

    def sudo(self, command: str):
        try:
            return self.c.sudo(command, hide=True)
        except NoValidConnectionsError as e:
            self.clear_queue()
            self.queue.put({'func': self.status_bar.showMessage, 'type': 'signal', 'arg': str(e)})

    def get_yaml_file(self, path: str):
        try:
            return get_yaml_file(self.c, path)
        except NoValidConnectionsError as e:
            self.clear_queue()
            self.queue.put({'func': self.status_bar.showMessage, 'type': 'signal', 'arg': str(e)})

    def get_config_file(self, path: str):
        try:
            return get_config_file(self.c, path)
        except NoValidConnectionsError as e:
            self.clear_queue()
            self.queue.put({'func': self.status_bar.showMessage, 'type': 'signal', 'arg': str(e)})
