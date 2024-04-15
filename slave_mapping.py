from PyQt6.QtWidgets import QTableWidgetItem

from config_reader import ConfigReader


class SlaveMapping(ConfigReader):
    def __init__(self, config: dict):
        super().__init__(config, 'slave_mapping')

    def get_info(self):
        self.store = self.get_yaml_file('/docker/easybms-master/slave_mapping.yaml')

    def show_info(self):
        headers = ['Number', 'Mac', 'Assignments']
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setRowCount(len(self.store['slaves']))
        for i, slave_mac in enumerate(self.store['slaves']):
            slave: dict = self.store['slaves'][slave_mac]
            self.table_widget.setItem(i, headers.index('Number'), QTableWidgetItem(str(slave['number'])))
            self.table_widget.setItem(i, headers.index('Mac'), QTableWidgetItem(slave_mac))
            assignments = []
            if slave.get('total_current_measurer', False):
                assignments.append('total_current_measurer')
            if slave.get('total_voltage_measurer', False):
                assignments.append('total_voltage_measurer')
            self.table_widget.setItem(i, headers.index('Assignments'), QTableWidgetItem(', '.join(assignments)))
        self.table_widget.resizeColumnsToContents()
        self.autosize_window()
