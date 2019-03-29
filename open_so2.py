# -*- coding: utf-8 -*-
"""
Created on Fri Jan 25 13:02:09 2019

@author: mqbpwbe2
"""

import os
from pathlib import Path
import numpy as np
from tkinter import ttk
import tkinter as tk
import traceback
import datetime as dt
import tkinter.scrolledtext as tkst
import tkinter.messagebox as tkMessageBox
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from openso2.program_setup import get_station_info, update_resfp
from openso2.station_com import Station
from openso2.analyse_scan import calc_scan_flux, calc_plume_height, get_wind_speed
from openso2.julian_time import hms_to_julian
from openso2.gui_funcs import update_graph, make_input

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
            self.stat_com[station] = Station(self.station_info[station])

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
        nb.grid(column=0, padx=10, pady=10, sticky = 'NW')

        # Frame for status and control
        stat_frame = tk.LabelFrame(overview_page, text = 'Control', font = LARG_FONT)
        stat_frame.grid(row=0, column=0, padx=10, pady=10, sticky="NW")

        mygui.columnconfigure(index = 1, weight = 1, self = self)
        mygui.rowconfigure(index = 5, weight = 1, self = self)

        # Create frame to hold graphs
        graph_frame = ttk.Frame(overview_page, relief = 'groove')
        graph_frame.grid(row=0, column=1, padx=10, pady=10, rowspan=10, sticky="NW")
        graph_frame.columnconfigure(index = 0, weight = 1)
        graph_frame.rowconfigure(index = 0, weight = 1)

#========================================================================================
#=============================== Add widjets to overview ================================
#========================================================================================

#===================================== Status Frame =====================================

        # Create status indicator
        self.status = tk.StringVar(stat_frame, value = 'Standby')
        self.status_e = tk.Label(stat_frame, textvariable = self.status, fg='red')
        self.status_e.grid(row=0, column=0, padx=5, pady=5, sticky="EW")
        self.status_col = 'red'

        # Ceate input for the results filepath
        self.res_fpath = tk.StringVar(value = 'Results/')
        res_fpath_ent = tk.Entry(stat_frame, font = NORM_FONT, width = 30,
                                 text = self.res_fpath)
        res_fpath_ent.grid(row = 1, column = 0, padx = 5, pady = 5, sticky = 'W',
                           columnspan = 2)
        res_fpath_b = ttk.Button(stat_frame, text = "Browse",
                                 command = lambda: update_resfp(self))
        res_fpath_b.grid(row = 1, column = 2, padx = 5, pady = 5, sticky = 'W')

        # Create control for the control loop speed
        self.loop_speed = tk.IntVar(value = 30)
        make_input(frame = stat_frame,
                   text = 'Sync Delay (s):',
                   var = self.loop_speed,
                   input_type = 'Spinbox',
                   row = 2, column = 0,
                   vals = (1, 600),
                   width = 10)

        # Create frame to hold text output
        text_frame = ttk.Frame(stat_frame)
        text_frame.grid(row=3, column=0, padx=10, pady=10, columnspan=5, sticky="NW")

        # Build text box
        self.text_box = tkst.ScrolledText(text_frame, width = 42, height = 8)
        self.text_box.grid(row = 1, column = 0, padx = 5, pady = 5, sticky = 'W',
                           columnspan = 2)
        self.text_box.insert('1.0', 'Welcome to Open SO2! Written by Ben Esse\n\n')

#===================================== Graph Frame ======================================

        # Create figure to hold the graphs
        plt.rcParams.update({'font.size': 8})
        self.fig = plt.figure(figsize = (6,6))
        gs = gridspec.GridSpec(3, 1, height_ratios = (2,1,1))

        # Create plot axes
        self.ax0 = self.fig.add_subplot(gs[0])
        self.ax1 = self.fig.add_subplot(gs[1])
        self.ax2 = self.fig.add_subplot(gs[2])

        # Set axis labels
        self.ax0.set_xlabel('Time (decimal hours)',    fontsize = 10)
        self.ax0.set_ylabel('SO$_2$ Flux (t/day)',     fontsize = 10)
        self.ax1.set_xlabel('Time (decimal hours)',    fontsize = 10)
        self.ax1.set_ylabel('Plume Height (m a.s.l.)', fontsize = 10)
        self.ax2.set_xlabel('Time (decimal hours)',    fontsize = 10)
        self.ax2.set_ylabel('Wind Speed (m/s)',        fontsize = 10)

        # Create lines for each station flux plot
        self.flux_lines = {}
        for station in self.station_info.keys():
            self.flux_lines[station], = self.ax0.plot(0, 0, 'o-', label = station)

        self.height_line, = self.ax1.plot(0, 0, 'o-')
        self.wind_speed_line = self.ax2.plot(0, 0, 'o-')

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

#========================================================================================
#========================== Add widjets to the station pages ============================
#========================================================================================

        # Create dictionaries to hold the corresponding widgets for each station
        self.station_widjets = {}

        for station in self.station_info.keys():

            # Ceate sub dictionary to hold the widjets for this staiton
            station_w = {}

            # Create a frame to hold the station status
            s_frame = tk.LabelFrame(station_page[station], text = 'Station Status',
                                    font = LARG_FONT)
            s_frame.grid(row = 0, column = 0)

            # Create status indicator
            station_w['status'] = tk.StringVar(value = 'Idle')
            make_input(frame = s_frame,
                       text = 'Status:',
                       var = station_w['status'],
                       input_type = 'Label',
                       row = 0, column = 0)

            # Create temperature indicator
            station_w['temp'] = tk.DoubleVar(value = 0)
            make_input(frame = s_frame,
                       text = 'Temperature:',
                       var = station_w['temp'],
                       input_type = 'Label',
                       row = 1, column = 0)

            # Create a scanner position indicator
            station_w['pos'] = tk.IntVar(value = 0)
            make_input(frame = s_frame,
                       text = 'Scanner Position:',
                       var = station_w['pos'],
                       input_type = 'Label',
                       row = 2, column = 0)

            # Add the station widjets to the master dictionary
            self.station_widjets[station] = station_w

#========================================================================================
#=============================== Start the control loop =================================
#========================================================================================

        # Begin the control loop
        self.after(1000, self.control_loop)

#========================================================================================
#===================================== Control Loop =====================================
#========================================================================================

    def control_loop(self):

        # Check the date and time
        timestamp = dt.datetime.now()
        today_date = str(timestamp.date())

        # Create dictinary to hold the file paths
        m_fpath     = {}
        so2_fpaths  = {}
        spec_fpaths = {}
        flux_fpaths = {}

        # Check that the required results folders and files exist
        for station in self.station_info.keys():

            # Build master filepath and add to dictionaries
            m_fpath[station] = self.res_fpath.get() + today_date + '/' + station + '/'
            so2_fpaths[station]  = m_fpath[station] + '/so2/'
            spec_fpaths[station] = m_fpath[station] + '/spectra/'
            flux_fpaths[station] = m_fpath[station] + today_date + '_' + station + \
                                   '_fluxes.csv'

            # Create the folder
            os.makedirs(so2_fpaths[station],  exist_ok = True)
            os.makedirs(spec_fpaths[station], exist_ok = True)

            # Create the results file if it doesn't exist
            if not Path(flux_fpaths[station]).is_file():

                # Create the file and write the header row
                with open(flux_fpaths[station], 'w') as w:
                    w.write('Time,Plume Height (m),Wind Speed (ms-1),Flux (t/day)\n')

        # Pull station data and update
        ##### Not yet implemented #####

        # If the stations are operational sync the so2 files. If sleeping sync spectra
        jul_time = hms_to_julian(timestamp)
        if jul_time > 6 and jul_time < 16:
            sync_mode = '/so2/'
        else:
            sync_mode = '/spectra/'

        # Sync the home folders with remotes
        self.status.set('Syncing')
        self.update()
        new_fnames = {}
        for station in self.station_info.keys():

            # Generate local and remote file paths to sync
            local_fpath = m_fpath[station] + sync_mode
            remote_fpath = '/home/pi/open_so2/Results/' + today_date + sync_mode

            # Sync the files
            n_files, new_fnames[station] = self.stat_com[station].sync(local_fpath,
                                                                       remote_fpath)

        # Update status indicator
        self.status.set('Standby')
        self.update()

        # If there are any new scans analysed then calculate the fluxes
        if sync_mode == '/so2/':

            for s in self.station_info.keys():

                for fname in new_fnames[s]:

                    # Build path to the latest SO2 data file
                    fpath = self.res_fpath.get() + today_date + '/' + s + '/SO2/' + fname

                    # Extract the time from the filename
                    scan_timestamp = dt.datetime.strptime(fname.split('_')[1], '%H%M%S')
                    scan_time = hms_to_julian(scan_timestamp)

                    # Get the wind speed
                    wind_speed = get_wind_speed()

                    # Calculate the new plume height
                    plume_height = calc_plume_height(s, fname)

                    # Calculate the flux from the scan
                    flux = calc_scan_flux(fpath, wind_speed, plume_height, 'arc')

                    # Add to the results arrays
                    self.times[s].append(scan_time)
                    self.fluxes[s].append(flux)
                    self.wtimes.append(scan_time)
                    self.heights.append(plume_height)
                    self.speeds.append(wind_speed)

                    # Update the results file
                    with open(flux_fpaths[s], 'a') as a:
                        a.write(str(scan_timestamp.time()) + ',' + str(wind_speed) + \
                                ',' + str(plume_height) + ',' + str(flux) + '\n')

                if len(new_fnames[s]) != 0:

                    # Update the plots
                    y_lim = [1.1 * (max(self.fluxes[s])),
                             1.1 * (max(self.heights)),
                             1.1 * (max(self.speeds))]
                    data = np.array(([self.times[s],self.fluxes[s],'auto',[0,y_lim[0]]],
                                     [self.wtimes,self.heights,'auto',[0,y_lim[1]]],
                                     [self.wtimes,self.speeds,'auto',[0,y_lim[2]]]))
                    lines = [self.flux_lines[s], self.height_line, self.wind_speed_line]
                    axes  = [self.ax0, self.ax1, self.ax2]
                    update_graph(lines, axes, self.canvas, data)

        # Update the status colour
        if self.status_col == 'red':
            self.status_e.config(fg = 'green')
            self.status_col = 'green'
        else:
            self.status_e.config(fg = 'red')
            self.status_col = 'red'

        # Pull the loop speed from the GUI
        try:
            loop_delay = int(self.loop_speed.get())
        except ValueError:
            loop_delay = 60

        self.after(loop_delay * 1000, self.control_loop)

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

# Run the App!
if __name__ == '__main__':
    mygui().mainloop()