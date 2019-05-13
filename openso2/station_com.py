# -*- coding: utf-8 -*-
"""
Created on Thu Jan 24 15:13:52 2019

@author: mqbpwbe2
"""

import os
import pysftp
import glob
import logging

class Station:

    '''
    Creates a Station object which is used by the home station to communicate with the
    scaning station

    INPUTS
    ------
    cinfo, dict
        Contains the connection parameters:
            - host: IP address of the remote server
            - username: Username for the remote server
            - password: Password for the remote server

    name, str
        Name of the station. Default is "TEST"

    METHODS
    -------
    sync(local_path, remote_path)
        Function to sync a local folder with a remote one. Returns (n_files, fnames)

    get_status
        method to retrieve the contents of the station status . Returns a dictionary of
        the station settings.
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

        INPUTS
        ------
        local_dir, str
            File path to the local folder

        remote_dir, str
            File path to the remote folder

        OUTPUTS
        -------
        n_files, int
            The number of files moved

        new_fnames, list
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

                # Create file counter
                n_files = 0

                # Iterate over them and copy any that are missing in the host directory
                for fname in remote_files:

                    # Check if in the local directory
                    if fname not in local_files:

                        # Copy the file across
                        sftp.get(remote_dir + fname, local_dir + fname)

                        # Add to the counter and file list
                        n_files += 1
                        new_fnames.append(fname)
        except Exception as e:
            print(f'Error syncing: {e}')
            logging.info('Error with station communication', exc_info = True)
            n_files, new_fnames = [], []

        return n_files, new_fnames

#========================================================================================
#===================================== Pull Status ======================================
#========================================================================================

    def pull_status(self):

        '''
        Function to pull the station status

        INPUTS
        ------
        cinfo, dict
            Contains the connection parameters:
                - host: IP address of the remote server
                - username: Username for the remote server
                - password: Password for the remote server

        OUTPUTS
        -------
        status, dict
            Dictionary containing the status of the station
        '''

        if not os.path.exists('Station'):
            os.makedirs('Station')

        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        # Make sure the log folder exists
        if not os.path.exists('Station'):
            os.makedirs('Station')

        try:

            # Open connection
            with pysftp.Connection(**self.cinfo, cnopts=cnopts) as sftp:

                # Get the status file
                sftp.get('/home/pi/open_so2/Station/status.txt',
                         f'Station/{self.name}_status.txt')


            with open(f'Station/{self.name}_status.txt', 'r') as r:

                time, status = r.readline().strip().split(' - ')

        except Exception as e:
            time, status = '', 'N/C'

        return time, status








