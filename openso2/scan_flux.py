# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 08:48:42 2018

@author: mqbpwbe2
"""

import numpy as np
from math import radians, cos, tan

def scan_flux(angles, so2, windspeed = 10, height = 1000, plume_type = 'flat'):
    
    '''
    Function to calculate the SO2 flux from a scan. Either assumes all SO2 is at the same
    altitude or that it is contained within a cylindrical plume
    
    INPUTS
    ------
    angles, array
        The anglular position of each spectrum in the scan (degrees)
        
    so2, array
        The so2 column density retrieved form each spectrum in molecules/cm^2. Must be 
        the same length as angles
        
    windspeed, float (optional)
        The wind speed used to calculate the flux in m/s (default is 10 m/s)
        
    height, float (optional)
        The height of the plume in meters (default is 1000 m)
        
    plume_type, str (optional)
        The type of plume.
            - 'flat' assumes all so2 is at the same altitude in a flat blanket. Good for
              wide plumes
            
            - 'cylinder' assumes the plume is cylindrical. Good for smaller plumes.
            
    OUTPUTS
    -------
    flux, float
        The flux of SO2 passing through the scan in tonnes/day
    '''
    
    # Check that the plume type is possible
    if plume_type not in ['flat', 'cylinder']:
        raise Exception('Plume type not recognised. Must be either "flat" or "cylinder"')
    
    # Convert the angles to radians
    rad_angles = [radians(a) for a in angles]
    
    # Correct the so2 column density to account for the scan angle
    corr_so2 = np.zeros(len(so2))
    for n, s in enumerate(so2):
        corr_so2[n] = s * cos(rad_angles[n])
    
    # Calculate the horizontal distance between the subsiquent scans
    dx = np.zeros(len(rad_angles) - 1)
    for n in range(len(dx)):
        dx[n] = height * (tan(rad_angles[n+1] - tan(rad_angles[n])))
        
    # Multiply the average SO2 column density of each two subsiquent spectra by the 
    #  horizontal distance between them
    arc_so2 = np.zeros(len(dx))
    for n, x in enumerate(dx):
        arc_so2[n] = x * (corr_so2[n+1] + corr_so2[n]) / 2
        
    # Sum the so2 in the scan
    tot_so2 = np.sum(arc_so2)
    
    # Convert from molecules/cm to moles/m
    so2_moles = tot_so2 * 1.0e4 / 6.022e23

    # Convert to kg/m. Molar mass of so2 is 64.066g/mole
    so2_kg = so2_moles * 0.064066
    
    # Get flux in kg/s
    flux_kg_s = so2_kg * windspeed
    
    # Convert to tonnes/day
    flux = flux_kg_s * 1.0e-3 * 86400
    
    return flux
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    