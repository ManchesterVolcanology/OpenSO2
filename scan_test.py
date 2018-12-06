import datetime as dt
import time

from openso2.scanner_control import Scanner

# Connect to the scanner
scanner = Scanner()

# Find home
print('Finding home...')
scanner.home()
print('Done!')

time.sleep(3)

# Scan
n = 0
while True:

    # Move to start position
    scanner.step(steps = 100, steptype = 'interleave')
    time.sleep(1)
    
    # Step
    for i in range(200):
        scanner.step(steptype = 'interleave')
        time.sleep(0.1)
    	
    time.sleep(1)
    
    n += 1
    print('Scan no.', n, 'complete!')
    print(dt.datetime.now())
    
    scanner.home()
    
    time.sleep(3)
