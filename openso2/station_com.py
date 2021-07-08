# -*- coding: utf-8 -*-
"""
Module to control communication between the home computer and the scanning
stations.
"""

import os
import pysftp
import glob
import logging
from datetime import datetime as dt
from paramiko.ssh_exception import SSHException

logging.getLogger("paramiko").setLevel(logging.WARNING)


class Station:

    """
    Creates a Station object which is used by the home station to communicate
    with the scaning station

    **Parameters:**

    cinfo : dict
        Contains the connection parameters:
            - host: IP address of the remote server
            - username: Username for the remote server
            - password: Password for the remote server

    name : str
        Name of the station. Default is "TEST"
    """

    def __init__(self, cinfo, name='TEST'):

        # Set the connection information for this station object
        self.cinfo = cinfo
        self.name = name

# =============================================================================
# Sync Folder
# =============================================================================

    def sync(self, local_dir, remote_dir):
        """
        Function to sync a local folder with a remote one.

        **Parameters:**

        local_dir : str
            File path to the local folder

        remote_dir : str
            File path to the remote folder

        **Returns:**

        new_fnames : list
            List of synced file name strings
        """

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        # Create list to hold new filenames
        new_fnames = []

        # Open connection
        try:
            with pysftp.Connection(**self.cinfo, cnopts=cnopts) as sftp:

                # Get the file names in the local directory
                local_files = glob.glob(local_dir + '*')
                local_files = [fn.split('\\')[-1] for fn in local_files]

                # Get the file names in the remote directory
                remote_files = sftp.listdir(remote_dir)

                # Iterate through and copy any that are missing in the host
                #  directory
                for fname in remote_files:

                    # Check if in the local directory
                    if fname not in local_files:

                        # Copy the file across
                        try:
                            sftp.get(remote_dir + fname, local_dir + fname,
                                     preserve_mtime=True)
                        except OSError:
                            pass

                        # Add file list
                        new_fnames.append(fname)

            # Set error message as false
            err = [False, '']

        # Handle the error is the connection is refused
        except SSHException as e:
            print(f'Error syncing: {e}')
            logging.info(f'Error with station {self.name} communication',
                         exc_info=True)
            new_fnames = []
            err = [True, e]

        return new_fnames, err

# =============================================================================
#   Pull Status
# =============================================================================

    def pull_status(self):
        """
        Function to pull the station status

        **Parameters:**

        cinfo : dict
            Contains the connection parameters:
                - host: IP address of the remote server
                - username: Username for the remote server
                - password: Password for the remote server

        **Returns:**

        status : dict
            Dictionary containing the status of the station
        """

        # Make sure the Station folder exists
        if not os.path.exists('Station'):
            os.makedirs('Station')

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        try:

            # Open connection
            with pysftp.Connection(**self.cinfo, cnopts=cnopts) as sftp:

                # Get the status file
                sftp.get('/home/pi/open_so2/Station/status.txt',
                         f'Station/{self.name}_status.txt',
                         preserve_mtime=True)

            # Read the status file
            with open(f'Station/{self.name}_status.txt', 'r') as r:
                time, status = r.readline().strip().split(' - ')

            # Successful read
            err = [False, '']

        # If connection fails, report
        except SSHException as e:
            time, status = '-', 'N/C'
            err = [True, e]

        return time, status, err

# =============================================================================
#   Pull Log
# =============================================================================

    def pull_log(self):
        """
        Function to pull the log file from the station for analysis

        NOTE THIS ASSUMES THE DATE ON THE PI IS CORRECT TO PULL THE CORRECT LOG
        FILE

        **Parameters:**

        None

        **Returns:**

        last_log : str
            The last log entry in the log file

        err : tuple
            Consists of the error flag (True is an error occured) and the error
            message
        """

        # Get the date to find the correct log file
        date = dt.now().date()

        # Make sure the Station folder exists
        if not os.path.exists(f'Results/{date}/'):
            os.makedirs(f'Results/{date}/')

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        try:

            # Open connection
            with pysftp.Connection(**self.cinfo, cnopts=cnopts) as sftp:

                # Get the status file
                try:
                    sftp.get(f'/home/pi/open_so2/Results/{date}/{date}.log',
                             f'Results/{date}/{self.name}/{date}.log',
                             preserve_mtime=True)
                    fname = f'Results/{date}/{self.name}/{date}.log'
                except FileNotFoundError:
                    fname = None
                    logging.info('No log file found')
                except OSError:
                    fname = None

            # Successful read
            err = [False, '']

        # If connection fails, report
        except SSHException as e:
            fname = None
            err = [True, e]

        return fname, err


# =============================================================================
# Sync Station
# =============================================================================

def sync_station(station, local_dir, remote_dir, queue):
    """
    Function to sync the status and files of a station

    **Parameters:**

    station : Station object
        The station object which will be synced

    local_dir : str
        File path to the local directory to be synced

    remote_dir : str
        File path to the remote directory to be synced

    queue : multiprocessing Queue
        The queue in which to put the outputs

    **Returns:**

    name : str
        Name of the station so it can be identified in the queue

    status_time : str
        The timestamp of the last status update

    status_msg : str
        The status of the station

    synced_fnames : list
        Contains the synced data file names
    """

    # Check station name
    name = station.name

    # Get the station status
    status_time, status_msg, stat_err = station.pull_status()

    # If the status is error, pull the log file
    if status_msg == 'Error':
        station.pull_log

    # If the connection was succesful then sync files
    if not stat_err[0]:
        synced_fnames, sync_err = station.sync(local_dir, remote_dir)
        err = [False, '']
    else:
        synced_fnames = []
        err = [True, 'Connection not established']

    # Place the results as a list in the queue
    queue.put([name, status_time, status_msg, synced_fnames, err])


# =============================================================================
# Get Station Status
# =============================================================================

def get_station_status(gui, station):
    """
    Function to retrieve the status of a station.

    **Parameters:**

    gui : tk.Tk GUI
        GUI object containing the program interface

    station : string
        Name of the station

    **Returns:**

    None
    """

    # Try to retrieve the station status
    time, status, err = gui.stat_com[station].pull_status()

    gui.station_widjets[station]['status_time'].set(time[:-7])
    gui.station_widjets[station]['status'].set(status)


# =============================================================================
# Sync Station
# =============================================================================

def sync_psudostation(station, local_dir, remote_dir, queue):

    from shutil import copy2

    remote_dir = '../psudoscanner/Results/so2/'

    # Check station name
    name = station.name

    status_time = '12:00:00'
    status_msg = 'testing'
    err = [False, '']

    local_files = glob.glob(local_dir + '*')
    remote_files = glob.glob(remote_dir + '*')

    local_files.sort()
    remote_files.sort()

    local_files = [fn.split('\\')[-1] for fn in local_files]
    remote_files = [fn.split('\\')[-1] for fn in remote_files]

    synced_fnames = []

    # Iterate through and copy any that are missing in the host
    #  directory
    for fname in remote_files:

        # Check if in the local directory
        if fname not in local_files:

            # Copy the file across
            copy2(remote_dir + fname, local_dir + fname)

            # Add file list
            synced_fnames.append(fname)

    # Place the results as a list in the queue
    queue.put([name, status_time, status_msg, synced_fnames, err])
