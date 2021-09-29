"""Control communication between the home computer and the scanning station."""

import os
import pysftp
import logging
from datetime import datetime as dt
from paramiko.ssh_exception import SSHException

logging.getLogger("paramiko").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


class Station:
    """Create a Station object to communicate with the scaning station.

    Parameters
    ----------
    com_info : dict
        Contains the connection parameters:
            - host: IP address of the remote server
            - username: Username for the remote server
            - password: Password for the remote server
    name : str
        Name of the station. Default is "TEST"
    """

    def __init__(self, name, com_info, loc_info):
        """Initialise."""
        # Set the connection and location information for this station
        self.name = name
        self.com_info = com_info
        self.loc_info = loc_info

# =============================================================================
# Sync Folder
# =============================================================================

    def sync(self, local_dir, remote_dir):
        """Sync a local folder with a remote one.

        Parameters
        ----------
        local_dir : str
            File path to the local folder
        remote_dir : str
            File path to the remote folder

        Returns
        -------
        new_fnames : list
            List of synced file name strings
        """
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None

        # Create list to hold new filenames
        new_fnames = []

        # Open connection
        try:
            with pysftp.Connection(**self.com_info, cnopts=cnopts) as sftp:

                # Get the file names in the local directory
                local_files = os.listdir(local_dir)
                # local_files = glob.glob(local_dir + '*')
                # local_files = [fn.split('\\')[-1] for fn in local_files]

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
            logger.info(f'Error with station {self.name} communication',
                        exc_info=True)
            new_fnames = []
            err = [True, e]

        return new_fnames, err

# =============================================================================
#   Pull Status
# =============================================================================

    def pull_status(self):
        """Pull the station status.

        Parameters
        ----------
        com_info : dict
            Contains the connection parameters:
                - host: IP address of the remote server
                - username: Username for the remote server
                - password: Password for the remote server

        Returns
        -------
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
            with pysftp.Connection(**self.com_info, cnopts=cnopts) as sftp:

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
        """Pull the log file from the station for analysis.

        NOTE THIS ASSUMES THE DATE ON THE PI IS CORRECT TO PULL THE CORRECT LOG
        FILE

        Parameters
        ----------
        None

        Returns
        -------
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
            with pysftp.Connection(**self.com_info, cnopts=cnopts) as sftp:

                # Get the status file
                try:
                    sftp.get(f'/home/pi/open_so2/Results/{date}/{date}.log',
                             f'Results/{date}/{self.name}/{date}.log',
                             preserve_mtime=True)
                    fname = f'Results/{date}/{self.name}/{date}.log'
                except FileNotFoundError:
                    fname = None
                    logger.info('No log file found')
                except OSError:
                    fname = None

            # Successful read
            err = [False, '']

        # If connection fails, report
        except SSHException as e:
            fname = None
            err = [True, e]

        return fname, err
