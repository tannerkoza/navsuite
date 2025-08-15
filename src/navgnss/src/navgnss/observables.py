from dataclasses import dataclass, fields, replace

import numpy as np
from aspn23_lcm import measurement_satnav_with_sv_data
from navtools.constants import SPEED_OF_LIGHT
from numpy.typing import NDArray


@dataclass
class Observables:
    system: NDArray
    prn: NDArray
    signal: NDArray
    pranges: NDArray[np.float128]
    prange_sigmas: NDArray[np.float128]
    prange_rates: NDArray[np.float128]
    prange_rate_sigmas: NDArray[np.float128]
    cn0: NDArray[np.float128]
    sv_pos: NDArray[np.float128]
    sv_vel: NDArray[np.float128]

    def apply_indices(self, indices: NDArray):
        for field in fields(self):
            arr = getattr(self, field.name)

            if isinstance(arr, np.ndarray):
                setattr(self, field.name, arr[indices])

        return self


def aspn2observables(satnav_msg: measurement_satnav_with_sv_data):
    systems = []
    prns = []
    signals = []
    pranges = []
    prange_sigmas = []
    prange_rates = []
    prange_rate_sigmas = []
    cn0 = []
    sv_pos = []
    sv_vel = []

    for obs, sv_data in zip(satnav_msg.obs, satnav_msg.sv_data):
        systems.append(obs.satellite_system)
        prns.append(obs.prn)
        signals.append(obs.signal_descriptor)

        # unpack observables
        pranges.append(obs.pseudorange)
        prange_sigmas.append(np.sqrt(obs.pseudorange_variance))

        # convert ASPN pseudorange rates to actual pseudorange rates
        if obs.pseudorange_rate_type == obs.PSEUDORANGE_RATE_TYPE_PSR_RATE_DOPPLER:
            prange_rate = obs.pseudorange_rate / -(obs.frequency / SPEED_OF_LIGHT)
            prange_rate_sigma = np.sqrt(obs.pseudorange_rate_variance) / -(
                obs.frequency / SPEED_OF_LIGHT
            )

        prange_rates.append(prange_rate)
        prange_rate_sigmas.append(prange_rate_sigma)

        cn0.append(obs.c_n0)

        # unpack satellite states
        sv_pos.append(sv_data.sv_pos)
        sv_vel.append(sv_data.sv_vel)

    return Observables(
        system=np.array(systems),
        prn=np.array(prns),
        signal=np.array(signals),
        pranges=np.array(pranges),
        prange_sigmas=np.array(prange_sigmas),
        prange_rates=np.array(prange_rates),
        prange_rate_sigmas=np.array(prange_rate_sigmas),
        cn0=np.array(cn0),
        sv_pos=np.array(sv_pos),
        sv_vel=np.array(sv_vel),
    )


class ObservablePreprocessor:
    def __init__(self, raw_observables: Observables):
        self._raw_observables = raw_observables

    @property
    def filtered_observables(self):
        return self._filtered_observables

    def filter_by_system(self, systems: list[str]):
        observables = self._check_for_filtered_observables()

        # gather available systems in most current observables
        available_systems: NDArray = np.array(
            [
                signal.casefold() if isinstance(signal, str) else signal
                for signal in observables.system
            ]
        )

        # create mask of observables to include
        systems_masks: list[NDArray] = [
            (
                available_systems == desired_signal.casefold()
                if isinstance(desired_signal, str)
                else available_systems == desired_signal
            )
            for desired_signal in systems
        ]

        valid_mask = np.logical_or.reduce(systems_masks)

        if valid_mask.sum() == 0:
            raise RuntimeError(
                f"No requested systems ({systems}) are availble in the filtered observables."
            )

        self._filtered_observables = observables.apply_indices(indices=valid_mask)

    def filter_by_signal(self, signals: list[str]):
        observables = self._check_for_filtered_observables()

        # gather available signals in most current observables
        available_signals: NDArray = np.array(
            [
                signal.casefold() if isinstance(signal, str) else signal
                for signal in observables.signal
            ]
        )

        # create mask of observables to include
        signal_masks: list[NDArray] = [
            (
                available_signals == desired_signal.casefold()
                if isinstance(desired_signal, str)
                else available_signals == desired_signal
            )
            for desired_signal in signals
        ]

        valid_mask = np.logical_or.reduce(signal_masks)

        if valid_mask.sum() == 0:
            raise RuntimeError(
                f"No requested signals ({signals}) are availble in the filtered observables."
            )

        self._filtered_observables = observables.apply_mask(mask=valid_mask)

    def _check_for_filtered_observables(self):
        if hasattr(self, "_filtered_observables"):
            return replace(self._filtered_observables)
        else:
            return replace(self._raw_observables)
