import time
import logging
import numpy as np
from datetime import datetime

try:
    import seabreeze.spectrometers as sb
    from seabreeze.spectrometers import SeaBreezeError
except ImportError:
    logging.warning('Seabreeze import failed!')
    pass


class Spectrometer():
    """Wrapper around the python-seabreeze library for controlling Ocean
    Optics spectrometers. For more information see:
    https://github.com/ap--/python-seabreeze

    Parameters
    ----------
    serial : string, optional
        The serial number of the spectrometer to use. If None connects to the
        first available device. Default is None
    integration_time : int, optional
        The integration time of the spectrometer in milliseconds. Default is
        100
    coadds : int, optional
        The number of individual spectra to average for each measurement.
        Default is 10
    correct_dark_counts : bool, optional
        Turns on electronic dark correction if available. Default is True
    correct_nonlinearity : bool, optional
        Turns on nonlinearity correction if available. Default is True

    Attributes
    ----------
    spectro : seabreeze.Spectrometer
        The spectrometer object
    serial_number : str
        The serial number of the spectrometer
    pixels : int
        The number of pixels in the sensor
    integration_time : int
        The integration time of the spectrometer in ms
    coadds : int
        The number of individual spectra to average for each measurement
    correct_dark_counts : bool
        Controls electronic dark correction onboard the spectrometer
    correct_nonlinearity : bool
        Controls nonlinearity correction onboard the spectrometer
    """

    def __init__(self, serial=None, integration_time=100, coadds=10,
                 correct_dark_counts=True, correct_nonlinearity=True):

        # Connect to the spectrometer
        try:
            self.spectro = sb.Spectrometer.from_serial_number(serial=serial)

            # Populate the serial number and pixel number
            self.serial_number = self.spectro.serial_number
            self.pixels = self.spectro.pixels

            logging.info(f'Spectrometer {self.serial_number} connected')

            # Set the initial integration time and coadds
            self.update_coadds(coadds)
            self.update_integration_time(integration_time)

            # Add the correction flags
            self.correct_dark_counts = correct_dark_counts
            self.correct_nonlinearity = correct_nonlinearity

        except SeaBreezeError:
            logging.warning('No spectrometer found')
            self.serial_number = None

    def update_integration_time(self, integration_time):
        """Update the spectrometer integrations time (ms)"""

        self.integration_time = integration_time
        self.spectro.integration_time_micros(integration_time*1000)
        logging.info(f'Updated integration time to {integration_time} ms')

    def update_coadds(self, coadds):
        """Update the number of coadds to average each spectrum over"""

        self.coadds = coadds
        logging.info(f'Updated coadds to {coadds}')

    def get_spectrum(self, fname=None):
        """Read a spectrum from the spectrometer

        Parameters
        ----------
        fname : str, optional
            File name to save the measured spectrum to. If None the spectrum is
            not saved

        Returns
        -------
        spectrum : numpy array
            2D array holding the spectrum wavelengths and intensities
        info : dict
            Contains the metadata for the spectrum
        """

        # Get the wavelengths
        x = self.spectro.wavelengths()

        # Create an empty array to hold the spectra data
        y_arr = np.zeros([self.coadds, len(x)])

        for n in range(self.coadds):
            y_arr[n] = self.spectro.intensities(self.correct_dark_counts,
                                                self.correct_nonlinearity)

        y = np.average(y_arr, axis=0)

        # Get the spectrum read time
        spec_time = datetime.now()

        # Form a dictionary of spectrum info
        info = {'serial_number': self.serial_number,
                'integration_time': self.integration_time,
                'coadds': self.coadds,
                'time': spec_time,
                'dark_correction': self.correct_dark_counts,
                'nonlin_correction': self.correct_nonlinearity,
                'fname': fname}

        if fname is not None:
            # Form the file header
            h = 'Ocean Optics spectrum file, generated by iFit\n' +\
                f'Spectrometer: {self.serial_number}\n' +\
                f'Integration time (ms): {self.integration_time}\n' +\
                f'Number of coadds: {self.coadds}\n' +\
                f'Date/Time: {spec_time}\n' +\
                f'Electronic dark correction: {self.correct_dark_counts}\n' +\
                f'Non-linearity correction: {self.correct_nonlinearity}\n' +\
                'Wavelength (nm),       Intensity (arb)'

            # Save the spectrum
            np.savetxt(fname, np.column_stack([x, y]), header=h)

        # Return the measured spectrum
        return [np.row_stack([x, y]), info]

    def close(self):
        """Close the connection to the spectrometer"""
        logging.info(f'Connection to spectrometer {self.serial_number} closed')
        self.spectro.close()


class VSpectrometer():
    """Virtual Spectrometer for testing"""

    def __init__(self, serial=None, integration_time=100, coadds=10,
                 correct_dark_counts=True, correct_nonlinearity=True):

        # Connect to the spectrometer:
        self.spectro = None

        # Populate the serial numer and pixel number
        self.serial_number = 'TEST123456'
        self.pixels = 2048

        logging.info(f'Spectrometer {self.serial_number} connected')

        # Set the initial integration time and coadds
        self.update_coadds(coadds)
        self.update_integration_time(integration_time)

        # Add the correction flags
        self.correct_dark_counts = correct_dark_counts
        self.correct_nonlinearity = correct_nonlinearity

        self.fpath = ''

    def update_integration_time(self, integration_time):
        """Update the spectrometer integrations time (ms"""

        self.integration_time = integration_time
        logging.info(f'Updated integration time to {integration_time} ms')

    def update_coadds(self, coadds):
        """Update the number of coadds to average each spectrum over"""

        self.coadds = coadds
        logging.info(f'Updated coadds to {coadds}')

    def get_spectrum(self, fname=None):
        """Read a spectrum from the spectrometer"""

        # Calculate the time to simulate reading in s
        t = self.coadds * self.integration_time / 1000
        time.sleep(t)

        # Get the wavelengths
        x, y = np.loadtxt(self.fpath, unpack=True)

        # Add a little noise for fun
        noise = np.random.normal(0, 50, y.shape)
        y += noise

        # Get the spectrum read time
        spec_time = datetime.now()

        # Form a dictionary of spectrum info
        info = {'serial_number': self.serial_number,
                'integration_time': self.integration_time,
                'coadds': self.coadds,
                'time': spec_time,
                'dark_correction': self.correct_dark_counts,
                'nonlin_correction': self.correct_nonlinearity,
                'fname': fname}

        if fname is not None:
            # Form the file header
            h = 'Ocean Optics spectrum file, generated by iFit\n' +\
                f'Spectrometer: {self.serial_number}\n' +\
                f'Integration time (ms): {self.integration_time}\n' +\
                f'Number of coadds: {self.coadds}\n' +\
                f'Date/Time: {spec_time}\n' +\
                f'Electronic dark correction: {self.correct_dark_counts}\n' +\
                f'Non-linearity correction: {self.correct_nonlinearity}\n' +\
                'Wavelength (nm),       Intensity (arb)'

            # Save the spectrum
            np.savetxt(fname, np.column_stack([x, y]), header=h)

        # Return the measured spectrum
        return [np.row_stack([x, y]), info]

    def close(self):
        """Close the connection to the spectrometer"""
        logging.info(f'Connection to spectrometer {self.serial_number} closed')
        pass
