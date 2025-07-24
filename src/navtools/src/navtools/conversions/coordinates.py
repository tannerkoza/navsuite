__all__ = [
    "ecef2geodetic",
    "ecef2enu",
    "geodetic2ecef",
    "geodetic2enu",
    "enu2ecef",
    "enu2geodetic",
]


from typing import NamedTuple

import numpy as np

from navtools.geodesy import GeodeticDatum


class ECI(NamedTuple):
    """
    Earth-Centered Inertial (ECI) coordinate tuple.

    Fields
    ------
    x : float or ndarray
        ECI x-coordinate (units consistent with input).
    y : float or ndarray
        ECI y-coordinate.
    z : float or ndarray
        ECI z-coordinate.

    Examples
    --------
    >>> e = ECI(x=7000e3, y=0, z=0)
    >>> e.x, e.y, e.z
    (7000000.0, 0, 0)
    """

    x: float | np.ndarray
    y: float | np.ndarray
    z: float | np.ndarray


class ECEF(NamedTuple):
    """
    Earth-Centered Earth-Fixed (ECEF) coordinate tuple.

    Fields
    ------
    x : float or ndarray
        ECEF x-coordinate (meters).
    y : float or ndarray
        ECEF y-coordinate (meters).
    z : float or ndarray
        ECEF z-coordinate (meters).

    Examples
    --------
    >>> pt = ECEF(x=6378137.0, y=0, z=0)
    >>> round(pt.x, 3)
    6378137.0
    """

    x: float | np.ndarray
    y: float | np.ndarray
    z: float | np.ndarray


class GEODETIC(NamedTuple):
    """
    Geodetic coordinate tuple: latitude, longitude, altitude.

    Fields
    ------
    lat : float or ndarray
        Geodetic latitude (radians or degrees if `deg=True`).
    lon : float or ndarray
        Geodetic longitude (radians or degrees if `deg=True`).
    alt : float or ndarray
        Altitude above ellipsoid (meters).

    Examples
    --------
    >>> g = GEODETIC(lat=0.0, lon=0.0, alt=0.0)
    >>> (g.lat, g.lon, g.alt)
    (0.0, 0.0, 0.0)
    """

    lat: float | np.ndarray
    lon: float | np.ndarray
    alt: float | np.ndarray


class ENU(NamedTuple):
    """
    Local tangent-plane ENU coordinate tuple.

    Fields
    ------
    east : float or ndarray
        East component (meters).
    north : float or ndarray
        North component (meters).
    up : float or ndarray
        Up component (meters).

    Examples
    --------
    >>> e = ENU(east=100.0, north=0.0, up=5.0)
    >>> (e.east, e.north, e.up)
    (100.0, 0.0, 5.0)
    """

    east: float | np.ndarray
    north: float | np.ndarray
    up: float | np.ndarray


# earth-centered earth-fixed (ECEF)
def ecef2geodetic(
    x: float | np.ndarray,
    y: float | np.ndarray,
    z: float | np.ndarray,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
) -> GEODETIC:
    """Borkowski closed-form cartesian to curvilinear conversion (Groves 2013).

    Parameters
    ----------
    x : float or ndarray
        x geocentric position, datum units
    y : float or ndarray
        y geocentric position, datum units
    z : float or ndarray
        z geocentric position, datum units
    datum : GeodeticDatum, optional
        geodetic datum (default WGS‑84)

    Returns
    -------
    GEODETIC
        geodetic position (lat, lon, alt)

    Examples
    --------
    >>> # single point at equator
    >>> pt = ecef2geodetic(6378137.0, 0, 0)
    >>> round(pt.lat, 6), round(pt.lon, 6), round(pt.alt, 3)
    (0.0, 0.0, 0.0)

    >>> # array input
    >>> pts = np.array([[6378137.0, 0, 0],
    ...                 [0, 6378137.0, 0]])
    >>> geod = ecef2geodetic(pts[:,0], pts[:,1], pts[:,2])
    >>> geod.lon.tolist()
    [0.0, 1.5707963267948966]
    """
    k1 = np.sqrt(1 - datum.eccentricity**2) * np.abs(z)
    k2 = datum.eccentricity**2 * datum.r0
    beta = np.sqrt(x**2 + y**2)  # Eq. C.18

    E = (k1 - k2) / beta  # Eq. C.29
    F = (k1 + k2) / beta  # Eq. C.30

    P = 4 / 3 * (E * F + 1)  # Eq. C.31
    Q = 2 * (E**2 - F**2)  # Eq. C.32
    D = P**3 + Q**2  # Eq. C.33
    V = (np.sqrt(D) - Q) ** (1 / 3) - (np.sqrt(D) + Q) ** (1 / 3)  # Eq. C.34
    G = 0.5 * (np.sqrt(E**2 + V) + E)  # Eq. C.35
    T = np.sqrt(G**2 + (F - V * G) / (2 * G - E)) - G  # Eq. C.36

    lat = np.sign(z) * np.arctan(
        (1 - T**2) / (2 * T * np.sqrt(1 - datum.eccentricity**2))
    )  # Eq. C.37
    lon = np.arctan2(y, x)
    alt = (beta - datum.r0 * T) * np.cos(lat) + (
        z - np.sign(z) * datum.r0 * np.sqrt(1 - datum.eccentricity**2)
    ) * np.sin(lat)  # Eq. C.38

    return GEODETIC(lat=lat, lon=lon, alt=alt)


def C_ecef2enu(
    x: float | np.ndarray,
    y: float | np.ndarray,
    z: float | np.ndarray,
    lat0: float,
    lon0: float,
    deg: bool = False,
) -> ENU:
    """Rotate ECEF vector into local ENU frame (Groves 2013).

    Parameters
    ----------
    x, y, z : float or ndarray
        ECEF position or vector components
    lat0 : float
        latitude of local tangent origin
    lon0 : float
        longitude of local tangent origin
    deg : bool, optional
        input lat/lon are in degrees if True

    Returns
    -------
    ENU
        ENU components of input vector

    Examples
    --------
    >>> # simple example at equator prime meridian
    >>> enu = C_ecef2enu(1, 0, 0, 0.0, 0.0)
    >>> round(enu.east, 6), round(enu.north, 6), round(enu.up, 6)
    (-0.0, -0.0, 1.0)
    """

    if deg:
        lat0 = np.radians(lat0)
        lon0 = np.radians(lon0)

    cos_lat0 = np.cos(lat0)
    sin_lat0 = np.sin(lat0)
    cos_lon0 = np.cos(lon0)
    sin_lon0 = np.sin(lon0)

    # Eq. 2.158 adapted for ENU instead of NED
    east = -sin_lon0 * x + cos_lon0 * y
    north = -sin_lat0 * cos_lon0 * x + -sin_lat0 * sin_lon0 * y + cos_lat0 * z
    up = cos_lat0 * cos_lon0 * x + cos_lat0 * sin_lon0 * y + sin_lat0 * z

    return ENU(east=east, north=north, up=up)


def ecef2enu(
    x: float | np.ndarray,
    y: float | np.ndarray,
    z: float | np.ndarray,
    lat0: float,
    lon0: float,
    alt0: float,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
    deg: bool = False,
) -> ENU:
    """Convert ECEF coordinates to local ENU position (Groves 2013).

    Parameters
    ----------
    x, y, z : float or ndarray
        ECEF coordinates of point
    lat0, lon0 : float
        geodetic origin of ENU frame
    alt0 : float
        altitude of origin
    datum : GeodeticDatum, optional
        geodetic datum for conversion
    deg : bool, optional
        lat/lon inputs in degrees if True

    Returns
    -------
    ENU
        ENU coordinates relative to origin

    Examples
    --------
    >>> e = ecef2enu(1, 0, 0, 0.0, 0.0, 0.0)
    >>> round(e.east,6), round(e.north,6), round(e.up,6)
    (-0.0, -0.0, 1.0)
    """

    x0, y0, z0 = geodetic2ecef(lat=lat0, lon=lon0, alt=alt0, datum=datum, deg=deg)
    enu = C_ecef2enu(
        x=x - x0, y=y - y0, z=z - z0, lat0=lat0, lon0=lon0, deg=deg
    )  # Eqs. 2.158 and 2.160

    return enu


# curvilinear (GEODETIC)
def geodetic2ecef(
    lat: float | np.ndarray,
    lon: float | np.ndarray,
    alt: float | np.ndarray,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
    deg: bool = False,
) -> ECEF:
    """Convert geodetic lat/lon/alt to ECEF coordinates (Groves 2013).

    Parameters
    ----------
    lat, lon : float or ndarray
        geodetic latitude and longitude (radians or degrees)
    alt : float or ndarray
        altitude above ellipsoid
    datum : GeodeticDatum, optional
        geodetic datum (default WGS‑84)
    deg : bool, optional
        input lat/lon in degrees if True

    Returns
    -------
    ECEF
        ECEF coordinates (x, y, z)

    Examples
    --------
    >>> pt = geodetic2ecef(0.0, 0.0, 0.0)
    >>> round(pt.x, 3), round(pt.y, 3), round(pt.z, 3)
    (6378137.0, 0.0, 0.0)
    """
    if deg:
        lat = np.radians(lat)
        lon = np.radians(lon)

    cos_lat = np.cos(lat)
    cos_lon = np.cos(lon)
    sin_lat = np.sin(lat)
    sin_lon = np.sin(lon)

    # transverse radius of curvature
    re = datum.r0 / np.sqrt(1 - (datum.eccentricity * sin_lat) ** 2)  # Eq. 2.106

    # Eq. 2.112
    x = (re + alt) * cos_lat * cos_lon
    y = (re + alt) * cos_lat * sin_lon
    z = ((1 - datum.eccentricity**2) * re + alt) * sin_lat

    return ECEF(x=x, y=y, z=z)


def geodetic2enu(
    lat: float | np.ndarray,
    lon: float | np.ndarray,
    alt: float | np.ndarray,
    lat0: float,
    lon0: float,
    alt0: float,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
    deg: bool = False,
) -> ENU:
    """Convert geodetic lla to ENU coordinates around a reference (WGS‑84).

    Parameters
    ----------
    lat, lon : float or ndarray
        geodetic position to convert
    alt : float or ndarray
        altitude above ellipsoid
    lat0, lon0, alt0 : float
        reference station geodetic coordinates
    datum : GeodeticDatum, optional
        geodetic datum (default WGS‑84)
    deg : bool, optional
        input in degrees if True

    Returns
    -------
    ENU
        ENU vector from reference point

    Examples
    --------
    >>> e = geodetic2enu(0, 0, 0, 0, 0, 0)
    >>> round(e.up, 6)
    0.0
    """
    x, y, z = geodetic2ecef(lat=lat, lon=lon, alt=alt, datum=datum, deg=deg)
    x0, y0, z0 = geodetic2ecef(lat=lat0, lon=lon0, alt=alt0, datum=datum, deg=deg)

    enu = C_ecef2enu(x=x - x0, y=y - y0, z=z - z0, lat0=lat0, lon0=lon0, deg=deg)

    return enu


# local navigation/tangent-plane (ENU)
def C_enu2ecef(
    east: float | np.ndarray,
    north: float | np.ndarray,
    up: float | np.ndarray,
    lat0: float,
    lon0: float,
    deg: bool = False,
) -> ECEF:
    """Rotate ENU vector to ECEF frame (Groves 2013).

    Parameters
    ----------
    east, north, up : float or ndarray
        ENU components of vector
    lat0, lon0 : float
        reference geodetic location
    deg : bool, optional
        input lat/lon in degrees if True

    Returns
    -------
    ECEF
        ECEF vector corresponding to input ENU

    Examples
    --------
    >>> ecef = C_enu2ecef(1, 0, 0, 0, 0)
    >>> round(ecef.x,6), round(ecef.y,6), round(ecef.z,6)
    (0.0, 0.0, 1.0)
    """

    if deg:
        lat0 = np.radians(lat0)
        lon0 = np.radians(lon0)

    cos_lat0 = np.cos(lat0)
    sin_lat0 = np.sin(lat0)
    cos_lon0 = np.cos(lon0)
    sin_lon0 = np.sin(lon0)

    # Eq. 2.158 adapted for ENU instead of NED
    x = -sin_lon0 * east + -sin_lat0 * cos_lat0 * north + cos_lat0 * cos_lon0 * up
    y = cos_lon0 * east + -sin_lat0 * sin_lon0 * north + cos_lat0 * sin_lon0 * up
    z = cos_lat0 * north + sin_lat0 * up

    return ECEF(x=x, y=y, z=z)


def enu2ecef(
    east: float | np.ndarray,
    north: float | np.ndarray,
    up: float | np.ndarray,
    lat0: float,
    lon0: float,
    alt0: float,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
    deg: bool = False,
) -> ECEF:
    """Convert local ENU to geocentric ECEF coordinates.

    Parameters
    ----------
    east, north, up : float or ndarray
        ENU coordinates
    lat0, lon0 : float
        reference geodetic coordinates
    alt0 : float
        reference altitude
    datum : GeodeticDatum, optional
        geodetic datum (default WGS‑84)
    deg : bool, optional
        input lat/lon in degrees

    Returns
    -------
    ECEF
        ECEF position corresponding to ENU

    Examples
    --------
    >>> ecef = enu2ecef(0, 0, 1, 0, 0, 0)
    >>> round(ecef.z,6)
    1.0
    """
    dx, dy, dz = C_enu2ecef(
        east=east, north=north, up=up, lat0=lat0, lon0=lon0, deg=deg
    )
    x0, y0, z0 = geodetic2ecef(
        lat=lat0, lon=lon0, alt=alt0, datum=datum, deg=deg
    )  # Eqs. 2.158 and 2.160

    return ECEF(x=x0 + dx, y=y0 + dy, z=z0 + dz)


def enu2geodetic(
    east: float | np.ndarray,
    north: float | np.ndarray,
    up: float | np.ndarray,
    lat0: float,
    lon0: float,
    alt0: float,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
    deg: bool = False,
) -> GEODETIC:
    """Convert local ENU displacement to geodetic coordinates.

    Parameters
    ----------
    east, north, up : float or ndarray
        ENU displacement vector
    lat0, lon0 : float
        geodetic reference point
    alt0 : float
        reference altitude
    datum : GeodeticDatum, optional
        geodetic datum
    deg : bool, optional
        input lat/lon in degrees

    Returns
    -------
    GEODETIC
        geodetic coordinates after applying ENU offset

    Examples
    --------
    >>> gd = enu2geodetic(0, 0, 1, 0, 0, 0)
    >>> round(gd.alt,6)
    1.0
    """
    x, y, z = enu2ecef(
        east=east,
        north=north,
        up=up,
        lat0=lat0,
        lon0=lon0,
        alt0=alt0,
        datum=datum,
        deg=deg,
    )

    geodetic = ecef2geodetic(x=x, y=y, z=z, datum=datum)

    return geodetic
