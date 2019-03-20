#!/home/pi/berryconda3/bin/python

import os
import numpy as np
import time
import seabreeze.spectrometers as sb
from multiprocessing import Process
import logging

from openso2.scanner import Scanner, acquire_scan
from openso2.analyse_scan import analyse_scan, update_int_time
from openso2.call_gps import GPS
from openso2.program_setup import read_settings
from openso2.julian_time import hms_to_julian
from openso2.station_status import status_loop

#========================================================================================
#=========================== Create comon and settings dicts ============================
#========================================================================================

# Create an empty dictionary to hold the comon parameters
common = {}

# Read in the station operation settings file
settings = read_settings('data_bases/station_settings.txt')

#========================================================================================
#============================ Connect to the GPS and scanner ============================
#========================================================================================

# Connect to the GPS
gps = GPS()

# Wait for GPS to get a fix
while True:
    timestamp, lat, lon, alt = gps.call_gps()

    if timestamp != '':
        break

# Convert the timestamp to a date and a julian time
datestamp = timestamp[0:10]

# Connect to the scanner
scanner = Scanner()

#========================================================================================
#==================================== Set up logging ====================================
#========================================================================================

# Create log name
logname = f'log/{datestamp}.log'
log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Make sure the log folder exists
if not os.path.exists('log'):
    os.makedirs('log')

# Create the logger
logging.basicConfig(filename=logname,
                    filemode = 'w',
                    format = log_fmt,
                    level = logging.INFO)

logging.info('Station awake')

#========================================================================================
#============================= Connect to the spectrometer ==============================
#========================================================================================

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

#========================================================================================
#==================================== Start scanning ====================================
#========================================================================================

# Read in reference spectra
model_grid, common['so2_xsec'] = np.loadtxt('data_bases/Ref/so2.txt',  unpack = True)
model_grid, common['o3_xsec']  = np.loadtxt('data_bases/Ref/o3.txt',   unpack = True)
model_grid, common['no2_xsec'] = np.loadtxt('data_bases/Ref/no2.txt',  unpack = True)
model_grid, common['sol']      = np.loadtxt('data_bases/Ref/sol.txt',  unpack = True)
model_grid, common['ring']     = np.loadtxt('data_bases/Ref/ring.txt', unpack = True)
x, common['flat']              = np.loadtxt('data_bases/Ref/flat.txt', unpack = True)

# Set the model grid
common['model_grid'] = model_grid
common['wave_start'] = 305
common['wave_stop']  = 318

# Set the order of the background poly
common['poly_n'] = 3

# Add other parameters
common['params'] = [1.0, 1.0, 1.0, -0.2, 0.05, 1.0, 1.0e16, 1.0e17, 1.0e19]

# Set the station name
common['station_name'] = settings['station_name']

# Create loop counter
common['scan_no'] = 0

# Create list to hold active processes
processes = []

#========================================================================================
#================================== Set up status loop ==================================
#========================================================================================

# Launch a seperate processs to keep the station status up to date
status_p = Process(target = status_loop)
status_p.start()

#========================================================================================
#=============================== Begin the scanning loop ================================
#========================================================================================

# Create results folder
common['fpath'] = 'Results/' + datestamp + '/'
if not os.path.exists(common['fpath'] + 'so2/'):
    os.makedirs(common['fpath'] + 'so2/')
if not os.path.exists(common['fpath'] + 'spectra/'):
    os.makedirs(common['fpath'] + 'spectra/')

# Get time and convert to julian time
timestamp, lat, lon, alt = gps.call_gps()
jul_t = hms_to_julian(timestamp[11:19], str_format = '%H:%M:%S')

# If before scan time, wait
while jul_t < settings['start_time']:
    logging.info('Station standby')
    time.sleep(60)

    # Update time
    timestamp, lat, lon, alt = gps.call_gps()
    jul_t = hms_to_julian(timestamp[11:19], str_format = '%H:%M:%S')


# Begin loop
while jul_t < settings['stop_time']:

    logging.info('Station active')

    # Get scan start time
    timestamp, lat, lon, alt = gps.call_gps()

    # Convert the timestamp to a date and a julian time
    datestamp = timestamp[0:10]
    jul_t = hms_to_julian(timestamp[11:19], str_format = '%H:%M:%S')

    logging.info('Begin scan ' + str(common['scan_no']))

    # Scan!
    common['scan_fpath'] = acquire_scan(scanner, gps, spec, common, settings)

    # Update the spectrometer integration time
    common['spec_int_time'] = update_int_time(common, settings)
    spec.integration_time_micros(common['spec_int_time'] * 1000)

    # Clear any finished processes from the processes list
    processes = [pro for pro in processes if pro.is_alive()]

    # Check the number of processes. If there are more than two then don't start
    # another to prevent too many processes running at once
    if len(processes) <= 2:

        # Create new process to handle fitting of the last scan
        p = Process(target = analyse_scan, kwargs = common)

        # Add to array of active processes
        processes.append(p)

        # Begin the process
        p.start()

    else:
        # Log that the process was not started
        msg = f"Too many processes running, scan {common['scan_no']} not analysed"
        logging.warning(msg)

    # Update the scan number
    common['scan_no'] += 1

logging.info('Station going to sleep')
gps.stop()