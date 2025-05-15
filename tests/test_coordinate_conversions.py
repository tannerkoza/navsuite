import navtools.conversions as ntc
import numpy as np
from navtools.constants import GEODETIC_DATUMS
from pytest import approx


def test_ecef_conversions():
    WGS84 = GEODETIC_DATUMS["wgs84"]

    lla = np.array(ntc.ecef2geodetic(x=WGS84.r0, y=0.0, z=0.0))
    assert lla == approx(np.zeros(3), rel=1e-9)

    ecef = np.array(ntc.geodetic2ecef(lat=90.0, lon=0.0, alt=0.0, deg=True))
    assert ecef == approx(np.array([0.0, 0.0, WGS84.rp]), abs=1e-9)


if __name__ == "__main__":
    test_ecef_conversions()
