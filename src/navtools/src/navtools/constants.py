"""constants.py contains constants commonly used in navigation"""

from __future__ import annotations
from math import sqrt
from dataclasses import dataclass
# physical
"""a collection of physical constants used across physics in general
"""
SPEED_OF_LIGHT: float = 299792458.0  # [m/s]
BOLTZMANN: float = 1.38e-23  # [J/K]
GRAVITY: float = 9.80665  # acceleration due to gravity (Earth) [m/s^2]

# global datums
""" a collection of constants specific to global datums (e.g., WGS84, GRS80, etc.) 
"""
WGS84_R0: float = 6378137.0  # WGS84 equatorial radius [m]
WGS84_RP: float = 6356752.31425  # WGS84 polar radius [m]
WGS84_F: float = 1.0 / 298.257223563  # WGS84 flattening
WGS84_E: float = 0.0818191908425  # WGS84 eccentricity
WGS84_EARTH_RATE: float = 7.292115e-5  # WGS84 Earth rotation rate [rad/s]

GRS80_R0: float = WGS84_R0  # GRS80 equatorial radius [m]
GRS80_RP: float = 6356752.31414  # GRS80 polar radius [m]
GRS80_F: float = 1.0 / 298.257222101  # GRS80 flattening
GRS80_E: float = 0.0818191910428  # GRS80 eccentricity


@dataclass
class GeodeticDatum:
    """a geodetic datum (ellipsoid) used for conversions, rotations, etc.

    default datums:
        wgs84: https://en.wikipedia.org/wiki/World_Geodetic_System#WGS84

        grs80: https://en.wikipedia.org/wiki/GRS_80

        pz90.11: https://structure.mil.ru/files/pz-90.pdf
    """

    model: str
    name: str
    r0: float
    rp: float
    flattening: float
    third_flattening: float
    eccentricity: float
    default_models = {
        # Earth ellipsoid models
        "grs80": {"name": "GRS-80 (1979)", "r0": 6378137.0, "rp": 6356752.31414036},
        "wgs84": {"name": "WGS-84 (1984)", "r0": 6378137.0, "rp": 6356752.31424518},
        "pz90.11": {"name": "ПЗ-90 (2011)", "r0": 6378136.0, "rp": 6356751.3618},
    }

    def __init__(
        self,
        r0: float,
        rp: float,
        name: str = "",
        model: str = "",
    ):
        """a default or custom geodetic datum (ellipsoid) model

        Parameters
        ----------
        r0 : float
            equatorial radius or semi-major axis
        rp : float
            polar radius or semi-minor axis
        name : str, optional
            formal datum name, by default ""
        model : str, optional
            short-hand datum name, by default ""
        """

        self.flattening = (r0 - rp) / r0
        assert self.flattening >= 0, "flattening must be >= 0"
        self.third_flattening = (r0 - rp) / (r0 + rp)
        self.eccentricity = sqrt(2 * self.flattening - self.flattening**2)

        self.name = name
        self.model = model
        self.r0 = r0
        self.rp = rp

    @classmethod
    def from_datum(cls, datum_name: str) -> GeodeticDatum:
        """create GeodeticDatum instance from known datum name

        Parameters
        ----------
        datum_name : str
            name of the desired default GeodeticDatum

        Returns
        -------
        GeodeticDatum
            desired default GeodeticDatum
        """

        return cls(
            cls.default_models[datum_name]["r0"],
            cls.default_models[datum_name]["rp"],
            name=cls.default_models[datum_name]["name"],
            model=datum_name,
        )
