#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module to connect to the spectrometer
"""

from seabreeze.spectrometers import Spectrometer

class Spectro:
    
    '''
    Spectrometer class to control the spectrometer
    
    **Parameters:**
    
    spec_name : str
        The serial number of a spectrometer. If not given will connect to the 
        first spectrometer found
        
    initial_int_time : int
        The initial integration time in ms. Default is 100.
        
    initial_coadds : int
        The initial number of coadds. Default is 10.
    '''
    
    # Initialise
    def __init__(self, spec_name = None, initial_int_time = 100, 
                 initial_coadds = 10):
        
        '''
        Connects to the spectrometer and sets the integration time and coadds
        '''
        
        # Connect to the spectormeter. If None then it connects to the first
        #  found
        self.spec = Spectrometer.from_serial_number(spec_name)
        
        # Set the spectrometer integration time and coadds
        self.int_time = initial_int_time
        self.coadds = initial_coadds
        
    def update_int_time(self, int_time):
        
        '''Update the spectrometer integration time'''
        
        # Update the integration time of the class and the actual spectrometer
        self.int_time = int_time
        self.spec.integration_time_micros(self.int_time * 1000)
        
    def update_coadds(self, coadds):
        
        '''Update the spectrometer coadds'''
        
        # Update the class coadds. Note that the coadds are performed on the 
        #  computer not the spectrometer
        self.coadds = coadds
        
    def get_spectrum(self, correct_dark = True, correct_nonlin = True):
        
        '''
        Measure a spectrum at the given integration time and coadds
        
        **Parameters:**
        
        correct_dark_counts : bool
            If true the average value of electric dark pixels on the ccd of the
            spectrometer is subtracted from the measurements to remove the 
            noise floor in the measurements caused by non optical noise sources
            
        correct_nonlinearity : `bool`
            Some spectrometers store non linearity correction coefficients in 
            their eeprom. If requested and supported by the spectrometer the
            readings returned by the spectrometer will be linearized using the
            stored coefficients.
            
        **Returns:**
        
        spectrum, 2D numpy array
            
        '''
        
        
        
        
        
        
        
        
        
        