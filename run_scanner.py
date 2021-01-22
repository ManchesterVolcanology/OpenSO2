#!/usr/bin/python3.7

import os
import sys
import time
import yaml
import logging
import numpy as np
from datetime import datetime
from multiprocessing import Process

from ifit.parameters import Parameters
from ifit.spectral_analysis import Analyser
from ifit.spectrometers import Spectrometer

from openso2.scanner import Scanner, acquire_scan
from openso2.analyse_scan import analyse_scan, update_int_time
from openso2.call_gps import sync_gps_time
from openso2.julian_time import hms_to_julian

# =============================================================================
# Set up logging
# =============================================================================

# Get the date
datestamp = datetime.now().date()

# Create results folder
results_fpath = f'Results/{datestamp}/'
if not os.path.exists(results_fpath + 'so2/'):
    os.makedirs(results_fpath + 'so2/')
if not os.path.exists(results_fpath + 'spectra/'):
    os.makedirs(results_fpath + 'spectra/')

# Create log name
logname = f'{results_fpath}{datestamp}.log'
log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Create the logger
logging.basicConfig(filename=logname,
                    filemode='a',
                    format=log_fmt,
                    level=logging.INFO)

logger = logging.getLogger(__name__)


# =============================================================================
# Set up status log
# =============================================================================

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
        logger.warning('Failed to update status file', exc_info=True)


# Create handler to log any exceptions
def my_handler(*exc_info):
    log_status('Error')
    logger.exception('Uncaught exception!', exc_info=exc_info)


sys.excepthook = my_handler

# =============================================================================
# Begin the main program
# =============================================================================

if __name__ == '__main__':

    log_status('Idle')
    logger.info('Station awake')

# =============================================================================
#   Program setup
# =============================================================================

    # Sync time with the GPS
    sync_gps_time()

    # Read in the station operation settings file
    with open('Station/station_settings.yml', 'r') as ymlfile:
        settings = yaml.load(ymlfile, Loader=yaml.FullLoader)

    spectro = Spectrometer(integration_time=settings['start_int_time'],
                           coadds=settings['start_coadds'])

# =============================================================================
#   Set up iFit analyser
# =============================================================================

    # Create parameter dictionary
    params = Parameters()

    # Add the gases
    params.add('SO2',  value=1.0e16, vary=True, xpath='Ref/SO2_295K.txt')
    params.add('O3',   value=1.0e19, vary=True, xpath='Ref/O3_243K.txt')
    params.add('Ring', value=0.1,    vary=True, xpath='Ref/Ring.txt')

    # Add background polynomial parameters
    params.add('bg_poly0', value=0.0, vary=True)
    params.add('bg_poly1', value=0.0, vary=True)
    params.add('bg_poly2', value=0.0, vary=True)
    params.add('bg_poly3', value=1.0, vary=True)

    # Add intensity offset parameters
    params.add('offset0', value=0.0, vary=True)

    # Add wavelength shift parameters
    params.add('shift0', value=0.0, vary=True)
    params.add('shift1', value=0.1, vary=True)

    # Generate the analyser
    analyser = Analyser(params,
                        fit_window=[310, 320],
                        frs_path='Ref/sao2010.txt',
                        flat_flag=True,
                        flat_path=f'Station/{spectro.serial_number}_flat.txt',
                        stray_flag=True,
                        stray_window=[280, 290],
                        dark_flag=True,
                        ils_type='Params',
                        ils_path=f'Station/{spectro.serial_number}_ils.txt')

    # Read in the wavelength calibration
    wl_calib = np.loadtxt(f'Station/{spectro.serial_number}_wl_calib.txt')

# =============================================================================
#   Begin the scanning loop
# =============================================================================

    # Create list to hold active processes
    processes = []

    # Get time and convert to julian time
    jul_t = hms_to_julian(datetime.now())

    # If before scan time, wait
    if jul_t < settings['start_time']:
        logger.info('Station idle')

        # Check time every 10s
        while jul_t < settings['start_time']:
            log_status('Idle')
            logging.debug('Station on standby')
            time.sleep(10)

            # Update time
            jul_t = hms_to_julian(datetime.now())

    # Connect to the scanner
    scanner = Scanner(step_type=settings['step_type'])

    # Create a scan counter
    scan_no = 0

    # Begin loop
    while jul_t < settings['stop_time']:

        # Log status change and scan number
        log_status('Active')
        logging.info(f'Begin scan {scan_no}')

        # Scan!
        scan_fname = acquire_scan(scanner, spectro, settings)

        # Log scan completion
        logging.info(f'Scan {scan_no} complete')

        # Update the spectrometer integration time
        new_int_time = update_int_time(scan_fname, spectro.integration_time,
                                       settings)
        spectro.update_integration_time(new_int_time)

        # Clear any finished processes from the processes list
        processes = [p for p in processes if p.is_alive()]

        # Check the number of processes. If there are more than two then don't
        #  start another to prevent too many processes running at once
        if len(processes) <= 2:

            # Log the start of the scan analysis
            logging.info(f'Start scan {scan_no} analysis')

            # Build the save filename
            if settings['save_format'] == 'numpy':
                file_end = '.npy'
            elif settings['save_format'] == 'csv':
                file_end = '.csv'
            save_fname = f'{results_fpath}/{scan_fname[:-3]}{file_end}'

            # Create new process to handle fitting of the last scan
            p = Process(target=analyse_scan,
                        args=[scan_fname, analyser, wl_calib, save_fname])

            # Add to array of active processes
            processes.append(p)

            # Begin the process
            p.start()

        else:
            # Log that the process was not started
            msg = f"Too many processes running, scan {scan_no} not analysed"
            logging.warning(msg)

        # Update the scan number
        scan_no += 1

        # Update time
        jul_t = hms_to_julian(datetime.now())

    # Release the scanner to conserve power
    scanner.motor.release()

    # Finish up any analysis that is still ongoing
    for p in processes:
        p.join()

    # Change the station status
    log_status('Asleep')
    logging.info('Station going to sleep')
