# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 14:44:50 2018

@author: mqbpwbe2
"""

import datetime
import adafruit_gps
import serial

#========================================================================================
#===================================== Connect GPS ======================================
#========================================================================================

def connect_gps():
    
    '''
    Function to connect to the GPS
    
    INPUTS
    ------
    None
    
    OUTPUTS
    -------
    gps, adafruit_gps object
        The object for the GPS for other programs to call
    '''
    try:
        
        # Establish uart access
        uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=3000)
        
        # Create a GPS module instance
        gps = adafruit_gps.GPS(uart, debug=False)
        
        # Turn on basic GGA and RMC info
        gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
        
        # Set update rate to be once a second
        gps.send_command(b'PMTK220, 1000')
        
    except Exception as msg:
        return None, (True, msg)
    
    return gps, (False, 'No error')

#========================================================================================
#======================================= Call GPS =======================================
#========================================================================================

def call_gps(gps):
    
    '''
    Function to call the connected GPS.
    
    INPUTS
    ------
    gps, adafruit_gps object
        The object for the GPS for other programs to call 
    
    OUPUTS
    ------
    lat, float
        Decimal latitude (degrees, North is positive)
        
    lon, float
        Decimal longitude (degrees, East is positive)
        
    alt, float
        Altitude above sea level (m)
        
    timestamp, datetime object
        The date and time at the time of the call
        
    info, dict
        Dictionary of other parameters
    '''
    
    # Required to call gps.update() at elast twice a loop
    gps.update()
    
    # Pull out the info
    year = int(gps.timestamp_utc.tm_year)
    month = int(gps.timestamp_utc.tm_mon)
    day = int(gps.timestamp_utc.tm_mday)
    hour = int(gps.timestamp_utc.tm_hour)
    minute = int(gps.timestamp_utc.tm_min)
    sec = int(gps.timestamp_utc.tm_sec)
    alt = int(gps.altitude_m)
    
    # Add other info to the dictionary
    info = {'n_sat': int(gps.satelites)}
    
    # Build timestamp
    timestamp = datetime.datetime(year = year,
                                  month = month,
                                  day = day,
                                  hour = hour,
                                  minute = minute,
                                  second = sec)
    
    return lat, lon, alt, timestamp, info