from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import NamedTuple

import numpy as np


class Datum(NamedTuple):
    """
    Basic ellipsoid datum definition.

    Attributes
    ----------
    name : str
        Full name of the datum (e.g., "WGS-84 (1984)").
    r0 : float
        Equatorial radius (semi-major axis) in meters.
    rp : float
        Polar radius (semi-minor axis) in meters.

    Examples
    --------
    >>> Datum(name="WGS84", r0=6378137.0, rp=6356752.31424518)
    Datum(name='WGS84', r0=6378137.0, rp=6356752.31424518)
    """

    name: str
    r0: float
    rp: float


"""A collection of constants specific to global datums (e.g., WGS84, GRS80)."""
GEODETIC_DATUMS: dict[str, Datum] = {
    "grs80": Datum(name="GRS-80 (1979)", r0=6378137.0, rp=6356752.31414036),
    "wgs84": Datum(name="WGS-84 (1984)", r0=6378137.0, rp=6356752.31424518),
    "pz90.11": Datum(name="ПЗ-90 (2011)", r0=6378136.0, rp=6356751.3618),
}


@dataclass
class GeodeticDatum:
    """
    A geodetic ellipsoid datum model for coordinate conversions.

    Default datums:
      - wgs84: https://en.wikipedia.org/wiki/World_Geodetic_System#WGS84
      - grs80: https://en.wikipedia.org/wiki/GRS_80
      - pz90.11: https://structure.mil.ru/files/pz-90.pdf

    Attributes
    ----------
    model : str
        Abbreviation of the datum ("wgs84", "grs80", etc.).
    name : str
        Full formal name of the datum.
    r0 : float
        Equatorial radius (m).
    rp : float
        Polar radius (m).
    flattening : float
        Flattening = (r0 - rp) / r0.
    third_flattening : float
        Third flattening = (r0 - rp) / (r0 + rp).
    eccentricity : float
        First eccentricity of the ellipsoid.

    Examples
    --------
    >>> d = GeodeticDatum.from_datum("wgs84")
    >>> round(d.flattening, 9)
    0.003352813
    """

    model: str
    name: str
    r0: float
    rp: float
    flattening: float
    third_flattening: float
    eccentricity: float

    def __init__(
        self,
        r0: float,
        rp: float,
        name: str = "",
        model: str = "",
    ):
        """
        Parameters
        ----------
        r0 : float
            Equatorial radius (semi-major axis).
        rp : float
            Polar radius (semi-minor axis).
        name : str, optional
            Full official name of the datum.
        model : str, optional
            Abbreviated model identifier.
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
        """
        Instantiate a GeodeticDatum from a predefined constant.

        Parameters
        ----------
        datum_name : str
            Key name in `GEODETIC_DATUMS` (e.g., "wgs84").

        Returns
        -------
        GeodeticDatum
            Instance with appropriate ellipsoid parameters.

        Examples
        --------
        >>> d = GeodeticDatum.from_datum("grs80")
        >>> d.model, d.name
        ('grs80', 'GRS-80 (1979)')
        """
        return cls(
            r0=GEODETIC_DATUMS[datum_name].r0,
            rp=GEODETIC_DATUMS[datum_name].rp,
            name=GEODETIC_DATUMS[datum_name].name,
            model=datum_name,
        )


def great_circle_distance(
    lat0,
    lon0,
    lat1,
    lon1,
    datum=GeodeticDatum.from_datum(datum_name="wgs84"),
    deg: bool = False,
):
    if deg:
        lat0 = np.radians(lat0)
        lon0 = np.radians(lon0)
        lat1 = np.radians(lat1)
        lon1 = np.radians(lon1)

    # differences in coordinates
    dlat = lat1 - lat0
    dlon = lon1 - lon0

    # Haversine formula
    a = np.sin(dlat / 2) ** 2 + np.cos(lat0) * np.cos(lat1) * np.sin(dlon / 2) ** 2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))

    # distance in meters
    distance = datum.r0 * c

    return distance
