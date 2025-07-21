__all__ = ["datetime2gps"]

import datetime as dt
import numpy as np
from numpy.typing import ArrayLike, NDArray

from navtools.constants import GPS_EPOCH, SECONDS_PER_WEEK


def datetime2gps(
    datetime: ArrayLike[dt.datetime],
) -> (
    tuple[float, float, float]
    | tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]
):
    """
    Convert a datetime or array of datetimes to GPS time.

    This function converts a single or multiple datetime objects to
    GPS time, returning the GPS seconds, GPS week, and GPS time of week
    (TOW). The conversion accounts for the GPS epoch starting on
    January 6, 1980.

    Parameters
    ----------
    datetime : array_like of datetime.datetime
        A single or array of datetime objects to be converted to GPS time.
        If the input is a scalar, the output will be scalar as well.

    Returns
    -------
    tuple of (float or ndarray of float)
        A tuple containing:
        - GPS seconds: The number of seconds since the GPS epoch.
        - GPS week: The GPS week number.
        - GPS time of week: The time of week in seconds.

    Notes
    -----
    The input datetime(s) are assumed to be in UTC. If a naive datetime
    (without timezone information) is provided, it is assumed to be in UTC.

    Examples
    --------
    >>> from datetime import datetime
    >>> gps_seconds, gps_week, gps_tow = datetime2gps(datetime(2025, 7, 21, 17, 0, 0))
    >>> gps_seconds
    2350000000.0
    >>> gps_week
    1234
    >>> gps_tow
    567890.0

    >>> from datetime import datetime
    >>> gps_seconds, gps_week, gps_tow = datetime2gps([datetime(2025, 7, 21, 17, 0, 0), datetime(2025, 7, 22, 17, 0, 0)])
    >>> gps_seconds
    array([2350000000.0, 2350003600.0])
    >>> gps_week
    array([1234, 1234])
    >>> gps_tow
    array([567890.0, 567890.0])
    """
    datetime_array: np.ndarray = np.atleast_1d(datetime)

    # ensure all datetimes are timezone-aware (assume UTC if naive)
    datetime_array = np.array(
        [
            time if time.tzinfo is not None else time.replace(tzinfo=dt.timezone.utc)
            for time in datetime_array
        ]
    )

    gps_seconds = np.array(
        [(time - GPS_EPOCH).total_seconds() for time in datetime_array]
    )
    gps_week = np.floor(gps_seconds / SECONDS_PER_WEEK).astype(int)
    gps_tow = gps_seconds % SECONDS_PER_WEEK

    if np.isscalar(datetime_array):
        return gps_seconds[0], gps_week[0], gps_tow[0]
    else:
        return gps_seconds, gps_week, gps_tow
