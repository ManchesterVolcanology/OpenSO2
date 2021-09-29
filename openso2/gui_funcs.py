"""Useful functions for the GUI."""

import os
import sys
import logging
import traceback
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from datetime import datetime, timedelta
from PySide2.QtGui import QFont
from PySide2.QtCore import Qt, QObject, Signal, Slot, QRunnable
from PySide2.QtWidgets import (QComboBox, QTextEdit, QLineEdit, QDoubleSpinBox,
                               QSpinBox, QCheckBox, QDateTimeEdit,
                               QPlainTextEdit)

from openso2.plume import calc_plume_altitude, calc_scan_flux


logger = logging.getLogger(__name__)


# =============================================================================
# Logging text box
# =============================================================================

class MyLog(QObject):
    """Signal for logs."""

    signal = Signal(str)


class QTextEditLogger(logging.Handler):
    """Record logs to the GUI."""

    def __init__(self, parent):
        """Initialise."""
        super().__init__()
        self.log = MyLog()
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setFont(QFont('Courier', 10))
        self.log.signal.connect(self.widget.appendPlainText)

    @Slot()
    def emit(self, record):
        """Emit the log."""
        msg = self.format(record)
        self.log.signal.emit(msg)


# =============================================================================
# Station Sync Worker
# =============================================================================


class SyncWorker(QObject):
    """Handle station syncing."""

    # Define signals
    finished = Signal()
    updateLog = Signal(str, list)

    def __init__(self, stations, today_date, volc_loc, default_alt,
                 default_az):
        """Initialize."""
        super(QObject, self).__init__()
        self.stations = stations
        self.today_date = today_date
        self.volc_loc = volc_loc
        self.default_alt = default_alt
        self.default_az = default_az

    def run(self):
        """Launch worker task."""
        try:
            self._run()
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.error.emit((exctype, value, traceback.format_exc()))
        self.finished.emit()

    def _run(self):
        pass


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
        """Initialize."""
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


def sync_stations(worker, widgets, stations, today_date, vent_loc, default_alt,
                  default_az, scan_pair_time, scan_pair_flag, log_callback,
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
    calculate_fluxes(stations, scans, today_date, vent_loc, default_alt,
                     default_az, scan_pair_time, scan_pair_flag)

    # Plot the fluxes on the GUI
    flux_callback.emit()

    logger.info('Sync complete')

    gui_status_callback.emit('Ready')


def calculate_fluxes(stations, scans, today_date, vent_loc, default_alt,
                     default_az, scan_pair_time, scan_pair_flag, min_scd=-1e17,
                     max_scd=1e20, plume_scd=1e17, good_scan_lim=0.2,
                     sg_window=11, sg_polyn=3):
    """Calculate the flux from a set of scans."""
    # Get the existing scan database
    scan_fnames, scan_times = get_local_scans(stations, today_date)

    # For each station calculate fluxes
    for name, station in stations.items():

        logger.info(f'Calculating fluxes for {name}')

        # Set filepath to scan data
        fpath = f'Results/{today_date}/{name}/so2/'

        for scan_fname in scans[name]:

            # Read in the scan
            scan_df = pd.read_csv(fpath + scan_fname)

            # Filter the scan
            msk_scan_df, peak, msg = filter_scan(scan_df, min_scd, max_scd,
                                                 plume_scd, good_scan_lim,
                                                 sg_window, sg_polyn)

            if msk_scan_df is None:
                logger.info(f'Scan {scan_fname} not analysed. {msg}')
                continue

            # Pull the scan time from the filename
            scan_time = datetime.strptime(os.path.split(scan_fname)[1][:14],
                                          '%Y%m%d_%H%M%S')

            # Find the nearest scan from other stations
            near_fname, near_ts, alt_name = find_nearest_scan(name, scan_time,
                                                              scan_fnames,
                                                              scan_times)

            # Calculate the time difference
            time_diff = scan_time - near_ts
            delta_time = timedelta(minutes=scan_pair_time)
            if time_diff < delta_time and scan_pair_flag:

                # Read in the scan
                alt_scan_df = pd.read_csv(near_fname)

                # Filter the scan
                alt_msk_df, alt_peak, msg = filter_scan(alt_scan_df, min_scd,
                                                        max_scd, plume_scd,
                                                        good_scan_lim,
                                                        sg_window, sg_polyn)

                # If the alt scan is good, calculate the plume altitude
                if alt_msk_df is None:
                    plume_alt = default_alt
                    plume_az = default_az
                else:
                    alt_station = stations[alt_name]
                    plume_alt, plume_az = calc_plume_altitude(station,
                                                              alt_station,
                                                              peak,
                                                              alt_peak,
                                                              vent_loc,
                                                              default_alt)

            # If scans are too far appart, use default values
            else:
                plume_alt = default_alt
                plume_az = default_az

            # Calculate the scan flux
            flux_amt, flux_err = calc_scan_flux(angles=scan_df['Angle'],
                                                scan_so2=[scan_df['SO2'],
                                                          scan_df['SO2_err']],
                                                station_info=station.loc_info,
                                                volcano_location=vent_loc,
                                                windspeed=1,
                                                plume_altitude=plume_alt,
                                                plume_azimuth=plume_az)

            # Format the file name of the flux output file
            flux_fname = f'Results/{today_date}/{name}/' \
                         + f'{today_date}_{name}_fluxes.csv'

            # Check the file exists
            if not os.path.exists(flux_fname):
                with open(flux_fname, 'w') as w:
                    w.write('Time [UTC],Flux [kg/s],Flux Err [kg/s]')

            # Write the results to the file
            with open(flux_fname, 'a') as w:
                w.write(f'\n{scan_time},{flux_amt},{flux_err}')


def filter_scan(scan_df, min_scd, max_scd, plume_scd, good_scan_lim,
                sg_window, sg_polyn):
    """Filter scans for quality and find the centre."""
    # Filter the points for quality
    mask = np.row_stack([scan_df['fit_quality'] != 1,
                         scan_df['SO2'] < min_scd,
                         scan_df['SO2'] > max_scd
                         ]).any(axis=0)

    if len(np.where(mask)[0]) > good_scan_lim*len(scan_df['SO2']):
        return None, None, 'Not enough good spectra'

    masked_scan_df = scan_df.mask(mask)
    so2_scd_masked = masked_scan_df['SO2']

    # Count the number of 'plume' spectra
    nplume = sum(so2_scd_masked > plume_scd)

    if nplume < 10:
        return None, None, 'Not enough plume spectra'

    # Determine the peak scan angle
    x = scan_df['Angle'][~mask].to_numpy()
    y = scan_df['SO2'][~mask].to_numpy()
    so2_filtered = savgol_filter(y, sg_window, sg_polyn, mode='nearest')
    peak_angle = x[so2_filtered.argmax()]

    return masked_scan_df, peak_angle, 'Scan analysed'


def get_local_scans(stations, today_date):
    """Find all the scans for the given day for all stations.

    Parameters
    ----------
    stations : dict
        Holds the openso2 Station objects.
    today_date : dateimte date
        The date of the analysis in question

    Returns
    -------
    scan_fnames : dict
        Dictionary of the scan filenames for each scanner
    scan_times : dict
        Dictionary of the scan timestamps ofr each scanner
    """
    # Set the results filepath
    fpath = f'Results/{today_date}'

    # Initialise empty dictionaries for the file names and timestamps
    scan_fnames = {}
    scan_times = {}

    # For each station find the available scans and there timestamps
    for name, station in stations.items():
        scan_fnames[station] = [f'{fpath}/{name}/so2/{f}'
                                for f in os.listdir(f'{fpath}/{name}/so2/')]
        scan_times = [datetime.strptime(f[:14], '%Y%m%d_%H%M%S')
                      for f in os.listdir(f'{fpath}/{name}/so2/')]

    return scan_fnames, scan_times


def find_nearest_scan(station_name, scan_time, scan_fnames, scan_times):
    """Find nearest scan from multiple other stations.

    Parameters
    ----------
    station_name : str
        The station from which the scan is being analysed.
    scan_time : datetime
        The timestamp of the scan
    scan_fnames : dict
        Dictionary of the scan filenames for each scanner
    scan_times : dict
        Dictionary of the scan timestamps ofr each scanner

    Returns
    -------
    nearest_fname : str
        The filepath to the nearest scan
    nearest_timestamp : datetime
        The timestamp of the nearest scan
    """
    # Initialise empty lists to hold the results
    nearest_scan_times = []
    nearest_scan_fnames = []

    # search through the dictionary of station scans
    for name, fnames in scan_fnames.items():

        # Skip if this is the same station
        if name == station_name:
            continue

        # Find the time difference
        delta_times = [abs(t - scan_time).total_seconds()
                       for t in scan_times[name]]

        # Find the closest time
        min_idx = np.argmin(delta_times)

        # Record the nearest scan for that station
        nearest_scan_times.append(scan_times[name][min_idx])
        nearest_scan_fnames.append(fnames[min_idx])

    # Now find the nearest of the nearest scans
    idx = np.argmin(nearest_scan_times)
    nearest_fname = nearest_scan_fnames[idx]
    nearest_timestamp = nearest_scan_times[idx]

    return nearest_fname, nearest_timestamp


# =============================================================================
# Spinbox
# =============================================================================

# Create a Spinbox object for ease
class DSpinBox(QDoubleSpinBox):
    """Object for generating custom float spinboxes."""

    def __init__(self, value, range):
        """Initialize."""
        super().__init__()
        self.setRange(*range)
        self.setValue(value)


class SpinBox(QSpinBox):
    """Object for generating custom integer spinboxes."""

    def __init__(self, value, range):
        """Initialize."""
        super().__init__()
        self.setRange(*range)
        self.setValue(value)


# =============================================================================
# Widgets Object
# =============================================================================

class Widgets(dict):
    """Object to allow easy config/info transfer with PyQT Widgets."""

    def __init__(self):
        """Initialize."""
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
        elif type(self[key]) == QDateTimeEdit:
            return self[key].textFromDateTime(self[key].dateTime())
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
        if type(self[key]) == QDateTimeEdit:
            self[key].setDateTime(self[key].dateTimeFromText(value))
        if type(self[key]) in [SpinBox, DSpinBox, QSpinBox, QDoubleSpinBox]:
            self[key].setValue(value)
