"""Some text about the module."""

import os
import logging
import numpy as np
import xarray as xr
from datetime import datetime


logger = logging.getLogger(__name__)


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
        Spectra info: spec no, hours, minutes, seconds, motor position, angle,
        coadds and integration time (ms)
    spec_block : array
        Array of the measured spectra for the scan block
    """
    try:
        # Read in the numpy file
        scan_data = np.load(scan_fname)

        # Create empty arrays to hold the spectra
        width, height = scan_data.shape
        info = np.zeros((width, 8))
        spec = np.zeros((width, height - 8))

        # Unpack the scan data
        for i, line in enumerate(scan_data):

            # Split the spectrum from the spectrum info
            info[i] = line[:8]
            spec[i] = line[8:]

        return 0, info, spec

    except Exception:
        return 1, 0, 0


# =============================================================================
# Analyse Scan
# =============================================================================

def analyse_scan(scan_fname, analyser, save_fname=None):
    """Run iFit analysis of a scan.

    Parameters
    ----------
    scan_fname : str
        File path to the scan to analyse

    analyser : iFit Analyser
        The analyser to use to fit the scan spectra

    save_fname : None or str, optional
        If not None, then the scan results are saved to the path given

    Returns
    -------
    results : Pandas DataFrame
        Contains the scan information and fit results and errors
    """
    # Read in the scan file
    scan_da = xr.open_dataarray(scan_fname)

    # Pull out the wavelength information and number of spectra
    wl_calib = scan_da.coords['wavelength'].to_numpy()
    nspec = scan_da.attrs['specs_per_scan']

    # Pull out the spectra and correct for the dark spectrum
    raw_spectra = scan_da.to_numpy()
    spectra = raw_spectra[1:] - raw_spectra[0]

    # Set up the output data arrays
    output_data = {
        'fit_quality': np.zeros(nspec, dtype=int),
        'int_lo': np.zeros(nspec, dtype=int),
        'int_av': np.zeros(nspec, dtype=int),
        'int_hi': np.zeros(nspec, dtype=int),
        'max_resid': np.zeros(nspec)
    }
    for par in analyser.params:
        output_data[par] = np.zeros(nspec)
        output_data[f'{par}_err'] = np.zeros(nspec)

    for i, spec in enumerate(spectra):

        try:
            fit = analyser.fit_spectrum(spectrum=[wl_calib, spec],
                                        update_params=True,
                                        resid_limit=20,
                                        int_limit=[0, 60000],
                                        interp_method='linear')

            output_data['fit_quality'][i] = fit.nerr
            output_data['int_lo'][i] = fit.int_lo
            output_data['int_av'][i] = fit.int_av
            output_data['int_hi'][i] = fit.int_hi
            output_data['max_resid'][i] = np.nanmax(fit.resid)

            for par in fit.params.values():
                output_data[par.name][i] = par.fit_val
                output_data[par.name + '_err'][i] = par.fit_err

        except ValueError as msg:
            logger.warning(f'Error in analysis, skipping\n{msg}')

        head, tail = os.path.split(scan_fname)

    logger.info(f'Analysis finished for scan {tail}')

    # Form output dataarrays
    data_vars = {}
    coords = {'angle': scan_da.coords['angle']}
    for key, value in output_data.items():
        data_vars[key] = xr.DataSet(
            data=value,
            coords=coords
        )

    # Form output dataset
    attrs = {**scan_da.attrs, **{'analysis_time': datetime.now()}}
    output_ds = xr.Dataset(
        data_vars=data_vars,
        coords=coords,
        attrs=attrs
    )

    # Save the output file if desired
    if save_fname is not None:
        output_ds.to_netcdf(save_fname)

    return output_ds


# =============================================================================
# Update Integration Time
# =============================================================================

def update_int_time(scan_fname, integration_time, settings):
    """Update spectrometer integration time.

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
    spec = read_scan(scan_fname)[-1]

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

    # Return the updated integration time
    return new_int_time
