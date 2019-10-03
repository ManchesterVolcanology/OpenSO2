# -*- coding: utf-8 -*-
"""
Module to control the power settings of the Raspberry Pi.
"""

from openso2.julian_time import hms_to_julian, julian_to_hms

def update_power_time(on_time, off_time):
    
    '''
    Function to update the WittyPi2 board schedule file
    
    Paramters:
        
    on_time : float
        Time to turn the station on in decimal hours
        
    off_time : float
        Time to turn the station off in decimal hours
        
    Returns:
        
    None
    '''

    # Find difference between the on and off times
    delta_t = julian_to_hms(hms_to_julian(off_time) - hms_to_julian(on_time))
    on_h = delta_t.hour
    on_m = delta_t.minute
    on_s = delta_t.second

    # Build on string
    on_str = 'ON   '
    if on_h != 0:
        on_str += f' H{on_h}'
    if on_m != 0:
        on_str += f' M{on_m}'
    if on_s != 0:
        on_str += f' S{on_s}'
    on_str += '\n'

    # Calculate the off time
    delta_t = julian_to_hms(24 - (hms_to_julian(off_time) - hms_to_julian(on_time)))
    off_h = delta_t.hour
    off_m = delta_t.minute
    off_s = delta_t.second

    # Build on string
    off_str = 'OFF  '
    if off_h != 0:
        off_str += f' H{off_h}'
    if off_m != 0:
        off_str += f' M{off_m}'
    if off_s != 0:
        off_str += f' S{off_s}'

    # Build strings for witty control file
    control_str = 'BEGIN 2000-01-01 ' + str(on_time) + '\n' + \
                  'END   2100-01-01 23:59:59\n' + on_str + off_str

    return control_str


if __name__ == '__main__':

    import datetime as dt

    t_on  = dt.time(6,  0,  0)
    t_off = dt.time(18, 30, 0)

    print(update_power_time(t_on, t_off))
