"""types.py contains containers and numpy dtypes for commonly used representations, measurement sets, etc."""

from typing import NamedTuple

import numpy as np


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


# emitter & observable dtypes
true_observable_dtype = np.dtype(
    {
        "names": [
            "ts",
            "id",
            "system",
            "signal",
            "freq",
            "cn0",
            "range",
            "range_rate",
        ],
        "formats": ["f8", "H", "H", "H", "f8", "f8", "f8", "f8", "f8", "f8"],
    }
)

raw_observable_dtype = np.dtype(
    {
        "names": [
            "ts",
            "id",
            "system",
            "signal",
            "freq",
            "cn0",
            "prange",
            "prange_var",
            "prange_rate",
            "prange_rate_var",
        ],
        "formats": ["f8", "H", "H", "H", "f8", "f8", "f8", "f8", "f8", "f8"],
    }
)

emitter_dtype = np.dtype(
    {
        "names": [
            "ts",
            "id",
            "system",
            "clock_bias",
            "clock_drift",
            "xpos",
            "ypos",
            "zpos",
            "xvel",
            "yvel",
            "zvel",
        ],
        "formats": ["f8", "H", "H", "f8", "f8", "f8", "f8", "f8", "f8", "f8", "f8"],
    }
)
