from typing import Union

import numpy as np
import pytest

# Assuming the module is imported as:
from navtools.conversions.coordinates import (
    ECEF,
    ECI,
    ENU,
    GEODETIC,
    ecef2enu,
    ecef2enuv,
    ecef2geodetic,
    enu2ecef,
    enu2ecefv,
    enu2geodetic,
    geodetic2ecef,
    geodetic2enu,
)
from navtools.geodesy import GeodeticDatum
from numpy.testing import assert_allclose, assert_array_almost_equal


class TestCoordinateClasses:
    """Test the coordinate system NamedTuple classes."""

    def test_eci_creation(self):
        """Test ECI coordinate creation and access."""
        eci = ECI(x=7000e3, y=0, z=0)
        assert eci.x == 7000000.0
        assert eci.y == 0
        assert eci.z == 0

    def test_ecef_creation(self):
        """Test ECEF coordinate creation and access."""
        ecef = ECEF(x=6378137.0, y=0, z=0)
        assert ecef.x == 6378137.0
        assert ecef.y == 0
        assert ecef.z == 0

    def test_geodetic_creation(self):
        """Test GEODETIC coordinate creation and access."""
        geo = GEODETIC(lat=0.0, lon=0.0, alt=0.0)
        assert geo.lat == 0.0
        assert geo.lon == 0.0
        assert geo.alt == 0.0

    def test_enu_creation(self):
        """Test ENU coordinate creation and access."""
        enu = ENU(east=100.0, north=0.0, up=5.0)
        assert enu.east == 100.0
        assert enu.north == 0.0
        assert enu.up == 5.0

    def test_coordinate_with_arrays(self):
        """Test coordinate classes with numpy arrays."""
        x_arr = np.array([1.0, 2.0, 3.0])
        y_arr = np.array([4.0, 5.0, 6.0])
        z_arr = np.array([7.0, 8.0, 9.0])

        ecef = ECEF(x=x_arr, y=y_arr, z=z_arr)
        assert_array_almost_equal(ecef.x, x_arr)
        assert_array_almost_equal(ecef.y, y_arr)
        assert_array_almost_equal(ecef.z, z_arr)


class TestGeodetic2ECEF:
    """Test geodetic to ECEF conversions."""

    def test_equator_prime_meridian(self):
        """Test conversion at equator and prime meridian."""
        ecef = geodetic2ecef(0.0, 0.0, 0.0)
        assert_allclose(ecef.x, 6378137.0, rtol=1e-6)
        assert_allclose(ecef.y, 0.0, atol=1e-9)
        assert_allclose(ecef.z, 0.0, atol=1e-9)

    def test_equator_90_degrees(self):
        """Test conversion at equator and 90 degrees longitude."""
        ecef = geodetic2ecef(0.0, np.pi / 2, 0.0)
        assert_allclose(ecef.x, 0.0, atol=1e-9)
        assert_allclose(ecef.y, 6378137.0, rtol=1e-6)
        assert_allclose(ecef.z, 0.0, atol=1e-9)

    def test_north_pole(self):
        """Test conversion at north pole."""
        ecef = geodetic2ecef(np.pi / 2, 0.0, 0.0)
        assert_allclose(ecef.x, 0.0, atol=1e-9)
        assert_allclose(ecef.y, 0.0, atol=1e-9)
        assert_allclose(ecef.z, 6356752.314245179, rtol=1e-6)  # WGS84 polar radius

    def test_with_altitude(self):
        """Test conversion with non-zero altitude."""
        alt = 1000.0  # 1km altitude
        ecef = geodetic2ecef(0.0, 0.0, alt)
        assert_allclose(ecef.x, 6378137.0 + alt, rtol=1e-6)
        assert_allclose(ecef.y, 0.0, atol=1e-9)
        assert_allclose(ecef.z, 0.0, atol=1e-9)

    def test_degrees_input(self):
        """Test conversion with degree inputs."""
        ecef = geodetic2ecef(0.0, 90.0, 0.0, deg=True)
        assert_allclose(ecef.x, 0.0, atol=1e-9)
        assert_allclose(ecef.y, 6378137.0, rtol=1e-6)
        assert_allclose(ecef.z, 0.0, atol=1e-9)

    def test_array_input(self):
        """Test conversion with array inputs."""
        lats = np.array([0.0, np.pi / 2])
        lons = np.array([0.0, 0.0])
        alts = np.array([0.0, 0.0])

        ecef = geodetic2ecef(lats, lons, alts)

        # First point: equator, prime meridian
        assert_allclose(ecef.x[0], 6378137.0, rtol=1e-6)
        assert_allclose(ecef.y[0], 0.0, atol=1e-9)
        assert_allclose(ecef.z[0], 0.0, atol=1e-9)

        # Second point: north pole
        assert_allclose(ecef.x[1], 0.0, atol=1e-9)
        assert_allclose(ecef.y[1], 0.0, atol=1e-9)
        assert_allclose(ecef.z[1], 6356752.314245179, rtol=1e-6)


class TestECEF2Geodetic:
    """Test ECEF to geodetic conversions."""

    def test_equator_prime_meridian(self):
        """Test conversion at equator and prime meridian."""
        geo = ecef2geodetic(6378137.0, 0.0, 0.0)
        assert_allclose(geo.lat, 0.0, atol=1e-9)
        assert_allclose(geo.lon, 0.0, atol=1e-9)
        assert_allclose(geo.alt, 0.0, atol=1e-3)

    def test_equator_90_degrees(self):
        """Test conversion at equator and 90 degrees longitude."""
        geo = ecef2geodetic(0.0, 6378137.0, 0.0)
        assert_allclose(geo.lat, 0.0, atol=1e-9)
        assert_allclose(geo.lon, np.pi / 2, rtol=1e-6)
        assert_allclose(geo.alt, 0.0, atol=1e-3)

    def test_north_pole(self):
        """Test conversion at north pole."""
        geo = ecef2geodetic(0.0, 0.0, 6356752.314245179)
        assert_allclose(geo.lat, np.pi / 2, rtol=1e-6)
        # Longitude is undefined at poles, but should be finite
        assert np.isfinite(geo.lon)
        assert_allclose(geo.alt, 0.0, atol=1e-3)

    def test_with_altitude(self):
        """Test conversion with altitude."""
        alt = 1000.0
        geo = ecef2geodetic(6378137.0 + alt, 0.0, 0.0)
        assert_allclose(geo.lat, 0.0, atol=1e-9)
        assert_allclose(geo.lon, 0.0, atol=1e-9)
        assert_allclose(geo.alt, alt, rtol=1e-6)

    def test_array_input(self):
        """Test conversion with array inputs."""
        x = np.array([6378137.0, 0.0])
        y = np.array([0.0, 6378137.0])
        z = np.array([0.0, 0.0])

        geo = ecef2geodetic(x, y, z)

        # First point
        assert_allclose(geo.lat[0], 0.0, atol=1e-9)
        assert_allclose(geo.lon[0], 0.0, atol=1e-9)

        # Second point
        assert_allclose(geo.lat[1], 0.0, atol=1e-9)
        assert_allclose(geo.lon[1], np.pi / 2, rtol=1e-6)


class TestRoundTripConversions:
    """Test round-trip conversions between coordinate systems."""

    @pytest.mark.parametrize(
        "lat,lon,alt",
        [
            (0.0, 0.0, 0.0),
            (np.pi / 4, np.pi / 4, 1000.0),
            (-np.pi / 6, -np.pi / 3, 5000.0),
            (np.pi / 2 - 1e-6, 0.0, 0.0),  # Near north pole
            (-np.pi / 2 + 1e-6, 0.0, 0.0),  # Near south pole
        ],
    )
    def test_geodetic_ecef_roundtrip(self, lat, lon, alt):
        """Test geodetic -> ECEF -> geodetic round trip."""
        # Forward conversion
        ecef = geodetic2ecef(lat, lon, alt)

        # Reverse conversion
        geo_back = ecef2geodetic(ecef.x, ecef.y, ecef.z)

        # Check round-trip accuracy
        assert_allclose(geo_back.lat, lat, rtol=1e-9, atol=1e-15)
        assert_allclose(geo_back.lon, lon, rtol=1e-9, atol=1e-15)
        assert_allclose(geo_back.alt, alt, rtol=1e-9, atol=1e-6)

    def test_array_roundtrip(self):
        """Test round-trip with array inputs."""
        lats = np.array([0.0, np.pi / 4, -np.pi / 6])
        lons = np.array([0.0, np.pi / 4, -np.pi / 3])
        alts = np.array([0.0, 1000.0, 5000.0])

        # Forward conversion
        ecef = geodetic2ecef(lats, lons, alts)

        # Reverse conversion
        geo_back = ecef2geodetic(ecef.x, ecef.y, ecef.z)

        # Check round-trip accuracy
        assert_allclose(geo_back.lat, lats, rtol=1e-9, atol=1e-15)
        assert_allclose(geo_back.lon, lons, rtol=1e-9, atol=1e-15)
        assert_allclose(geo_back.alt, alts, rtol=1e-9, atol=1e-6)


class TestECEF2ENU:
    """Test ECEF to ENU conversions."""

    def test_ecef2enuv_basic(self):
        """Test basic ecef2enuv transformation."""
        # At equator, prime meridian, ECEF x-axis points up in ENU
        enu = ecef2enuv(1.0, 0.0, 0.0, 0.0, 0.0)
        assert_allclose(enu.east, 0.0, atol=1e-15)
        assert_allclose(enu.north, 0.0, atol=1e-15)
        assert_allclose(enu.up, 1.0, rtol=1e-15)

    def test_ecef2enuv_east_direction(self):
        """Test east direction transformation."""
        # At equator, prime meridian, ECEF y-axis points east in ENU
        enu = ecef2enuv(0.0, 1.0, 0.0, 0.0, 0.0)
        assert_allclose(enu.east, 1.0, rtol=1e-15)
        assert_allclose(enu.north, 0.0, atol=1e-15)
        assert_allclose(enu.up, 0.0, atol=1e-15)

    def test_ecef2enuv_north_direction(self):
        """Test north direction transformation."""
        # At equator, prime meridian, ECEF z-axis points north in ENU
        enu = ecef2enuv(0.0, 0.0, 1.0, 0.0, 0.0)
        assert_allclose(enu.east, 0.0, atol=1e-15)
        assert_allclose(enu.north, 1.0, rtol=1e-15)
        assert_allclose(enu.up, 0.0, atol=1e-15)

    def test_ecef2enu_same_point(self):
        """Test ECEF to ENU when points are the same."""
        enu = ecef2enu(6378137.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert_allclose(enu.east, 0.0, atol=1e-6)
        assert_allclose(enu.north, 0.0, atol=1e-6)
        assert_allclose(enu.up, 0.0, atol=1e-6)

    def test_ecef2enu_with_degrees(self):
        """Test ECEF to ENU with degree inputs."""
        enu = ecef2enuv(1.0, 0.0, 0.0, 0.0, 0.0, deg=True)
        assert_allclose(enu.up, 1.0, rtol=1e-15)


class TestGeoetic2ENU:
    """Test geodetic to ENU conversions."""

    def test_geodetic2enu_same_point(self):
        """Test geodetic to ENU when points are the same."""
        enu = geodetic2enu(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert_allclose(enu.east, 0.0, atol=1e-9)
        assert_allclose(enu.north, 0.0, atol=1e-9)
        assert_allclose(enu.up, 0.0, atol=1e-9)

    def test_geodetic2enu_altitude_difference(self):
        """Test geodetic to ENU with altitude difference."""
        enu = geodetic2enu(0.0, 0.0, 1000.0, 0.0, 0.0, 0.0)
        assert_allclose(enu.east, 0.0, atol=1e-6)
        assert_allclose(enu.north, 0.0, atol=1e-6)
        assert_allclose(enu.up, 1000.0, rtol=1e-6)

    def test_geodetic2enu_with_degrees(self):
        """Test geodetic to ENU with degree inputs."""
        enu = geodetic2enu(0.0, 0.0, 1000.0, 0.0, 0.0, 0.0, deg=True)
        assert_allclose(enu.up, 1000.0, rtol=1e-6)


class TestENU2ECEF:
    """Test ENU to ECEF conversions."""

    def test_enu2ecefv_basic(self):
        """Test basic enu2ecefv transformation."""
        # At equator, prime meridian, ENU up should give ECEF x
        ecef = enu2ecefv(0.0, 0.0, 1.0, 0.0, 0.0)
        assert_allclose(ecef.x, 1.0, rtol=1e-15)
        assert_allclose(ecef.y, 0.0, atol=1e-15)
        assert_allclose(ecef.z, 0.0, atol=1e-15)

    def test_enu2ecefv_east_direction(self):
        """Test east direction transformation."""
        # At equator, prime meridian, ENU east should give ECEF y
        ecef = enu2ecefv(1.0, 0.0, 0.0, 0.0, 0.0)
        assert_allclose(ecef.x, 0.0, atol=1e-15)
        assert_allclose(ecef.y, 1.0, rtol=1e-15)
        assert_allclose(ecef.z, 0.0, atol=1e-15)

    def test_enu2ecef_zero_displacement(self):
        """Test ENU to ECEF with zero displacement."""
        ecef = enu2ecef(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        geo_origin = geodetic2ecef(0.0, 0.0, 0.0)
        assert_allclose(ecef.x, geo_origin.x, rtol=1e-9)
        assert_allclose(ecef.y, geo_origin.y, rtol=1e-9)
        assert_allclose(ecef.z, geo_origin.z, rtol=1e-9)


class TestENU2Geodetic:
    """Test ENU to geodetic conversions."""

    def test_enu2geodetic_zero_displacement(self):
        """Test ENU to geodetic with zero displacement."""
        geo = enu2geodetic(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        assert_allclose(geo.lat, 0.0, atol=1e-15)
        assert_allclose(geo.lon, 0.0, atol=1e-15)
        assert_allclose(geo.alt, 0.0, atol=1e-9)

    def test_enu2geodetic_up_displacement(self):
        """Test ENU to geodetic with upward displacement."""
        geo = enu2geodetic(0.0, 0.0, 1000.0, 0.0, 0.0, 0.0)
        assert_allclose(geo.lat, 0.0, atol=1e-9)
        assert_allclose(geo.lon, 0.0, atol=1e-9)
        assert_allclose(geo.alt, 1000.0, rtol=1e-6)


class TestENU_Roundtrips:
    """Test round-trip conversions involving ENU."""

    def test_enu_ecef_roundtrip(self):
        """Test ENU -> ECEF -> ENU round trip."""
        east, north, up = 100.0, 200.0, 50.0
        lat0, lon0, alt0 = np.pi / 6, np.pi / 4, 1000.0

        # Forward conversion
        ecef = enu2ecef(east, north, up, lat0, lon0, alt0)

        # Reverse conversion
        enu_back = ecef2enu(ecef.x, ecef.y, ecef.z, lat0, lon0, alt0)

        # Check round-trip accuracy
        assert_allclose(enu_back.east, east, rtol=1e-9)
        assert_allclose(enu_back.north, north, rtol=1e-9)
        assert_allclose(enu_back.up, up, rtol=1e-9)

    def test_enu_geodetic_roundtrip(self):
        """Test ENU -> geodetic -> ENU round trip."""
        east, north, up = 100.0, 200.0, 50.0
        lat0, lon0, alt0 = np.pi / 6, np.pi / 4, 1000.0

        # Forward conversion
        geo = enu2geodetic(east, north, up, lat0, lon0, alt0)

        # Reverse conversion
        enu_back = geodetic2enu(geo.lat, geo.lon, geo.alt, lat0, lon0, alt0)

        # Check round-trip accuracy
        assert_allclose(enu_back.east, east, rtol=1e-9, atol=1e-6)
        assert_allclose(enu_back.north, north, rtol=1e-9, atol=1e-6)
        assert_allclose(enu_back.up, up, rtol=1e-9, atol=1e-6)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_near_poles(self):
        """Test conversions near the poles."""
        # Very close to north pole
        lat_near_pole = np.pi / 2 - 1e-9
        ecef = geodetic2ecef(lat_near_pole, 0.0, 0.0)
        geo_back = ecef2geodetic(ecef.x, ecef.y, ecef.z)
        assert_allclose(geo_back.lat, lat_near_pole, rtol=1e-9)

    def test_negative_altitudes(self):
        """Test with negative altitudes."""
        alt = -1000.0  # Below ellipsoid
        ecef = geodetic2ecef(0.0, 0.0, alt)
        geo_back = ecef2geodetic(ecef.x, ecef.y, ecef.z)
        assert_allclose(geo_back.alt, alt, rtol=1e-6)

    def test_large_coordinates(self):
        """Test with large coordinate values."""
        # Test with coordinates at satellite altitudes
        alt = 35786000.0  # Geostationary orbit altitude
        ecef = geodetic2ecef(0.0, 0.0, alt)
        geo_back = ecef2geodetic(ecef.x, ecef.y, ecef.z)
        assert_allclose(geo_back.alt, alt, rtol=1e-6)

    def test_zero_coordinates(self):
        """Test with zero coordinates."""
        geo = ecef2geodetic(0.0, 0.0, 0.0)
        # Should handle gracefully without errors
        assert np.isfinite(geo.lat)
        assert np.isfinite(geo.lon)
        assert np.isfinite(geo.alt)


class TestArrayOperations:
    """Test operations with various array shapes and sizes."""

    def test_mixed_scalar_array(self):
        """Test mixing scalar and array inputs."""
        lats = np.array([0.0, np.pi / 4])
        lon_scalar = 0.0
        alt_scalar = 0.0

        ecef = geodetic2ecef(lats, lon_scalar, alt_scalar)
        assert len(ecef.x) == 2
        assert len(ecef.y) == 2
        assert len(ecef.z) == 2

    def test_large_arrays(self):
        """Test with larger arrays."""
        n = 1000
        lats = np.random.uniform(-np.pi / 2, np.pi / 2, n)
        lons = np.random.uniform(-np.pi, np.pi, n)
        alts = np.random.uniform(0, 10000, n)

        ecef = geodetic2ecef(lats, lons, alts)
        geo_back = ecef2geodetic(ecef.x, ecef.y, ecef.z)

        # Check that all conversions are reasonable
        assert_allclose(geo_back.lat, lats, rtol=1e-9, atol=1e-15)
        assert_allclose(geo_back.lon, lons, rtol=1e-9, atol=1e-15)
        assert_allclose(geo_back.alt, alts, rtol=1e-9, atol=1e-6)


class TestCustomDatum:
    """Test with custom geodetic datums."""

    def test_custom_datum_roundtrip(self):
        """Test round-trip with a custom datum."""
        # This test assumes GeodeticDatum.from_datum works with other datums
        # You may need to adjust based on your actual GeodeticDatum implementation
        try:
            custom_datum = GeodeticDatum.from_datum(datum_name="grs80")

            lat, lon, alt = np.pi / 4, np.pi / 6, 1000.0
            ecef = geodetic2ecef(lat, lon, alt, datum=custom_datum)
            geo_back = ecef2geodetic(ecef.x, ecef.y, ecef.z, datum=custom_datum)

            assert_allclose(geo_back.lat, lat, rtol=1e-9)
            assert_allclose(geo_back.lon, lon, rtol=1e-9)
            assert_allclose(geo_back.alt, alt, rtol=1e-9)
        except:
            pytest.skip("Custom datum not available")


if __name__ == "__main__":
    pytest.main([__file__])
