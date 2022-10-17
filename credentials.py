from PyQt5.QtWidgets import QTableWidgetItem

from config_reader import ConfigReader


class Credentials(ConfigReader):
    def __init__(self, config: dict):
        super().__init__(config, 'credentials')

    def get_info(self):
        self.signal.emit({'func': self.status_bar.showMessage, 'arg': 'can..'})
        can = self.get_yaml_file('/docker/build/can-service/credentials.yaml')
        if can is None:
            return
        self.signal.emit({'func': self.status_bar.showMessage, 'arg': 'master..'})
        master = self.get_yaml_file('/docker/build/easybms-master/credentials.yaml')
        self.signal.emit({'func': self.status_bar.showMessage, 'arg': 'relay..'})
        relay = self.get_yaml_file('/docker/build/relay-service/credentials.yaml')
        env = self.get_config_file('/docker/.env')
        if can != master:
            print('can != master!', can, master)
            return
        if master != relay:
            print('master != relay!', master, relay)
            return
        if relay['username'] != env['mqtt_user'] or relay['password'] != env['mqtt_password']:
            print('relay != env!', relay, env)
            return
        self.store = can | master | relay
        self.store['mqtt_user'] = self.store.pop('username')
        self.store['mqtt_password'] = self.store.pop('password')
        self.store |= env
        self.signal.emit({'func': self.status_bar.showMessage, 'arg': 'credentials match!'})

    def show_info(self):
        headers = ['variable', 'value']
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setRowCount(len(self.store))
        for i, key in enumerate(self.store):
            self.table_widget.setItem(i, 0, QTableWidgetItem(str(key)))
            self.table_widget.setItem(i, 1, QTableWidgetItem(str(self.store[key])))
        self.table_widget.resizeColumnsToContents()
        self.autosize_window()
