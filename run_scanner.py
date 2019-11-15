#!/usr/bin/python3.7

import os
import sys
import numpy as np
import time
import seabreeze.spectrometers as sb
from multiprocessing import Process
import datetime
import logging

from openso2.scanner import Scanner, acquire_scan
from openso2.analyse_scan import analyse_scan, update_int_time
from openso2.call_gps import sync_gps_time
from openso2.program_setup import read_settings
from openso2.julian_time import hms_to_julian
from openso2.make_ils import make_ils

#==============================================================================
#=============================== Set up logging ===============================
#==============================================================================

# Get the date
dt = datetime.datetime.now()
datestamp = str(dt.date())

# Create results folder
fpath = 'Results/' + datestamp + '/'
if not os.path.exists(fpath + 'so2/'):
    os.makedirs(fpath + 'so2/')
if not os.path.exists(fpath + 'spectra/'):
    os.makedirs(fpath + 'spectra/')

# Create log name
logname = f'{fpath}{datestamp}.log'
log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Create the logger
logging.basicConfig(filename=logname,
                    filemode = 'a',
                    format = log_fmt,
                    level = logging.INFO)

logger = logging.getLogger(__name__)

#==============================================================================
#============================= Set up status log ==============================
#==============================================================================

def log_status(status):

    # Make sure the Station directory exists
    if not os.path.exists('Station'):
        os.makedirs('Station')

    try:
        # Write the current status to the status file
        with open('Station/status.txt', 'w') as w:
            time_str = datetime.datetime.now()
            w.write(f'{time_str} - {status}')

    except Exception:
        logger.warning('Failed to update status file', exc_info = True)

# Create handler to log any exceptions
def my_handler(*exc_info):
    log_status('Error')
    logger.exception(f'Uncaught exception!', exc_info = exc_info)

sys.excepthook = my_handler

#==============================================================================
#=========================== Begin the main program ===========================
#==============================================================================

if __name__ == '__main__':

    log_status('Idle')
    logger.info('Station awake')

#==============================================================================
#====================== Create common and settings dicts ======================
#==============================================================================

    # Create an empty dictionary to hold the comon parameters
    common = {'fpath': fpath}

    # Read in the station operation settings file
    settings = read_settings('data_bases/station_settings.txt')

#==============================================================================
#=============================== Sync GPS Time ================================
#==============================================================================

    # Sync time with the GPS
    sync_gps_time()

#==============================================================================
#======================== Connect to the spectrometer =========================
#==============================================================================

    # Find connected spectrometers
    devices = sb.list_devices()

    # Connect to spectrometer
    spec = sb.Spectrometer(devices[0])

    # Set intial integration time
    common['spec_int_time'] = settings['start_int_time']
    spec.integration_time_micros(common['spec_int_time'] * 1000)

    # Record serial number in settings
    settings['Spectrometer'] = str(spec.serial_number)
    logging.info('Spectrometer ' + settings['Spectrometer'] + ' Connected')

#==============================================================================
#============================ Read in ref spectra =============================
#==============================================================================

    # Set the fit window
    common['wave_start'] = 310
    common['wave_stop']  = 320

    # Read in reference spectra
    grid, so2_xsec = np.loadtxt('data_bases/Ref/so2.txt',  unpack = True)
    grid, o3_xsec  = np.loadtxt('data_bases/Ref/o3.txt',   unpack = True)
    grid, no2_xsec = np.loadtxt('data_bases/Ref/no2.txt',  unpack = True)
    grid, sol      = np.loadtxt('data_bases/Ref/sol.txt',  unpack = True)
    grid, ring     = np.loadtxt('data_bases/Ref/ring.txt', unpack = True)

    # Extract the fit window
    fit_idx = np.where(np.logical_and(grid > common['wave_start'] - 2,
                                      grid < common['wave_stop'] + 2))

    # Set the model grid
    common['model_grid'] = grid[fit_idx]
    common['so2_xsec']   = so2_xsec[fit_idx]
    common['o3_xsec']    = o3_xsec[fit_idx]
    common['no2_xsec']   = no2_xsec[fit_idx]
    common['sol']        = sol[fit_idx]
    common['ring']       = ring[fit_idx]

    # Get spectrometer flat spectrum
    x, flat = np.loadtxt(f'data_bases/Ref/flat_{settings["Spectrometer"]}.txt',
                         unpack = True)
    idx = np.where(np.logical_and(x > common['wave_start'], 
                                  x < common['wave_stop']))
    common['flat'] = flat[idx]

    # Get spectrometer ILS
    #ils_fpath = f'data_bases/Ref/ils_{settings["Spectrometer"]}.txt'
    #common['ils'] = np.loadtxt(ils_fpath)
    
    ils_fpath = f'data_bases/Ref/ils_params_{settings["Spectrometer"]}.txt'
    FWHM, k, a_w, a_k = np.loadtxt(ils_fpath)
    common['ils'] = make_ils(0.01, FWHM, k, a_w, a_k)

    # Set first guess for parameters
    common['params'] = [1.0, 1.0, 1.0, 1.0, -0.2, 0.05, 1.0, 1.0e16, 1.0e17, 
                        1.0e19]

    # Set the station name
    common['station_name'] = settings['station_name']

    # Set the station motor details and add to the common
    common['steps_per_degree'] = settings['steps_per_degree']
    common['home_offset'] = settings['home_offset']

    # Create loop counter
    common['scan_no'] = 0

    # Create list to hold active processes
    processes = []

#==============================================================================
#========================== Begin the scanning loop ===========================
#==============================================================================

    # Get time and convert to julian time
    timestamp = datetime.datetime.now()
    jul_t = hms_to_julian(timestamp)

    # If before scan time, wait
    if jul_t < settings['start_time']:
        logger.info('Station idle')

        # Check time every 10s
        while jul_t < settings['start_time']:
            log_status('Idle')
            logging.debug('Station on standby')
            time.sleep(10)

            # Update time
            timestamp = datetime.datetime.now()
            jul_t = hms_to_julian(timestamp)

    # Connect to the scanner
    scanner = Scanner(step_type = settings['step_type'])

    # Begin loop
    while jul_t < settings['stop_time']:

        # Log status change and scan number
        log_status('Active')
        logging.info('Begin scan ' + str(common['scan_no']))

        # Scan!
        common['scan_fpath'] = acquire_scan(scanner, spec, common, settings)

        # Log scan completion
        logging.info('Scan ' + str(common['scan_no']) + ' complete')

        # Update the spectrometer integration time
        common['spec_int_time'] = update_int_time(common, settings)
        spec.integration_time_micros(common['spec_int_time'] * 1000)

        # Clear any finished processes from the processes list
        processes = [pro for pro in processes if pro.is_alive()]

        # Check the number of processes. If there are more than two then don't 
        #  start another to prevent too many processes running at once
        if len(processes) <= 2:

            # Create new process to handle fitting of the last scan
            p = Process(target = analyse_scan, 
                        args = [True, common['scan_fpath']],
                        kwargs = common)

            # Add to array of active processes
            processes.append(p)

            # Begin the process
            p.start()

        else:
            # Log that the process was not started
            msg = f"Too many processes running, " + \
                  f"scan {common['scan_no']} not analysed"
            logging.warning(msg)

        # Update the scan number
        common['scan_no'] += 1

        # Update time
        timestamp = datetime.datetime.now()
        jul_t = hms_to_julian(timestamp)

    # Release the scanner to conserve power
    scanner.motor.release()

    # Finish up any analysis that is still ongoing
    for p in processes:
        p.join()

    # Change the station status
    log_status('Asleep')
    logging.info('Station going to sleep')
