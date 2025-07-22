import datetime as dt

import lcm
import numpy as np
from aspn23 import (
    MeasurementNavsimSatnavWithSvData,
    MeasurementPosition,
    MeasurementPositionErrorModel,
    MeasurementPositionReferenceFrame,
    MeasurementVelocity,
    MeasurementVelocityErrorModel,
    MeasurementVelocityReferenceFrame,
    TypeHeader,
    TypeNavsimSatnavObs,
    TypeSatnavObsIonoCorrectionSource,
    TypeSatnavObsPseudorangeRateType,
    TypeSatnavSvData,
    TypeSatnavSvDataCoordinateFrame,
    TypeSatnavSvDataEphemerisType,
    TypeSatnavSvDataGroupDelayEnum,
    TypeSatnavTime,
    TypeSatnavTimeTimeReference,
    TypeTimestamp,
)
from aspn23_lcm import (
    measurement_navsim_satnav_with_sv_data_to_lcm,
    measurement_position_to_lcm,
    measurement_velocity_to_lcm,
)
from navgnss.los import compute_range_and_uv, compute_range_rate, compute_visibility
from navgnss.signals import SATELLITE_SIGNALS
from navtools.constants import EARTH_RATE, SPEED_OF_LIGHT
from navtools.conversions import datetime2gps, ecef2geodetic
from numpy.typing import ArrayLike
from tqdm import tqdm

from navsim.channel import (
    compute_carrier_to_noise,
    compute_klobuchar_delay,
    compute_saastamoinen_delay,
)
from navsim.clock import NAVIGATION_CLOCKS, compute_clock_states
from navsim.emitters import SatelliteEmitters
from navsim.rx import compute_dll_sigma, compute_fll_sigma, compute_pll_sigma
from navsim.simulations import MeasurementConfiguration


class MeasurementSimulation:
    LOOKAHEAD_INTERVAL = 30  # [s]

    def __init__(
        self, config: MeasurementConfiguration, output_path: str | None = None
    ):
        self._initialize(config=config)

        if output_path:
            self._log = lcm.EventLog(path=output_path, mode="w", overwrite=True)

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
        self._prepare_input_states(
            datetimes=utc_timestamps,
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
        initial_ts = self._timestamps[0][0]
        niterations = len(self._datetimes)

        with tqdm(total=niterations) as progress_bar:
            for block in range(niterations):
                datetimes = self._datetimes[block]
                timestamps = self._timestamps[block]
                sim_time = timestamps.max() - initial_ts

                rx_pos = np.array(self._rx_pos[block])
                rx_vel = np.array(self._rx_vel[block])
                rx_cb = np.array(self._rx_cb[block])
                rx_cd = np.array(self._rx_cd[block])

                lla_rx_pos = ecef2geodetic(
                    x=rx_pos[:, 0], y=rx_pos[:, 1], z=rx_pos[:, 2]
                )

                # compute emitter states at receive time
                emitters = self._emitters.process(utc_timestamps=datetimes)

                # create aspn headers
                aspn_headers = create_aspn_headers(timestamps=timestamps, block=block)

                # create aspn timestamps
                aspn_timestamps = [
                    TypeTimestamp(elapsed_nsec=int(ts)) for ts in timestamps * 1e9
                ]

                # create aspn satnav times
                _, week_number, seconds_of_week = datetime2gps(datetime=datetimes)
                aspn_satnav_times = [
                    TypeSatnavTime(
                        week_number=week,
                        seconds_of_week=secs,
                        time_reference=TypeSatnavTimeTimeReference(value=0),
                    )
                    for week, secs in zip(week_number, seconds_of_week)
                ]

                emitter_data = {}

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

                    # sv time errors (not currently modeled)
                    emitter_cb = np.zeros_like(timestamps)
                    emitter_cd = np.zeros_like(timestamps)

                    constellation = self._get_emitter_constellation(
                        emitter_id=emitter_id
                    )
                    signals = self._signals[constellation]

                    # package emitter data
                    system = self._get_emitter_constellation(emitter_id=emitter_id)
                    satnav_sv_data = create_aspn_satnav_sv_data(
                        timestamps=timestamps,
                        prn=emitter_id,
                        system=system,
                        sv_data_time=aspn_satnav_times,
                        sv_pos=emitter_pos_rx,
                        sv_vel=emitter_vel_rx,
                        sv_clock_bias=emitter_cb,
                        sv_clock_drift=emitter_cd,
                    )

                    # filter by view status
                    satnav_sv_data[view_status == False] = None

                    for signal_name, signal in signals.items():
                        # compute channel errors
                        iono_delays, iono_drifts, tropo_delays, tropo_drifts = (
                            self._compute_atmosphere_errors(
                                timestamps=datetimes,
                                rx_pos=rx_pos,
                                az=az,
                                el=el,
                                fcarrier=signal.fcarrier,
                            )
                        )

                        # compute signal power and resulting measurement noise
                        cn0 = compute_carrier_to_noise(
                            range=los_range,
                            transmit_eirp=self._transmit_eirps[constellation],
                            fcarrier=signal.fcarrier,
                            cn0_attenuation=self._cn0_attenuations[constellation],
                        )
                        cn0 -= self._cn0_attenuations[constellation]

                        (
                            dll_sigma,
                            dll_noise,
                            fll_sigma,
                            fll_noise,
                            pll_sigma,
                            pll_noise,
                        ) = self._compute_rx_noise(cn0=cn0, fcarrier=signal.fcarrier)

                        # compute pseudorange
                        prange = (
                            los_range
                            + iono_delays
                            + tropo_delays
                            + rx_cb
                            - emitter_cb
                            + dll_noise
                        )

                        # compute doppler
                        noiseless_prange_rate = (
                            los_range_rate
                            - iono_drifts
                            + tropo_drifts
                            + rx_cd
                            - emitter_cd
                        )
                        prange_rate = noiseless_prange_rate + fll_noise
                        doppler = -prange_rate * signal.fcarrier / SPEED_OF_LIGHT

                        # compute carrier phase
                        # #TODO: figure out timing and correct calculation
                        noiseless_doppler = (
                            -noiseless_prange_rate * signal.fcarrier / SPEED_OF_LIGHT
                        )
                        carrier_phase = np.cumsum(noiseless_doppler) + pll_noise
                        lock_count = np.arange(0, carrier_phase.size)

                        satnav_obs = create_aspn_satnav_obs(
                            timestamps=timestamps,
                            satellite_system=system,
                            signal_descriptor=signal_name,
                            prn=emitter_id,
                            frequency=signal.fcarrier,
                            pseudorange=prange,
                            pseudorange_variance=dll_sigma**2,
                            pseudorange_rate=doppler,
                            pseudorange_rate_variance=fll_sigma**2,
                            carrier_phase=carrier_phase,
                            carrier_phase_variance=pll_sigma**2,
                            c_n0=cn0,
                            lock_count=lock_count,
                            iono_correction_applied=np.logical_not(self._ionosphere),
                            tropo_correction_applied=np.logical_not(self._troposphere),
                        )

                        # filter by view status
                        satnav_obs[view_status == False] = None

                        emitter_data[emitter_id] = {
                            signal_name: (satnav_obs, satnav_sv_data)
                        }

                # Using the generator
                measurements = []
                position = []
                velocity = []
                for idx in range(timestamps.size):
                    epoch_data = list(create_measurement_epochs(emitter_data, idx))

                    if epoch_data:
                        epoch_obs, epoch_sv_data = zip(*epoch_data)

                        num_signal_types = np.unique(
                            np.array([obs.signal_descriptor for obs in epoch_obs])
                        ).size
                        measurement = MeasurementNavsimSatnavWithSvData(
                            header=aspn_headers[idx],
                            time_of_validity=aspn_timestamps[idx],
                            receiver_clock_time=aspn_satnav_times[idx],
                            num_signal_types=num_signal_types,
                            obs=list(epoch_obs),
                            sv_data=list(epoch_sv_data),
                            integrity=[],
                        )

                        pos = MeasurementPosition(
                            header=aspn_headers[idx],
                            time_of_validity=aspn_timestamps[idx],
                            reference_frame=MeasurementPositionReferenceFrame(value=0),
                            term1=lla_rx_pos.lat[idx],
                            term2=lla_rx_pos.lon[idx],
                            term3=lla_rx_pos.alt[idx],
                            covariance=np.zeros((3, 3)),
                            error_model=MeasurementPositionErrorModel(value=0),
                            error_model_params=np.zeros(1),
                            integrity=[],
                        )

                        vel = MeasurementVelocity(
                            header=aspn_headers[idx],
                            time_of_validity=aspn_timestamps[idx],
                            reference_frame=MeasurementVelocityReferenceFrame(value=1),
                            x=rx_vel[idx, 0],
                            y=rx_vel[idx, 1],
                            z=rx_vel[idx, 2],
                            covariance=np.zeros((3, 3)),
                            error_model=MeasurementVelocityErrorModel(value=0),
                            error_model_params=np.zeros(1),
                            integrity=[],
                        )

                        measurements.append(measurement)
                        position.append(pos)
                        velocity.append(vel)

                satnav_channel = "aspn23://navsim/measurement_satnav_with_sv_data"
                true_rx_pos_channel = "aspn23://navsim/true_measurement_position"
                true_rx_vel_channel = "aspn23://navsim/true_measurement_velocity"

                for idx in range(timestamps.size):
                    satnav = measurements[idx]
                    pos = position[idx]
                    vel = velocity[idx]

                    utime = int(satnav.time_of_validity.elapsed_nsec * 1e-3)

                    satnav_msg = measurement_navsim_satnav_with_sv_data_to_lcm(
                        old=satnav
                    )
                    pos_msg = measurement_position_to_lcm(old=pos)
                    vel_msg = measurement_velocity_to_lcm(old=vel)

                    self._log.write_event(
                        utime=utime, channel=satnav_channel, data=satnav_msg.encode()
                    )
                    self._log.write_event(
                        utime=utime, channel=true_rx_pos_channel, data=pos_msg.encode()
                    )
                    self._log.write_event(
                        utime=utime, channel=true_rx_vel_channel, data=vel_msg.encode()
                    )

                progress_bar.desc = (
                    f"Simulating Measurements (Sim. Time: {sim_time:.3f} [s])"
                )
                progress_bar.update()

    def _initialize(self, config: MeasurementConfiguration):
        # assign non-constellation values
        self._ionosphere = config.ionosphere
        self._troposphere = config.troposphere
        self._rx_noise = config.rx_noise
        self._rx_clock = NAVIGATION_CLOCKS[config.rx_clock_type.casefold()]

        # assing constellation specific
        self._mask_angles = {}
        self._eph_names = {}
        self._signals = {}
        self._transmit_eirps = {}
        self._cn0_attenuations = {}

        for constellation in config.constellation:
            c = constellation.reference_constellation

            self._mask_angles[c] = constellation.mask_angle
            self._eph_names[c] = SatelliteEmitters.SUPPORTED_CONSTELLATIONS[c].eph_name
            self._signals[c] = {
                s.upper(): SATELLITE_SIGNALS[s.upper()] for s in constellation.signals
            }
            self._transmit_eirps[c] = constellation.transmit_eirp
            self._cn0_attenuations[c] = constellation.cn0_attenuation

        constellations = list(self._eph_names.keys())
        self._emitters = SatelliteEmitters(
            constellations=constellations, disable_warnings=True
        )

    def _prepare_input_states(
        self,
        datetimes: ArrayLike,
        rx_pos: ArrayLike,
        rx_vel: ArrayLike,
        rx_cb: ArrayLike,
        rx_cd: ArrayLike,
    ):
        # create new input states
        timestamps = np.array([d.timestamp() for d in datetimes])

        # partition input states
        self._datetimes = _partition_timeseries(timeseries=datetimes)
        self._timestamps = _partition_timeseries(timeseries=timestamps)
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

    def _compute_atmosphere_errors(
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

    def _compute_rx_noise(self, cn0: ArrayLike, fcarrier: float):
        if self._rx_noise:
            dll_sigma = compute_dll_sigma(cn0=cn0)
            fll_sigma = compute_fll_sigma(cn0=cn0, fcarrier=fcarrier)
            pll_sigma = compute_pll_sigma(cn0=cn0)

            dll_noise = dll_sigma * np.random.randn()
            fll_noise = fll_sigma * np.random.randn()
            pll_noise = pll_sigma * np.random.randn()

        else:
            dll_sigma = np.zeros_like(cn0)
            fll_sigma = np.zeros_like(cn0)
            pll_sigma = np.zeros_like(cn0)
            dll_noise = np.zeros_like(cn0)
            fll_noise = np.zeros_like(cn0)
            pll_noise = np.zeros_like(cn0)

        return dll_sigma, dll_noise, fll_sigma, fll_noise, pll_sigma, pll_noise

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


def create_aspn_headers(timestamps: ArrayLike, block: int):
    headers = []

    vendor_id = 0
    device_id = 0
    context_id = 0

    for idx in range(timestamps.size):
        sequence_id = block * timestamps.size + idx
        headers.append(
            TypeHeader(
                vendor_id=vendor_id,
                device_id=device_id,
                context_id=context_id,
                sequence_id=sequence_id,
            )
        )

    return np.array(headers)


def create_aspn_satnav_sv_data(
    timestamps: ArrayLike,
    prn: str,
    system: str,
    sv_data_time: list[TypeSatnavTime],
    sv_pos: ArrayLike,
    sv_vel: ArrayLike,
    sv_clock_bias: ArrayLike,
    sv_clock_drift: ArrayLike,
):
    satnav_sv_data = []

    for idx in range(timestamps.size):
        satnav_sv_data.append(
            TypeSatnavSvData(
                prn=prn,
                satellite_system=system,
                ephemeris_type=TypeSatnavSvDataEphemerisType(value=0),
                sv_data_time=sv_data_time[idx],
                coordinate_frame=TypeSatnavSvDataCoordinateFrame(value=1),
                sv_pos=sv_pos[idx],
                sv_vel=sv_vel[idx],
                sv_clock_bias=sv_clock_bias[idx],
                sv_clock_drift=sv_clock_drift[idx],
                group_delay_enum=TypeSatnavSvDataGroupDelayEnum(value=0),
                group_delay_vector=np.zeros(4),
            )
        )

    return np.array(satnav_sv_data)


def create_aspn_satnav_obs(
    timestamps: ArrayLike,
    satellite_system: str,
    signal_descriptor: str,
    prn: str,
    frequency: float,
    pseudorange: ArrayLike,
    pseudorange_variance: ArrayLike,
    pseudorange_rate: ArrayLike,
    pseudorange_rate_variance: ArrayLike,
    carrier_phase: ArrayLike,
    carrier_phase_variance: ArrayLike,
    c_n0: ArrayLike,
    lock_count: ArrayLike,
    iono_correction_applied: bool,
    tropo_correction_applied: bool,
):
    satnav_satnav_obs = []

    for idx in range(timestamps.size):
        satnav_satnav_obs.append(
            TypeNavsimSatnavObs(
                satellite_system=satellite_system,
                signal_descriptor=signal_descriptor,
                prn=prn,
                frequency=frequency,
                pseudorange=pseudorange[idx],
                pseudorange_variance=pseudorange_variance[idx],
                pseudorange_rate_type=TypeSatnavObsPseudorangeRateType(value=0),
                pseudorange_rate=pseudorange_rate[idx],
                pseudorange_rate_variance=pseudorange_rate_variance[idx],
                carrier_phase=carrier_phase[idx],
                carrier_phase_variance=carrier_phase_variance[idx],
                c_n0=c_n0[idx],
                lock_count=lock_count[idx],
                iono_correction_applied=iono_correction_applied,
                iono_correction_source=TypeSatnavObsIonoCorrectionSource(value=1),
                tropo_correction_applied=tropo_correction_applied,
                signal_bias_correction_applied=True,
                integrity=[],
            )
        )

    return np.array(satnav_satnav_obs)


def create_measurement_epochs(emitter_data, idx):
    """Generator that yields valid signal pairs for a given epoch"""
    for emitter in emitter_data.values():
        for signal in emitter.values():
            observables, sv_data_array = signal[0], signal[1]

            # Check if epoch index is valid for both arrays
            if idx >= len(observables) or idx >= len(sv_data_array):
                continue

            # Extract values for this epoch
            obs = observables[idx]
            sv_data = sv_data_array[idx]

            # Only yield if both values are valid
            if obs is not None and sv_data is not None:
                yield obs, sv_data
