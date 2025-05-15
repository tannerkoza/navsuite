"""coordinates.py contains coordinate frame transformations for multiple reference frames used commonly in navigation"""

__all__ = [
    "ecef2geodetic",
    "ecef2enu",
    "geodetic2ecef",
    "geodetic2enu",
    "enu2ecef",
    "enu2geodetic",
]


import numba as nb
import numpy as np

from navtools.constants import GeodeticDatum
from navtools.types import ECI, ECEF, GEODETIC, ENU


# earth-centered earth-fixed (ECEF)
def ecef2geodetic(
    x: float | np.ndarray,
    y: float | np.ndarray,
    z: float | np.ndarray,
    datum: GeodeticDatum = GeodeticDatum.from_datum(datum_name="wgs84"),
) -> GEODETIC:
    """Borkowski closed-form cartesian to curvilinear conversion, Principles of GNSS, Inertial, and
    Multisensor Integrated Navigation Systems, Groves (2013), Appendix C.2.3

        Parameters
        ----------
        x : float | np.ndarray
            x geocentric position, datum units
        y : float | np.ndarray
            y geocentric position, datum units
        z : float | np.ndarray
            z geocentric position, datum units
        datum : GeodeticDatum, optional
            geodetic datum describing ellipsoid, by default GeodeticDatum.from_datum(datum_name="wgs84")

        Returns
        -------
        GEODETIC
            geodetic position
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


@nb.njit(cache=True, fastmath=True)
def C_ecef2enu(
    x: float | np.ndarray,
    y: float | np.ndarray,
    z: float | np.ndarray,
    lat0: float,
    lon0: float,
    deg: bool = False,
) -> ENU:
    """rotates ECEF vector to local tangent plane, Principles of GNSS, Inertial, and
    Multisensor Integrated Navigation Systems, Groves (2013), Chapter 2.5.4

    Parameters
    ----------
    x : float | np.ndarray
        x geocentric component
    y : float | np.ndarray
        y geocentric component
    z : float | np.ndarray
        z geocentric component
    lat0 : float
        local tangent origin latitude
    lon0 : float
        local tangent origin longitude
    deg : bool, optional
        geodetic units boolean, by default False

    Returns
    -------
    ENU
        enu local tangent vector
    """

    if deg:
        lat0 = np.radians(lat0)
        lon0 = np.radians(lon0)

    # Eq. 2.158 adapted for ENU instead of NED
    east = -np.sin(lon0) * x + np.cos(lon0) * y
    north = (
        -np.sin(lat0) * np.cos(lon0) * x
        + -np.sin(lat0) * np.sin(lon0) * y
        + np.cos(lat0) * z
    )
    up = (
        np.cos(lat0) * np.cos(lon0) * x
        + np.cos(lat0) * np.sin(lon0) * y
        + np.sin(lat0) * z
    )

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
    """converts geocentric position to local tangent enu, Principles of GNSS, Inertial, and
    Multisensor Integrated Navigation Systems, Groves (2013), Chapter 2.5.4

    Parameters
    ----------
    x : float | np.ndarray
        x geocentric position, datum units
    y : float | np.ndarray
        y geocentric position, datum units
    z : float | np.ndarray
        z geocentric position, datum units
    lat0 : float
        local tangent origin latitude
    lon0 : float
        local tangent origin longitude
    alt0 : float
        local tangent origin altitude (HAE), datum units
    datum : GeodeticDatum, optional
        geodetic datum describing ellipsoid, by default GeodeticDatum.from_datum(datum_name="wgs84")
    deg : bool, optional
        geodetic units boolean, by default False

    Returns
    -------
    ENU
        enu local tangent position
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
    """converts geodetic curvilinear position to geocentric position, Principles of GNSS, Inertial, and
    Multisensor Integrated Navigation Systems, Groves (2013), Chapter 2.4.3

    Parameters
    ----------
    lat : float | np.ndarray
        geodetic latitude, [rad]
    lon : float | np.ndarray
        geodetic longitude, [rad]
    alt : float | np.ndarray
        altitude, datum units
    datum : GeodeticDatum, optional
        geodetic datum describing ellipsoid, by default GeodeticDatum.from_datum(datum_name="wgs84")
    deg : bool, optional
        geodetic units boolean, by default False

    Returns
    -------
    ECEF
        geocentric position
    """
    if deg:
        lat = np.radians(lat)
        lon = np.radians(lon)

    # transverse radius of curvature
    re = datum.r0 / np.sqrt(1 - (datum.eccentricity * np.sin(lat)) ** 2)  # Eq. 2.106

    cos_lat = np.cos(lat)
    cos_lon = np.cos(lon)
    sin_lat = np.sin(lat)
    sin_lon = np.sin(lon)

    # Eq. 2.112
    x = (re + alt) * cos_lat * cos_lon
    y = (re + alt) * cos_lat * sin_lon
    z = ((1 - datum.eccentricity**2) * re + alt) * sin_lat

    return ECEF(x=x, y=y, z=z)


@nb.njit(cache=True, fastmath=True)
def geodetic2enu(
    lat: float | np.ndarray,
    lon: float | np.ndarray,
    alt: float | np.ndarray,
    deg: bool = False,
) -> ENU:
    pass


# local navigation/tangent-plane (ENU)
@nb.njit(cache=True, fastmath=True)
def enu2ecef(
    east: float | np.ndarray, north: float | np.ndarray, up: float | np.ndarray
) -> ECEF:
    pass


@nb.njit(cache=True, fastmath=True)
def enu2geodetic(
    east: float | np.ndarray, north: float | np.ndarray, up: float | np.ndarray
) -> GEODETIC:
    pass
