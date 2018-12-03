import numpy as np
from scipy.interpolate import griddata
from scipy.optimize import curve_fit

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

def fit_spec(common, spectrum, grid, q = None):
    
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
    
    # Remove stray light
    y = np.subtract(y, np.average(y[common['stray_idx']]))
    
    # Cut desired wavelength window
    y = y[common['fit_idx']]

    # Divide by flat spectrum
    y = np.divide(y, common['flat'])
    
    # Unpack the inital fit parameters
    fit_params = []
    
    for key, val in common['params'].items():
        fit_params.append(val[0])
    
    # Appempt to fit!
    try:
        # Fit
        popt, pcov = curve_fit(ifit_fwd_model, grid, y, p0 = fit_params)
        
        # Fit successful
        fitted_flag = True
    
    # If fit fails, report and carry on
    except RuntimeError:
        
        # Fill returned arrays with zeros
        popt = np.zeros(len(fit_params))
        pcov = np.zeros((len(fit_params), len(fit_params)))
        
        fit = np.zeros(len(grid))
        
        # Turn off fitted flag
        fitted_flag = False

    # Unpack fit results
    fit_dict  = {}
    m = 0
    for key, val in common['params'].items():
        if val[1] == 'Fit':
            fit_dict[key] = popt[m]
            m+=1

    # Generate a dictionary of errors
    # NOTE this is covarience in fitting params and does not include systematic errors!
    err_dict = {}
    m = 0
    for key, val in common['params'].items():
        if val[1] == 'Fit':
            err_dict[key] = np.sqrt(np.diag(pcov))[m]
            m+=1
    
    # Return results, either to a queue if threaded, or as an array if not
    if q == None:                     
        return fit_dict, err_dict, y, fit, fitted_flag
    
    else:
        output = fit_dict, err_dict, y, fit, fitted_flag
        q.put(('fit', output))


#========================================================================================
#======================================== ifit_fwd ======================================
#========================================================================================

def ifit_fwd_model(grid, *fit_params):
    
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

    # Unpack params
    p = {}
    i = 0

    for key, val in com['params'].items():
           
        if val[1] == 'Fit':
            p[key] = fit_params[i]
            i += 1
            
        if val[1] in ['Fix', 'Pre-calc', 'File']:
            p[key] = val[0]
            
        if val[1] == 'N/A':
            p[key] = 0
       
    # Unpack polynomial parameters
    poly_coefs = np.zeros(com['poly_n'])
    for i in range(com['poly_n']):
        poly_coefs[i] = (fit_params[i])

    # Construct background polynomial
    bg_poly = make_poly(com['model_grid'], poly_coefs)
    
    
    # Build gas transmittance spectra
    so2_T = np.exp(-(np.multiply(com['so2_xsec'], p['so2_amt'])))
    no2_T = np.exp(-(np.multiply(com['no2_xsec'], p['no2_amt'])))
    o3_T  = np.exp(-(np.multiply(com['o3_xsec'],  p['o3_amt'])))

    
    # Background sky spectrum
    sol_spec = np.multiply(bg_poly, com['sol'])
    
    
    # Ring effect
    ring_T = np.exp(np.multiply(com['ring'], p['ring_amt']))
    sol_T = np.multiply(sol_spec, ring_T)
    
    
    # Background sky spectrum
    bg_spec = np.multiply(np.multiply(sol_T, no2_T), o3_T)
       
    
    # Include gasses and areosol
    raw_F = np.multiply(bg_spec, so2_T)

    
    # Convolve with the ILS
    F_conv = np.convolve(raw_F, com['ils'], 'same')
    
    
    # Apply shift and stretch to the model_grid
    shift_model_grid = np.add(com['model_grid'], p['shift'])
    line = np.linspace(0, 1, num = len(shift_model_grid))
    shift_model_grid = np.add(shift_model_grid, np.multiply(line, p['stretch']))
    
    # Interpolate onto measurement wavelength grid
    fit = griddata(shift_model_grid, F_conv, grid, method = 'cubic')
        
    return fit
