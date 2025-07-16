import datetime as dt

import numpy as np

from navtools.constants import GPS_EPOCH, SECONDS_PER_WEEK


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
        return gps_seconds, gps_week, gps_tow
