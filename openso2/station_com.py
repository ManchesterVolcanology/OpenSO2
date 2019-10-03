# -*- coding: utf-8 -*-
"""
Created on Thu Jan 24 15:13:52 2019

@author: mqbpwbe2
"""

import os
import pysftp
import glob
import logging
from datetime import datetime as dt
from paramiko.ssh_exception import SSHException

class Station:

    '''
    Creates a Station object which is used by the home station to communicate with the
    scaning station

    Paramaters:

    cinfo : dict
        Contains the connection parameters:
            - host: IP address of the remote server
            - username: Username for the remote server
            - password: Password for the remote server

    name : str
        Name of the station. Default is "TEST"
    '''

    def __init__(self, cinfo, name = 'TEST'):

        # Set the connection information for this station object
        self.cinfo = cinfo
        self.name = name


#========================================================================================
#===================================== Sync Folder ======================================
#========================================================================================

    def sync(self, local_dir, remote_dir):

        '''
        Function to sync a local folder with a remote one.

        Parameters:

        local_dir : str
            File path to the local folder

        remote_dir : str
            File path to the remote folder

        Returns:
        
        new_fnames : list
            List of synced file name strings
        '''

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

                # Iterate over them and copy any that are missing in the host directory
                for fname in remote_files:

                    # Check if in the local directory
                    if fname not in local_files:

                        # Copy the file across
                        sftp.get(remote_dir + fname, local_dir + fname)

                        # Add file list
                        new_fnames.append(fname)

            # Set error message as false
            err = [False, '']

        # Handle the error is the connection is refused
        except SSHException as e:
            print(f'Error syncing: {e}')
            logging.info('Error with station communication', exc_info = True)
            new_fnames = []
            err = [True, e]

        return new_fnames, err

#========================================================================================
#===================================== Pull Status ======================================
#========================================================================================

    def pull_status(self):

        '''
        Function to pull the station status

        Parameters:
        
        cinfo : dict
            Contains the connection parameters:
                - host: IP address of the remote server
                - username: Username for the remote server
                - password: Password for the remote server

        Returns:
        
        status : dict
            Dictionary containing the status of the station
        '''

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
                         f'Station/{self.name}_status.txt')

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

#========================================================================================
#======================================= Pull Log =======================================
#========================================================================================

    def pull_log(self):

        '''
        Function to pull the log file from the station for analysis

        NOTE THIS ASSUMES THE DATE ON THE PI IS CORRECT TO PULL THE CORRECT LOG FILE

        Parameters:
        
        None

        Returns:
        
        last_log : str
            The last log entry in the log file

        err : tuple
            Consists of the error flag (True is an error occured) and the error message
        '''

        # Make sure the Station folder exists
        if not os.path.exists('Station'):
            os.makedirs('Station')

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        try:

            # Open connection
            with pysftp.Connection(**self.cinfo, cnopts=cnopts) as sftp:

                # Get the status file
                sftp.get(f'/home/pi/open_so2/log/{dt.now().date()}.log',
                         f'Station/{self.name}_log.txt')

            # Successful read
            err = [False, '']

        # If connection fails, report
        except SSHException as e:
            err = [True, e]

        return err


#========================================================================================
#===================================== Sync Station =====================================
#========================================================================================

def sync_station(station, local_dir, remote_dir, queue):

    '''
    Function to sync the status and files of a station

    Parameters:
        
    station : Station object
        The station object which will be synced

    local_dir : str
        File path to the local directory to be synced

    remote_dir : str
        File path to the remote directory to be synced

    queue : multiprocessing Queue
        The queue in which to put the outputs

    Returns:
        
    name : str
        Name of the station so it can be identified in the queue

    status_time : str
        The timestamp of the last status update

    status_msg : str
        The status of the station

    synced_fnames : list
        Contains the synced data file names
    '''

    # Check station name
    name = station.name

    # Get the station status
    status_time, status_msg, stat_err = station.pull_status()

    # If the status is error, pull the log file
    if status_msg == 'Error':
        station.pull_log

    # If the connection was succesful then sync files
    if stat_err[0] == False:
        synced_fnames, sync_err = station.sync(local_dir, remote_dir)
        err = [False, '']
    else:
        synced_fnames = []
        err = [True, 'Connection not established']

    # Place the results as a list in the queue
    queue.put([name, status_time, status_msg, synced_fnames, err])




