"""Module to control the scanner head."""

import time
import atexit
import logging
import numpy as np
import xarray as xr
from threading import Thread
from datetime import datetime
from adafruit_motor import stepper
from adafruit_motorkit import MotorKit
from gpiozero import DigitalInputDevice


logger = logging.getLogger(__name__)


class Scanner:
    """Scanner class.

    Control the scanner head which consists of a stepper
    motor and a microswitch
    """

    # Initialise
    def __init__(self, switch_pin=24, step_type='single', angle_per_step=1.8,
                 home_angle=180, max_steps_home=1000, spectrometer=None,
                 gps=None, position_file=None):
        """Initialise.

        Parameters
        ----------
        switch_pin : int, optional
            The GPIO pin that connects to the home switch. Default is 24
        steptype : str, optional
            Stepping type. Must be one of:
                - single;     single step (lowest power, default)
                - double;     double step (more power but stronger)
                - interleave; finer control, has double the steps of single
                - micro;      slower but with much higher precision (8x)
            Default is single
        angle_per_step : float, optional
            The angle change with every step in degrees. Default is 1.8
        home_angle : float, optional
            The angular position (deg) of the scanner when home. Default is 180
        max_steps_home : int, optional
            Sets the maximum number of steps to look for home before giving up.
            Default is 1000.
        spectrometer : iFit Spectrometer, optional
            The spectrometer to use when taking a scan. If None, then ignored.
        gps : iFit GPS, optional
            The GPS to locate the scan. If None then ignored.
        position_file : str, optional
            File path to a file to record the current scanner position
        """
        # Connect to the home switch
        self.home_switch = DigitalInputDevice(switch_pin, pull_up=False)

        # Connect to the stepper motor
        self.motor = MotorKit().stepper1

        # Define function to release the stepper at exit
        def release_motor():
            self.motor.release()
        atexit.register(release_motor)

        # Set the initial motor position and angle (assuming scanner is home)
        self.position = np.nan
        self.home_angle = home_angle
        self.angle = home_angle

        # Set the max number of steps to home the scanner
        self.max_steps_home = max_steps_home

        # Define the angle change per step
        self.angle_per_step = angle_per_step

        # Define the type of stepping
        self.step_type = step_type

        # Create a counter for the scan number
        self.scan_number = 0

        # Add the spectrometer and gps
        self.spectrometer = spectrometer
        self.gps = gps

        # Add status filepath
        self.position_file = position_file

# =============================================================================
#   Find Home
# =============================================================================

    def find_home(self):
        """Rotate the scanner head to the home position.

        Parameters
        ----------
        None

        Returns
        -------
        steps_to_home : int
            The number of steps taken to reach home
        """
        # Log searching for home
        logger.info('Finding home position')

        # Check if already home
        if self.home_switch.value:
            logger.info('Scanner already home!')
            return 0

        # Create a counter for the number of steps taken
        i = 0

        # Set home flag to false
        self.home_flag = False

        # Launch home watcher thread
        watcher_thread = Thread(target=self._watch_for_home)
        watcher_thread.daemon = True
        watcher_thread.start()

        # Search for home
        while not self.home_flag:

            # Step the scanner
            self.step()
            i += 1

            # Check if the max home steps has been reached
            if i >= self.max_steps_home:
                logger.error(f'Scanner cannot find home after {i} steps')
                raise Exception('Error with scanner: unable to find home')

        # Log steps to home
        logger.info(f'Steps to home: {i}')

        # Once home set the motor position to 0 and set the home angle
        self.position = 0
        self.angle = self.home_angle

        return i

# =============================================================================
#   Watch for home
# =============================================================================

    def _watch_for_home(self):
        """Watch for change in home switch state."""
        self.home_switch.wait_for_active()
        self.home_flag = True

# =============================================================================
#   Move Motor
# =============================================================================

    def step(self, steps=1, direction='backward'):
        """Move the motor by a given number of steps.

        Parameters
        ----------
        steps : int
            Number of steps to move

        direction : str
            Stepping direction, either 'forward' or 'backward'

        Returns
        -------
        None
        """
        # Set stepping mode dict
        step_mode = {
            'single':     stepper.SINGLE,
            'double':     stepper.DOUBLE,
            'interleave': stepper.INTERLEAVE,
            'micro':      stepper.MICROSTEP
        }

        # Set stepping direction dict
        step_dir = {'forward':  stepper.FORWARD, 'backward': stepper.BACKWARD}

        # Perform steps
        for i in range(steps):

            # Add a short rest between steps to improve accuracy
            time.sleep(0.01)

            # Step the motor
            self.motor.onestep(
                direction=step_dir[direction], style=step_mode[self.step_type]
            )

        # Update the motor postion
        if direction == 'backward':
            self.position += steps
        elif direction == 'forward':
            self.position -= steps

        # Update the angular posiotion
        if direction == 'backward':
            self.angle += steps * self.angle_per_step
        elif direction == 'forward':
            self.angle -= steps * self.angle_per_step

        # Make sure the angle is between -180 to 180 degrees
        self.angle = ((self.angle + 180) % 360) - 180

        if self.position_file is not None:
            with open(self.position_file, 'w') as w:
                w.write(str(self.angle))

# =============================================================================
# Acquire Scan
# =============================================================================

    def acquire_scan(self, settings, save_path):
        """Acquire a scan.

        Perform a scan along the following order:
            1) Return to home position
            2) Take dark spectrum
            3) Move to scan start
            3) Take measurement spectra, stepping the scanner between each

        Parameters
        ----------
        settings : dict
            Holds the settings for the scanner
        save_path : str
            The folder to hold the scan results

        Returns
        -------
        str
            File path to the saved scan
        """
        # Create array to hold scan data
        spectra = np.zeros(
            [settings['specs_per_scan']+1, self.spectrometer.pixels]
        )
        scan_angles = np.zeros(settings['specs_per_scan']+1)

        # Return the scanner position to home
        logger.info('Returning to home position...')
        self.find_home()

        # Take the dark spectrum
        logger.info('Acquiring dark spectrum')
        self.spectrometer.fpath = 'data_bases/dark.txt'
        spectrum = self.spectrometer.get_spectrum()
        spectra[0] = spectrum.data
        wavelengths = spectrum.wavelength
        scan_angles[0] = self.angle

        # Move scanner to start position
        logger.info('Moving to start position')
        self.step(steps=settings['steps_to_start'])

        # Get the scan start time
        scan_start_time = datetime.now()
        time_str = datetime.strftime(scan_start_time, "%Y%m%d_%H%M%S")

        # Form the filename of the scan file
        fname = f'{save_path}/spectra/{time_str}_{settings["station_name"]}_' \
                f'{settings["version"]}_Scan{self.scan_number:03d}_spectra.nc'

        # Begin stepping through the scan
        logger.info('Begin main scan')

        for step_no in range(1, settings['specs_per_scan']+1):

            # Acquire the spectrum
            self.spectrometer.fpath = 'data_bases/spectrum_00360.txt'
            spectrum = self.spectrometer.get_spectrum()
            spectra[step_no] = spectrum.data
            scan_angles[step_no] = self.angle

            # Step the scanner
            self.step(settings['steps_per_spec'])

        # Get the scan end time
        scan_end_time = datetime.now()

        # Scan complete
        logger.info('Scan complete')

        # Form the scan info
        scan_info = {
            'filename': fname,
            'spectrometer': self.spectrometer.serial_number,
            'scan_start_time': scan_start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'scan_end_time': scan_end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'integration_time': self.spectrometer.integration_time,
            'coadds': self.spectrometer.coadds,
            'scan_number': self.scan_number,
            'latitude': self.gps.lat,
            'longitude': self.gps.lon,
            'altitude': self.gps.alt
        }

        # Form the output Dataset
        scan_data = xr.DataArray(
            data=spectra,
            coords={
                'angle': scan_angles,
                'wavelength': wavelengths
            },
            attrs={**scan_info, **settings}
        )

        # Save the scan
        scan_data.to_netcdf(fname)

        # Return the filepath to the saved scan
        return fname


# =============================================================================
# Virtual Scanner
# =============================================================================

class VScanner:
    """Virtual Scanner class for testing.

    Control the scanner head which consists of a stepper
    motor and a microswitch
    """

    # Initialise
    def __init__(self, switch_pin=21, step_type='single', angle_per_step=1.8,
                 home_angle=180, max_steps_home=1000, spectrometer=None):
        """Initialise.

        Parameters
        ----------
        uswitch_pin : int, optional
            The GPIO pin that connects to the microswitch. Default is 21

        steptype : str, optional
            Stepping type. Must be one of:
                - single;     single step (lowest power, default)
                - double;     double step (more power but stronger)
                - interleave; finer control, has double the steps of single
                - micro;      slower but with much higher precision (8x)
            Default is single

        angle_per_step : float, optional
            The angle checge with every step in degrees. Default is 1.8

        home_angle : float, optional
            The angular position (deg) of the scanner when home. Default is 180
        """
        # Connect to the virtual micro switch
        self.home_switch = VSwitch()

        # Connect to the virtual stepper motor
        self.motor = VMotorKit()

        # Set the initial motor position and angle (assuming scanner is home)
        self.position = 0
        self.home_angle = home_angle
        self.angle = home_angle

        # Set the max number of steps to home the scanner
        self.max_steps_home = max_steps_home

        # Define the angle change per step
        self.angle_per_step = angle_per_step

        # Define the type of stepping
        self.step_type = step_type

        # Create a counter for the scan number
        self.scan_number = 0

        # Add the spectrometer
        self.spectrometer = spectrometer

# =============================================================================
#   Find Home
# =============================================================================

    def find_home(self):
        """Rotate the scanner head to the home position."""
        # Log searching for home
        logger.info('Finding home position')

        # Check if already home
        if self.home_switch.value:
            logger.info('Scanner already home!')
            return 0

        # Create a counter for the number of steps taken
        i = 0

        # Set home flag to false
        self.home_flag = False

        # Launch home watcher thread
        watcher_thread = Thread(target=self._watch_for_home)
        watcher_thread.daemon = True
        watcher_thread.start()

        # Search for home
        while not self.home_flag:

            # Step the scanner
            self.step()
            i += 1

            # Check if the max home steps has been reached
            if i >= self.max_steps_home:
                logger.error(f'Scanner cannot find home after {i} steps')
                raise Exception('Error with scanner: unable to find home')

        # Log steps to home
        logger.info(f'Steps to home: {i}')

        # Once home set the motor position to 0 and set the home angle
        self.position = 0
        self.angle = self.home_angle + 30

        return i

# =============================================================================
#   Watch for home
# =============================================================================

    def _watch_for_home(self):
        """Watch for change in home switch state."""
        while not self.home_switch.value:
            pass
        self.home_flag = True

# =============================================================================
#   Move Motor
# =============================================================================

    def step(self, steps=1, direction='backward'):
        """Move the motor by a given number of steps.

        Parameters
        ----------
        steps : int
            Number of steps to move

        direction : str
            Stepping direction, either 'forward' or 'backward'

        Returns
        -------
        None
        """
        # Perform steps
        for i in range(steps):

            # Add a short rest between steps to improve accuracy
            time.sleep(0.1)

        # Update the motor postion
        if direction == 'backward':
            self.position += steps
        elif direction == 'forward':
            self.position -= steps

        # Update the angular posiotion
        if direction == 'backward':
            self.angle += steps * self.angle_per_step
        elif direction == 'forward':
            self.angle -= steps * self.angle_per_step

        # Make sure the angle is between -180 to 180 degrees
        self.angle = ((self.angle + 180) % 360) - 180

        if self.angle > 179 or self.angle < -179:
            self.home_switch.value = False
        else:
            self.home_switch.value = True

# =============================================================================
# Acquire Scan
# =============================================================================

    def acquire_scan(self, settings, save_path):
        """Acquire a scan.

        Perform a scan, measuring a dark spectrum then spectra from horizon to
        horizon as defined in the settings.

        Parameters
        ----------
        scanner : OpenSO2 Scanner object
            The scanner used to take the scan

        spectro : iFit Spectrometer object
            The spectrometer to acquire the spectra in the scan

        settings : dict
            Holds the settings for the scan

        save_path : str
            The folder to hold the scan results

        Returns
        -------
        fpath : str
            File path to the saved scan
        """
        # Create array to hold scan data
        scan_data = np.zeros((settings['specs_per_scan'],
                              self.spectrometer.pixels+8))

        # Return the scanner position to home
        logger.info('Returning to home position...')
        self.find_home()

        # Get time
        dt = datetime.now()

        # Form the filename of the scan file
        fname = f'{dt.year}{dt.month:02d}{dt.day:02d}_'           # yyyymmdd
        fname += f'{dt.hour:02d}{dt.minute:02d}{dt.second:02d}_'  # Time HHMMSS
        fname += f'{settings["station_name"]}_'                   # Name
        fname += f'{settings["version"]}_'                        # Version
        fname += f'Scan{self.scan_number:03d}.npy'             # Scan no

        # Take the dark spectrum
        logger.info('Acquiring dark spectrum')
        self.spectrometer.fpath = 'data_bases/dark.txt'
        dark_spec, info = self.spectrometer.get_spectrum()
        dark_data = np.array([0,  # Step number
                              dt.hour, dt.minute, dt.second,  # Time
                              self.position,  # Scanner position
                              self.angle,  # Scan angle
                              info['coadds'],  # Coadds
                              info['integration_time']  # Integration time
                              ])
        scan_data[0] = np.append(dark_data, dark_spec[1])

        # Move scanner to start position
        logger.info('Moving to start position')
        self.step(steps=settings['steps_to_start'])

        # Begin stepping through the scan
        logger.info('Begin main scan')
        for step_no in range(1, settings['specs_per_scan']+1):

            # Acquire the spectrum
            self.spectrometer.fpath = 'data_bases/spectrum_00360.txt'
            spectrum, info = self.spectrometer.get_spectrum()

            # Get the time
            t = info['time']

            # Add the data to the array
            spec_data = np.array([step_no,  # Step number
                                  t.hour, t.minute, t.second,  # Time
                                  self.position,  # Scanner pos
                                  self.angle,  # Scan angle
                                  self.spectrometer.coadds,   # Coadds
                                  self.spectrometer.integration_time  # I time
                                  ])
            scan_data[step_no] = np.append(spec_data, spectrum[1])

            # Step the scanner
            self.step(settings['steps_per_spec'])

        # Scan complete
        logger.info('Scan complete')

        # Save the scan data
        fpath = f'{save_path}spectra/{fname}'

        np.save(fpath, scan_data.astype('float16'))

        # Return the filepath to the saved scan
        return fpath


class VSwitch():
    """Virtual swith."""

    def __init__(self):
        """Initialise."""
        self.value = False


class VMotorKit():
    """Virtual motor class."""

    def __init__(self):
        """Initialise."""
        pass

    def onestep(self):
        """Take one step."""
        time.sleep(0.1)

    def release(self):
        """Release the motor."""
        pass
