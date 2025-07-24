import datetime as dt


# time
"""A collection of time constants."""
SECONDS_PER_HOUR = 3600.0
SECONDS_PER_DAY = SECONDS_PER_HOUR * 24
SECONDS_PER_WEEK = SECONDS_PER_DAY * 7
SECONDS_PER_YEAR = SECONDS_PER_WEEK * 52
GPS_EPOCH = dt.datetime(1980, 1, 6, tzinfo=dt.timezone.utc)

# physical
"""A collection of physical constants used across physics in general."""
SPEED_OF_LIGHT: float = 299792458.0  # [m/s]
BOLTZMANN: float = 1.38e-23  # [J/K]
GRAVITY: float = 9.80665  # acceleration due to gravity (Earth) [m/s^2]
EARTH_RATE: float = 7.292115e-5  # WGS84 Earth rotation rate [rad/s]
