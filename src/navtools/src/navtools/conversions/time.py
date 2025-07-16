import numpy as np
import datetime as dt
from navtools.constants import SECONDS_PER_WEEK, GPS_EPOCH


def datetime_to_gps(datetime: dt.datetime):
    datetime = np.atleast_1d(datetime)

    # Ensure all datetimes are timezone-aware (assume UTC if naive)
    datetime = np.array(
        [
            time if time.tzinfo is not None else time.replace(tzinfo=dt.timezone.utc)
            for time in datetime
        ]
    )

    gps_seconds = np.array([(time - GPS_EPOCH).total_seconds() for time in datetime])
    gps_week = np.floor(gps_seconds / SECONDS_PER_WEEK).astype(int)
    gps_tow = gps_seconds % SECONDS_PER_WEEK

    if np.isscalar(datetime):
        return gps_week[0], gps_tow[0]
    else:
        return gps_week, gps_tow
