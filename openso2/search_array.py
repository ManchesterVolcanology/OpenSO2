# Written by Ben Esse
# July 2019

import numpy as np
import warnings

#==============================================================================
#================================ find_nearest ================================
#==============================================================================

def find_nearest(data, val):

    '''
    Function to find the nearest item in a list or array to a supplied value

    **Parameters**
    
    data : list or array
        The data array to be searched
    
    val : float
        The target value

    O**Returns**
    
    nearest_val : float
        The nearest value in data to val

    idx : int
        The index of the nearest value
    '''

    # Turn the array into a numpy array
    data = np.asarray(data)

    # Subtract the value from the array
    sub_data = data - val

    # Make all values positive
    abs_data = abs(sub_data)

    # Find the minimum value
    min_val = min(abs_data)
    
    # Get the index
    idx = np.where(abs_data == min_val)[0]
    
    # Check if more than one value found
    if len(idx) > 1:
        warnings.warn(f'{len(idx)} nearest values found, no unique solution')
        idx = np.array([idx[0]])

    return data[idx][0], int(idx)
