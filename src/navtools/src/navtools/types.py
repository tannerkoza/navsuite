"""types.py contains containers and numpy dtypes for commonly used representations, measurement sets, etc."""

import numpy as np

from typing import NamedTuple


# geodetic datums
class Datum(NamedTuple):
    name: str
    r0: float
    rp: float


# coordinate/reference frame
class ECI(NamedTuple):
    x: float | np.ndarray
    y: float | np.ndarray
    z: float | np.ndarray


class ECEF(NamedTuple):
    x: float | np.ndarray
    y: float | np.ndarray
    z: float | np.ndarray


class GEODETIC(NamedTuple):
    lat: float | np.ndarray
    lon: float | np.ndarray
    alt: float | np.ndarray


class ENU(NamedTuple):
    east: float | np.ndarray
    north: float | np.ndarray
    up: float | np.ndarray
