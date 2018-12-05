# -*- coding: utf-8 -*-
"""
Created on Fri Nov 23 15:34:46 2018

@author: mqbpwbe2
"""

import board
import digitalio
from Adafruit_MotorHAT import Adafruit_MotorHAT
import atexit

class Scanner:
    
    '''
    Scanner class used to control the scanner head which consists of a stepper motor and 
    a microswitch
    
    INPUTS
    ------
    steps, int
        The number of steps the stepper motor does for one rotation. Default is 200
        
    speed, int
        The speed the stepper motor will spin in RPM. Default is 10 RPM
        
    METHODS
    -------
    find_home
        Function that rotates the scanner to the home position
        
    move
        Moves the scanner by a specified number of steps
    '''
    
    # Initialise
    def __init__(self, steps, speed):
        
        # Define the no. of steps and rotation speed 
        self.motor_steps = steps
        self.motor_speed = speed
    
        # Connect to the micro switch. It should be at pin 19
        self.uswitch = digitalio.DigitalInOut(board.D20)
        
        # Connect to the motor HAT
        mh = Adafruit_MotorHAT(addr = 0x60)
        
        # Turn off motor at exit
        atexit.register(mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE))
        
        # Connect to the stepper motor
        self.motor = mh.getStepper(steps, 1)
        
        # Set the motor speed
        self.motor.setSpeed(speed)

#========================================================================================
#======================================= Find Home ======================================
#========================================================================================
    
    # Method to find home
    def home(self):
        
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
            Error message consisting of (bool, msg), where bool is true if there is an 
            error and msg gives the error message
        '''
        
        # First check if the switch is turned on 
        while self.uswitch.value == True:
            
            # Rotate until it is off
            self.move_scanner(self.motor)
        
        # Step the motor until the switch turns on
        loop = 0
        while self.uswitch.value == False:
            
            # Move the motor one step
            self.motor.oneStep(Adafruit_MotorHAT.FORWARD, Adafruit_MotorHAT.SINGLE)
            
            # Check that the motor isn't spinning infinitely
            if loop > self.motor_steps:
                return (True, 'Unable to find home')

#========================================================================================
#======================================= Move Motor =====================================
#========================================================================================
                
    def step(self, steps = 1, steptype = 'SINGLE', direction = 'forward'):
    
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
        None
        '''
        
        # Set stepping mode dict
        step_mode = {'single': Adafruit_MotorHAT.SINGLE,
                     'double': Adafruit_MotorHAT.DOUBLE,
                     'interleave': Adafruit_MotorHAT.INTERLEAVE,
                     'micro': Adafruit_MotorHAT.MICROSTEP}
        
        # Set stepping direction dict
        step_dir = {'forward': Adafruit_MotorHAT.FORWARD,
                    'backward': Adafruit_MotorHAT.BACKWARD}
        
        # Step!
        for i in range(steps):
            self.motor.onestep(step_dir[direction], step_mode[steptype])    
            
    