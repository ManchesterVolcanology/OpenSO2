# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 14:44:50 2018

@author: mqbpwbe2
"""

import datetime
import adafruit_gps
import serial

class GPS:

    '''
    GPS class used to control the GPS of the scanning station

    INPUTS
    ------
    None

    METHODS
    -------
    get_location
        Function to get the GPS location. Returns the list [lat, lon, alt]

    get_time
        Function to get the date and time from the GPS clock. Returns a datetime object
    '''

    # Initialise
    def __inti__(self):

        # Establish uart access
        uart = serial.Serial("/dev/ttyUSB0", baudrate=9600, timeout=3000)

        # Create a GPS module instance
        self.gps = adafruit_gps.GPS(uart, debug=False)

        # Turn on basic GGA and RMC info
        self.gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')

        # Set update rate to be twice a second
        self.gps.send_command(b'PMTK220, 500')

        # Update gps
        self.gps.update()

#========================================================================================
#======================================= call_gps =======================================
#========================================================================================

    def call_gps(self):

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
        '''
        '''
        # Required to call gps.update() at elast twice a loop
        self.gps.update()

        # Pull out the info
        year   = int(self.gps.timestamp_utc.tm_year)
        month  = int(self.gps.timestamp_utc.tm_mon)
        day    = int(self.gps.timestamp_utc.tm_mday)
        hour   = int(self.gps.timestamp_utc.tm_hour)
        minute = int(self.gps.timestamp_utc.tm_min)
        sec    = int(self.gps.timestamp_utc.tm_sec)
        lat    = int(self.gps.latitude)
        lon    = int(self.gps.longitude)
        alt    = int(self.gps.altitude_m)

        # Build timestamp
        timestamp = datetime.datetime(year = year,
                                      month = month,
                                      day = day,
                                      hour = hour,
                                      minute = minute,
                                      second = sec)
        '''
        lat, lon, alt = 0, 0, 0
        timestamp = datetime.datetime.now()
        return lat, lon, alt, timestamp

#========================================================================================
#===================================== get_location =====================================
#========================================================================================

    def get_location(self):

        '''
        Function to get the position of the GPS

        INPUTS
        ------
        None

        OUTPUTS
        -------
        lat, float
            Latitude in decimal degrees. Positive is North

        lon, float
            Longitude in decimal degrees. Positive is East

        alt, float
            Altitude a.s.l. in meters
        '''

        # Update GPS
        self.gps.update()

        # Get location information
        lat = int(self.gps.latitude)
        lon = int(self.gps.longitude)
        alt = int(self.gps.altitude_m)

        return lat, lon, alt

#========================================================================================
#======================================= get_time =======================================
#========================================================================================

    def get_time(self):

        '''
        Function to get just the time from the gps clock

        INPUTS
        ------
        None

        OUTPUTS
        -------
        time_arr, list
            Returns 6 element array containing year, month, day, hour, minute and second
        '''
        '''
        # Update GPS
        self.gps.update()

        # Get location information
        year   = int(self.gps.timestamp_utc.tm_year)
        month  = int(self.gps.timestamp_utc.tm_mon)
        day    = int(self.gps.timestamp_utc.tm_mday)
        hour   = int(self.gps.timestamp_utc.tm_hour)
        minute = int(self.gps.timestamp_utc.tm_min)
        sec    = int(self.gps.timestamp_utc.tm_sec)
        '''

        t = datetime.datetime.now()
        year = '{:04d}'.format(t.year)
        month = '{:02d}'.format(t.month)
        day = '{:02d}'.format(t.day)
        hour = '{:02d}'.format(t.hour)
        minute = '{:02d}'.format(t.minute)
        sec = '{:02d}'.format(t.second)

        return year, month, day, hour, minute, sec