"""coordinates.py contains coordinate frame transformations for multiple reference frames used commonly in navigation"""

__all__ = ["ecef2lla"]

import numpy as np
import numba as nb

from typing import NamedTuple
from navtools.constants import WGS84_R0, WGS84_E


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
def ecef2lla(x: np.array, y: np.array, z: np.array) -> GEODETIC:
    return True


# local navigation/tangent-plane (NED/ENU)
