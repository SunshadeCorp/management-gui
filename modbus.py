from PyQt5.QtWidgets import QTableWidgetItem

from config_reader import ConfigReader


class Modbus(ConfigReader):
    def __init__(self, config: dict):
        super().__init__(config, 'modbus')

    def get_info(self):
        self.store = self.get_yaml_file('/docker/modbus4mqtt/sungrow_sh10rt.yaml')

    def show_info(self):
        headers = ['address', 'table', 'pub_topic', 'type', 'unit', 'retain', 'sensor_type']
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setRowCount(len(self.store['registers']))
        for i, register in enumerate(self.store['registers']):
            for j, header in enumerate(headers):
                self.table_widget.setItem(i, j, QTableWidgetItem(str(register.get(header, ''))))
        self.table_widget.resizeColumnsToContents()
        self.autosize_window()
