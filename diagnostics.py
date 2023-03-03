"""Diagnostics script for OpenSo2 scanner."""
import sys
import yaml
import logging
import traceback
from datetime import datetime
import seabreeze.spectrometers as sb

from openso2.scanner import Scanner
from openso2.spectrometers import Spectrometer

from ifit.gps import GPS


class bcolors:
    """Colors for printing."""

    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


logger = logging.getLogger(__name__)

# Setup logger to standard output
logger.setLevel(logging.INFO)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.INFO)
stdout_formatter = logging.Formatter('%(asctime)s - %(message)s', '%H:%M:%S')
stdout_handler.setFormatter(stdout_formatter)
logger.addHandler(stdout_handler)

print('Welcome to OpenSO2 diagnosis\n'
      + 'This script will run through tests to ensure the scanner is '
      + 'working as expected')

print(f'Current system time: {datetime.now()}')

print('Reading stations settings...')

try:
    with open('Station/station_settings.yml', 'r') as ymlfile:
        settings = yaml.load(ymlfile, Loader=yaml.FullLoader)

    print('Station settings:')
    for key, item in settings.items():
        print(key, item)
except FileNotFoundError:
    print('No settings file found, using default')
    with open('Station/station_settings_ex.yml', 'r') as ymlfile:
        settings = yaml.load(ymlfile, Loader=yaml.FullLoader)

print('Testing scanner...')

try:
    scanner = Scanner(
        switch_pin=settings['switch_pin'],
        step_type=settings['step_type'],
        angle_per_step=settings['angle_per_step'],
        home_angle=settings['home_angle'],
        max_steps_home=settings['max_steps_home']
    )
    print('Scanner connected, trying to find home...')
    scanner.find_home()

except Exception:
    print(f'{bcolors.FAIL}Error with scanner!{bcolors.ENDC}')
    print(traceback.format_exc())

print('Testing spectrometer...')

try:
    devs = sb.list_devices()
    print('Available spectrometers:')
    if len(devs) == 0:
        print('None')
    else:
        for dev in devs:
            print(dev)
        spectro = Spectrometer(
            integration_time=settings['start_int_time'],
            coadds=settings['start_coadds']
        )
        spectrum = spectro.get_spectrum()
        print(spectrum)

except Exception:
    print(f'{bcolors.FAIL}Error with spectomreter!{bcolors.ENDC}')
    print(traceback.format_exc())

print('Testing GPS')

try:
    gps = GPS()
    ts, lat, lon, alt = gps.get_position()
    print(f'GPS fix:\nTime: {ts}\nLat: {lat}\nLon: {lon}\nAlt: {alt}')
except Exception:
    print(f'{bcolors.FAIL}Error with GPS!{bcolors.ENDC}')
    print(traceback.format_exc())
