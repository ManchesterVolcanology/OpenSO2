"""Some text about the module."""

import os
import logging
import numpy as np
import xarray as xr
from datetime import datetime


logger = logging.getLogger(__name__)


# =============================================================================
# Analyse Scan
# =============================================================================

def analyse_scan(scan_data, analyser, save_fname=None):
    """Run iFit analysis of a scan.

    Parameters
    ----------
    scan_data : xarray DataArray
        Holds the scan wavelength, intensity and meta data

    analyser : iFit Analyser
        The analyser to use to fit the scan spectra

    save_fname : None or str, optional
        If not None, then the scan results are saved to the path given

    Returns
    -------
    results : Pandas DataFrame
        Contains the scan information and fit results and errors
    """
    # Pull out the wavelength information and number of spectra
    wl_calib = scan_data.coords['wavelength'].to_numpy()
    nspec = scan_data.attrs['specs_per_scan']

    # Pull out the spectra and correct for the dark spectrum
    raw_spectra = scan_data.data()
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
            fit = analyser.fit_spectrum(
                spectrum=[wl_calib, spec],
                update_params=True,
                resid_limit=20,
                int_limit=[0, 60000],
                interp_method='linear'
            )

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

        _, tail = os.path.split(scan_data.filename)

    logger.info(f'Analysis finished for scan {tail}')

    # Form output dataarrays
    data_vars = {}
    coords = {'angle': scan_data.coords['angle'][1:]}
    for key, value in output_data.items():
        data_vars[key] = xr.DataArray(
            data=value,
            coords=coords
        )

    # Form output dataset
    attrs = {
        **scan_data.attrs,
        **{'analysis_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}
    }
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

def update_int_time(scan_data, settings):
    """Update spectrometer integration time.

    Function to calculate a new integration time based on the intensity of the
    previous scan

    Parameters
    ----------
    scan_data : xarray DataArray
        Holds the scan wavelength, intensity and meta data

    settings : dict
        Dictionary of station settings

    Returns
    -------
    new_int_time : int
        New integration time for the next scan
    """
    # Load the previous scan
    spectra = scan_data.data

    # Find the maximum intensity
    max_int = np.max(spectra)

    # Scale the intensity to the target
    scale = settings['target_int'] / max_int

    # Scale the integration time by this factor
    int_time = scan_data.integration_time * scale

    # Find the nearest integration time
    int_times = np.arange(
        settings['min_int_time'],
        settings['max_int_time'] + settings['int_time_step'],
        settings['int_time_step']
    )

    # Find the nearest value
    diff = ((int_times - int_time)**2)**0.5
    idx = np.where(diff == min(diff))[0][0]
    new_int_time = int(int_times[idx])

    # Return the updated integration time
    return new_int_time
