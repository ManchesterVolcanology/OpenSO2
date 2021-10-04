"""Main Home Station Script.

Syncs data from scanners and calculates fluxes for an OpenSO2 network
"""
import os
import sys
import yaml
import logging
import traceback
import numpy as np
import pandas as pd
import pyqtgraph as pg
from datetime import datetime
from functools import partial
from collections import OrderedDict
from logging.handlers import RotatingFileHandler
from PyQt5.QtGui import QPalette, QColor, QFont, QIcon
from PyQt5.QtCore import Qt, QThreadPool, QTimer, pyqtSlot, QThread
from PyQt5.QtWidgets import (QMainWindow, QWidget, QApplication, QGridLayout,
                             QMessageBox, QLabel, QLineEdit, QPushButton,
                             QFrame, QSplitter, QTabWidget, QFileDialog,
                             QScrollArea, QToolBar, QPlainTextEdit,
                             QFormLayout, QDialog, QAction, QDateTimeEdit,
                             QDateEdit, QSpinBox, QDoubleSpinBox, QCheckBox)

from openso2.station import Station
from openso2.gui_funcs import (SyncWorker, PostAnalysisWorker, Widgets,
                               QTextEditLogger)
from openso2.plume import calc_end_point

__version__ = '1.2'
__author__ = 'Ben Esse'

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set up logging
if not os.path.isdir('bin/'):
    os.makedirs('bin/')
fh = RotatingFileHandler('bin/OpenSO2.log', maxBytes=20000, backupCount=5)
fh.setLevel(logging.INFO)
fmt = '%(asctime)s %(levelname)s %(module)s %(funcName)s %(message)s'
fh.setFormatter(logging.Formatter(fmt))
logger.addHandler(fh)

COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b',
          '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']


class MainWindow(QMainWindow):
    """View for the OpenSO2 GUI."""

    def __init__(self):
        """View initialiser."""
        super().__init__()

        # Set the window properties
        self.setWindowTitle(f'OpenSO2 {__version__}')
        self.statusBar().showMessage('Ready')
        self.setGeometry(40, 40, 1200, 700)
        self.setWindowIcon(QIcon('bin/icons/main.png'))

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

        # Set the default theme
        self.theme = 'Dark'

        # Initialise an empty dictionary to hold the station information
        self.stations = {}

        # Build the GUI
        self._createApp()

        # Update widgets from loaded config file
        self.config = {}
        self.config_fname = None
        if os.path.isfile('bin/.config'):
            with open('bin/.config', 'r') as r:
                self.config_fname = r.readline().strip()
            self.load_config(fname=self.config_fname)

        # Update GUI theme
        if self.theme == 'Dark':
            self.changeThemeDark()
        elif self.theme == 'Light':
            self.changeThemeLight()

    def _createApp(self):
        """Handle building the main GUI."""
        # Generate GUI actions
        # Save action
        saveAct = QAction(QIcon('bin/icons/save.png'), '&Save', self)
        saveAct.setShortcut('Ctrl+S')
        saveAct.triggered.connect(partial(self.save_config, False))

        # Save As action
        saveasAct = QAction(QIcon('bin/icons/saveas.png'), '&Save As', self)
        saveasAct.setShortcut('Ctrl+Shift+S')
        saveasAct.triggered.connect(partial(self.save_config, True))

        # Load action
        loadAct = QAction(QIcon('bin/icons/open.png'), '&Load', self)
        loadAct.triggered.connect(partial(self.load_config, None))

        # Change theme action
        themeAct = QAction(QIcon('bin/icons/theme.png'), '&Change Theme', self)
        themeAct.triggered.connect(self.change_theme)

        # Add menubar
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(saveAct)
        fileMenu.addAction(saveasAct)
        fileMenu.addAction(loadAct)
        toolMenu = menubar.addMenu('&View')
        toolMenu.addAction(themeAct)

        # Create a toolbar
        toolbar = QToolBar("Main toolbar")
        self.addToolBar(toolbar)
        toolbar.addAction(saveAct)
        toolbar.addAction(saveasAct)
        toolbar.addAction(loadAct)
        toolbar.addAction(themeAct)

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
        self._createControls()
        self._createOutputs()
        self._createResults()

# =============================================================================
#   Generate the program inputs
# =============================================================================

    def _createControls(self):
        """Generate the program controls."""
        # Create the layout
        layout = QGridLayout(self.controlFrame)
        layout.setAlignment(Qt.AlignTop)
        nrow = 0

        header = QLabel('Volcano')
        header.setAlignment(Qt.AlignLeft)
        header.setFont(QFont('Ariel', 12))
        layout.addWidget(header, nrow, 0, 1, 2)
        nrow += 1

        # Create inputs for the volcano latitude
        layout.addWidget(QLabel('Volcano\nLatitude:'), nrow, 0)
        self.widgets['vlat'] = QLineEdit()
        layout.addWidget(self.widgets['vlat'], nrow, 1)
        nrow += 1

        # Create inputs for the volcano longitude
        layout.addWidget(QLabel('Volcano\nLongitutde:'), nrow, 0)
        self.widgets['vlon'] = QLineEdit()
        layout.addWidget(self.widgets['vlon'], nrow, 1)
        nrow += 1

        layout.addWidget(QHLine(), nrow, 0, 1, 10)
        nrow += 1

        header = QLabel('Default Plume Settings')
        header.setAlignment(Qt.AlignLeft)
        header.setFont(QFont('Ariel', 12))
        layout.addWidget(header, nrow, 0, 1, 2)
        nrow += 1

        # Create input for the plume speed
        layout.addWidget(QLabel('Plume Speed\n[m/s]:'), nrow, 0)
        self.widgets['plume_speed'] = QDoubleSpinBox()
        self.widgets['plume_speed'].setRange(0, 1000)
        self.widgets['plume_speed'].setValue(1.0)
        layout.addWidget(self.widgets['plume_speed'], nrow, 1)
        nrow += 1

        # Create input for the plume direction
        layout.addWidget(QLabel('Plume Direction\n[degrees]:'), nrow, 0)
        self.widgets['plume_dir'] = QDoubleSpinBox()
        self.widgets['plume_dir'].setRange(0, 360)
        self.widgets['plume_dir'].setValue(0.0)
        layout.addWidget(self.widgets['plume_dir'], nrow, 1)
        nrow += 1

        # Create input for the plume altitude
        layout.addWidget(QLabel('Plume Altitude\n[m a.s.l.]:'), nrow, 0)
        self.widgets['plume_alt'] = QDoubleSpinBox()
        self.widgets['plume_alt'].setRange(0, 100000)
        self.widgets['plume_alt'].setValue(1000)
        layout.addWidget(self.widgets['plume_alt'], nrow, 1)
        nrow += 1

        layout.addWidget(QLabel('Scan Pair Time\nLimit (min):'), nrow, 0)
        self.widgets['scan_pair_time'] = QSpinBox()
        self.widgets['scan_pair_time'].setRange(0, 1440)
        self.widgets['scan_pair_time'].setValue(10)
        layout.addWidget(self.widgets['scan_pair_time'], nrow, 1)
        nrow += 1

        self.widgets['scan_pair_flag'] = QCheckBox('Calc Plume\nLocation?')
        self.widgets['scan_pair_flag'].setToolTip('Toggle whether plume '
                                                  + 'location is calculated '
                                                  + 'from paired scans')
        layout.addWidget(self.widgets['scan_pair_flag'], nrow, 0)
        nrow += 1

        layout.addWidget(QHLine(), nrow, 0, 1, 10)
        nrow += 1

        # Form the tab widget
        analysisTabHolder = QTabWidget()
        syncTab = QWidget()
        analysisTabHolder.addTab(syncTab, 'Station Sync Controls')
        postTab = QWidget()
        analysisTabHolder.addTab(postTab, 'Post Analysis')

        layout.addWidget(analysisTabHolder, nrow, 0, 1, 2)

        # Add syncing controls
        sync_layout = QGridLayout(syncTab)

        # Create widgets for the start and stop scan times
        sync_layout.addWidget(QLabel('Sync Start Time\n(HH:MM):'), 0, 0)
        self.widgets['sync_start_time'] = QDateTimeEdit(displayFormat='HH:mm')
        sync_layout.addWidget(self.widgets['sync_start_time'], 0, 1)

        sync_layout.addWidget(QLabel('Sync Stop Time\n(HH:MM):'), 1, 0)
        self.widgets['sync_stop_time'] = QDateTimeEdit(displayFormat='HH:mm')
        sync_layout.addWidget(self.widgets['sync_stop_time'], 1, 1)

        sync_layout.addWidget(QLabel('Sync Time\nInterval (s):'), 2, 0)
        self.widgets['sync_interval'] = QSpinBox()
        self.widgets['sync_interval'].setRange(0, 86400)
        self.widgets['sync_interval'].setValue(30)
        sync_layout.addWidget(self.widgets['sync_interval'], 2, 1)

        # Add a button to control syncing
        self.sync_button = QPushButton('Syncing OFF')
        self.sync_button.setStyleSheet("background-color: red")
        self.sync_button.clicked.connect(self._toggle_sync)
        self.sync_button.setFixedSize(150, 25)
        self.syncing = False
        sync_layout.addWidget(self.sync_button, 3, 0, 1, 2)

        # Add post analysis controls
        post_layout = QGridLayout(postTab)

        # File path to the data
        post_layout.addWidget(QLabel('Date to Analyse:'), 0, 0)
        self.widgets['date_to_analyse'] = QDateEdit(displayFormat='yyyy-MM-dd')
        self.widgets['date_to_analyse'].setCalendarPopup(True)
        post_layout.addWidget(self.widgets['date_to_analyse'], 0, 1)

        # Add a button to control syncing
        self.post_button = QPushButton('Run Post Analysis')
        self.post_button.clicked.connect(self._flux_post_analysis)
        self.post_button.setFixedSize(150, 25)
        post_layout.addWidget(self.post_button, 1, 0, 1, 2)

# =============================================================================
#   Generate the program outputs
# =============================================================================

    def _createOutputs(self):
        """Generate GUI outputs."""
        # Create the layout
        layout = QGridLayout(self.outputFrame)
        layout.setAlignment(Qt.AlignTop)

        # Create a textbox to display the program logs
        self.logBox = QTextEditLogger(self)
        fmt = logging.Formatter('%(asctime)s - %(message)s',
                                '%Y/%m/%d %H:%M:%S')
        self.logBox.setFormatter(fmt)
        logger.addHandler(self.logBox)
        logger.setLevel(logging.INFO)
        layout.addWidget(self.logBox.widget, 3, 0, 1, 6)
        msg = f'Welcome to OpenSO2 v{__version__}! Written by Ben Esse'
        self.logBox.widget.appendPlainText(msg)

# =============================================================================
#   Create program results
# =============================================================================

    def _createResults(self):
        """Create the results tabs."""
        # Setup tab layout
        layout = QGridLayout(self.resultsFrame)

        # Form the tab widget
        self.stationTabHolder = QTabWidget()
        resultsTab = QWidget()
        self.stationTabHolder.addTab(resultsTab, 'Flux Results')

        # Add plots for overall results
        # Create the graphs
        graph_layout = QGridLayout(resultsTab)
        self.flux_graphwin = pg.GraphicsLayoutWidget(show=True)
        pg.setConfigOptions(antialias=True)

        # Make the graphs
        x_axis = pg.DateAxisItem(utcOffset=0)
        ax0 = self.flux_graphwin.addPlot(row=0, col=0, colspan=2,
                                         axisItems={'bottom': x_axis})
        x_axis = pg.DateAxisItem(utcOffset=0)
        ax1 = self.flux_graphwin.addPlot(row=1, col=0,
                                         axisItems={'bottom': x_axis})
        x_axis = pg.DateAxisItem(utcOffset=0)
        ax2 = self.flux_graphwin.addPlot(row=1, col=1,
                                         axisItems={'bottom': x_axis})
        self.flux_axes = [ax0, ax1, ax2]

        for ax in self.flux_axes:
            ax.setDownsampling(mode='peak')
            ax.setClipToView(True)
            ax.showGrid(x=True, y=True)
            ax.setLabel('bottom', 'Time')

        # Add axis labels
        ax0.setLabel('left', 'SO2 Flux [kg/s]')
        ax1.setLabel('left', 'Plume Altitude [m]')
        ax2.setLabel('left', 'Plume Direction [deg]')
        self.flux_legend = ax0.addLegend()

        graph_layout.addWidget(self.flux_graphwin)

        # Add a tab for the map
        mapTab = QWidget()
        self.stationTabHolder.addTab(mapTab, 'Station Map')

        # Create the map axes
        map_layout = QGridLayout(mapTab)
        self.map_graphwin = pg.GraphicsLayoutWidget(show=True)
        self.map_ax = self.map_graphwin.addPlot(row=0, col=0)
        self.map_ax.setAspectLocked()
        self.map_ax.setDownsampling(mode='peak')
        self.map_ax.setClipToView(True)
        self.map_ax.showGrid(x=True, y=True)
        self.map_ax.setLabel('bottom', 'Time')

        # Create the plot of the volcano
        scatter = pg.ScatterPlotItem(size=20, pen=pg.mkPen(COLORS[7]),
                                     brush=pg.mkBrush(COLORS[3]))
        scatter.setToolTip("Volcano")
        line = pg.PlotCurveItem(pen=pg.mkPen(COLORS[3], width=2))
        arrow = pg.ArrowItem(pen=pg.mkPen(COLORS[3], width=2), tipAngle=45,
                             baseAngle=25, brush=pg.mkBrush(COLORS[3]))
        line.setToolTip("Plume")
        arrow.setToolTip("Plume")
        self.map_ax.addItem(line)
        self.map_ax.addItem(arrow)
        self.map_ax.addItem(scatter)
        self.map_plots = {'volcano': [scatter, line, arrow]}

        # Connect changes in the volcano location to the plot
        self.widgets['vlat'].textChanged.connect(self.update_map)
        self.widgets['vlon'].textChanged.connect(self.update_map)
        self.widgets['plume_dir'].valueChanged.connect(self.update_map)

        # Add axis labels
        self.map_ax.setLabel('left', 'Latitude [deg]')
        self.map_ax.setLabel('bottom', 'Longitude [deg]')

        map_layout.addWidget(self.map_graphwin)

        # Initialise dictionaries to hold the station widgets
        self.station_log = {}
        self.station_plot_lines = {}
        self.station_axes = {}
        self.station_status = {}
        self.station_graphwin = {}
        self.flux_lines = {}
        self.station_widgets = {}

        # Add station tabs
        self.stationTabs = OrderedDict()
        for station in self.stations.values():
            self.add_station(station)
        layout.addWidget(self.stationTabHolder, 0, 0, 1, 10)

        # Add a button to add a station
        self.add_station_btn = QPushButton('Add Station')
        self.add_station_btn.setFixedSize(150, 25)
        self.add_station_btn.clicked.connect(self.new_station)
        layout.addWidget(self.add_station_btn, 1, 0)

    def update_map(self):
        """Update the volcano location."""
        try:
            x = float(self.widgets.get('vlon'))
            y = float(self.widgets.get('vlat'))
            az = self.widgets.get('plume_dir')
            ay, ax = calc_end_point([y, x], 5000, az)
            self.map_plots['volcano'][0].setData([x], [y])
            self.map_plots['volcano'][1].setData([x, ax], [y, ay])
            self.map_plots['volcano'][2].setPos(ax, ay)
            self.map_plots['volcano'][2].setStyle(angle=az+90)
        except ValueError:
            pass

# =============================================================================
#   Add Scanning Stations
# =============================================================================

    def add_station(self, name, com_info, loc_info):
        """Add station controls and displays to a new tab."""
        # Create the station object
        self.stations[name] = Station(name, com_info, loc_info)

        # Create the tab to hold the station widgets
        self.stationTabs[name] = QWidget()
        self.stationTabHolder.addTab(self.stationTabs[name],
                                     str(name))

        # Set up the station layout
        layout = QGridLayout(self.stationTabs[name])

        # Add a status notifier
        self.station_status[name] = QLabel('Status: -')
        coln = 0
        layout.addWidget(self.station_status[name], 0, coln)
        layout.addWidget(QVLine(), 0, coln+1)
        coln += 2

        # Add the station location
        stat_lat = f'{abs(loc_info["latitude"])}'
        if loc_info["latitude"] >= 0:
            stat_lat += u"\N{DEGREE SIGN}N"
        else:
            stat_lat += u"\N{DEGREE SIGN}S"
        stat_lon = f'{abs(loc_info["longitude"])}'
        if loc_info["longitude"] >= 0:
            stat_lon += u"\N{DEGREE SIGN}E"
        else:
            stat_lon += u"\N{DEGREE SIGN}W"
        stat_loc = QLabel(f'Location: {stat_lat}, {stat_lon}')
        layout.addWidget(stat_loc, 0, coln)
        layout.addWidget(QVLine(), 0, coln+1)
        coln += 2

        # Add the station altitude
        stat_alt = QLabel(f'Altitude: {loc_info["altitude"]} m')
        layout.addWidget(stat_alt, 0, coln)
        layout.addWidget(QVLine(), 0, coln+1)
        coln += 2

        # Add the station orientation
        stat_az = QLabel(f'Orientation: {loc_info["azimuth"]}'
                         + u"\N{DEGREE SIGN}")
        layout.addWidget(stat_az, 0, coln)
        layout.addWidget(QVLine(), 0, coln+1)
        coln += 2

        # Add button to edit the station
        edit_btn = QPushButton('Edit Station')
        edit_btn.clicked.connect(lambda: self.edit_station(name))
        layout.addWidget(edit_btn, 0, coln)
        coln += 1

        # Add button to delete the station
        close_btn = QPushButton('Delete Station')
        close_btn.clicked.connect(lambda: self.del_station(name))
        layout.addWidget(close_btn, 0, coln)
        coln += 1

        # Add the station widgets to a dictionary
        self.station_widgets[name] = {'loc': stat_loc, 'az': stat_az}

        # Create the graphs
        self.station_graphwin[name] = pg.GraphicsLayoutWidget(show=True)
        pg.setConfigOptions(antialias=True)

        # Make the graphs
        ax0 = self.station_graphwin[name].addPlot(row=0, col=0)
        x_axis = pg.DateAxisItem(utcOffset=0)
        ax1 = self.station_graphwin[name].addPlot(row=0, col=1,
                                                  axisItems={'bottom': x_axis})
        self.station_axes[name] = [ax0, ax1]

        for ax in self.station_axes[name]:
            ax.setDownsampling(mode='peak')
            ax.setClipToView(True)
            ax.showGrid(x=True, y=True)

        # Add axis labels
        ax0.setLabel('left', 'SO2 SCD [molec/cm2]')
        ax1.setLabel('left', 'SO2 Flux [kg/s]')
        ax0.setLabel('bottom', 'Scan Angle [deg]')
        ax1.setLabel('bottom', 'Time [UTC]')

        # Initialise the lines
        p0 = pg.mkPen(color='#1f77b4', width=1.0)
        l0 = pg.PlotCurveItem(pen=p0)
        e1 = pg.ErrorBarItem(pen=p0)
        l1 = pg.PlotCurveItem(pen=p0)
        ax0.addItem(l0)
        ax1.addItem(e1)
        ax1.addItem(l1)
        self.station_plot_lines[name] = [l0, e1, l1]

        # Create a textbox to hold the station logs
        self.station_log[name] = QPlainTextEdit(self)
        self.station_log[name].setReadOnly(True)
        self.station_log[name].setFont(QFont('Courier', 10))

        # Add overview plot lines
        pen = pg.mkPen(color=COLORS[len(self.stations.keys())-1], width=1.0)
        fe0 = pg.ErrorBarItem(pen=pen)
        fl0 = pg.PlotCurveItem(pen=pen)
        fl1 = pg.PlotCurveItem(pen=pen)
        fl2 = pg.PlotCurveItem(pen=pen)
        self.flux_axes[0].addItem(fe0)
        self.flux_axes[0].addItem(fl0)
        self.flux_axes[1].addItem(fl1)
        self.flux_axes[2].addItem(fl2)
        self.flux_lines[name] = [fe0, fl0, fl1, fl2]
        self.flux_legend.addItem(fl0, name)

        # Add station to map plot
        scatter = pg.ScatterPlotItem(x=[loc_info['longitude']],
                                     y=[loc_info['latitude']],
                                     size=15, brush=pg.mkBrush(COLORS[0]))
        line = pg.PlotCurveItem(pen=pg.mkPen(COLORS[0], width=2))
        arrow = pg.ArrowItem(baseAngle=25, brush=pg.mkBrush(COLORS[0]))
        scatter.setToolTip(name)
        self.map_ax.addItem(scatter)
        self.map_ax.addItem(line)
        self.map_ax.addItem(arrow)
        self.map_plots[name] = [scatter, line, arrow]
        self.update_station_map(name)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.station_graphwin[name])
        splitter.addWidget(self.station_log[name])
        layout.addWidget(splitter, 1, 0, 1, coln)

        logger.info(f'Added {name} station')

    def del_station(self, name):
        """Remove a station tab."""
        # Get the index of the station tab
        station_idx = [i for i, key in enumerate(self.stationTabs.keys())
                       if name == key][0] + 2

        # Remove the tab from the GUI
        self.stationTabHolder.removeTab(station_idx)

        # Delete the actual widget from memory
        self.stationTabs[name].setParent(None)

        # Remove the station from the stations dictionary
        self.stations.pop(name)

        # Remove the station from the flux legend
        self.flux_legend.removeItem(name)

        # Remove the station from the map
        for item in self.map_plots[name]:
            self.map_ax.removeItem(item)
        self.map_plots.pop(name)

        logger.info(f'Removed {name} station')

    def new_station(self):
        """Input new information for a station."""
        dialog = NewStationWizard(self)
        if dialog.exec_():
            self.add_station(**dialog.station_info)

    def edit_station(self, name):
        """Edit information for a station."""
        station = self.stations[name]
        dialog = EditStationWizard(self, station)
        if dialog.exec_():
            # Edit the station object
            self.stations[name] = dialog.station

            # Edit the text on the station tab
            loc_info = station.loc_info
            stat_lat = f'{abs(loc_info["latitude"])}'
            if loc_info["latitude"] >= 0:
                stat_lat += u"\N{DEGREE SIGN}N"
            else:
                stat_lat += u"\N{DEGREE SIGN}S"
            stat_lon = f'{abs(loc_info["longitude"])}'
            if loc_info["longitude"] >= 0:
                stat_lon += u"\N{DEGREE SIGN}E"
            else:
                stat_lon += u"\N{DEGREE SIGN}W"
            self.station_widgets[name]['loc'].setText(f'Location: {stat_lat}, '
                                                      + f'{stat_lon}')
            self.station_widgets[name]['az'].setText('Orientation: '
                                                     + f'{loc_info["azimuth"]}'
                                                     + u"\N{DEGREE SIGN}")

            # Update the station map
            self.update_station_map(name)

            logger.info(f'{name} station updated')

    def update_station_map(self, name):
        """Update station on the map."""
        loc_info = self.stations[name].loc_info

        x = loc_info['longitude']
        y = loc_info['latitude']
        az = loc_info['azimuth']
        y0, x0 = calc_end_point([y, x], 2500, az-90)
        y1, x1 = calc_end_point([y, x], 2500, az+90)
        self.map_plots[name][0].setData(x=[x], y=[y])
        self.map_plots[name][1].setData([x0, x1], [y0, y1])
        self.map_plots[name][2].setPos(x, y)
        self.map_plots[name][2].setStyle(angle=az+90)

# =============================================================================
#   Syncing Controls
# =============================================================================

    def _toggle_sync(self):
        """Toggle syncing."""
        # If syncing if ON, turn it OFF
        if self.syncing:
            self.sync_button.setText('Syncing OFF')
            self.sync_button.setStyleSheet("background-color: red")
            self.widgets['sync_interval'].setDisabled(False)
            self.widgets['sync_interval'].setStyleSheet("color: white")
            self.syncing = False
            self.syncTimer.stop()

        # iF syncing is OFF, turn it ON
        else:
            self.sync_button.setText('Syncing ON')
            self.sync_button.setStyleSheet("background-color: green")
            self.syncing = True
            interval = self.widgets.get('sync_interval') * 1000
            self.widgets['sync_interval'].setDisabled(True)
            self.widgets['sync_interval'].setStyleSheet("color: darkGray")
            self._station_sync()
            self.syncTimer = QTimer(self)
            self.syncTimer.setInterval(interval)
            self.syncTimer.timeout.connect(self._station_sync)
            self.syncTimer.start()

    def _station_sync(self):

        # If the previous sync thread is still running, wait a cycle
        try:
            if self.syncThread.isRunning():
                return
        except AttributeError:
            pass

        # Check that the program is within the syncing time
        start_time = datetime.strptime(self.widgets.get('sync_start_time'),
                                       "%H:%M").time()
        stop_time = datetime.strptime(self.widgets.get('sync_stop_time'),
                                      "%H:%M").time()

        now_time = datetime.now().time()

        sync_mode = 'so2'

        if now_time < start_time or now_time > stop_time:
            logger.info('Not within syncing time window')
            return

        logger.info('Beginning scanner sync')

        # Get today's date
        self.analysis_date = datetime.now().date()

        # Get the volcano location
        volc_loc = [float(self.widgets.get('vlat')),
                    float(self.widgets.get('vlon'))]

        # Get the default altitude and azimuth
        default_alt = float(self.widgets.get('plume_alt'))
        default_az = float(self.widgets.get('plume_dir'))

        # Get the scan pair time
        scan_pair_time = self.widgets.get('scan_pair_time')
        scan_pair_flag = self.widgets.get('scan_pair_flag')

        self.statusBar().showMessage('Syncing...')

        # Initialise the sync thread
        self.syncThread = QThread()
        self.syncWorker = SyncWorker(self.stations, self.analysis_date,
                                     sync_mode, volc_loc, default_alt,
                                     default_az, scan_pair_time,
                                     scan_pair_flag)

        # Move the worker to the thread
        self.syncWorker.moveToThread(self.syncThread)

        # Connect the signals
        self.syncThread.started.connect(self.syncWorker.run)
        self.syncWorker.finished.connect(self.sync_finished)
        self.syncWorker.error.connect(self.update_error)
        self.syncWorker.updateLog.connect(self.update_station_log)
        self.syncWorker.updateStationStatus.connect(self.update_stat_status)
        self.syncWorker.updateGuiStatus.connect(self.update_gui_status)
        self.syncWorker.updatePlots.connect(self.update_scan_plot)
        self.syncWorker.updateFluxPlot.connect(self.update_flux_plots)
        self.syncWorker.finished.connect(self.syncThread.quit)

        # Start the flag
        self.syncThread.start()

# =============================================================================
# Flux Post Analysis
# =============================================================================

    def _flux_post_analysis(self):

        # If the previous sync thread is still running, wait a cycle
        try:
            if self.postThread.isRunning():
                return
        except AttributeError:
            pass

        self.analysis_date = self.widgets.get('date_to_analyse')

        # Get the volcano location
        volc_loc = [float(self.widgets.get('vlat')),
                    float(self.widgets.get('vlon'))]

        # Get the default altitude and azimuth
        default_alt = float(self.widgets.get('plume_alt'))
        default_az = float(self.widgets.get('plume_dir'))

        # Get the scan pair time
        scan_pair_time = self.widgets.get('scan_pair_time')
        scan_pair_flag = self.widgets.get('scan_pair_flag')

        # Initialise the sync thread
        self.postThread = QThread()
        self.postWorker = PostAnalysisWorker(self.stations, self.analysis_date,
                                             volc_loc, default_alt, default_az,
                                             scan_pair_time, scan_pair_flag)

        # Move the worker to the thread
        self.postWorker.moveToThread(self.postThread)

        # Connect the signals
        self.postThread.started.connect(self.postWorker.run)
        self.postWorker.finished.connect(self.post_finished)
        self.postWorker.error.connect(self.update_error)
        self.postWorker.updateGuiStatus.connect(self.update_gui_status)
        self.postWorker.updateFluxPlot.connect(self.update_flux_plots)
        self.postWorker.finished.connect(self.postThread.quit)

        # Start the flag
        self.postThread.start()

# =============================================================================
#   Gui Slots
# =============================================================================

    def update_error(self, error):
        """Slot to update error messages from the worker."""
        exctype, value, trace = error
        logger.warning(f'Uncaught exception!\n{trace}')

    def sync_finished(self):
        """Signal end of sync."""
        logger.info('Sync complete')

    def post_finished(self):
        """Signal end of post analysis."""

    def update_gui_status(self, status):
        """Update the status."""
        self.statusBar().showMessage(status)

    def update_stat_status(self, name, time, status):
        """Update the station staus."""
        self.station_status[name].setText(f'Status: {status}')

    def update_station_log(self, station, log_text):
        """Slot to update the station logs."""
        text = self.station_log[station].toPlainText().split('\n')
        for line in log_text[len(text):]:
            self.station_log[station].appendPlainText(line.strip())

    def update_scan_plot(self, s, fname):
        """Update the plots."""
        # Load the scan file, unpacking the angle and SO2 data
        scan_df = pd.read_csv(fname)
        plotx = scan_df['Angle'].dropna().to_numpy()
        ploty = scan_df['SO2'].dropna().to_numpy()

        # Check for large numbers in the ydata. This is due to a
        # bug in pyqtgraph not displaying large numbers
        if np.nanmax(ploty) > 1e6:
            order = int(np.ceil(np.log10(np.nanmax(ploty)))) - 1
            ploty = ploty / 10**order
            self.station_axes[s][0].setLabel('left',
                                             f'SO2 SCD (1e{order} molec/cm2)')

        self.station_plot_lines[s][0].setData(x=plotx, y=ploty)

    # @pyqtSlot()
    def update_flux_plots(self):
        """Display the calculated fluxes."""
        # Cycle through the stations
        for name, station in self.stations.items():

            # Get the flux output file
            flux_fpath = f'Results/{self.analysis_date}/{name}/' \
                         + f'{self.analysis_date}_{name}_fluxes.csv'

            # Read the flux file
            try:
                flux_df = pd.read_csv(flux_fpath, parse_dates=['Time [UTC]'])
            except FileNotFoundError:
                logger.warning(f'Flux file not found for {name}!')
                continue

            # Extract the data, converting to UNIX time for the x-axis
            xdata = np.array([t.timestamp() for t in flux_df['Time [UTC]']])
            flux = flux_df['Flux [kg/s]'].to_numpy()
            flux_err = flux_df['Flux Err [kg/s]'].to_numpy()
            plume_alt = flux_df['Plume Altitude [m]'].to_numpy()
            plume_dir = flux_df['Plume Direction [deg]'].to_numpy()
            self.station_plot_lines[name][1].setData(x=xdata, y=flux,
                                                     height=flux_err)
            self.station_plot_lines[name][2].setData(x=xdata, y=flux)

            # Also update the flux plots
            self.flux_lines[name][0].setData(x=xdata, y=flux, height=flux_err)
            self.flux_lines[name][1].setData(x=xdata, y=flux)
            self.flux_lines[name][2].setData(x=xdata, y=plume_alt)
            self.flux_lines[name][3].setData(x=xdata, y=plume_dir)

# =============================================================================
#   Configuratuion Controls
# =============================================================================

    def save_config(self, asksavepath=True):
        """Save the config file."""
        # Get the GUI configuration
        config = {}
        for label in self.widgets:
            config[label] = self.widgets.get(label)
        config['theme'] = self.theme

        # Add the station ssettings to the config
        config['stations'] = {}
        for name, station in self.stations.items():
            config['stations'][name] = {'com_info': station.com_info,
                                        'loc_info': station.loc_info}

        # Get save filename if required
        if asksavepath or self.config_fname is None:
            filter = 'YAML (*.yml *.yaml);;All Files (*)'
            fname, s = QFileDialog.getSaveFileName(self, 'Save Config', '',
                                                   filter)
            # If valid, proceed. If not, return
            if fname != '' and fname is not None:
                self.config_fname = fname
            else:
                return

        # Write the config
        with open(self.config_fname, 'w') as outfile:
            yaml.dump(config, outfile)

        # Log the update
        logger.info(f'Config file saved to {self.config_fname}')

        # Record the path for next load
        with open('bin/.config', 'w') as w:
            w.write(self.config_fname)

        self.config = config

    def load_config(self, fname=None):
        """Read the config file."""
        if fname is None:
            filter = 'YAML (*.yml *.yaml);;All Files (*)'
            fname, tfile = QFileDialog.getOpenFileName(self, 'Load Config', '',
                                                       filter)

        if fname is None:
            return {}

        # Open the config file
        try:
            with open(fname, 'r') as ymlfile:
                config = yaml.load(ymlfile, Loader=yaml.FullLoader)

            for key, value in config.items():
                try:
                    if key == 'theme':
                        self.theme = value
                    elif key == 'stations':
                        for name, info in value.items():
                            self.add_station(name, **info)
                    else:
                        self.widgets.set(key, value)
                except Exception:
                    logger.warning(f'Failed to load {key} from config file')

        except FileNotFoundError:
            logger.warning(f'Unable to load config file {self.config_fname}')
            config = {}
        self.config = config
        logger.info(f'Configuration loaded from {self.config_fname}')
        return config

# =============================================================================
#   Theme changing
# =============================================================================

    def change_theme(self):
        """Change the theme."""
        if self.theme == 'Light':
            self.changeThemeDark()
            self.theme = 'Dark'
        elif self.theme == 'Dark':
            self.changeThemeLight()
            self.theme = 'Light'

    @pyqtSlot()
    def changeThemeDark(self):
        """Change theme to dark."""
        darkpalette = QPalette()
        darkpalette.setColor(QPalette.Window, QColor(53, 53, 53))
        darkpalette.setColor(QPalette.WindowText, Qt.white)
        darkpalette.setColor(QPalette.Base, QColor(25, 25, 25))
        darkpalette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        darkpalette.setColor(QPalette.ToolTipBase, Qt.black)
        darkpalette.setColor(QPalette.ToolTipText, Qt.white)
        darkpalette.setColor(QPalette.Text, Qt.white)
        darkpalette.setColor(QPalette.Button, QColor(53, 53, 53))
        darkpalette.setColor(QPalette.Active, QPalette.Button,
                             QColor(53, 53, 53))
        darkpalette.setColor(QPalette.ButtonText, Qt.white)
        darkpalette.setColor(QPalette.BrightText, Qt.red)
        darkpalette.setColor(QPalette.Link, QColor(42, 130, 218))
        darkpalette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        darkpalette.setColor(QPalette.HighlightedText, Qt.black)
        darkpalette.setColor(QPalette.Disabled, QPalette.ButtonText,
                             Qt.darkGray)
        QApplication.instance().setPalette(darkpalette)

        pen = pg.mkPen('w', width=1)

        self.flux_graphwin.setBackground('k')
        self.map_graphwin.setBackground('k')
        for ax in self.flux_axes + [self.map_ax]:
            ax.getAxis('left').setPen(pen)
            ax.getAxis('right').setPen(pen)
            ax.getAxis('top').setPen(pen)
            ax.getAxis('bottom').setPen(pen)
            ax.getAxis('left').setTextPen(pen)
            ax.getAxis('bottom').setTextPen(pen)

        for name, station in self.stations.items():
            self.station_graphwin[name].setBackground('k')
            for ax in self.station_axes[name]:
                ax.getAxis('left').setPen(pen)
                ax.getAxis('right').setPen(pen)
                ax.getAxis('top').setPen(pen)
                ax.getAxis('bottom').setPen(pen)
                ax.getAxis('left').setTextPen(pen)
                ax.getAxis('bottom').setTextPen(pen)

    @pyqtSlot()
    def changeThemeLight(self):
        """Change theme to light."""
        QApplication.instance().setPalette(self.style().standardPalette())
        pen = pg.mkPen('k', width=1)

        self.flux_graphwin.setBackground('w')
        self.map_graphwin.setBackground('w')
        for ax in self.flux_axes + [self.map_ax]:
            ax.getAxis('left').setPen(pen)
            ax.getAxis('right').setPen(pen)
            ax.getAxis('top').setPen(pen)
            ax.getAxis('bottom').setPen(pen)
            ax.getAxis('left').setTextPen(pen)
            ax.getAxis('bottom').setTextPen(pen)

        for name, station in self.stations.items():
            self.station_graphwin[name].setBackground('w')
            for ax in self.station_axes[name]:
                ax.getAxis('left').setPen(pen)
                ax.getAxis('right').setPen(pen)
                ax.getAxis('top').setPen(pen)
                ax.getAxis('bottom').setPen(pen)
                ax.getAxis('left').setTextPen(pen)
                ax.getAxis('bottom').setTextPen(pen)


class NewStationWizard(QDialog):
    """Opens a wizard to define a new station."""

    def __init__(self, parent=None):
        """Initialise the window."""
        super(NewStationWizard, self).__init__(parent)

        # Set the window properties
        self.setWindowTitle('Add new station')
        self.station_data = {}

        self._createApp()

    def _createApp(self):
        # Set the layout
        layout = QFormLayout()

        # Setup entry widgets
        self.widgets = {'Name': QLineEdit(),
                        'Latitude': QLineEdit(),
                        'Longitude': QLineEdit(),
                        'Altitude': QLineEdit(),
                        'Azimuth': QLineEdit(),
                        'Host': QLineEdit(),
                        'Username': QLineEdit(),
                        'Password': QLineEdit()}
        for key, item in self.widgets.items():
            layout.addRow(key + ':', item)

        # Add cancel and accept buttons
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.cancel_action)
        accept_btn = QPushButton('Accept')
        accept_btn.clicked.connect(self.accept_action)
        layout.addRow(cancel_btn, accept_btn)

        self.setLayout(layout)

    def accept_action(self):
        """Record the station data and exit."""
        try:
            loc_info = {}
            loc_info['latitude'] = float(self.widgets['Latitude'].text())
            loc_info['longitude'] = float(self.widgets['Longitude'].text())
            loc_info['altitude'] = float(self.widgets['Altitude'].text())
            loc_info['azimuth'] = float(self.widgets['Azimuth'].text())
            com_info = {}
            com_info['host'] = self.widgets['Host'].text()
            com_info['username'] = self.widgets['Username'].text()
            com_info['password'] = self.widgets['Password'].text()
        except ValueError:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error adding station, please check input fields.")
            msg.setWindowTitle("Error!")
            msg.setDetailedText(traceback.format_exc())
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return

        self.station_info = {'name': self.widgets['Name'].text(),
                             'loc_info': loc_info,
                             'com_info': com_info}
        self.accept()

    def cancel_action(self):
        """Close the window without creating a new station."""
        self.station_info = {}
        self.close()


class EditStationWizard(QDialog):
    """Opens a wizard to define a new station."""

    def __init__(self, parent=None, station=None):
        """Initialise the window."""
        super(EditStationWizard, self).__init__(parent)

        # Set the window properties
        self.setWindowTitle(f'Edit {station.name} station')
        self.station = station
        self.loc_info = station.loc_info
        self.com_info = station.com_info
        self.station_data = {}

        self._createApp()

    def _createApp(self):
        # Set the layout
        layout = QFormLayout()

        # Setup entry widgets
        self.widgets = {
            'Name': QLineEdit(str(self.station.name)),
            'Latitude': QLineEdit(str(self.loc_info['latitude'])),
            'Longitude': QLineEdit(str(self.loc_info['longitude'])),
            'Altitude': QLineEdit(str(self.loc_info['altitude'])),
            'Azimuth': QLineEdit(str(self.loc_info['azimuth'])),
            'Host': QLineEdit(str(self.com_info['host'])),
            'Username': QLineEdit(str(self.com_info['username'])),
            'Password': QLineEdit(str(self.com_info['password']))}
        for key, item in self.widgets.items():
            layout.addRow(key + ':', item)

        # Add cancel and accept buttons
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.cancel_action)
        accept_btn = QPushButton('Accept')
        accept_btn.clicked.connect(self.accept_action)
        layout.addRow(cancel_btn, accept_btn)

        self.setLayout(layout)

    def accept_action(self):
        """Record the station data and exit."""
        try:
            loc_info = {}
            loc_info['latitude'] = float(self.widgets['Latitude'].text())
            loc_info['longitude'] = float(self.widgets['Longitude'].text())
            loc_info['altitude'] = float(self.widgets['Altitude'].text())
            loc_info['azimuth'] = float(self.widgets['Azimuth'].text())

            com_info = {}
            com_info['host'] = self.widgets['Host'].text()
            com_info['username'] = self.widgets['Username'].text()
            com_info['password'] = self.widgets['Password'].text()
        except ValueError:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Error adding station, please check input fields.")
            msg.setWindowTitle("Error!")
            msg.setDetailedText(traceback.format_exc())
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec_()
            return

        self.station.name = self.widgets['Name'].text()
        self.station.loc_info = loc_info
        self.station.com_info = com_info
        self.accept()

    def cancel_action(self):
        """Close the window without editing the station."""
        self.close()


class QHLine(QFrame):
    """Horizontal line widget."""

    def __init__(self):
        """Initialize."""
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class QVLine(QFrame):
    """Horizontal line widget."""

    def __init__(self):
        """Initialize."""
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)


# Cliet Code
def main():
    """Run main function."""
    # Create an instance of QApplication
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Show the GUI
    view = MainWindow()
    view.show()

    # Execute the main loop
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
