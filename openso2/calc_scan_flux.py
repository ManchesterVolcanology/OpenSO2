#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 16 15:16:36 2019

@author: mqbpwbe2
"""

import numpy as np
from openso2.calc_plume_height import haversine

#==============================================================================
#============================== calc_arc_radius ===============================
#==============================================================================

def calc_arc_radius(volc_loc, stat_info, plume_az, plume_height):

    '''
    Function to calculate the radius of the scan arc given the location of
    scanner and volcano, and the plume height and azimuth.

    **Parameters**

    volc_loc : tuple of floats
        The volcano coordinates (lat, lon) in decimal degrees

    stat_info : list
        Contains the scanner information in the form [lat, lon, az, alt]

            - lat: the station latitude in decimal degrees

            - lon: the station longitude in decimal degrees

            - alt: the station altitude

            - az:  the azimuth of the scanning plane, defined as the direction
                   in degrees clockwise form north of the start of the scan.
                   Should be 0 - 360.

    plume_az : float
        The plume azimuth in degrees clockwise form North

    plume_height : float
        The height of the plume above the station

    **Returns**

    arc_radius : float
        The radius of the arc
    '''

    # Unpack the station info
    stat_lat, stat_lon, alt, scan_az = stat_info

    # Convert the plume azimuth to radians
    plume_az = np.radians(plume_az)

    # Find the distance and bearing from the volcano to the station
    x, mu = haversine(volc_loc, [stat_lat, stat_lon])

    # Make sure the bearing is between 0 and 2pi
    if mu < 0:
        mu += np.pi * 2

    # Calculate the distance between the scanner and where the plume intersects
    #  the scan plane
    d = x * (np.sin(abs(plume_az - mu)) / np.sin(abs(plume_az - np.pi)))

    # Subtract the station altitude from the plume height
    height_above_stat = plume_height - alt

    # Calculate the arc radius from d and the plume height from Pythag
    arc_radius = np.sqrt(height_above_stat**2 + d**2)

    return arc_radius

#==============================================================================
#=============================== Calc Scan Flux ===============================
#==============================================================================

def calc_scan_flux(df, stat_info, volc_loc, windspeed, plume_az, plume_height,
                   flux_units = 't/day'):

    '''
    Function to calculate the SO2 flux from a scan. Assumes all the gas is at a
    fixed distance from the scanner

    **Parameters:**

    angles : list or array
        The angle of each measurement in a scan

    so2_amt : list or array
        The retrieved SO2 SCD in molecules/cm2 for each measurement. Must have
        the same length as angles

    stat_info : list
        Contains the scanner information in the form [lat, lon, az, alt]

            - lat: the station latitude in decimal degrees

            - lon: the station longitude in decimal degrees

            - alt: the station altitude

            - az:  the azimuth of the scanning plane, defined as the direction
                   in degrees clockwise form north of the start of the scan.
                   Should be 0 - 360.

    volc_loc : tuple of floats
        The coordinates of the volcano (or vent) in decimal degrees

    windspeed : float
        The wind speed used to calculate the flux in m/s

    plume_az : float
        The plume azimuth in degrees clockwise from North.

    plume_height : float
        The height of the plume in meters

    flux_units : str
        The units to report the flux as. One of 't/day' or 'kg/s'

    **Returns:**

    flux : float
        The flux of SO2 passing through the scan in tonnes/day
    '''

    # Get the fit quality
    idx = np.logical_and(df['fit_quality'] == 1, df['so2'].notnull())

    # Extract the data from the dataframe
    so2_amts = np.asarray(df['so2'])[idx]
    so2_errs = np.asarray(df['so2_e'])[idx]
    angles = np.asarray(df['angle'])[idx]

    # Convert all angles to radians
    phi = np.radians(angles)

    # Calculate the delta angle
    dphi = [phi[n+1] - phi[n] for n in range(len(phi) - 1)]

    # Calculate the arc radius
    arc_radius = calc_arc_radius(volc_loc, stat_info, plume_az, plume_height)

    # Convert to arc length
    dx = np.multiply(dphi, arc_radius)

    # Calculate the so2 mass in each spectrum
    arc_so2 = [x/2 * (so2_amts[n+1] + so2_amts[n]) for n, x in enumerate(dx)]

    # Sum the so2 in the scan
    total_so2 = np.sum(arc_so2)

    # Correct for the scan angle through the plume
    scan_az = stat_info[3]
    corr_total_so2 = total_so2 * np.sin(np.radians(plume_az - scan_az))

    # Convert from molecules/cm to moles/m
    so2_moles = corr_total_so2 * 1.0e4 / 6.022e23

    # Convert to kg/m. Molar mass of so2 is 64.066g/mole
    so2_kg = so2_moles * 0.064066

    # Get flux in kg/s
    flux_kg_s = so2_kg * windspeed

    # Calculate the error
    deltaA = np.divide(np.average(np.abs(so2_errs)), np.average(so2_amts))

    if flux_units == 'kg/s':
        flux = flux_kg_s

    elif flux_units == 't/day':
        flux = flux_kg_s * 1.0e-3 * 8.64e4

    # Calculate the flux error
    flux_err = flux * deltaA

    return flux, flux_err

#==============================================================================
#============================== Get Station Info ==============================
#==============================================================================

def get_station_data(station):

    '''
    Function to pull the station information from file

    **Parameters**

    station : str
        The station name

    **Returns**

    stat_lat : float
        The station latitude in decimal degrees

    stat_lon : float
        The staiton longitude in decimal degrees

    stat_alt : float
        The station altitude in m above sea level

    scan_az : float
        the azimuth of the scanning plane, defined as the direction in degrees
        clockwise form north of the start of the scan. Should be 0 - 360.
    '''

    stat_dict = {'LOVE': [16.7171, -62.2176, 80, 180]}

    return stat_dict[station]


if __name__ == '__main__':

    volc_loc = [16.7103, -62.1773]
    stat_loc = [16.7171, -62.2176]
    plume_az = 260
    plume_height = 915

    r = calc_arc_radius(volc_loc, stat_loc, plume_az, plume_height)

    print(r)




