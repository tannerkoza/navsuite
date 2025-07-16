import erfa
import numpy as np

from astropy.time import Time, TimeDelta
from astropy import units as u
from astropy.coordinates.builtin_frames.utils import get_polar_motion


def teme2itrf(time, teme_pos, teme_vel):
    def smart_mmult(C, X):
        # C: (T, 3, 3), X: (N, T, 3)
        return np.einsum("tij,ntj->nti", C, X)

    dt = 1.0
    half_dt = dt / 2

    C = C_teme2itrf(time=time)

    itrf_pos = smart_mmult(C, teme_pos)
    itrf_vel = smart_mmult(C, teme_vel)

    itrf_pos_fwd = smart_mmult(
        C_teme2itrf(Time(time) + TimeDelta(half_dt * u.second)), teme_pos
    )
    itrf_pos_back = smart_mmult(
        C_teme2itrf(Time(time) - TimeDelta(half_dt * u.second)), teme_pos
    )

    itrf_vel += (itrf_pos_fwd - itrf_pos_back) / dt

    return itrf_pos, itrf_vel


def C_teme2itrf(time: Time | list[Time]):
    jd1 = time.ut1.jd1
    jd2 = time.ut1.jd2

    time = time if time.shape else [time]

    # Assume get_polar_motion can handle vector input — otherwise vectorize/memoize it
    xp, yp = np.transpose([get_polar_motion(t) for t in time])

    # ERFA: gst from UT1
    gst = erfa.gmst82(jd1, jd2)

    pmmat = erfa.pom00(xp, yp, 0)
    C = erfa.c2tcio(np.eye(3), gst, pmmat)

    return C
