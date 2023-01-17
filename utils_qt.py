from PyQt5 import QtWidgets


def exchange_widget_positions(grid_layout: QtWidgets.QGridLayout, widget1: QtWidgets.QWidget,
                              widget2: QtWidgets.QWidget):
    row1, column1, row_span1, column_span1 = grid_layout.getItemPosition(grid_layout.indexOf(widget1))
    row2, column2, row_span2, column_span2 = grid_layout.getItemPosition(grid_layout.indexOf(widget2))
    grid_layout.removeWidget(widget1)
    grid_layout.removeWidget(widget2)
    grid_layout.addWidget(widget1, row2, column2, row_span2, column_span2)
    grid_layout.addWidget(widget2, row1, column1, row_span1, column_span1)
    grid_layout.update()
