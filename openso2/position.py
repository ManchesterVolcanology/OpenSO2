"""Contains GPS functions."""

import logging
import subprocess

logger = logging.getLogger()


def gps_sync(gps, name):
    """Syncs the position and time with the GPS."""
    # Get a fix from the GPS
    ts, lat, lon, alt, flag = gps.get_fix(time_to_wait=7200)
    tstamp = ts.strftime("%Y-%m-%d %H:%M:%S")

    if flag:
        logger.info('Updating system time: {tstamp}')
        tstr = ts.strftime('%a %b %d %H:%M:%S UTC %Y')
        subprocess.call(f'sudo date -s {tstr}', shell=True)

        # Log the scanner location
        logger.info('Scanner location:\n'
                    + f'Latitude:   {lat}'
                    + f'Longitutde: {lon}'
                    + f'Altitude:   {alt}')

        # Write the position to a file
        with open(f'Station/{name}', 'w') as w:
            w.write(f'Time: {tstamp}\nLat: {lat}\nLon: {lon}\nAlt: {alt}')

    else:
        logger.warning('GPS fix failed, using RTC time (not yet implemented)')
