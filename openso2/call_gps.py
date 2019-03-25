# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 14:44:50 2018

@author: mqbpwbe2
"""

import gps
import logging
from multiprocessing import Process, Queue

import subprocess

def sync_gps_time():

    # Listen on port 2947 (GPSD) of localhost
    gpsd = gps.gps("localhost", "2947")
    gpsd.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

    while True:
      #wait until the next GPSD time tick
      gpsd.next()
      if gpsd.utc != None and gpsd.utc != '':
        #gpsd.utc is formatted like"2015-04-01T17:32:04.000Z"
        #convert it to a form the date -u command will accept: "20140401 17:32:04"
        #use python slice notation [start:end] (where end desired end char + 1)
        #   gpsd.utc[0:4] is "2015"
        #   gpsd.utc[5:7] is "04"
        #   gpsd.utc[8:10] is "01"
        gpsutc = gpsd.utc[0:4] + gpsd.utc[5:7] + gpsd.utc[8:10] + ' ' + gpsd.utc[11:19]
        subprocess.call('sudo date -u --set="%s"' % gpsutc, shell = True)
        logging.info('System time updated from GPS: ' + gpsutc)
        break



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
    def __init__(self):

        # Listen on port 2947 (GPSD) of localhost
        self.session = gps.gps("localhost", "2947")
        self.session.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

        # Create an empty GPS data list to hold the data
        self.gps_data = ['', '', '', '']

        # Create a stopping flag to halt the update loop
        self.stop_flag = False

        # Create a queue to hold the time info
        self.q = Queue()

        # Set off the GPS loop
        gps_pro = Process(target = self.gps_update, args=(self.q,))
        gps_pro.start()

#========================================================================================
#======================================= call_gps =======================================
#========================================================================================

    def gps_update(self, q):

        '''
        Function to loop the GPS

        This is called automatically by the GPS object, no need to run again!

        INPUTS
        ------
        q, multiprocessing.Queue
            Queue into which the gps data is placed. It is cleared before each placement
            to ensure the queue doesn't grow very long between calls
        '''

        while not self.stop_flag:

            # Emtpy the queue
            while q.qsize() > 1:
                q.get()

            # Get GPS data
            try:
                # Wait for a 'TPV' report
                report = self.session.next()

                if report['class'] == 'TPV':

                    time, latitude, longitude, altitude = '', '', '', ''

                    # Cycle through attributes and pull info if available
                    if hasattr(report, 'latitude'):
                        latitude = report.latitude
                    if hasattr(report, 'longitude'):
                        longitude = report.longitude
                    if hasattr(report, 'altitude'):
                        altitude = report.altitude
                    if hasattr(report, 'time'):
                        time = report.time

                    # Add the results to the queue
                    q.put([time, latitude, longitude, altitude])

            except KeyError:
                pass

            except StopIteration:
                self.session = None
                logging.info('GPSD has terminated')


#========================================================================================
#======================================= call_gps =======================================
#========================================================================================

    def call_gps(self):

        '''
        Function to get the time and position form the GPS

        INPUTS
        ------
        None

        OUTPUTS
        -------
        gps_data, list
            List of strings holding the GPS data in the format [time, lat, lon, alt]
        '''

        # Pull the data from the GPS object
        if self.q.qsize() > 0:
            self.gps_data = self.q.get()

        # Return the data
        return self.gps_data


#========================================================================================
#======================================= stop_gps =======================================
#========================================================================================

    def stop(self):

        '''
        Function to stop the gps update loop

        INPUTS
        ------
        None

        OUTPUTS
        -------
        None
        '''

        # Turn on the stop flag
        self.stop_flag = True