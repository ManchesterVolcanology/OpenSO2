# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 15:30:36 2018

@author: mqbpwbe2
"""

import numpy as np
from seabreeze.cseabreeze.wrapper import SeaBreezeError

def acquire_spectrum(spec, scans_to_av = 10, q = None):
    
    '''
    Function to acquire a spectrum from the spectrometer
    
    INPUTS
    ------
    spec, seabreeze.Spectrometer
        Spectrometer object for the spectormeter connected to the scanner
        
    scans_to_av, int
        Number of spectra to average per spectrum. Default is 10
        
    q, queue (optional)
        The queue to which to add the measured spectrum if multithreading
        
    OUTPUTS
    -------
    x, numpy array
        Wavelength grid
        
    y, numpy array
        Intensity array
        
    err, tuple
        Tuple containing the error flag and message. Consists of (bool, msg), where True
        means there is an error, given by msg
    '''
    
    try:
        # Read wavelength grid
        x = spec.wavelengths()
        
        # Create empty array to hold intensities
        y = np.zeros(2048)
        
        # Loop over the coadds
        for i in range(scans_to_av):
            # Read the spectrum
            y = np.add(y, spec.intensities(correct_dark_counts = True,
                                           correct_nonlinearity = True))
    
    except SeaBreezeError:
        err = (True, 'Exception: SeaBreezeError')
        return np.zeros(2048), np.zeros(2048), err
    
    # If read is successful set error to False      
    err = (False, 'No error')
    
    # Divide by number of coadds
    y = np.divide(y, scans_to_av)
    
    return x, y, err