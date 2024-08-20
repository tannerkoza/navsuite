"""constants.py contains constants commonly used in navigation"""

# physical
"""a collection of physical constants used across physics in general
"""
SPEED_OF_LIGHT: float = 299792458.0  # [m/s]
BOLTZMANN: float = 1.38e-23  # [J/K]
GRAVITY: float = 9.80665  # acceleration due to gravity (Earth) [m/s^2]

# global datums
""" a collection of constants specific to global datums (e.g., WGS84, GRS80, etc.) 
"""
WGS84_R0: float = 6378137.0  # WGS84 equatorial radius [m]
WGS84_RP: float = 6356752.31425  # WGS84 polar radius [m]
WGS84_F: float = 1.0 / 298.257223563  # WGS84 flattening
WGS84_E: float = 0.0818191908425  # WGS84 eccentricity
WGS84_EARTH_RATE: float = 7.292115e-5  # WGS84 Earth rotation rate [rad/s]

GRS80_R0: float = WGS84_R0  # GRS80 equatorial radius [m]
GRS80_RP: float = 6356752.31414  # GRS80 polar radius [m]
GRS80_F: float = 1.0 / 298.257222101  # GRS80 flattening
GRS80_E: float = 0.0818191910428  # GRS80 eccentricity
