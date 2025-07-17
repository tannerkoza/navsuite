import datetime as dt

import numpy as np
from astropy.time import Time
from navgnss.los import compute_range_and_uv, compute_range_rate, compute_visibility
from navgnss.signals import SATELLITE_SIGNALS
from navtools.constants import EARTH_RATE, SPEED_OF_LIGHT
from navtools.conversions import ecef2geodetic, datetime2gps
from navsim.channel import compute_klobuchar_delay, compute_saastamoinen_delay
from navsim.clock import compute_clock_states, NAVIGATION_CLOCKS
from navsim.simulations import MeasurementConfiguration
from numpy.typing import ArrayLike
from collections import defaultdict
from tqdm import tqdm

from navsim.emitters import SatelliteEmitters


class MeasurementSimulation:
    LOOKAHEAD_INTERVAL = 30  # [s]

    def __init__(
        self,
        config: MeasurementConfiguration,
    ):
        self._initialize(config=config)

    def simulate(
        self,
        utc_timestamps: dt.datetime | list[dt.datetime],
        rx_pos: ArrayLike,
        rx_vel: ArrayLike,
    ):
        if not isinstance(utc_timestamps, list):
            utc_timestamps = list(utc_timestamps)

        # compute receiver clock bias and clock drift [m, m/s]
        rx_cb, rx_cd = self._compute_rx_clock(timestamps=utc_timestamps)

        # partition inputs states into blocks for segemented loop
        self._partition_input_states(
            timestamps=utc_timestamps,
            rx_pos=rx_pos,
            rx_vel=rx_vel,
            rx_cb=rx_cb,
            rx_cd=rx_cd,
        )

        # lookahead and remove out of view emitters to increase performance
        self._lookahead(timestamps=utc_timestamps, rx_pos=rx_pos)

        # generate measurements from emitter states
        return self._process()

    def _process(self):
        niterations = len(self._datetimes)
        with tqdm(total=niterations) as progress_bar:

            observables = defaultdict(list)
            emitter_data = defaultdict(list)

            for block in range(niterations):
                datetimes = self._datetimes[block]
                timestamps = np.array([d.timestamp() for d in datetimes])
                rx_pos = np.array(self._rx_pos[block])
                rx_vel = np.array(self._rx_vel[block])
                rx_cb = np.array(self._rx_cb[block])
                rx_cd = np.array(self._rx_cd[block])

                # compute emitter states at receive time
                emitters = self._emitters.process(utc_timestamps=datetimes)

                for emitter_id, (emitter_pos_rx, emitter_vel_rx) in emitters.items():
                    # compute emitter states at transmit time
                    emitter_pos_tx, emitter_vel_tx = self._apply_sagnac(
                        rx_pos=rx_pos,
                        emitter_pos=emitter_pos_rx,
                        emitter_vel=emitter_vel_rx,
                    )

                    # compute true line of sight states
                    los_range, los_range_rate = self._compute_los_states(
                        rx_pos=rx_pos,
                        rx_vel=rx_vel,
                        emitter_pos=emitter_pos_tx,
                        emitter_vel=emitter_vel_tx,
                    )

                    view_status, az, el = self._compute_visibility(
                        emitter_id=emitter_id,
                        rx_pos=rx_pos,
                        emitter_pos=emitter_pos_tx,
                    )

                    # ignore emitter if not in view during block
                    if view_status.sum() == 0:
                        continue

                    constellation = self._get_emitter_constellation(
                        emitter_id=emitter_id
                    )
                    signals = self._signals[constellation]

                    for name, signal in signals.items():
                        iono_delays, iono_drifts, tropo_delays, tropo_drifts = (
                            self._compute_channel_errors(
                                timestamps=datetimes,
                                rx_pos=rx_pos,
                                az=az,
                                el=el,
                                fcarrier=signal.fcarrier,
                            )
                        )

                        # build measurements
                        prange = los_range + iono_delays + tropo_delays + rx_cb
                        cp_prange = los_range - iono_delays + tropo_delays + rx_cb
                        prange_rate = (
                            los_range_rate + iono_drifts + tropo_drifts + rx_cd
                        )

                        # filter by view status
                        observables_id = f"{emitter_id} - {name}"
                        observables[observables_id].append(
                            (
                                timestamps[view_status],
                                prange[view_status],
                                cp_prange[view_status],
                                prange_rate[view_status],
                            )
                        )
                        emitter_data[emitter_id].append(
                            (
                                timestamps[view_status],
                                emitter_pos_rx[view_status],
                                emitter_vel_rx[view_status],
                            )
                        )

                progress_bar.update()

        return observables, emitter_data

    def _initialize(self, config: MeasurementConfiguration):
        # assign non-constellation values
        self._ionosphere = config.ionosphere
        self._troposphere = config.troposphere
        self._rx_clock = NAVIGATION_CLOCKS[config.rx_clock_type.casefold()]

        # assing constellation specific
        self._mask_angles = {}
        self._eph_names = {}
        self._signals = {}

        for constellation in config.constellation:
            c = constellation.reference_constellation

            self._mask_angles[c] = constellation.mask_angle
            self._eph_names[c] = SatelliteEmitters.SUPPORTED_CONSTELLATIONS[c].eph_name
            self._signals[c] = {
                s.upper(): SATELLITE_SIGNALS[s.upper()] for s in constellation.signals
            }

        constellations = list(self._eph_names.keys())
        self._emitters = SatelliteEmitters(
            constellations=constellations, disable_warnings=True
        )

    def _partition_input_states(
        self,
        timestamps: list,
        rx_pos: ArrayLike,
        rx_vel: ArrayLike,
        rx_cb: ArrayLike,
        rx_cd: ArrayLike,
    ):
        self._datetimes = _partition_timeseries(timeseries=timestamps)
        self._rx_pos = _partition_timeseries(timeseries=rx_pos.tolist())
        self._rx_vel = _partition_timeseries(timeseries=rx_vel.tolist())
        self._rx_cb = _partition_timeseries(timeseries=rx_cb.tolist())
        self._rx_cd = _partition_timeseries(timeseries=rx_cd.tolist())

    def _compute_rx_clock(self, timestamps: list):
        ntimestamps = len(timestamps)
        delta_timestamps = np.diff(timestamps)
        mean_time_step = np.mean(delta_timestamps).seconds

        clock_bias, clock_drift = compute_clock_states(
            h0=self._rx_clock.h0,
            h2=self._rx_clock.h2,
            T=mean_time_step,
            nperiods=ntimestamps,
        )

        return clock_bias, clock_drift

    def _compute_channel_errors(
        self,
        timestamps: list,
        rx_pos: ArrayLike,
        az: ArrayLike,
        el: ArrayLike,
        fcarrier: float,
    ):
        _, _, tow = datetime2gps(datetime=timestamps)

        if self._ionosphere:
            iono_delay = compute_klobuchar_delay(
                receiver_ecef=rx_pos.transpose(),
                azimuth_rad=az,
                elevation_rad=el,
                fcarrier=fcarrier,
                time_of_week_s=tow,
            )
            iono_drift = np.gradient(iono_delay, tow)

        else:
            iono_delay = np.zeros_like(tow)
            iono_drift = np.zeros_like(tow)

        if self._troposphere:
            tropo_delay = compute_saastamoinen_delay(rx_ecef=rx_pos, elevation_rad=el)
            tropo_drift = np.gradient(tropo_delay, tow)

        else:
            tropo_delay = np.zeros_like(tow)
            tropo_drift = np.zeros_like(tow)

        return iono_delay, iono_drift, tropo_delay, tropo_drift

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
        def smart_mmult(R, x):
            return (R @ x[..., :, None])[..., 0]

        range, _ = compute_range_and_uv(rx_pos=rx_pos, emitter_pos=emitter_pos)

        omega = EARTH_RATE * range / SPEED_OF_LIGHT

        R = np.zeros((omega.size, 3, 3))

        R[:, 0, 0] = 1
        R[:, 0, 1] = omega
        R[:, 1, 0] = -omega
        R[:, 1, 1] = 1
        R[:, 2, 2] = 1

        tx_emitter_pos = smart_mmult(R, emitter_pos)
        tx_emitter_vel = smart_mmult(R, emitter_vel)

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
        constellation = self._get_emitter_constellation(emitter_id=emitter_id)

        # determine constellation mask angle
        mask_angle = self._mask_angles[constellation]

        # determine visibility
        status, az, el = compute_visibility(
            rx_pos=rx_pos,
            emitter_pos=emitter_pos,
            mask_angle=mask_angle,
        )

        return status, az, el

    def _get_emitter_constellation(self, emitter_id: str):
        constellation = next(
            (
                c
                for c, eph_name in self._eph_names.items()
                if emitter_id.startswith(eph_name)
            )
        )

        return constellation

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


def _partition_timeseries(timeseries, chunk_size=512):
    return [
        timeseries[i : i + chunk_size] for i in range(0, len(timeseries), chunk_size)
    ]


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
