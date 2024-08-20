import navtools.conversions as ntc
from navtools.conversions.coordinates import GEODETIC


def test_ecef_conversions():
    assert ntc.ecef2lla(1.0, 1.0, 1.0) == GEODETIC(lat=32.0, lon=-85.0, alt=200)


if __name__ == "__main__":
    test_ecef_conversions()
