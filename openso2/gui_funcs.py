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
#================================ Connect to Spectrometer ===============================
#========================================================================================
        
# Function to connect to the attached spectrometer
def connect_spec(self, settings):
    
    '''
    Fuction to connect to a spectrometer
    
    INPUTS
    ------
    self,
        Program object containing parameters
        
    settings, dict
        Contains the GUI settings
        
    OUTPUTS
    -------
    None
    '''
    
    # Find connected spectrometers
    devices = sb.list_devices()
    
    # If no devices are connected then set string to show. Else assign first to spec
    if len(devices) == 0:
        self.spec = 0
        settings['Spectrometer'] = 'Not Connected'
        devices = ['Not Connected']
        self.print_output('No devices found')
    else:
        try:
            # Connect to spectrometer
            self.spec = sb.Spectrometer(devices[0])
            
            # Set intial integration time
            self.spec.integration_time_micros(float(self.int_time.get())*1000)
            
            # Record serial number in settings
            settings['Spectrometer'] = str(self.spec.serial_number)
            
            self.print_output('Spectrometer '+settings['Spectrometer']+' Connected')
            
            # Create notes file
            self.notes_fname = self.results_folder + 'notes.txt'
            with open(self.notes_fname, 'w') as w:
                w.write('Notes file for iFit\n\n')
    
            
        except SeaBreezeError:
            self.print_output('Spectrometer already open')
        
    # Update text to show spectrometer name
    self.c_spec.set(settings['Spectrometer'])
        
