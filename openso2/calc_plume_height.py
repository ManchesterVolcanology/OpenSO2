# -*- coding: utf-8 -*-
"""
Created on Mon Sep 17 11:08:03 2018

@author: mqbpwbe2
"""

import numpy as np
from math import radians, degrees, sin, cos, tan, atan, pi, atan2

#==============================================================================
#==============================================================================
#==============================================================================

def station_data(station):

    '''
    Function to retrieve the station data required

    INPUTS
    ------
    station, string
        Station name

    OUTPUTS
    -------
    lat, float
        Station latitude in decimal degrees (N is positive)

    lon, float
        station longitude in decimal degrees (E is positive)

    alt, float
        station altitude in m a.s.l.

    az, float
        station azimuth, defined as the direction orthogonal to the clockwise 
        rotation (left hand) in degrees clockwise from North
    '''

    # Set station data
    #                Name    Lat      Lon       Alt  Azimuth
    station_info = {'LOVE': [16.7171, -62.2176, 50,  180]
                    }

    # Check that the station data exists
    if station not in station_info.keys():
        raise Exception('Station not recognised')

    return station_info[station]

#==============================================================================
#==============================================================================
#==============================================================================

def calc_plume_height(volc_loc, station1, station2, theta1, theta2):

    '''
    Function to calculate the height of a plume measured by two scanning 
    stations

    **Parameters**
    
    volc_loc : tuple
        The Lat/Lon coordinates of the volcano in decimal degrees
    
    station1/station2 : string
        Station names

    theta1/theta2 : float
        Scan angle of the plume (anticlockwise facing the vent)

    **Returns**
    
    plume_height : height of the plume in meters a.s.l.
    '''

    # Volcano location for Etna
    volc_lat, volc_lon = volc_loc

    # Unpack the station information
    lat1, lon1, alt1, az1 = station_data(station1)
    lat2, lon2, alt2, az2 = station_data(station2)

    # Convert angles into radians
    az1 = radians(az1)
    az2 = radians(az2)
    theta1 = radians(theta1)
    theta2 = radians(theta2)

    # Calculate x and mu, the distance and bearing from the volcano to the 
    #  scanner
    x1, mu1 = haversine(volc_lat, volc_lon, lat1, lon1)
    x2, mu2 = haversine(volc_lat, volc_lon, lat2, lon2)

    # Calculate phi from the azimuth and convert to radians
    if theta1 > pi/2:
        phi1 = az1 + (pi/2)
        theta1 = pi - theta1
    else:
        phi1 = az1 - (pi/2)

    if theta2 > pi/2:
        phi2 = az2 + (pi/2)
        theta2 = pi - theta2
    else:
        phi2 = az2 - (pi/2)

    # Calculate quadratic coeficents
    try:
        a = sin(phi1 - phi2) / (tan(theta1) * tan(theta2))
        b = ((x1 * sin(mu1-phi2)) / tan(theta2))+((x2 * sin(phi1-mu2)) / tan(theta1))
        c = x1 * x2 * sin(mu1 - mu2)

    except ZeroDivisionError:
        return np.nan

    # Solve for the roots
    det = ( b**2 - ( 4*a*c ) )**0.5

    try:
        h = np.array([(-b + d) / (2 * a) for d in [det, -det]])
    except ZeroDivisionError:
        print('Division by zero incountered')
        print('Theta values:', station1, "{:.2f}".format(degrees(theta1)), \
                               station2, "{:.2f}".format(degrees(theta2)))
        print('Phi values:', station1, "{:.2f}".format(degrees(phi1)), \
                             station2, "{:.2f}".format(degrees(phi2)))
        return np.nan

    # Only use the positive root and add the altitude of the first station
    try:
        height = float(h[np.where(h > 0)]) + alt1

    except TypeError:
        #print('Result is complex, no plume height found')
        #print('Theta values:', station1, "{:.2f}".format(degrees(theta1)), \
        #                       station2, "{:.2f}".format(degrees(theta2)))
        #print('Phi values:', station1, "{:.2f}".format(degrees(phi1)), \
        #                     station2, "{:.2f}".format(degrees(phi2)) + '\n')
        return np.nan

    return height

#==============================================================================
#==============================================================================
#==============================================================================

def calc_plume_azimuth(station1, station2, theta1, theta2, solution_no = 0):

    '''
    Function to calculate the azimuth of a plume measured by two scanning 
    stations

    **Parameters**
    
    station1/station2 : string
        Station name

    theta1/theta2 : float
        Scan angle of the plume (anticlockwise facing the vent)

    solution_no : int
        The number of the solution to report. Two are generated, so must be 
        either 0 or 1

    **Returns**
    
    plume_azimuth : float
        Azimth of the plume in degrees clockwise from North
    '''

   # Volcano location for Etna
    volc_lat, volc_lon = 37.750529, 14.993437

    # Unpack the station information
    lat1, lon1, alt1, az1 = station_data(station1)
    lat2, lon2, alt2, az2 = station_data(station2)

    # Convert angles into radians
    az1 = radians(az1)
    az2 = radians(az2)
    theta1 = radians(theta1)
    theta2 = radians(theta2)

    # Calculate x and mu, the distance and bearing from the volcano to the 
    #  scanner
    x1, mu1 = haversine(volc_lat, volc_lon, lat1, lon1)
    x2, mu2 = haversine(volc_lat, volc_lon, lat2, lon2)

    # Caclulate the distance and bearing between the two stations
    dist, bearing = haversine(lat2, lon2, lat1, lon1)

    # Calculate phi from the azimuth and convert to radians
    if theta1 > pi/2:
        phi1 = az1 + (pi/2)
        theta1 = pi - theta1
    else:
        phi1 = az1 - (pi/2)

    if theta2 > pi/2:
        phi2 = az2 + (pi/2)
        theta2 = pi - theta2
    else:
        phi2 = az2 - (pi/2)

    # Define quadratic coefs
    a = (x1*tan(theta1)*cos(phi2)*cos(mu1))-(x2*tan(theta2)*cos(phi1)*cos(mu2))

    b = (x2*tan(theta2)*sin(phi1 + mu2)) - (x1*tan(theta1)*sin(mu1 + phi2))

    c = (x1*tan(theta1)*sin(mu1)*sin(phi2))-(x2*tan(theta2)*sin(mu2)*sin(phi1))

    # Calculate the determinant
    det = (b**2 - (4*a*c))**0.5

    # Solve
    tan_az = [(-b + d) / (2 * a) for d in [det, -det]]

    # Take inverse tan, selecting one solution
    try:
        plume_azimuth = atan(tan_az[solution_no])

        # Check angle is positive
        if plume_azimuth < 0:
            plume_azimuth += pi

    except TypeError:
        print('Result is complex, no plume height found')
        return np.nan

    return degrees(plume_azimuth)

#==============================================================================
#==============================================================================
#==============================================================================

def calc_plume_height_single(volc_loc, station, plume_azimuth, theta):

    '''
    Function to calculate the height of the plume from a single station given 
    the azimuth

    **Parameters**
    
    volc_loc : tuple
        The Lat/Lon coordinates of the volcano in decimal degrees
    
    station : string
        Name of the station

    plume_azimuth : float
        Plume azimuth direction assuming straight line transport from source to 
        scanner (degrees clockwise from North)

    theta : float
        Scan angle of the plume (anticlockwise facing the vent)

    **Returns**
    
    height : float
        Calculated plume height (m a.s.l.), including the altitude of the 
        station
    '''

    # Unpack the station information
    lat, lon, alt, az = station_data(station)

    # Convert angles into radians
    az = radians(az)
    theta = radians(theta)
    plume_azimuth = radians(plume_azimuth)

    # Calculate x and mu, the distance and bearing from the volcano to the 
    #  scanner
    x, mu = haversine(volc_loc, [lat, lon])

    # Calculate phi, gamma and delta from the station layout
    if theta > pi/2:
        theta = pi - theta
        phi = az + (pi/2)
        gamma = plume_azimuth - mu
        delta = phi - plume_azimuth

    else:
        phi = az - (pi/2)
        gamma = mu - plume_azimuth
        delta = plume_azimuth - phi

    # Calculate the height, adding the station altitude
    plume_height = (x * sin(gamma) * tan(theta)) / sin(delta) + alt

    return plume_height

#==============================================================================
#==============================================================================
#==============================================================================

def calc_plume_azimuth_single(station, plume_height, theta):

    '''
    Function to calculate the azimuth of the plume from a single station given 
    the height

    **Parameters**
    
    station : string
        Name of the station

    height : float
        Plume height (m a.s.l.)

    theta : float
        Scan angle of the plume (anticlockwise facing the vent)

    **Returns**
    
    height : float
        Calculated plume azimuth (degrees clockwise from North)
    '''

    # Volcano location for Etna
    volc_lat, volc_lon = 37.750529, 14.993437

    # Unpack the station information
    lat, lon, alt, az = station_data(station)

    # Convert angles into radians
    az = radians(az)
    theta = radians(theta)

    # Calculate x and mu, the distance and bearing from the volcano to the 
    #  scanner
    x, mu = haversine(volc_lat, volc_lon, lat, lon)

    # Take station altitude from plume height
    plume_height = plume_height - alt

    # Calculate phi from the azimuth and convert to radians
    if theta > pi/2:
        phi = az + (pi/2)
        theta = pi - theta
    else:
        phi = az - (pi/2)

    # Calculate top and botton row of quotiant
    top = (x * sin(mu) * tan(theta)) + (plume_height * sin(phi))
    bot = (x * cos(mu) * tan(theta)) + (plume_height * cos(phi))

    # Take atan
    plume_azimuth = atan(top / bot)

    # Check the angle is positive
    if plume_azimuth < 0:
        plume_azimuth += pi

    return degrees(plume_azimuth)

#==============================================================================
#================================= haversine ==================================
#==============================================================================

def haversine(start_coords, end_coords, radius = 6371000):
    
    '''
    Function to calculate the distance and initial bearing between two points
    
    **Parameters**

    start_coords : tuple
        Start coordinates (lat, lon) in decimal degrees (+ve = north/east)
           
    end_coords : tuple
        End coordinates (lat, lon) in decimal degrees (+ve = north/east)
        
    radius : float, optional (default 6371000 m)
        Radius of the body in meters. Default is set to the Earth radius 
        
    **Returns**
    
    distance : float
        The linear distance between the two points in meters
        
    bearing : float
        The initial bearing between the two points (radians clockwise from N)
    '''
    
    # Unpack the coordinates and convert to radians
    lat1, lon1 = np.radians(start_coords)
    lat2, lon2 = np.radians(end_coords)
    
    # Calculate the change in lat and lon
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    # Calculate the square of the half chord length
    a = (sin(dlat/2))**2 + ( cos(lat1) * cos(lat2) * (sin(dlon/2))**2 )
    
    # Calculate the angular distance
    c = 2 * atan2(np.sqrt(a), np.sqrt(1-a))
    
    # Find distance moved
    distance = radius * c

    # Calculate the initial bearing
    bearing = atan2(sin(dlon) * cos(lat2),
                    (cos(lat1)*sin(lat2)) - (sin(lat1)*cos(lat2)*cos(dlon)))
    
    return distance, bearing

