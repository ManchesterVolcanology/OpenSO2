# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 10:59:03 2019

@author: mqbpwbe2
"""

import os
import time

def status_loop():

    while True:

        # Read the temperature
        temp_str = os.popen("/opt/vc/bin/vcgencmd measure_temp").readline()

        # Convert the string output to a float
        temp = temp_str.replace("temp=","").replace("'C", "").strip()

        # Write status to a file
        with open('Station/temp.txt', 'w') as w:
            w.write(temp)

        # Wait
        time.sleep(1)