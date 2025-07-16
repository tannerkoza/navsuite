import datetime as dt

import numpy as np
from astropy.time import Time
from navgnss.los import compute_range_and_uv, compute_range_rate, compute_visibility
from navtools.constants import EARTH_RATE, SPEED_OF_LIGHT
from numpy.typing import ArrayLike
from tqdm import tqdm

from navsim.emitters import SatelliteEmitters


class MeasurementSimulation:
    LOOKAHEAD_INTERVAL = 30  # [s]

    def __init__(self, constellations: list[str], mask_angles: list[float]):
        self._constellations = constellations
        self._mask_angles = {
            constellation: angle
            for constellation, angle in zip(constellations, mask_angles)
        }

        self._emitters = SatelliteEmitters(
            constellations=constellations, disable_warnings=True
        )

    def simulate(
        self,
        utc_timestamps: dt.datetime | list[dt.datetime],
        rx_pos: ArrayLike,
        rx_vel: ArrayLike,
    ):
        # ensure timestamps are list[dt.datetime] and chunk
        utc_timestamps if isinstance(utc_timestamps, list) else [utc_timestamps]
        timestamp_chunks = _chunk_timeseries(utc_timestamps)
        rx_pos_chunks = _chunk_timeseries(timeseries=rx_pos.tolist())
        rx_vel_chunks = _chunk_timeseries(timeseries=rx_vel.tolist())

        self._lookahead(timestamps=utc_timestamps, rx_pos=rx_pos)

        with tqdm(total=len(timestamp_chunks)) as progress_bar:
            for chunk_idx, time_chunk in enumerate(timestamp_chunks):
                rx_pos_chunk = np.array(rx_pos_chunks[chunk_idx])
                rx_vel_chunk = np.array(rx_vel_chunks[chunk_idx])

                emitters = self._emitters.process(utc_timestamps=time_chunk)

                for emitter_id, (rx_emitter_pos, rx_emitter_vel) in emitters.items():
                    tx_emitter_pos, tx_emitter_vel = self._apply_sagnac(
                        rx_pos=rx_pos_chunk,
                        emitter_pos=rx_emitter_pos,
                        emitter_vel=rx_emitter_vel,
                    )
                    range, range_rate = self._compute_los_states(
                        rx_pos=rx_pos_chunk,
                        rx_vel=rx_vel_chunk,
                        emitter_pos=tx_emitter_pos,
                        emitter_vel=tx_emitter_vel,
                    )

                    status, az, el = self._compute_visibility(
                        emitter_id=emitter_id,
                        rx_pos=rx_pos_chunk,
                        emitter_pos=tx_emitter_pos,
                    )

                elapsed_time = _generate_elapsed_time(
                    now=time_chunk[-1], start_time=utc_timestamps[0]
                )
                progress_bar.set_description(f"Simulation Time - {elapsed_time} [s]")
                progress_bar.update()

    def _compute_los_states(
        self,
        rx_pos: ArrayLike,
        rx_vel: ArrayLike,
        emitter_pos: ArrayLike,
        emitter_vel: ArrayLike,
    ):
        range, uv = compute_range_and_uv(rx_pos=rx_pos, emitter_pos=emitter_pos)
        range_rate = compute_range_rate(
            rx_vel=rx_vel, emitter_vel=emitter_vel, unit_vector=uv
        )

        return range, range_rate

    def _apply_sagnac(
        self, rx_pos: ArrayLike, emitter_pos: ArrayLike, emitter_vel: ArrayLike
    ):
        range, _ = compute_range_and_uv(rx_pos=rx_pos, emitter_pos=emitter_pos)

        omega = EARTH_RATE * range / SPEED_OF_LIGHT

        R = np.zeros((omega.size, 3, 3))

        R[:, 0, 0] = 1
        R[:, 0, 1] = omega
        R[:, 1, 0] = -omega
        R[:, 1, 1] = 1
        R[:, 2, 2] = 1

        tx_emitter_pos = np.einsum("ijk,ik->ij", R, emitter_pos)
        tx_emitter_vel = np.einsum("ijk,ik->ij", R, emitter_vel)

        return tx_emitter_pos, tx_emitter_vel

    def _lookahead(self, timestamps: list[dt.datetime], rx_pos: ArrayLike):
        timestamps = np.array(timestamps)
        duration = timestamps.max() - timestamps.min()

        # build lookahead criteria
        has_tle_constellations = len(self._emitters.tle_constellations) > 0
        duration_exceeds_lookahead = (
            duration.seconds > MeasurementSimulation.LOOKAHEAD_INTERVAL
        )

        if has_tle_constellations and duration_exceeds_lookahead:
            elapsed_time = timestamps - timestamps[0]
            elapsed_sec = elapsed_time.astype("timedelta64[s]").astype(float)
            elapsed_remainder = elapsed_sec % MeasurementSimulation.LOOKAHEAD_INTERVAL

            lookahead_idx = _find_local_minima(array=elapsed_remainder)

            timestamps = timestamps[lookahead_idx]
            rx_pos = rx_pos[lookahead_idx]

            emitters = self._emitters.process(utc_timestamps=timestamps)
            self._filter_emitters(emitters=emitters, rx_pos=rx_pos)

    def _compute_visibility(
        self, emitter_id: str, rx_pos: ArrayLike, emitter_pos: ArrayLike
    ):
        eph_names = {
            SatelliteEmitters.SUPPORTED_CONSTELLATIONS[c].eph_name: c
            for c in self._constellations
        }

        # determine constellation mask angle
        constellation = next(
            (eph_names[name] for name in eph_names if emitter_id.startswith(name))
        )
        mask_angle = self._mask_angles[constellation]

        # determine visibility
        status, az, el = compute_visibility(
            rx_pos=rx_pos,
            emitter_pos=emitter_pos,
            mask_angle=mask_angle,
        )

        return status, az, el

    def _filter_emitters(self, emitters: dict, rx_pos: ArrayLike):
        timesteps_visible = []
        emitter_ids = []

        for emitter_id, (emitter_pos, _) in emitters.items():
            status, _, _ = self._compute_visibility(
                emitter_id=emitter_id, rx_pos=rx_pos, emitter_pos=emitter_pos
            )

            timesteps_visible.append(status.sum())
            emitter_ids.append(emitter_id)

        timesteps_visible = np.array(timesteps_visible)
        emitter_ids = np.array(emitter_ids)

        removal_mask = timesteps_visible == 0
        emitters_to_remove = emitter_ids[removal_mask]

        self._emitters.remove_emitters(emitter_id=emitters_to_remove)


def _chunk_timeseries(timeseries, chunk_size=512):
    return [
        timeseries[i : i + chunk_size] for i in range(0, len(timeseries), chunk_size)
    ]


def _generate_elapsed_time(now: dt.datetime, start_time: dt.datetime):
    elapsed_time = now - start_time
    elapsed_sec = elapsed_time.total_seconds()

    formatted_time = f"{int(elapsed_sec):02}"

    return formatted_time


def _find_local_minima(array: ArrayLike):
    previous = array[:-2]
    current = array[1:-1]
    following = array[2:]

    middle_mask = (current < previous) & (current < following)
    middle_indices = np.where(middle_mask)[0] + 1  # +1 for correct index shift

    start_min = array[0] < array[1]
    end_min = array[-1] < array[-2]

    all_minima = []

    if start_min:
        all_minima.append(0)

    all_minima.extend(middle_indices.tolist())

    if end_min:
        all_minima.append(array.size - 1)

    return np.array(all_minima)
