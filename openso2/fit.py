"""
Contains functions to fit UV spectra to retrieve volcanic SO2 slant column densities.
"""

import logging
import numpy as np
from scipy.interpolate import griddata
from scipy.optimize import curve_fit

#==============================================================================
#================================= make_poly ==================================
#==============================================================================

def make_poly(grid, coefs):

    '''
    Function to construct a polynolial given a list of coefficients

    **Parameters:**
        
    grid : array
        X grid over which to calculate the polynomial

    coefs : list
        Polynomial coefficents (of acesnding rank)

    **Returns:**
        
    poly : array
        Resulting polynomial, calculated as:
            poly = p0 + p1*grid + p2*grid^2 + ...
    '''

    poly = np.zeros(len(grid))

    for i, p in enumerate(coefs):

        poly = np.add(poly, np.multiply(np.power(grid, i), p))

    return poly

#==============================================================================
#================================== fit_spec ==================================
#==============================================================================

def fit_spec(common, spectrum, grid):

    '''
    Function to fit measured spectrum using a full forward model including a 
    solar spectrum background polynomial, ring effect, wavelength shift and
    stretch, and gas amounts for so2, no2, o3

    **Parameters:**
        
    common : dictionary
        Common dictionary of parameters and variables passed from the main 
        program to subroutines

    spectrum : 2D array
        Intensity data from the measured spectrum

    grid : 1D array
        Measurement wavelength grid over which the fit occurs

    q : queue (optional)
        Queue to which to add the output if threaded (default = None)

    **Returns:**
        
    fit_dict : dictionary
        Dictionary of optimised parameters

    err_dict : dictionary
        Dictionary of error in the optimised parameters

    y : array
        Measured spectrum, corrected for dark, bias and flat response, in the 
        fitting window

    fit : array
        Fitted spectrum

    fitted_flag : bool
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
    if not np.any(y == 0) and max(y) > 3000:
        try:
            # Fit
            popt, pcov = curve_fit(ifit_fwd_model, 
                                   grid, 
                                   y, 
                                   p0 = common['params'])

            # Get fit errors
            perr = np.sqrt(np.diag(pcov))

            # Fit successful
            fitted_flag = True

        # If fit fails, report and carry on
        except (RuntimeError, ValueError, np.linalg.linalg.LinAlgError):

            # Fill returned arrays with nans
            popt = np.full(len(common['params']), np.nan)
            perr = np.full(len(common['params']), np.nan)

            # Turn off fitted flag
            fitted_flag = False

            # Log
            logging.warning('Fit failed')

    else:
        # Fill returned arrays with nans
        popt = np.full(len(common['params']), np.nan)
        perr = np.full(len(common['params']), np.nan)

        # Turn off fitted flag
        fitted_flag = False

        # Log
        logging.warning('Intensity too low')

    # Return results, either to a queue if threaded, or as an array if not
    return popt, perr, fitted_flag


#==============================================================================
#================================== ifit_fwd ==================================
#==============================================================================

def ifit_fwd_model(grid, p0, p1, p2, p3, shift, stretch, ring_amt, so2_amt,
                   no2_amt, o3_amt):

    '''
    iFit forward model to fit measured UV sky spectra

    **Parameters:**
        
    grid : array
        Measurement wavelength grid

    *args : list
        Forward model state vector

    **Returns:**
        
    fit : array
        Fitted spectrum interpolated onto the spectrometer wavelength grid
    '''

    # Construct background polynomial and add to the fraunhoffer spectrum
    bg_poly = make_poly(com['model_grid'], [p0, p1, p2, p3])
    frs = np.multiply(com['sol'], bg_poly)

    # Build gas spectra
    so2_T = -(np.multiply(com['so2_xsec'], so2_amt))
    no2_T = -(np.multiply(com['no2_xsec'], no2_amt))
    o3_T  = -(np.multiply(com['o3_xsec'],  o3_amt))

    # Ring effect
    ring_T = np.multiply(com['ring'], ring_amt)

    # Combine into a single array
    exponent_data = np.column_stack((so2_T, no2_T, o3_T, ring_T))

    # Sum the data
    exponent = np.exp(np.sum(exponent_data, axis = 1))

    # Multipy by the fraunhofer reference spectrum
    raw_F = np.multiply(frs, exponent)

    # Convolve with the ILS
    F_conv = np.convolve(raw_F, com['ils'], 'same')

    # Apply shift and stretch to the model_grid
    shift_model_grid = np.add(com['model_grid'], shift)
    line = np.linspace(0, 1, num = len(shift_model_grid))
    shift_model_grid = np.add(shift_model_grid, np.multiply(line, stretch))

    # Interpolate onto measurement wavelength grid
    fit = griddata(shift_model_grid, F_conv, grid, method = 'cubic')

    return fit
