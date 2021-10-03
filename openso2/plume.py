"""Functions to calculate SO2 fluxes from scanners."""

import logging
import numpy as np
from scipy.optimize import least_squares
from math import sin, cos, atan2, pi, asin


logger = logging.getLogger(__name__)


# =============================================================================
# Calculate plume altitude
# =============================================================================

def calc_plume_altitude(station1, station2, plume_loc1, plume_loc2,
                        vent_location, init_altitude=1000, bounds=[0, np.inf]):
    """Calculate the plume altitude.

    This function calculates the plume altitude from the location of the plume
    centre position in two scans given the vent and scanner locations. The
    algorithm works by varying an estimated plume altitude to minimise the
    difference between the calculated plume azimuths for each scanner.

    Parameters
    ----------
    station1, station2 : openso2 Station objects
        Holds the station information. This function requires the loc_info
        dictionary, which contains the latitude, longitude, altitude and
        azimuth of the station in a dictionary.
    plume_loc1, plume_loc2 : float
        The plume centre location in the scans for station 1 and 2 respectively
        in degrees from zenith, increasing anit-clockwise when looking along
        the scan axis.
    vent_location : tuple of floats
        The location of the gas source as [lat, lon] in decimal degrees.
    init_altitude : float, optional
        The initial guess at the plume altitude in meters above sea level.
        Default is 1000m.
    bounds : tuple, optional
        Bounds for the minimiser on the calculated altitude as [min, max].
        Default is [0, inf].

    Returns
    -------
    plume_altitude : float
        The altitude of the plume in meters above sea level
    plume_azimuth : float
        The azimuth of the plume in degrees clockwise from north
    """
    # Pack the arguments for the minimiser function
    args = [station1, station2, plume_loc1, plume_loc2, vent_location]

    # Find the optimal altitude
    output = least_squares(_altitude_minimiser, [init_altitude], args=args,
                           bounds=bounds)

    # Unpack the output
    plume_altitude = output['x'][0]

    # Calculate the corresponding azimuth
    plume_azimuth = calc_plume_azimuth(station1, plume_loc1, vent_location,
                                       plume_altitude)

    return plume_altitude, plume_azimuth


def _altitude_minimiser(altitude, *args):

    # Extract the altitude float
    alt = altitude[0]

    # Unpack the other arguements
    station1, station2, plume_loc1, plume_loc2, vent_location = args

    az1 = calc_plume_azimuth(station1, plume_loc1, vent_location, alt)
    az2 = calc_plume_azimuth(station2, plume_loc2, vent_location, alt)

    # Return the difference
    return abs(az1 - az2)


# =============================================================================
# Calculate Scan Flux
# =============================================================================

def calc_scan_flux(angles, scan_so2, station, vent_location, windspeed,
                   plume_altitude, plume_azimuth):
    """Calculate the SO2 flux from a single scan.

    This function calculates the SO2 flux from a scan assuming the gas is at a
    fixed distance from the scanner.

    Parameters
    ----------
    angles : numpy array length N
        The scan angles for each individual measurement [degrees].
    scan_so2 : numpy array length N
        The SO2 slant columns for each individual measurement [molecules/cm^2].
    station : openso2 Station object
        Holds the station information. This function requires the loc_info
        dictionary, which contains the latitude, longitude, altitude and
        azimuth of the station in a dictionary.
    vent_location : tuple
        The location of the volcano (or gas source) as [lat, lon].
    windspeed : float
        The wind speed used to scale the cross-section to a flux [m/s].
    plume_altitude : float
        The altitude of the plume in m a.s.l..
    plume_azimuth : float
        The azimuthal direction of travel of the plume in degrees (measured
        clockwise from North).

    Returns
    -------
    flux_kg_s : float
        The calculated flux [kg/s].
    flux_err : float
        The error on the flux [kg/s].
    """
    # Unpack SO2 amts and error
    so2_amts, so2_errs = scan_so2

    # Extract the station information
    keys = ['latitude', 'longitude', 'altitude', 'azimuth']
    lat, lon, alt, az = [station.loc_info[key] for key in keys]

    # Convert angles to radians
    scan_phi = np.radians(az)
    plume_phi = np.radians(plume_azimuth)
    phi = np.radians(angles)

    arc_radius = calc_arc_radius(station, vent_location, plume_altitude,
                                 plume_azimuth)

    # Calculate the delta angle of each spectrum
    dphi = np.diff(phi)

    # Convert to arc length
    dx = np.multiply(dphi, arc_radius)

    # Calculate the arc so2 between each spectrum
    arc_so2 = [x*np.average([so2_amts[n], so2_amts[n+1]])
               for n, x in enumerate(dx)]
    arc_err = [x*np.average([so2_errs[n], so2_errs[n+1]])
               for n, x in enumerate(dx)]

    # Add up the total SO2 in the scan, ignoring any nans
    total_so2 = np.nansum(arc_so2)
    total_err = np.nansum(np.power(arc_err, 2))**0.5

    # Correct for the angle between the plume azimuth and scan plane
    corr_total_so2 = np.multiply(total_so2,
                                 np.cos(scan_phi - (plume_phi-np.pi)))
    corr_total_err = np.multiply(total_err,
                                 np.cos(scan_phi - (plume_phi-np.pi)))

    # Convert from molecules/cm to moles/m
    so2_moles = corr_total_so2 * 1.0e4 / 6.022e23
    err_moles = corr_total_err * 1.0e4 / 6.022e23

    # Convert to kg/m. Molar mass of so2 is 64.066g/mole
    so2_kg = so2_moles * 0.064066
    err_kg = err_moles * 0.064066

    # Get flux in kg/s
    flux_kg_s = so2_kg * windspeed
    flux_err = err_kg * windspeed

    return flux_kg_s, flux_err


# =============================================================================
# Calculate Plume Azimuth
# =============================================================================

def calc_plume_azimuth(station, plume_loc, vent_location, plume_altitude):
    """Determine the plume azimuth given a plume altitude and station info.

    Parameters
    ----------
    station : openso2 Station object
        Holds the station information. This function requires the loc_info
        dictionary, which contains the latitude, longitude, altitude and
        azimuth of the station in a dictionary.
    plume_loc : float
        The location of the plume center in the scan, measured in degrees from
        zenith, increasing anit-clockwise when looking along the scan axis.
    vent_location : tuple of floats
        The location of the gas source as [lat, lon] in decimal degrees.
    plume_altitude : float
        The altitude of the plume in meters above sea level.

    Returns
    -------
    plume_azimth : float
        The azimuth of the plume, measured in degrees clockwise from North.
    """
    # Extract the station information
    keys = ['latitude', 'longitude', 'altitude', 'azimuth']
    lat, lon, alt, az = [station.loc_info[key] for key in keys]

    # Convert the scan theta into radians
    alpha = np.radians(plume_loc)

    # Calculate the bearing of the scan plane vector, depending on the plume
    # position. If the plume is directly overhead, just return the voclano -
    # station bearing
    if alpha == 0:
        x, plume_azimth = haversine(vent_location, [lat, lon])
        return plume_azimth
    elif alpha > 0:
        phi = bearing_check(np.radians(az) - pi/2)
    else:
        phi = bearing_check(np.radians(az) + pi/2)

    # Correct the plume altitude given the station altitude
    plume_height = plume_altitude - alt

    # Calculate the distance from the staiton to the plume
    d = plume_height * np.tan(np.abs(alpha))

    # Calculate the location of the intersection point
    intersect_point = calc_end_point([lat, lon], d, phi)

    # Calculate th vector from the volcano to the intersect point
    dist, plume_azimuth = haversine(vent_location, intersect_point)

    return plume_azimuth


# =============================================================================
# Calcuate Plume Height
# =============================================================================

def calc_plume_altitude_single(station, plume_loc, vent_location,
                               plume_azimuth, x0=[1000, 1000],
                               bounds=[0, np.inf]):
    """Calculate the plume altitude from a single scan given the plume azimuth.

    Parameters
    ----------
    station : openso2 Station object
        Holds the station information. This function requires the loc_info
        dictionary, which contains the latitude, longitude, altitude and
        azimuth of the station in a dictionary.
    plume_loc : float
        The location of the plume center in the scan, measured in degrees from
        zenith, increasing anit-clockwise when looking along the scan axis.
    vent_location : tuple of floats
        The location of the gas source as [lat, lon] in decimal degrees.
    plume_azimuth : float
        The azimuth of the plume vector in degrees clockwise from North.

    Returns
    -------
    plume_altitude : float
        The altitude of the plume in meters above sea level.
    """
    # Unpack the station location information
    keys = ['latitude', 'longitude', 'altitude', 'azimuth']
    lat, lon, alt, az = [station.loc_info[key] for key in keys]

    # Convert the scan theta into radians
    alpha = np.radians(plume_loc)

    # Calculate the bearing of the scan plane vector, depending on the plume
    # position. If the plume is directly overhead, just return the voclano -
    # station bearing
    if alpha == 0:
        logger.warning("Plume directly over scanner, altitude unconstrained")
        return np.nan
    elif alpha > 0:
        phi = bearing_check(np.radians(az) - pi/2)
    else:
        phi = bearing_check(np.radians(az) + pi/2)

    # Set minimiser arguements
    args = [[lat, lon], phi, vent_location, plume_azimuth]

    # Perform minimisation
    output = least_squares(_intersect_minimiser, x0, args=args, bounds=bounds)

    # Unpack the output
    scan_dist, plume_dist = output['x']

    # Calculate the plume altitude, correcting for the station altitude
    plume_altitude = alt + (scan_dist / np.tan(np.abs(alpha)))

    return plume_altitude


def _intersect_minimiser(x, *args):

    # Extract the altitude float
    scan_dist, plume_dist = x

    # Unpack the other arguements
    stat_location, scan_azimuth, vent_location, plume_azimuth = args

    # Calculate the intersect positions
    x1, y1 = calc_end_point(vent_location, plume_dist, plume_azimuth)
    x2, y2 = calc_end_point(stat_location, scan_dist, scan_azimuth)

    # Return the difference
    return abs(x1 - x1) + abs(y1 - y2)


# =============================================================================
# Calculate scan arc radius
# =============================================================================

def calc_arc_radius(station, vent_location, plume_altitude, plume_azimuth):
    """Calculate the scan arc radius.

    Parameters
    ----------
    station : openso2 Station object
        Holds the station information. This function requires the loc_info
        dictionary, which contains the latitude, longitude, altitude and
        azimuth of the station in a dictionary.
    vent_location : tuple
        The location of the volcano (or gas source) as [lat, lon].
    plume_altitude : float
        The altitude of the plume in m a.s.l..
    plume_azimuth : float
        The azimuthal direction of travel of the plume in degrees (measured
        clockwise from North).

    Returns
    -------
    arc_radius : float
        The radius of the scan arc in meters
    """
    # Pull pi from numpy
    pi = np.pi

    # Extract the station information
    keys = ['latitude', 'longitude', 'altitude', 'azimuth']
    lat, lon, alt, az = [station.loc_info[key] for key in keys]

    # Correct the plume height for the station altitude
    rel_plume_altitude = plume_altitude - alt

    # Convert the plume and scan azimuth to radians
    scan_phi = np.radians(az)
    plume_phi = np.radians(plume_azimuth)

    # Find the distance and bearing from the volcano to the station and back
    x, mu_p = haversine(vent_location, [lat, lon])
    x1, mu = haversine([lat, lon], vent_location)

    # Calculate delta, the angle between the station-volcano and plume vectors
    delta = np.abs(plume_phi - mu_p)

    # Calculate psi, the azimuth angle of the scan plane
    if plume_phi < mu_p:
        psi = scan_phi + pi/2
    elif plume_phi > mu_p:
        psi = scan_phi - pi/2

    # Calculate gamma, the internal angle between the scan plane and the
    # station-volcano vector
    gamma = np.abs(psi - mu)

    # Calculate epsilon, the angle between the station-plume and plume vectors
    epsilon = pi - gamma - delta

    # Calcuate d, the ground distance from the scanner to the plume
    d = x * np.sin(delta) / np.sin(epsilon)

    arc_radius = (d**2 + rel_plume_altitude**2)**0.5

    return arc_radius


# =============================================================================
# haversine
# =============================================================================

def haversine(start_coords, end_coords, radius=6371000):
    """Calculate the distance and initial bearing between two points.

    Parameters
    ----------
    start_coords : tuple
        Start coordinates (lat, lon) in decimal degrees (+ve = north/east).
    end_coords : tuple
        End coordinates (lat, lon) in decimal degrees (+ve = north/east).
    radius: float, optional
        Radius of the body in meters. Default is set to the Earth radius
        (6731km).

    Returns
    -------
    distance : float
        The linear distance between the two points in meters.
    bearing : float
        The initial bearing between the two points (radians).
    """
    # Unpack the coordinates and convert to radians
    lat1, lon1 = np.radians(start_coords)
    lat2, lon2 = np.radians(end_coords)

    # Calculate the change in lat and lon
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    # Calculate the square of the half chord length
    a = (sin(dlat/2))**2 + (cos(lat1) * cos(lat2) * (sin(dlon/2))**2)

    # Calculate the angular distance
    c = 2 * atan2(np.sqrt(a), np.sqrt(1-a))

    # Find distance moved
    distance = radius * c

    # Calculate the initial bearing
    bearing = atan2(sin(dlon) * cos(lat2),
                    (cos(lat1)*sin(lat2)) - (sin(lat1)*cos(lat2)*cos(dlon)))

    bearing = bearing_check(bearing)

    return distance, bearing


# =============================================================================
# Calculate end point
# =============================================================================

def calc_end_point(start_coords, distance, bearing, radius=6371000):
    """Calculate end point from a start location given a distance and bearing.

    Parameters
    ----------
    start_coords : tuple
        Starting coordinates (lat, lon) in decimal degrees (+ve = north/east).
    distance : float
        The distance moved in meters.
    bearing : float
        The bearing of travel in degrees clockwise from north.
    radius : float
        Radius of the body in meters. Default is set to the Earth radius
        (6731 km).

    Returns
    -------
    end_coords, tuple
        The final coordinates (lat, lon) in decimal degrees (+ve = north/east)
    """
    # Convert the inputs to radians
    lat, lon = np.radians(start_coords)
    theta = np.radians(bearing)

    # Calculate the angular distance moved
    ang_dist = distance / radius

    # Calculate the final latitude
    end_lat = asin(np.add((sin(lat) * cos(ang_dist)),
                          (cos(lat) * sin(ang_dist) * cos(theta))))

    # Calculate the final longitude
    end_lon = lon + atan2(sin(theta) * sin(ang_dist) * cos(lat),
                          cos(ang_dist) - (sin(lat)*sin(end_lat)))

    return np.degrees([end_lat, end_lon])


# =============================================================================
# Bearing Check
# =============================================================================

def bearing_check(angle):
    """Ensure an angle is between 0 and 2pi."""
    return angle % (2*pi)
