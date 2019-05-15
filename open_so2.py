# -*- coding: utf-8 -*-
"""
Created on Fri Jan 25 13:02:09 2019

@author: mqbpwbe2
"""

import os
from pathlib import Path
import numpy as np
import logging
from tkinter import ttk
import tkinter as tk
import traceback
import datetime as dt
import tkinter.scrolledtext as tkst
import tkinter.messagebox as tkMessageBox
from multiprocessing import Process, Queue
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from openso2.program_setup import get_station_info, update_resfp
from openso2.station_com import Station, sync_station
from openso2.analyse_scan import calc_scan_flux, calc_plume_height, get_wind, read_scan_so2
from openso2.julian_time import hms_to_julian
from openso2.gui_funcs import update_graph, make_input
from openso2.station_status import get_station_status

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

        # Button Style
        ttk.Style().configure('TButton', width = 15, height = 20, relief="flat")

        # Add a title and icon
        tk.Tk.wm_title(self, 'Open SO2 v1.0 - Home Station')
        try:
            tk.Tk.iconbitmap(self, default = 'data_bases/icon.ico')
        except tk.TclError:
            pass

        # Read in the station information
        self.station_info = get_station_info('data_bases/station_info.txt')

        # Create dictionary of station objects
        self.stat_com = {}
        for station in self.station_info.keys():
            self.stat_com[station] = Station(self.station_info[station], station)

        # Create dicionaries to hold the flux results and plume height and speed
        self.times   = {}
        self.fluxes  = {}
        self.wtimes  = []
        self.heights = []
        self.speeds  = []

        # Populate the flux dictionaries with arrays for each staiton
        for station in self.station_info.keys():
            self.times[station]   = []
            self.fluxes[station]  = []

        # Create notebook to hold overview and station info pages
        nb = ttk.Notebook(self)

        # Add overview page
        overview_page = ttk.Frame(nb)
        nb.add(overview_page, text = 'Overview')

        # Add station pages
        station_page = {}
        for station in self.station_info.keys():

            station_page[station] = ttk.Frame(nb)
            nb.add(station_page[station], text = station)

        # Add the notebook to the GUI
        nb.grid(column=0, padx=10, pady=5, sticky = 'NW')

        mygui.columnconfigure(index = 1, weight = 1, self = self)
        mygui.rowconfigure(index = 5, weight = 1, self = self)

#========================================================================================
#================================== Add global widgets ==================================
#========================================================================================

#===================================== Graph Frame ======================================

        # Create frame to hold graphs
        graph_frame = ttk.Frame(self, relief = 'groove')
        graph_frame.grid(row=0, column=1, padx=10, pady=10, sticky="NW")
        graph_frame.columnconfigure(index = 0, weight = 1)
        graph_frame.rowconfigure(index = 0, weight = 1)

        # Create figure to hold the graphs
        plt.rcParams.update({'font.size': 8})
        self.fig = plt.figure(figsize = (8, 5))
        gs = gridspec.GridSpec(2, 2)

        # Create plot axes
        self.ax0 = self.fig.add_subplot(gs[0,:])
        self.ax1 = self.fig.add_subplot(gs[1,0])
        self.ax2 = self.fig.add_subplot(gs[1,1])

        # Set axis labels
        self.ax0.set_xlabel('Time (decimal hours)', fontsize = 10)
        self.ax0.set_ylabel('SO$_2$ Flux (t/day)',  fontsize = 10)
        self.ax1.set_xlabel('Scan Angle (deg)',     fontsize = 10)
        self.ax1.set_ylabel('SO2 CD (ppm.m)',       fontsize = 10)
        self.ax2.set_xlabel('Time (decimal hours)', fontsize = 10)
        self.ax2.set_ylabel('Wind Speed (m/s)',     fontsize = 10)

        # Create lines for each station flux plot
        self.flux_lines = {}
        for station in self.station_info.keys():
            self.flux_lines[station], = self.ax0.plot(0, 0, 'o-', label = station)

        self.cd_line, = self.ax1.plot(0, 0)
        self.wind_speed_line, = self.ax2.plot(0, 0)

        # Add a title
        self.date = str(dt.datetime.now().date())
        self.ax0.set_title(self.date)

        # Make the plot look nice
        plt.tight_layout()

        # Add legend
        self.ax0.legend(loc = 0)

        # Create the canvas to hold the graph in the GUI
        self.canvas = FigureCanvasTkAgg(self.fig, graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, padx=10, pady = 10)

        # Add matplotlib toolbar above the plot canvas
        toolbar_frame = tk.Frame(graph_frame, bg = 'black')
        toolbar_frame.grid(row=1,column=0, sticky = 'W', padx = 5, pady = 5)
        toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        toolbar.update()

#===================================== Text Output ======================================

        # Create frame to hold text output
        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=1, padx=10, pady=5, sticky="NE")

        # Build text box
        self.text_box = tkst.ScrolledText(text_frame, width = 100, height = 8)
        self.text_box.grid(row = 1, column = 0, padx = 5, pady = 5, sticky = 'E',
                           columnspan = 2)
        self.text_box.insert('1.0', 'Welcome to Open SO2! Written by Ben Esse\n\n')

#========================================================================================
#=============================== Add widjets to overview ================================
#========================================================================================

#==================================== Sync Controls =====================================

        # Create frame
        sync_frame = tk.LabelFrame(overview_page, text = 'Sync Settings',
                                   font = LARG_FONT)
        sync_frame.grid(row=0, column=0, padx=10, pady=10, sticky="NW")

        # Ceate input for the results filepath
        self.res_fpath = tk.StringVar(value = 'Results/')
        res_fpath_ent = tk.Entry(sync_frame, font = NORM_FONT, width = 30,
                                 text = self.res_fpath)
        res_fpath_ent.grid(row = 0, column = 0, padx = 5, pady = 5, sticky = 'W',
                           columnspan = 2)
        res_fpath_b = ttk.Button(sync_frame, text = "Browse",
                                 command = lambda: update_resfp(self))
        res_fpath_b.grid(row = 0, column = 2, padx = 5, pady = 5, sticky = 'W')

        # Create control for the control loop speed
        self.loop_speed = tk.IntVar(value = 30)
        make_input(frame = sync_frame,
                   text = 'Sync Delay (s):',
                   var = self.loop_speed,
                   input_type = 'Spinbox',
                   row = 1, column = 0,
                   vals = (1, 600),
                   width = 10)

        # Create status indicator
        self.status = tk.StringVar(value = 'Standby')
        self.status_e = tk.Label(sync_frame, textvariable = self.status, fg='red')
        self.status_e.grid(row=1, column=2, padx=5, pady=5, sticky="EW")
        self.status_col = 'red'

#==================================== Flux Controls =====================================

        # Create Frame
        flux_frame = tk.LabelFrame(overview_page, text = 'Flux Settings',
                                   font = LARG_FONT)
        flux_frame.grid(row=1, column=0, padx=10, pady=10, sticky="NW")

        # Create control for the plume height
        self.plume_height = tk.IntVar(value = 1000)
        make_input(frame = flux_frame,
                   text = 'Plume Height (m):',
                   var = self.plume_height,
                   input_type = 'Spinbox',
                   row = 0, column = 0,
                   width = 10,
                   vals = [0, 5000], increment = 100)

        # Select how the plume height is calculated
        self.how_calc_height = tk.StringVar(value = 'Fix')
        make_input(frame = flux_frame,
                   text = None,
                   var = self.how_calc_height,
                   input_type = 'OptionMenu',
                   row = 0, column = 2,
                   width = 5,
                   options = [self.how_calc_height.get(), 'Fix', 'Calc'])

        # Create control for the wind speed
        self.wind_speed = tk.IntVar(value = 10)
        make_input(frame = flux_frame,
                   text = 'Wind Speed (m/s):',
                   var = self.wind_speed,
                   input_type = 'Spinbox',
                   row = 1, column = 0,
                   width = 10,
                   vals = [0, 30], increment = 0.1)

        # Select how the wind speed is set
        self.how_calc_wind = tk.StringVar(value = 'Fix')
        make_input(frame = flux_frame,
                   text = None,
                   var = self.how_calc_wind,
                   input_type = 'OptionMenu',
                   row = 1, column = 2,
                   width = 5,
                   options = [self.how_calc_wind.get(), 'Fix', 'Pull'])

        # Create control for the wind direction
        self.wind_dir = tk.IntVar(value = 90)
        make_input(frame = flux_frame,
                   text = 'Wind Bearing (deg):',
                   var = self.wind_dir,
                   input_type = 'Spinbox',
                   row = 2, column = 0,
                   width = 10,
                   vals = [0, 360], increment = 5)

#========================================================================================
#========================== Add widjets to the station pages ============================
#========================================================================================

        # Create dictionaries to hold the corresponding widgets for each station
        self.station_widjets = {}

        for station in self.station_info.keys():

            # Ceate sub dictionary to hold the widjets for this station
            station_w = {}

            # Create a frame to hold the station status
            s_frame = tk.LabelFrame(station_page[station], text = 'Station Status',
                                    font = LARG_FONT)
            s_frame.grid(row = 0, column = 0, padx = 10, pady = 10)

            # Create status indicator
            station_w['status'] = tk.StringVar(value = '-')
            make_input(frame = s_frame,
                       text = 'Status:',
                       var = station_w['status'],
                       input_type = 'Label',
                       row = 0, column = 0)

            station_w['status_time'] = tk.StringVar(value = '-')
            make_input(frame = s_frame,
                       text = 'Status Time:',
                       var = station_w['status_time'],
                       input_type = 'Label',
                       row = 1, column = 0)

            # Create a button to update the status now
            ttk.Button(s_frame, text = 'Get Status',
                       command = lambda: get_station_status(self, station)
                       ).grid(row = 2, column = 1)

            # Add the station widjets to the master dictionary
            self.station_widjets[station] = station_w

#========================================================================================
#=============================== Start the control loop =================================
#========================================================================================

        # Begin the control loop
        self.after(1000, self.begin_sync)

#========================================================================================
#===================================== Control Loop =====================================
#========================================================================================

    def begin_sync(self):

        # Check the date and time
        timestamp = dt.datetime.now()
        today_date = str(timestamp.date())

        # Check if the date has changed
        if today_date != self.date:

            # Update the date
            self.date = today_date

            # Change the plot title
            self.ax0.set_title(today_date)

            # Clear the results lists
            for s in self.station_info.keys():
                self.times[s]   = []
                self.fluxes[s]  = []

                # Clear the plots
                data = np.array(([self.times[s], self.fluxes[s], 'auto', [0, 500]]))
                lines = [self.flux_lines[s]]
                axes  = [self.ax0]
                update_graph(lines, axes, self.canvas, data)

        # Create dictinary to hold the file paths
        self.so2_fpaths  = {}
        self.spec_fpaths = {}
        self.flux_fpaths = {}

        # Check that the required results folders and files exist
        for station in self.station_info.keys():

            # Build master filepath and add to dictionaries
            m_fpath = self.res_fpath.get() + today_date + '/' + station + '/'
            self.so2_fpaths[station]  = m_fpath + '/so2/'
            self.spec_fpaths[station] = m_fpath + '/spectra/'
            self.flux_fpaths[station] = f'{m_fpath}{today_date}_{station}_fluxes.csv'

            # Create the folder
            os.makedirs(self.so2_fpaths[station],  exist_ok = True)
            os.makedirs(self.spec_fpaths[station], exist_ok = True)

            # Create the results file if it doesn't exist
            if not Path(self.flux_fpaths[station]).is_file():

                # Create the file and write the header row
                with open(self.flux_fpaths[station], 'w') as w:
                    w.write('Time,Plume Height (m),Wind Speed (ms-1),Flux (t/day)\n')

        # If the stations are operational sync the so2 files. If sleeping sync spectra
        # Stations should be operational from 08:00 - 16:00 (local time)
        jul_time = hms_to_julian(timestamp)
        if jul_time > 8 and jul_time < 16.2:
            self.sync_mode = '/so2/'
        else:
            self.sync_mode = '/spectra/'

        # Build a queue to hold the results
        self.q = Queue()

        # Sync the home folders with remotes
        self.status.set('Syncing')
        self.update()

        for station in self.station_info.keys():

            # Generate local and remote file paths to sync
            if self.sync_mode == '/so2/':
                local_dir = self.so2_fpaths[station]
            if self.sync_mode == '/spectra/':
                local_dir = self.spec_fpaths[station]
            remote_dir = '/home/pi/open_so2/Results/' + today_date + self.sync_mode

            # Launch a process to sync the status and data
            self.text_out(f'Syncing {station} station')
            p = Process(target = sync_station,
                        args = (self.stat_com[station], local_dir, remote_dir, self.q))
            p.start()

        # Begin the function to check on the process progress
        self.after(500, self.check_proc)

#========================================================================================
#==================================== Check Process =====================================
#========================================================================================

    def check_proc(self):

        # Check the queue for results
        if self.q.qsize() == len(self.station_info.keys()):

            # Make results dictionary
            sync_dict = {}

            # Pull the data for each station from the queue
            for n in range(len(self.station_info.keys())):
                name, status_time, status_msg, synced_fnames, err = self.q.get()

                # Put the results in the dict
                sync_dict[name] = synced_fnames

                # Update the status
                self.station_widjets[name]['status_time'].set(status_time[:-7])
                self.station_widjets[name]['status'].set(status_msg)

                # Report sync results
                if err[0] == True:
                    self.text_out(f'{name} station: connection failed')
                else:
                    self.text_out(f'{name} station: {len(synced_fnames)} files synced')

            # Pull the loop speed from the GUI
            try:
                loop_delay = int(self.loop_speed.get())
            except ValueError:
                loop_delay = 60

            # Update status indicator
            self.status.set('Standby')
            self.update()

            # If there are any new scans analysed then calculate the fluxes
            if self.sync_mode == '/so2/':

                for s in self.station_info.keys():

                    # Get new scan file names
                    new_fnames = sync_dict[s]

                    for fname in new_fnames:

                        # Build path to the latest SO2 data file
                        fpath = self.so2_fpaths[s] + fname

                        # Extract the time from the filename
                        scan_timestamp = dt.datetime.strptime(fname.split('_')[1],
                                                              '%H%M%S')
                        scan_time = hms_to_julian(scan_timestamp)

                        # Get the scan data
                        scan_angles, so2_cd = read_scan_so2(fpath)

                        # Get the wind speed
                        wind_dir, wind_speed = get_wind(self, scan_time)

                        # Calculate the new plume height
                        plume_height = calc_plume_height(self, s, scan_time)

                        # Calculate the flux from the scan
                        flux = calc_scan_flux(fpath, wind_speed, plume_height, 'arc')

                        # Add to the results arrays
                        self.times[s].append(scan_time)
                        self.fluxes[s].append(flux)
                        self.wtimes.append(scan_time)
                        self.heights.append(plume_height)
                        self.speeds.append(wind_speed)

                        # Update the results file
                        with open(self.flux_fpaths[s], 'a') as a:
                            a.write(str(scan_timestamp.time()) + ',' + str(wind_speed) + \
                                    ',' + str(plume_height) + ',' + str(flux) + '\n')

                    if len(new_fnames) != 0:

                        # Update the plots
                        y_lim = [1.1 * (max(self.fluxes[s])),
                                 1.1 * (max(self.heights)),
                                 1.1 * (max(self.speeds))]
                        data = np.array(([self.times[s],self.fluxes[s],'auto',[0,y_lim[0]]],
                                         [scan_angles,  so2_cd,        'auto', 'auto'     ]))
                        lines = [self.flux_lines[s], self.cd_line]
                        axes  = [self.ax0, self.ax1]
                        update_graph(lines, axes, self.canvas, data)

            self.after(loop_delay * 1000, self.begin_sync)

        else:
            # Not finished yet, wait another second
            self.after(1000, self.check_proc)

#========================================================================================
#==================================== GUI Operations ====================================
#========================================================================================

    # Report exceptions in a new window
    def report_callback_exception(self, *args):

        # Update status indicator
        self.status.set('ERROR')
        self.status_e.config(fg = 'red')
        self.update()

        # Report error
        err = traceback.format_exception(*args)
        tkMessageBox.showerror('Exception', err)

    # Close program on 'x' button
    def handler(self):

        # Turn on stopping flag
        self.stop_flag = True

        # Open exit dialouge
        text = 'Are you sure you want to quit?'
        message = tkMessageBox.askquestion('Exit', message = text, type = 'yesno')

        if message == 'yes':
            self.quit()

        if message == 'no':
            pass

    # Function to print text to the output box
    def text_out(self, text, add_t_stamp = True, add_line = False):

        # Check if timestamp is required
        if add_t_stamp == True:
            time_stamp = str(dt.datetime.now().time())[:-7]
            text = time_stamp + ' - ' + text

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

        logging.debug(text)

        # Force gui to update
        mygui.update(self)

# Run the App!
if __name__ == '__main__':
    mygui().mainloop()