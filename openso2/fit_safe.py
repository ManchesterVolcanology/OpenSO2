import numpy as np
import logging
from scipy.interpolate import griddata
from scipy.optimize import curve_fit

from openso2.make_ils import make_ils

#========================================================================================
#===================================== make_poly ========================================
#========================================================================================

def make_poly(grid, coefs):

    '''
    Function to construct a polynolial given a list of coefficients

    INPUTS
    ------
    grid, array
        X grid over which to calculate the polynomial

    coefs, list
        Polynomial coefficents (of acesnding rank)

    OUTPUTS
    -------
    poly, array
        Resulting polynomial, calculated as poly = p0 + p1*grid + p2*grid^2 + ...
    '''

    poly = np.zeros(len(grid))

    for i, p in enumerate(coefs):

        poly = np.add(poly, np.multiply(np.power(grid, i), p))

    return poly

#========================================================================================
#======================================== fit_spec ======================================
#========================================================================================

def fit_spec(common, spectrum, grid):

    '''
    Function to fit measured spectrum using a full forward model including a solar
    spectrum background polynomial, ring effect, wavelength shift and stretch, and gas
    amounts for so2, no2, o3

    INPUTS:
    -------
    common: dictionary
        Common dictionary of parameters and variables passed from the main program
        to subroutines

    spectrum: 2D array
        Intensity data from the measured spectrum

    grid: 1D array
        Measurement wavelength grid over which the fit occurs

    q: queue (optional)
        Queue to which to add the output if threaded (default = None)

    OUTPUTS:
    --------
    fit_dict: dictionary
        Dictionary of optimised parameters

    err_dict: dictionary
        Dictionary of error in the optimised parameters

    y: array
        Measured spectrum, corrected for dark, bias and flat response, in the fitting
        window

    fit: array
        Fitted spectrum

    fitted_flag: bool
        Flag showing if the fit was successful or not

    '''

    # Cretae a copy of common for forward model to access
    global com
    com = common

    # Unpack spectrum
    x, y = spectrum

    # Remove the dark spectrum
    y = np.subtract(y, common['dark'])

    # Extract the fit region
    y = y[common['idx']]

    # Divide by flat spectrum
    y = np.divide(y, common['flat'])

    # Appempt to fit!
    try:
        # Fit
        popt, pcov = curve_fit(ifit_fwd_model, grid, y, p0 = common['params'])

        # Get fit errors
        perr = np.sqrt(np.diag(pcov))

        # Fit successful
        fitted_flag = True

    # If fit fails, report and carry on
    except Exception as e:

        # Fill returned arrays with zeros
        popt = np.zeros(len(common['params']))
        perr = np.zeros(len(common['params']))

        # Turn off fitted flag
        fitted_flag = False

        # Log
        logging.error('Excepion Occurred', exc_info=True)

    # Return results, either to a queue if threaded, or as an array if not
    return popt, perr, fitted_flag


#========================================================================================
#======================================== ifit_fwd ======================================
#========================================================================================

def ifit_fwd_model(grid, p0, p1, p2, shift, stretch, ring_amt, so2_amt, no2_amt, o3_amt):

    '''
    iFit forward model to fit measured UV sky spectra

    INPUTS:
    -------
    grid, array
        Measurement wavelength grid

    *args, list
        Forward model state vector

    OUTPUTS:
    --------
    fit, array
        Fitted spectrum interpolated onto the spectrometer wavelength grid
    '''

    # Construct background polynomial
    bg_poly = make_poly(com['model_grid'], [p0, p1, p2])

    # Build gas transmittance spectra
    so2_T = np.exp(-(np.multiply(com['so2_xsec'], so2_amt)))
    no2_T = np.exp(-(np.multiply(com['no2_xsec'], no2_amt)))
    o3_T  = np.exp(-(np.multiply(com['o3_xsec'],  o3_amt)))

    # Background sky spectrum
    sol_spec = np.multiply(bg_poly, com['sol'])

    # Ring effect
    ring_T = np.exp(np.multiply(com['ring'], ring_amt))
    sol_T = np.multiply(sol_spec, ring_T)

    # Background sky spectrum
    bg_spec = np.multiply(np.multiply(sol_T, no2_T), o3_T)

    # Include gasses and areosol
    raw_F = np.multiply(bg_spec, so2_T)

    # Convolve with the ILS
    F_conv = np.convolve(raw_F, make_ils(0.6), 'same')

    # Apply shift and stretch to the model_grid
    shift_model_grid = np.add(com['model_grid'], shift)
    line = np.linspace(0, 1, num = len(shift_model_grid))
    shift_model_grid = np.add(shift_model_grid, np.multiply(line, stretch))

    # Interpolate onto measurement wavelength grid
    fit = griddata(shift_model_grid, F_conv, grid, method = 'cubic')

    return fit
