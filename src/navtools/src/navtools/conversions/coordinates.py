"""coordinates.py contains coordinate frame transformations for multiple reference frames used commonly in navigation"""

__all__ = ["ecef2lla"]

from typing import NamedTuple

import numba as nb
import numpy as np

from navtools.constants import WGS84_E, WGS84_R0


# coordinate/reference frame types
class ECI(NamedTuple):
    x: float | np.ndarray
    y: float | np.ndarray
    z: float | np.ndarray


class ECEF(NamedTuple):
    x: float | np.ndarray
    y: float | np.ndarray
    z: float | np.ndarray


class NED(NamedTuple):
    north: float | np.ndarray
    east: float | np.ndarray
    down: float | np.ndarray


class ENU(NamedTuple):
    east: float | np.ndarray
    north: float | np.ndarray
    up: float | np.ndarray


class GEODETIC(NamedTuple):
    lat: float | np.ndarray
    lon: float | np.ndarray
    alt: float | np.ndarray


# earth-centered inertial (ECI)


# earth-centered earth-fixed (ECEF)
@nb.njit(cache=True, fastmath=True)
def ecef2lla(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> GEODETIC:
    return GEODETIC(lat=32.0, lon=-85.0, alt=200)


# local navigation/tangent-plane (NED/ENU)
