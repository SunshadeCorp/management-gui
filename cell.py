from PyQt5 import QtWidgets


class Cell:
    DATA_POINTS: dict[float, float] = {
        0.0: -0.2,
        3.420: 0.0,
        3.499: 0.1,
        3.579: 0.2,
        3.615: 0.3,
        3.641: 0.4,
        3.678: 0.5,
        3.756: 0.6,
        3.825: 0.7,
        3.913: 0.8,
        4.016: 0.9,
        4.136: 1.00,
        5.0: 1.2,
    }
    LOWER_VOLTAGE: float = min(DATA_POINTS)
    UPPER_VOLTAGE: float = max(DATA_POINTS)

    def __init__(self, label):
        self.label: QtWidgets.QLabel = label
        self.voltage = None
        self.is_balancing = False

    def get_voltage(self):
        return -1 if self.voltage is None else self.voltage

    def get_soc(self):
        lower_voltage: float = self.LOWER_VOLTAGE
        upper_voltage: float = self.UPPER_VOLTAGE
        for table_voltage in self.DATA_POINTS:
            if self.voltage >= table_voltage:
                lower_voltage = table_voltage
            else:
                upper_voltage = table_voltage
                break
        lower_soc = self.DATA_POINTS[lower_voltage]
        upper_soc = self.DATA_POINTS[upper_voltage]
        d = (upper_voltage - self.voltage) / (upper_voltage - lower_voltage)
        return ((1 - d) * upper_soc + d * lower_soc) * 100


if __name__ == '__main__':
    test_cell = Cell(None)
    test_cell.voltage = 2
    print(test_cell.get_soc())
    test_cell.voltage = 0.1
    print(test_cell.get_soc())
    test_cell.voltage = 3
    print(test_cell.get_soc())
    test_cell.voltage = 4
    print(test_cell.get_soc())
    test_cell.voltage = 4.9
    print(test_cell.get_soc())
