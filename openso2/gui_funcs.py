import os
import sys
import logging
import traceback
import pandas as pd
from datetime import datetime
from PySide2.QtCore import Qt, QObject, Signal, Slot, QRunnable
from PySide2.QtWidgets import (QComboBox, QTextEdit, QLineEdit, QDoubleSpinBox,
                               QSpinBox, QCheckBox)

from openso2.calculate_flux import calc_scan_flux


logger = logging.getLogger(__name__)


class Signaller(QObject):
    """Signal for logs."""

    signal = Signal(str, logging.LogRecord)


class QtHandler(logging.Handler):
    """Logging handler for Qt application."""

    def __init__(self, slotfunc, *args, **kwargs):
        super(QtHandler, self).__init__(*args, **kwargs)
        self.signaller = Signaller()
        self.signaller.signal.connect(slotfunc)

    # @Signal()
    def emit(self, record):
        """Emit the log message and record."""
        s = self.format(record)
        self.signaller.signal.emit(s, record)


# Create a worker signals object to handle worker signals
class WorkerSignals(QObject):
    """Define the signals available from a running worker thread."""

    finished = Signal()
    plot = Signal(str, str)
    log = Signal(str, list)
    flux = Signal()
    gui_status = Signal(str)
    stat_status = Signal(str, str, str)
    error = Signal(tuple)


# Create a worker to handle QThreads
class Worker(QRunnable):
    """Worker thread.

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up

    Parameters
    ----------
    fn : function
        The function to run on the worker thread
    """

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.kwargs['log_callback'] = self.signals.log
        self.kwargs['plot_callback'] = self.signals.plot
        self.kwargs['flux_callback'] = self.signals.flux
        self.kwargs['gui_status_callback'] = self.signals.gui_status
        self.kwargs['stat_status_callback'] = self.signals.stat_status

    @Slot()
    def run(self):
        """Initialise the runner function with passed args, kwargs."""
        # Retrieve args/kwargs here; and fire processing using them
        try:
            self.fn(self, *self.args, **self.kwargs)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

        # Done
        self.signals.finished.emit()


def sync_stations(worker, stations, today_date, vent_loc, log_callback,
                  plot_callback, flux_callback, gui_status_callback,
                  stat_status_callback):
    """Sync the station logs and scans."""
    # Generate an empty dictionary to hold the scans
    scans = {}

    # Sync each station
    for station in stations.values():

        logging.info(f'Syncing {station.name} station...')

        # Sync the station status and log
        time, status, err = station.pull_status()
        fname, err = station.pull_log()

        # Update the station status
        stat_status_callback.emit(station.name, time, status)

        # Read the log file
        if fname is not None:
            with open(fname, 'r') as r:
                log_text = r.readlines()

            # Send signal with log text
            log_callback.emit(station.name, log_text)

        # Sync SO2 files
        local_dir = f'Results/{today_date}/{station.name}/so2/'
        if not os.path.isdir(local_dir):
            os.makedirs(local_dir)
        remote_dir = f'/home/pi/open_so2/Results/{today_date}/so2/'
        new_fnames, err = station.sync(local_dir, remote_dir)
        logging.info(f'Synced {len(new_fnames)} scans from {station.name}')

        # Add the scans to the dictionary
        scans[station.name] = new_fnames

        # Plot last scan
        if len(new_fnames) != 0:
            plot_callback.emit(station.name, local_dir + new_fnames[-1])

    # Calculate the fluxes
    gui_status_callback.emit('Calculating fluxes')
    calculate_fluxes(stations, scans, today_date, vent_loc)

    # Plot the fluxes on the GUI
    flux_callback.emit()

    logger.info('Sync complete')

    gui_status_callback.emit('Ready')


def calculate_fluxes(stations, scans, today_date, vent_loc):
    """Calculate the flux from a scan."""
    # Get the scan database
    # saved_scans = get_local_scans(today_date)

    # For each station calculate fluxes
    for name, station in stations.items():

        # Set filepath to scan data
        fpath = f'Results/{today_date}/{name}/so2/'

        for scan_fname in scans[name]:

            scan_df = pd.read_csv(fpath + scan_fname)

            flux_amt, flux_err = calc_scan_flux(angles=scan_df['Angle'],
                                                scan_so2=[scan_df['SO2'],
                                                          scan_df['SO2_err']],
                                                station_info=station.loc_info,
                                                volcano_location=vent_loc,
                                                windspeed=1,
                                                plume_altitude=600,
                                                plume_azimuth=270)

            scan_time = datetime.strptime(os.path.split(scan_fname)[1][:14],
                                          '%Y%m%d_%H%M%S')

            flux_fname = f'Results/{today_date}/{name}/' \
                         + f'{today_date}_{name}_fluxes.csv'

            if not os.path.exists(flux_fname):
                with open(flux_fname, 'w') as w:
                    w.write('Time [UTC],Flux [kg/s],Flux Err [kg/s]')
            with open(flux_fname, 'a') as w:
                w.write(f'\n{scan_time},{flux_amt},{flux_err}')


def get_local_scans(today_date):
    """Find al the scans for the given day for all stations."""
    # Set the results filepath
    fpath = f'Results/{today_date}'

    # Get the stations
    stations = os.listdir(fpath)

    # For each station find the available scans
    saved_scans = {}
    for station in stations:
        saved_scans[station] = [f'{fpath}/{station}/so2/{f}'
                                for f in os.listdir(f'{fpath}/{station}/so2/')]

    return saved_scans


# =============================================================================
# Spinbox
# =============================================================================

# Create a Spinbox object for ease
class DSpinBox(QDoubleSpinBox):
    """Object for generating custom float spinboxes."""

    def __init__(self, value, range):
        super().__init__()
        self.setRange(*range)
        self.setValue(value)


class SpinBox(QSpinBox):
    """Object for generating custom integer spinboxes."""

    def __init__(self, value, range):
        super().__init__()
        self.setRange(*range)
        self.setValue(value)


# =============================================================================
# Widgets Object
# =============================================================================

class Widgets(dict):
    """Object to allow easy config/info transfer with PyQT Widgets."""

    def __init__(self):
        super().__init__()

    def get(self, key):
        """Get the value of a widget."""
        if type(self[key]) == QTextEdit:
            return self[key].toPlainText()
        elif type(self[key]) == QLineEdit:
            return self[key].text()
        elif type(self[key]) == QComboBox:
            return str(self[key].currentText())
        elif type(self[key]) == QCheckBox:
            return self[key].isChecked()
        elif type(self[key]) in [SpinBox, DSpinBox, QSpinBox, QDoubleSpinBox]:
            return self[key].value()

    def set(self, key, value):
        """Set the value of a widget."""
        if type(self[key]) in [QTextEdit, QLineEdit]:
            self[key].setText(str(value))
        if type(self[key]) == QComboBox:
            index = self[key].findText(value, Qt.MatchFixedString)
            if index >= 0:
                self[key].setCurrentIndex(index)
        if type(self[key]) == QCheckBox:
            self[key].setChecked(value)
        if type(self[key]) in [SpinBox, DSpinBox, QSpinBox, QDoubleSpinBox]:
            self[key].setValue(value)
