# -*- coding: utf-8 -*-
"""
Created on Fri Jun 29 10:43:17 2018

@author: mqbpwbe2
"""

import seabreeze.spectrometers as sb
from seabreeze.cseabreeze.wrapper import SeaBreezeError

#========================================================================================
#====================================== read_setttings ==================================
#========================================================================================

def read_settings(fname, settings):
    
    '''
    Fuction to read in the settings file
    
    INPUTS
    ------
    fname, str
        File path to settings file
    
    settings, dict
        Dictionary of GUI settings
        
    OUTPUTS
    -------
    settings, dict
        Setting dictionary updated with setings from the file
    '''
    
    # Open the settings file 
    with open(fname, 'r') as r:
                
        # Read data line by line
        data = r.readlines()
        
        # Unpack and save to dictionary
        for i in data:
            name, val, dtype = i.strip().split(';')
            
            # Get the parameter value and change to correct variable type
            if dtype == "<class 'float'>":
                settings[name] = float(val)
                
            
            if dtype == "<class 'int'>":
                settings[name] = int(val)
                
                
            if dtype == "<class 'bool'>":
                if val == 'True':
                    settings[name] = True
                if val == 'False':
                    settings[name] = False
                             
            if dtype == "<class 'str'>":
                settings[name] = str(val)
                    
    return settings

#========================================================================================
#======================================= Find Home ======================================
#========================================================================================
        

        
