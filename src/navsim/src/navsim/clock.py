"""
Navigation Clock Module

This module provides tools for modeling and simulating navigation clock behavior
using Allan variance parameters and two-state clock models. It includes predefined
clock types commonly used in navigation systems and functions for generating
realistic clock noise.
"""

from dataclasses import dataclass

import numpy as np
from navtools.constants import SPEED_OF_LIGHT


@dataclass()
class NavigationClock:
    """
    Dataclass representing navigation clock Allan variance parameters.

    This class stores the Allan variance coefficients that characterize the
    noise behavior of different types of navigation clocks. The parameters
    h0, h1, and h2 correspond to white phase noise, flicker phase noise,
    and random walk phase noise respectively.

    Parameters
    ----------
    h0 : float
        White phase noise coefficient (units: s)
        Represents short-term stability characteristics
    h1 : float
        Flicker phase noise coefficient (units: dimensionless)
        Represents medium-term stability characteristics
    h2 : float
        Random walk phase noise coefficient (units: s^-1)
        Represents long-term stability characteristics

    Notes
    -----
    The Allan variance coefficients relate to the power spectral density
    of phase fluctuations according to:

    S_φ(f) = h_{-2}/f^2 + h_{-1}/f + h_0 + h_1*f + h_2*f^2

    where this class uses the convention that h0, h1, h2 correspond to
    the coefficients for f^0, f^1, and f^2 terms respectively.

    References
    ----------
    .. [1] IEEE Standard 1139-2008, "IEEE Standard Definitions of Physical
           Quantities for Fundamental Frequency and Time Metrology"
    """

    h0: float
    h1: float
    h2: float


# Predefined clock types with typical Allan variance parameters
LOW_QUALITY_TCXO = NavigationClock(h0=2e-19, h1=7e-21, h2=2e-20)
"""NavigationClock: Low quality Temperature Compensated Crystal Oscillator parameters"""

HIGH_QUALITY_TCXO = NavigationClock(h0=2e-21, h1=1e-22, h2=2e-20)
"""NavigationClock: High quality Temperature Compensated Crystal Oscillator parameters"""

OCXO = NavigationClock(h0=2e-25, h1=7e-25, h2=6e-25)
"""NavigationClock: Oven Controlled Crystal Oscillator parameters"""

RUBIDIUM = NavigationClock(h0=2e-22, h1=4.5e-26, h2=1e-30)
"""NavigationClock: Rubidium atomic clock parameters"""

CESIUM = NavigationClock(h0=2e-22, h1=5e-27, h2=1.5e-33)
"""NavigationClock: Cesium atomic clock parameters"""

NAVIGATION_CLOCKS = {
    "low_quality_tcxo": LOW_QUALITY_TCXO,
    "high_quality_tcxo": HIGH_QUALITY_TCXO,
    "ocxo": OCXO,
    "rubidium": RUBIDIUM,
    "cesium": CESIUM,
}
"""
dict
    Dictionary mapping clock type names to NavigationClock instances.
    
    Keys
    ----
    "low_quality_tcxo" : NavigationClock
        Low quality TCXO parameters
    "high_quality_tcxo" : NavigationClock
        High quality TCXO parameters  
    "ocxo" : NavigationClock
        OCXO parameters
    "rubidium" : NavigationClock
        Rubidium atomic clock parameters
    "cesium" : NavigationClock
        Cesium atomic clock parameters
"""


def compute_clock_states(
    h0: float, h2: float, T: float, nperiods: int = 1
) -> tuple[np.array, np.array]:
    """
    Compute clock bias and drift using two-state clock model.

    Generates realistic clock bias and drift time series using a two-state
    Markov model based on Allan variance parameters. The model accounts for
    white phase noise (h0) and random walk phase noise (h2) to simulate
    clock behavior over multiple time periods.

    Parameters
    ----------
    h0 : float
        White phase noise Allan variance coefficient (units: s)
        Represents the strength of white phase noise
    h2 : float
        Random walk phase noise Allan variance coefficient (units: s^-1)
        Represents the strength of random walk phase noise
    T : float
        Sampling period (units: s)
        Time interval between consecutive clock state samples
    nperiods : int, optional
        Number of sampling periods to simulate, by default 1
        Must be positive integer

    Returns
    -------
    bias_m : numpy.ndarray
        Clock bias in meters, shape (nperiods,)
        Cumulative clock bias converted to range units using speed of light
    drift_ms : numpy.ndarray
        Clock drift in meters per second, shape (nperiods,)
        Clock frequency drift converted to range rate units using speed of light

    Notes
    -----
    The two-state clock model represents the clock state vector as:

    x(t) = [bias(t), drift(t)]^T

    The state evolution follows:
    x(k+1) = Φ*x(k) + w(k)

    where Φ is the state transition matrix and w(k) is process noise with
    covariance matrix Q derived from the Allan variance parameters.

    The covariance matrix is:
    Q = [[s_f*T + (1/3)*s_g*T^3, (1/2)*s_g*T^2],
         [(1/2)*s_g*T^2,          s_g*T        ]]

    where s_f = h0/2 and s_g = h2*2*π^2

    Examples
    --------
    >>> # Simulate 100 periods of 1-second samples for a rubidium clock
    >>> bias, drift = compute_clock_states(2e-22, 1e-30, 1.0, 100)
    >>> print(f"Final bias: {bias[-1]:.3f} meters")
    >>> print(f"Final drift: {drift[-1]:.6f} m/s")

    References
    ----------
    .. [1] L. Galleani, "A tutorial on the two-state model of the atomic clock
           noise," Metrologia, vol. 45, no. 6, p. S175, Dec. 2008,
           doi: 10.1088/0026-1394/45/6/S23.
    """
    # Input validation
    if nperiods <= 0:
        raise ValueError("nperiods must be a positive integer")
    if T <= 0:
        raise ValueError("Sampling period T must be positive")
    if h0 < 0 or h2 < 0:
        raise ValueError("Allan variance coefficients must be non-negative")

    # Two-state clock model white noise spectral amplitudes
    sf = h0 / 2  # White phase noise spectral amplitude
    sg = h2 * 2 * np.pi**2  # Random walk phase noise spectral amplitude

    # Error covariance noise matrix
    covariance = np.array(
        [
            [sf * T + (1 / 3) * sg * T**3, (1 / 2) * sg * T**2],
            [(1 / 2) * sg * T**2, sg * T],
        ]
    )  # [s], [s/s]

    # Generate correlated noise samples
    bias_noise, drift_noise = np.random.multivariate_normal(
        mean=[0, 0], cov=covariance, size=nperiods
    ).T

    # Compute cumulative states
    drift_ss = np.cumsum(drift_noise)  # Cumulative drift in s/s
    bias_s = np.cumsum(drift_ss * T) + np.cumsum(bias_noise)  # Cumulative bias in s

    # Convert to range units using speed of light
    drift_ms = drift_ss * SPEED_OF_LIGHT  # Convert to m/s
    bias_m = bias_s * SPEED_OF_LIGHT  # Convert to m

    return bias_m, drift_ms
