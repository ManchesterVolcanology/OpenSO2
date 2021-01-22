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
                 home_angle=180):
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

        # Define the angle change per step
        self.angle_per_step = angle_per_step

        # Define the type of stepping
        self.step_type = step_type

# =============================================================================
#   Find Home
# =============================================================================

    def find_home(self):
        """Rotate the scanner head to the home position."""
        # First check if the switch is turned off (station is at home)
        while not self.uswitch.value:

            # Rotate until it is on
            self.step()

        # Step the motor until the switch turns off
        i = 0
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
            self.position += steps * self.angle_per_step
        elif direction == 'forward':
            self.position -= steps * self.angle_per_step

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

def aquire_scan(scanner, spectro, settings, save_path):
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
    scanner.find_home()

    # Get time
    dt = datetime.datetime.now()

    # Form the filename of the scan file
    fname = f'{dt.year}{dt.month:02d}{dt.dayd:02d}_'          # Date "yyyymmdd"
    fname += f'{dt.hour:02d}{dt.minute:02d}{dt.second:02d}_'  # Time HHMMSS
    fname += f'{settings["station_name"]}_'                   # Station name
    fname += f'{settings["version"]}_'                        # Version
    fname += f'Block{scanner.scan_no}.npy'                    # Scan no

    # Take the dark spectrum
    dark_spec, info = spectro.get_spectrum()
    dark_data = np.array([0,                              # Step number
                          dt.hour, dt.minute, dt.second,  # Time
                          scanner.position,               # Scanner position
                          scanner.angle,                  # Scan angle
                          spectro.coadds,                 # Coadds
                          spectro.integration_time        # Integration time
                          ])
    scan_data[0] = np.append(dark_data, dark_spec[1])

    # Move scanner to start position
    logging.info('Moving to start position')
    Scanner.step(steps=settings['steps_to_start'])

    # Begin stepping through the scan
    logging.info('Begin scanning')
    for step_no in range(1, settings['specs_per_scan']):

        # Acquire the spectrum
        spectrum, info = spectro.get_spectrum()
        x, y = spectrum

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
        scan_data[step_no] = np.append(spec_data, y)

        # Step the scanner
        scanner.step(settings['steps_per_spec'])

    # Scan complete
    logging.info('Scan complete')

    # Save the scan data
    fpath = f'{save_path}spectra/{fname}'

    np.save(fpath, scan_data.astype('float16'))

    # Return the filepath to the saved scan
    return fpath
