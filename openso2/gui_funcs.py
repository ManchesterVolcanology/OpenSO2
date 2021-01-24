import os
import sys
import logging
import traceback
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QRunnable
from PyQt5.QtWidgets import (QComboBox, QTextEdit, QLineEdit, QDoubleSpinBox,
                             QSpinBox, QCheckBox, QPlainTextEdit)


class QTextEditLogger(logging.Handler, QObject):
    """Records logs to the GUI"""
    appendPlainText = pyqtSignal(str)

    def __init__(self, parent):
        super().__init__()
        QObject.__init__(self)
        self.widget = QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self.widget.setFont(QFont('Courier', 10))
        self.appendPlainText.connect(self.widget.appendPlainText)

    def emit(self, record):
        msg = self.format(record)
        self.appendPlainText.emit(msg)


# Create a worker signals object to handle worker signals
class WorkerSignals(QObject):
    """Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data
    progress
        `int` indicating % progress
    plotter
        `list` data to be plotted on the analysis graphs
    error
        `tuple` (exctype, value, traceback.format_exc() )
    status
        'str' status message for the GUI
    spectrum
        `tuple` spectrum to be displayed on the scope graph
    """
    finished = pyqtSignal()
    plot = pyqtSignal(str, str)
    log = pyqtSignal(str, list)


# Create a worker to handle QThreads
class Worker(QRunnable):
    """Worker thread

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

    @pyqtSlot()
    def run(self):
        """Initialise the runner function with passed args, kwargs"""

        # Retrieve args/kwargs here; and fire processing using them
        try:
            self.fn(self, *self.args, **self.kwargs)
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))

        # Done
        self.signals.finished.emit()


def sync_station(worker, station, today_date, log_callback, plot_callback):
    """Sync the log file and write to the text file"""

    # Sync the station log
    fname, err = station.pull_log()

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

    # Plot last scan
    if len(new_fnames) != 0:
        plot_callback.emit(station.name, local_dir + new_fnames[-1])


# =============================================================================
# Spinbox
# =============================================================================

# Create a Spinbox object for ease
class DSpinBox(QDoubleSpinBox):
    """Object for generating custom float spinboxes"""

    def __init__(self, value, range):
        super().__init__()
        self.setRange(*range)
        self.setValue(value)


class SpinBox(QSpinBox):
    """Object for generating custom integer spinboxes"""

    def __init__(self, value, range):
        super().__init__()
        self.setRange(*range)
        self.setValue(value)


# =============================================================================
# Widgets Object
# =============================================================================

class Widgets(dict):
    """Object to allow easy config/info transfer with PyQT Widgets"""

    def __init__(self):
        super().__init__()

    def get(self, key):
        """Get the value of a widget"""
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
        """Set the value of a widget"""
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
