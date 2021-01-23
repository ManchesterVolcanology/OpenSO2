# -*- coding: utf-8 -*-
"""
Module to control the scanner head.
"""

import logging
import datetime
import atexit
import time
import numpy as np
try:
    import board
    import digitalio
    from adafruit_motorkit import MotorKit
    from adafruit_motor import stepper
except ImportError:
    logging.warning('Failed to import Raspberry Pi modules')


class Scanner:
    """Scanner class.

    Control the scanner head which consists of a stepper
    motor and a microswitch
    """

    # Initialise
    def __init__(self, uswitch_pin=21, step_type='single', angle_per_step=1.8,
                 home_angle=180, max_steps_home=1000):
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

        # Define the GPIO pins
        gpio_pin = {'4':  board.D4,
                    '5':  board.D5,
                    '6':  board.D6,
                    '12': board.D12,
                    '13': board.D13,
                    '16': board.D16,
                    '17': board.D17,
                    '18': board.D18,
                    '19': board.D19,
                    '20': board.D20,
                    '21': board.D21,
                    '22': board.D22,
                    '23': board.D23,
                    '24': board.D24,
                    '25': board.D25,
                    '27': board.D27}

        # Connect to the micro switch
        self.uswitch = digitalio.DigitalInOut(gpio_pin[str(uswitch_pin)])
        self.uswitch.direction = digitalio.Direction.INPUT
        self.uswitch.pull = digitalio.Pull.UP

        # Connect to the stepper motor
        self.motor = MotorKit().stepper1

        # Define function to release the stepper at exit
        def release_motor():
            self.motor.release()
        atexit.register(release_motor)

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

# =============================================================================
#   Find Home
# =============================================================================

    def find_home(self):
        """Rotate the scanner head to the home position."""

        # Create a counter for the number of steps taken
        i = 0
        
        # If the scanner is home, rotate until the switch is on
        while not self.uswitch.value:
            self.step()
            i += 1
            if i > self.max_steps_home:
                logging.error(f'Scanner cannot find home after {i} steps')

        # Then step the motor until the switch turns off (scanner is home)
        while self.uswitch.value:
            self.step()
            i += 1

        # Log steps to home
        logging.info(f'Steps to home: {i}')

        # Once home set the motor position to 0 and set the home angle
        self.position = 0
        self.angle = self.home_angle

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
        step_mode = {'single':     stepper.SINGLE,
                     'double':     stepper.DOUBLE,
                     'interleave': stepper.INTERLEAVE,
                     'micro':      stepper.MICROSTEP}

        # Set stepping direction dict
        step_dir = {'forward':  stepper.FORWARD,
                    'backward': stepper.BACKWARD}

        # Perform steps
        for i in range(steps):
            self.motor.onestep(direction=step_dir[direction],
                               style=step_mode[self.step_type])

            # Add a short rest between steps to improve accuracy
            time.sleep(0.01)

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
        self.angle_check()

# =============================================================================
#   Angle check
# =============================================================================

    def angle_check(self, max_iter=1000):
        """Check scanner angle is between -180/+180."""
        counter = 0
        while self.angle <= -180 or self.angle > 180:
            if self.angle <= -180:
                self.angle += 360
            elif self.angle > 180:
                self.angle -= 360
            counter += 1
            if counter >= max_iter:
                msg = "Error calculating scanner angle, max iteration reached"
                raise Exception(msg)

        return self.angle


# =============================================================================
# Acquire Scan
# =============================================================================

def acquire_scan(scanner, spectro, settings, save_path):
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
    scan_data = np.zeros((settings['specs_per_scan'], spectro.pixels+8))

    # Return the scanner position to home
    logging.info('Returning to home position...')
    scanner.find_home()

    # Get time
    dt = datetime.datetime.now()

    # Form the filename of the scan file
    fname = f'{dt.year}{dt.month:02d}{dt.day:02d}_'           # Date "yyyymmdd"
    fname += f'{dt.hour:02d}{dt.minute:02d}{dt.second:02d}_'  # Time HHMMSS
    fname += f'{settings["station_name"]}_'                   # Station name
    fname += f'{settings["version"]}_'                        # Version
    fname += f'Block{scanner.scan_number}.npy'                # Scan no

    # Take the dark spectrum
    logging.info('Acquiring dark spectrum')
    spectro.fpath = 'Station/spectrum_00005.txt' #################################
    dark_spec, info = spectro.get_spectrum()
    dark_data = np.array([0,                              # Step number
                          dt.hour, dt.minute, dt.second,  # Time
                          scanner.position,               # Scanner position
                          scanner.angle,                  # Scan angle
                          info['coadds'],                 # Coadds
                          info['integration_time']        # Integration time
                          ])
    scan_data[0] = np.append(dark_data, dark_spec[1])

    # Move scanner to start position
    logging.info('Moving to start position')
    scanner.step(steps=settings['steps_to_start'])

    # Begin stepping through the scan
    logging.info('Begin main scan')
    for step_no in range(1, settings['specs_per_scan']):

        # Acquire the spectrum
        spectro.fpath = 'Station/spectrum_00227.txt' ############################
        spectrum, info = spectro.get_spectrum()

        # Get the time
        t = datetime.datetime.now()

        # Add the data to the array
        spec_data = np.array([step_no,                     # Step number
                              t.hour, t.minute, t.second,  # Time
                              scanner.position,            # Scanner position
                              scanner.angle,               # Scan angle
                              spectro.coadds,              # Coadds
                              spectro.integration_time     # Integration time
                              ])
        scan_data[step_no] = np.append(spec_data, spectrum[1])

        # Step the scanner
        scanner.step(settings['steps_per_spec'])

    # Scan complete
    logging.info('Scan complete')

    # Save the scan data
    fpath = f'{save_path}spectra/{fname}'

    np.save(fpath, scan_data.astype('float16'))

    # Return the filepath to the saved scan
    return fpath


class VScanner:
    """Virtual Scanner class for testing.

    Control the scanner head which consists of a stepper
    motor and a microswitch
    """

    # Initialise
    def __init__(self, uswitch_pin=21, step_type='single', angle_per_step=1.8,
                 home_angle=180, max_steps_home=1000):
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
        self.uswitch = VSwitch()

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

# =============================================================================
#   Find Home
# =============================================================================

    def find_home(self):
        """Rotate the scanner head to the home position."""

        # Create a counter for the number of steps taken
        i = 0
        
        # If the scanner is home, rotate until the switch is on
        while not self.uswitch.value:
            self.step()
            i += 1
            if i > self.max_steps_home:
                logging.error(f'Scanner cannot find home after {i} steps')

        # Then step the motor until the switch turns off (scanner is home)
        while self.uswitch.value:
            self.step()
            i += 1

        # Log steps to home
        logging.info(f'Steps to home: {i}')

        # Once home set the motor position to 0 and set the home angle
        self.position = 0
        self.angle = self.home_angle

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
        self.angle_check()

        if self.position > 200 or self.position < 5:
            self.uswitch.value = False
        else:
            self.uswitch.value = True

# =============================================================================
#   Angle check
# =============================================================================

    def angle_check(self, max_iter=1000):
        """Check scanner angle is between -180/+180."""
        counter = 0
        while self.angle <= -180 or self.angle > 180:
            if self.angle <= -180:
                self.angle += 360
            elif self.angle > 180:
                self.angle -= 360
            counter += 1
            if counter >= max_iter:
                msg = "Error calculating scanner angle, max iteration reached"
                raise Exception(msg)

        return self.angle


class VSwitch():
    def __init__(self):
        self.value = False


class VMotorKit():

    def __init__(self):
        pass

    def onestep(self):
        time.sleep(0.1)

    def release(self):
        pass

