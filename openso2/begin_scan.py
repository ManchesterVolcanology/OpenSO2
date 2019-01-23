# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 11:45:25 2019

@author: mqbpwbe2
"""

import numpy as np

#========================================================================================
#====================================== Begin Scan ======================================
#========================================================================================

def begin_scan(GUI, Scanner, GPS, Spectro, common):

    '''
    Function to perform a scan. Simultaneously analyses the spectra from the previous
    scan while aquiring the current one

    INPUTS
    ------
    GUI, tk.Tk object
        Object for the main GUI of the control program

    Scanner, openso2 Scanner object
        Object to control the scanner head consisting of a stepper motor and a
        microswitch

    GPS, openso2 GPS object
        Object to control the GPS module for location and date/time information

    Spectro, Seabreeze.Spectrometer object
        Object to control the spectrometer

    OUPUTS
    ------
    None
    '''

    # Create array to hold scan data
    scan_data = np.zeros((105, 2058))

    # Return the scanner position to home
    Scanner.find_home()

    # Take the dark spectrum
    scan_data[0] = Spectro.intensities()

    # Move scanner to start position
    Scanner.step(steps = 53, steptype = 'micro', direction = 'forward')

    # Begin stepping through the scan
    for step_no in range(1, 105):

        # Acquire spectrum
        spec_int = Spectro.intensities()

        # Get time
        y, mo, d, h, mi, s = GPS.get_time()

        # Add the data to the array
        # Has the format N_acq, Year, Month, Day, Hour, Min, Sec, MotorPos, Coadds,
        # Int time, Spectrum
        scan_data[step_no] = np.append(np.array([step_no, y, mo, d, h, mi, s, 0, 0, 0]),
                                       spec_int)

    # Save the scan data
    fname = str(y) + str(mo) + str(d) + '_' + str(h) + str(mi) + str(s) + '_' + \
            common['station_name'] + '_v_1_1_Block' + str(common['scan_no']) + '.npy'
    np.save(fname, scan_data)
















