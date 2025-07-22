import numpy as np
from navtools.conversions import enu2geodetic, geodetic2ecef, geodetic2enu
from navtools.conversions.coordinates import ECEF, GEODETIC
from numpy.typing import ArrayLike, NDArray
from scipy.interpolate import CubicSpline, PchipInterpolator

from navsim.io import PROJECT_PATH


def load_sample_trajectory(
    trajectory_name: str,
) -> tuple[
    NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]
]:
    # load sample trajectory file
    file_path = PROJECT_PATH / "trajectories" / trajectory_name
    data = np.loadtxt(fname=file_path.with_suffix(".csv"), delimiter=",", skiprows=1)

    # extract relevant data
    timeseries = data[:, 3] - data[0, 3]  # [s]
    lat = data[:, 0]  # [deg]
    lon = data[:, 1]  # [deg]
    alt = data[:, 2]  # [m]

    return timeseries, lat, lon, alt


def translate_trajectory(
    lat: ArrayLike,
    lon: ArrayLike,
    alt: ArrayLike,
    lat0: float,
    lon0: float,
    alt0: float,
    deg: bool = False,
) -> GEODETIC:
    enu = geodetic2enu(
        lat=lat, lon=lon, alt=alt, lat0=lat[0], lon0=lon[0], alt0=alt[0], deg=deg
    )

    lla = enu2geodetic(
        east=enu.east,
        north=enu.north,
        up=enu.up,
        lat0=lat0,
        lon0=lon0,
        alt0=alt0,
        deg=deg,
    )

    return lla


def interpolate_trajectory(
    time: ArrayLike,
    lat: ArrayLike,
    lon: ArrayLike,
    alt: ArrayLike,
    new_time: ArrayLike,
    include_accel: bool = False,
    deg: bool = False,
) -> tuple[ECEF, ECEF] | tuple[ECEF, ECEF, ECEF]:
    ecef_pos = np.array(geodetic2ecef(lat=lat, lon=lon, alt=alt, deg=deg)).transpose()

    if include_accel:
        cs = CubicSpline(x=time, y=ecef_pos, extrapolate=False)
        pos = cs(new_time).transpose()
        vel = cs(new_time, 1).transpose()
        accel = cs(new_time, 2).transpose()

        return (
            ECEF(x=pos[0], y=pos[1], z=pos[2]),
            ECEF(x=vel[0], y=vel[1], z=vel[2]),
            ECEF(x=accel[0], y=accel[1], z=accel[2]),
        )

    else:
        pchip = PchipInterpolator(x=time, y=ecef_pos, extrapolate=False)
        pos = pchip(new_time).transpose()
        vel = pchip(new_time, 1).transpose()

        return ECEF(x=pos[0], y=pos[1], z=pos[2]), ECEF(x=vel[0], y=vel[1], z=vel[2])
