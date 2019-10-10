# -*- coding: utf-8 -*-
"""
Module to control the scanner head.
"""

import numpy as np
import logging
import datetime
import atexit
import time
try:
    import board
    import digitalio
    from adafruit_motorkit import MotorKit
    from adafruit_motor import stepper
except ImportError:
    print('Failled to import Raspberry Pi modules')

class Scanner:

    '''
    Scanner class used to control the scanner head which consists of a stepper 
    motor and a microswitch

    **Parameters:**
        
    uswitch_pin : int (optional)
        The GPIO pin that connects to the microswitch. Default is 21

    steptype : str
        Stepping type. Must be one of:
            - single;     single step (lowest power, default)
            - double;     double step (more power but stronger)
            - interleave; finer control, has double the steps of single
            - micro;      slower but with much higher precision (8x)
    '''

    # Initialise
    def __init__(self, uswitch_pin = 21, step_type = 'single'):

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

        # Set the motor position to zero
        self.position = 0

        # Define the type of stepping
        self.step_type = step_type

#==============================================================================
#================================== Find Home =================================
#==============================================================================

    def find_home(self):

        '''
        Function to rotate the scanner head to the home position

        **Parameters:**

        None

        **Returns:**

        None
        '''

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
        logging.info('Steps to home: ' + str(i))

        # Once home set the motor position to 0
        self.position = 0

#==============================================================================
#================================== Move Motor ================================
#==============================================================================

    def step(self, steps = 1, direction = 'backward'):

        '''
        Function to move the motor by a given number of steps

        **Parameters:**

        motor : motor object
            The object for the stepper motor

        steps : int
            Number of steps to move

        direction : str
            Stepping direction, either 'forward' or 'backward'

        **Returns:**

        None
        '''

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
            self.motor.onestep(direction = step_dir[direction],
                               style = step_mode[self.step_type])

            # Add a short rest between steps to improve accuracy
            time.sleep(0.01)

        # Update the motor postion
        if direction == 'backward':
            self.position += steps
        elif direction == 'forward':
            self.position -= steps

        # Write position to file
        try:
            with open('Station/position.txt', 'w') as w:
                w.write(str(self.position))
        except FileNotFoundError:
            pass

#==============================================================================
#================================ Acuire Scan =================================
#==============================================================================

def acquire_scan(Scanner, Spectrometer, common, settings):

    '''
    Function to perform a scan.

    **Parameters:**

    Scanner : openso2 Scanner object
        Object to control the scanner head consisting of a stepper motor and a
        microswitch

    Spectrometer : Seabreeze.Spectrometer object
        Object to control the spectrometer
        
    common : dict
        Dictionary of program variables
        
    settings : dict
        Dictionary of the program settings

    **Returns:**

    fpath : str
        File path to the saved scan

    Written by Ben Esse, January 2019
    '''

    # Create array to hold scan data
    scan_data = np.zeros((settings['specs_per_scan'], 2055))

    # Return the scanner position to home
    Scanner.find_home()

    # Get time
    t = datetime.datetime.now()
    y = t.year
    mo = t.month
    d = t.day
    h = t.hour
    m = t.minute
    s = t.second

    # Form the filename of the scan file
    fname = f'{y}{mo:02d}{d:02d}_'                  # Date "yyyymmdd"
    fname += f'{h:02d}{m:02d}{s:02d}_'              # Time HHMMSS
    fname += f'{settings["station_name"]}'          # Station name
    fname += f'_v_1_1_Block{common["scan_no"]}.npy' # Version and scan number

    # Take the dark spectrum
    dark = Spectrometer.intensities()
    dark_data = np.array([0, h, m, s, Scanner.position, 1, 
                         common['spec_int_time']])
    scan_data[0] = np.append(dark_data, dark)

    # Move scanner to start position
    logging.info('Moving to start position')
    Scanner.step(steps = settings['steps_to_start'])

    # Begin stepping through the scan
    logging.info('Begin scanning')
    for step_no in range(1, settings['specs_per_scan']):

        # Get time
        t = datetime.datetime.now()
        h = t.hour
        m = t.minute
        s = t.second

        # Acquire spectrum
        spec_int = np.zeros(len(dark))
        for i in range(settings['coadds']):
            spec_int = np.add(spec_int, Spectrometer.intensities())
        spec_int = np.divide(spec_int, settings['coadds'])

        # Add the data to the array
        # Has the format N_acq, Hour, Min, Sec, MotorPos, Coadds, Int time
        spec_data = np.array([step_no, h, m, s, Scanner.position, 1,
                              common['spec_int_time']])
        scan_data[step_no] = np.append(spec_data, spec_int)

        # Step the scanner
        Scanner.step(settings['steps_per_spec'])

    # Scan complete
    logging.info('Scan complete')

    # Save the scan data
    fpath = common['fpath'] + 'spectra/' + fname

    np.save(fpath, scan_data.astype('float16'))

    # Return the filepath to the save scan
    return fpath
