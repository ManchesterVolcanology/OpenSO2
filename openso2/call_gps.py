# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 14:44:50 2018

@author: mqbpwbe2
"""

import datetime

def call_gps():
    
    '''
    Function to call the connected GPS.
    
    INPUTS
    ------
    None
    
    OUPUTS
    ------
    lat, float
        Decimal latitude (degrees, North is positive)
        
    lon, float
        Decimal longitude (degrees, East is positive)
        
    alt, float
        Altitude above sea level (m)
        
    time, datetime object
        The date and time at the time of the call
    '''
    
    print('This function will call the GPS')
    
    lat = 1
    lon = 1
    alt = 1
    time = datetime.datetime.now()
    
    return lat, lon, alt, time