# -*- coding: utf-8 -*-
"""
Created on Fri Nov 23 15:34:46 2018

@author: mqbpwbe2
"""

import board
import digitalio
from Adafruit_MotorHAT import Adafruit_MotorHAT
import atexit

from openso2.acquire_spectrum import acquire_spectrum

#========================================================================================
#=================================== Connect the motor ==================================
#========================================================================================

def connect_scanner(steps = 200, speed = 1):
    
    '''
    Function to connect to the motor and micro switch
    
    INPUTS
    ------
    steps, int (optional)
        The number of steps the stepper motor does for one rotation. Default is 200
        
    speed, int (optional)
        The speed the stepper motor will spin in RPM. Default is 10 RPM
    
    OUTPUTS
    -------
    motor, motor object
        The object for the stepper motor
        
    uswitch, micro switch object
        The object for the micro switch
        
    mh, MotorHAT object
        The object for the motor control HAT
        
    err, tuple
        Error message consisting of (bool, msg), where bool is true if there is an error
        and msg gives the error message
    '''
    
    try:
    
        # Connect to the micro switch. It should be at pin 4
        uswitch = digitalio.DigitalInOut(board.D4)
        
        # Connect to the motor HAT
        mh = Adafruit_MotorHAT(addr = 0x60)
        
        # Turn off motor at exit
        atexit.register(mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE))
        
        # Connect to the stepper motor
        motor = mh.getStepper(steps, 1)
        
        # Set the motor speed
        motor.setSpeed(speed)
        
    except Exception as msg:
        return None, None, None, (True, msg)
    
    return motor, uswitch, mh, (False, 'No error')

#========================================================================================
#======================================= Find Home ======================================
#========================================================================================

def find_home(motor, uswitch):
    
    '''
    Function to rotate the scanner head to the home position
    
    INPUTS
    ------
    motor, motor object
        The object for the stepper motor
        
    uswitch, micro switch object
        The object for the micro switch
    
    OUTPUTS
    -------
    err, tuple
        Error message consisting of (bool, msg), where bool is true if there is an error
        and msg gives the error message
    '''
    
    # First check if the switch is turned on 
    while uswitch.value == True:
        
        # Rotate until it is off
        err = move_scanner(motor)
         
        # Check for error
        if err[0] == True:
            (True, 'Stepping error')
    
    # Step the motor until the switch turns on
    loop = 0
    while uswitch.value == False:
        
        # Move the motor one step
        motor.oneStep(Adafruit_MotorHAT.FORWARD, Adafruit_MotorHAT.SINGLE)
        
        # Check that the motor isn't spinning infinitely
        if loop > 300:
            return (True, 'Unable to find home')
        
    return (False, 'No error')

#========================================================================================
#======================================= Move Motor =====================================
#========================================================================================

def move_scanner(motor, steps = 1, steptype = 'SINGLE', direction = 'forward'):
    
    '''
    Function to move the motor by a given number of steps
    
    INPUTS
    ------
    motor, motor object
        The object for the stepper motor
        
    steps, int
        Number of steps to move
        
    steptype, str
        Stepping type. Must be one of:
            - single; single step (lowest power)
            - double; double step (more power but stronger)
            - interleave; finer control, has double the steps of single
            - micro; slower but with much higher precision (8x)
            
    direction, str
        Stepping direction, either 'forward' or 'backward'
            
    OUTPUTS
    -------
    err, tuple
        Error message consisting of (bool, msg), where bool is true if there is an error
        and msg gives the error message
    '''
    
    # Check steptype is valid
    if steptype not in ['single', 'double', 'interleave', 'micro']:
        return (True, 'Step type not valid. Must be one of single, double, interleave, micro')
    
    # Set stepping mode dict
    step_mode = {'single': Adafruit_MotorHAT.SINGLE,
                 'double': Adafruit_MotorHAT.DOUBLE,
                 'interleave': Adafruit_MotorHAT.INTERLEAVE,
                 'micro': Adafruit_MotorHAT.MICROSTEP}
    
    # Check direction is valid
    if direction not in ['forward', 'backward']:
        return (True, 'Step direction not valid. Must be either "forward" or "backward"')
    
    # Set stepping direction dict
    step_dir = {'forward': Adafruit_MotorHAT.FORWARD,
                'backward': Adafruit_MotorHAT.BACKWARD}
    
    # Step!
    try:
        motor.step(steps, step_dir[direction], step_mode[steptype])
        
    except:
        return(True, 'Error in stepping command')
    
    return (False, 'No error')

#========================================================================================
#========================================== Scan ========================================
#========================================================================================

def scan(common):
    
    '''
    Function to complete a single scan. Must be in home position before beginning the 
    scan
    
    INPUTS
    ------
    common, dict
        Common dictionary of parameters for the program
    
    OUTPUTS
    -------
    err, tuple
        Error flag with message in form (bool, msg). False for no error 
    '''
    
    # Take dark spectrum
    
    
    # Move to scan start
    err = move_scanner(common['motor'], common['start_pos'], 'double')
    
    # Take a spectrum
    x, y, err = acquire_spectrum(common['spec'])
    
    # Set initial position
    current_pos = common['motor_start']
    
    # Run a loop
    while current_pos < common['motor_stop']:
        
        # Take a spectrum
        x, y, err = acquire_spectrum(common['spec'])
        
        # Step
        move_scanner(motor = common['motor'],
                     steps = 4,
                     step_type = 'micro')
        
        
    
    return
    
    
    
    
    
    
    
    
    