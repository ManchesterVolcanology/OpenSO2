# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 11:45:25 2019

@author: mqbpwbe2
"""

import numpy as np
import datetime as dt
import logging
from math import radians, cos, tan, pi

from openso2.fit import fit_spec
from openso2.julian_time import hms_to_julian

#========================================================================================
#====================================== Read Scan =======================================
#========================================================================================

def read_scan(fpath):

    '''
    Function to read in a scan file in the Open SO2 format. Each line in the array
    consists of 2053 floats. The first five hold the spectrum information followed by the
    spectrum. The infomation is arranged as: [spec_n, hour, minute, second, motor_pos]

    INPUTS
    ------
    fpath, str
        File path to the scan file

    OUTPUTS
    -------
    err, bool
        Error flag to check for a read error

    wavelength, array
        Wavelength grid of the spectrometer

    info, array
        Acquisition info for each spectrum: [spec_n, hour, minute, second, motor_pos]

    spec, array
        Measured spectra

    Written by Ben Esse, January 2019
    '''

    try:
        # Read in the numpy file
        data = np.load(fpath)

        # Create empty arrays to hold the spectra
        w, h = data.shape
        info = np.zeros((w, 7))
        spec = np.zeros((w, h - 7))

        # Unpack the data
        for n, line in enumerate(data):

            # Split the spectrum from the spectrum info
            info[n] = data[n][:7]
            spec[n] = data[n][7:]

        # Get the station data
        scanner, spec_name, intercept, c1, c2, c3 = get_spec_details(fpath)

        # Generate the wavelength grid
        pixel_no = np.arange(h-7) + 1
        wavelength = intercept + np.multiply(pixel_no, c1)  + \
                     np.multiply(np.power(pixel_no, 2), c2) + \
                     np.multiply(np.power(pixel_no, 3), c3)

        return 0, wavelength, info, spec

    except Exception as e:
        return 1, 0, 0, 0

#========================================================================================
#===================================== Analyse Scan =====================================
#========================================================================================

def analyse_scan(**common):

    '''
    Function to analyse a scan block

    INPUTS
    ------
    common, dict
        Common dictionary of parameters used by the program

    OUTPUTS
    -------
    None

    Written by Ben Esse, January 2019
    '''

    # Create empty array to hold the results
    fit_data = np.zeros((105, 5))

    # Read in the scan data
    err, x, info_block, spec_block = read_scan(common['scan_fpath'])

    # Logthe start of the scan
    logging.info('Start scan ' + str(common['scan_no']) + ' analysis')

    # Check for read error
    if err == 0:

        # Find fit region
        common['idx'] = np.where(np.logical_and(common['wave_start'] <= x,
                                                x <= common['wave_stop']))
        grid = x[common['idx']]

        # Extract the dark spectrum
        common['dark'] = spec_block[0]

        for n in range(1, len(spec_block)):

            # Extract spectrum info
            info = info_block[n]
            n_aq, h, m, s, motor_pos, int_time, coadds = info

            # Convert motor position to angle
            angle = float(motor_pos) * 0.06 - 90

            # Convert time to decimal hours
            dec_time = hms_to_julian(dt.time(int(h), int(m), int(s)))

            # Extract spectrum
            y = spec_block[n]

            # Fit the spectrum
            popt, perr, fitted_flag = fit_spec(common, [x, y], grid)

            # Update fit parameters
            if fitted_flag == True:
                common['params'] = popt

            # Add the fit results to the results array
            fit_data[n-1] = [dec_time, motor_pos, angle, popt[6], perr[6]]

        logging.info('Scan ' + str(common['scan_no']) + ' analysis complete')

        # Save the data
        fname = common['scan_fpath'].split('/')[-1][:-4] + '_so2.npy'
        fpath = common['fpath'] + 'so2/' + fname
        np.save(fpath, fit_data.astype('float32'))

#========================================================================================
#==================================== Update Int Time ===================================
#========================================================================================

def update_int_time(common, settings):

    '''
    Function to calculate a new integration time based on the intensity of the previous
    scan

    INPUTS
    ------
    scan_fpath, str
        Filepath to previous scan

    prev_int_time, int
        Previous scan integration time (ms)

    target_int, int
        Target intensity i ncounts for the spectrometer to read

    OUTPUTS
    -------
    new_int_time, int
        New integration time for the next scan
    '''

    # Load the previous scan
    err, x, info, spec = read_scan(common['scan_fpath'])

    # Find the maximum intensity
    max_int = np.max(spec)

    # Scale the intensity to the target
    scale = settings['target_int'] / max_int

    # Scale the integration time by this factor
    int_time = common['spec_int_time'] * scale

    # Find the nearest integration time
    int_times = np.arange(start = settings['min_int_time'],
                          stop  = settings['max_int_time'] + settings['int_time_step'],
                          step  = settings['int_time_step'])

    # Find the nearest value
    diff = ((int_times - int_time)**2)**0.5
    idx = np.where(diff == min(diff))[0][0]
    new_int_time = int(int_times[idx])

    # Log change
    logging.info('Updated integration time to ' + str(new_int_time) + ' ms')

    # Return the updated integration time
    return int(int_times[idx])

#========================================================================================
#==================================== Calc Scan Flux ====================================
#========================================================================================

def calc_scan_flux(fpath, windspeed = 10, height = 1000, plume_type = 'flat'):

    '''
    Function to calculate the SO2 flux from a scan. Either assumes all SO2 is at the same
    altitude or that it is contained within a cylindrical plume

    INPUTS
    ------
    fpath, str
        File path to the scan so2 file

    windspeed, float (optional)
        The wind speed used to calculate the flux in m/s (default is 10 m/s)

    height, float (optional)
        The height of the plume in meters (default is 1000 m)

    plume_type, str (optional)
        The type of plume.
            - 'flat' assumes all so2 is at the same altitude in a flat blanket. Good for
              wide plumes

            - 'cylinder' assumes the plume is cylindrical. Good for smaller plumes.
              (not yet implemented)

            - 'arc' puts the SO2 at a fixed distance from the scanner across the arc of
              the scan

    OUTPUTS
    -------
    flux, float
        The flux of SO2 passing through the scan in tonnes/day
    '''

    # Check that the plume type is possible
    if plume_type not in ['flat', 'cylinder', 'arc']:
        raise Exception('Plume type not recognised. Must be one of "flat", "cylinder"' +\
                        ' or "arc"')

    # Read in the scan so2 file
    scan_data = np.load(fpath)

    # Unpack useful information
    angles  = scan_data[:,2]
    so2_amt = scan_data[:,3]

    # Convert the angles to radians
    phi = [radians(a) for a in angles]

    if plume_type == 'flat':

        # Correct the so2 column density to account for the scan angle
        corr_so2 = [s * cos(phi[n] - (pi/2)) for n, s in enumerate(so2_amt)]

        # Calculate the horizontal distance between the subsiquent scans
        dx = [height * (abs(tan(phi[n+1]) - tan(phi[n]))) for n in range(len(phi) - 1)]

        # Multiply the average SO2 column density of each two subsiquent spectra by the
        #  horizontal distance between them
        arc_so2 = [x * (corr_so2[n+1] + corr_so2[n]) / 2 for n, x in enumerate(dx)]

    elif plume_type == 'arc':

        # Calculate the delta angle
        dr = [phi[n+1] - phi[n] for n in range(len(phi) - 1)]

        # Convert to arc length
        dx = np.multiply(dr, height)

        # Calculate the so2 mass in each spectrum
        arc_so2 = [x * (so2_amt[n+1] + so2_amt[n]) / 2 for n, x in enumerate(dx)]

    # Sum the so2 in the scan
    total_so2 = np.sum(arc_so2)

    # Convert from molecules/cm to moles/m
    so2_moles = total_so2 * 1.0e4 / 6.022e23

    # Convert to kg/m. Molar mass of so2 is 64.066g/mole
    so2_kg = so2_moles * 0.064066

    # Get flux in kg/s
    flux_kg_s = so2_kg * windspeed

    # Convert to tonnes/day
    flux = flux_kg_s * 1.0e-3 * 8.64e4

    return flux

#========================================================================================
#================================== calc_plume_height ===================================
#========================================================================================

def calc_plume_height(station, fpath):
    
    '''
    Function to calculate the plume height from two station scans
    ***Currently returns 1000 m as not confired***
    
    INPUTS
    ------
    station, str
        Station name for which the scan is being 
    
    OUTPUTS
    -------
    plume_height, float
        The height of the plume in m a.s.l.
    '''

    return 1000.0

#========================================================================================
#=================================== get_wind_speed =====================================
#========================================================================================

def get_wind_speed():
    
    '''
    Function to get the wind speed.
    ***Currently just returns 10 m/s as not configured***
    
    INPUTS
    ------
    None
    
    OUTPUTS
    -------
    wind_speed, float
        The latest windspeed in m/s
    '''
    
    return 10.0

#========================================================================================
#================================== get_spec_details ====================================
#========================================================================================

def get_spec_details(fpath):

    '''
    Function to get spectrometer details given the FLAME network station name

    INPUTS
    ------
    fpath, str
        Filename of the spectra block, containing the station name

    OUTPUTS
    -------
    scanner, str
        Scanner station name

    spec_name, str
        Spectrometer serial number

    intercept, float
        Intercept

    c1, c2, c3, floats
        Calibration coeficents

    Written by Ben Esse, June 2018
    '''

    # Define staion parameters
    #         Station  Spec Name  Intercept    C1           C2            C3
    params = {'ecur': ['I2J5773', 296.388306,  0.048254,    -5.345750e-6, -1.687630e-11],
              'enic': ['I2J5769', 296.6937822, 0.047945548, -4.89043e-6,  -1.77072e-10 ],
              'eili': ['I2J5774', 296.2133877, 0.048868629, -5.55088e-6,  3.97945E-11  ],
              'emil': ['I2J5768', 295.9804618, 0.049231176, -5.52944e-6,  -6.98636E-12 ],
              'even': ['I2J5775', 296.2851694, 0.04864757,  -5.17264e-6,  -0.106506e-10],
              'etst': ['I2J5770', 295.1845975, 0.049603817, -5.54717e-6,  -3.531373-11 ],
              'TEST': ['I2J5769', 296.6937822, 0.047945548, -4.89043e-6,  -1.77072e-10 ],}

    # Get just filename
    fname = fpath.split('/')[-1]

    # Split fname into info pieces and extract station name
    scanner = fname.split('_')[2]

    # Get spectrometer parameters from the station name
    spec_name, intercept, c1, c2, c3 = params[scanner]

    return scanner, spec_name, intercept, c1, c2, c3







