import datetime as dt

import numpy as np
from navtools.conversions import geodetic2ecef
from navsim.emitters import SatelliteEmitters

from navplot.plotter import NavPlotter, NavplotConstellation

plt = NavPlotter()

# define simulation parameters (Toomer's Corner)
latitude = 32.60649884093691
longitude = -85.48191280674644
ecef_pos = np.array(geodetic2ecef(lat=latitude, lon=longitude, alt=0.0, deg=True))
focal_position_name = "Auburn, AL"

constellations = ["gps", "iridium"]

initial_datetime = dt.datetime(year=2025, month=7, day=20, tzinfo=dt.timezone.utc)
duration = 0  # [s]
time_step = 60  # [s]

# initialize datetimes
ntime_steps = int(np.ceil(duration / time_step)) + 1
timeseries = np.linspace(start=0.0, stop=duration, num=ntime_steps)
datetimes = [initial_datetime + dt.timedelta(seconds=step) for step in timeseries]

# simulate satellite states
satellites = SatelliteEmitters(constellations=constellations)
satellite_states = satellites.process(utc_timestamps=datetimes)

navplot_constellations = []
for cnst in constellations:
    positions = {
        sv_name: states[0]
        for sv_name, states in satellite_states.items()
        if cnst.casefold() == satellites.get_constellation(emitter_id=sv_name)
    }
    velocities = {
        sv_name: states[1]
        for sv_name, states in satellite_states.items()
        if cnst.casefold() == satellites.get_constellation(emitter_id=sv_name)
    }

    if positions and velocities:
        navplot_cnst = NavplotConstellation(
            name=cnst, positions=positions, velocities=velocities
        )

        navplot_constellations.append(navplot_cnst)

plt.set_background("black")
plt.plot_earth(
    focal_position=ecef_pos,
    focal_position_name=focal_position_name,
)
plt.plot_satellites(constellations=navplot_constellations, point_size=10)
plt.add_triad()
plt.plot_ecef(label_color="white")
plt.show()
