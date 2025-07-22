import numpy as np
from navtools.conversions.coordinates import C_ecef2enu, ecef2geodetic, geodetic2ecef

# lla = np.array([90, 0, 0])

# ecef = geodetic2ecef(lat=lla[0], lon=lla[1], alt=lla[2], deg=True)

ecef = np.array([0, 0, -6356752.3142])

lla = ecef2geodetic(ecef[0], ecef[1], ecef[2])


import math


def ecef2lla(
    x,
    y,
    z,
    a=6378137.0,  # semi-major axis
    b=6356752.3142,  # semi-minor axis
    tol=1e-12,  # convergence threshold (radians)
    max_iter=10,
):
    """
    Convert ECEF (x, y, z) → geodetic (lat, lon, h).
    Returns latitude & longitude in radians, altitude in meters.
    Based on Bowring’s 1985 one‑iteration method with a small loop for convergence.
    """
    """
    Olson (1996) ECEF → Geodetic conversion (non-iterative, pole-stable).
    Returns lat, lon in radians, height in meters.
    """
    # Ellipsoid constants
    e2 = (a * a - b * b) / (a * a)
    ep2 = (a * a - b * b) / (b * b)

    p = math.hypot(x, y)
    r = math.hypot(p, z)

    # Olson's intermediary steps
    E = a * math.sqrt(e2)
    u = math.sqrt(
        0.5 * (r * r - E * E)
        + 0.5 * math.sqrt((r * r - E * E) ** 2 + 4 * E * E * z * z)
    )
    sin_lat = abs(z) / u
    cos_lat = p / u
    lat = math.atan2(z + ep2 * b * sin_lat**3, p - e2 * a * cos_lat**3)
    lon = math.atan2(y, x)

    N = a / math.sqrt(1 - e2 * math.sin(lat) ** 2)
    h = (
        p * math.cos(lat)
        + z * math.sin(lat)
        - a * math.sqrt(1 - e2 * math.sin(lat) ** 2)
    )

    return lat, lon, h


lla2 = ecef2lla(ecef[0], ecef[1], ecef[2])
print(lla)
print(lla2)
pass
