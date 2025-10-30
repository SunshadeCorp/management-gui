import json

from PySide6.QtWidgets import QTableWidgetItem

from config_reader import ConfigReader


class DockerContainer(ConfigReader):
    def __init__(self, config: dict):
        super().__init__(config, 'docker_container')

    def get_info(self):
        result = self.sudo('docker container ls --all --format "{{json . }}"')
        container = result.stdout
        container = '[' + container.strip() + ']'
        container = container.replace('\n', ',')
        self.store = json.loads(container)

    def show_info(self):
        headers = ['Names', 'State', 'Ports', 'Networks', 'Status']
        self.table_widget.clear()
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setRowCount(len(self.store))
        for i, single_container in enumerate(self.store):
            for j, header in enumerate(headers):
                if header == 'Ports':
                    ports = single_container[header].split(',')
                    ports = [port.strip() for port in ports if not port.strip().startswith('::')]
                    self.table_widget.setItem(i, j, QTableWidgetItem(', '.join(ports)))
                    continue
                self.table_widget.setItem(i, j, QTableWidgetItem(single_container[header]))
        self.table_widget.resizeColumnsToContents()
        self.autosize_window()
