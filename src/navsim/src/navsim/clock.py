from dataclasses import dataclass

import numpy as np
from navtools.constants import SPEED_OF_LIGHT


@dataclass()
class NavigationClock:
    """dataclass of navigation clock Allan variance values"""

    h0: float
    h1: float
    h2: float


LOW_QUALITY_TCXO = NavigationClock(h0=2e-19, h1=7e-21, h2=2e-20)
HIGH_QUALITY_TCXO = NavigationClock(h0=2e-21, h1=1e-22, h2=2e-20)
OCXO = NavigationClock(h0=2e-25, h1=7e-25, h2=6e-25)
RUBIDIUM = NavigationClock(h0=2e-22, h1=4.5e-26, h2=1e-30)
CESIUM = NavigationClock(h0=2e-22, h1=5e-27, h2=1.5e-33)
NAVIGATION_CLOCKS = {
    "low_quality_tcxo": LOW_QUALITY_TCXO,
    "high_quality_tcxo": HIGH_QUALITY_TCXO,
    "ocxo": OCXO,
    "rubidium": RUBIDIUM,
    "cesium": CESIUM,
}


def compute_clock_states(
    h0: float, h2: float, T: float, nperiods: int = 1
) -> tuple[np.array, np.array]:
    """computes clock bias and drift using two-state clock model for specified period and number of periods

    Parameters
    ----------
    h0 : float
    h2 : float
    T : float
        sampling period
    nperiods : int, optional
        number of total sampling periods, by default 1

    Returns
    -------
    tuple[np.array, np.array]
        clock bias and drift

    Reference
    -------
    L. Galleani, “A tutorial on the two-state model of the atomic clock noise,” Metrologia, vol. 45, no. 6, p. S175, Dec. 2008, doi: 10.1088/0026-1394/45/6/S23.
    """
    # two-state clock model white noise spectral amplitudes
    sf = h0 / 2
    sg = h2 * 2 * np.pi**2

    # error covariance noise
    covariance = np.array(
        [
            [sf * T + (1 / 3) * sg * T**3, (1 / 2) * sg * T**2],
            [(1 / 2) * sg * T**2, sg * T],
        ]
    )  # [s], [s/s]
    bias_noise, drift_noise = np.random.multivariate_normal(
        mean=[0, 0], cov=covariance, size=nperiods
    ).T

    drift_ss = np.cumsum(drift_noise)
    bias_s = np.cumsum(drift_ss * T) + np.cumsum(bias_noise)

    drift_ms = drift_ss * SPEED_OF_LIGHT
    bias_m = bias_s * SPEED_OF_LIGHT

    return bias_m, drift_ms
