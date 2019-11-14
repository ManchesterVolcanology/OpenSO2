# -*- coding: utf-8 -*-
"""
Contains functions to read and analyse raw scan files and processed SO2 files.
"""

import logging
import numpy as np
import pandas as pd
import datetime as dt
from math import radians, cos, tan, pi

from openso2.fit import fit_spec

#==============================================================================
#================================= Read Scan ==================================
#==============================================================================

def read_scan(fpath):

    '''
    Function to read in a scan file in the Open SO2 format. Each line in the 
    array consists of 2053 floats. The first five hold the spectrum information 
    followed by the spectrum. The infomation is arranged as: 
        [spec_n, hour, minute, second, motor_pos]

    **Parameters:**
        
    fpath : str
        File path to the scan file

    **Returns:**
        
    err : bool
        Error flag to check for a read error

    wavelength : array
        Wavelength grid of the spectrometer

    info : array
        Acquisition info for each spectrum: 
            [spec_n, hour, minute, second, motor_pos]

    spec : array
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

    except Exception:
        return 1, 0, 0, 0

#==============================================================================
#================================ Analyse Scan ================================
#==============================================================================

def analyse_scan(scan_path, save_results = True, save_path = None, **common):

    '''
    Function to analyse a scan block

    **Parameters:**
    
    scan_path : str
        File path to the scan file to analyse

    save_results : bool (default True)
        Flag whether or not to save the results. Turn False for post analysis.
        
    save_path : str, optional, default None
        The directory in which to save the results. If None then the results
        are saved in a folders named "so2" in the same directory as the scan
        parent folder
        
    common : dict
        Common dictionary of keyword parameters used by the program

    **Returns:**
        
    fit_data : pandas.DataFrame
        DataFrame containing the fit metadata and results

    Written by Ben Esse, January 2019
    '''

    # Read in the scan data
    err, x, info_block, spec_block = read_scan(scan_path)
    
    # Set the column names for the output file
    columns = ['time', 'motor_pos', 'angle', 'int_time', 'coads', 'w_lo', 
               'w_hi', 'spec_max_int', 'fit_max_int', 'fit_quality', 'p0', 
               'p0_e', 'p1', 'p1_e', 'p2', 'p2_e', 'p3', 'p3_e', 'shift', 
               'shift_e', 'stretch', 'stretch_e', 'ring', 'ring_e', 'so2', 
               'so2_e', 'no2', 'no2_e', 'o3', 'o3_e']
    
    # Initialise the dataframe
    df = pd.DataFrame(index = np.arange(spec_block.shape[0]-1),
                      columns=columns)

    # Logthe start of the scan
    logging.info(f'Start scan {common["scan_no"]} analysis')

    # Check for read error
    if err == 0:

        # Find fit region
        common['idx'] = np.where(np.logical_and(common['wave_start'] <= x,
                                                x <= common['wave_stop']))
        grid = x[common['idx']]

        # Extract the dark spectrum
        common['dark'] = spec_block[0]

        for n in range(1, spec_block.shape[0]):

            # Extract spectrum info
            info = info_block[n]
            n_aq, h, m, s, motor_pos, int_time, coadds = info

            # Convert motor position to angle
            angle = float(motor_pos) / common['steps_per_degree']
            
            # Subtract the home offset
            angle -= common['home_offset']

            # Convert time to decimal hours
            start_time = dt.time(int(h), int(m), int(s))

            # Extract spectrum
            y = spec_block[n]

            # Fit the spectrum
            popt, perr, fitted_flag = fit_spec(common, [x, y], grid)
            
            # Make the fit quality flag
            if max(y[common['idx']]) > 50000:
                fit_quality = 0
            #elif max(y[common['idx']]) < 4000:
            #    fit_quality = 0
            elif not fitted_flag:
                fit_quality = 0
            elif popt[7] < -2.463e17:
                fit_quality = 0
            else:
                fit_quality = 1
            
            # Pull the fit metadata together
            fit_data = [
                        start_time, 
                        motor_pos,
                        angle,
                        int_time, 
                        coadds, 
                        common['wave_start'],
                        common['wave_stop'], 
                        max(y), 
                        max(y[common['idx']]),
                        fit_quality
                        ]
            
            # Add the fit results to the metadata
            for i in range(len(popt)):
                fit_data += [popt[i], perr[i]]
                
            # Add to the dataframe
            df.iloc[n-1] = fit_data

            # Update fit parameters
            if fitted_flag == True and fit_quality == 1:
                common['params'] = popt

        logging.info(f'Scan {str(common["scan_no"])} analysis complete')

        if save_results == True:

            # Form the path to the directory
            if save_path == None:
                save_path = common['fpath'] + 'so2/'

            # Extract the file name and save the data
            fname = scan_path.split('/')[-1][:-4] + '_so2'
            fpath = save_path + fname
            
            # Try to save in the parquet format
            try:
                df.to_parquet(fpath + '.parquet')
             
            # Else save as a .csv
            except ImportError:
                df.to_csv(fpath + '.csv')

        return df

#==============================================================================
#============================== Update Int Time ===============================
#==============================================================================

def update_int_time(common, settings):

    '''
    Function to calculate a new integration time based on the intensity of the 
    previous scan

    **Parameters:**
        
    common : dict
        Common dictionary of parameters for the program

    settings : dict
        Dictionary of station settings

    **Returns:**
        
    new_int_time : int
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

#==============================================================================
#=============================== Read Scan SO2 ================================
#==============================================================================

def read_scan_so2(fpath):

    '''
    Function to read the so2 results file from a scan

    **Parameters:**
        
    fpath : str
        File path to the scan results file

    **Returns:**
        
    scan_angles : numpy array
        Scan angles

    so2_cd s: numpy array
        SO2 column densities
    '''

    # Read in the scan so2 file
    scan_data = np.load(fpath)

    # Unpack information
    jul_time    = scan_data[:,0]
    motor_pos   = scan_data[:,1]
    scan_angles = scan_data[:,2]
    so2_cds     = scan_data[:,3]
    so2_err     = scan_data[:,4]

    return jul_time, motor_pos, scan_angles, so2_cds, so2_err

#==============================================================================
#=============================== Calc Scan Flux ===============================
#==============================================================================

def calc_scan_flux(angles, so2_amt, windspeed = 10, height = 1000, 
                   plume_type = 'flat'):

    '''
    Function to calculate the SO2 flux from a scan. Either assumes all SO2 is 
    at the same distance from the scanner or at a fixed altitude

    **Parameters:**
        
    angles : list or array
        The angle of each measurement in a scan
        
    so2_amt : list or array
        The retrieved SO2 SCD in molecules/cm2 for each measurement. Must have 
        the same length as angles

    windspeed : float (optional)
        The wind speed used to calculate the flux in m/s (default is 10 m/s)

    height : float (optional)
        The height of the plume in meters (default is 1000 m)

    plume_type : str (optional)
        The type of plume. One of:
            - 'flat' assumes all so2 is at the same altitude in a flat blanket. 
              Good for wide plumes (default)

            - 'cylinder' assumes the plume is cylindrical. Good for smaller 
               plumes. (not yet implemented)

            - 'arc' puts the SO2 at a fixed distance from the scanner across 
              the arc of the scan

    **Returns:**
        
    flux : float
        The flux of SO2 passing through the scan in tonnes/day
    '''

    # Check that the plume type is possible
    if plume_type not in ['flat', 'cylinder', 'arc']:
        raise Exception('Plume type not recognised. Must be one of "flat", ' +\
                        '"cylinder" or "arc"')

    # Convert the angles to radians
    phi = [radians(a) for a in angles]

    if plume_type == 'flat':

        # Correct the so2 column density to account for the scan angle
        corr_so2 = [s * cos(phi[n] - (pi/2)) for n, s in enumerate(so2_amt)]

        # Calculate the horizontal distance between the subsiquent scans
        dx = [height * (abs(tan(phi[n+1]) - tan(phi[n]))) for n in range(len(phi) - 1)]

        # Multiply the average SO2 column density of each two subsiquent 
        #  spectra by the horizontal distance between them
        arc_so2 = [x * (corr_so2[n+1] + corr_so2[n]) / 2 for n, x in enumerate(dx)]

    elif plume_type == 'arc':

        # Calculate the delta angle
        dr = [phi[n+1] - phi[n] for n in range(len(phi) - 1)]

        # Convert to arc length
        dx = np.multiply(dr, height)

        # Calculate the so2 mass in each spectrum
        arc_so2 = [x/2 * (so2_amt[n+1] + so2_amt[n]) for n, x in enumerate(dx)]
        
    # Mask any nans
    masked_arc_so2 = np.ma.masked_invalid(arc_so2)

    # Sum the so2 in the scan
    total_so2 = np.sum(masked_arc_so2)

    # Convert from molecules/cm to moles/m
    so2_moles = total_so2 * 1.0e4 / 6.022e23

    # Convert to kg/m. Molar mass of so2 is 64.066g/mole
    so2_kg = so2_moles * 0.064066

    # Get flux in kg/s
    flux_kg_s = so2_kg * windspeed

    # Convert to tonnes/day
    flux = flux_kg_s * 1.0e-3 * 8.64e4

    return flux

#==============================================================================
#============================= calc_plume_height ==============================
#==============================================================================

def calc_plume_height(gui, station, scan_time):

    '''
    Function to return the plume height. Either pulls it from the main GUI or
    calculates it from two scans

    **Parameters:**
        
    gui : tk.Tk
        The main GUI object
        
    station : str
        Station name for which the scan is being

    scan_time : float
        The time of the scan in decimal hours UTC

    **Returns:**
        
    plume_height : float
        The height of the plume in m a.s.l.
    '''

    # Check how the plume height is calculated
    how_calc_height = gui.how_calc_height.get()

    # Fixed Plume height
    if how_calc_height == 'Fix':
        plume_height = gui.plume_height.get()

    # Calculate (NOT YET IMPLEMENTED)
    if how_calc_height == 'Calc':
        plume_height = 1000.0

    return plume_height

#==============================================================================
#=============================== get_wind_speed ===============================
#==============================================================================

def get_wind(gui, scan_time):

    '''
    Function to get the wind speed.
    ***Currently just returns 10 m/s as not configured***

    **Parameters:**
        
    gui : tk.Tk
        The main GUI object

    scan_time : float
        The time of the scan in decimal hours UTC

    **Returns:**
        
    wind_speed : float
        The latest wind speed in m/s
        
    wind_dir : float
        The latest wind bearing in degrees
    '''

    # Check how the wind speed is calculated
    how_calc_wind = gui.how_calc_wind.get()

    # Fixed wind speed
    if how_calc_wind == 'Fix':
        wind_speed = gui.wind_speed.get()
        wind_dir   = gui.wind_dir.get()

    # Pull wid=nd data from anenometer (NOT YET IMPLEMENTED)
    if how_calc_wind == 'Pull':
        wind_speed = 1000
        wind_dir   = 0

    return wind_speed, wind_dir

#==============================================================================
#============================== get_spec_details ==============================
#==============================================================================

def get_spec_details(fpath):

    '''
    Function to get spectrometer details given the FLAME network station name

    **Parameters:**
        
    fpath : str
        Filename of the spectra block, containing the station name

    **Returns:**
        
    scanner : str
        Scanner station name

    spec_name : str
        Spectrometer serial number

    intercept : float
        Intercept

    c1, c2, c3 : floats
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
              'LOVE': ['USB2+H15972', 275.88781999999975, 0.09256299600000058, -8.025713200000456e-06, 9.706872043555717e-23],
              'BROD': ['FLMS02929', 298.4462299999999, 0.0780060889999999, -5.226187099999893e-06, -1.4457043469125537e-23]}

    # Get just filename
    fname = fpath.split('/')[-1]

    # Split fname into info pieces and extract station name
    scanner = fname.split('_')[2]

    # Get spectrometer parameters from the station name
    spec_name, intercept, c1, c2, c3 = params[scanner]

    return scanner, spec_name, intercept, c1, c2, c3







