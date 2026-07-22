#!/usr/bin/python3.7

"""The main script for the scanner unit.

This script should be run automatically after startup (e.g. using crontab). It
will perform the following tasks in order:
    - Check and update the system time using the GPS
    - Connect to the spectrometer and prepare for analysis
    - Wait until the designated start time
    - Connect to the scanner head and find home
    - Operate through defined SCAN and POINT blocks, operating continuously
      until the designated stop time
    - Disconnect the scanner head
    - Finish any outstanding analysis
    - Wait to power down, allowing the home station to sync the data as
      required
"""

import os
import sys
import time
import yaml
import logging
import subprocess
import numpy as np
import pandas as pd
import xarray as xr
from glob import glob
from pathlib import Path
from datetime import datetime
from multiprocessing import Process, Queue

from openso2.gps import GPS
from openso2.scanner import Scanner
from openso2.parameters import Parameters
from openso2.spectrometers import Spectrometer, VSpectrometer
from openso2.analyse_scan import Analyser, analyse_scan, update_int_time

__version__ = 'v_1_6'

# =============================================================================
# Set up logging
# =============================================================================

# Get the logger
logger = logging.getLogger()

# Setup logger to standard output
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_formatter = logging.Formatter('%(asctime)s - %(processName)s - %(message)s', '%H:%M:%S')
stdout_handler.setFormatter(stdout_formatter)
logger.addHandler(stdout_handler)

# Get the date
datestamp = datetime.now().date()

# Create results folder
home = Path.home()
results_fpath = f'{home}/Results/{datestamp}'
if not os.path.exists(f'{results_fpath}/so2/'):
    os.makedirs(f'{results_fpath}/so2/')
if not os.path.exists(f'{results_fpath}/spectra/'):
    os.makedirs(f'{results_fpath}/spectra/')
if not os.path.exists(f'{results_fpath}/pointing/'):
    os.makedirs(f'{results_fpath}/pointing/')

# Add a file handler to the logger
file_handler = logging.FileHandler(f'{results_fpath}/{datestamp}.log')
log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(processName)s - %(message)s'
file_format = logging.Formatter(log_fmt, '%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(file_format)
logger.addHandler(file_handler)


# =============================================================================
# Set up status log
# =============================================================================

def log_status(status):
    """Log scanner status to file."""
    # Make sure the Station directory exists
    if not os.path.exists('Station'):
        os.makedirs('Station')

    try:
        # Write the current status to the status file
        with open('Station/status.txt', 'w') as w:
            time_str = datetime.now()
            w.write(f'{time_str} - {status}')

    except Exception:
        logger.warning('Failed to update status file', exc_info=True)


# Create handler to log any exceptions
def exception_handler(*exc_info):
    """Handle uncaught exceptions."""
    log_status('Error')
    logger.exception('Uncaught exception!', exc_info=exc_info)


sys.excepthook = exception_handler


# =============================================================================
# Setup the GPS sync function
# =============================================================================

def gps_time_sync(gps):
    """Syncs the position and time with the GPS."""
    logger.info('Starting GPS sync...')

    # Get a fix from the GPS
    position = gps.get_position(time_to_wait=7200)

    if position is not None:
        ts, lat, lon, alt = position
        tstamp = ts.strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f'Updating system time: {tstamp}')
        tstr = ts.strftime('%a %b %d %H:%M:%S UTC %Y')
        subprocess.call(f'sudo date -s "{tstr}"', shell=True)

        # Also write the system time to the wittypi
        subprocess.call('./write_rtc_time.sh', shell=True)

        # Log the scanner location
        logger.info(
            'Scanner position:\n'
            f'Latitude:   {lat}\n'
            f'Longitutde: {lon}\n'
            f'Altitude:   {alt}\n'
        )

        # Write the position to a file
        with open(f'Station/location.yml', 'w') as w:
            w.write(f'Time: {tstamp}\nLat: {lat}\nLon: {lon}\nAlt: {alt}')

    else:
        logger.warning('GPS fix failed')


# =============================================================================
# Pointing analysis process
# =============================================================================

def pointing_worker(analyser, q):
    """Analyse pointing spectra as they land."""

    while True:

        try:

            # Wait for something to land in the queue
            response = q.get()

            # Define exit clause
            if isinstance(response, str) and response == 'kill':
                logger.info('Killing scanning worker process')
                break

            else:

                # Unpack the spectrum and path to the outputs
                spectrum, point_fpath = response
                logger.info(f'Analysing {spectrum.fname}')

                # Set the output path, creating the file if it doesn't exist
                output_fname = f'{point_fpath}/pointing_so2.csv'

                # If it doesn't exist then we are in a new block. Write the file
                # header and reset the analyser initial guess
                if not os.path.isfile(output_fname):
                    with open(output_fname, 'w') as w:
                        w.write('Timestamp,SO2,SO2_err')
                    analyser.p0 = analyser.params.fittedvalueslist()

                # Get the integration time and load the relevant dark
                spec_int_time = spectrum.integration_time
                dark_fname = f'{point_fpath}/dark_{int(spec_int_time)}ms.nc'
                if os.path.isfile(dark_fname):
                    with xr.open_dataarray(dark_fname) as dark:
                        spectrum.data = spectrum.data - dark.data
                else:
                    logger.info(f"Can't find dark file {dark_fname}")

                # Analyse the spectrum
                fit = analyser.fit_spectrum(spectrum=spectrum)

                # Set the output path, creating the file if it doesn't exist
                output_fname = f'{point_fpath}/pointing_so2.csv'
                if not os.path.isfile(output_fname):
                    with open(output_fname, 'w') as w:
                        w.write('Timestamp,SO2,SO2_err')

                # Write the results
                with open(output_fname, 'a') as w:
                    w.write(
                        f'\n{spectrum.timestamp},'
                        f'{analyser.params["SO2"].fit_val},'
                        f'{analyser.params["SO2"].fit_err}'
                    )

        except ValueError as msg:
            logger.warning(f'Error in analysis, skipping\n{msg}')


def scanning_worker(analyser, q):
    """Analyse scanning spectra as they land."""

    while True:

        # Wait for something to land in the queue
        response = q.get()

        # Define exit clause
        if isinstance(response, str) and response == 'kill':
            logger.info('Killing scanning worker process')
            break

        else:

            # Log the start of the scan analysis
            scan_data = response
            _, tail = os.path.split(scan_data.filename)
            logger.info(f'Start analysis for scan {tail}')

            # Build the save filename
            save_fname = f'{results_fpath}/so2/{tail[:-11]}_results.nc'

            # Reset the analyser initial guess parameters
            analyser.p0 = analyser.params.fittedvalueslist()

            # Analyse the scan
            analyse_scan(scan_data, analyser, save_fname)


# =============================================================================
# Begin the main program
# =============================================================================

def main_loop():
    """Run control loop."""
    log_status('Idle')
    logger.info('Station awake')

# =============================================================================
#   Program setup
# =============================================================================

    # Read in the station operation settings file
    with open('Station/station_settings.yml', 'r') as ymlfile:
        settings = yaml.load(ymlfile, Loader=yaml.FullLoader)
    settings['version'] = __version__

    msg = 'Scanner Settings:'
    for key, item in settings.items():
        if isinstance(item, dict):
            msg += f'\n{key}:'
            for k, v in item.items():
                msg += f'\n{k}:\t{v}'
        else:
            msg += f'\n{key}:\t{item}'
    logger.info(msg)

# =============================================================================
#   Sync with GPS
# =============================================================================

    # Connect to the GPS
    gps = GPS()

    # Set a task to sync the station time and position with the GPS
    gps_time_sync(gps)

# =============================================================================
#   Connect to the spectrometer
# =============================================================================

    # Use this block for actual analysis
    spectro = Spectrometer(
        integration_time=settings['start_int_time'],
        coadds=settings['start_coadds']
    )

    # Use this block for testing without the spectrometer attached
    # spectro = VSpectrometer(
    #     integration_time=settings['start_int_time'],
    #     coadds=settings['start_coadds']
    # )

# =============================================================================
#   Set up iFit analyser
# =============================================================================

    # Create parameter dictionary
    params = Parameters()

    # Load the parameter information and convert the parameter info to a string
    params_str = 'Fit Parameters\nName\tValue\tVary\tXpath'
    for name, par in settings['fit_parameters'].items():
        par['value'] = float(par['value'])
        params.add(name, **par)
        params_str += f'\n{name}\t{params[name].value}' \
                      f'\t{params[name].vary}\t{params[name].xpath}'
    settings['fit_parameters'] = params_str

    # Generate the analyser
    analyser = Analyser(
        params=params,
        fit_window=[310, 320],
        frs_path='Ref/sao2010.txt',
        update_params_flag=True,
        residual_limit=20,
        intensity_limit=[0, 60000],
        interp_method='linear',
        stray_flag=True,
        stray_window=[280, 290],
        ils_type='Params',
        ils_path=f'Station/{spectro.serial_number}_ils.txt'
    )

    # Report fitting parameters
    logger.info(params.pretty_print(cols=['name', 'value', 'vary', 'xpath']))

# =============================================================================
# Set up workers to analyse spectra
# =============================================================================

    # Define the scanning queue
    scan_queue = Queue()
    scan_worker = Process(target=scanning_worker, args=(analyser, scan_queue,))
    scan_worker.daemon = True
    scan_worker.start()

    # Define the scanning queue
    point_queue = Queue()
    point_worker = Process(
        target=pointing_worker, args=(analyser, point_queue,)
    )
    point_worker.daemon = True
    point_worker.start()

# =============================================================================
# Begin the control loop
# =============================================================================

    # Calculate the timings for the measurement block
    scan_mins = settings['scan_block_minutes']
    point_mins = settings['point_block_minutes']
    block_length = scan_mins + point_mins

    # Get today's date
    today = pd.Timestamp.now().floor('D')

    # Pull the opertaion start and stop times
    start_time = datetime.strptime(settings['start_time'], '%H:%M').time()
    stop_time = datetime.strptime(settings['stop_time'], '%H:%M').time()

    # Create list to hold active processes
    processes = []

    # If before scan time, wait
    if datetime.now().time() < start_time:
        logger.info(f'Station idle, waiting untill {start_time}')

        # Check time every 10s
        while datetime.now().time() < start_time:
            log_status('Idle')
            logger.debug('Station on standby')
            time.sleep(10)

    # Connect to the scanner
    scanner = Scanner(
        switch_pin=settings['switch_pin'],
        step_type=settings['step_type'],
        angle_per_step=settings['angle_per_step'],
        home_angle=settings['home_angle'],
        max_steps_home=settings['max_steps_home'],
        spectrometer=spectro,
        gps=gps,
        position_file='Station/scanner_position.txt'
    )
    logger.info('Scanner engaged')

    # Create a flag to ensure we always start with scanning
    init_scan_flag = True

    # Begin loop
    while datetime.now().time() < stop_time:

        # Log the status change
        log_status('Active')

        # Pull the time since today's start
        delta_time = (pd.Timestamp.now() - today) / pd.Timedelta(1, 'm')

        # Calcualte what block number we're in
        block_number = delta_time // block_length
        logger.info(f'In analysis block {int(block_number)}')

        # Calcualte the time through this current block
        block_time = delta_time - (block_number * block_length)
        delta_block_time = pd.Timedelta(minutes=block_time)
        logger.info(f'Currently {delta_block_time} through the block')

        # Scanning ============================================================

        # Check if we're in a scanning block, or if we haven't had a scanning
        # block yet
        if init_scan_flag or block_time <= scan_mins:

            # Turn of forcing to scan first if we are in a scan block
            if init_scan_flag and block_time <= scan_mins:
                init_scan_flag = False

            log_status('Scanning')

            logger.info(f'Begin scan {scanner.scan_number}')

            # Scan!
            scan_data = scanner.acquire_scan(settings, results_fpath)

            # Save the scan
            scan_data.to_netcdf(scan_data.filename)

            # Log scan completion
            logger.info(f'Scan {scanner.scan_number} complete')

            # Send the scan for processing
            scan_queue.put(scan_data)

            # Update the spectrometer integration time
            new_int_time = update_int_time(scan_data, settings)
            spectro.update_integration_time(new_int_time)

            # Update the scan number
            scanner.scan_number += 1

        # Pointing ============================================================

        else:

            log_status('Pointing')

            logger.info('Begin pointing block')

            # Rotate the scanner to home
            logger.info('Returning to home position...')
            scanner.find_home()

            # Create a new directory to hold this pointing data
            point_fpath = str(
                f'{results_fpath}/pointing/{pd.Timestamp.now().strftime("%H%M")}'
            )
            if not os.path.isdir(point_fpath):
                os.makedirs(point_fpath)

            # Create spectrum counter
            n = 0

            # Get the current integration time
            current_integration_time = spectro.integration_time

            # Acquire dark spectra
            logger.info('Acquiring dark spectra')
            int_times = np.arange(
                settings['min_int_time'],
                settings['max_int_time'] + settings['int_time_step'],
                settings['int_time_step']
            )
            for int_time in int_times:
                spectro.update_integration_time(int_time)
                spectro.fpath = 'TEST/dark.txt'
                spectro.get_spectrum(
                    fname=f'{point_fpath}/dark_{int(int_time)}ms.nc'
                )

            # Put the integration time back to what it was before
            spectro.update_integration_time(current_integration_time)

            # Get the end time of this pointing block
            block_time_offset = pd.Timedelta(minutes=block_number*block_length)
            block_length_mins = pd.Timedelta(minutes=block_length)
            point_end_time = today + block_time_offset + block_length_mins

            # Begin the pointing block setup loop
            while pd.Timestamp.now() < point_end_time:

                # Get the most recently analysed scan SO2 data
                so2_files = glob(f'{results_fpath}/so2/*_results.nc')
                so2_files.sort()

                if len(so2_files) == 0:
                    while(glob(f'{results_fpath}/so2/*_results.nc')):
                        logger.info('No SO2 files found, waiting...')
                        time.sleep(1)

                else:

                    # Open the last scan SO2 data
                    last_so2_fname = so2_files[-1]
                    _, tail = os.path.split(last_so2_fname)
                    logger.info(f'Reading last analysed scan: {tail}')
                    with xr.open_dataset(last_so2_fname) as ds:

                        # Pull the scan angles
                        scan_angle = ds.angle.data

                        # Pull the SO2 data where there is good fit quality
                        mask = ds.fit_quality.data == 1
                        scan_so2 = np.where(mask, ds.SO2.data, np.nan)

                        # Add a fallback in case there was an error in the last
                        # scan, using zenith instead
                        if mask.all():
                            logger.info('Issue with last scan, using zenith')
                            pointing_angle = 0

                        # Otherwise get the angle at the maximum SO2 value
                        else:
                            pointing_angle = scan_angle[np.nanargmax(scan_so2)]

                    logger.info(f'Rotating to {pointing_angle:.02f} degrees')

                    # Calcualte the number of steps to the pointing angle
                    nsteps = int(
                        (pointing_angle + 180) / settings['angle_per_step']
                    )

                    # Move the scanner to the pointing direction
                    scanner.step(nsteps)

                    # Break out of this holding loop
                    break

            # Begin the pointing block acquisition loop
            logger.info('Begin pointing acquisition')
            while pd.Timestamp.now() < point_end_time:

                # Take a spectrum
                spectro.fpath = 'TEST/spectrum_00366.txt'
                spectrum = spectro.get_spectrum(
                    fname=f'{point_fpath}/spectrum_{n:05d}.nc'
                )
                n += 1

                # Send the specturm for analysis
                point_queue.put([spectrum, point_fpath])

                # Adjust the integration time
                scale = settings['target_int'] / np.max(spectrum.data)
                int_time = spectrum.integration_time * scale

                # Get the nearest allowed integration time
                diff = ((int_times - int_time)**2)**0.5
                idx = np.nanargmin(diff)
                new_int_time = int(int_times[idx])

                # Update the integration time
                spectro.update_integration_time(new_int_time)

    # Return the scanner to home and release to conserve power
    scanner.find_home()
    scanner.motor.release()
    logger.info('Scanner released')

    # Finish up any analysis that is still ongoing
    for p in processes:
        p.join()

    # Change the station status
    log_status('Asleep')
    logger.info('Station going to sleep')


if __name__ == '__main__':
    main_loop()
