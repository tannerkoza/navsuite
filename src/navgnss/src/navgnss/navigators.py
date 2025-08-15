from collections import Counter
from dataclasses import dataclass
from xml.etree.ElementInclude import include

import numpy as np
from navtools.constants import EARTH_RATE, SPEED_OF_LIGHT
from navtools.conversions.coordinates import ecef2geodetic, geodetic2ecef
from numpy.typing import NDArray

from navgnss.los import compute_range
from navgnss.observables import Observables


@dataclass
class WNLSConfiguration:
    reference_system: str
    is_weighted: str
    include_velocity: bool


class WNLS:
    CONVERGENCE_THRESHOLD = 0.0001

    def __init__(self, configuration: WNLSConfiguration):
        self._config = configuration

        self._systems = np.array([])

        self._rx_pos = np.array([])
        self._rx_cb = np.array([])
        self._rx_cd = np.array([])

    @property
    def position(self):
        return self._rx_pos

    @property
    def clock_bias(self):
        return self._rx_cb

    @property
    def velocity(self):
        return self._rx_vel

    @property
    def clock_drift(self):
        return self._rx_cd

    def update(self, observables: Observables):
        self._update_systems(systems=observables.system)

        # check if observables include reference system
        if not np.isin(self._config.reference_system, self._systems):
            print("Update not performed because reference system is unavailable.")
            return

        if not hasattr(self, "_rx_state"):
            self._initialize_estimate(sv_pos=observables.sv_pos)

        observables = self._sort_observables(observables=observables)

        converged = False
        while not converged:
            # compute predicted pseudoranges
            sv_pos_tx, sv_vel_tx = self._apply_sagnac_rotation(
                sv_pos=observables.sv_pos, sv_vel=observables.sv_vel
            )
            geometric_ranges = compute_range(rx_pos=self._rx_pos, emitter_pos=sv_pos_tx)
            clock_biases = np.repeat(self._rx_cb, self._obs_per_system)
            predicted_pranges = geometric_ranges + clock_biases

            # build observation model
            obs_model, uv = self._build_obs_model(
                sv_pos=sv_pos_tx,
                geometric_ranges=geometric_ranges,
                systems=observables.system,
            )

            # build weighting matrix
            weighting_model = self._build_weighting_model(
                cn0=observables.cn0, observable_sigma=observables.prange_sigmas
            )

            # estimate position and clock bias
            y = observables.pranges - predicted_pranges
            delta_pos_cb = compute_wnls_estimate(y=y, H=obs_model, W=weighting_model)

            corr_rx_pos = self._rx_pos + delta_pos_cb[:3]
            corr_rx_cb = self._rx_cb + delta_pos_cb[3:]

            # update convergence state
            pos_residual = np.linalg.norm(corr_rx_pos - self._rx_pos)
            converged = pos_residual < WNLS.CONVERGENCE_THRESHOLD

            # update position and clock bias
            self._rx_pos = corr_rx_pos
            self._rx_cb = corr_rx_cb

        if self._config.include_velocity:
            geometric_range_rates = np.einsum("ij,ij->i", -uv, sv_vel_tx)
            clock_drifts = np.repeat(self._rx_cd, self._obs_per_system)
            predicted_prange_rates = geometric_range_rates + clock_drifts
            y = observables.prange_rates - predicted_prange_rates
            weighting_model = self._build_weighting_model(
                cn0=observables.cn0, observable_sigma=observables.prange_rate_sigmas
            )

            vel_cd = compute_wnls_estimate(y=y, H=obs_model, W=weighting_model)

            # update velocity and clock drift
            self._rx_vel = vel_cd[:3]
            self._rx_cd = vel_cd[3:]

    def _build_weighting_model(self, cn0: NDArray, observable_sigma: NDArray):
        if self._config.is_weighted:
            norm_cn0 = cn0 / cn0.max()
            weights = (1 / observable_sigma**2) * norm_cn0

            weighting_model = np.diag(weights)
        else:
            weighting_model = np.eye(cn0.size)

        return weighting_model

    def _build_obs_model(
        self, sv_pos: NDArray, geometric_ranges: NDArray, systems: NDArray
    ):
        # compute unit vectors
        rel_rx_pos = self._rx_pos - sv_pos  # relative to each satellite
        uv = (
            rel_rx_pos / geometric_ranges[:, np.newaxis]
        )  # unit vector from satellite to rx pos

        # compute clock observation model columns
        clock_columns = np.ones((systems.size, 1))
        secondary_systems = self._systems[1:]

        for system in secondary_systems:
            system_mask = system == systems
            column = system_mask[:, np.newaxis].astype(int)
            clock_columns = np.hstack((clock_columns, column))

        H = np.hstack((uv, clock_columns))

        return H, uv

    def _apply_sagnac_rotation(self, sv_pos: NDArray, sv_vel: NDArray):
        geometric_ranges = compute_range(rx_pos=self._rx_pos, emitter_pos=sv_pos)

        omega = EARTH_RATE * geometric_ranges / SPEED_OF_LIGHT
        C = np.zeros((omega.size, 3, 3))

        C[:, 0, 0] = 1
        C[:, 0, 1] = omega
        C[:, 1, 0] = -omega
        C[:, 1, 1] = 1
        C[:, 2, 2] = 1

        sv_pos_tx = np.einsum("sij,sj->si", C, sv_pos)
        sv_vel_tx = np.einsum("sij,sj->si", C, sv_vel)

        return sv_pos_tx, sv_vel_tx

    def _initialize_estimate(self, sv_pos: NDArray):
        x, y, z = sv_pos.transpose()

        lla = ecef2geodetic(x=x, y=y, z=z)
        projected_sv_pos = np.array(
            geodetic2ecef(lat=lla.lat, lon=lla.lon, alt=np.zeros_like(lla.lat))
        )

        self._rx_pos = projected_sv_pos.mean(axis=1)

    def _sort_observables(self, observables: Observables):
        system_indices = {val: idx for idx, val in enumerate(self._systems)}
        obs_system_indices = np.array(
            [system_indices[item] for item in observables.system]
        )
        sorted_obs_indices = np.argsort(obs_system_indices)
        sorted_obs = observables.apply_indices(indices=sorted_obs_indices)

        return sorted_obs

    def _update_systems(self, systems: NDArray):
        unique_systems = np.unique(systems)

        if not self._config.reference_system in unique_systems.tolist():
            return

        # ensure reference system is first in systems
        reference_system_order = (
            unique_systems != self._config.reference_system
        ).astype(int)  # 0 for reference system, 1 for others
        alphabetical_order = np.argsort(unique_systems)
        sort_indices = np.lexsort([alphabetical_order, reference_system_order])

        sorted_systems = unique_systems[sort_indices]

        # add new systems
        new_system_mask = ~np.isin(sorted_systems, self._systems)
        self._systems = np.append(self._systems, sorted_systems[new_system_mask])
        self._obs_per_system = np.array(
            [(systems == system).sum() for system in self._systems]
        )

        # expand clock states if new systems
        nnew_systems = new_system_mask.sum()
        if nnew_systems > 0:
            new_clock_states = np.zeros(nnew_systems)
            self._rx_cb = np.append(self._rx_cb, new_clock_states)
            self._rx_cd = np.append(self._rx_cd, new_clock_states)


def compute_wnls_estimate(y: NDArray, H: NDArray, W: NDArray):
    states = np.linalg.pinv(H.T @ W @ H) @ H.T @ W @ y

    return states
