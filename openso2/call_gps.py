import logging
import subprocess

try:
    import gps
except ImportError:
    print('GPS module missing!')


logger = logging.getLogger(__name__)


def sync_gps_time():
    """Sync the system time with GPS.

    **Parameters:**

    None

    **Returns:**

    None
    """
    # Listen on port 2947 (GPSD) of localhost
    gpsd = gps.gps("localhost", "2947")
    gpsd.stream(gps.WATCH_ENABLE | gps.WATCH_NEWSTYLE)

    while True:

        # Wait until the next GPSD time tick
        gpsd.next()

        if gpsd.utc is not None and gpsd.utc != '':
            # gpsd.utc is formatted like"2015-04-01T17:32:04.000Z"
            # convert it to a form the date -u command will accept:
            #     "20140401 17:32:04"
            # use python slice notation [start:end]
            # (where end desired end char+1)
            #    gpsd.utc[0:4] is "2015"
            #    gpsd.utc[5:7] is "04"
            #    gpsd.utc[8:10] is "01"
            # gpsutc = gpsd.utc[0:4] + gpsd.utc[5:7] + gpsd.utc[8:10] + ' ' +
            # gpsd.utc[11:19]

            # Extract the GPS timestamp
            gpsutc = gpsd.utc[11:19]

            # Call a process to update the system time with the GPS time
            subprocess.call(f'sudo date -s "$(date +%y-%m-%d) {gpsutc}"',
                            shell=True)

            # Log the change
            logger.info('System time updated from GPS: ' + gpsutc)

            # Exit the loop
            break
