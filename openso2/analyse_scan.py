"""Some text about the module."""

import logging
import numpy as np
import pandas as pd


# =============================================================================
# Read Scan
# =============================================================================

def read_scan(scan_fname):
    """Read in an OpenSO2 scan file.

    Paramters
    ---------
    scan_fname : string
        The file path to the scan file

    Returns
    -------
    error : bool
        An error code, 0 if all is OK, 1 if an error was produced
    info_block : array
        Spectra info: spec no, hours, minutes, seconds, motor position
    spec_block : array
        Array of the measured spectra for the scan block
    """
    try:
        # Read in the numpy file
        scan_data = np.load(scan_fname)

        # Create empty arrays to hold the spectra
        width, height = scan_data.shape
        info = np.zeros((width, 7))
        spec = np.zeros((width, height - 7))

        # Unpack the scan data
        for i, line in enumerate(scan_data):

            # Split the spectrum from the spectrum info
            info[i] = line[:7]
            spec[i] = line[7:]

        return 0, info, spec

    except Exception:
        return 1, 0, 0


# =============================================================================
# Fit Scan
# =============================================================================

def analyse_scan_spectra(scan_fname, analyser, wl_calib, save_fname=None):
    """Run iFit analysis of a scan.

    Parameters
    ----------
    scan_fname : str
        File path to the scan to analyse

    analyser : iFit Analyser
        The analyser to use to fit the scan spectra

    wl_calib : 1D numpy array
        The wavelength calibration of the spectrometer

    save_fname : None or str, optional
        If not None, then the scan results are saved to the path given

    Returns
    -------
    results : Pandas DataFrame
        Contains the scan information and fit results and errors
    """

    # Read in the scan
    err, info_block, spec_block = read_scan(scan_fname)

    if not err:

        # Correct for the dark spectrum
        corr_spec_block = np.subtract(spec_block[1:], spec_block[0])

        # Create columns for the dataframe
        cols = ['Number', 'Time', 'Angle']
        for par in analyser.params:
            cols += [par, f'{par}_err']
        cols += ['fit_quality', 'int_lo', 'int_hi', 'int_av']

        # Create a dataframe to hold the results
        fit_df = pd.DataFrame(index=np.arange(len(corr_spec_block)),
                              columns=cols)

        for i, spec in enumerate(corr_spec_block):
            try:
                fit = analyser.fit_spectrum(spectrum=[wl_calib, spec],
                                            update_params=True,
                                            resid_limit=10,
                                            int_limit=[0, 60000],
                                            interp_method='linear')

                # Get the spectrum time and angle
                hours = info_block[i][1]
                minutes = info_block[i][1]
                seconds = info_block[i][1]
                scan_time = hours + minutes/60 + seconds/3600
                scan_angle = info_block[i][5]

                # Add to the results dataframe
                row = [i, scan_time, scan_angle]
                for par in fit.params.values():
                    row += [par.fit_val, par.fit_err]
                row += [fit.nerr, fit.int_lo, fit.int_hi,
                        fit.int_av]
                fit_df.loc[i] = row

            except ValueError as msg:
                logging.warning(f'Error in analysis, skipping\n{msg}')

        if save_fname is not None:

            # Either save as a .csv or a .npy file
            file_end = save_fname.split('.')[-1]
            if file_end == 'csv':
                fit_df.to_csv(save_fname)
            elif file_end == 'npy':
                np.save(save_fname, fit_df.to_numpy())
            else:
                logging.warning(f'Error in save filename {save_fname}')

        return fit_df

    else:
        logging.warning(f'Error reading file {scan_fname}')


# =============================================================================
# Update Integration Time
# =============================================================================

def update_int_time(scan_fname, integration_time, settings):
    """ Update spectrometer integration time.

    Function to calculate a new integration time based on the intensity of the
    previous scan

    Parameters
    ----------
    common : dict
        Common dictionary of parameters for the program

    settings : dict
        Dictionary of station settings

    Returns
    -------
    new_int_time : int
        New integration time for the next scan
    """

    # Load the previous scan
    err, x, info, spec = read_scan(scan_fname)

    # Find the maximum intensity
    max_int = np.max(spec)

    # Scale the intensity to the target
    scale = settings['target_int'] / max_int

    # Scale the integration time by this factor
    int_time = integration_time * scale

    # Find the nearest integration time
    int_times = np.arange(settings['min_int_time'],
                          settings['max_int_time'] + settings['int_time_step'],
                          settings['int_time_step'])

    # Find the nearest value
    diff = ((int_times - int_time)**2)**0.5
    idx = np.where(diff == min(diff))[0][0]
    new_int_time = int(int_times[idx])

    # Log change
    logging.info(f'Updated integration time to {new_int_time} ms')

    # Return the updated integration time
    return new_int_time
