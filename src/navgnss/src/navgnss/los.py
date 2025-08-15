import numpy as np
from navtools.conversions import ecef2enu, ecef2geodetic
from navtools.utils import to_cartesian_series
from numpy.typing import ArrayLike, NDArray


def compute_visibility(
    rx_pos: np.array, emitter_pos: np.array, mask_angle: float = 10.0
) -> tuple[bool, float, float]:
    emitter_az, emitter_el = compute_az_and_el(rx_pos=rx_pos, emitter_pos=emitter_pos)
    is_visible = np.degrees(emitter_el) >= mask_angle

    return is_visible, emitter_az, emitter_el


def compute_az_and_el(rx_pos: np.array, emitter_pos: np.array) -> tuple[float, float]:
    # ensure cartestian series (T, 3)
    rx_pos = to_cartesian_series(array=rx_pos)
    emitter_pos = to_cartesian_series(array=emitter_pos)

    range, _ = compute_range_and_uv(rx_pos=rx_pos, emitter_pos=emitter_pos)
    lla = ecef2geodetic(x=rx_pos[:, 0], y=rx_pos[:, 1], z=rx_pos[:, 2])
    enu = ecef2enu(
        x=emitter_pos[:, 0],
        y=emitter_pos[:, 1],
        z=emitter_pos[:, 2],
        lat0=lla.lat,
        lon0=lla.lon,
        alt0=lla.alt,
    )
    el = np.arcsin(enu.up / range)
    az = np.arctan2(enu.east, enu.north)

    return az, el


def compute_range(rx_pos: NDArray, emitter_pos: NDArray):
    rx_pos = to_cartesian_series(array=rx_pos)
    emitter_pos = to_cartesian_series(array=emitter_pos)

    pos_rx_emitter = rx_pos - emitter_pos  # position relative to emitter

    range = np.linalg.norm(pos_rx_emitter, axis=1)

    return range


def compute_range_and_uv(
    rx_pos: np.array, emitter_pos: np.array
) -> tuple[float, np.array]:
    # ensure cartestian series (T, 3)
    rx_pos = to_cartesian_series(array=rx_pos)
    emitter_pos = to_cartesian_series(array=emitter_pos)

    pos_rx_emitter = rx_pos - emitter_pos  # position relative to emitter

    range = np.sqrt(np.sum(pos_rx_emitter**2, axis=-1))
    unit_vector = pos_rx_emitter.T / range

    return range, unit_vector


def compute_range_rate(
    rx_vel: np.array, emitter_vel: np.array, unit_vector: np.array
) -> float:
    rx_vel = to_cartesian_series(array=rx_vel)
    emitter_vel = to_cartesian_series(array=emitter_vel)
    unit_vector = to_cartesian_series(array=unit_vector)

    vel_rx_emitter = rx_vel - emitter_vel  # velocity relative to emitter
    range_rate = np.sum(vel_rx_emitter * unit_vector, axis=-1)

    return range_rate
