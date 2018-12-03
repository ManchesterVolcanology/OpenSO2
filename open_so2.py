# -*- coding: utf-8 -*-
"""
Created on Fri Mar  2 09:24:05 2018

@author: mqbpwbe2
"""

# Import required libraries
import matplotlib
matplotlib.use('TkAgg')
import traceback
import tkinter.messagebox as tkMessageBox
import tkinter.scrolledtext as tkst
from tkinter import ttk
import tkinter as tk
import seabreeze.spectrometers as sb
from seabreeze import SeaBreezeError
import logging

from openso2.build_gui import make_input
from openso2.call_gps import connect_gps, call_gps
from openso2.program_setup import read_settings
from openso2.scanner_control import connect_scanner, find_home

# Define some fonts to use in the program
NORM_FONT = ('Verdana', 8)
MED_FONT  = ('Veranda', 11)
LARG_FONT = ('Verdana', 12, 'bold')

class mygui(tk.Tk):
    
    def __init__(self, *args, **kwargs):
        
#========================================================================================
#================================= Build GUI Containers =================================
#========================================================================================
        
        # Create GUI in the backend
        tk.Tk.__init__(self, *args, **kwargs)
        
        # Cause exceptions to report in a new window
        tk.Tk.report_callback_exception = self.report_callback_exception
               
        # Close program on closure of window
        self.protocol("WM_DELETE_WINDOW", self.handler)
        
        # Create log
        logging.getLogger(__name__).addHandler(logging.NullHandler())
        
        # Button Style
        ttk.Style().configure('TButton', width = 15, height = 20, relief="flat") 
        
        # Add a title and icon
        tk.Tk.wm_title(self, 'Open SO2')
        try:
            tk.Tk.iconbitmap(self, default = 'data_bases/icon.ico')
        except tk.TclError:
            pass
        
        # Create frames
        spec_frame = tk.LabelFrame(self, text='Spectrometer Control', relief='groove',
                                   font=LARG_FONT)
        spec_frame.grid(row=0, column=0, padx=10, pady=10, sticky='NW')
        
        scan_frame = tk.LabelFrame(self, text = 'Scanner Control', relief = 'groove',
                                   font=LARG_FONT)
        scan_frame.grid(row=1, column=0, padx=10, pady=10, sticky='NW')
        
        stat_frame = tk.LabelFrame(self, text = 'Station Settings', relief = 'groove',
                                   font=LARG_FONT)
        stat_frame.grid(row=0, column=1, padx=10, pady=10, sticky='NW')
        
        disp_frame = tk.LabelFrame(self, text = 'Output', relief = 'groove',
                                   font=LARG_FONT)
        disp_frame.grid(row=1, column=1, padx=10, pady=10, sticky='NW')
        
        # Create settings dictionary
        global settings
        settings = {}
        
        # Create common dictionary
        global common
        common = {}
        
        # Read in settings file
        settings = read_settings('data_bases/settings.txt', settings)
                
#========================================================================================
#================================= Spectrometer Control =================================
#========================================================================================
        
        # Control the spectrometer
        self.spec_name = tk.StringVar(self, value = 'Not Connected')
        make_input(frame = spec_frame, 
                   text = 'Spectrometer:', 
                   row = 0, column = 0, 
                   var = self.c_spec, 
                   input_type = 'Label',
                   sticky = 'W')
        
        # Integration Time
        self.int_time = tk.DoubleVar(self, value = settings['int_time'])
        make_input(frame = spec_frame, 
                   text = 'Integration\ntime (ms):', 
                   row = 1, column = 0, 
                   var = self.int_time, 
                   input_type = 'Spinbox',
                   width = 15,
                   vals = [50, 1000],
                   increment = 50)
        
        # Coadds
        self.coadds = tk.DoubleVar(self, value = settings['coadds'])
        make_input(frame = spec_frame, 
                   text = 'Scans to\nAverage:', 
                   row = 2, column = 0, 
                   var = self.coadds, 
                   input_type = 'Spinbox',
                   width = 15,
                   vals = [1, 100])
        
        # Spectrometer status
        self.spec_stat = tk.StringVar(self, value = 'Disconnected')
        make_input(frame = spec_frame, 
                   text = 'Spectrometer\nStatus:', 
                   row = 3, column = 0, 
                   var = self.spec_stat, 
                   input_type = 'Label',
                   width = 10)
                
#========================================================================================
#=================================== Scanner Control ====================================
#========================================================================================
        
        # Scanner starting position
        self.scan_start = tk.DoubleVar(self, value = 12)
        make_input(frame = scan_frame, 
                   text = 'Start Pos:', 
                   row = 0, column = 0, 
                   var = self.scan_start, 
                   input_type = 'Spinbox',
                   width = 15,
                   vals = [1, 360])
        
        # Scanner stopping position
        self.scan_stop = tk.DoubleVar(self, value = 168)
        make_input(frame = scan_frame, 
                   text = 'Stop Pos:', 
                   row = 1, column = 0, 
                   var = self.scan_stop, 
                   input_type = 'Spinbox',
                   width = 15,
                   vals = [1, 360])
        
        # Scanner current position
        self.scan_curr = tk.DoubleVar(self, value = 0)
        make_input(frame = scan_frame, 
                   text = 'Current Pos:', 
                   row = 2, column = 0, 
                   var = self.scan_curr, 
                   input_type = 'Label')
        
        # Scanner status
        self.scan_stat = tk.StringVar(self, value = 'Disconnected')
        make_input(frame = scan_frame, 
                   text = 'Scanner\nStatus:', 
                   row = 3, column = 0, 
                   var = self.scan_stat, 
                   input_type = 'Label',
                   width = 10)
                
#========================================================================================
#================================== Station Settings ====================================
#========================================================================================
        
        # Start time for acquisition
        self.start_time = tk.DoubleVar(self, value = 0)
        make_input(frame = stat_frame, 
                   text = 'Start Time:', 
                   row = 0, column = 0, 
                   var = self.start_time, 
                   input_type = 'Entry',
                   width = 10)
        
        # Stop time for acquisition
        self.stop_time = tk.DoubleVar(self, value = 0)
        make_input(frame = stat_frame, 
                   text = 'Stop Time:', 
                   row = 1, column = 0, 
                   var = self.stop_time, 
                   input_type = 'Entry',
                   width = 10)
                
#========================================================================================
#=================================== Station Output =====================================
#========================================================================================
        
        row_n = 0
        # Scan number
        self.scan_no = tk.DoubleVar(self, value = 0)
        make_input(frame = disp_frame, 
                   text = 'Scan no.:', 
                   row = row_n, column = 0, 
                   var = self.scan_no, 
                   input_type = 'Label',
                   width = 10)
        
        # Spectrum Number
        self.spec_no = tk.DoubleVar(self, value = 0)
        make_input(frame = disp_frame, 
                   text = 'Spectrum no.:', 
                   row = row_n, column = 2, 
                   var = self.spec_no, 
                   input_type = 'Label',
                   width = 10)
        row_n += 1
        
        # Last spectrum SO2
        self.last_so2 = tk.DoubleVar(self, value = 0)
        make_input(frame = disp_frame, 
                   text = 'Last SO2:', 
                   row = row_n, column = 0, 
                   var = self.last_so2, 
                   input_type = 'Label',
                   width = 10)
        
        # Last spectrum error
        self.last_err = tk.DoubleVar(self, value = 0)
        make_input(frame = disp_frame, 
                   text = '+/-', 
                   row = row_n, column = 2, 
                   var = self.last_err, 
                   input_type = 'Label',
                   width = 10)
        row_n += 1
        
        # Last spectrum intensity
        self.last_int = tk.DoubleVar(self, value = 0)
        make_input(frame = disp_frame, 
                   text = '   Last\nIntensity:', 
                   row = row_n, column = 0, 
                   var = self.last_int, 
                   input_type = 'Label',
                   width = 10)
        
        # Last scan flux
        self.last_flux = tk.DoubleVar(self, value = 0)
        make_input(frame = disp_frame, 
                   text = 'Last Flux:', 
                   row = row_n, column = 2, 
                   var = self.last_int, 
                   input_type = 'Label',
                   width = 10)
        row_n += 1
        
        # Create frame to hold text output
        text_frame = ttk.Frame(disp_frame)
        text_frame.grid(row=row_n, column=0, padx=10, pady=10, columnspan=4, sticky="NW")      
                 
        # Build text box
        self.text_box = tkst.ScrolledText(text_frame, width = 42, height = 8)
        self.text_box.grid(row = 1, column = 0, padx = 5, pady = 5, sticky = 'W',
                           columnspan = 2)
        self.text_box.insert('1.0', 'Welcome to Open SO2! Written by Ben Esse\n\n') 
        
#========================================================================================
#============================= Connect to the spectrometer ==============================
#========================================================================================
        
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
                common['spec'] = sb.Spectrometer(devices[0])
                
                # Set intial integration time
                common['spec'].integration_time_micros(float(self.int_time.get())*1000)
                
                # Record serial number in settings
                settings['Spectrometer'] = str(common['spec'].serial_number)
                
                self.print_output('Spectrometer '+settings['Spectrometer']+' Connected')
                
            except SeaBreezeError:
                self.print_output('Spectrometer already open')
            
        # Update text to show spectrometer name
        self.spec_name.set(settings['Spectrometer'])     
        
#========================================================================================
#================================== Connect to the GPS ==================================
#========================================================================================
                
        # Connect to the GPS   
        common['gps'], err = connect_gps()
        
#========================================================================================
#======================== Connect to the motor and micro switch =========================
#========================================================================================
        
        # Connect to the motor and microswitch
        common['motor'], common['uswitch'], mh, err = connect_scanner()
        
        # If there was an error, report and exit
        if err[0] == True:
            self.print_output(err[1])
            
        else:
            
            # Move the motor to the home position
            err = find_home(common['motor'], common['uswitch'])
            
            if err[0] == True:
                self.print_output(err[1])
                
                
                
                
                
                
                
                
#========================================================================================
#========================= Check time and see if ready to scan ==========================
#========================================================================================                
                
    def check_time(self):
        
        # Get time form GPS
        call_gps(common['gps'])
                
                
                
                
                
                
                
        
#========================================================================================         
#========================================================================================
#===================================== GUI Operations ===================================
#======================================================================================== 
#======================================================================================== 

    # Report exceptions in a new window
    def report_callback_exception(self, *args):
        
        # Report error
        err = traceback.format_exception(*args)
        tkMessageBox.showerror('Exception', err)

    # Close program on 'x' button
    def handler(self):
        
        # Turn on stopping flag
        self.stop_flag = True
        
        # Open save dialouge
        text = 'Are you sure you want to quit?'
        message = tkMessageBox.askquestion('Exit', message = text, type = 'yesno')
        
        if message == 'yes':
            self.quit()
            
        if message == 'no':
            pass
        
    # Function to print text to the output box          
    def print_output(self, text, add_line = True):
        
        if add_line == True:
            # Add new line return to text
            text = text + '\n\n'
            
        else:
            text = text + '\n'
        
        # Write text with a new line
        self.text_box.insert(tk.END, text)
        
        # Scroll if needed
        self.text_box.see(tk.END)
        
        # Write to notes file
        try:
            with open(self.notes_fname, 'a') as a:
                a.write(text)
        
        except AttributeError:
            pass
        
        # Force gui to update
        mygui.update(self)  






# Run the App!
if __name__ == '__main__':    
    mygui().mainloop()
