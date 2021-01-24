import os
import sys
import logging
import numpy as np
import pandas as pd
import pyqtgraph as pg
from datetime import datetime
from logging.handlers import RotatingFileHandler
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont
from PyQt5.QtCore import Qt, QThreadPool, QTimer
from PyQt5.QtWidgets import (QMainWindow, QWidget, QApplication, QGridLayout,
                             QMessageBox, QLabel, QComboBox, QTextEdit,
                             QLineEdit, QPushButton, QProgressBar, QFrame,
                             QSplitter, QCheckBox, QSizePolicy, QSpacerItem,
                             QTabWidget, QAction, QFileDialog, QScrollArea,
                             QToolBar, QPlainTextEdit)

from ifit.gui_functions import Widgets, QTextEditLogger
from openso2.station_com import Station
from openso2.gui_funcs import Worker, sync_station

__version__ = '1.2'
__author__ = 'Ben Esse'

# Set up logging
if not os.path.isdir('bin/'):
    os.makedirs('bin/')
fh = RotatingFileHandler('bin/OpenSO2.log', maxBytes=20000, backupCount=5)
fh.setLevel(logging.INFO)
fmt = '%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s'
fh.setFormatter(logging.Formatter(fmt))
logging.getLogger().addHandler(fh)


class MainWindow(QMainWindow):
    """View for the OpenSO2 GUI"""

    def __init__(self):
        """View initialiser"""
        super().__init__()

        # Set the window properties
        self.setWindowTitle(f'OpenSO2 {__version__}')
        self.statusBar().showMessage('Ready')
        self.setGeometry(40, 40, 1200, 600)
        # self.setWindowIcon(QIcon('bin/icons/main.ico'))

        # Set the window layout
        self.generalLayout = QGridLayout()
        self._centralWidget = QScrollArea()
        self.widget = QWidget()
        self.setCentralWidget(self._centralWidget)
        self.widget.setLayout(self.generalLayout)

        # Scroll Area Properties
        self._centralWidget.setWidgetResizable(True)
        self._centralWidget.setWidget(self.widget)

        # Generate the threadpool for launching background processes
        self.threadpool = QThreadPool()

        # Setup widget stylesheets
        QTabWidget().setStyleSheet('QTabWidget { font-size: 18pt; }')

        # Create an empty dictionary to hold the GUI widgets
        self.widgets = Widgets()

        station_info = {'LOVE': {'host': '192.168.1.146',
                                 'username': 'pi',
                                 'password': 'soufriere'},
                        'BROD': {'host': '192.168.1.146',
                                 'username': 'pi',
                                 'password': 'soufriere'}}

        self.stations = {}
        for station, info in station_info.items():
            self.stations[station] = Station(info, station)

        # Get today's date
        self.today_date = datetime.now().date()

        # Build the GUI
        self._createApp()

        self.logTimer = QTimer(self)
        self.logTimer.setInterval(5000)
        self.logTimer.timeout.connect(self._station_sync)
        self.logTimer.start()

    def _createApp(self):
        """Handles building the main GUI"""

        # Create a frame to hold program controls
        self.controlFrame = QFrame()
        self.controlFrame.setFrameShape(QFrame.StyledPanel)

        # Create a frame to hold program outputs
        self.outputFrame = QFrame(self)
        self.outputFrame.setFrameShape(QFrame.StyledPanel)

        # Create a frame to hold graphs
        self.resultsFrame = QFrame(self)
        self.resultsFrame.setFrameShape(QFrame.StyledPanel)

        # Add splitters to allow for adjustment
        splitter1 = QSplitter(Qt.Horizontal)
        splitter1.addWidget(self.controlFrame)
        splitter1.addWidget(self.resultsFrame)

        splitter2 = QSplitter(Qt.Vertical)
        splitter2.addWidget(splitter1)
        splitter2.addWidget(self.outputFrame)

        # Pack the Frames and splitters
        self.generalLayout.addWidget(splitter2)

        # Generate the GUI widgets
        self._createOutputs()
        self._createResults()

# =============================================================================
#   Generate the program outputs
# =============================================================================

    def _createOutputs(self):
        """"""

        # Create the layout
        layout = QGridLayout(self.outputFrame)
        layout.setAlignment(Qt.AlignTop)

        # Create a textbox to display the program logs
        self.logBox = QTextEditLogger(self)
        self.logBox.setFormatter(logging.Formatter('%(message)s'))
        logging.getLogger().addHandler(self.logBox)
        logging.getLogger().setLevel(logging.INFO)
        layout.addWidget(self.logBox.widget, 2, 0, 1, 6)
        msg = 'Welcome to OpenSO2! Written by Ben Esse'
        self.logBox.widget.appendPlainText(msg)

    def _createResults(self):
        """Create the results tabs"""

        # Setup tab layout
        tablayout = QGridLayout(self.resultsFrame)

        # Form the tab widget
        tabwidget = QTabWidget()
        tabwidget.addTab(QWidget(), 'Flux Results')

        self.station_log = {}
        self.plot_lines = {}
        self.plot_axes = {}

        for station in self.stations:

            # Create the tab to hold the station widgets
            stationtab = QWidget()
            tabwidget.addTab(stationtab, str(station))

            # Create the graphs
            graphwin = pg.GraphicsWindow(show=True)
            pg.setConfigOptions(antialias=True)

            # Set up the station layout
            layout = QGridLayout(stationtab)
            # layout.setAlignment(Qt.AlignTop)

            # Make the graphs
            ax0 = graphwin.addPlot(row=0, col=0)
            ax1 = graphwin.addPlot(row=0, col=1)
            self.plot_axes[station] = [ax0, ax1]

            for ax in self.plot_axes[station]:
                ax.setDownsampling(mode='peak')
                ax.setClipToView(True)
                ax.showGrid(x=True, y=True)

            # Add axis labels
            ax0.setLabel('left', 'SO2 SCD (molec/cm2)')
            ax1.setLabel('left', 'SO2 Flux (kg/s)')
            ax0.setLabel('bottom', 'Scan Angle (deg)')
            ax1.setLabel('bottom', 'Time')

            # Initialise the lines
            p0 = pg.mkPen(color='#1f77b4', width=1.0)
            l0 = ax0.plot(pen=p0)
            l1 = ax1.plot(pen=p0)

            self.plot_lines[station] = [l0, l1]

            # Create a textbox to hold the station logs
            self.station_log[station] = QPlainTextEdit(self)
            self.station_log[station].setReadOnly(True)
            self.station_log[station].setFont(QFont('Courier', 10))
            # self.station_log[station].setMinimumSize(800, 50)

            splitter = QSplitter(Qt.Vertical)
            splitter.addWidget(graphwin)
            splitter.addWidget(self.station_log[station])
            layout.addWidget(splitter)

        tablayout.addWidget(tabwidget, 0, 0)

    def update_log(self, station, log_text):
        """Slot to update the station logs"""

        text = self.station_log[station].toPlainText().split('\n')

        for line in log_text[len(text):]:
            self.station_log[station].appendPlainText(line.strip())

    def update_plot(self, station, fname):

        # Load the scan file, unpacking the angle and SO2 data
        scan_data = pd.read_csv(fname)
        plotx = scan_data['Angle'].dropna().to_numpy()
        ploty = scan_data['SO2'].dropna().to_numpy()

        # Check for large numbers in the ydata. This is due to a
        # bug in pyqtgraph not displaying large numbers
        if np.nanmax(ploty) > 1e6:
            order = int(np.ceil(np.log10(np.nanmax(ploty)))) - 1
            ploty = ploty / 10**order
            self.plot_axes[station][0].setLabel('left',
                                                f'SO2 FLux (kg/s) (1e{order})')

        self.plot_lines[station][0].setData(plotx, ploty)

    def _station_sync(self):
        for station in self.stations.values():
            self.log_worker = Worker(sync_station, station, self.today_date)
            self.log_worker.signals.log.connect(self.update_log)
            self.log_worker.signals.plot.connect(self.update_plot)
            self.threadpool.start(self.log_worker)


# Cliet Code
def main():
    """Main function"""
    # Create an instance of QApplication
    app = QApplication(sys.argv)

    app.setStyle("Fusion")

    # Use a palette to switch to dark colors:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.black)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.Active, QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, Qt.darkGray)
    app.setPalette(palette)

    # Show the GUI
    view = MainWindow()
    view.show()

    # Execute the main loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
