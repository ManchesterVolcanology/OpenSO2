import gps
import logging
import subprocess
from datetime import datetime

logger = logging.getLogger()

class GPS(object):

    """GPS class used to listen to GPS signals"""

    def __init__(self):

        # Turn on the GPS daemon
        logger.info('Activating GPS daemon')
        subprocess.call('sudo systemctl stop gpsd.socket', shell=True)
        subprocess.call('sudo systemctl disable gpsd.socket', shell=True)
        subprocess.call('sudo gpsd /dev/ttyUSB0 -F /var/run/gpsd.sock',
                        shell=True)

        # Connect to the GPS
        logger.info('Connecting to GPS')
        self.gpsd = gps.gps("localhost", "2947")
        self.gpsd.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

    def read(self, maxtime=10):
        """Call the GPS for position data"""

        while True:
            print('mark')
            nx = self.gpsd.next()

            if nx['class'] == 'TPV':
                output = {'time': getattr(nx, 'time', 'Unknown'),
                          'lat': getattr(nx, 'lat', 'Unknown'),
                          'lon': getattr(nx, 'lon', 'Unknown'),
                          'alt': getattr(nx, 'alt', 'Unknown')}
                return output

            elif nx['class'] == 'ERROR':
                logger.error(nx['message'])

        logger.warning(f'GPS timed out after {maxtime}s')
        return None

if __name__ == '__main__':

    import time

    gps = GPS()

    data = gps.read()
    for i in range(10):
        print(data['time'], data['lat'], data['lon'])
        time.sleep(1)
