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
    def __init__(self, steps=200, speed=10, uswitch_pin = '21'):
        
        # Define the GPIO pins
        gpio_pin = {'4': board.D4,
                    '5': board.D5,
                    '6': board.D6,
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
        
        # Define the no. of steps and rotation speed 
        self.motor_steps = steps
        self.motor_speed = speed
    
        # Connect to the micro switch. It should be at pin 19
        self.uswitch = digitalio.DigitalInOut(gpio_pin[uswitch_pin])
        
        # Connect to the motor HAT
        mh = Adafruit_MotorHAT(addr = 0x60)
        
        # Turn off motor at exit
        def turnOffMotors():
            mh.getMotor(1).run(Adafruit_MotorHAT.RELEASE)
            mh.getMotor(2).run(Adafruit_MotorHAT.RELEASE)
            mh.getMotor(3).run(Adafruit_MotorHAT.RELEASE)
            mh.getMotor(4).run(Adafruit_MotorHAT.RELEASE)

        atexit.register(turnOffMotors)
        
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
        None
        '''

        # First check if the switch is turned on 
        if not self.uswitch.value:
            
            # Rotate until it is on
            self.step(steps = 100, steptype = 'single')

        # Step the motor until the switch turns off
        while self.uswitch.value:

            # Move the motor one step
            self.step(steptype = 'interleave')

#========================================================================================
#======================================= Move Motor =====================================
#========================================================================================
                
    def step(self, steps = 1, steptype = 'single', direction = 'forward'):
    
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
        
        if steps > 1:
            
            for i in range(steps):
                self.motor.oneStep(step_dir[direction], step_mode[steptype])    
        
        else:
            self.motor.oneStep(step_dir[direction], step_mode[steptype])
    