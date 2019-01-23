# -*- coding: utf-8 -*-
"""
Created on Wed Jan 23 15:22:46 2019

@author: mqbpwbe2
"""

import seabreeze.spectrometers as sb

from openso2.scanner_control import Scanner
from openso2.call_gps import GPS

global common
common = {}

global settings
settings = {}

#========================================================================================
#============================= Connect to the spectrometer ==============================
#========================================================================================

# Find connected spectrometers
devices = sb.list_devices()

# If no devices are connected then set string to show. Else assign first to spec
if len(devices) == 0:
    spec = 0
    settings['Spectrometer'] = 'Not Connected'
    devices = ['Not Connected']
    print('No devices found')
else:
    try:
        # Connect to spectrometer
        common['spec'] = sb.Spectrometer(devices[0])

        # Set intial integration time
        common['spec'].integration_time_micros(1000)

        # Record serial number in settings
        settings['Spectrometer'] = str(common['spec'].serial_number)

        print('Spectrometer '+settings['Spectrometer']+' Connected')

    except:
        print('Spectrometer already open')

#========================================================================================
#============================ Connect to the GPS and scanner ============================
#========================================================================================

# Connect to the GPS
common['gps'] = GPS()

# Connect to the scanner
common['scanner'] = Scanner()